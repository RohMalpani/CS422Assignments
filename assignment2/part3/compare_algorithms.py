"""Collect comparable CUBIC, Reno, and BBR TCP_INFO runs; plotting is separate."""

import argparse
import csv
from pathlib import Path
import socket
import sys
import time
from uuid import uuid4

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "part1"))
from goodput import GoodputSampler
from iperf3_client import Iperf3Error, run_test
from select_servers import Server, ServerPool

ALGORITHMS = ("cubic", "reno", "bbr")
DEFAULT_REPS = 3
DEFAULT_DURATION = 60
DEFAULT_INTERVAL = 1.0
RUN_FIELDS = ("session_id", "run_id", "test_order", "rep", "host", "port", "site",
              "country", "requested_algorithm", "actual_algorithm", "status", "error",
              "bytes_sent", "server_bytes", "duration_s")
SAMPLE_FIELDS = ("session_id", "run_id", "test_order", "rep", "host", "port", "site",
                 "country", "requested_algorithm", "actual_algorithm", "timestamp",
                 "elapsed_s", "interval_s", "bytes_acked", "goodput_bps", "snd_cwnd",
                 "rtt_us", "rttvar_us", "total_retrans", "retrans_interval", "lost",
                 "pacing_rate_Bps", "delivery_rate_Bps")
DEST_FIELDS = ("session_id", "host", "port", "site", "country")


def destination(value):
    """Parse HOST:PORT or [IPv6]:PORT."""
    host, sep, port = (value[1:].partition("]:") if value.startswith("[")
                       else value.rpartition(":"))
    try:
        port = int(port)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("destination must be HOST:PORT") from exc
    if not sep or not host or not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("destination must be HOST:PORT")
    return Server(host, port)


def check_algorithms():
    """Stop before any public tests if a required kernel algorithm is unavailable."""
    for algorithm in ALGORITHMS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_CONGESTION, algorithm.encode())
                actual = sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_CONGESTION, 16)
            except OSError as exc:
                raise RuntimeError(f"{algorithm} unavailable or not permitted: {exc}") from exc
            if actual.split(b"\0", 1)[0].decode() != algorithm:
                raise RuntimeError(f"kernel did not select {algorithm}")


def ordered_algorithms(rep, destination_index):
    """Rotate test order so one algorithm is not always tested first."""
    start = (rep - 1 + destination_index) % len(ALGORITHMS)
    return ALGORITHMS[start:] + ALGORITHMS[:start]


def collect_one(server, algorithm, rep, session, order, duration, interval,
                run_writer, sample_writer, run_file, sample_file):
    run_id = f"{session}-{order:04d}"
    row = dict(session_id=session, run_id=run_id, test_order=order, rep=rep,
               host=server.host, port=server.port, site=server.site,
               country=server.country, requested_algorithm=algorithm,
               actual_algorithm="")
    sampler = GoodputSampler()
    start = time.monotonic()
    try:
        result = run_test(server.host, server.port, duration=duration,
                          congestion=algorithm, sample_interval=interval,
                          on_sample=sampler)
        actual = result["congestion"]
        streams = result["server_results"].get("streams") or []
        row.update(actual_algorithm=actual, bytes_sent=result["bytes_sent"],
                   server_bytes=streams[0].get("bytes", "") if streams else "")
        if actual != algorithm:
            row.update(status="failed", error=f"requested {algorithm}; got {actual}")
        elif not sampler.rows:
            row.update(status="failed", error="no TCP_INFO samples")
        else:
            row.update(status="ok", error="")
    except Iperf3Error as exc:
        row.update(status="failed", error=str(exc))
    row["duration_s"] = round(time.monotonic() - start, 3)
    run_writer.writerow(row)
    for sample in sampler.rows:
        sample_writer.writerow({**{k: row.get(k, "") for k in SAMPLE_FIELDS if k not in sample},
                                **sample})
    run_file.flush()
    sample_file.flush()
    print(f"{order:03d} rep {rep} {server.host}:{server.port} {algorithm}: "
          f"{row['status']} ({len(sampler.rows)} samples)"
          + (f" - {row['error']}" if row["error"] else ""), flush=True)
    return row["status"] == "ok"


def collect(args):
    if not sys.platform.startswith("linux"):
        raise RuntimeError("TCP_INFO collection requires Linux or WSL2")
    check_algorithms()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    session = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
    pool = None if args.destination else ServerPool(args.servers, args.seed)
    candidates = iter(args.destination)
    requested = len(args.destination) if args.destination else args.n
    chosen = []
    failures = order = 0

    with (args.out_dir / "part3_runs.csv").open("w", newline="") as run_file, \
         (args.out_dir / "part3_samples.csv").open("w", newline="") as sample_file, \
         (args.out_dir / "part3_destinations.csv").open("w", newline="") as dest_file:
        rw = csv.DictWriter(run_file, RUN_FIELDS)
        sw = csv.DictWriter(sample_file, SAMPLE_FIELDS)
        dw = csv.DictWriter(dest_file, DEST_FIELDS)
        rw.writeheader()
        sw.writeheader()
        dw.writeheader()
        try:
            while len(chosen) < requested and (args.destination or failures < args.max_failures):
                server = next(candidates, None) if args.destination else pool.next_server()
                if server is None:
                    break
                successes = []
                for algorithm in ordered_algorithms(1, len(chosen)):
                    order += 1
                    successes.append(collect_one(server, algorithm, 1, session, order,
                                                 args.duration, args.interval, rw, sw,
                                                 run_file, sample_file))
                if all(successes):
                    chosen.append(server)
                    dw.writerow(dict(session_id=session, host=server.host, port=server.port,
                                     site=server.site, country=server.country))
                    dest_file.flush()
                else:
                    failures += 1
                    print(f"Replacing {server.host}:{server.port} "
                          f"({failures}/{args.max_failures} failed candidates)", flush=True)

            for rep in range(2, args.reps + 1):
                for index, server in enumerate(chosen):
                    for algorithm in ordered_algorithms(rep, index):
                        order += 1
                        collect_one(server, algorithm, rep, session, order, args.duration,
                                    args.interval, rw, sw, run_file, sample_file)
        except KeyboardInterrupt:
            print("Interrupted; completed tests are saved.")
    print(f"Selected {len(chosen)}/{requested} destinations; {order} attempts. "
          f"Data: {args.out_dir}")
    if len(chosen) < requested:
        print(f"SHORTFALL: {requested - len(chosen)} destinations.")
    return chosen


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--servers", type=Path, default=BASE / "servers.csv")
    ap.add_argument("--destination", type=destination, action="append", default=[],
                    help="fixed HOST:PORT; repeat for multiple destinations")
    ap.add_argument("-n", type=int, default=10, help="destinations from --servers")
    ap.add_argument("--duration", type=int, default=DEFAULT_DURATION)
    ap.add_argument("--interval", type=float, default=DEFAULT_INTERVAL)
    ap.add_argument("--reps", type=int, default=DEFAULT_REPS)
    ap.add_argument("--max-failures", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out-dir", type=Path, default=BASE / "results")
    return ap


def main():
    ap = build_parser()
    args = ap.parse_args()
    if args.n < 1 or args.duration < 1 or args.interval <= 0 or args.reps < 2 or args.max_failures < 1:
        ap.error("n, duration, max-failures > 0; interval > 0; reps >= 2 required")
    if len({(s.host, s.port) for s in args.destination}) != len(args.destination):
        ap.error("--destination entries must be unique")
    try:
        collect(args)
    except (OSError, RuntimeError) as exc:
        ap.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()

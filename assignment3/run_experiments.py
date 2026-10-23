# Assignment 3 driver (adapted from assignment2/part1/run_experiments.py).
# Run matched iperf3 tests for every algorithm against the same destinations, log every sample.
#
# Design (see DECISIONS.md): each destination is tested with all algorithms back to back, in an
# order that is rotated per destination and repetition, so no algorithm always runs first/last.
# Rep 1 doubles as server selection: a destination counts only if every algorithm succeeds on
# it, otherwise it is replaced by a fresh random one (bounded). Later reps reuse the same
# destinations (host AND port), so all algorithms see the same path.
#
# Outputs (in --out-dir):
#   samples.csv     one row per sampling interval (goodput + TCP stats), long format
#   runs.csv        one row per test attempt: ok/failed, error, bytes, algorithm, test order
#   run_config.json arguments, kernel, algorithms, chosen destinations (for reproduction)
import argparse
import csv
import json
import os
import platform
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "client"))
import goodput
import iperf3_client
from select_servers import ServerPool

DEFAULT_ALGORITHMS = ["cubic", "reno", "bbr", "cs422_custom"]
AVAILABLE_CC = "/proc/sys/net/ipv4/tcp_available_congestion_control"

RUN_FIELDS = ["run_id", "rep", "order_pos", "seq", "host", "port", "site", "country", "algorithm",
              "status", "error", "bytes_sent", "server_bytes", "duration_s"]
SAMPLE_FIELDS = ["run_id", "rep", "order_pos", "seq", "host", "port", "algorithm"] + [
    "timestamp", "elapsed_s", "interval_s", "bytes_acked", "goodput_bps", "snd_cwnd", "rtt_us",
    "rttvar_us", "total_retrans", "retrans_interval", "lost", "pacing_rate_Bps", "delivery_rate_Bps"]


def check_algorithms(algorithms):
    """Fail fast if the kernel doesn't offer an algorithm (e.g. module lost after a WSL restart)."""
    with open(AVAILABLE_CC) as f:
        available = f.read().split()
    missing = [a for a in algorithms if a not in available]
    if missing:
        sys.exit(f"Not available in this kernel: {missing} (available: {available}). "
                 f"Load them first (sudo modprobe tcp_bbr; sudo insmod kernel/tcp_cs422.ko).")


def rotated(algorithms, shift):
    """Cyclic rotation: shift 0 -> a,b,c,d; shift 1 -> b,c,d,a; ..."""
    k = shift % len(algorithms)
    return algorithms[k:] + algorithms[:k]


def run_one(server, algo, args, run_id, rep, order_pos, seq, runs_w, samples_w, out_files):
    """Run one test of `algo` against `server`, write its rows, return True on success."""
    sampler = goodput.GoodputSampler()
    row = {"run_id": run_id, "rep": rep, "order_pos": order_pos, "seq": seq,
           "host": server.host, "port": server.port, "site": server.site,
           "country": server.country, "algorithm": algo}
    t0 = time.monotonic()
    try:
        res = iperf3_client.run_test(server.host, server.port, duration=args.duration,
                                     congestion=algo, sample_interval=args.interval,
                                     on_sample=sampler)
    except iperf3_client.Iperf3Error as e:
        row.update(status="failed", error=str(e), duration_s=round(time.monotonic() - t0, 2))
        runs_w.writerow(row)
        out_files[0].flush()
        print(f"    {algo}: FAILED: {e}")
        return False

    used = res["congestion"]  # what the kernel actually used
    row.update(status="ok", error="", algorithm=used, bytes_sent=res["bytes_sent"],
               server_bytes=res["server_results"].get("streams", [{}])[0].get("bytes", ""),
               duration_s=round(time.monotonic() - t0, 2))
    runs_w.writerow(row)
    for s in sampler.rows:
        samples_w.writerow({"run_id": run_id, "rep": rep, "order_pos": order_pos, "seq": seq,
                            "host": server.host, "port": server.port, "algorithm": used, **s})
    for f in out_files:
        f.flush()  # keep data on disk even if a later test crashes or we get Ctrl+C
    ok_rows = sampler.rows
    mean = sum(r["goodput_bps"] for r in ok_rows) / len(ok_rows) / 1e6 if ok_rows else 0
    note = "" if used == algo else f"  (WARNING: asked for {algo})"
    print(f"    {algo}: ok, {len(ok_rows)} samples, mean goodput {mean:.2f} Mbps{note}")
    return used == algo


def run_destination(server, dest_idx, rep, args, run_id, seq, runs_w, samples_w, files):
    """Test every algorithm on one destination in rotated order. Returns (all_ok, next_seq)."""
    order = rotated(args.algorithms, dest_idx + rep - 1)
    print(f"  order: {' -> '.join(order)}")
    all_ok = True
    for pos, algo in enumerate(order, 1):
        seq += 1
        if not run_one(server, algo, args, run_id, rep, pos, seq, runs_w, samples_w, files):
            all_ok = False
        time.sleep(args.pause)  # let the server and path settle between tests
    return all_ok, seq


def run_experiments(args):
    check_algorithms(args.algorithms)
    os.makedirs(args.out_dir, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    pool = ServerPool(args.servers, args.seed)
    chosen, failures, seq = [], 0, 0

    with open(os.path.join(args.out_dir, "runs.csv"), "w", newline="") as rf, \
         open(os.path.join(args.out_dir, "samples.csv"), "w", newline="") as sf:
        runs_w = csv.DictWriter(rf, RUN_FIELDS)
        samples_w = csv.DictWriter(sf, SAMPLE_FIELDS)
        runs_w.writeheader()
        samples_w.writeheader()
        files = (rf, sf)

        try:
            for rep in range(1, args.reps + 1):
                print(f"=== repetition {rep}/{args.reps} ===")
                if rep == 1:
                    while len(chosen) < args.n and failures < args.max_failures:
                        server = pool.next_server()
                        if server is None:
                            print("server list exhausted")
                            break
                        print(f"[{len(chosen) + 1}/{args.n}] {server}")
                        ok, seq = run_destination(server, len(chosen), rep, args, run_id, seq,
                                                  runs_w, samples_w, files)
                        if ok:
                            chosen.append(server)
                        else:
                            failures += 1
                else:
                    for i, server in enumerate(chosen):
                        print(f"[{i + 1}/{len(chosen)}] {server}")
                        _, seq = run_destination(server, i, rep, args, run_id, seq,
                                                 runs_w, samples_w, files)
        except KeyboardInterrupt:
            print("\ninterrupted - data collected so far has been saved")

    with open(os.path.join(args.out_dir, "run_config.json"), "w") as f:
        json.dump({"run_id": run_id, "args": vars(args), "kernel": platform.release(),
                   "destinations": [str(s) for s in chosen],
                   "destination_ports": {s.host: s.port for s in chosen},
                   "rejected_destinations": failures}, f, indent=2)

    print(f"\nDone: {len(chosen)}/{args.n} destinations succeeded, {failures} replaced "
          f"(bound {args.max_failures}).")
    if len(chosen) < args.n:
        print(f"SHORTFALL: requested {args.n} destinations, got {len(chosen)}.")
    return chosen


def build_parser():
    ap = argparse.ArgumentParser(description="Assignment 3: matched iperf3 goodput measurements (Linux/WSL2).")
    ap.add_argument("--servers", default="servers.csv", help="server list CSV (iperf3serverlist.net format)")
    ap.add_argument("-n", type=int, default=10, help="number of destinations")
    ap.add_argument("--duration", type=int, default=10, help="seconds per test")
    ap.add_argument("--interval", type=float, default=1.0, help="sampling interval, seconds")
    ap.add_argument("--reps", type=int, default=3, help="repetitions per destination")
    ap.add_argument("--algorithms", nargs="+", default=DEFAULT_ALGORITHMS,
                    help="TCP congestion-control algorithms to compare")
    ap.add_argument("--pause", type=float, default=3.0, help="seconds between tests")
    ap.add_argument("--max-failures", type=int, default=10, help="max replaced destinations before giving up")
    ap.add_argument("--seed", type=int, default=None, help="RNG seed for reproducible server choice")
    ap.add_argument("--out-dir", default="results")
    return ap


if __name__ == "__main__":
    run_experiments(build_parser().parse_args())

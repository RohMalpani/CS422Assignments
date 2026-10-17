# Part 1 driver: pick n servers (with bounded replacement), run timed iperf3 tests, log every sample.
#
# Outputs (in --out-dir):
#   part1_samples.csv  one row per sampling interval (goodput + TCP stats), long format
#   part1_runs.csv     one row per test attempt: ok/failed, error text, bytes, actual algorithm
import argparse
import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import goodput
import iperf3_client
from select_servers import ServerPool

RUN_FIELDS = ["run_id", "rep", "host", "port", "site", "country", "algorithm", "status",
              "error", "bytes_sent", "server_bytes", "duration_s"]
SAMPLE_FIELDS = ["run_id", "rep", "host", "port", "algorithm"] + [
    "timestamp", "elapsed_s", "interval_s", "bytes_acked", "goodput_bps", "snd_cwnd", "rtt_us",
    "rttvar_us", "total_retrans", "retrans_interval", "lost", "pacing_rate_Bps", "delivery_rate_Bps"]


def run_one(server, args, run_id, rep, runs_w, samples_w, out_files):
    """Run one test against `server`, write its rows, return True on success."""
    sampler = goodput.GoodputSampler()
    row = {"run_id": run_id, "rep": rep, "host": server.host, "port": server.port,
           "site": server.site, "country": server.country,
           "algorithm": args.algorithm or "default"}
    t0 = time.monotonic()
    try:
        res = iperf3_client.run_test(server.host, server.port, duration=args.duration,
                                     congestion=args.algorithm, sample_interval=args.interval,
                                     on_sample=sampler)
    except iperf3_client.Iperf3Error as e:
        row.update(status="failed", error=str(e), duration_s=round(time.monotonic() - t0, 2))
        runs_w.writerow(row)
        out_files[0].flush()
        print(f"  FAILED: {e}")
        return False

    algo = res["congestion"]  # what the kernel actually used
    row.update(status="ok", error="", algorithm=algo, bytes_sent=res["bytes_sent"],
               server_bytes=res["server_results"].get("streams", [{}])[0].get("bytes", ""),
               duration_s=round(time.monotonic() - t0, 2))
    runs_w.writerow(row)
    for s in sampler.rows:
        samples_w.writerow({"run_id": run_id, "rep": rep, "host": server.host,
                            "port": server.port, "algorithm": algo, **s})
    for f in out_files:
        f.flush()  # keep data on disk even if a later test crashes or we get Ctrl+C
    ok_rows = sampler.rows
    mean = sum(r["goodput_bps"] for r in ok_rows) / len(ok_rows) / 1e6 if ok_rows else 0
    print(f"  ok: {len(ok_rows)} samples, mean goodput {mean:.2f} Mbps, algorithm {algo}")
    return True


def run_experiments(args):
    os.makedirs(args.out_dir, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    pool = ServerPool(args.servers, args.seed)
    chosen, failures = [], 0

    with open(os.path.join(args.out_dir, "part1_runs.csv"), "w", newline="") as rf, \
         open(os.path.join(args.out_dir, "part1_samples.csv"), "w", newline="") as sf:
        runs_w = csv.DictWriter(rf, RUN_FIELDS)
        samples_w = csv.DictWriter(sf, SAMPLE_FIELDS)
        runs_w.writeheader()
        samples_w.writeheader()
        files = (rf, sf)

        try:
            for rep in range(1, args.reps + 1):
                print(f"=== repetition {rep}/{args.reps} ===")
                if rep == 1:
                    # First repetition doubles as server selection: a failed server is replaced
                    # by a fresh random one, until we have n or hit the failure bound.
                    while len(chosen) < args.n and failures < args.max_failures:
                        server = pool.next_server()
                        if server is None:
                            print("server list exhausted")
                            break
                        print(f"[{len(chosen) + 1}/{args.n}] {server}")
                        if run_one(server, args, run_id, rep, runs_w, samples_w, files):
                            chosen.append(server)
                        else:
                            failures += 1
                else:
                    # Later repetitions reuse the same destinations (same paths -> comparable runs).
                    for i, server in enumerate(chosen, 1):
                        print(f"[{i}/{len(chosen)}] {server}")
                        run_one(server, args, run_id, rep, runs_w, samples_w, files)
        except KeyboardInterrupt:
            print("\ninterrupted - data collected so far has been saved")

    print(f"\nDone: {len(chosen)}/{args.n} destinations succeeded, {failures} failed attempts "
          f"(bound {args.max_failures}).")
    if len(chosen) < args.n:
        print(f"SHORTFALL: requested {args.n} destinations, got {len(chosen)}.")
    return chosen


def build_parser():
    ap = argparse.ArgumentParser(description="Assignment 2 part 1: iperf3 goodput measurements (Linux/WSL2).")
    ap.add_argument("--servers", default="servers.csv", help="server list CSV (iperf3serverlist.net format)")
    ap.add_argument("-n", type=int, default=10, help="number of destinations")
    ap.add_argument("--duration", type=int, default=60, help="seconds per test")
    ap.add_argument("--interval", type=float, default=1.0, help="sampling interval, seconds")
    ap.add_argument("--reps", type=int, default=1, help="repetitions per destination")
    ap.add_argument("--algorithm", default=None, help="TCP congestion control (default: OS default)")
    ap.add_argument("--max-failures", type=int, default=10, help="max failed attempts before giving up on replacements")
    ap.add_argument("--seed", type=int, default=None, help="RNG seed for reproducible server choice")
    ap.add_argument("--out-dir", default="results")
    return ap


if __name__ == "__main__":
    run_experiments(build_parser().parse_args())

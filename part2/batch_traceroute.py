"""
Step 3: run traceroute across all 5 selected targets, skip/log any that
never reach their destination, and persist raw per-hop results to disk
for the plotting step (assignment 1, part 2a/2b).
"""

import argparse
import json
import time

from select_targets import DEFAULT_N, DEFAULT_SEED, load_servers, pick_targets
from traceroute_runner import Hop, TracerouteResult, hop_min_rtt, run_traceroute


MAX_ATTEMPTS = 2  # 1 retry -- see DECISIONS.md: back-to-back traceroute runs
                   # were observed to fail transiently even against hosts
                   # that reach fine when retried, so a single non-reach
                   # isn't treated as proof the destination is dead.


def run_batch(targets: list[str]) -> tuple[list[TracerouteResult], list[TracerouteResult]]:
    """Run traceroute against each target, retrying once on a non-reach
    before giving up. Returns (reached, skipped) -- skipped destinations
    are logged, not replaced (see DECISIONS.md)."""
    reached, skipped = [], []
    for i, target in enumerate(targets, start=1):
        for attempt in range(1, MAX_ATTEMPTS + 1):
            print(f"[{i}/{len(targets)}] traceroute -> {target} (attempt {attempt}/{MAX_ATTEMPTS}) ...", flush=True)
            start = time.monotonic()
            result = run_traceroute(target)
            elapsed = time.monotonic() - start
            print(f"    reached={result.reached}  hops={len(result.hops)}  ({elapsed:.1f}s)")
            if result.reached:
                break
        (reached if result.reached else skipped).append(result)
    return reached, skipped


def result_to_dict(result: TracerouteResult) -> dict:
    return {
        "target": result.target,
        "resolved_ip": result.resolved_ip,
        "reached": result.reached,
        "hops": [
            {
                "number": hop.number,
                "address": hop.address,
                "probe_rtts_ms": hop.probe_rtts_ms,
                "min_rtt_ms": hop_min_rtt(hop),
            }
            for hop in result.hops
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Run traceroute against N random targets.")
    parser.add_argument("--input", default="../ips.csv")
    parser.add_argument("--n", type=int, default=DEFAULT_N)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", default="part2/data/traceroute_results.json")
    args = parser.parse_args()

    servers = load_servers(args.input)
    targets = pick_targets(servers, n=args.n, seed=args.seed)
    target_hosts = [t.host for t in targets]
    print(f"Selected targets: {target_hosts}")

    reached, skipped = run_batch(target_hosts)

    print(f"\n{len(reached)}/{len(target_hosts)} destinations reached; {len(skipped)} skipped (non-responsive).")
    if skipped:
        print("Skipped:", [r.target for r in skipped])

    output = {
        "reached": [result_to_dict(r) for r in reached],
        "skipped": [{"target": r.target, "resolved_ip": r.resolved_ip} for r in skipped],
    }
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Wrote raw results to {args.output}")


if __name__ == "__main__":
    main()

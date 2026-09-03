"""
Orchestrator for assignment 1, part 2 (Latency Breakdown): selects targets,
runs traceroute against all of them, and generates both required plots --
all in one shot, per the assignment's automation requirement.

Usage:
    python part2/run.py --input ips.csv
"""

import argparse

from batch_traceroute import result_to_dict, run_batch
from plotting import load_results, plot_hopcount_vs_rtt, plot_stacked_bar
from select_targets import DEFAULT_N, DEFAULT_SEED, load_servers, pick_targets

import json


def main():
    parser = argparse.ArgumentParser(description="Run the full part 2 pipeline: select targets, traceroute, plot.")
    parser.add_argument("--input", default="../ips.csv", help="Path to the server list CSV")
    parser.add_argument("--n", type=int, default=DEFAULT_N)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--data-out", default="data/traceroute_results.json")
    parser.add_argument("--plots-out", default="results")
    args = parser.parse_args()

    # Step 1: pick targets
    servers = load_servers(args.input)
    targets = pick_targets(servers, n=args.n, seed=args.seed)
    target_hosts = [t.host for t in targets]
    print(f"Selected {len(target_hosts)} targets (seed={args.seed}): {target_hosts}")

    # Steps 2-3: traceroute each target (with retry), skip non-responsive
    reached, skipped = run_batch(target_hosts)
    print(f"\n{len(reached)}/{len(target_hosts)} destinations reached; {len(skipped)} skipped (non-responsive).")
    if skipped:
        print("Skipped:", [r.target for r in skipped])

    output = {
        "reached": [result_to_dict(r) for r in reached],
        "skipped": [{"target": r.target, "resolved_ip": r.resolved_ip} for r in skipped],
    }
    with open(args.data_out, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Wrote raw results to {args.data_out}")

    # Steps 4-5: plots
    results = load_results(args.data_out)
    if not results:
        print("No reached destinations -- skipping plots.")
        return

    stacked_path = f"{args.plots_out}/latency_breakdown_stacked_bar.pdf"
    scatter_path = f"{args.plots_out}/hopcount_vs_rtt_scatter.pdf"
    plot_stacked_bar(results, stacked_path)
    plot_hopcount_vs_rtt(results, scatter_path)
    print(f"Wrote {stacked_path}")
    print(f"Wrote {scatter_path}")


if __name__ == "__main__":
    main()

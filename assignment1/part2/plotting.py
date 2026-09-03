"""
Steps 4 & 5: build the two required plots for part 2 (assignment 1):
  (b) stacked bar chart of per-hop incremental latency, per destination
  (c) scatter plot of hop count vs total RTT, per destination

Reads the raw traceroute JSON produced by batch_traceroute.py.
"""

import argparse
import json

import matplotlib
import matplotlib.pyplot as plt
from matplotlib import cm

matplotlib.use("Agg")  # headless -- we only write files, never show a window


def load_results(json_path: str) -> list[dict]:
    with open(json_path) as f:
        data = json.load(f)
    return data["reached"]  # only completed traceroutes get plotted


def incremental_latencies(hops: list[dict]) -> list[tuple[int, float]]:
    """Turn a list of hop dicts (as stored in the results JSON) into
    (hop_number, incremental_latency_ms) pairs.

    Only hops with a min_rtt_ms value are included -- a hop that never
    responded (all 3 probes timed out) has no RTT to attribute latency to.
    Its real delay, if any, ends up folded into the *next responsive* hop's
    increment, since that's the next point we actually have a cumulative
    RTT measurement for. This is a real limitation of traceroute-based
    measurement, not a bug -- worth calling out explicitly in the report.
    """
    increments = []
    last_rtt = 0.0
    for hop in hops:
        rtt = hop["min_rtt_ms"]
        if rtt is None:
            continue
        increments.append((hop["number"], max(0.0, rtt - last_rtt)))
        last_rtt = rtt
    return increments


def plot_stacked_bar(results: list[dict], output_path: str):
    fig, ax = plt.subplots(figsize=(10, 6))

    labels = [r["target"] for r in results]
    max_segments = max(len(incremental_latencies(r["hops"])) for r in results)
    cmap = matplotlib.colormaps["viridis"].resampled(max_segments)

    bottoms = [0.0] * len(results)
    for seg_idx in range(max_segments):
        seg_values = []
        for r in results:
            incs = incremental_latencies(r["hops"])
            seg_values.append(incs[seg_idx][1] if seg_idx < len(incs) else 0.0)
        ax.bar(labels, seg_values, bottom=bottoms, color=cmap(seg_idx), edgecolor="white", linewidth=0.3)
        bottoms = [b + v for b, v in zip(bottoms, seg_values)]

    ax.set_ylabel("Round-trip time (ms)")
    ax.set_xlabel("Destination")
    ax.set_title("Per-hop incremental latency breakdown (traceroute)")
    plt.xticks(rotation=30, ha="right")

    sm = cm.ScalarMappable(cmap=cmap, norm=matplotlib.colors.Normalize(vmin=1, vmax=max_segments))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax)
    cbar.set_label("Hop position along path")

    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def plot_hopcount_vs_rtt(results: list[dict], output_path: str):
    fig, ax = plt.subplots(figsize=(7, 6))

    hop_counts = [len(r["hops"]) for r in results]
    total_rtts = [r["hops"][-1]["min_rtt_ms"] for r in results]
    labels = [r["target"] for r in results]

    ax.scatter(hop_counts, total_rtts)
    for x, y, label in zip(hop_counts, total_rtts, labels):
        ax.annotate(label, (x, y), textcoords="offset points", xytext=(5, 5), fontsize=8)

    ax.set_xlabel("Hop count")
    ax.set_ylabel("Total RTT to destination (ms)")
    ax.set_title("Hop count vs. RTT")

    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Generate part 2 plots from traceroute results.")
    parser.add_argument("--input", default="part2/data/traceroute_results.json")
    parser.add_argument("--outdir", default="figures", help="Directory report.tex reads figures from")
    args = parser.parse_args()

    results = load_results(args.input)
    if not results:
        print("No reached destinations in results -- nothing to plot.")
        return

    # Filenames match what report.tex's \plotplaceholder calls expect.
    stacked_path = f"{args.outdir}/hop_latency_breakdown.pdf"
    scatter_path = f"{args.outdir}/hop_count_vs_rtt.pdf"

    plot_stacked_bar(results, stacked_path)
    plot_hopcount_vs_rtt(results, scatter_path)

    print(f"Wrote {stacked_path}")
    print(f"Wrote {scatter_path}")


if __name__ == "__main__":
    main()

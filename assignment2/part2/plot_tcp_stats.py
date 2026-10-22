"""Seven-page TCP-statistics PDF for Part 2, reusable by Part 3."""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from tcp_stats import load_tcp_stats, select_representative

BASE = Path(__file__).resolve().parents[1]
COLORS = ("#2a78d6", "#eb6834", "#1baf7a", "#8c5ec2")
METRICS = (
    ("snd_cwnd", "Congestion window", "snd_cwnd (segments)"),
    ("rtt_ms", "RTT estimate", "RTT (ms)"),
    ("retrans_interval", "Retransmissions per interval", "retransmissions / interval"),
    ("goodput_mbps", "Acknowledged goodput", "goodput (Mbps)"),
)


def shared_limits(samples):
    """Find metric ranges once so Part 3 can use identical scales in all PDFs."""
    limits = {"elapsed_s": (0, max(1.0, samples["elapsed_s"].max() * 1.02))}
    for metric, _, _ in METRICS:
        values = samples[metric].dropna()
        top = max(1.0, values.max() * 1.05) if not values.empty else 1.0
        # Leave a little space below zero when no loss occurred, so a zero
        # retransmission trace is visible instead of sitting on the axis line.
        bottom = -0.05 if metric == "retrans_interval" and not values.empty and values.max() == 0 else 0
        limits[metric] = (bottom, top)
    return limits


def _page(pdf, samples, algorithm, destination, metric, title, y_label,
          x_metric, x_label, limits, scatter=False):
    fig, ax = plt.subplots(figsize=(8.5, 6), facecolor="#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    groups = list(samples.groupby(["run_id", "rep"], sort=True))
    for index, ((_, rep), group) in enumerate(groups):
        points = group.sort_values("elapsed_s")
        color = COLORS[index % len(COLORS)]
        label = f"run {rep}"
        if scatter:
            ax.scatter(points[x_metric], points[metric], s=24, alpha=0.52,
                       color=color, edgecolors="none", label=label)
        else:
            ax.plot(points[x_metric], points[metric], color=color, linewidth=1.4,
                    alpha=0.85, label=label)

    ax.set(xlabel=x_label, ylabel=y_label, xlim=limits[x_metric], ylim=limits[metric])
    ax.grid(color="#e1e0d9", linewidth=0.65)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if len(groups) > 1:
        ax.legend(frameon=False, loc="best")
    if metric == "retrans_interval" or x_metric == "retrans_interval":
        fig.text(0.02, 0.02, "Loss proxy: new TCP retransmissions in each sample interval.",
                 fontsize=8, color="#52514e")
        if samples["retrans_interval"].fillna(0).eq(0).all():
            ax.text(0.5, 0.5, "No retransmissions observed", transform=ax.transAxes,
                    ha="center", va="center", color="#52514e", fontsize=10)
    host, port = destination
    fig.suptitle(f"{algorithm.upper()} | {host}:{port} | {title}", fontsize=13)
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    pdf.savefig(fig)
    plt.close(fig)


def plot_tcp_stats(samples, output_pdf, *, algorithm, destination, axis_limits):
    """Create four time-series and three scatter pages for one algorithm.

    `samples` contains Part 1's TCP_INFO fields plus rtt_ms and goodput_mbps.
    This same function renders the per-algorithm PDFs in Part 3.
    """
    data = samples[samples["algorithm"] == algorithm]
    if data.empty:
        raise ValueError(f"No TCP samples for algorithm {algorithm!r}")
    output_pdf = Path(output_pdf)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(output_pdf) as pdf:
        for metric, title, y_label in METRICS:
            _page(pdf, data, algorithm, destination, metric, title, y_label,
                  "elapsed_s", "elapsed time (s)", axis_limits)
        for x_metric, x_label in (
            ("snd_cwnd", "snd_cwnd (segments)"),
            ("rtt_ms", "RTT (ms)"),
            ("retrans_interval", "retransmissions / interval"),
        ):
            _page(pdf, data, algorithm, destination, "goodput_mbps",
                  f"{x_label} vs goodput", "goodput (Mbps)", x_metric,
                  x_label, axis_limits, scatter=True)
    return output_pdf


def make_part2_outputs(results_dir, plots_dir, *, algorithm=None, destination=None):
    """Render Part 2 directly from Part 1's saved measurements."""
    samples = load_tcp_stats(results_dir, algorithm=algorithm)
    chosen, address = select_representative(samples, destination=destination)
    actual_algorithm = chosen["algorithm"].iloc[0]
    output = Path(plots_dir) / "part2_tcp_stats.pdf"
    plot_tcp_stats(chosen, output, algorithm=actual_algorithm, destination=address,
                   axis_limits=shared_limits(chosen))
    print(f"Saved {output} (7 pages; {actual_algorithm} on {address[0]}:{address[1]})")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=BASE / "results")
    parser.add_argument("--plots-dir", type=Path, default=BASE / "plots")
    parser.add_argument("--algorithm", help="actual algorithm recorded by Part 1")
    parser.add_argument("--destination", help="representative HOST:PORT from Part 1")
    args = parser.parse_args()
    try:
        make_part2_outputs(args.results_dir, args.plots_dir,
                           algorithm=args.algorithm, destination=args.destination)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()

"""Render three seven-page TCP comparison PDFs from saved Part 3 CSVs."""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
ALGORITHMS = ("cubic", "reno", "bbr")
COLORS = ("#2a78d6", "#eb6834", "#1baf7a")
METRICS = (
    ("snd_cwnd", "Congestion window", "snd_cwnd (segments)"),
    ("rtt_ms", "RTT estimate", "RTT (ms)"),
    ("retrans_interval", "Retransmissions per interval", "retransmissions / interval"),
    ("goodput_mbps", "Acknowledged goodput", "goodput (Mbps)"),
)


def load_representative(results_dir, destination=None):
    """Keep only successful runs on a selected destination shared by all algorithms."""
    runs = pd.read_csv(results_dir / "part3_runs.csv")
    samples = pd.read_csv(results_dir / "part3_samples.csv")
    selected = pd.read_csv(results_dir / "part3_destinations.csv")
    if selected.empty:
        raise ValueError("No destination completed all three algorithms in repetition 1")
    good_runs = runs.loc[runs["status"] == "ok", ["run_id", "actual_algorithm"]]
    samples = samples.merge(good_runs, on="run_id", suffixes=("", "_verified"))
    samples = samples.merge(selected[["host", "port"]], on=["host", "port"])
    for column in ("elapsed_s", "snd_cwnd", "rtt_us", "retrans_interval", "goodput_bps"):
        samples[column] = pd.to_numeric(samples[column], errors="coerce")
    samples["rtt_ms"] = samples["rtt_us"] / 1000
    samples["goodput_mbps"] = samples["goodput_bps"] / 1e6

    if destination:
        host, sep, port = destination.rpartition(":")
        if not sep or not host or not port.isdigit():
            raise ValueError("--destination must be HOST:PORT")
        if host.startswith("[") and host.endswith("]"):
            host = host[1:-1]
        candidates = [(host, int(port))]
    else:
        candidates = [(row.host, row.port) for row in selected.itertuples()]
    for host, port in candidates:
        subset = samples[(samples["host"] == host) & (samples["port"] == port)]
        if set(ALGORITHMS).issubset(set(subset["actual_algorithm_verified"].dropna())):
            return subset, (host, port)
    raise ValueError("No successful samples for all three algorithms on that destination")


def shared_limits(samples):
    """Use identical metric scales in all three PDFs for direct comparison."""
    limits = {"elapsed_s": (0, max(1.0, samples["elapsed_s"].max() * 1.02))}
    for metric, _, _ in METRICS:
        values = samples[metric].dropna()
        top = max(1.0, values.max() * 1.05) if not values.empty else 1.0
        limits[metric] = (0, top)
    return limits


def _style(ax, x_label, y_label, xlim, ylim):
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.grid(color="#e1e0d9", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def _page(pdf, samples, algorithm, destination, metric, label, unit, x_metric,
          x_label, axis_limits, scatter=False):
    fig, ax = plt.subplots(figsize=(8.5, 6))
    for index, (rep, group) in enumerate(samples.groupby("rep", sort=True)):
        color = COLORS[index % len(COLORS)]
        data = group.sort_values("elapsed_s")
        if scatter:
            ax.scatter(data[x_metric], data[metric], s=22, alpha=0.42,
                       color=color, label=f"run {rep}", edgecolors="none")
        else:
            ax.plot(data[x_metric], data[metric], linewidth=1.3, alpha=0.72,
                    color=color, label=f"run {rep}")
    _style(ax, x_label, unit, axis_limits[x_metric], axis_limits[metric])
    ax.legend(frameon=False, loc="best")
    host, port = destination
    fig.suptitle(f"{algorithm.upper()} | {host}:{port} | {label}", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    pdf.savefig(fig)
    plt.close(fig)


def plot_tcp_stats(samples, output_pdf, *, algorithm, destination, axis_limits):
    """Implement the Part 2 plot function header for Part 3: exactly seven pages."""
    data = samples[samples["actual_algorithm_verified"] == algorithm]
    if data.empty:
        raise ValueError(f"No successful samples for {algorithm}")
    with PdfPages(output_pdf) as pdf:
        for metric, label, unit in METRICS:
            _page(pdf, data, algorithm, destination, metric, label, unit,
                  "elapsed_s", "elapsed time (s)", axis_limits)
        for x_metric, x_label in (
            ("snd_cwnd", "snd_cwnd (segments)"),
            ("rtt_ms", "RTT (ms)"),
            ("retrans_interval", "retransmissions / interval"),
        ):
            _page(pdf, data, algorithm, destination, "goodput_mbps",
                  f"{x_label} vs goodput", "goodput (Mbps)", x_metric,
                  x_label, axis_limits, scatter=True)


def make_comparison_outputs(results_dir, plots_dir, destination=None):
    samples, chosen = load_representative(Path(results_dir), destination)
    limits = shared_limits(samples)
    plots_dir = Path(plots_dir)
    plots_dir.mkdir(parents=True, exist_ok=True)
    for algorithm in ALGORITHMS:
        output = plots_dir / f"part3_{algorithm}.pdf"
        plot_tcp_stats(samples, output, algorithm=algorithm, destination=chosen,
                       axis_limits=limits)
        print(f"Saved {output} (7 pages)")
    return chosen


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results-dir", type=Path, default=BASE / "results")
    ap.add_argument("--plots-dir", type=Path, default=BASE / "plots")
    ap.add_argument("--destination", help="representative HOST:PORT from collected runs")
    args = ap.parse_args()
    try:
        host, port = make_comparison_outputs(args.results_dir, args.plots_dir,
                                             args.destination)
    except (OSError, ValueError) as exc:
        ap.exit(1, f"{exc}\n")
    print(f"Representative destination: {host}:{port}")


if __name__ == "__main__":
    main()

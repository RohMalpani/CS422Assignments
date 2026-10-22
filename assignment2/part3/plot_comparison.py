"""Render three seven-page TCP comparison PDFs from saved Part 3 CSVs."""

import argparse
from pathlib import Path
import sys

import pandas as pd

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "part2"))
from plot_tcp_stats import plot_tcp_stats, shared_limits

ALGORITHMS = ("cubic", "reno", "bbr")


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
    samples["algorithm"] = samples["actual_algorithm_verified"]

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

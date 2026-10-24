"""Audit saved Option 1 data and render four-algorithm comparison plots.

This script only reads existing measurements; it never starts a TCP experiment.
It writes a seven-page comparison PDF, an aggregate-distribution PDF, and a
machine-readable analysis summary beside the raw CSVs.
"""

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
from statistics import mean, median, stdev

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


BASE = Path(__file__).resolve().parent
ALGORITHMS = ("cubic", "reno", "bbr", "cs422_custom")
LABELS = {"cubic": "CUBIC", "reno": "Reno", "bbr": "BBR",
          "cs422_custom": "Adaptive Delay/Loss AIMD"}
COLORS = {"cubic": "#2a78d6", "reno": "#eb6834", "bbr": "#8c5ec2",
          "cs422_custom": "#1baf7a"}
REP_COLORS = ("#2a78d6", "#eb6834", "#1baf7a")
METRICS = (
    ("snd_cwnd", "Congestion window", "cwnd (segments)"),
    ("rtt_ms", "RTT estimate", "RTT (ms)"),
    ("retrans_interval", "Retransmissions per interval", "new retransmissions"),
    ("goodput_mbps", "Acknowledged goodput", "goodput (Mbps)"),
)


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def destination_keys(config):
    """Use accepted host/port pairs, excluding failed candidate servers."""
    return {(host, int(port)) for host, port in config["destination_ports"].items()}


def run_key(row):
    return row["host"], int(row["port"]), int(row["rep"]), row["algorithm"]


def load_and_audit(results_dir):
    config = json.loads((results_dir / "run_config.json").read_text())
    raw_runs = read_csv(results_dir / "runs.csv")
    raw_samples = read_csv(results_dir / "samples.csv")
    selected = destination_keys(config)
    runs = [row for row in raw_runs if (row["host"], int(row["port"])) in selected]
    samples = [row for row in raw_samples if (row["host"], int(row["port"])) in selected]
    algorithms = tuple(config["args"]["algorithms"])
    if set(algorithms) != set(ALGORITHMS):
        raise ValueError(f"Expected four algorithms, found {algorithms}")
    if len(selected) != config["args"]["n"]:
        raise ValueError("Run did not select the requested number of destinations")
    # JSON preserves insertion order: the driver saved accepted destinations
    # in the order used for its cyclic algorithm rotation.
    selected_order = [(host, int(port)) for host, port in
                      config["destination_ports"].items()]
    destination_index = {key: index for index, key in enumerate(selected_order)}

    expected = {(host, port, rep, algorithm) for host, port in selected
                for rep in range(1, config["args"]["reps"] + 1)
                for algorithm in algorithms}
    run_keys = [run_key(row) for row in runs]
    if len(run_keys) != len(set(run_keys)) or set(run_keys) != expected:
        raise ValueError("Selected run keys are duplicated or incomplete")
    if [int(row["seq"]) for row in raw_runs] != list(range(1, len(raw_runs) + 1)):
        raise ValueError("Attempt sequence numbers are not consecutive")
    for row in runs:
        key = run_key(row)
        expected_algorithm = algorithms[(destination_index[key[:2]] + key[2] - 1 +
                                         int(row["order_pos"]) - 1) % len(algorithms)]
        if row["algorithm"] != expected_algorithm:
            raise ValueError(f"Requested/recorded algorithm mismatch in {key}")

    by_run = defaultdict(list)
    for row in samples:
        key = run_key(row)
        if key not in expected:
            raise ValueError(f"Unexpected sample key: {key}")
        by_run[key].append({
            "elapsed_s": float(row["elapsed_s"]),
            "interval_s": float(row["interval_s"]),
            "goodput_mbps": float(row["goodput_bps"]) / 1_000_000,
            "snd_cwnd": float(row["snd_cwnd"]),
            "rtt_ms": float(row["rtt_us"]) / 1_000,
            "retrans_interval": float(row["retrans_interval"]),
        })

    per_run = []
    for row in runs:
        key = run_key(row)
        points = sorted(by_run[key], key=lambda item: item["elapsed_s"])
        if row["status"] == "ok":
            if not points:
                raise ValueError(f"Successful run has no samples: {key}")
            if any(point["interval_s"] <= 0 or point["goodput_mbps"] < 0 or
                   point["rtt_ms"] < 0 or point["retrans_interval"] < 0
                   for point in points):
                raise ValueError(f"Invalid TCP sample in {key}")
            if any(right["elapsed_s"] <= left["elapsed_s"]
                   for left, right in zip(points, points[1:])):
                raise ValueError(f"Non-increasing sample time in {key}")
            per_run.append({
                "host": key[0], "port": key[1], "rep": key[2],
                "algorithm": key[3], "sample_count": len(points),
                "goodput_mbps": mean(p["goodput_mbps"] for p in points),
                "rtt_ms": mean(p["rtt_ms"] for p in points),
                "retransmissions": sum(p["retrans_interval"] for p in points),
            })
        elif points:
            raise ValueError(f"Failed run unexpectedly has saved samples: {key}")

    expected_samples = round(config["args"]["duration"] / config["args"]["interval"])
    status = Counter(row["status"] for row in runs)
    audit = {
        "raw_attempts": len(raw_runs),
        "rejected_candidate_attempts": len(raw_runs) - len(runs),
        "selected_destinations": len(selected),
        "selected_attempts": len(runs),
        "selected_successes": status["ok"],
        "selected_failures": status["failed"],
        "selected_samples": len(samples),
        "short_successful_traces": sum(r["sample_count"] < expected_samples for r in per_run),
        "expected_samples_per_run": expected_samples,
    }
    return config, selected, runs, by_run, per_run, audit


def choose_representative(selected, per_run, expected_per_destination, expected_samples):
    by_destination = defaultdict(list)
    for row in per_run:
        by_destination[(row["host"], row["port"])].append(row)
    pooled = {key: mean(row["goodput_mbps"] for row in rows)
              for key, rows in by_destination.items()}
    middle = median(pooled.values())
    candidates = [key for key in selected
                  if len(by_destination[key]) == expected_per_destination
                  and all(row["sample_count"] >= expected_samples
                          for row in by_destination[key])]
    if not candidates:
        raise ValueError("No destination has complete four-algorithm traces")
    return min(candidates, key=lambda key: (abs(pooled[key] - middle), key))


def aggregate(per_run):
    output = {}
    for algorithm in ALGORITHMS:
        rows = [row for row in per_run if row["algorithm"] == algorithm]
        gp = [row["goodput_mbps"] for row in rows]
        rtt = [row["rtt_ms"] for row in rows]
        ret = [row["retransmissions"] for row in rows]
        output[algorithm] = {
            "successful_runs": len(rows),
            "mean_goodput_mbps": mean(gp),
            "median_goodput_mbps": median(gp),
            "sd_goodput_mbps": stdev(gp) if len(gp) > 1 else 0,
            "mean_rtt_ms": mean(rtt),
            "median_rtt_ms": median(rtt),
            "sd_rtt_ms": stdev(rtt) if len(rtt) > 1 else 0,
            "mean_retransmissions_per_run": mean(ret),
        }
    return output


def axis_limits(points):
    limits = {}
    for metric in ("elapsed_s", "snd_cwnd", "rtt_ms", "retrans_interval", "goodput_mbps"):
        values = [point[metric] for point in points]
        top = max(values) if values else 1.0
        if metric == "rtt_ms":
            limits[metric] = (max(0, min(values) * 0.90), max(1, top * 1.10))
        elif metric == "retrans_interval":
            limits[metric] = (-max(0.05, top * 0.02), max(1, top * 1.06))
        else:
            limits[metric] = (0, max(1, top * 1.06))
    return limits


def plot_comparison(pdf_path, destination, by_run, repetitions):
    host, port = destination
    all_points = [point for algorithm in ALGORITHMS for rep in range(1, repetitions + 1)
                  for point in by_run[(host, port, rep, algorithm)]]
    limits = axis_limits(all_points)
    pages = [("elapsed_s", "Elapsed time (s)", metric, title, ylabel)
             for metric, title, ylabel in METRICS]
    pages += [(metric, xlabel, "goodput_mbps", f"Goodput vs {xlabel.lower()}",
               "goodput (Mbps)")
              for metric, xlabel in (("snd_cwnd", "cwnd (segments)"),
                                    ("rtt_ms", "RTT (ms)"),
                                    ("retrans_interval", "retransmissions / interval"))]
    with PdfPages(pdf_path) as pdf:
        for x_metric, xlabel, y_metric, title, ylabel in pages:
            scatter = x_metric != "elapsed_s"
            fig, axes = plt.subplots(2, 2, figsize=(11, 8.5), sharex=True, sharey=True)
            for ax, algorithm in zip(axes.flat, ALGORITHMS):
                for rep in range(1, repetitions + 1):
                    points = by_run[(host, port, rep, algorithm)]
                    if not points:
                        continue
                    color = REP_COLORS[(rep - 1) % len(REP_COLORS)]
                    x = [point[x_metric] for point in points]
                    y = [point[y_metric] for point in points]
                    if scatter:
                        ax.scatter(x, y, s=15, alpha=0.55, color=color,
                                   edgecolors="none", label=f"run {rep}")
                    else:
                        ax.plot(x, y, color=color, linewidth=1.35, alpha=0.85,
                                label=f"run {rep}")
                ax.set(title=LABELS[algorithm], xlim=limits[x_metric], ylim=limits[y_metric],
                       xlabel=xlabel, ylabel=ylabel)
                ax.grid(color="#e1e0d9", linewidth=0.6)
                ax.set_axisbelow(True)
                ax.spines[["top", "right"]].set_visible(False)
                ax.legend(frameon=False, fontsize=8)
            fig.suptitle(f"{title} | {host}:{port}", fontsize=15)
            if x_metric == "retrans_interval" or y_metric == "retrans_interval":
                fig.text(0.5, 0.012,
                         "Loss proxy: increase in TCP retransmissions during a sample interval.",
                         ha="center", fontsize=8)
            fig.tight_layout(rect=(0, 0.025, 1, 0.94))
            pdf.savefig(fig)
            plt.close(fig)


def plot_aggregates(pdf_path, per_run):
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.2), facecolor="#fcfcfb")
    for ax, metric, title, ylabel in (
        (axes[0], "goodput_mbps", "Acknowledged goodput", "per-run mean (Mbps)"),
        (axes[1], "rtt_ms", "TCP RTT estimate", "per-run mean (ms)"),
    ):
        groups = [[row[metric] for row in per_run if row["algorithm"] == algorithm]
                  for algorithm in ALGORITHMS]
        boxes = ax.boxplot(groups, patch_artist=True, showmeans=True,
                           meanprops={"marker": "o", "markerfacecolor": "black",
                                      "markeredgecolor": "black", "markersize": 4})
        for patch, algorithm in zip(boxes["boxes"], ALGORITHMS):
            patch.set_facecolor(COLORS[algorithm])
            patch.set_alpha(0.72)
        ax.set_xticks(range(1, len(ALGORITHMS) + 1),
                      ["CUBIC", "Reno", "BBR", "Custom"])
        ax.set(title=title, ylabel=ylabel, ylim=(0, None))
        ax.grid(axis="y", color="#e1e0d9", linewidth=0.6)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Successful selected runs across 10 destinations (30 each; Reno 29)", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(pdf_path)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=BASE / "results")
    parser.add_argument("--plots-dir", type=Path, default=BASE / "plots")
    parser.add_argument("--representative", help="override the selected HOST:PORT")
    args = parser.parse_args()
    config, selected, runs, by_run, per_run, audit = load_and_audit(args.results_dir)
    repetitions = config["args"]["reps"]
    representative = choose_representative(selected, per_run,
                                           repetitions * len(ALGORITHMS),
                                           audit["expected_samples_per_run"])
    if args.representative:
        host, separator, port = args.representative.rpartition(":")
        if not separator or not port.isdigit() or (host, int(port)) not in selected:
            parser.error("--representative must be a selected HOST:PORT")
        representative = host, int(port)
    if any(not by_run[(representative[0], representative[1], rep, algorithm)]
           for rep in range(1, repetitions + 1) for algorithm in ALGORITHMS):
        raise ValueError("Representative destination is missing a successful trace")

    args.plots_dir.mkdir(parents=True, exist_ok=True)
    comparison_pdf = args.plots_dir / "option1_comparison.pdf"
    aggregate_pdf = args.plots_dir / "aggregate_distributions.pdf"
    plot_comparison(comparison_pdf, representative, by_run, repetitions)
    plot_aggregates(aggregate_pdf, per_run)
    summary = {
        "source_run_id": config["run_id"],
        "method": "Arithmetic mean of interval goodput and RTT within each successful run; "
                  "then aggregate per-run means. Rejected candidate servers are excluded.",
        "audit": audit,
        "representative": {"host": representative[0], "port": representative[1],
                           "selection": "closest to median pooled destination goodput among "
                                        "destinations with complete four-algorithm traces"},
        "algorithms": aggregate(per_run),
    }
    (args.results_dir / "analysis_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Selected {len(selected)} destinations; {audit['selected_successes']}/"
          f"{audit['selected_attempts']} successful tests; {audit['short_successful_traces']} short traces")
    print(f"Representative destination: {representative[0]}:{representative[1]}")
    print(f"Saved {comparison_pdf}, {aggregate_pdf}, and analysis_summary.json")


if __name__ == "__main__":
    main()

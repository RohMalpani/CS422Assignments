# Generate per-destination goodput-over-time PDF plots and throughput summary tables.
import argparse
import math
import os

import matplotlib
matplotlib.use("Agg")  # file output only; never opens a window, so it runs unattended
import matplotlib.pyplot as plt
import pandas as pd

# Ink + categorical slots 1-3 from the validated reference palette (light surface). Repetitions
# take slots in fixed order; the first three are validated as distinguishable in every pairing.
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]


def load(samples_csv, runs_csv):
    samples = pd.read_csv(samples_csv)
    samples["goodput_mbps"] = samples["goodput_bps"] / 1e6
    runs = pd.read_csv(runs_csv)
    meta = runs[runs["status"] == "ok"].drop_duplicates(["host", "port"])[["host", "port", "site", "country"]]
    return samples.merge(meta, on=["host", "port"], how="left")


def plot_goodput(samples, out_pdf):
    """One panel per destination, goodput (Mbps) vs time, one line per repetition.

    Each panel has its own y-axis: destinations differ by 10-100x, so a shared axis would flatten
    the slow ones. (Cross-algorithm comparisons in part 3 will share axes instead.)
    """
    dests = sorted(samples.groupby(["host", "port"]).groups)
    ncols = 2 if len(dests) > 1 else 1
    nrows = math.ceil(len(dests) / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(5.8 * ncols, 2.7 * nrows), squeeze=False,
                             facecolor=SURFACE)
    flat = axes.flatten()
    reps = sorted(samples["rep"].unique())
    per_rep_color = len(reps) <= len(SERIES)  # more reps than slots: one hue, faint lines

    for ax, (host, port) in zip(flat, dests):
        d = samples[(samples["host"] == host) & (samples["port"] == port)]
        for i, rep in enumerate(reps):
            r = d[d["rep"] == rep]
            if r.empty:
                continue
            ax.plot(r["elapsed_s"], r["goodput_mbps"], lw=1.75, solid_capstyle="round",
                    color=SERIES[i] if per_rep_color else SERIES[0],
                    alpha=1.0 if per_rep_color else 0.5, label=f"rep {rep}")
        site = d["site"].iloc[0] if d["site"].notna().any() else ""
        ax.set_title(f"{site} - {host}:{port}  ({d['algorithm'].iloc[0]})", loc="left",
                     fontsize=9, color=INK)
        ax.set_facecolor(SURFACE)
        ax.set_ylim(bottom=0)
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(GRID)
        ax.tick_params(colors=MUTED, labelsize=8)
        ax.set_xlabel("time (s)", fontsize=8, color=INK2)
        ax.set_ylabel("goodput (Mbps)", fontsize=8, color=INK2)
    for ax in flat[len(dests):]:
        ax.axis("off")

    if len(reps) > 1 and per_rep_color:
        flat[0].legend(frameon=False, fontsize=8, labelcolor=INK2, loc="upper left")
    fig.suptitle("Goodput over time per destination (acknowledged bytes, TCP_INFO)",
                 fontsize=11, color=INK, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(out_pdf, facecolor=SURFACE)
    plt.close(fig)


def summary_table(samples):
    """min / median / mean / p95 goodput (Mbps) per destination and algorithm, over all samples."""
    g = samples.groupby(["site", "host", "port", "algorithm"], dropna=False)["goodput_mbps"]
    t = g.agg(samples="count", min="min", median="median", mean="mean",
              p95=lambda s: s.quantile(0.95)).reset_index()
    return t.round(2)


def write_summary(table, out_csv, out_tex):
    table.to_csv(out_csv, index=False)
    esc = lambda x: str(x).replace("_", r"\_")
    lines = [r"\begin{tabular}{llrrrrr}", r"\hline",
             r"Destination & Algorithm & Min & Median & Mean & P95 & N \\", r"\hline"]
    for r in table.itertuples():
        lines.append(f"{esc(r.site)} ({esc(r.host)}) & {esc(r.algorithm)} & {r.min:.2f} & "
                     f"{r.median:.2f} & {r.mean:.2f} & {r.p95:.2f} & {r.samples} \\\\")
    lines += [r"\hline", r"\end{tabular}"]
    with open(out_tex, "w") as f:
        f.write("\n".join(lines) + "\n")


def make_part1_outputs(results_dir, plots_dir):
    samples = load(os.path.join(results_dir, "part1_samples.csv"),
                   os.path.join(results_dir, "part1_runs.csv"))
    if samples.empty:
        print("no samples to plot")
        return
    os.makedirs(plots_dir, exist_ok=True)
    plot_goodput(samples, os.path.join(plots_dir, "part1_goodput.pdf"))
    table = summary_table(samples)
    write_summary(table, os.path.join(results_dir, "part1_summary.csv"),
                  os.path.join(results_dir, "part1_summary.tex"))
    print(table.to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Re-plot part 1 from saved CSVs.")
    ap.add_argument("--results-dir", default="results")
    ap.add_argument("--plots-dir", default="plots")
    a = ap.parse_args()
    make_part1_outputs(a.results_dir, a.plots_dir)

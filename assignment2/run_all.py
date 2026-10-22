# Run server selection, all TCP experiments, measurements, tables, and PDF plots from one entry point.
#
# Runs Part 1 measurements, Part 2 plots, and Part 3 comparison and plots.
# Linux / WSL2 only (TCP_INFO). Example:
#   python3 run_all.py --servers servers.csv -n 10 --duration 60
#   python3 run_all.py --replot-only          # regenerate plots/tables from saved CSVs
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "part1"))
import plot_goodput
import run_experiments
sys.path.insert(0, os.path.join(HERE, "part2"))
import plot_tcp_stats
sys.path.insert(0, os.path.join(HERE, "part3"))
import compare_algorithms
import plot_comparison


def record_host_environment(results_dir):
    """Save the Linux kernel and congestion-control settings used for the tests."""
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        f"UTC time: {datetime.now(timezone.utc).isoformat()}",
        f"Host Linux kernel: {platform.release()}",
    ]
    for label, name in (
        ("Available congestion controls", "tcp_available_congestion_control"),
        ("Allowed congestion controls", "tcp_allowed_congestion_control"),
        ("Default congestion control", "tcp_congestion_control"),
    ):
        value = (Path("/proc/sys/net/ipv4") / name).read_text().strip()
        lines.append(f"{label}: {value}")
    (results_dir / "host_environment.txt").write_text("\n".join(lines) + "\n")


def main():
    ap = run_experiments.build_parser()
    ap.add_argument("--plots-dir", default="plots")
    ap.add_argument("--representative", help="Part 2 destination as HOST:PORT (default: median-goodput destination)")
    ap.add_argument("--replot-only", action="store_true", help="skip measurements, redraw from saved CSVs")
    ap.add_argument("--part3-out-dir", type=Path, help="Part 3 CSV directory (default: OUT-DIR/part3)")
    ap.add_argument("--part3-reps", type=int, default=compare_algorithms.DEFAULT_REPS)
    ap.add_argument("--part3-cooldown", type=float, default=compare_algorithms.DEFAULT_COOLDOWN)
    ap.add_argument("--part3-destination", type=compare_algorithms.destination,
                    action="append", default=[], help="fixed HOST:PORT for Part 3; repeat as needed")
    ap.add_argument("--skip-part3", action="store_true", help="run or replot only Parts 1 and 2")
    args = ap.parse_args()
    if args.part3_reps < 2 or args.part3_cooldown < 0:
        ap.error("--part3-reps must be at least 2 and --part3-cooldown cannot be negative")
    part3_dir = args.part3_out_dir or Path(args.out_dir) / "part3"

    if not args.replot_only:
        if not sys.platform.startswith("linux"):
            sys.exit("This experiment needs Linux (TCP_INFO). Run it on Linux or inside WSL2.")
        if not args.skip_part3:
            compare_algorithms.check_algorithms()
        record_host_environment(args.out_dir)
        run_experiments.run_experiments(args)
    plot_goodput.make_part1_outputs(args.out_dir, args.plots_dir)
    plot_tcp_stats.make_part2_outputs(args.out_dir, args.plots_dir,
                                     algorithm=args.algorithm,
                                     destination=args.representative)
    if not args.skip_part3:
        if not args.replot_only:
            part3_args = argparse.Namespace(**vars(args))
            part3_args.destination = args.part3_destination
            part3_args.out_dir = part3_dir
            part3_args.reps = args.part3_reps
            part3_args.cooldown = args.part3_cooldown
            compare_algorithms.collect(part3_args)
        plot_comparison.make_comparison_outputs(part3_dir, args.plots_dir)


if __name__ == "__main__":
    main()

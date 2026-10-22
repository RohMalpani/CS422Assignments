# Run server selection, all TCP experiments, measurements, tables, and PDF plots from one entry point.
#
# Covers Part 1 goodput and Part 2 TCP-stat plots. Part 3 collection is separate.
# Linux / WSL2 only (TCP_INFO). Example:
#   python3 run_all.py --servers servers.csv -n 10 --duration 60
#   python3 run_all.py --replot-only          # regenerate plots/tables from saved CSVs
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "part1"))
import plot_goodput
import run_experiments
sys.path.insert(0, os.path.join(HERE, "part2"))
import plot_tcp_stats


def main():
    ap = run_experiments.build_parser()
    ap.add_argument("--plots-dir", default="plots")
    ap.add_argument("--representative", help="Part 2 destination as HOST:PORT (default: median-goodput destination)")
    ap.add_argument("--replot-only", action="store_true", help="skip measurements, redraw from saved CSVs")
    args = ap.parse_args()

    if not args.replot_only:
        if not sys.platform.startswith("linux"):
            sys.exit("This experiment needs Linux (TCP_INFO). Run it on Linux or inside WSL2.")
        run_experiments.run_experiments(args)
    plot_goodput.make_part1_outputs(args.out_dir, args.plots_dir)
    plot_tcp_stats.make_part2_outputs(args.out_dir, args.plots_dir,
                                     algorithm=args.algorithm,
                                     destination=args.representative)


if __name__ == "__main__":
    main()

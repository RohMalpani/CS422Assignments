# Assignment 3 — Option 1

Scaffold for the custom Linux TCP congestion-control module and its four-algorithm evaluation.

- `kernel/`: kernel module source and build file.
- `client/`: iperf3 client, TCP_INFO/goodput sampling, and server selection, copied unchanged from `assignment2/part1/` (see `DECISIONS.md`).
- `servers.csv`: iperf3 server list, copied from `assignment2/`.
- `run_experiments.py`: matched 10-second tests and raw measurements.
- `plot_results.py`: comparison plots and aggregate statistics.
- `results/`: raw data and run configuration.
- `plots/`: generated PDF figures.
- `report.tex`: final report source.

The kernel module and the experiment/plot scripts are placeholders until the algorithm design is agreed on.

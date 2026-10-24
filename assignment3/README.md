# Assignment 3 — Option 1

This folder contains the Adaptive Delay/Loss AIMD Linux TCP congestion-control
module, a matched four-algorithm iperf3 experiment, its raw data, plots, and
the final report source. The measured host was WSL2 with kernel
`6.6.87.2-microsoft-standard-WSL2` (`results/run_config.json`). Do not use
Assignment 2's 60-second data as a fourth-algorithm baseline: this run used
10 seconds for all four algorithms on the same host/port pairs.

## Files

- `kernel/tcp_cs422.c`, `kernel/Makefile`: module source and external-module build.
- `client/`: Python iperf3 protocol, data-socket TCP_INFO sampler, and server selection.
- `run_experiments.py`, `servers.csv`: four-algorithm experiment and candidate list.
- `results/runs.csv`, `results/samples.csv`: unfiltered raw attempts and samples.
- `results/run_config.json`, `results/run_log.txt`: original run settings and console log.
- `plot_results.py`, `requirements.txt`: offline audit and plotting dependencies.
- `results/analysis_summary.json`: derived counts and aggregate statistics.
- `plots/option1_comparison.pdf`: seven pages, each showing all four algorithms
  on the same representative destination with shared axes.
- `plots/aggregate_distributions.pdf`: per-run goodput and RTT distributions.
- `report.tex`, `report.pdf`: report source and Brightspace-ready PDF.

The original run selected 10 destinations, with three candidates replaced.
Across the selected destinations, 119 of 120 planned tests succeeded; the sole
failure was a Reno timeout in repetition 3. All successful tests have samples.
Seven successful traces have fewer than the expected ten intervals, and the
report explains how they affect interpretation. The custom algorithm completed
30 selected tests. The raw CSVs retain failed and rejected attempts.

## Kernel features and build

The running kernel must support loadable modules (`CONFIG_MODULES=y`) and the
Linux TCP congestion-control API. `CONFIG_MODVERSIONS=y` on the measured WSL2
kernel makes a matching `Module.symvers` necessary. The commands below also
require a readable `/proc/config.gz` (`CONFIG_IKCONFIG_PROC`) to copy the
running kernel's configuration. CUBIC, Reno, and BBR must be available; load BBR
with `sudo modprobe tcp_bbr` if necessary. A different kernel requires a fresh
build against its matching source/configuration or installed headers.

On the same `6.6.87.2-microsoft-standard-WSL2` kernel used for the saved run:

```sh
uname -r
sudo apt update
sudo apt install -y build-essential flex bison libssl-dev libelf-dev bc dwarves git python3 python3-venv
git clone --depth 1 -b linux-msft-wsl-6.6.87.2 https://github.com/microsoft/WSL2-Linux-Kernel.git ~/WSL2-Linux-Kernel
cd ~/WSL2-Linux-Kernel
zcat /proc/config.gz > .config
make olddefconfig
mv .git .git.saved  # Only in this disposable source clone; avoids an extra '+' in vermagic.
make -j"$(nproc)" modules  # Generates Module.symvers; this can take substantial time/disk.
cd <repo>/assignment3/kernel
make KDIR=~/WSL2-Linux-Kernel
modinfo -F vermagic tcp_cs422.ko
sudo modprobe tcp_bbr
sudo insmod tcp_cs422.ko
cat /proc/sys/net/ipv4/tcp_available_congestion_control
```

Replace `<repo>` with the checkout path. `modinfo -F vermagic` must match
`uname -r` at its start. The available list should include `cs422_custom`.
The group's WSL2 setup notes record a successful build, load, and socket
selection. A compiler/load transcript was not saved in the repo, so demonstrate
these steps live during grading. A WSL restart unloads the module. After all
custom-algorithm sockets close, `sudo rmmod tcp_cs422` removes it. The scripts
never change the system-wide default congestion control.

On a regular Ubuntu kernel with matching installed headers, replace the WSL
source build with `sudo apt install build-essential linux-headers-$(uname -r)`
and run `make` from `assignment3/kernel/`. This is an alternative build path,
not the environment that produced the committed measurements.

## Reproduce experiments and plots

From `assignment3/` on the compatible Linux host, after loading the module:

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 run_experiments.py --servers servers.csv -n 10 --duration 10 --interval 1 \
  --reps 3 --algorithms cubic reno bbr cs422_custom --pause 3 \
  --max-failures 10 --seed 422 --out-dir results/reproduction
python3 plot_results.py --results-dir results/reproduction --plots-dir plots/reproduction
```

This takes at least 20 minutes of transfer time plus pauses and any failed
candidate attempts. It writes to new folders and does not overwrite the
submitted raw measurements. Plotting alone can run on macOS, Windows, or Linux
with Python and Matplotlib; it does not run any network tests:

```sh
python3 plot_results.py --results-dir results --plots-dir plots
```

For a grading demo, show `uname -r`, rebuild the module with the matching
kernel tree, load it, show `cs422_custom` in the available list, and verify a
Python data socket can select and read back `TCP_CONGESTION=cs422_custom` before
connecting. The saved `runs.csv` and `samples.csv` then show the full matched
evaluation. See `report.pdf` for methods, figures, results, caveats, and code links.

To regenerate the submission PDF after plotting, install Tectonic 0.17 or a
TeX distribution with `geometry`, `graphicx`, `booktabs`, and `hyperref`, then
run `tectonic report.tex` from this directory. The report embeds the PDFs in
`plots/`, so regenerate those first if the raw data change.

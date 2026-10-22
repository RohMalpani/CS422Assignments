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

The kernel module implements the Adaptive Delay/Loss AIMD design documented in
`../assignment2/part3/custom_congestion_control.md`. The experiment and plot
scripts remain placeholders.

On an Ubuntu host with matching kernel headers, `make` and a C compiler:

```sh
cd kernel
make
sudo insmod tcp_cs422.ko
cat /proc/sys/net/ipv4/tcp_available_congestion_control
```

The available-algorithm list should include `cs422_custom`. Select it with
`TCP_CONGESTION` on the Python client's data socket before `connect()`, then
read `TCP_CONGESTION` back to record the algorithm actually used. Unload after
all custom-algorithm sockets close with `sudo rmmod tcp_cs422`. Do not change
the system-wide default congestion-control algorithm.

### WSL2 (Windows)

WSL2 has no kernel headers, so build them from Microsoft's matching source
(replace the tag with `uname -r`'s version; see `DECISIONS.md` for why):

```sh
sudo apt install build-essential flex bison libssl-dev libelf-dev bc dwarves iperf3 git
git clone --depth 1 -b linux-msft-wsl-6.6.87.2 https://github.com/microsoft/WSL2-Linux-Kernel.git ~/WSL2-Linux-Kernel
cd ~/WSL2-Linux-Kernel
zcat /proc/config.gz > .config && make olddefconfig
rm -rf .git            # otherwise vermagic gets a "+" suffix and insmod rejects the module
make -j$(nproc) modules   # slow; produces Module.symvers
cd <repo>/assignment3/kernel && make KDIR=~/WSL2-Linux-Kernel
```

Built and loaded successfully this way on `6.6.87.2-microsoft-standard-WSL2`.
Modules do not survive a WSL restart; run `insmod` again.

The module source was written for the Ubuntu VM's Linux `6.8.0-147-generic`
headers. Rebuild it for the exact kernel used during evaluation; compilation
and runtime behavior have not yet been verified.

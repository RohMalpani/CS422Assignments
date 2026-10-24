# Decisions

Record algorithm, implementation, measurement, and evaluation decisions here with brief rationales.

## Structure

- **No `part1/` folder.** Option 1 is a single deliverable, not a sequence of parts, so a `part1/` folder would be misleading and add a path level. This departs from the per-part subfolder convention in CLAUDE.md on purpose.
- **`kernel/` is separate from the Python code.** It has a different build system (C, kernel headers, `make`, `insmod`) and the handout says graders review it on its own.
- **`client/` holds code copied from A2 part 1** (`iperf3_client.py`, `goodput.py`, `select_servers.py`), unchanged, so "what changed from A2?" has a clear answer: nothing in `client/`. It already selects the congestion algorithm on the data socket before `connect()` and reads back the one actually in use, which is what A3 requires.

## Reuse from Assignment 2

- **Copy, don't import.** Each assignment folder stays self-contained, and a later edit in `assignment2/` (owned partly by teammates) can't silently break A3.
- **Do not reuse A2's CUBIC/Reno/BBR measurements.** A3 requires the same destinations, duration (10 s) and sampling interval for all four algorithms; A2 used 60 s runs, and public-Internet conditions drift over days. All four algorithms are re-measured together, with test order rotated.

## 2026-10-22 — Adaptive Delay/Loss AIMD kernel module

Use ACK-derived delivery rate, minimum RTT, smoothed RTT, and TCP loss events
to control `cwnd`. Low-delay growth is Reno-like, with a short two-segment
probe only when delivery improves. Congestive loss halves `cwnd`; isolated loss
with stable delivery uses a milder 15% reduction. This tests whether a
bandwidth-aware loss response improves goodput without BBR's observed RTT
inflation on several paths. The thresholds are provisional and must be tested
against all three baselines; no performance improvement is assumed.

The implementation registers `cs422_custom` through Linux
`tcp_congestion_ops`. Keeping TCP's built-in retransmission and recovery
mechanisms makes the module smaller and easier to audit. The Ubuntu VM runs
kernel `6.8.0-147-generic`; build and runtime verification are still needed.

## 2026-10-22 — Building and loading on WSL2

- **Build on WSL2 against Microsoft's kernel source, not Docker.** A module must match the running kernel's exact version and symbol checksums (`CONFIG_MODVERSIONS=y`). Containers share the host kernel, so Docker would not remove this requirement.
- **Matching tag `linux-msft-wsl-6.6.87.2`.** WSL ships no kernel headers, and Ubuntu's header packages don't match Microsoft's kernel. Config comes from `/proc/config.gz` so it matches the running kernel.
- **Full `make modules` once.** This generates `Module.symvers`, which `modpost` needs to attach symbol versions. `modules_prepare` alone doesn't produce it.
- **Moved `.git` out of the kernel tree.** The shallow clone made `setlocalversion` append `+`, giving vermagic `...WSL2+`, which `insmod` rejects against `uname -r`.
- **`.ko` files are not committed.** They are tied to one kernel and architecture; `.gitignore` excludes them and each person builds their own.
- **Verified:** compiles without errors, loads with `insmod`, appears in `tcp_available_congestion_control`, and a socket accepts `TCP_CONGESTION=cs422_custom`. Performance is not yet measured.

## 2026-10-22 — Experiment driver (`run_experiments.py`)

- **Adapted from A2's driver, not rewritten.** Same server selection with bounded replacement, same per-sample CSV rows, so the A2 plotting and its explanations carry over. Changes: 10 s default, several algorithms per destination, test-order columns, config file.
- **Every algorithm on the same destination, back to back.** The handout requires identical destinations, duration and sampling interval. Running all four in a row on one path minimizes drift in network conditions between them (A2 measured days apart).
- **Rotated test order** (cyclic shift by destination index + repetition). Without this, the algorithm that always runs first or last could be systematically helped or hurt by server load or cache/queue state. `order_pos` and `seq` are logged so the order can be reported.
- **Destination counts only if all four algorithms succeed in rep 1**; otherwise it is replaced (bounded). Keeps the four-way comparison on identical destinations. Failures in later reps are logged but not replaced, and reported.
- **Host and port fixed per destination** (the same `Server` object is reused), so all algorithms and repetitions share an endpoint.
- **A run is only "ok" if the socket reports the requested algorithm** (`getsockopt` read-back), guarding against silently measuring the default.
- **Fail fast if an algorithm is unavailable.** WSL drops loaded modules when it restarts, which previously produced a run of misleading "No such file" failures.
- **3 s pause between tests** so one test's queues/retransmits don't bleed into the next.
- **Default 3 repetitions.** Single runs showed about 15 Mbps variation on one path, so one run per algorithm can't separate algorithms.

## 2026-10-22 — Full run results (`results/`)

- **Config:** 10 destinations x 3 reps x 4 algorithms, 10 s, 1 s sampling, seed 422, kernel 6.6.87.2-microsoft-standard-WSL2 (WSL2 NAT in the path). Test order and sequence are in `runs.csv` (`order_pos`, `seq`).
- **Outcome:** 120 planned tests on 10 selected destinations, of which 119 succeeded. Three candidate destinations were replaced (servers busy: `ACCESS_DENIED`, or refused). The one selected-test gap is `speed1.fiberby.dk` rep 3 `reno`, which timed out; Reno has 29 successful tests versus 30 for each other algorithm.
- **Analysis must filter to the destinations in `run_config.json`.** `speedtest.iway.ch` was rejected after one test succeeded (the others hit `ACCESS_DENIED`), so its partial rows remain in the raw CSVs but are not one of the 10 chosen destinations.
- **Raw files kept unfiltered** so the failed attempts stay auditable; `run_log.txt` is the console log.
- **Trace coverage:** all 119 successful selected tests have TCP_INFO samples, but seven have fewer than the expected ten sampling intervals. This is disclosed in the report rather than silently dropping or treating them as complete ten-second traces.

# Decisions Log — Assignment 2

Format per entry: Context / Decision / Why / Code (see `assignment1/DECISIONS.md`).

## 2026-10-16 — Server list source and format
**Context:** Part 1(b) needs a list of public iperf3 servers.
**Decision:** Download the CSV export from `https://export.iperf3serverlist.net/listed_iperf3_servers.csv` into `assignment2/servers.csv` and read it directly, same columns as `assignment1/ips.csv`.
**Why:** The site is JS-rendered (no scrapable HTML); the export is the official machine-readable list. The handout says the entry script takes a server-list file, so a plain CSV file is the input.
**Code:** `part1/select_servers.py: load_servers`

## 2026-10-16 — Port ranges: pick one random port per server
**Context:** Most rows have a range (`5201-5210`), not a single port.
**Decision:** Expand the range and pick one port at random when a server is handed out.
**Why:** Public servers run one test per listener, so a range means "any of these ports may be free". Random choice spreads load and avoids everyone hammering 5201. Simpler than probing all ports.
**Code:** `part1/select_servers.py: parse_ports, ServerPool.next_server`

## 2026-10-16 — Replacement strategy: shuffle once, pop from the end
**Context:** Part 1(b): on rejection/rate-limit, log and try a replacement, with bounded attempts.
**Decision:** `ServerPool` shuffles all servers once; `next_server()` pops one each call (initial n and replacements use the same call). The attempt bound lives in the caller, not the pool.
**Why:** One shuffle = uniform sample without replacement, so a replacement can never be a host we already tried. Keeping the bound in the caller keeps the pool trivial to explain. `--seed` makes runs reproducible for debugging.
**Code:** `part1/select_servers.py: ServerPool`

## 2026-10-17 — Target WSL2/Linux; pure-Python iperf3 client
**Context:** Handout requires Linux/WSL2 (TCP_INFO is Linux-only); we have WSL2 Ubuntu 22.04 (kernel 6.6, Python 3.10).
**Decision:** Code and test inside WSL2, standard library only for the client. No Windows/mac fallbacks.
**Why:** Fallbacks would be code nobody can validate against the graded environment. WSL kernel currently offers only reno+cubic; BBR needs loading for part 3.
**Code:** `part1/iperf3_client.py`

## 2026-10-17 — iperf3 protocol implemented from the source's state machine
**Context:** Part 1(a): speak iperf3 ourselves, no iperf3 binary.
**Decision:** Client-sends TCP test, 1 stream, in order: cookie -> PARAM_EXCHANGE JSON -> CREATE_STREAMS (open data socket, send cookie) -> TEST_START/RUNNING -> send zeros -> TEST_END -> EXCHANGE_RESULTS (both JSON) -> DISPLAY_RESULTS -> IPERF_DONE. States are 1 signed byte; JSON has a 4-byte big-endian length prefix.
**Why:** Matches iperf3's `iperf_api.h` state machine; verified against real public servers (server's reported byte count matched ours within in-flight data).
**Code:** `part1/iperf3_client.py: run_test`

## 2026-10-17 — Error handling: two exception types, bounded by timeouts
**Context:** Handle busy servers, timeouts, premature termination.
**Decision:** `ServerRejected` (ACCESS_DENIED/SERVER_ERROR state) and `Iperf3Error` (everything else: connect fail, timeout, reset, EOF, SERVER_TERMINATE, unexpected state). Connect timeout 5s, read/write timeout 10s. Caller catches `Iperf3Error` and asks the pool for a replacement.
**Why:** The caller only needs "this server failed, log why, try another"; one base class makes that a single except clause. Busy servers are common (saw ACCESS_DENIED in testing).
**Code:** `part1/iperf3_client.py: _recv_state, run_test`

## 2026-10-17 — Congestion algorithm set via TCP_CONGESTION before connect(); sampling via callback
**Context:** Part 3 needs a per-socket algorithm; part 1(c) needs stats from the data socket mid-transfer.
**Decision:** `run_test(congestion=...)` sets `TCP_CONGESTION` on the data socket before `connect()`. `on_sample(data_sock, elapsed)` is called every `sample_interval` from the send loop; goodput.py will supply it.
**Why:** Set before connect so the algorithm governs the whole flow. A callback keeps the client ignorant of stats/plotting. Sampling inside the send loop avoids threads (simpler to explain); data.send() returns often since socket timeouts are bounded.
**Code:** `part1/iperf3_client.py: run_test, _send_data`

## 2026-10-17 — Goodput must use acked bytes, not bytes sent
**Context:** Test runs showed bytes sent (13.7MB) > bytes server received (12.6MB) in a 5s run.
**Decision:** Part 1(c) goodput will use `tcpi_bytes_acked` from TCP_INFO, not our own send() counter.
**Why:** send() returns when data is copied to the kernel buffer, not when the peer has it; the gap is unacked/in-flight data. The handout explicitly asks for acknowledged bytes.

## 2026-10-17 — Decode TCP_INFO with a field table, verified against C offsetof()
**Context:** Part 1(c)/2(a) need bytes_acked, snd_cwnd, rtt, retransmits from `getsockopt(TCP_INFO)`.
**Decision:** One ordered `(name, format)` list mirroring `struct tcp_info` in `linux/tcp.h`; `read_tcp_info` unpacks field by field and stops when the kernel's returned length runs out. Requests a 256-byte buffer.
**Why:** A field list is easier to explain/extend than a hand-counted giant format string, and degrades gracefully on older kernels with shorter structs. Verified every field offset against a compiled C `offsetof()` in WSL (0 mismatches); the kernel struct is 232 B, we decode the first 224 (the rest are fields we don't use).
**Code:** `part1/goodput.py: _TCP_INFO_FIELDS, read_tcp_info`

## 2026-10-17 — Goodput uses real elapsed time between samples
**Context:** The send loop only checks the clock after `send()` returns, so samples land 0.85–1.14s apart for a nominal 1s interval.
**Decision:** goodput = Δbytes_acked / (actual Δelapsed) × 8, not Δbytes / nominal interval. Each row stores `interval_s`.
**Why:** The handout says to divide by actual elapsed sampling time. Using the nominal interval would bias each point by up to ~15%.
**Code:** `part1/goodput.py: GoodputSampler.__call__`

## 2026-10-17 — Loss proxy = new retransmits per interval
**Context:** Part 2 needs a loss signal; tcp_info has `retransmits`, `lost`, `total_retrans`.
**Decision:** Log cumulative `total_retrans` and `lost`, and derive `retrans_interval` (delta of total_retrans) as the primary loss proxy.
**Why:** `total_retrans` is monotonic so deltas are well-defined; `retransmits` resets on recovery and `lost` is an instantaneous estimate. Retransmits include spurious ones, so it is a proxy, not true loss — say so in the report.
**Code:** `part1/goodput.py: GoodputSampler.__call__`

## 2026-10-17 — Driver: first repetition doubles as server selection
**Context:** Part 1(b) wants n servers with bounded replacement; part 3 wants repeated runs on the *same* destinations.
**Decision:** In repetition 1, a server that fails is replaced by the next pool entry until n succeed or `--max-failures` (default 10) is hit. Repetitions 2+ reuse the n chosen servers; failures there are logged but not replaced. Shortfall is printed if fewer than n succeeded.
**Why:** Replacing in later reps would change the paths being compared. Reusing selection-run data (not discarding it) avoids wasting 60s tests on public servers that rate-limit. Bound = total failed attempts, simplest to state and explain.
**Code:** `part1/run_experiments.py: run_experiments`

## 2026-10-17 — Output: long-format CSV, flushed after every test
**Context:** Handout wants stored measurements with units, destination, algorithm, run id.
**Decision:** `part1_samples.csv` (one row per sample, units in column names: `_bps`, `_us`, `_Bps`) and `part1_runs.csv` (one row per attempt incl. failures, error text, bytes sent vs server-reported). Files are flushed after each test.
**Why:** Long format loads straight into pandas/groupby for plots and tables. Keeping failed attempts in the runs file documents rate-limiting for the report. Flushing means Ctrl+C or a crash mid-run loses at most one test (60s runs x 10 servers is 10+ min).
**Code:** `part1/run_experiments.py: run_one`

## 2026-10-17 — Record the algorithm the kernel reports, not the one requested
**Context:** Handout: "record the algorithm actually used."
**Decision:** After connect, read `TCP_CONGESTION` back from the data socket and store that string; `iperf3_client.run_test` returns it as `congestion`.
**Why:** If the request fails or is unset, the OS default is used; reading back is the only way to be sure. Test confirmed default on WSL2 = `cubic`.
**Code:** `part1/iperf3_client.py: run_test`

## 2026-10-17 — Plots: one panel per destination, independent y-axes, one line per repetition
**Context:** Part 1(c) asks for throughput over time for all destinations (separate panels fine).
**Decision:** Small-multiples grid (2 columns), goodput in Mbps vs time, one line per repetition (palette slots 1-3 in fixed order; more than 3 reps -> one hue, faint). Each panel has its own y-axis; legend only on the first panel.
**Why:** Destinations differ 10-100x in goodput (0.7 to 400 Mbps in test), so a shared axis flattens the slow ones. Panels avoid dual axes. Part 3's cross-algorithm plots will use shared axes because the handout asks for consistent scales there.
**Code:** `part1/plot_goodput.py: plot_goodput`

## 2026-10-17 — Matplotlib 'Agg' backend, PDF output, no plt.show()
**Context:** Handout needs PDF plots generated fully automatically; assignment 1 had a blocking `plt.show()` problem.
**Decision:** `matplotlib.use("Agg")`, `fig.savefig(...pdf)` only.
**Why:** Agg never opens a window, so it works headless in WSL/Docker and in one-shot runs.
**Code:** `part1/plot_goodput.py`

## 2026-10-17 — Summary table pools all samples per (destination, algorithm)
**Context:** Handout wants min/median/mean/p95 per destination and algorithm.
**Decision:** Pool every interval sample across repetitions (including the slow-start first seconds); p95 = pandas linear-interpolated quantile. Written as CSV and as a LaTeX `tabular` for `report.tex`.
**Why:** Per-sample statistics are what "throughput over time" summarises; dropping slow-start would hide real behaviour. Because repetitions on one path differ hugely (e.g. Frankfurt 179 vs 17 Mbps mean), the report should also mention per-rep variation. Units: Mbps.
**Code:** `part1/plot_goodput.py: summary_table, write_summary`

## 2026-10-17 — Single entry point `run_all.py`; Linux guard; venv for dependencies
**Context:** Handout: one entry script taking a server list + options; must run on Linux/WSL2.
**Decision:** `run_all.py` reuses `run_experiments.build_parser()` plus `--plots-dir` and `--replot-only`; exits with a clear message on non-Linux. Python deps (matplotlib/pandas/numpy) installed in a venv (`~/cs422venv` in WSL) because WSL had no pip/pandas.
**Why:** One parser means CLI options can't drift between the driver and the entry script. `--replot-only` lets us tweak plots without re-running 10+ minutes of tests on public servers. A venv avoids sudo/system-wide installs.
**Code:** `run_all.py`, `requirements.txt`

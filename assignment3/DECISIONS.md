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

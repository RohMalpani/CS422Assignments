# Decisions Log

This is the "why" record for this repo. Every notable design decision — a
library/API choice, an algorithm, a data source, a parameter or buffer-size
choice, etc. — gets a short entry here as it's made, not retroactively.

This exists because grading is an oral exam: any group member can be asked
"why did you implement it this way," and the answer needs to be something a
person actually decided and can defend, not just "the AI wrote it that way."
The `exam-prep` skill reads this file to build its walkthroughs.

## Format

```
## YYYY-MM-DD — <short decision title>
**Context:** what problem/step this was part of
**Decision:** what was chosen
**Why:** rationale / alternatives considered
**Code:** file/function pointer
```

## Log

## 2026-09-03 — Traceroute tool & invocation
**Context:** Part 2 needs traceroute against 5 targets; group is on mixed OSes.
**Decision:** Use system `traceroute` (installed via WSL Ubuntu-22.04 on Windows
machines); script detects `platform.system()` and prefixes the command with
`wsl -d Ubuntu-22.04 --` on Windows, calls `traceroute` directly otherwise.
Flags: `-I -n -q 3 -w 2` (ICMP echo probes, numeric output, 3 probes/hop,
2s per-probe timeout).
**Why:** Native Linux `traceroute` has more standard, predictable output than
Windows `tracert`; the platform check lets one script run unmodified for every
group member regardless of OS, instead of maintaining OS-specific versions.
`-I` was added after testing: default UDP-mode traceroute reported 3 of our
first 5 randomly-selected targets as unreachable, but plain `ping` showed all
3 were actually alive — they (or something in the path) silently drop the
"port unreachable" ICMP reply UDP traceroute depends on, while still
answering ICMP echo normally. Switching to `-I` (ICMP probes, same mechanism
as ping) fixed all 3. Ran without root -- the `traceroute` binary already has
`CAP_NET_RAW`, no sudo needed for `-I` in our setup.
**Code:** part2/traceroute_runner.py — `_build_command()`

## 2026-09-03 — Per-hop RTT aggregation
**Context:** traceroute sends 3 probes per hop; need one RTT value per hop.
**Decision:** Use the minimum of the responsive probes at each hop.
**Why:** Min approximates the hop's propagation+processing floor and is less
skewed by transient queuing delay/jitter than the average; standard choice in
latency measurement. A hop with all 3 probes as `*` has no RTT value (still
counted toward hop count, excluded from per-hop RTT data).
**Code:** part2/traceroute_runner.py — `hop_min_rtt()`

## 2026-09-03 — Stacked bar chart: incremental, not cumulative
**Context:** traceroute reports cumulative RTT to each hop from the source.
**Decision:** Plot each hop's *incremental* contribution,
`max(0, RTT_i - RTT_{i-1})`, not the raw cumulative RTT.
**Why:** Raw cumulative values stacked would make later hops visually dwarf
earlier ones by construction, not because they're actually slower -- it
wouldn't represent a real "breakdown." Clamped at 0 because each hop's RTT is
an independent measurement (separate probes), so jitter can occasionally make
hop i's value come in lower than hop i-1's even though the path only grows.
**Code:** part2/plotting.py (pending)

## 2026-09-03 — Non-responsive destination handling
**Context:** Some of the 5 randomly picked targets may never complete a
traceroute (destination itself doesn't respond).
**Decision:** Skip and log such destinations; do not auto-draw a replacement.
Report may end up with fewer than 5 destinations if this happens.
**Why:** Matches the assignment's explicit note that skipping non-responsive
servers is acceptable; avoids silently changing what "5 random targets" means
by re-sampling until success.
**Code:** part2/traceroute_runner.py — `run_traceroute()` (`.reached` field)

## 2026-09-03 — Plots write directly to the report's figures/ directory
**Context:** A teammate's `report.tex` expects plots at root-level
`figures/hop_latency_breakdown.pdf` and `figures/hop_count_vs_rtt.pdf`.
**Decision:** `part2/run.py` and `part2/plotting.py` now write PDFs directly
to `../figures` / `figures` (repo root) with those exact filenames, instead
of a separate `part2/results/` directory.
**Why:** Avoids keeping two copies of the same plots that can silently drift
out of sync (e.g. regenerating in `part2/results/` without remembering to
re-copy into `figures/`); the report always reads whatever the script most
recently produced.
**Code:** part2/run.py, part2/plotting.py

## 2026-09-03 — Reconciling with a teammate's Part 1 push
**Context:** A groupmate pushed Part 1 work (`ping.sh` + `scatter.py`) directly
while Part 2 was in progress. Two conflicts surfaced: they renamed the server
list CSV to `ips.csv` while we'd separately renamed our copy to `servers.csv`
(same data, two names); and their scripts sat flat at repo root while `part2/`
was already its own subfolder.
**Decision:** Keep `ips.csv` (drop `servers.csv`, since `ping.sh` already
depended on that name); move `ping.sh`/`scatter.py` into a new `part1/`
folder to match the `part1/`/`part2/` convention, adding `cd
"$(dirname "$0")"` to `ping.sh` and a relative `../ips.csv` reference so it
still works from its new location.
**Why:** Conform to whatever's already shared/merged rather than forcing a
rename onto a teammate's already-pushed, working script; keep one consistent
per-assignment-part folder structure going forward instead of a mixed
flat/subfoldered layout.
**Code:** part1/ping.sh, part2/select_targets.py, part2/batch_traceroute.py,
part2/run.py (all default CSV paths updated to `ips.csv`)

## 2026-09-03 — Retry once before marking a destination non-responsive
**Context:** Running traceroute against 5 targets back-to-back, 2 of them
failed to reach the destination in one batch run, then succeeded on both a
standalone rerun and a full batch rerun immediately after.
**Decision:** Retry a target once (2 attempts total) before counting it as
skipped/non-responsive.
**Why:** A single failed attempt was shown (empirically, via rerun) to not
reliably indicate a dead destination -- likely transient contention from
spawning traceroute processes in quick succession. Retrying once avoids
dropping a real data point from a 5-target sample due to a one-off glitch,
while still respecting the "skip if genuinely non-responsive" policy (an
actually-dead target will fail both attempts).
**Code:** part2/batch_traceroute.py — `run_batch()`, `MAX_ATTEMPTS`

## 2026-09-03 — Target selection: seeded random, not hardcoded
**Context:** Part 2a asks for "5 random ip addresses" from the server list.
**Decision:** Script randomly selects 5 targets from the full input CSV using
a fixed seed (42, arbitrary), via a dedicated `random.Random(seed)` instance
rather than the global `random` module.
**Why:** Hardcoding 5 IPs directly would mean the "random selection" step
happens outside the automated script, undermining the assignment's
fully-automated/re-runnable requirement. A seeded RNG keeps it genuinely
random while staying reproducible across reruns. A dedicated RNG instance
(not global `random.seed`) avoids other code paths' random calls affecting
this selection's reproducibility.
**Code:** part2/select_targets.py — `pick_targets()`

# CS 422: Computer Networks (Fall 2026) — Group Repo

## Course context

Four assignments span the semester, each building on the last:

1. **Network latencies** (this repo, `assignment-1.pdf`) — ping + traceroute
   against the iperf3 server list, RTT/distance analysis.
2. **Custom TCP socket + congestion control** — hand-write a Python socket
   client against iperf3 servers, measure throughput/cwnd/RTT under CUBIC,
   RENO, and BBR, then design a hand-written algorithm that switches between
   them based on live network conditions.
3. **Kernel module/eBPF (bonus) or NS-3 (no bonus)** — implement the
   assignment-2 algorithm either as a real kernel module/eBPF program, or
   inside NS-3's TCP/IP stack on a leaf-spine topology, and compare flow
   completion times against CUBIC/RENO/BBR.
4. **Distributed collectives over pytorch gloo** — reduce-scatter (ring,
   recursive doubling, swing) and broadcast (binary tree, binomial tree)
   across the group's own machines, with a bonus for a real LAN ring setup.

**Grading**: 5% participation, 45% assignments, 20% midterm, 30% final.
**Late policy**: 72hr grace period per assignment, then -25% per 24hrs late.

### Evaluation model — read this carefully

Assignments are graded via **oral exam** during PSO/office hours. Any group
member can be asked to explain *any* line of code and, critically, **why it
was implemented that way**. There are no lectures on the frameworks involved —
this is meant to be self-directed learning, with AI as a tool, not a
substitute for understanding.

### AI policy (course-stated)

- Full, unrestricted use of AI tools is allowed unless an assignment says
  otherwise.
- You are responsible for fully understanding, validating, and being able to
  explain any AI-produced code, design choice, or analysis.
- Submissions that rely on AI-generated content the student can't explain may
  receive **reduced credit** — even if the code is correct.
- A brief AI-usage acknowledgment statement is required in each submission
  (how AI was used — debugging, boilerplate, conceptual guidance, etc.). No
  penalty for using AI; the acknowledgment itself is the requirement.

## Group

3 people. Get current contributors from git history rather than trusting a
hardcoded list here (names/emails below will go stale):

```
git log --format='%an <%ae>' | sort -u
```

Members may keep **separate versions** of a given assignment rather than one
shared solution — don't assume a single canonical implementation across the
group. When working on someone's branch/version, these instructions still
apply to whoever is in the room.

## Working style — how Claude should operate in this repo

The point of this repo is not just working code — it's code **every group
member can defend live, unscripted, in front of a TA**. That changes the
default way to work here:

1. **Do not one-shot assignment solutions.** Build incrementally, in logical
   steps (e.g. "ping script", "geolocation lookup", "plotting" — not
   per-function, not the whole assignment in one pass).
2. **Pause after each step** and explain in plain terms: what was just built,
   why this approach/library/algorithm was chosen over the alternatives, and
   any tradeoffs — before moving to the next step. This holds even when it
   feels slower than just finishing.
3. **Log every notable decision** to `DECISIONS.md` (library/API choice,
   algorithm, data source, parameter or buffer-size choice, etc.) with a
   one-line rationale as you go. This is the material both the `exam-prep`
   skill and the student draw on later — an undocumented decision is one
   nobody can explain under questioning.
4. **Prefer simple, explainable approaches over clever ones** when both work.
   Cleverness that only the AI understands is a liability here, not an asset.
5. **Keep the AI-usage acknowledgment current** (e.g. in the report or an
   `AI_USAGE.md`) — required by the course policy, separate from the internal
   `DECISIONS.md` log.

Use the `exam-prep` skill (`.claude/skills/exam-prep/`) to do a guided
walkthrough of an assignment's code + rationale ahead of the oral exam.

## Repo conventions

- Input data (`ips.csv`, the iperf3 server list) lives at repo root, shared
  by both parts.
- Each assignment part gets its own subfolder (`part1/`, `part2/`, ...) with
  its own scripts/outputs, rather than everything flat at repo root.
- Assignment 1 deliverables (per `assignment-1.pdf`): a single automated
  script per part (input = IP list file) that runs ping/traceroute, handles
  non-responsive hosts/hops, and generates all PDF plots in one shot; a
  report linking to the relevant code sections for each plot/finding.
- **Part 1** (`part1/`): `ping.sh` (ping test + geolocation via ip-api.com,
  writes `results.csv`) then `scatter.py` (distance vs RTT scatter). Note:
  currently saves a PNG (`figures/scatter_plot.png`) and calls a blocking
  `plt.show()` before `plt.savefig()` — worth revisiting for the "PDF plots,
  fully automated" requirement.
- **Part 2** (`part2/`): `run.py` is the one-shot entry point (select targets
  → traceroute → plots). Individual steps (`select_targets.py`,
  `traceroute_runner.py`, `batch_traceroute.py`, `plotting.py`) are also
  runnable standalone for testing/debugging.

# Oral-exam prep: why de Bruijn is near-optimal for large n

**Not in the report on purpose.** This is backup for the exam question
"if de Bruijn isn't optimal, why is it the best answer?"

## One-line answer

No known formula gives the optimal topology for every (n, d). De Bruijn is
optimal *in the limit*: for n = d^D, its λ is at least
(1 − d/((d−1)²·D)) · (1 − 1/n) times the best possible λ. That factor goes to 1
as n grows. For small n it isn't optimal (69–86% of the true optimum for n ≤ 11).

## The proof (3 steps)

**Step 1: no topology can beat 1/h\*** (see `BOUND.md`).
- Flow that travels h hops uses h units of capacity.
- Total capacity n·d equals total demand, so λ ≤ 1 / (average hop count).
- At most d^h nodes can be h hops away, so the average hop count is at least the
  Moore value h\*.
- So λ_best ≤ 1/h\*.

**Step 2: de Bruijn reaches at least (n−1)/(n·D).**
- Take n = d^D and write each node as D base-d digits.
- The link u → (d·u + k) mod n drops the first digit and appends digit k.
- *Shift routing:* to go from s to v, append v's digits one by one. After D
  steps you are at v. Every route is ≤ D hops.
- *Counting load:* fix a step t and a link "node x, append digit k". The route
  for a pair (s, v) uses it at step t when two things hold:
  - x = (last D−t digits of s)(first t digits of v), and
  - k = v's digit number t+1.
- Free choices: the first t digits of s (d^t options) and the last D−t−1 digits
  of v (d^(D−t−1) options). That gives d^(D−1) = **n/d pairs, the same for
  every link.**
- Over D steps, each link carries n·D/d pairs, each sending λ·d/(n−1). The load
  is λ·n·D/(n−1), and keeping it ≤ 1 gives **λ_dB ≥ (n−1)/(n·D)**.
- The LP picks the best routing, so it does at least as well as shift routing.
- Key idea: **every link carries the same load, so nothing is a hotspot.** This
  is the "load balance" condition from `BOUND.md`.

**Step 3: compare the two.**
- h\* = Σ_h P(distance ≥ h). Within h−1 hops there are at most
  (d^h − d)/(d−1) nodes. Summing over h = 1..D gives
  **h\* ≥ D − d/(d−1)²**. Nearly all nodes must sit about D hops away.
- So λ_dB / λ_best ≥ h\*·(n−1)/(n·D) ≥ (1 − d/((d−1)²·D))·(1 − 1/n) → 1.
- Examples: d=4, n=1024 (D=5) gives ≥ ~91%. d=2, n=1024 (D=10) gives ≥ ~80%.
  It converges more slowly for d=2.

## Numerical check (LP λ vs the proof's guarantee)

| n | d | D | LP λ (de Bruijn) | proof lower bound (n−1)/(nD) | Moore bound 1/h\* | LP λ / bound |
|---|---|---|---|---|---|---|
| 8 | 2 | 3 | 0.389 | 0.292 | 0.539 | 72% |
| 16 | 2 | 4 | 0.292 | 0.234 | 0.395 | 74% |
| 32 | 2 | 5 | 0.236 | 0.194 | 0.301 | 78% |
| 9 | 3 | 2 | 0.494 | 0.444 | 0.615 | 80% |
| 16 | 4 | 2 | 0.495 | 0.469 | 0.577 | 86% |

The LP value is always at least the proof's lower bound. For d = 2 the ratio
climbs with n, as the proof predicts. (Larger n exceeds the restricted Gurobi
license.)

## The weak spot: say it before the TA does

- The proof needs n = d^D, which means d divides n, so d does **not** divide
  n−1, the assignment's assumption.
- For d | n−1 we rely on two facts:
  - the generalized de Bruijn's max hop count is ⌈log_d n⌉ (Imase–Itoh 1981;
    Reddy–Pradhan–Kuhl 1980), which matches the Moore limit;
  - the LP measures 63–89% of the bound across 15 cases.
- The assignment says d | n−1 is "just for simplicity", not a requirement.
- Script: "We proved it for powers of d and measured it for the rest."

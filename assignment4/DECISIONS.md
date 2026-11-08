# Decisions — Assignment 4 (Maximum Concurrent Flow and Network Design)

Record modelling, algorithm, and implementation decisions here with a brief rationale.

## Modelling assumptions (both parts)

- **Directed links, capacity 1 each.** "d incoming and d outgoing links" reads naturally as d one-way arcs in each direction.
- **Multi-hop, fractional routing.** Nodes relay traffic for others (there are no switches) and a demand may be split over several paths. This is the standard definition of concurrent flow (topologies slides, p. 108).
- **Parallel links allowed; a self-loop is a wasted port.** A node can point several ports at the same peer. A self-loop carries no traffic. Part 1's de Bruijn graph has a few and we keep them (so out-degree stays exactly d) and count them as part of its gap to the bound. Part 2's optimizer will simply never create one.

## Tooling

- **gurobipy with the pip-bundled restricted license.** It covers models up to about 2000 variables/constraints, which is enough for Part 1's small test cases and Part 2 (n = 8). It avoids the academic-license setup unless we exceed the limit.
- **networkx** for building graphs and computing shortest paths. **matplotlib** for figures (saved as PDF).

## Part 1 — Uniform traffic

- **The yardstick is λ ≤ 1/h̄ ≤ 1/h\*(n,d)** (`part1/BOUND.md`). Each hop uses one unit of capacity, and total capacity equals total demand (n·d). So for uniform traffic, maximizing λ means minimizing average hop count *while keeping load balanced*. h\* is the Moore-style best case (d nodes at 1 hop, d² at 2, …) and applies to every topology.
- **Judge candidate topologies by exact LP λ against λ_Moore**, not by hop count alone. The bound is only reached when shortest-path routing also loads every link equally.
- **Topology = integer capacity matrix `cap[u][v]`** (number of parallel u→v links), not a networkx graph. It represents parallel links naturally, and Part 2's integer variables x[u][v] have exactly this shape, so the same LP code serves both parts.
- **LP uses one commodity per source, not per (s, t) pair** (`part1/concurrent_flow.py`, `concurrent_flow`). It needs n commodities instead of n(n−1), which keeps us under the restricted license's size limit. The optimal λ is unchanged: by flow decomposition, a single-source flow that delivers the right amount to each sink splits into s→t paths that carry exactly λ·T[s][t] each.
- **Arc-based (not path-based) LP**, unlike the slides (p. 108). Enumerating all paths blows up; arc flows with conservation constraints are polynomial size and give the same optimum.
- **Sanity checks before trusting it:** the complete graph gives λ = 1 and a directed 6-ring gives λ = 1/3 = 1/h̄ with every arc exactly full. Both match the hand derivation.
- **Explored before choosing (code since removed):** cyclotomic circulant, generalized Kautz, and an exhaustive best-circulant search. The cyclotomic circulant (n prime, jumps = {h : h^d ≡ 1 mod n}) was best on paper: perfectly balanced, λ = 1/h̄ exactly, and it reaches the bound for diameter-2 cases. It is **not in the slides**, though, so it was dropped in favour of something easier to defend from lecture material.
- **Submitted topology: generalized de Bruijn, u → (d·u + k) mod n, k = 0..d−1** (`part1/topologies.py`, `de_bruijn`). It is the lecture's de Bruijn graph (shift left = ×d, append digit = +k) taken mod n. The mod n is required because d | n−1 rules out n = d^m. It is defended with slide material only: the hop bound (pp. 54, 66), the reach-in-⌈log_d n⌉-shifts property (p. 49), and the lecture's own caveat that labels don't balance traffic (p. 53), which explains the gap.
- **Framed as near-optimal with a measured gap, not optimal.** Exact λ is 63–89% of the bound that applies to every topology. Max hops = ⌈log_d n⌉ in all 15 cases.
- **Baseline = simple circulant u → u+1..u+d.** It is the obvious alternative and has linear-in-n hop counts. De Bruijn wins 12/15. The circulant wins only at 7/2, 7/3, 9/4, where hop counts are nearly equal and de Bruijn's self-loops cost more than its shorter paths save. This is reported honestly.
- **Example figure uses n = 9, d = 2, not 7/2.** At 7/2 the baseline wins, so it would illustrate the wrong point. 9/2 is small enough to draw legibly.
- **One-shot entry point `part1/run.py`** writes `part1/results/part1.csv` and both PDFs into `assignment4/figures/`, using a non-interactive matplotlib backend so it never blocks (the lesson from A1's `plt.show()`).

# Decisions — Assignment 4 (Maximum Concurrent Flow and Network Design)

Record modelling, algorithm, and implementation decisions here with a brief rationale.

## Modelling assumptions (both parts)

- **Directed links, capacity 1 each.** "d incoming and d outgoing links" reads naturally as d one-way arcs in each direction.
- **Multi-hop, fractional routing.** Nodes relay traffic for others (there are no switches) and a demand may be split over several paths. This is the standard definition of concurrent flow (topologies slides, p. 108).
- **Parallel links allowed; a self-loop is a wasted port.** A node can point several ports at the same peer. A self-loop carries no traffic. The original Part 1 de Bruijn baseline retains them; the later loop-rewired candidate replaces them while preserving in/out degree. Part 2's optimizer never creates one.

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
- **Base topology: generalized de Bruijn, u → (d·u + k) mod n, k = 0..d−1** (`part1/topologies.py`, `de_bruijn`). It is the lecture's de Bruijn graph (shift left = ×d, append digit = +k) taken mod n. The mod n is required because d | n−1 rules out n = d^m. It is defended with slide material: the hop bound (pp. 54, 66), the reach-in-⌈log_d n⌉-shifts property (p. 49), and the lecture's caveat that labels don't balance traffic (p. 53). The submitted improved candidate rewires its self-loops as described below.
- **Framed with a measured gap, not optimal.** Base exact λ is 63–89% of the universal bound; rewired exact λ is 71–95%. Max hops = ⌈log_d n⌉ in all 15 measured cases for each variant.
- **Baseline = simple circulant u → u+1..u+d.** It is the obvious alternative and has linear-in-n hop counts. The original de Bruijn wins 12/15; the rewired variant wins 14/15 and ties one.
- **Example figure uses n = 9, d = 2, not 7/2.** At 7/2 the baseline wins, so it would illustrate the wrong point. 9/2 is small enough to draw legibly.
- **One-shot entry point `part1/run.py`** writes `part1/results/part1.csv` and three PDFs into `assignment4/figures/`, using a non-interactive matplotlib backend so it never blocks (the lesson from A1's `plt.show()`).

## Part 2 — Hose traffic, n = 8, d = 4

- **Adaptive reading: one MILP solved per T** (`part2/topology_milp.py`, `best_topology`). The PDF asks "how the topology adapts to the given traffic matrix", so the topology is re-optimized for each T, like an optical circuit switch picking a new matching. We did not use the robust reading (one fixed topology for all of T_hose), which is a harder max–min problem.
- **MILP rather than a constructive design.** A construction would have to be *proved* optimal for every real-valued hose T, which is hard. A MILP is optimal by construction, and the PDF requires a Gurobi implementation anyway.
- **Formulation = Part 1's LP + topology variables** (`part2/FORMULATION.md`). Conservation and capacity constraints are the same as Part 1. The only additions are integer `x[u,v]` replacing the fixed capacity, and the degree constraints. This makes it easy to explain: "Part 1 evaluates a topology; Part 2 also chooses it."
- **x integer in [0, d], self-loops excluded, parallel links allowed.** Integer because you can't build half a link. Parallel links are needed for skewed T (4 × permutation → λ = 1 needs 4 links to one peer).
- **Cross-check with Part 1's LP:** every MILP topology is re-evaluated by `part1/concurrent_flow.py`, and the λ must match. This catches modelling bugs in either file.
- **Sanity results:** 4 × permutation → λ = 1. Uniform → λ = 0.7 with a proven 0% gap, exactly the Part 1 bound 1/h\*(8,4), so for n = 8, d = 4 the bound is tight. Solves take about 1 s.
- **Test matrices** (`part2/run.py`, `test_matrices`): integer permutation mixes (λ = 1 should be reachable), a real-weighted permutation mix, a skewed matrix, uniform (the hardest case), and 10 random dense matrices. All have row/column sums *exactly* 4. The hose set allows ≤ 4, but equality is the fully loaded and hardest case, and it makes λ ≤ 1 a clean bound. Random matrices are generated by Sinkhorn scaling (alternately normalize rows and columns) with a fixed seed (422) for reproducibility. Permutations are derangements, so there is no traffic to self.
- **Baselines that don't adapt**, to show what adaptation buys: (i) the MILP-optimal uniform topology, chosen once, and (ii) Part 1's de Bruijn. Both are scored with the same Part 1 LP, so the only difference is whether the topology was re-chosen for T.
- **Results:** adaptive λ = 1 for integer permutation mixes, 0.92 for the real-weighted mix, 0.70 for uniform (= bound), and about 0.80 for random. The fixed uniform-optimal topology gets 0.50 on a permutation, and on random T it is 16% below adaptive on average. Every solve has gap ≤ 4e-5 and takes seconds. The whole run takes about 2 min.
- **Example figure = real-weighted 3-permutation matrix.** It shows both effects at once: links follow demand (2.0 → 2 links) and integrality forces some two-hop relaying (1.2 → 1 link), which explains why λ < 1.

## Independent audit fixes (2026-11-08)

An auditor agent that saw only the spec, the slides, the code and the report (not this file) found no critical issues. Fixes:

- **The Plesník–Znám claim was overstated.** It only rules out perfect Moore digraphs (n = 1+d+…+d^D). The bound *is* reachable for some (n, d): (8,4), (7,3), (9,4), (11,2), (11,5). The report and BOUND.md now say this.
- **Added a true-optimum column for n ≤ 11** (`part1/optimum_small.py`, which reuses the Part 2 MILP). De Bruijn is 69–86% of the real optimum. The report now answers "why not use the MILP for Part 1?": it is an exponential search that is only practical for small n, not a construction for general n.
- **Explained what d | n−1 is for:** it gives gcd(d, n) = 1, so u → d·u mod n is a permutation and the construction doesn't degenerate. This is also why de Bruijn does badly in Part 2: (8,4) has gcd 4, every even node shares one neighbour block, and there are **4** self-loops (the report had wrongly said 2).
- **Corrected the explanation of why the circulant wins:** at 7/3 and 9/4 the circulant has *fewer* average hops, not more.
- **Part 2 now checks optimality:** `run.py` asserts gap ≤ 1e-4. This immediately caught a 120 s time-limit hit on "skewed" (gap 2.7%, partly from CPU contention), so the time limit was raised to 600 s. The gap is stored unrounded in the CSV. `best_topology` rejects T = 0, which would be unbounded.
- **The three-permutation test matrix now requires the permutations to be disjoint** (two of them collided in one row before). The results were regenerated, so Part 2 numbers changed slightly (3-perm λ = 0.938; random-matrix gain from adapting is 18%).
- Qualified "uniform is the hardest" as an empirical observation, cited the generalized de Bruijn digraph (Reddy–Pradhan–Kuhl; Imase–Itoh), gave the reason for in-degree d, and fixed line-range links.
- **At the time of the independent audit:** the Part 1 construction was still the unmodified de Bruijn graph. The later loop-rewired revision is documented below.

## Loop-rewired revision (2026-11-09)

- **Construction:** start from generalized de Bruijn, delete each self-loop, and connect its former endpoint to the next loop endpoint in ascending-label cyclic order. This uses each freed input and output port once. Parallel edges remain allowed.
- **Why this variant:** self-loops waste capacity under all-to-all traffic. The cycle removes them without changing the port budget or requiring a search over topologies. It is a deterministic heuristic, not a proof of optimality for general $(n,d)$.
- **Verification:** structural tests check degree, zero self-loops and edge replacement across all 15 measured cases. The Gurobi LP was rerun for those cases; the rewired candidate improved exact concurrent flow in all 15, reaching 71--95% of the universal bound. It remains below known small-instance optima.
- **Part 2 unchanged:** its fixed de Bruijn baseline is the original construction, not the rewired candidate; the Part 2 adaptive MILP and published data were not rerun as part of this Part 1 revision.

- **Asymptotic-optimality proof kept out of the report, in `part1/PROOF_NOTES.md` for exam prep.** For n = d^D, shift routing loads every link equally, so λ_dB ≥ (n−1)/(nD), and h* ≥ D − d/(d−1)², so de Bruijn reaches at least (1 − d/((d−1)²D))(1 − 1/n) of the optimum, which goes to 1. The report already argues via hop counts and measurements; the proof is backup for "why isn't it optimal?" questions.

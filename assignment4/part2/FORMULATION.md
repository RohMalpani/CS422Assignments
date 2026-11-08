# Part 2: MILP formulation (n = 8, d = 4, hose traffic)

Given **one** traffic matrix T from the hose set, choose the topology *and* the
routing together so that the concurrent flow λ is as large as possible. The
topology adapts to T because we re-solve for each T, like an optical circuit
switch reconfiguring its matching (intro lecture, pp. 34–37).

## Decision variables

| Variable | Domain | Meaning |
|---|---|---|
| `x[u,v]` for u ≠ v | integer ≥ 0 | number of links from u to v (**the topology**) |
| `f[s,u,v]` for every source s, u ≠ v | real ≥ 0 | traffic originating at s that crosses link u→v (**the routing**) |
| `λ` | real ≥ 0 | fraction of every demand that is delivered (**the objective**) |

## Objective

```
maximize  λ
```

## Constraints

**1. Degree (topology is valid).** Every node uses exactly d ports in each direction:

```
Σ_v x[u,v] = d     for every u        (d outgoing links)
Σ_u x[u,v] = d     for every v        (d incoming links)
```

**2. Flow conservation (routing delivers λ·T).** For each source s and node v:

```
Σ_w f[s,v,w] − Σ_u f[s,u,v]  =  λ · Σ_t T[s,t]     if v = s   (s sends all its traffic)
                              = −λ · T[s,v]         if v ≠ s   (v absorbs its share; relays net 0)
```

**3. Capacity (routing fits on the topology).** A link carries at most its
number of parallel unit links:

```
Σ_s f[s,u,v]  ≤  x[u,v]     for every u ≠ v
```

## Intuition: how this captures the problem

- Constraints 2 and 3 with x **fixed** are exactly Part 1's concurrent-flow LP
  (`part1/concurrent_flow.py`). For a given topology they compute the best
  λ over all multi-hop, split routings.
- Making x a **variable** lets the solver choose the topology too, subject only
  to the port budget (constraint 1). So the optimum is the best λ over *every*
  topology with d-in/d-out ports *and* every routing. That is the
  definition of "the topology that maximizes concurrent flow for T".
- It stays **linear**: λ·T[s,t] is a variable times a constant, and capacity
  compares a sum of flows with x. Only x must be **integer** (you can't
  build half a link), so it is a MILP rather than an LP.
- **Self-loops** are excluded (u ≠ v) since they can never carry traffic.
  **Parallel links** are allowed (x can be 2, 3, 4), which matters: for T = 4 × a
  permutation, the best answer is 4 parallel links from each node to its
  single destination, giving λ = 1.
- **One commodity per source** (8 commodities, not 56 pairs) gives the same λ by
  flow decomposition (same argument as Part 1) and keeps the model small:
  56 integer + 448 continuous variables.

## What to expect

- Every hose matrix here has row/column sums of 4. Total demand is then 32 = total
  capacity 8·4, so **λ ≤ 1**, with equality only if every demand goes
  in one hop.
- If T is "4 × (a sum of permutations with integer weights)", direct links
  realize it exactly: **λ = 1**.
- Uniform T (4/7 everywhere) can't be all one-hop: **λ ≤ 0.7** (Part 1 bound).

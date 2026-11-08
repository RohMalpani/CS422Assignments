# Part 1, Step 1: Upper bound on concurrent flow under uniform traffic

## Setup

- Directed graph G on n nodes. Each node has d outgoing and d incoming
  links. Each link (arc) has capacity 1.
- Total capacity of the network: **C = n·d**.
- Uniform traffic: T_ij = d/(n−1) for i ≠ j, so each node sends d in total.
  Total demand: n(n−1) · d/(n−1) = **n·d**.
- Concurrent flow λ: the largest λ such that λ·T_ij can be routed for **all**
  pairs at once without exceeding any link capacity. Flow can be split
  across multiple paths and relayed through other nodes.

## Bound 1: λ ≤ 1 / (average hop count)

A unit of flow that travels h hops occupies 1 unit of capacity on each of h
links, so it uses h units of capacity in total. Routing λ·T_ij from i to j
therefore uses at least λ·T_ij·dist(i,j) capacity, where dist is the
shortest-path hop count in G. Summing over all pairs:

```
λ · Σ_{i≠j} T_ij · dist(i,j)  ≤  total capacity used  ≤  n·d
λ · d/(n−1) · Σ_{i≠j} dist(i,j)  ≤  n·d
λ  ≤  n(n−1) / Σ_{i≠j} dist(i,j)  =  1 / h̄(G)
```

where h̄(G) is the average shortest-path length over all ordered pairs.

**Takeaway:** for uniform traffic, *maximizing λ is (at best) minimizing the
average hop count*. A packet that takes extra hops takes capacity away from
other traffic.

**When is this bound reached exactly?** When both of these hold:
1. all flow uses shortest paths (no hops wasted), and
2. every link carries exactly 1 unit (no capacity left idle). The load must
   be perfectly balanced.

Short paths alone are not enough. A topology with short paths and one hot
link can do worse than a slightly longer but symmetric one.

## Bound 2: no topology can beat the Moore-style bound

From any node, at most d nodes are at distance 1, at most d² at distance 2,
and in general at most d^h at distance h. Each node at distance h−1 has only
d outgoing links. The best any topology can do is fill these layers greedily:

```
m_h = min(d^h, (n−1) − Σ_{k<h} m_k)      // nodes at distance h
h*(n,d) = (1/(n−1)) · Σ_h h·m_h          // smallest possible average hop count
λ  ≤  1 / h̄(G)  ≤  1 / h*(n,d)  =: λ_Moore(n,d)   // for every topology G
```

This holds even if parallel links are allowed, because parallel links only
reduce the number of distinct neighbours.

### Worked examples

| n | d | layers (m_1, m_2, …) | h* | λ_Moore |
|---|---|---|---|---|
| 7 | 2 | 2, 4 | 10/6 ≈ 1.667 | 0.600 |
| 8 | 4 | 4, 3 | 10/7 ≈ 1.429 | 0.700 |
| 13 | 3 | 3, 9 | 21/12 = 1.75 | ≈ 0.571 |
| n | n−1 | n−1 | 1 | 1 (complete graph, bound is tight) |

(n = 8, d = 4 is also Part 2's setting. There, uniform traffic can never get
above λ = 0.7.)

## What this gives us for the next steps

- **λ_Moore(n,d)** is the yardstick. A topology is "best" if its λ, computed
  exactly by a linear program in Step 2, equals or comes closest to this
  bound.
- Directed graphs that reach the Moore bound exactly do not exist for d ≥ 2
  and diameter ≥ 2 (Plesník and Znám, 1974). So for general n and d, the goal
  is a construction that gets close to it, with a good argument for why.
- Candidates trade off the two tightness conditions:
  - *short paths* (Kautz / de Bruijn) vs.
  - *perfect load balance* (symmetric circulant graphs).

"""Exact maximum concurrent flow for a given topology and traffic matrix.

A topology is an n x n integer matrix `cap`, where cap[u][v] is the number of
parallel unit-capacity links from u to v (so cap[u][v] is the capacity of
u -> v). A traffic matrix T is an n x n matrix of demands with T[i][i] = 0.

Run directly (`python concurrent_flow.py`) for sanity checks against cases
whose answer we know by hand.
"""

import gurobipy as gp
import networkx as nx
import numpy as np
from gurobipy import GRB


def uniform_tm(n, d):
    """Uniform traffic matrix from the assignment: d/(n-1) off-diagonal, 0 on the diagonal."""
    T = np.full((n, n), d / (n - 1))
    np.fill_diagonal(T, 0.0)
    return T


def concurrent_flow(cap, T):
    """Return (lam, arc_load) where lam is the max concurrent flow of T on cap.

    LP (one commodity per *source* s, which carries all of s's traffic):
        variables  f[s, u, v] >= 0   flow of source s's traffic on arc u->v
                   lam >= 0          fraction of every demand that is routed
        maximize   lam
        subject to conservation, for every source s and node v:
                       out(v) - in(v) = lam * sum_t T[s][t]   if v == s
                       out(v) - in(v) = -lam * T[s][v]        otherwise
                   capacity, for every arc u->v:
                       sum_s f[s, u, v] <= cap[u][v]

    One commodity per source instead of per (s, t) pair gives n commodities
    instead of n(n-1). It gives the same lam: a single-source flow that
    delivers the right amount to each sink can always be decomposed into
    s->t paths carrying exactly lam*T[s][t] each (flow decomposition).
    """
    cap = np.asarray(cap)
    T = np.asarray(T, dtype=float)
    n = len(cap)
    arcs = [(u, v) for u in range(n) for v in range(n) if u != v and cap[u][v] > 0]

    m = gp.Model("concurrent_flow")
    m.Params.OutputFlag = 0
    f = m.addVars([(s, u, v) for s in range(n) for (u, v) in arcs], lb=0.0, name="f")
    lam = m.addVar(lb=0.0, name="lam")
    m.setObjective(lam, GRB.MAXIMIZE)

    for s in range(n):
        for v in range(n):
            out_v = gp.quicksum(f[s, v, w] for (x, w) in arcs if x == v)
            in_v = gp.quicksum(f[s, u, v] for (u, x) in arcs if x == v)
            net = lam * T[s].sum() if v == s else -lam * T[s][v]
            m.addConstr(out_v - in_v == net, name=f"cons[{s},{v}]")

    for (u, v) in arcs:
        m.addConstr(gp.quicksum(f[s, u, v] for s in range(n)) <= cap[u][v], name=f"cap[{u},{v}]")

    m.optimize()
    if m.Status != GRB.OPTIMAL:
        raise RuntimeError(f"LP not solved to optimality (status {m.Status})")

    # Load on each arc, as a fraction of its capacity (1.0 = full).
    arc_load = {(u, v): sum(f[s, u, v].X for s in range(n)) / cap[u][v] for (u, v) in arcs}
    return lam.X, arc_load


def avg_hops(cap):
    """Average shortest-path hop count over all ordered pairs (h-bar in BOUND.md)."""
    cap = np.asarray(cap)
    n = len(cap)
    G = nx.DiGraph([(u, v) for u in range(n) for v in range(n) if u != v and cap[u][v] > 0])
    G.add_nodes_from(range(n))
    total = 0
    for s, dists in nx.all_pairs_shortest_path_length(G):
        if len(dists) < n:
            return float("inf")  # some node unreachable: not strongly connected
        total += sum(dists.values())
    return total / (n * (n - 1))


def moore_bound(n, d):
    """Best possible average hop count h*(n, d) and lam_Moore = 1/h* (BOUND.md, Bound 2)."""
    remaining, h, total = n - 1, 0, 0
    while remaining > 0:
        h += 1
        m_h = min(d ** h, remaining)  # at most d^h nodes can sit at distance h
        total += h * m_h
        remaining -= m_h
    h_star = total / (n - 1)
    return h_star, 1 / h_star


if __name__ == "__main__":
    # 1. Complete graph (d = n-1): every pair one hop away -> lam = 1.
    n = 5
    K = np.ones((n, n), dtype=int) - np.eye(n, dtype=int)
    lam, _ = concurrent_flow(K, uniform_tm(n, n - 1))
    print(f"complete graph n={n}:   lam={lam:.4f}  (expect 1)")

    # 2. Directed ring (d = 1): average hops = n/2, perfectly symmetric -> lam = 2/n.
    n = 6
    ring = np.zeros((n, n), dtype=int)
    for i in range(n):
        ring[i][(i + 1) % n] = 1
    lam, load = concurrent_flow(ring, uniform_tm(n, 1))
    print(f"directed ring n={n}:    lam={lam:.4f}  (expect {2 / n:.4f}),  "
          f"1/avg_hops={1 / avg_hops(ring):.4f},  arc loads={sorted(set(round(x, 4) for x in load.values()))}")

    # 3. Moore bound table from BOUND.md.
    for n, d in [(7, 2), (8, 4), (13, 3)]:
        h_star, lam_m = moore_bound(n, d)
        print(f"moore_bound n={n:2d} d={d}:  h*={h_star:.4f}  lam_Moore={lam_m:.4f}")

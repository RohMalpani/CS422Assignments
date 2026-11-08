"""Part 2: choose the topology and routing that maximize concurrent flow for a given T.

MILP (see FORMULATION.md):
    variables  x[u,v] integer >= 0   links u -> v (the topology), u != v
               f[s,u,v] >= 0         flow of source s's traffic on link u -> v
               lam >= 0              fraction of every demand delivered
    maximize   lam
    subject to sum_v x[u,v] = d,  sum_u x[u,v] = d          (degree)
               out(v) - in(v) = lam * sum_t T[s,t]  if v == s (conservation,
               out(v) - in(v) = -lam * T[s,v]       otherwise  per source s)
               sum_s f[s,u,v] <= x[u,v]                      (capacity)

    python topology_milp.py      # sanity checks on matrices with known answers
"""

import os
import sys

import gurobipy as gp
import numpy as np
from gurobipy import GRB

# Reuse Part 1's LP to independently re-check the topology the MILP returns.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "part1"))
from concurrent_flow import concurrent_flow  # noqa: E402


def best_topology(T, d, time_limit=None):
    """Return (lam, X, gap): X[u][v] is the optimal number of u -> v links for T,
    and gap is Gurobi's optimality gap (0 = proven optimal)."""
    T = np.asarray(T, dtype=float)
    if T.sum() <= 0:  # no demand at all: every lam is feasible, so the MILP would be unbounded
        raise ValueError("traffic matrix has no demand")
    n = len(T)
    arcs = [(u, v) for u in range(n) for v in range(n) if u != v]  # no self-loops

    m = gp.Model("best_topology")
    m.Params.OutputFlag = 0
    if time_limit:
        m.Params.TimeLimit = time_limit

    x = m.addVars(arcs, vtype=GRB.INTEGER, lb=0, ub=d, name="x")
    f = m.addVars([(s, u, v) for s in range(n) for (u, v) in arcs], lb=0.0, name="f")
    lam = m.addVar(lb=0.0, name="lam")
    m.setObjective(lam, GRB.MAXIMIZE)

    # 1. Degree: d outgoing and d incoming links per node.
    for u in range(n):
        m.addConstr(gp.quicksum(x[u, v] for v in range(n) if v != u) == d, name=f"out[{u}]")
        m.addConstr(gp.quicksum(x[v, u] for v in range(n) if v != u) == d, name=f"in[{u}]")

    # 2. Conservation: source s emits lam * (its row sum); each v != s absorbs lam * T[s][v].
    for s in range(n):
        for v in range(n):
            out_v = gp.quicksum(f[s, v, w] for w in range(n) if w != v)
            in_v = gp.quicksum(f[s, u, v] for u in range(n) if u != v)
            net = lam * T[s].sum() if v == s else -lam * T[s][v]
            m.addConstr(out_v - in_v == net, name=f"cons[{s},{v}]")

    # 3. Capacity: total flow on u -> v fits on the x[u,v] unit links chosen.
    for (u, v) in arcs:
        m.addConstr(gp.quicksum(f[s, u, v] for s in range(n)) <= x[u, v], name=f"cap[{u},{v}]")

    m.optimize()
    if m.SolCount == 0:
        raise RuntimeError(f"no solution found (status {m.Status})")

    X = np.zeros((n, n), dtype=int)
    for (u, v) in arcs:
        X[u][v] = round(x[u, v].X)
    return lam.X, X, m.MIPGap


if __name__ == "__main__":
    n, d = 8, 4

    # 1. 4 x a permutation: 4 parallel links to the single destination -> lam = 1.
    P = np.zeros((n, n))
    for i in range(n):
        P[i][(i + 3) % n] = 4
    lam, X, gap = best_topology(P, d)
    print(f"4 x permutation: lam={lam:.4f} (expect 1)   check LP={concurrent_flow(X, P)[0]:.4f}")

    # 2. Uniform 4/7: cannot be all one-hop -> lam <= 0.7 (Part 1 bound).
    U = np.full((n, n), d / (n - 1))
    np.fill_diagonal(U, 0)
    lam, X, gap = best_topology(U, d)
    print(f"uniform:         lam={lam:.4f} (expect <= 0.7) check LP={concurrent_flow(X, U)[0]:.4f}  gap={gap:.1e}")
    print("  links per row:", [np.nonzero(X[u])[0].tolist() for u in range(n)])

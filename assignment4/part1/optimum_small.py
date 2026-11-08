"""Yardstick for Part 1: the true optimum lam for small (n, d), using Part 2's MILP.

The MILP searches over every topology with d-in/d-out ports, so its value is the
best any topology can do. It is exponential-time, which is exactly why it is not
the Part 1 answer, and it only fits the restricted Gurobi license for n <= 11.
When the time limit hits, the true optimum lies in [best found, upper bound],
where the upper bound is min(Gurobi's bound, 1/h*(n, d)).

Writes part1/results/part1_optimum.csv.   python optimum_small.py
"""

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "part2"))
from concurrent_flow import concurrent_flow, moore_bound, uniform_tm  # noqa: E402
from topologies import de_bruijn  # noqa: E402
from topology_milp import best_topology  # noqa: E402

CASES = [(7, 2), (7, 3), (9, 2), (9, 4), (11, 2), (11, 5)]
TIME_LIMIT = 300  # seconds per case


def main():
    rows = []
    for n, d in CASES:
        lam, X, gap = best_topology(uniform_tm(n, d), d, time_limit=TIME_LIMIT)
        upper = min(lam * (1 + gap), moore_bound(n, d)[1])  # gap is relative to the incumbent
        proven = gap <= 1e-4 or abs(lam - upper) < 1e-4
        db = concurrent_flow(de_bruijn(n, d), uniform_tm(n, d))[0]
        rows.append({"n": n, "d": d, "opt_lower": round(lam, 4), "opt_upper": round(upper, 4),
                     "proven": proven, "debruijn_lam": round(db, 4),
                     "debruijn_pct_of_opt_upper": round(100 * db / upper, 1)})
        print(rows[-1], flush=True)
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    path = os.path.join(HERE, "results", "part1_optimum.csv")
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("wrote", path)


if __name__ == "__main__":
    main()

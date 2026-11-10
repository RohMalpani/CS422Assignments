"""Part 1 one-shot entry point: evaluate generalized de Bruijn under uniform traffic.

For each (n, d) with n-1 divisible by d:
  - lam for de Bruijn, its loop-rewired variant, and the circulant baseline (exact LP),
  - the Moore bound lam_Moore = 1/h*(n, d), which no topology can beat,
  - average/maximum hop count and number of self-loops.

Outputs:
  part1/results/part1.csv
  figures/part1_lambda_vs_bound.pdf   (lam vs. bound for every case)
  figures/part1_debruijn_n9_d2.pdf    (drawing of an example topology)
  figures/part1_rewired_n9_d2.pdf     (drawing of the loop-rewired example)

    python run.py
"""

import csv
import math
import os

import matplotlib

matplotlib.use("Agg")  # write files only, never open a window
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

from concurrent_flow import avg_hops, concurrent_flow, moore_bound, uniform_tm
from topologies import de_bruijn, loop_rewired_de_bruijn, simple_circulant

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
FIGURES = os.path.join(HERE, "..", "figures")

# n - 1 divisible by d, as the assignment assumes. Small enough for the
# restricted Gurobi license (about 2000 variables: n * n * d flow variables).
CASES = [(7, 2), (7, 3), (9, 2), (9, 4), (11, 2), (11, 5), (13, 2), (13, 3),
         (13, 4), (13, 6), (16, 3), (16, 5), (17, 2), (17, 4), (19, 3)]

# Distinct colors for the three candidates; bound in neutral ink.
C_DEBRUIJN, C_REWIRED, C_CIRCULANT = "#2a78d6", "#1baf7a", "#eb6834"
C_BOUND, C_MUTED = "#0b0b0b", "#52514e"


def max_hops(cap):
    n = len(cap)
    G = nx.DiGraph([(u, v) for u in range(n) for v in range(n) if u != v and cap[u][v] > 0])
    return nx.diameter(G)


def evaluate():
    rows = []
    for n, d in CASES:
        _, lam_moore = moore_bound(n, d)
        row = {"n": n, "d": d, "lam_moore": lam_moore, "ceil_log_d_n": math.ceil(math.log(n, d) - 1e-9)}
        for name, cap in [("debruijn", de_bruijn(n, d)),
                          ("rewired", loop_rewired_de_bruijn(n, d)),
                          ("circulant", simple_circulant(n, d))]:
            lam, _ = concurrent_flow(cap, uniform_tm(n, d))
            row[f"{name}_lam"] = lam
            row[f"{name}_pct_of_bound"] = 100 * lam / lam_moore
            row[f"{name}_avg_hops"] = avg_hops(cap)
            row[f"{name}_max_hops"] = max_hops(cap)
            row[f"{name}_self_loops"] = int(np.trace(cap))
        rows.append(row)
        print(f"n={n:2d} d={d}  bound={lam_moore:.4f}  de Bruijn={row['debruijn_lam']:.4f} "
              f"({row['debruijn_pct_of_bound']:.0f}%, max hops {row['debruijn_max_hops']} "
              f"<= {row['ceil_log_d_n']}, {row['debruijn_self_loops']} self-loops)  "
              f"rewired={row['rewired_lam']:.4f} ({row['rewired_pct_of_bound']:.0f}%, "
              f"{row['rewired_self_loops']} self-loops)  "
              f"circulant={row['circulant_lam']:.4f} ({row['circulant_pct_of_bound']:.0f}%)")
    return rows


def write_csv(rows):
    os.makedirs(RESULTS, exist_ok=True)
    path = os.path.join(RESULTS, "part1.csv")
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: round(v, 4) if isinstance(v, float) else v for k, v in r.items()})
    print("wrote", path)


def plot_lambda(rows):
    """Dot plot: one column per (n, d); the bound is a dash, topologies are dots."""
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    x = np.arange(len(rows))
    ax.scatter(x, [r["lam_moore"] for r in rows], marker="_", s=260, linewidths=2,
               color=C_BOUND, label="Upper bound $1/h^*(n,d)$ (any topology)", zorder=3)
    ax.scatter(x, [r["debruijn_lam"] for r in rows], s=42, color=C_DEBRUIJN,
               edgecolors="white", linewidths=1, label="Generalized de Bruijn", zorder=4)
    ax.scatter(x, [r["rewired_lam"] for r in rows], s=42, color=C_REWIRED,
               edgecolors="white", linewidths=1, label="Loop-rewired de Bruijn", zorder=5)
    ax.scatter(x, [r["circulant_lam"] for r in rows], s=42, color=C_CIRCULANT,
               edgecolors="white", linewidths=1, label="Simple circulant (baseline)", zorder=4)
    ax.set_xticks(x, [f"{r['n']},{r['d']}" for r in rows], fontsize=8)
    ax.set_xlabel("(n, d)", color=C_MUTED)
    ax.set_ylabel("Concurrent flow $\\lambda$", color=C_MUTED)
    ax.set_ylim(0, 0.8)
    ax.grid(axis="y", color="#e4e3df", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#bdbcb6")
    ax.tick_params(colors=C_MUTED)
    ax.legend(frameon=False, fontsize=8, loc="upper left", ncol=2, bbox_to_anchor=(0, 1.18))
    fig.tight_layout()
    path = os.path.join(FIGURES, "part1_lambda_vs_bound.pdf")
    fig.savefig(path)
    plt.close(fig)
    print("wrote", path)


def plot_topology(n=9, d=2, rewired=False):
    """Draw the original or loop-rewired de Bruijn topology."""
    cap = loop_rewired_de_bruijn(n, d) if rewired else de_bruijn(n, d)
    original = de_bruijn(n, d)
    G = nx.MultiDiGraph()
    G.add_nodes_from(range(n))
    for u in range(n):
        for v in range(n):
            for _ in range(cap[u, v]):
                G.add_edge(u, v)
    pos = {i: (math.sin(2 * math.pi * i / n), math.cos(2 * math.pi * i / n)) for i in range(n)}

    fig, ax = plt.subplots(figsize=(4.2, 4.2))
    nx.draw_networkx_nodes(G, pos, node_color="white", edgecolors=C_DEBRUIJN, linewidths=2,
                           node_size=520, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=11, ax=ax)
    normal = [(u, v) for u in range(n) for v in range(n) if u != v
              for _ in range(min(cap[u, v], original[u, v]))]
    new_links = [(u, v) for u in range(n) for v in range(n) if u != v
                 for _ in range(max(0, cap[u, v] - original[u, v]))]
    loops = [(u, v) for u, v in G.edges() if u == v]
    nx.draw_networkx_edges(G, pos, edgelist=normal, edge_color=C_DEBRUIJN, width=1.4,
                           arrowstyle="-|>", arrowsize=12, node_size=520,
                           connectionstyle="arc3,rad=0.12", ax=ax)
    if new_links:
        nx.draw_networkx_edges(G, pos, edgelist=new_links, edge_color=C_REWIRED, width=2.1,
                               arrowstyle="-|>", arrowsize=12, node_size=520,
                               connectionstyle="arc3,rad=0.12", ax=ax)
    for u, _ in loops:  # networkx does not draw self-loops reliably; draw a ring outside the node
        x, y = pos[u]
        ax.add_patch(plt.Circle((1.22 * x, 1.22 * y), 0.13, fill=False, color=C_CIRCULANT, lw=1.6))
    title = "Loop-rewired de Bruijn" if rewired else "Generalized de Bruijn"
    ax.set_title(f"{title}, n={n}, d={d}", fontsize=10)
    note = "green = links replacing self-loops" if rewired else f"orange = self-loop (wasted port), {int(np.trace(cap))} in total"
    ax.text(0, -1.32, note, ha="center", fontsize=8, color=C_MUTED)
    ax.set_xlim(-1.35, 1.35)
    ax.set_ylim(-1.4, 1.42)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    kind = "rewired" if rewired else "debruijn"
    path = os.path.join(FIGURES, f"part1_{kind}_n{n}_d{d}.pdf")
    fig.savefig(path)
    plt.close(fig)
    print("wrote", path)


def main():
    os.makedirs(FIGURES, exist_ok=True)
    rows = evaluate()
    write_csv(rows)
    plot_lambda(rows)
    plot_topology(9, 2)
    plot_topology(9, 2, rewired=True)


if __name__ == "__main__":
    main()

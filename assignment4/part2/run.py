"""Part 2 one-shot entry point: adaptive topology (MILP) on hose traffic matrices, n = 8, d = 4.

For every test matrix T:
  - adaptive:      best_topology(T): topology chosen for this T (MILP, proven optimal)
  - fixed uniform: one topology chosen once (MILP-optimal for uniform T) and never changed
  - fixed de Bruijn: Part 1's construction, never changed
Fixed topologies are scored with Part 1's LP, so all three use the same routing model.

Outputs:
  part2/results/part2.csv
  figures/part2_lambda.pdf          (lam per matrix: adaptive vs. fixed)
  figures/part2_adapt_example.pdf   (T next to the topology chosen for it)

    python run.py
"""

import csv
import os
import sys

import matplotlib

matplotlib.use("Agg")  # write files only, never open a window
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "part1"))
from concurrent_flow import concurrent_flow, uniform_tm  # noqa: E402
from topologies import de_bruijn  # noqa: E402
from topology_milp import best_topology  # noqa: E402

RESULTS = os.path.join(HERE, "results")
FIGURES = os.path.join(HERE, "..", "figures")
N, D = 8, 4
SEED = 422
N_RANDOM = 10

# Reference palette slots 1-3, light mode.
C_ADAPT, C_FIXED_U, C_FIXED_DB, C_MUTED = "#2a78d6", "#eb6834", "#1baf7a", "#52514e"


# ---------- hose traffic matrices (every row and column sums to D, zero diagonal) ----------

def derangement(rng, n):
    """Random permutation with no fixed point (a node never sends to itself)."""
    while True:
        p = rng.permutation(n)
        if all(p[i] != i for i in range(n)):
            return p


def perm_matrix(p):
    P = np.zeros((len(p), len(p)))
    P[np.arange(len(p)), p] = 1
    return P


def sinkhorn(A, total, iters=2000):
    """Scale a nonnegative matrix until every row and column sums to `total`."""
    A = A.copy()
    for _ in range(iters):
        A *= total / A.sum(axis=1, keepdims=True)
        A *= total / A.sum(axis=0, keepdims=True)
    return A


def test_matrices(rng):
    n, d = N, D
    while True:  # three permutations that never send to the same destination in any row
        p1, p2, p3 = derangement(rng, n), derangement(rng, n), derangement(rng, n)
        if all(len({p1[i], p2[i], p3[i]}) == 3 for i in range(n)):
            break
    mats = [
        ("permutation", d * perm_matrix(p1)),                                   # one partner each
        ("2 permutations", 2 * perm_matrix(p1) + 2 * perm_matrix(p2)),          # integer mix
        ("3 perms, real wts", d * (0.5 * perm_matrix(p1) + 0.3 * perm_matrix(p2)
                                   + 0.2 * perm_matrix(p3))),                    # fractional mix
        ("skewed", 3 * perm_matrix(p1) + uniform_tm(n, 1)),                     # 3 to a partner, 1 spread
        ("uniform", uniform_tm(n, d)),                                          # all-to-all
    ]
    for i in range(N_RANDOM):
        A = rng.random((n, n))
        np.fill_diagonal(A, 0)
        mats.append((f"random {i + 1}", sinkhorn(A, d)))
    for name, T in mats:  # every matrix must be in the hose set
        assert np.allclose(T.sum(axis=1), d) and np.allclose(T.sum(axis=0), d), name
        assert np.allclose(np.diag(T), 0) and (T >= -1e-12).all(), name
    return mats


# ---------- evaluation ----------

def evaluate(mats):
    lam_u, fixed_uniform, _ = best_topology(uniform_tm(N, D), D)  # chosen once, never changed
    fixed_db = de_bruijn(N, D)
    print(f"fixed uniform-optimal topology: lam on uniform = {lam_u:.4f}")
    rows, chosen = [], {}
    for name, T in mats:
        lam, X, gap = best_topology(T, D, time_limit=600)
        assert gap <= 1e-4, f"{name}: not solved to optimality (gap {gap})"  # Gurobi's default tolerance
        lam_check, _ = concurrent_flow(X, T)  # independent re-check with Part 1's LP
        assert abs(lam - lam_check) < 1e-5, (name, lam, lam_check)
        r = {
            "matrix": name,
            "adaptive_lam": lam,
            "mip_gap": gap,
            "fixed_uniform_lam": concurrent_flow(fixed_uniform, T)[0],
            "fixed_debruijn_lam": concurrent_flow(fixed_db, T)[0],
            "parallel_links": int((X >= 2).sum()),
            "distinct_neighbours_avg": float((X > 0).sum(axis=1).mean()),
        }
        rows.append(r)
        chosen[name] = X
        print(f"{name:18s} adaptive={lam:.4f} (gap {gap:.0e})  fixed-uniform={r['fixed_uniform_lam']:.4f}  "
              f"fixed-deBruijn={r['fixed_debruijn_lam']:.4f}  parallel links={r['parallel_links']}")
    return rows, chosen


def write_csv(rows):
    os.makedirs(RESULTS, exist_ok=True)
    path = os.path.join(RESULTS, "part2.csv")
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.1e}" if k == "mip_gap" else round(v, 4)) if isinstance(v, float) else v
                        for k, v in r.items()})
    print("wrote", path)


# ---------- figures ----------

def style(ax):
    ax.grid(axis="y", color="#e4e3df", linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#bdbcb6")
    ax.tick_params(colors=C_MUTED)


def plot_lambda(rows):
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    x = np.arange(len(rows))
    for key, color, label, off in [("adaptive_lam", C_ADAPT, "Adaptive (MILP per T)", 0),
                                   ("fixed_uniform_lam", C_FIXED_U, "Fixed: uniform-optimal", -0.18),
                                   ("fixed_debruijn_lam", C_FIXED_DB, "Fixed: de Bruijn (Part 1)", 0.18)]:
        ax.scatter(x + off, [r[key] for r in rows], s=40, color=color, edgecolors="white",
                   linewidths=1, label=label, zorder=3)
    ax.set_xticks(x, [r["matrix"] for r in rows], rotation=40, ha="right", fontsize=8)
    ax.set_ylabel("Concurrent flow $\\lambda$", color=C_MUTED)
    ax.set_ylim(0, 1.05)
    style(ax)
    ax.legend(frameon=False, fontsize=8, loc="upper left", ncol=3, bbox_to_anchor=(0, 1.13))
    fig.tight_layout()
    path = os.path.join(FIGURES, "part2_lambda.pdf")
    fig.savefig(path)
    plt.close(fig)
    print("wrote", path)


def plot_adapt_example(T, X, name):
    """T and the chosen link counts side by side: the topology follows the demand."""
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4))
    for ax, M, title, fmt in [(axes[0], T, f"Traffic matrix T ({name})", "{:.1f}"),
                              (axes[1], X, "Links x[u,v] chosen by the MILP", "{:d}")]:
        ax.imshow(M, cmap="Blues", vmin=0, vmax=D)
        for i in range(N):
            for j in range(N):
                if M[i][j] > 1e-9:
                    v = M[i][j]
                    ax.text(j, i, fmt.format(int(v) if fmt == "{:d}" else v), ha="center",
                            va="center", fontsize=7, color="white" if v > D / 2 else "#0b0b0b")
        ax.set_title(title, fontsize=9)
        ax.set_xticks(range(N))
        ax.set_yticks(range(N))
        ax.tick_params(labelsize=7, colors=C_MUTED, length=0)
        ax.set_xlabel("destination v", fontsize=8, color=C_MUTED)
        ax.set_ylabel("source u", fontsize=8, color=C_MUTED)
        for s in ax.spines.values():
            s.set_visible(False)
    fig.tight_layout()
    path = os.path.join(FIGURES, "part2_adapt_example.pdf")
    fig.savefig(path)
    plt.close(fig)
    print("wrote", path)


def main():
    os.makedirs(FIGURES, exist_ok=True)
    mats = test_matrices(np.random.default_rng(SEED))
    rows, chosen = evaluate(mats)
    write_csv(rows)
    plot_lambda(rows)
    example = "3 perms, real wts"
    plot_adapt_example(dict(mats)[example], chosen[example], example)


if __name__ == "__main__":
    main()

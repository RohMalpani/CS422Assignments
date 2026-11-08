"""Topologies for Part 1 (uniform traffic).

Each function returns an n x n integer matrix cap, where cap[u][v] is the
number of u -> v links. Every node has exactly d outgoing links.
"""

import numpy as np


def de_bruijn(n, d):
    """Generalized de Bruijn digraph (the submitted Part 1 topology).

    Node u links to (d*u + k) mod n for k = 0, 1, ..., d-1.

    This is the slides' de Bruijn rule ("shift left, append one new digit",
    9-topologies.pdf pp. 48-53) written as arithmetic: shifting a base-d label
    left is multiplying by d, and appending digit k is adding k. With n = d^m
    it is exactly the slides' graph. Taking it mod n makes it work for any n,
    which is required here because n - 1 divisible by d rules out n = d^m.

    Every node reaches every other in at most ceil(log_d n) hops: m steps of
    u -> d*u + k can steer u to any target, as when building a base-d number
    digit by digit.

    In-degree is also d: node v is entered from the u with d*u + k = v (mod n),
    and as u ranges over 0..n-1 the d*n values d*u + k cover each residue d times.

    Self-loops: d*u + k = u (mod n) is possible (always at u = 0 with k = 0, and
    at u = n-1 with k = d-1). A self-loop is a wasted port; we keep it so every
    node still has exactly d outgoing links, as the slides' formal graph does.
    """
    cap = np.zeros((n, n), dtype=int)
    for u in range(n):
        for k in range(d):
            cap[u][(d * u + k) % n] += 1
    return cap


def simple_circulant(n, d):
    """Baseline for comparison: node u links to u+1, u+2, ..., u+d (mod n).

    The obvious "ring with extra chords". With n-1 = d*k, a node reaches d new
    nodes per hop, so the average hop count grows linearly in n (about k/2)
    instead of logarithmically like de Bruijn.
    """
    cap = np.zeros((n, n), dtype=int)
    for u in range(n):
        for a in range(1, d + 1):
            cap[u][(u + a) % n] += 1
    return cap

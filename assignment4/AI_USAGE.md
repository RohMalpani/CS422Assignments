# AI Usage — Assignment 4

AI assistant: Claude (Claude Code), used interactively with the group in the loop, one step at a time.

- **Conceptual guidance:** explaining maximum concurrent flow, deriving the λ ≤ 1/(average hop count) bound and the Moore-style hop bound, and mapping lecture slides to the assignment.
- **Exploration:** proposing candidate Part 1 topologies (circulants, Kautz/de Bruijn) and an LP-based comparison. The group chose the slide-based de Bruijn construction.
- **Code:** drafting the Gurobi LP (`part1/concurrent_flow.py`), the Part 2 MILP (`part2/topology_milp.py`) and its formulation write-up, hose test-matrix generation, topology constructions, the evaluation/plotting script, and LaTeX report text. These were checked against hand-computed cases (complete graph, directed ring, 4 × permutation → λ = 1, uniform → Part 1 bound 0.7). Every MILP topology is re-scored by the independent Part 1 LP.
- **Later revision with Codex:** the assistant proposed and implemented the deterministic loop-rewiring of de Bruijn self-loops, added structural tests, reran the Part 1 LP experiment, regenerated figures, and updated the report. The measured improvement is empirical; no general optimality proof is claimed. The group should review the implementation and interpretation.
- **Decisions and rationale** are logged in `DECISIONS.md`.

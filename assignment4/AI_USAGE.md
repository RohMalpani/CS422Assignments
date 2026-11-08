# AI Usage — Assignment 4

AI assistant: Claude (Claude Code), used interactively with the group in the loop, one step at a time.

- **Conceptual guidance:** explaining maximum concurrent flow, deriving the λ ≤ 1/(average hop count) bound and the Moore-style hop bound, and mapping lecture slides to the assignment.
- **Exploration:** proposing candidate Part 1 topologies (circulants, Kautz/de Bruijn) and an LP-based comparison. The group chose the slide-based de Bruijn construction.
- **Code:** drafting the Gurobi LP (`part1/concurrent_flow.py`), topology constructions, the evaluation/plotting script, and LaTeX report text. All of it was reviewed, run, and checked against hand-computed cases (complete graph, directed ring).
- **Decisions and rationale** are logged in `DECISIONS.md`.

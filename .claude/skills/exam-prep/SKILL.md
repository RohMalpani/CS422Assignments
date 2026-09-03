---
name: exam-prep
description: Guided walkthrough of an assignment's code and design rationale, ahead of the oral exam. Use when the user asks to review/study/prep for the oral exam, walk through the code, or understand "what we built and why" for a given assignment.
---

# exam-prep

Guided walkthrough for CS 422 oral-exam prep. This is **not** a quiz — it does
not test or grade the user. Its job is to surface, in order, what exists in
the codebase and why it exists, so the user is ready to explain any of it
unscripted.

## Arguments

`args` may name an assignment (e.g. `assignment-1`, `2`) or a path. If empty,
infer scope from the repo: prefer whatever assignment directory/script set is
most recently modified (`git log -1 --name-only`, or file mtimes), and say
which scope you picked before proceeding.

## Steps

1. **Establish scope.** Identify the assignment's requirement doc (e.g.
   `assignment-N.pdf`, or the relevant section of `CLAUDE.md`'s course
   context) and the set of code files that implement it. If there's no code
   yet for the requested scope, say so plainly and stop — don't invent a
   walkthrough for code that doesn't exist.

2. **Read `DECISIONS.md`** in full and index entries by the file/function
   pointers in their `**Code:**` line.

3. **Walk the code in dependency order** — input/data handling first, then
   processing/measurement logic, then plotting/output, then the top-level
   orchestrator script last (the order data actually flows, not file-alpha
   order). For each file or logical unit:
   - Summarize what it does in plain terms.
   - Walk through the non-trivial logic (parsing, algorithm choices, edge
     case handling) — enough that the user could explain it, not a line-by-
     line recitation of obvious code.
   - Pull in the matching `DECISIONS.md` entry for the "why." If a piece of
     non-obvious code (a library pick, an algorithm, a magic parameter) has
     **no** matching decision entry, call that out explicitly as a gap — the
     user should either explain it live right now (and you log it to
     `DECISIONS.md`) or flag it as unresolved before the exam.

4. **Tie back to requirements.** Cross-reference each piece against what the
   assignment doc actually asks for, so explanations answer "why does this
   exist" in terms of the assignment, not just "what does this code do."

5. **Close with a review checklist** — a short bullet list of the non-obvious
   design choices in scope, phrased as things the user should be ready to
   defend out loud (e.g. "why RTT is computed as X and not Y", "why this
   geolocation source over alternatives"). Keep it tight — the choices that
   would actually draw a "why did you do it this way" question, not routine
   code.

## Notes

- If multiple group members have separate versions of an assignment (per
  `CLAUDE.md`), confirm which version/branch is in scope before walking it —
  don't silently pick one.
- Stay in plain, spoken-explanation register throughout — this is prep for a
  live conversation, not a written report.

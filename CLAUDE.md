# Project instructions

## Keep the skills current

The skills in `.claude/skills/` are part of the deliverable: they are how the next agent does this
work well. Maintain them while building, not afterwards.

When: at the end of every study (verified or abandoned), and whenever a run teaches something
non-obvious (a tool quirk, a failed check or prediction, a workaround). Update the skills in the
same commit as the work that taught it.

- **Add** the lesson where the next agent will look: tool behaviour ->
  `build-model/references/tool-notes.md`; a convergence pattern -> `convergence-diagnosis.md`; a new
  check -> `check-catalog.md`; a new model -> the tables in `run-case` and `verify-against-reference`.
  Give the symptom, the cause, the fix, and the study that showed it.
- **Refine** advice a later study contradicted or narrowed, and say what changed it. Never leave
  advice the evidence has disproved.
- **Prune** notes the code now enforces (a test or check exists), duplicates, and one-run trivia.
  Git keeps the history.
- **Optimise** for the reader: keep each SKILL.md lean (Anthropic: under 500 lines; ours are 44-164)
  with detail in `references/`; merge overlapping notes; keep each `description` line accurate so the
  skill triggers when it should.
- When a lesson is a trap an agent would plausibly fall into, propose an eval case for it
  (`<skill>/evals/`); ask before adding one.

`tests/test_skill_harness.py` catches the mechanical drift (a registered model missing from the
skill tables, a dead reference link, an oversized SKILL.md); this rule covers the judgement.

List skill changes in the end-of-task summary, one line each. Settings, hooks and agent files still
need the user's approval first.

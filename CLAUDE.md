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

## Write handoff notes often, so sessions can be cleared

Long sessions are what use up the usage limit: in the 2026-11-21 audit of this project's sessions,
calls with more than 400k tokens of context were 66% of all input tokens. Auto-compaction now
triggers at 300k (`autoCompactWindow` in the user's settings), but clearing at a task boundary beats
compacting mid-task, because nothing gets summarised away. A good handoff note is what makes a clear
safe.

**When:** at the end of each task or study step (verified, abandoned, or handed off to a background
run), before starting a run you'll wait on, when the context passes about 200k, and whenever the user
says they're stepping away.

**Where:** a workstream with its own plan file keeps its handoff there, under `## Next session`
(e.g. `local_llm/PLAN.md`). Otherwise it goes in BACKLOG.md as `## Session handoff: <workstream>
(<date>, <time>)`. Several sessions work in this clone at once, so replace only your own workstream's
block, never another session's. Git keeps the old ones.

**What:** facts a fresh session can act on, not a narrative.
1. Running jobs: case, run folder, state, expected finish, how to tell whether it's still alive, how
   to rerun it.
2. What to do when each one finishes.
3. Decisions the user made this session (with the time) and questions still open for them.
4. Uncommitted files, and which session owns them.
5. Next steps, in order.

Use paths and commands that work as written, and absolute times. Link to git, run reports, plan logs
and memory rather than repeating them.

**Then:** commit the handoff with the work it describes (only your own paths), and tell the user in
one line that it's a good point to `/clear`.

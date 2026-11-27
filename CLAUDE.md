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
- **Optimise** for the reader: keep each SKILL.md lean (Anthropic: under 500 lines; ours are 60-300)
  with detail in `references/`; merge overlapping notes; keep each `description` line accurate so the
  skill triggers when it should.
- When a lesson is a trap an agent would plausibly fall into, propose an eval case for it
  (`<skill>/evals/`); ask before adding one.

`tests/test_skill_harness.py` catches the mechanical drift (a registered model missing from the
skill tables, a dead reference link, an oversized SKILL.md); this rule covers the judgement.

List skill changes in the end-of-task summary, one line each. Settings, hooks and agent files still
need the user's approval first.

## Use only information a real project would have

Studies here rehearse contract engineering work, so build each workflow only on information that would
realistically exist for that kind of job (user's rule, 2026-11-22):

- **New design (no hardware):** specifications, datasheets with their tolerances, drawings, standards,
  published correlations.
- **Existing hardware (benchmarking, retrofit, a field problem):** the tests a client would normally run
  (for a motor: back-EMF, phase resistance, inductance; for a structure: a modal tap test), as well as the above.
- **Not:** measurements only a research teardown or a benchmark's answer key provides (e.g. a measured air-gap
  flux map), used to set inputs or to choose between hypotheses.

Tag each input in the case file with its source class. If unsure whether something would be available, treat it
as available and say so in the case. Test data held back for validation is still opened only for the comparison.

## Update the record as results come in

Every finished run updates everything that shows its result, in the same working session, without
being asked. A result that only lives in a run folder or a chat message is not done.

When a run finishes (or a scratch probe changes a conclusion), in this order:

1. **Case file:** a Results block in the header scoring every prediction (HELD, PARTLY or MISSED, with
   the reason). Commit it with the curated run evidence (`scripts/scrub_paths.py`, `git add -f`
   without `*.inp`, `*.dat`, `__pycache__`, large logs; then `tests/test_privacy.py`).
2. **Handoff:** the running-jobs table and the study's state in BACKLOG.md.
3. **Every page that shows the result:**

   | If the result changes... | Update |
   |---|---|
   | a study's answer, numbers or status | its portfolio page (`portfolio/NN-*.md`) and its row in PORTFOLIO.md; a draft page's "answer so far" |
   | a study with HTML reports (`reports/<study>/`) | rebuild them with the study's `build_report.py`; republish the artifact they're published to |
   | the list of studies, models or cases | the README study table |
   | a reference value behind an evaluation task | that task's `solution.md`, `grader.py` and tests |
   | how to do the work (a tool quirk, a failed check) | the skills, as in "Keep the skills current" |

4. **New pages:** when a study's first case is verified and it has no portfolio page, write one
   (marked "Draft" until the study is complete) and add it to PORTFOLIO.md.
5. **Counts and cross-references:** don't write counts that go stale ("eleven studies"); check the
   links you touched.

Files under `site/`, `DASHBOARD.md` and `scripts/make_study_renders.py` belong to the dashboard
session: don't edit them; if a result makes them stale, add one line for that session to BACKLOG.md.

Batch the doc updates per result, not per file: one commit for the run's evidence and case, one for
the pages it changed. Mention the updated pages in one line when reporting the result.

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

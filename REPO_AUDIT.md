# Repository audit: engineering-agent-lab

Measured 2026-11-25, 22:19 EST, at commit `6201097` on `main`. Written as a handoff: an agent with this
repository and no other context should be able to act on it.

## Summary

The engineering method in this repo is sound and should not change: a small generic harness, case files with
predictions written before the run, independent references, saved run evidence, tests that guard privacy and
skill drift. The problems are all about growth. The repo went from nothing to 41 studies, 221 cases, 44,000
lines of Python and 591 commits in eight days, and four things did not scale with it:

1. **There is no single list of studies.** Adding or changing one study means editing about a dozen
   hand-maintained places, under four different numbering schemes that collide. Only two of those places are
   guarded by a test, and those two tests account for eight of the nine recent CI failures.
2. **Committed run evidence is 373 MB and 90 % of all tracked files.** About a third of it is the same data
   written twice, and large arrays stored inside JSON manifests.
3. **Shared solver code lives in whichever study needed it first.** Twenty studies import a solver locator
   from one of two early studies; 31 study files each load a model writer with their own copy of the same code.
4. **The working documents have become expensive to read.** `BACKLOG.md` is 98 KB, was edited in 135 of the
   591 commits, is written to by both sessions, and carries about 380 lines of superseded history.

The recommended order is in [Roadmap](#roadmap). The first two phases are low risk and remove most of the
day-to-day friction. Six decisions belong to the user and are listed under
[Questions for the user](#questions-for-the-user); nothing in phases 0 to 2 depends on them.

## Rules the executing agent must follow

These come from `CLAUDE.md` and from how the repo is used. Breaking them causes real damage.

- **The repository is public** and GitHub Pages serves `docs/`. Portfolio pages hold 186 links to paths under
  `runs/`. Moving or deleting a committed run, case file or portfolio page breaks published links.
- **Two sessions work in this clone at once and share one git index.** Commit your own paths in one command
  (`git add <paths> && git commit -m ... -- <paths>`). Never leave files staged. Never `git add -A`.
  At the time of this audit the other session had 40 modified files in the tree.
- **`site/`, `DASHBOARD.md` and `scripts/make_study_renders.py` belong to the dashboard session.** Do not edit
  them. Phase 5 below is a proposal for that session, not work for you.
- **Settings, hooks and agent files need the user's approval before any change**, and the user wants to see
  each Claude Code configuration change before it is made. This includes `CLAUDE.md`.
- **Do not rewrite git history** or force-push. That is the user's decision (question 1).
- **Run evidence must stay byte-identical** (`.gitattributes`: `runs/** -text`). Do not reformat, re-save or
  "clean up" files in committed run folders.
- **Long solver jobs may be running.** Do not start the full test suite on the workstation without checking
  the running-jobs table in `BACKLOG.md`; with the tools installed, the suite runs real solvers.
- After any refactor of `harness/`, `studies/` or `models/`, prove nothing changed with the checks listed
  under [How to verify a refactor](#how-to-verify-a-refactor).

## What was measured

| Item | Value |
|---|---|
| Age and activity | First commit 2026-11-18; 591 commits, all on `main`; 8 unpushed at audit time |
| Tracked files | 13,153, of which 11,874 are under `runs/` |
| Tracked size | About 440 MB in the working tree: `runs/` 373 MB, `docs/` 26 MB, `site/` 22 MB, `portfolio/` 13 MB |
| Git pack | 162 MB (GitHub reports 172 MB) |
| Local disk, not tracked | `runs/` 7.2 GB (250 folders), `build/` 1.2 GB, `.venv/` 1.4 GB |
| Python, excluding runs | 44,145 lines: `studies/` 12,105, `scripts/` 9,583, `models/` 8,250, `tests/` 4,265, `harness/` 3,201, `site/` 2,855, `validation/` 2,120 |
| Studies and cases | 41 registered studies, 44 model names, 221 case files, 237 committed runs |
| Tests | 388 tests in 55 files; on CI 72 to 90 s, 10 skipped (no solver installed there) |
| CI, last 51 test runs | 42 passed, 9 failed: 8 on the two skill-table tests, 1 on the privacy test |
| Python environments | Three: `.venv` (`requirements-lock.txt`), `~/.venvs/pyleecan` (`models/motor/pyleecan-env.txt`), `~/.venvs/ross` (no pinned file in the repo); plus solvers in WSL |
| Lint, format, type check | None configured, none installed |

Not done in this audit: the full test suite was not run locally (it would compete with running solver jobs);
test coverage was not measured; the site's JavaScript and CSS were not reviewed; not every study module was
read line by line. Findings about study code rest on the harness, six study modules and repo-wide searches.

## What works and should be kept

- **The harness design.** `harness/` is 3,201 lines, generic, and has no study-specific logic in `run.py`,
  `verify.py`, `report.py`, `compare.py` or `optimize.py`. The `Study` and `Backend` interfaces are small.
- **Reproducibility.** Each run saves its case file, model sources and hashes; `harness rerun` reproduces from
  the saved copies. All 217 case files that have a committed run still match that run's saved inputs once
  comments are ignored (checked by parsing both).
- **Guard tests.** `test_privacy.py`, `test_skill_harness.py`, `test_failures_ledger.py` and `test_tasks.py`
  check things an agent would otherwise forget. Extend this pattern; several recommendations below are
  "add a guard test".
- **The rule that `validation/` must not import from `models/`.** No violation was found.
- **Pinned environments.** `.venv` matches `requirements-lock.txt` exactly.
- **Failed runs kept as evidence**, with `FAILURES.md` and a test that enforces it.

## Findings

Each finding gives the evidence, why it matters, and what to do. They are ordered by how much day-to-day
friction they cause.

### 1. No single list of studies

**Evidence.** One study (the shaft fillet, traced by searching for its name) appears in all of these, each
edited by hand:

| Place | Guarded by a test? |
|---|---|
| `harness/registry.py`: an import list and a second list of `STUDY` objects (changed in 34 commits) | Fails at run time only |
| `README.md` study table | No. Five of the 44 registered models are missing from it: `cadquery_ccx_random`, `cadquery_ccx_random_uq`, `gmsh_ccx_edge_crack`, `openfoam_step_rans`, `ross_rotor` |
| `PORTFOLIO.md` row and `portfolio/NN-*.md` page | No |
| `BACKLOG.md` study table | No |
| `.claude/skills/run-case/SKILL.md` and `verify-against-reference/SKILL.md` tables | Yes |
| `site/build_v2.py`: `VP`, `CARDS`, `GROUPS`, `SLUG`, `CASES`, `DRAWINGS`, `QUESTION` and more | The build fails on dead links only |
| `site/extras.py`: `REQS`, `STUDY_DOCS`, `RUN_PREFIX`, `RUN_LIST` | No |
| `scripts/make_figures.py`, `scripts/make_drawings.py` | No |

The studies also have four identifiers that do not agree:

- the `BACKLOG.md` number (1 to 16) and, for some, a letter (C to H);
- the portfolio page number (01 to 27);
- the site key (`fea`, `cfd`, `heat`, `pv_nozzle`);
- the study module and model names (`cantilever`, `channel_flow`, `ccx_shaft_fillet`).

"Study N" is used for both the first and the second, and they collide. "Study 11" is the heated channel in
`tasks/README.md` (portfolio page 11) and natural convection in `tool-notes.md` (backlog 11). "Study 12" is
the bracket optimisation in `site/extras.py` and the O-ring in `tool-notes.md`. "Study 13" is the strut in
`tool-notes.md` and the cracked plate in `BACKLOG.md`.

**Why it matters.** This is the main source of the "update every page" work that `CLAUDE.md` describes as a
manual procedure, and of stale tables. An agent reading "study 12" cannot know which study is meant.

**Recommendation.** Add one catalog file, `catalog.toml` at the root, with one table per study:

```toml
[shaft_fillet]                      # the key is the canonical id: the study module name
title = "Shaft shoulder fillet"
page = "26"                         # portfolio page number, the only public number
portfolio = "portfolio/26-shaft-shoulder-fatigue.md"
site_key = "shaft"
discipline = "structures"
status = "done"                     # planned | in_progress | done
models = ["ccx_shaft_fillet"]
cited_runs = ["<run id>", "..."]    # the runs the pages and figures quote
aliases = ["backlog 16"]            # old names, so searches still land here
```

Do it in two steps so nothing breaks:

1. **Check only.** Write the catalog and `tests/test_catalog.py`: every registered study is in the catalog and
   the reverse; every `portfolio` file exists; every `cited_runs` folder is committed; every registered model
   is in the README table. No other file changes.
2. **Then generate.** Replace the two hand lists in `harness/registry.py` with discovery of `STUDY` objects in
   `studies/` (`pkgutil.iter_modules`; note `flag_csm` exports two, `STUDY` and `STUDY_CSM3`). Generate the
   README study table between marker comments. Have the figure scripts read `cited_runs` instead of the 72
   run ids now hardcoded across `scripts/`, `site/` and `reports/` (54 in `make_figures.py` alone).

Retire "study N" in favour of the catalog key plus the portfolio page number. Rename as files are touched;
do not do a bulk search-and-replace across committed run folders.

### 2. Committed run evidence is growing without a budget

**Evidence.** `.gitignore` and `runs/README.md` say run folders are ignored and a "curated example" is
committed by hand. In practice 237 of the 250 run folders on disk are committed. What is in them:

| Content | Size | Files | Note |
|---|---|---|---|
| `manifest.json` | 62.2 MB | 233 | Up to 4.1 MB each |
| `point.json` | 54.6 MB | 951 | **Identical to the entry in the manifest's `points` list** (confirmed by comparing them) |
| `response.png` | 91.2 MB | 878 | About 104 KB each; embedded by 186 `report.md` files |
| Solver logs (`.log`, `log.foamRun`, preCICE logs) | about 75 MB | about 1,600 | |
| `history.csv`, other CSV | 22 MB | 636 | |

The large manifests come from arrays stored as JSON under `solver_outputs`: `shell_lines` and `head_lines`
at about 180 KB each per point in the vessel-head runs, `ops` at 123 KB per point in the motor look-up-table
runs. Eighteen cases have two or more committed runs.

Committing is a hand-typed `git add -f` with exclusions listed in `CLAUDE.md`. Nothing limits the size.

**Why it matters.** The pack grew 162 MB in eight days. A clone is already slow for a reviewer, which works
against the portfolio's purpose. The cost of fixing it rises with every run.

**Recommendation.**

1. **Stop writing point data twice.** In `harness/run.py`, keep `label`, `parameters`, `status` and `metrics`
   per point in the manifest and leave the rest in `point.json`. Readers of the manifest (`verify.py`,
   `report.py`, `compare.py`, `rerun.py`, `site/`, `scripts/`) must be checked and updated; old runs keep the
   old shape, so readers need to accept both.
2. **Move arrays out of JSON.** A backend returning an array longer than, say, 200 values under `outputs`
   should have it written to a side file (`points/<label>/outputs.npz` or CSV) with a pointer in the JSON.
3. **Replace the hand-typed commit with a command**, `python -m harness publish runs/<id>`: scrub paths
   (`harness/privacy.py`), select files from an explicit allowlist, refuse a file over a size limit, run the
   privacy test, and print the `git add -f` line. The allowlist becomes the definition of "curated".
4. **Add a size budget test**: fail when a committed run folder or a single committed file exceeds a limit
   (suggested 10 MB and 1 MB; existing runs listed as known exceptions).
5. **Make `response.png` smaller** at the source (`harness/plotting.py`): lower resolution or an optimised
   palette. It cannot be dropped, because the reports embed it.
6. **Decide what happens to a superseded run** (question 1).

Old committed runs stay as they are. These changes apply to new runs.

### 3. Shared solver code lives inside individual studies

**Evidence.**

- `find_ccx` is defined in `studies/fin.py` and imported from there by 9 other studies, 2 scripts and
  3 test files. `find_freecadcmd` is defined in `studies/cantilever.py` and imported by 11 studies, 4 scripts
  and 2 test files. Most of these imports sit inside `__init__` to avoid import cycles.
- `read_dat_blocks` is imported from `studies/strut_buckling.py` by 7 studies; `read_dat_temperatures` from
  `studies/fin.py` by the cold plate.
- A five-line `_load_writer` function (load a model writer from a saved file path) is copied into 18 files;
  `importlib.util.spec_from_file_location` appears in 31 study files and 15 test files.
- Every CalculiX backend repeats the same steps by hand: make a temporary folder, build the mesh, write the
  deck, call `ccx` with `subprocess.run`, collect the log, decide which files to keep, return a failure dict.
  `harness/backend_base.py` has a shared base class for Modelica only.
- `harness/plotting.py` (602 lines) holds one figure function per early study (`quarter_car_bump_figure`,
  `fin_figure`, `strap_figure`, ...). The generic layer depends on study details.

**Why it matters.** A fix to how CalculiX is called, timed out or logged must be made in about 20 places,
and each new study starts by copying the previous one's boilerplate.

**Recommendation.**

1. `harness/tools.py`: `find_ccx`, `find_freecadcmd`, `find_omc`, `find_blender`, and `load_module(path, name)`.
   Leave re-exports in `studies/fin.py` and `studies/cantilever.py` so nothing breaks, then update importers.
2. Move `read_dat_blocks` and `read_dat_temperatures` into `harness/calculix.py`, same re-export approach.
3. `CalculiXBackend` base class next to `ModelicaBackend`: work folder, `run_ccx(job, timeout)` with log
   capture, the kept-files list, `fail()`, and `tool_versions()`. Convert studies one at a time, newest
   first, since the newest ones (`shaft_fillet`, `oring_seal`) already share a shape. Do the same for the
   OpenFOAM backends after reading two of them; this audit did not compare them in detail.
4. Move the study-specific figure functions out of `harness/plotting.py` into their studies. Lowest priority.

Keep one behaviour exactly: a backend loads its writer from the copy saved in the run's `inputs/` folder when
there is one. That is what makes `harness rerun` reproduce an old run with the model as it was.

### 4. The working documents are large, shared and partly history

**Evidence.** `BACKLOG.md` is 960 lines and 98 KB, roughly 25,000 tokens per read. It holds the study plan
table, install notes, one long session handoff with "Done" logs going back to 2026-11-21 (lines 211 to 344),
and a section headed "Earlier notes (history: the summary above supersedes anything here that disagrees)"
from line 689 to 933. It was edited in 135 commits by two sessions. The project's own usage audit found that
context length is what uses up the usage limit.

The root also holds `DASHBOARD.md` (50 KB, 55 commits), `FAILURES.md`, `PORTFOLIO.md`, `CAD-TOOLS.md`,
`LINKEDIN_HANDOFF.md` and `README.md`: reader-facing pages and working notes mixed together.

`CLAUDE.md` says the skill files are "44-164" lines; they are 60 to 290. It is the kind of stale count the
same file warns against.

**Recommendation.** Split by purpose and by owner:

- `BACKLOG.md`: the plan table and open items only. Target under 150 lines.
- One handoff file per workstream, replaced rather than appended, for example `handoff/studies.md` and
  `handoff/dashboard.md`. This also ends two sessions editing one file.
- Delete the superseded history and the "Done" logs. Git keeps them.
- Move the install notes (preCICE, OpenFOAM v2512) to `CAD-TOOLS.md`.
- Put working notes in one folder (suggested `project/`: backlog, dashboard backlog, failure ledger,
  handoffs) and leave `README.md`, `PORTFOLIO.md` and `CLAUDE.md` at the root. `docs/` is not available: it
  is the published site. `tests/test_failures_ledger.py` reads `FAILURES.md` by path and must move with it.
- `CLAUDE.md` names `BACKLOG.md` as the handoff location, so it changes too. Show the user the edit first.

### 5. `scripts/` is the second-largest code area and has no structure

**Evidence.** 34 files and 9,583 lines in one flat folder: figure builders (`make_figures.py` is 2,258 lines,
`make_drawings.py` 1,422), render drivers, eleven `motor_*` analysis scripts, and repo tools (`scrub_paths.py`,
`list_failures.py`). Forty-three `sys.path.insert` lines in 31 files across `scripts/`, `site/`, `reports/`,
`validation/`, `tasks/` and `tests/` make imports work. There is no index of what each script produces or in what order to run them.
`pyproject.toml` has no build system or package list, so nothing is importable without those lines.

**Recommendation.**

1. Add a `[build-system]` and a package list (`harness`, `studies`, `models`, `validation`, `excitation`) to
   `pyproject.toml` and install with `pip install -e .`. Then delete the `sys.path` lines. Do not add
   `site`, `scripts` or `tests` as packages; `site` would shadow a standard-library module.
2. Group the folder: `scripts/figures/`, `scripts/renders/`, `scripts/motor/`, `scripts/tools/`. Update the
   paths quoted in `README.md`, `site/README.md` and the skills in the same commit.
3. Add `scripts/README.md`: one line per script with what it writes and what it needs.
4. Do not rename the top-level packages or move to a `src/` layout. Run manifests record repo-relative
   source paths, the skills quote paths, and the gain does not cover the breakage.

### 6. Two sessions commit straight to `main`, and checks run after the push

**Evidence.** 591 commits in eight days, all on `main`, from two sessions sharing one working tree and index.
Nine of the last 51 CI test runs failed. Eight were the two skill-table tests, a check that takes seconds
locally. The ninth was `test_no_committed_file_contains_a_personal_path`: because the check runs after the
push, that file was already in the public repository when it failed. There are no pytest markers, so with solvers installed the only local option is the
whole suite. 279 commit subject lines are over 150 characters and 77 are over 300, so `git log --oneline` is
hard to scan. A second worktree (`engineering-agent-lab-ui`, branch `ui-redesign`) exists and is fully merged.

**Recommendation.**

1. Add pytest markers (`solver` for tests that start an external tool) and a `tests/conftest.py` with shared
   tool-detection fixtures; the detection is repeated per test file today.
2. Add one fast command, `python -m pytest -m "not solver" -q`, and name it in `CLAUDE.md` as the check to
   run before each commit. A git pre-commit hook would enforce it, but hooks need the user's approval.
3. Commit subjects of 72 characters or fewer, detail in the body.
4. Give the second session its own worktree, as was done for `ui-redesign` (question 4).

### 7. Site: output committed beside its source, and numbers typed by hand

For the dashboard session. Do not act on this from a study session.

**Evidence.** `site/v2/` and `docs/v2/` hold the same 226 files, byte for byte; outside `runs/`, 162 files
over 50 KB are tracked at two paths (22.8 MB). `docs/` is build output, committed because Pages serves it
from `main`. `site/studies/*.html` contain about 1,036 numbers with units typed by hand, and `extras.REQS`
re-types each requirement's limit and result, which already exist in the case file and in the run's
`report.json`. `site/index_v1.html`, `contact_section.html` and `heat_section.html` are kept "for reference
only".

**Recommendation.** Read `REQS` values from `report.json` by run id and metric name (the build already fails
on dead links, so failing on a missing metric fits). Consider publishing Pages from a GitHub Actions build so
`docs/` leaves the tree (question 5). Delete the three reference-only files; git keeps them.

### 8. Tooling and dependencies

**Evidence.** No linter, formatter or type checker. `ross` and PyMuPDF (`fitz`) are imported by tracked code
but are in neither `pyproject.toml` nor a lock file in the repo; the ROSS environment (`~/.venvs/ross`) has
no pinned file at all. CI runs on Windows only, which matches the workstation.

**Recommendation.** Add `ruff` to the `dev` extra with a `[tool.ruff]` section (line length 120, matching
the code) and run `ruff check` in CI. Start with the default rules and fix or ignore per file; do not run the
formatter across the repo in one commit while two sessions are active. Add `models/rotor/ross-env.txt`,
frozen from the environment that produced the rotor runs, beside the Pyleecan one.

### 9. Smaller items

- **README.** "First implementation milestone", "Suggested first skills" and "Handoff prompt for a new project
  chat" date from the project's first day. The folder list omits `site/`, `docs/`, `scripts/`, `reports/`
  and `build/`. The "Since added" paragraph is a hand-kept changelog.
- **`skills/README.md`** is a status table for skills that live in `.claude/skills/`. Fold it into the
  README or delete it.
- **`validation/`** mixes importable reference modules with per-study data and notes
  (`validation/motor_ornl/` has plans, client data, results and a `.npy` file). Move the data folders to
  `validation/data/` so the code folder holds only code.
- **`reports/motor/`** commits five built HTML files (3.2 MB) beside the script that builds them.
- **`excitation/`** is one file. It can stay; it is not worth a move.
- **`tool-notes.md`** is 756 lines in one file and changed in 47 commits. Split it by tool
  (`references/tools/calculix.md`, `openfoam.md`, `femm-pyleecan.md`, `precice.md`, ...) so an agent loads
  only the solver in use. Update the links; `test_skill_harness.py` checks them.
- **Case files.** 34 % of all case-file lines are comments (8,322 of 24,351), because the header carries the
  method, predictions and results. That is deliberate and should stay. Two gaps: no test checks that a case
  file's settings still match its run's saved inputs after the Results block is added (they do today, 217 of
  217; add the test), and variants are full copies (29 enclosure cases repeat a 55-line header and differ in
  two or three values). An `extends = "<base case>"` key in `harness/case.py`, with the resolved file written
  to `inputs/case.toml`, would remove the copies. Grouping `cases/` into per-study folders is worthwhile
  but breaks links; leave it until the catalog exists.
- **Test file names** do not map to study names (`test_channel.py` for `channel_flow`,
  `test_oring_reference.py` for `oring_seal`), so coverage per study cannot be read from the file list.
  The catalog can carry a `tests` field.
- **Local disk.** `runs/` is 7.2 GB and `build/` 1.2 GB with no clean-up rule.

## Target layout

Only the changes from today are marked.

```
README.md  PORTFOLIO.md  CLAUDE.md  pyproject.toml  requirements-lock.txt
catalog.toml                  NEW   one table per study
harness/
  tools.py                    NEW   solver locators, load_module
  backend_base.py                   + CalculiXBackend, OpenFOAM base
  calculix.py                       + read_dat_blocks, read_dat_temperatures
studies/  models/  excitation/
validation/                         reference code only
  data/                       NEW   per-study data and notes (motor_ornl, enclosure, ...)
cases/                              flat for now
runs/                               new runs written through `harness publish`
tests/
  conftest.py                 NEW   markers, shared tool fixtures
  test_catalog.py             NEW
scripts/
  figures/ renders/ motor/ tools/   NEW grouping, README.md
site/  docs/  portfolio/  reports/  tasks/  local_llm/
project/                      NEW   BACKLOG.md, DASHBOARD.md, FAILURES.md
handoff/                      NEW   one file per workstream
.claude/skills/build-model/references/tools/   NEW   tool-notes split by tool
```

## Roadmap

Each phase is independent of the later ones and leaves the repo working.

| Phase | Work | Risk | Done when |
|---|---|---|---|
| 0. Guards and quick fixes | pytest markers and `conftest.py`; test that case settings match run inputs; `ruff` config, check only; add the five missing models to the README table; fix the stale skill-length range in `CLAUDE.md` (show the user first) | Low | Fast test command runs in under two minutes locally without starting a solver; CI green |
| 1. Catalog, check only | `catalog.toml`, `tests/test_catalog.py` | Low | The test passes and fails when a study is added without a catalog entry |
| 2. Shared solver code | `harness/tools.py`; move the `.dat` readers; `CalculiXBackend`; convert studies one per commit | Medium | See "How to verify a refactor" |
| 3. Evidence diet | Manifest and point split; arrays to side files; `harness publish`; size budget test | Medium | A new motor look-up-table run commits under 1 MB of JSON; old runs still verify and report |
| 4. Working documents | Split `BACKLOG.md`; per-workstream handoffs; split `tool-notes.md`; update `CLAUDE.md` | Low, needs approval | `BACKLOG.md` under 150 lines; skill link test passes |
| 5. Generated tables and site | Registry discovery; README table generated; figure scripts read `cited_runs`; site `REQS` from `report.json` | Medium; site part is the dashboard session's | Adding a study touches the study module, its cases, its catalog entry and its pages, and nothing else |
| 6. Optional | Package install and removal of `sys.path` lines; `scripts/` grouping; case `extends`; worktree per session | Medium | Agreed with the user first |

### How to verify a refactor

Before starting phase 2 or 3, pick three committed runs as references, one per tool chain: a Modelica run
(`msd_step_modelica`), a CalculiX run (`fin_mesh` or `shaft_fillet_mesh_r2`) and an OpenFOAM run
(`channel_mesh`). Then, after each commit:

1. `python -m pytest -q` on the tests for the touched study, and the fast suite.
2. `python -m harness rerun runs/<reference run>` prints `REPRODUCIBILITY PASS`.
3. `python -m harness report runs/<an old committed run>` still builds, and `git status` shows no change to
   any committed file under `runs/`.
4. `python -m pytest tests/test_privacy.py tests/test_skill_harness.py tests/test_failures_ledger.py -q`.

Check the running-jobs table in `BACKLOG.md` before step 2; a rerun starts a solver.

## Questions for the user

1. **Run evidence.** Is every run meant to be public, or only the runs the pages cite? If only the cited
   ones, superseded runs can be removed from the tree as new ones land. Separately: leave the existing
   history alone (recommended), or rewrite it once to shrink the clone? A rewrite needs a force-push to a
   public repository and a fresh clone for every session and worktree.
2. **Portfolio pages and the site.** `portfolio/*.md` and `site/studies/*.html` both describe each study by
   hand. Is the site the public face and the Markdown pages a secondary record, or are both first-class?
   The answer decides how much of the "update every page" work can be generated.
3. **Study identifiers.** Is it acceptable to make the study module name the one identifier, keep the
   portfolio page number as the only public number, and retire the backlog numbers and letters?
4. **Two sessions.** Should the dashboard session move to its own git worktree, as `ui-redesign` did? It
   ends the shared-index problem. The study session would keep this folder because it holds the 7.2 GB of
   local runs. Also: can the merged `ui-redesign` branch and its worktree be removed?
5. **Pages deployment.** Publish from a GitHub Actions build so `docs/` is no longer committed, or keep
   `docs/` on `main` for simplicity?
6. **Clean-up approvals.** May these be deleted: `LINKEDIN_HANDOFF.md` (its own text says to delete it when
   the profile is done), `site/index_v1.html`, `site/contact_section.html`, `site/heat_section.html`,
   `skills/README.md`? And is a pre-commit hook that runs the fast tests acceptable?

## How the numbers were produced

All from the repository at `6201097`, with `git ls-files`, `git ls-tree -r -l HEAD`, `git count-objects -vH`,
`git log`, `wc -l`, `grep`, `du -sh`, `pytest --collect-only`, `gh run list` and `gh run view --log-failed`.
Two short Python checks parsed files: one compared every `cases/*.toml` with the `inputs/case.toml` of its
latest committed run, the other compared a manifest's `points` entry with the matching `point.json` and
listed the largest keys in the two largest manifests.

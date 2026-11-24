---
name: build-model
description: Add a new verified simulation study or model to this repo's harness: model source (Python, Modelica, FreeCAD, CadQuery, OpenFOAM case writer), backend, metrics, independent reference, numerical and validity checks, plots, tests, and a first evidence run. Use whenever the user wants to model a new problem, add a tool path, add a second model of an existing problem, extend a model (new geometry, boundary condition, 3D version), or when run-case says a model is not supported yet. Also use to diagnose a study whose checks fail or whose mesh convergence looks wrong.
---

# Build a model

Adds a study that the existing skills can run (`run-case`), check
(`verify-against-reference`), and report (`requirements-report`). The case file
should already exist from `frame-requirements`; if it does not, do that first,
because the checks and tolerances come from it.

The goal is not a model that runs. It is a model whose every reported number is
backed by an independent check, and whose failure modes are caught by the
checks before a reviewer catches them.

## Where things go

| File | Role | Rule |
|---|---|---|
| `models/<area>/<name>.py` (or `.mo`, `.sh`) | model under test: geometry, equations, case writer | listed in the backend's `sources`, so it is copied into each run's `inputs/` and hashed |
| `validation/<name>.py` | independent reference (closed form, exact series, correlation) | must not import from `models/`; the reference cannot share the model's mistakes |
| `studies/<name>.py` | `Backend` (runs the tool) and `Study` (metrics, checks, plots) | one module per family of problems; `STUDY = ...` at the bottom |
| `harness/registry.py` | maps the case's `model` name to (study, backend) | add the study to `_studies()` |
| `harness/plotting.py` | evidence figures | dataviz palette constants at the top of the file |
| `tests/test_<name>.py` | reference unit tests, parser tests, one small end-to-end run | the end-to-end test skips when the tool is not installed |

Read `harness/study.py` and one existing study close to the new one before
writing (`studies/channel_flow.py` for an external solver with files,
`studies/mounting_plate.py` for an in-process library, `studies/quarter_car.py`
for time-domain ODEs).

### Backend contract

`solve(params, numerics)` returns
`{"success", "message", "nfev", "series", "outputs", "files", "cleanup"}`:

- `series`: arrays saved to `points/<label>/<series_file>` (time histories, nodal
  or cell results).
- `outputs`: scalar results (solver diagnostics, patch-integrated values) saved
  in `point.json` as `solver_outputs` and passed to `compute_metrics`.
- `files`: native solver files to keep (input deck, logs, native model file);
  keys may contain subfolders. Return them on failure too: a failed run's logs
  are evidence.
- `prepare(source_dir=...)` must load model sources from `source_dir` (the run's
  saved `inputs/`), so `harness rerun` reproduces with the saved model, not the
  current one. Load Python model sources with `importlib.util.spec_from_file_location`.

### Study contract

- `derive(params)`: validate inputs (raise `ValueError`) and compute reference
  values from `validation/`.
- `compute_metrics(series, params, case, outputs)`: requirement metrics from what
  the model produced, measured back from the result, never copied from the
  design intent (the mounting plate measures holes from the B-rep, not from the
  parameters).
- `verify_point(...)`: returns a list of `check(id, description, value, tolerance,
  kind)`; `kind="validity"` for assumption checks. Writes `response.png`.
- `verify_run_level(...)`: checks needing several points (GCI). Add
  `| {"metric": metric}` to a check so a failure withholds verdicts on that
  metric only.

## Choosing checks

Each requirement metric needs at least one independent reference. Beyond that,
cover four questions; the catalog in
[references/check-catalog.md](references/check-catalog.md) lists what was used
per problem type:

1. **Solved correctly?** Exact or closed-form reference, conservation (mass,
   energy, force balance), solver and iterative convergence.
2. **Resolved enough?** Mesh or time-step convergence with an observed order
   (GCI over the three finest levels).
3. **Right everywhere, not only on average?** Compare a field (profile, full
   velocity field, nodal deflection), not only an integral. In the 3D duct
   study an inverted mesh grading passed the pressure-gradient check on the
   finer meshes; only the field comparison exposed it.
4. **Valid for this point?** One validity check per assumption that can fail
   (wheel lift, yield, small deflection, laminar, fully developed).

## Procedure

1. **Reference first.** Write `validation/<name>.py` and unit-test it before any
   model exists: known textbook values (square-duct fRe = 14.227), limits (wide
   duct → parallel plates), self-consistency (the exact field integrates back to
   the mean velocity). A wrong reference makes every check meaningless.
2. **Model source.** Write the model or case writer. Generated text must not
   contain numpy reprs: cast to `float` before formatting (`np.float64(0.5)`
   breaks OpenFOAM dictionaries).
3. **Audit the model against the drawing, part by part, before any run that matters.** Make a table: every
   dimension and material value the model uses, its value in the model, its value in each design source, and
   where they differ. Templates impose simplifications silently: Pyleecan's V-pocket template (HoleM50) makes the
   magnet as thick as its pocket, so study 7's magnet filled a 6.80 mm pocket where the drawing has a 5.31 mm magnet
   and 1.5 mm of air. That one difference was most of a 24 % blind error, found two days later. Each difference
   gets a run or a hand estimate of what EXACTLY changes (study 7's dismissal estimate thinned the pocket with the
   magnet, -0.4 %; the real change leaves air in series, -23 to -28 %). A difference the template cannot represent
   is an assumption in the case file with its estimated effect, not a silent default.
   How to make the audit complete (study 7's audit, `validation/motor_ornl/DRAWING_AUDIT.md`): list every label on
   the drawing and mark the ones the model does not use (study 7: 12 of 23, most on the stator's mounting ears, but
   also a second bridge value and the hub keys), and unlabelled features too (the magnet stops); render the whole part, not only the sector you measured (one
   rotor view settled "is there a centre rib?"); check what the solver leaves out of the template, not only what
   the template draws (Pyleecan leaves the shaft unmeshed, so a steel hub ring that the designer's own model
   counted as rotor iron was missing); and for each such gap, read the saved field (flux density in the region)
   before estimating it: unsaturated iron in parallel changes little. Mark which inherited values are used at all
   (Pyleecan's end-winding length is not; the efficiency study computes its own).
   Each audit row's status belongs to the revision audited: write the revision in the status, and re-audit the
   "differs" rows when the geometry changes. Study 7 nearly queued a revision for the magnet stops from a row written
   on revision 4's template pocket; an overlay of revision 5 on the drawing (`scripts/motor_drawing_stops.py`) showed
   the traced pocket already put every magnet on its stop.
4. **Run the tool by hand once**, outside the harness, on a coarse setup: does it
   mesh, does the mesh check pass, does it converge, where are the outputs?
   Tool-specific traps are in [references/tool-notes.md](references/tool-notes.md).
5. **Backend and study.** Register the study. Parse results from the tool's own
   files where possible.
   Every case parameter that names an input (a machine file, a mesh, a table run) must
   be read from the case, never from a module constant: study 7's rotor study loaded
   its first machine file whatever the case named, unnoticed for two days because
   every case named that file. Check that changing the parameter changes the run.
6. **Smoke test into the scratchpad**, never into `runs/`:
   `run_case(Path("<scratch>/case.toml"), runs_root=Path("<scratch>/runs"))` with
   the sweep cut to the coarsest point, then `verify_run`. Look at every check
   value and at the figures. The smoke test exists to find problems with the
   setup before an evidence run: a metric that measures the wrong thing, a
   convergence criterion that can never pass, a plot that misleads.
7. If the smoke test changes the case (metric definition, convergence criterion),
   record it in the case header per `frame-requirements` before the evidence run.
8. **Evidence run:** `.venv/Scripts/python.exe -m harness pipeline cases/<name>.toml`.
9. **Read it critically.** Compare the observed order of convergence with the
   method's design order, find where the maximum error sits, and check every
   figure. Symptoms and causes are in
   [references/convergence-diagnosis.md](references/convergence-diagnosis.md).
10. **When a check fails, classify it** before changing anything:
   - Model or setup bug (wrong grading, wrong face, wrong sign): fix the code,
     keep the failed run, rerun, and record the history in the case header.
   - Model limit (validity failure, singularity in the metric): the model is the
     wrong tool for that point; revise the scenario or the model
     (`frame-requirements`, "Revising a case").
   - Tolerance: never loosen it to pass.
11. **Tests:** `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider`.
12. **Docs:** add the model to the tables in `run-case` and
    `verify-against-reference`, the README studies table, and PORTFOLIO if it is a
    portfolio piece.
13. **Commit curated evidence** with `git add -f`, leaving out bulky result CSVs,
    long solver logs, and `__pycache__`. Always keep `manifest.json`, even over the
    size limit (a 13-point dq table's is 2-3.5 MB): `harness rerun` and `verify`
    need it. Check it for local paths first.

## Human judgment needed

Which simplifications are acceptable, what a model-form tolerance should be,
and whether a failed check is a bug or a limit of the model. Report the
evidence and the classification; let the user decide on anything that changes
scope.

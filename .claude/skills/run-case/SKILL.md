---
name: run-case
description: Run an engineering simulation case from a TOML case file and capture reproducible evidence in runs/. Use when the user asks to run, execute, simulate, sweep, or rerun a case (e.g. cases/msd_step.toml), or to reproduce a previous run directory.
---

# Run a case

Executes a case file through the harness and preserves inputs, environment,
solver diagnostics, time series, and metrics. Does not judge correctness; that
is the `verify-against-reference` skill.

## Supported

| `model` in case file | Tool | Source |
|---|---|---|
| `msd` | SciPy `solve_ivp` | `models/msd.py` |
| `msd_modelica` | OpenModelica 1.26.3 (omc, DASSL) + Modelica Standard Library 4.1.0 | `models/modelica/EngLab.mo` (`EngLab.MSDStep`) |

- Python 3.14 in `.venv` (numpy, scipy, matplotlib pinned in `requirements-lock.txt`).
- For `msd_modelica`, the harness finds `omc` via `OPENMODELICAHOME` or
  `C:/Program Files/OpenModelica*/bin`. It compiles the model once per run, then runs
  the executable for each point. Model parameters are passed with `-override`; stop
  time, step size, tolerance, and solver are passed as their own flags
  (`-stopTime`, `-stepSize`, `-tolerance`, `-s`), because OpenModelica 1.26 silently
  ignores them inside `-override`. The harness rejects any output that is not on the
  requested time grid.
- If MSL is missing, omc's build log (`<run_dir>/build/omc_build.log`) will say
  `Failed to load package Modelica`. Install it with an omc script containing
  `installPackage(Modelica);`, and tell the user.

For any other model, stop and tell the user it is not supported yet. Do not
improvise a new model inside this skill.

## Inputs

A case file under `cases/` with `[case]`, `[parameters]`, optional `[sweep]`,
`[numerics]`, `[metrics]`, `[verification]`, and `[[requirements]]`. See
`cases/msd_step.toml`.

## Procedure

Run every command from the repository root.

1. **Check the environment.** Run `.venv/Scripts/python.exe --version`. If `.venv` is missing,
   recreate it with Python 3.14 and `pip install -r requirements-lock.txt`, and tell the user.
2. **Read the case file** and restate to the user, briefly: the parameters (with units), the
   sweep, the numerical settings, and the requirements. If units are missing, if a requirement
   is not measurable, or if the verification tolerances are absent, stop and ask. Tolerances
   must exist **before** the run.
3. **Run.**
   - New run: `.venv/Scripts/python.exe -m harness run cases/<case>.toml`
   - Run + verify + report in one step: `.venv/Scripts/python.exe -m harness pipeline cases/<case>.toml`
   - Reproduce an earlier run: `.venv/Scripts/python.exe -m harness rerun runs/<run_id>`
4. **Read the output.** The last lines are `RUN_DIR <path>` (and `REPRODUCIBILITY PASS|FAIL` for
   rerun). Exit code 0 means all points completed, 1 means some failed, and 2 means bad input.
5. **Inspect `<run_dir>/manifest.json`.** Report the status per point. For any point with
   status `failed`, quote its `error` or `solver.message` and the relevant lines of `run.log`.

## Artifacts

`runs/<run_id>/`: `inputs/case.toml`, `manifest.json`, `run.log`,
`points/<label>/{timeseries.csv, point.json}`; for Modelica, also `inputs/EngLab.mo` and
`build/{build.mos, omc_build.log}`. See `runs/README.md`.

If a point fails with `output grid mismatch`, the executable ignored the requested time
settings. Check the flags in `harness/backends.py` against `<exe> -help`. Do not relax
the grid check.

## Failure handling

- Never delete or overwrite a run directory, including failed ones. Failed runs are evidence.
- Do not change the case's tolerances or requirements to make a run pass. If a change is
  justified, edit the case file, say why, and start a new run.
- If a solver fails, report it. Changing `method`, `rtol`, or `atol` is an engineering decision
  for the user to make.

## Human judgment needed

The choice of parameters, assumptions, and acceptance tolerances. A completed run only means the
solver finished. It says nothing about whether the result is correct.

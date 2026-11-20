---
name: run-case
description: Run an engineering simulation case from a TOML case file and capture reproducible evidence in runs/. Use when the user asks to run, execute, simulate, sweep, or rerun a case (e.g. cases/msd_step.toml), or to reproduce a previous run directory.
---

# Run a case

Executes a case file through the harness and preserves inputs, environment,
solver diagnostics, time series, and metrics. Does not judge correctness; that
is the `verify-against-reference` skill.

## Supported

| `model` in case file | Study | Tool | Source |
|---|---|---|---|
| `msd` | mass-spring-damper | SciPy `solve_ivp` | `models/msd.py` |
| `msd_modelica` | mass-spring-damper | OpenModelica 1.26.3 + MSL 4.1.0 | `models/modelica/EngLab.mo` (`EngLab.MSDStep`) |
| `quarter_car` | quarter car | SciPy `solve_ivp` (road `bump` or `iso8608`) | `models/quarter_car.py`, `excitation/road.py` |
| `quarter_car_modelica` | quarter car | OpenModelica + MSL (road `bump` only) | `EngLab.mo` (`EngLab.QuarterCarBump`) |
| `cantilever_freecad` | cantilever FEA | FreeCAD 1.1.4 (`freecadcmd`) + Gmsh + CalculiX 2.22 | `models/fea/cantilever_freecad.py` |
| `cadquery_plate` | mounting plate | CadQuery 2.8 (OpenCASCADE) | `models/cad/mounting_plate.py` |
| `openfoam_channel` | laminar channel flow | OpenFOAM 14 in WSL (blockMesh, checkMesh, foamRun) | `models/cfd/channel_openfoam.py`, `models/cfd/run_channel.sh` |
| `openfoam_duct` | rectangular duct (3D side-wall check) | OpenFOAM 14 in WSL, periodic quarter section | `models/cfd/duct_openfoam.py`, `models/cfd/run_channel.sh` |

The registry is `harness/registry.py`; each study lives in `studies/<name>.py`.

- Python 3.14 in `.venv` (numpy, scipy, matplotlib, cadquery pinned in `requirements-lock.txt`).
- For `cantilever_freecad`, the harness finds `freecadcmd` via `FREECADCMD` or the FreeCAD
  install folder. Each point runs a fresh FreeCAD session (about 4 s at 8 mm mesh, 30 s at
  2 mm). The CalculiX deck, `.dat`, and native `cantilever.FCStd` are kept in
  `points/<label>/solver/`. Nodal results are parsed from the `.frd` file by
  `harness/calculix.py`, not by FreeCAD.
- For `openfoam_channel`, OpenFOAM runs inside WSL. The harness finds the newest
  `/opt/openfoam*/etc/bashrc` (override with `OPENFOAM_BASHRC`; pick a distro with
  `OPENFOAM_WSL_DISTRO`). The Python writer generates the case dictionaries and
  `run_channel.sh` runs blockMesh, checkMesh, foamRun, and writeCellCentres; the
  dictionaries and logs are kept in `points/<label>/solver/`. Fields are read from
  OpenFOAM's ASCII files by `harness/openfoam.py`. Giving `supply_height_mm`,
  `supply_length_mm`, and `contraction_length_mm` adds a supply header and smooth
  contraction ahead of the channel; without them the inlet is an idealized uniform
  velocity at the channel entry (singular inlet corners). If OpenFOAM is missing, stop:
  installing it needs `sudo apt` in WSL, which only the user can do.
- `openfoam_duct` runs a fixed number of iterations (`[numerics] iterations`), not a
  residual target: its p, Uy, and Uz fields are exactly uniform or zero, so their
  normalised residuals never fall. The finest mesh of `duct_side_walls` takes about
  7 minutes. Velocity relaxation above about 0.99 diverges.
- For the Modelica models, the harness finds `omc` via `OPENMODELICAHOME` or
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

A case file under `cases/` with `[case]`, `[parameters]`, optional `[sweep]` (one
`parameter` with `values`, or named `[[sweep.scenarios]]` that each set several
parameters, e.g. tolerance corners),
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
settings. Check the flags in `harness/backend_base.py` against `<exe> -help`. Do not relax
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

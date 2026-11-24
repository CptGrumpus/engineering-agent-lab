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
| `quarter_car_modelica_liftoff` | quarter car, tire that can leave the road | OpenModelica + MSL (road `bump`, `tire_model = "liftoff"`, no bump stop) | `EngLab.mo` (`EngLab.QuarterCarBumpLiftoff`) |
| `cantilever_freecad` | cantilever FEA | FreeCAD 1.1.4 (`freecadcmd`) + Gmsh + CalculiX 2.22 | `models/fea/cantilever_freecad.py` |
| `cadquery_plate` | mounting plate | CadQuery 2.8 (OpenCASCADE) | `models/cad/mounting_plate.py` |
| `cadquery_ccx_strap` | strap with a hole (CAD to FEA) | CadQuery -> STEP -> Gmsh -> CalculiX, plane stress | `models/fea/strap_hole.py` |
| `cadquery_ccx_modal` | bracket modal analysis | CadQuery -> STEP -> Gmsh (C3D10) -> CalculiX *FREQUENCY | `models/fea/bracket_modal.py` |
| `cadquery_ccx_random` | bracket random vibration (study C): base PSD, 3 sigma stress, fatigue | CadQuery -> Gmsh (C3D10) -> CalculiX *FREQUENCY (modal stresses, participation factors) + *STEADY STATE DYNAMICS check; modal superposition in Python | `models/fea/bracket_random.py`, `studies/bracket_random.py` |
| `cadquery_ccx_random_uq` | probabilistic uncertainty on study C (study H): failure probability, Sobol indices | study C's model at several thicknesses (one mesh, z scaled), a surrogate in (log damping, thickness), Monte Carlo / Sobol, FORM and importance sampling (`harness/uncertainty.py`) | `models/fea/bracket_random.py`, `studies/bracket_random_uq.py` |
| `gmsh_ccx_edge_crack` | edge-cracked plate: stress intensity, critical crack, fatigue crack growth life (study F) | Gmsh half model, 6-node triangles at the tip -> CalculiX plane strain; K(a) by energy release rate and crack opening, BS 7910 / IIW growth law | `models/fea/edge_crack.py`, `studies/edge_crack.py` |
| `ross_rotor` | fan rotor critical speeds and unbalance response (study G) | ROSS 3.1 in its own environment (`~/.venvs/ross`): Timoshenko shaft, rigid disc, linear bearings; Campbell diagram, API 684 unbalance | `models/rotor/fan_rotor.py`, `studies/rotor_critical.py` |
| `gmsh_ccx_contact` | roller-on-plate contact | scripted Gmsh .geo (C3D8 slab, plane strain) -> CalculiX surface-to-surface contact | `models/fea/hertz_contact.py` |
| `strap_fatigue` | strap fatigue life (chained) | strap CAD-to-FEA pipeline, then Peterson K_f, SWT, Basquin fit to cited 6061-T6 data | `models/fea/strap_hole.py`, `models/fatigue/sn_6061.py` |
| `openfoam_channel` | laminar channel flow | OpenFOAM 14 in WSL (blockMesh, checkMesh, foamRun) | `models/cfd/channel_openfoam.py`, `models/cfd/run_channel.sh` |
| `openfoam_duct` | rectangular duct (3D side-wall check) | OpenFOAM 14 in WSL, periodic quarter section | `models/cfd/duct_openfoam.py`, `models/cfd/run_channel.sh` |
| `ccx_fin` | heat-sink fin, 3D steady conduction | CalculiX 2.22 (`ccx.exe` bundled with FreeCAD), structured C3D8 deck written in Python | `models/thermal/fin_ccx.py` |
| `openfoam_heated_channel` | heated coolant channel (thermal entry) | OpenFOAM 14 in WSL, flow then scalarTransport on the frozen flow | `models/cfd/heated_channel_openfoam.py`, `models/cfd/run_heated.sh` |
| `openfoam_ccx_cold_plate` | cold plate, full thermal chain | OpenFOAM coolant CFD coupled to CalculiX plate conduction (Robin-Neumann, Aitken), then CalculiX thermal stress | `models/cfd/cold_plate_openfoam.py`, `models/cfd/run_cold_plate.sh`, `models/thermal/cold_plate_ccx.py` |
| `cadquery_ccx_tapered` | tapered cantilever bracket (the optimisation loop's model) | CadQuery -> STEP -> Gmsh (C3D10) -> CalculiX static | `models/fea/tapered_bracket.py` |
| `ccx_strut` | strut buckling (eigenvalue, then imperfect and nonlinear) | CalculiX *BUCKLE, then geometrically nonlinear static, structured C3D8I deck written in Python | `models/fea/strut_ccx.py` |
| `cadquery_ccx_strap_plastic` | strap proof test beyond notch yield | strap CAD-to-FEA pipeline with CalculiX isotropic-hardening plasticity, load then unload | `models/fea/strap_hole.py`, `models/fea/strap_plastic.py` |
| `ccx_bolted_joint` | preloaded bolted joint, friction contact to slip | CalculiX surface-to-surface penalty contact with Coulomb friction, structured polar C3D8I half model | `models/fea/bolted_joint_ccx.py` |
| `cadquery_ccx_clevis` | machined clevis bracket (the 3D optimisation loop's model) | CadQuery -> STEP -> Gmsh (C3D10; optional `fillet_element_size_mm` refines the fillets) -> CalculiX static, rigid pin | `models/fea/clevis_bracket.py` |
| `ccx_flag` | Turek-Hron elastic flag, static (CSM1, CSM2) | CalculiX NLGEOM static under gravity plus *FREQUENCY, structured plane-strain C3D8I mesh clamped on the cylinder arc | `models/fea/flag_ccx.py` |
| `ccx_flag_dynamic` | Turek-Hron elastic flag, dynamic (CSM3) | CalculiX NLGEOM *DYNAMIC (ALPHA 0), plus a gravity/1000 companion run and *FREQUENCY | `models/fea/flag_ccx.py` |
| `openfoam_turek_hron` | Turek-Hron fluid stage (cylinder + rigid flag, steady) | Gmsh .geo (FreeCAD's gmsh.exe) -> gmshToFoam -> OpenFOAM 14 incompressibleFluid in WSL, forces on the body | `models/cfd/turek_hron_openfoam.py`, `models/cfd/run_turek_hron.sh` |
| `openfoam_ccx_precice_fsi` | Turek-Hron FSI (flag behind a cylinder, coupled) | OpenFOAM v2512 pimpleFoam (moving mesh, Gmsh mesh) + CalculiX (`ccx_preCICE`) through preCICE 3.4, both in WSL; needs the v2512 bashrc (`OPENFOAM_V2512_BASHRC` to override) | `models/fsi/turek_hron_fsi.py`, `models/fsi/run_turek_hron_fsi.sh` |
| `pyleecan_femm` | electric-machine electromagnetics (study 7; the 2004 Prius motor) | Pyleecan master + FEMM 4.2, run as a subprocess in Pyleecan's own environment (`PYLEECAN_PYTHON`, default `~/.venvs/pyleecan`) | `models/motor/pyleecan_em.py` |
| `pyleecan_femm_load` | electric-machine torque against current (study 7): a current-angle sweep per point, MTPA torque | same runner in its current-angle mode | `models/motor/pyleecan_em.py` |
| `pyleecan_femm_lut` | electric-machine dq look-up table (study 7, efficiency map input): one d-axis current per point, a q-axis sweep inside, dq flux linkages, torque and iron-loss coefficients (P = A f + B f^2 + C f^1.5) | same runner in its dq-grid mode | `models/motor/pyleecan_em.py` |
| `lut_efficiency` | electric-machine efficiency map (study 7) from a `motor_lut` run: lowest-loss feasible current at each speed and torque under the bus voltage and a current limit; scenarios for temperatures | numpy/scipy, no solver | `models/motor/efficiency_map.py` |
| `lumped_thermal` | electric-machine steady thermal network (study 7) from the geometry, coupled to the cold and hot `motor_lut` tables: continuous torque-speed envelope under hotspot and magnet limits, hot-corner check; CalculiX slot-pitch conduction check on three meshes | numpy + Gmsh + CalculiX (seconds per mesh) | `models/motor/thermal_network.py`, `models/motor/stator_section_ccx.py` |
| `cadquery_ccx_vessel` | pressure vessel shell with a radial nozzle (study 18): quarter model, internal pressure with closed-end thrusts, stresses linearised along classification lines at the fillet toes and through the crotch (Pm, PL, P + Q); optional `scl_toe_offset_mm` | CadQuery + Gmsh C3D10 + CalculiX | `models/fea/pressure_vessel.py` |
| `ccx_vessel_head_axi` | cylindrical shell closed by a hemispherical head (study 18, the head-to-shell junction): axisymmetric, structured mesh generated in Python, lines through the wall on element boundaries | CAX8 + CalculiX | `models/fea/vessel_head_axi.py` |
| `openfoam_step_rans` | backward-facing step, Driver and Seegmiller (study 19 part 2): 2D steady RANS, k-omega SST, walls resolved; inflow boundary layer matched at x = -4 H; two-stage run (first-order k, omega start-up, then limitedLinear) | OpenFOAM 14 (in WSL, nice 19, one core) | `models/cfd/step_openfoam.py`, `run_step.sh` |
| `openfoam_pipe_rans` | fully developed turbulent pipe flow (study 19): axisymmetric periodic wedge, RANS (k-omega SST), bulk velocity held by meanVelocityForce; low-Reynolds or wall-function wall treatment; friction factor | OpenFOAM v14 in WSL | `models/cfd/pipe_openfoam.py`, `models/cfd/run_pipe.sh` |
| `pyleecan_gmsh_ccx_rotor` | IPM rotor lamination at overspeed (study 7): half a pole in plane stress, linearized bridge stress | Pyleecan export (its own environment) + Gmsh + CalculiX | `models/motor/export_rotor_pole.py`, `models/fea/rotor_ccx.py` |

A case with an `[optimization]` section runs with `python -m harness optimize <case>`
(harness/optimize.py): COBYLA proposes designs, each candidate is a point under
`points/c###` with its own evidence and checks, and a candidate that fails any check is
infeasible to the optimiser. Confirm the optimum with a separate mesh-study case.

The registry is `harness/registry.py`; each study lives in `studies/<name>.py`.

- Python 3.14 in `.venv` (numpy, scipy, matplotlib, cadquery pinned in `requirements-lock.txt`).
- For `cantilever_freecad`, the harness finds `freecadcmd` via `FREECADCMD` or the FreeCAD
  install folder. Each point runs a fresh FreeCAD session (about 4 s at 8 mm mesh, 30 s at
  2 mm). The CalculiX deck, `.dat`, and native `cantilever.FCStd` are kept in
  `points/<label>/solver/`. Nodal results are parsed from the `.frd` file by
  `harness/calculix.py`, not by FreeCAD.
- For `ccx_fin`, the harness runs `ccx` directly (found via `CCX` or the FreeCAD install
  folder); no FreeCAD session. The deck, `.dat`, `.sta`, `.frd` and log are kept in
  `points/<label>/solver/`. About 15 s per point at 0.25 mm elements. The tip-face
  temperatures are read from the `.dat` (7 digits; the `.frd` has 6). CalculiX's base
  RFL total excludes the film load lumped on the base nodes; the study adds it back.
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

## Resources (the user's machine is shared)

- Before a mesh study, run the coarsest point (or a scratch prototype) and look at its peak memory and output sizes;
  scale them by the node count to the finest mesh. Study C's finest mesh wrote a 16.5 GB result file and its reader
  took 38 of 64 GB of RAM (CalculiX output requests carried into later steps); the coarse mesh's 40 MB file would have
  shown it (x 12 nodes).
- While long runs go, check free RAM and the processes now and then (`Get-Process`, `Win32_OperatingSystem`), not only
  the log: a run can be "progressing" while the machine pages.
- To stop a run of your own, stop its background task (TaskStop), not by killing processes. Then fix the cause, note
  the stopped run in the case's Results, and rerun; don't keep the partial run as evidence of anything but the stop.
- Before a transient mesh study at a fixed time step, compute or measure the Courant number on every level: it
  scales as 1/h, so the finest level runs at a different temporal resolution from the coarsest. Write the
  per-level value in the case and decide on purpose: a fixed dt (the study then mixes in temporal error, and the
  fine level carries a stability risk under PISO, `nOuterCorrectors 1`) or a fixed Courant number (dt scaled with
  h, stated). Study 6 measured max Co 1.2-1.4 on the 3.54 / 2.5 mm levels and 2.36 on 1.77 mm.
- A deforming-mesh run that dies suddenly: read the last max Courant numbers in the kept tail. A jump of several
  times per step (study 6, FSI2 at 1.77 mm: 2.2 -> 5.8 -> 17.9, then a floating point exception in GAMG) means a
  cell collapsing under the mesh motion or a local PISO instability at Courant numbers above 1; the tail alone does
  not separate them (I first called it a collapse and had to correct it: the flag had passed the same position
  before). Choose the next single change so it separates them (more outer correctors fixes only the instability; a
  stiffer mesh motion only the collapse), and keep fields near a known crash time when rerunning.
- On long runs, read the live solver log in the work dir now and then, not only the harness log: the max Courant
  number per simulated second and the coupling iterations per window, from the log's tail (FSI / CFD studies:
  `%LOCALAPPDATA%/Temp/fsi_*/case/fluid/log.pimpleFoam`). A rising trend is the warning a crash otherwise gives
  only after hours.
- Predict a case's run time as the sum over its points: a sweep's scenarios run one after another (FEMM always,
  being one at a time). Study 7's steel case predicted 45-75 min from one point's 35 min and took 105 min for three.
- In a coupled (preCICE) run the slower participant sets the pace: a fluid mesh study on a fixed solid mesh does not
  speed up below the solid's cost. Study 6's 3.54 mm FSI2 level took 8.75 h, as long as the 2.5 mm level (8.9 h),
  against a prediction of 3 h; the solid ran at about 90 % of a core throughout. Time one coupling window per
  participant before predicting.
- One FEMM at a time; OpenFOAM under `nice -n 19`; several single-core jobs at once are fine on this machine, but
  watch memory more than CPU.

## Artifacts

`runs/<run_id>/`: `inputs/case.toml`, `manifest.json`, `run.log`,
`points/<label>/{timeseries.csv, point.json}`; for Modelica, also `inputs/EngLab.mo` and
`build/{build.mos, omc_build.log}`. See `runs/README.md`.

If a point fails with `output grid mismatch`, the executable ignored the requested time
settings. Check the flags in `harness/backend_base.py` against `<exe> -help`. Do not relax
the grid check.

## Failure handling

- Never delete or overwrite a run directory, including failed ones. Failed runs are evidence.
- A failed point keeps the last 400 lines of every solver log the study did not copy, in
  `points/<label>/solver/failure_tails/` (`harness/run.py`, `keep_failure_tails`). Read them before
  changing anything, then change one thing per rerun. If the tail is missing (a study that deletes its own work
  dir), rerun unchanged first to capture the error: a serial solve repeats the same crash.
- Do not change the case's tolerances or requirements to make a run pass. If a change is
  justified, edit the case file, say why, and start a new run.
- If a solver fails, report it. Changing `method`, `rtol`, or `atol` is an engineering decision
  for the user to make.

## Human judgment needed

The choice of parameters, assumptions, and acceptance tolerances. A completed run only means the
solver finished. It says nothing about whether the result is correct.

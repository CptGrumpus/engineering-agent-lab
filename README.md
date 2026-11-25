# Engineering Agent Lab

[![tests](https://github.com/CptGrumpus/engineering-agent-lab/actions/workflows/tests.yml/badge.svg)](https://github.com/CptGrumpus/engineering-agent-lab/actions/workflows/tests.yml)

A personal project for building an agent harness that translates engineering requirements into repeatable models, simulation runs, and reviewable evidence.

## Background

The intended user is an automotive engineer with a master's degree in mechanical engineering. Current professional work includes using AI agents to run virtual models and translating functional requirements into tools that automate engineering workflows. This project develops similar skills using personal hardware and public or synthetic examples in preparation for potential contract work.

## Start here

- **[PORTFOLIO.md](PORTFOLIO.md)**: capabilities and the case studies, grouped by discipline (for reviewers). Each case study has its own page in [portfolio/](portfolio/), and [a sample client memo](portfolio/deliverables/coolant-channel-memo.md) shows the deliverable format.
- [CAD-TOOLS.md](CAD-TOOLS.md): the tool stack, installed versions, how the harness drives each tool, and hardware context.
- [skills/README.md](skills/README.md): agent skills and their status.

## Studies

| Study | Model names (case `model`) | Tools | Cases |
|---|---|---|---|
| Mass-spring-damper step response | `msd`, `msd_modelica` | SciPy; OpenModelica + MSL | `msd_step`, `msd_step_modelica` |
| Quarter-car ride / road holding | `quarter_car`, `quarter_car_modelica`, `quarter_car_modelica_liftoff` | SciPy; OpenModelica + MSL | `qc_speed_bump`, `qc_speed_bump_modelica`, `qc_iso_road`, `qc_bump`, `qc_bump_liftoff`, `qc_bump_liftoff_modelica`, `qc_bump_stop` |
| Cantilever, 3D solid FEA | `cantilever_freecad` | FreeCAD + Gmsh + CalculiX | `cantilever_tet10`, `cantilever_tet4` |
| Parametric mounting plate | `cadquery_plate` | CadQuery | `mounting_plate` |
| Strap with a cable hole, CAD to FEA | `cadquery_ccx_strap` | CadQuery -> Gmsh -> CalculiX | `strap_hole_mesh`, `strap_hole_size` |
| Bracket arm modal analysis (vibration) | `cadquery_ccx_modal` | CadQuery -> Gmsh -> CalculiX | `bracket_modal_mesh`, `bracket_modal_thickness` |
| Roller-on-plate contact (Hertz) | `gmsh_ccx_contact` | Gmsh (scripted geometry) -> CalculiX contact | `contact_roller_mesh` |
| Strap fatigue life (chained FE + S-N) | `strap_fatigue` | CadQuery -> Gmsh -> CalculiX, then stress-life | `strap_fatigue_load` |
| Laminar coolant channel, CFD | `openfoam_channel` | OpenFOAM 14 (in WSL) | `channel_header_mesh`, `channel_header_tolerance`, `channel_header_gap_limits`, `channel_mesh` |
| Side-wall (3D) check of the channel | `openfoam_duct` | OpenFOAM 14 (in WSL) | `duct_side_walls` |
| Heated coolant channel (thermal entry) | `openfoam_heated_channel` | OpenFOAM 14 (in WSL), scalarTransport | `heated_channel_mesh`, `heated_channel_flux` |
| Heat-sink fin tip temperature, 3D conduction | `ccx_fin` | CalculiX (bundled with FreeCAD) | `fin_mesh`, `fin_tolerance`, `fin_h_sweep` |
| Cold plate, full thermal chain (CFD + conduction + thermal stress) | `openfoam_ccx_cold_plate` | OpenFOAM 14 (in WSL) coupled to CalculiX | `cold_plate_mesh`, `cold_plate_mesh_r1`, `cold_plate_solver_check` |
| Tapered bracket, optimisation loop | `cadquery_ccx_tapered` | CadQuery -> Gmsh -> CalculiX, COBYLA | `bracket_opt`, `bracket_opt_confirm` |
| Clevis bracket, 3D optimisation loop | `cadquery_ccx_clevis` | CadQuery -> Gmsh -> CalculiX, COBYLA | `clevis_opt`, `clevis_opt_r1`, `clevis_opt_r2`, `clevis_confirm`, `clevis_confirm_r1`, `clevis_confirm_r1_fillet`, `clevis_confirm_r2`, `clevis_confirm_r2b` |
| Strut buckling (eigenvalue, then imperfect and nonlinear) | `ccx_strut` | CalculiX | `strut_mesh`, `strut_length` |
| Strap proof test, plasticity | `cadquery_ccx_strap_plastic` | CadQuery -> Gmsh -> CalculiX plasticity | `strap_proof`, `strap_proof_r1` |
| Bolted joint, friction contact to slip | `ccx_bolted_joint` | CalculiX contact with friction | `bolted_joint_mesh`, `bolted_joint_mesh_r1` |
| Turek-Hron flag, solid stage (static, dynamic) | `ccx_flag`, `ccx_flag_dynamic` | CalculiX NLGEOM | `flag_csm1_mesh`, `flag_csm2_mesh`, `flag_csm3_dt`, `flag_csm3_dt_r1` |
| Turek-Hron fluid stage (cylinder + rigid flag) | `openfoam_turek_hron` | Gmsh -> OpenFOAM 14 (in WSL) | `turek_hron_cfd1_mesh`, `turek_hron_cfd1_mesh_r1`, `turek_hron_cfd2_mesh` |
| Turek-Hron FSI, coupled (flag behind a cylinder) | `openfoam_ccx_precice_fsi` | OpenFOAM v2512 (moving mesh) + CalculiX through preCICE 3.4 (in WSL) | `turek_hron_fsi1_mesh`, `turek_hron_fsi1_mesh_r1`, `turek_hron_fsi1_mesh_r2`, `turek_hron_fsi1_noise_{a,b,c,d}`; periodic: `turek_hron_fsi2`, `turek_hron_fsi3`, mesh studies `turek_hron_fsi{2,3}_mesh_{a,b,c}` (combined by `scripts/combine_mesh_levels.py`), crash diagnosis `turek_hron_fsi2_mesh_c_diag` |
| Prius traction motor, open circuit (back-EMF, flux linkage) | `pyleecan_femm` | Pyleecan + FEMM 4.2 (own environment, `models/motor/pyleecan-env.txt`) | `motor_prius_ornl_oc_mesh_r3` (final machine), its earlier revisions, `motor_prius_ornl_oc_m250`, `motor_prius_ornl_oc_y390`, `motor_prius_ornl_oc_js205`, `motor_prius_oc_mesh`, `motor_prius_oc_mesh_r1`; calibrated `motor_prius_cal_oc_mesh`, `motor_prius_cal_oc_br`; client data (revision 5) `motor_prius_rev5_oc`, `motor_prius_rev5_oc_f2`, `motor_prius_rev5_steel`, `motor_prius_rev5_inductance` (second solver: `scripts/motor_elmer_check.py`, ElmerFEM) |
| Prius motor, torque against current (MTPA) | `pyleecan_femm_load` | Pyleecan + FEMM 4.2 | `motor_prius_torque_current_r1`, `motor_prius_torque_current`, `motor_prius_torque_mesh`, `motor_prius_torque_m250`, `motor_prius_torque_y390`, `motor_prius_torque_js205`, `motor_prius_cal_torque_br`, `motor_prius_rev5_torque`, `motor_prius_rev5_torque_ref` |
| Prius motor, dq look-up tables | `pyleecan_femm_lut` | Pyleecan + FEMM 4.2 | `motor_prius_lut_mesh`, `motor_prius_lut_cold`, `motor_prius_lut_hot`, `motor_prius_lut_cold_lowiq`, `motor_prius_lut_hot_lowiq`, the calibrated `*_br` and client-data `*_rev5` sets (`motor_prius_lut_{cold,hot}{,_lowiq,_refine}_rev5`) |
| Prius motor, efficiency map | `lut_efficiency` | Python (NumPy, SciPy) on the dq tables | `motor_prius_efficiency`, `motor_prius_efficiency_r1`, `motor_prius_efficiency_br`, `motor_prius_efficiency_rev5` |
| Prius motor, thermal network and continuous rating | `lumped_thermal` | Python (NumPy) network on the dq tables; Gmsh + CalculiX slot-pitch check | `motor_prius_thermal_r1`, `motor_prius_thermal`, `motor_prius_thermal_br`, `motor_prius_thermal_rev5` |
| Prius motor, rotor stress at overspeed | `pyleecan_gmsh_ccx_rotor` | Pyleecan geometry -> Gmsh -> CalculiX | `motor_prius_rotor_overspeed_mesh`, `motor_prius_rotor_overspeed_rev5_mesh` |
| Pressure vessel nozzle, design by analysis | `cadquery_ccx_vessel` | CadQuery -> Gmsh -> CalculiX, stress linearisation | `pv_nozzle_mesh`, `pv_nozzle_thickness`, `pv_nozzle_crotch_*`, `pv_nozzle_scl_offset` |
| Head-to-shell junction | `ccx_vessel_head_axi` | Python mesh -> CalculiX CAX8, stress linearisation | `vh_junction_mesh_r1`, `vh_thin_head_mesh_r1`, `vh_head_thickness_r1` |
| Turbulent pipe friction (RANS) | `openfoam_pipe_rans` | OpenFOAM 14 (in WSL), k-omega SST | `pipe_rans_mesh`, `pipe_rans_mesh_r1`, `pipe_rans_mesh_r2`, `pipe_rans_reynolds`, `pipe_rans_wf_mesh`, `pipe_rans_wf_yplus` |
| O-ring face seal (squeeze, contact pressure, closing force, fill) | `ccx_oring` | Gmsh (Python API) -> CalculiX, axisymmetric neo-Hookean, node-to-surface contact | `oring_seal_corners`, `oring_seal_mesh`, `oring_free_lindley`, `oring_free_hertz` |
| Shaft shoulder fillet (Kt, Kts; Shigley fatigue and yield safety; sizing) | `ccx_shaft_fillet` | Gmsh (OCC revolve, C3D10) -> CalculiX, half model, bending and torsion decks | `shaft_fillet_mesh_r2`, `shaft_fillet_noise`, `shaft_fillet_radius`, `shaft_fillet_radius_r1`, `shaft_fillet_size` |
| Natural convection in a square cavity (de Vahl Davis) | `openfoam_cavity` | OpenFOAM 14 (in WSL), fluid solver, Boussinesq | `cavity_devahldavis`, `cavity_mesh_ra1e6` |
| Grey-surface radiation between concentric cylinders | `openfoam_annulus_radiation` | OpenFOAM 14, fluid solver with fvDOM | `annulus_angular`, `annulus_emissivity` |
| Sealed electronics enclosure (conjugate heat transfer, convection and radiation; shell and bridge redesign) | `openfoam_enclosure_cht` | OpenFOAM 14 (in WSL), foamMultiRun: air, board, component, optional aluminium shell and bridge, fvDOM | `enclosure_k{5,20}_eps0p{1,9}`, `enclosure_k20_eps0p9_mesh1mm`, `enclosure_fix_k5_eps0p{1,9}_{shell,br1,br2,br5,br20}` |

## Project folders

- `portfolio/`: one page per case study, linked from PORTFOLIO.md; `portfolio/img/` headline figures and result visuals (made by `scripts/make_portfolio_figures.py`, `scripts/make_result_visuals.py`, and the Blender renders by `scripts/make_renders.py`, checks logged in `portfolio/img/renders.json`); `portfolio/deliverables/` sample client memo.
- `tasks/`: engineering evaluation tasks (statement, reference solution, automated grader, traps), built from the verified studies; graders tested in `tests/test_tasks.py`.
- `cases/`: case files (TOML) with parameters, sweep, numerics, verification tolerances, and requirements.
- `models/`: models under test (Python, Modelica `.mo`, FreeCAD script, CadQuery, OpenFOAM case writer).
- `validation/`: independent references (closed form, state space, beam theory); these must not import from `models/`.
- `excitation/`: load definitions shared by models and references (road profiles).
- `studies/`: one module per study: backends, metrics, checks, plots.
- `harness/`: generic run, verify, report, compare, and rerun tooling (`python -m harness`).
- `runs/`: evidence from individual executions; see [runs/README.md](runs/README.md). Git-ignored except curated example runs (without bulky result CSVs).
- `local_llm/`: running a local open-weight LLM (Inkling 2 Mini) on this workstation next to the solvers: action list and experiment log ([local_llm/PLAN.md](local_llm/PLAN.md)), speed ceilings, benchmark wrapper and run ledger. Separate from the studies; nothing in `harness/` depends on it yet.
- `.claude/skills/`: executable Claude Code skills.
- `tests/`: pytest suite, including negative tests showing that the checks catch wrong models and invalid assumptions.

## Reading it on another machine

Nothing needs installing to read the work. The portfolio pages, figures, renders and evidence reports are all committed.

```powershell
git clone https://github.com/CptGrumpus/engineering-agent-lab.git
code engineering-agent-lab                            # open PORTFOLIO.md, then Ctrl+Shift+V for the preview
```

Or browse it on GitHub: start at `PORTFOLIO.md`; each study links its evidence report under `runs/`. Raw time series and full meshes are not committed (they regenerate from the case files); everything a reviewer reads is.

## Setup and commands

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
# optional tool paths
winget install --id OpenModelica.OpenModelica.Official   # then an omc script: installPackage(Modelica);
winget install --id FreeCAD.FreeCAD                       # bundles CalculiX and Gmsh
# OpenFOAM: in WSL Ubuntu, add the dl.openfoam.org apt repository, then
#   sudo apt-get install openfoam14

.venv\Scripts\python.exe -m harness pipeline cases\qc_speed_bump.toml      # run + verify + report
.venv\Scripts\python.exe -m harness compare runs\<run> runs\<other_run>      # cross-tool check
.venv\Scripts\python.exe -m harness report runs\<run>                        # regenerate the report
.venv\Scripts\python.exe -m harness rerun runs\<run_id>                      # reproduce
.venv\Scripts\python.exe -m pytest -q        # Modelica/FreeCAD/OpenFOAM tests skip if the tool is absent
```

Since added: friction contact (the bolted joint), plasticity (the strap proof test), buckling (the strut), a chained coolant-to-conduction-to-stress model (the cold plate), design by analysis of a pressure-vessel nozzle, and turbulent pipe flow against a measured-data correlation. In progress: two-way fluid-structure coupling (the Turek-Hron flag). Done, and failed: the first blind comparison with measured test data (the traction motor against Oak Ridge's published tests: the model's magnet flux was about 24 % high; a calibrated revision is in progress). Not yet done: fully conjugate heat transfer, where the fluid and solid temperatures are solved together.

## First implementation milestone (done)

1. Select one public benchmark and one tool path.
2. Inspect which required tools are already installed and record their versions.
3. Establish a successful baseline run using the official documentation.
4. Add a small agent workflow around that baseline.
5. Retain the inputs, scripts, settings, logs, and result metrics for each run.
6. Compare against an independent reference and document the result.
7. Rerun from the saved inputs to demonstrate reproducibility.

Define acceptance tolerances before evaluating the result. Distinguish numerical error from modeling assumptions and physical uncertainty.

## Suggested first skills

Develop these incrementally around the working example:

- Clarify requirements and model assumptions.
- Build or modify a model using a documented interface.
- Run a case and capture evidence.
- Verify results against independent checks.
- Summarize requirement compliance and limitations for human review.

## Handoff prompt for a new project chat

> Read README.md, CAD-TOOLS.md, and skills/README.md. Help me build the first small, reproducible engineering-agent workflow on this Windows PC. Begin by inspecting the project and available software, then help select a public benchmark that fits my experience. Choose one tool path and establish a baseline before building reusable skills. Preserve inputs, settings, outputs, and independent checks. Use public or synthetic data and report uncertainty and failed checks clearly. Keep the first milestone small enough that I can understand and review the engineering myself.

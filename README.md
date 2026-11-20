# Engineering Agent Lab

[![tests](https://github.com/CptGrumpus/engineering-agent-lab/actions/workflows/tests.yml/badge.svg)](https://github.com/CptGrumpus/engineering-agent-lab/actions/workflows/tests.yml)

A personal project for building an agent harness that translates engineering requirements into repeatable models, simulation runs, and reviewable evidence.

## Background

The intended user is an automotive engineer with a master's degree in mechanical engineering. Current professional work includes using AI agents to run virtual models and translating functional requirements into tools that automate engineering workflows. This project develops similar skills using personal hardware and public or synthetic examples in preparation for potential contract work.

## Start here

- **[PORTFOLIO.md](PORTFOLIO.md)**: capabilities and the nine case studies, grouped by discipline (for reviewers). Each case study has its own page in [portfolio/](portfolio/), and [a sample client memo](portfolio/deliverables/coolant-channel-memo.md) shows the deliverable format.
- [CAD-TOOLS.md](CAD-TOOLS.md): the tool stack, installed versions, how the harness drives each tool, and hardware context.
- [skills/README.md](skills/README.md): agent skills and their status.

## Studies

| Study | Model names (case `model`) | Tools | Cases |
|---|---|---|---|
| Mass-spring-damper step response | `msd`, `msd_modelica` | SciPy; OpenModelica + MSL | `msd_step`, `msd_step_modelica` |
| Quarter-car ride / road holding | `quarter_car`, `quarter_car_modelica` | SciPy; OpenModelica + MSL | `qc_speed_bump`, `qc_speed_bump_modelica`, `qc_iso_road`, `qc_bump` |
| Cantilever, 3D solid FEA | `cantilever_freecad` | FreeCAD + Gmsh + CalculiX | `cantilever_tet10`, `cantilever_tet4` |
| Parametric mounting plate | `cadquery_plate` | CadQuery | `mounting_plate` |
| Strap with a cable hole, CAD to FEA | `cadquery_ccx_strap` | CadQuery -> Gmsh -> CalculiX | `strap_hole_mesh`, `strap_hole_size` |
| Bracket arm modal analysis (vibration) | `cadquery_ccx_modal` | CadQuery -> Gmsh -> CalculiX | `bracket_modal_mesh`, `bracket_modal_thickness` |
| Strap fatigue life (chained FE + S-N) | `strap_fatigue` | CadQuery -> Gmsh -> CalculiX, then stress-life | `strap_fatigue_load` |
| Laminar coolant channel, CFD | `openfoam_channel` | OpenFOAM 14 (in WSL) | `channel_header_mesh`, `channel_header_tolerance`, `channel_header_gap_limits`, `channel_mesh` |
| Side-wall (3D) check of the channel | `openfoam_duct` | OpenFOAM 14 (in WSL) | `duct_side_walls` |
| Heat-sink fin tip temperature, 3D conduction | `ccx_fin` | CalculiX (bundled with FreeCAD) | `fin_mesh`, `fin_tolerance`, `fin_h_sweep` |

## Project folders

- `portfolio/`: one page per case study, linked from PORTFOLIO.md; `portfolio/img/` headline figures (made by `scripts/make_portfolio_figures.py`); `portfolio/deliverables/` sample client memo.
- `cases/`: case files (TOML) with parameters, sweep, numerics, verification tolerances, and requirements.
- `models/`: models under test (Python, Modelica `.mo`, FreeCAD script, CadQuery, OpenFOAM case writer).
- `validation/`: independent references (closed form, state space, beam theory); these must not import from `models/`.
- `excitation/`: load definitions shared by models and references (road profiles).
- `studies/`: one module per study: backends, metrics, checks, plots.
- `harness/`: generic run, verify, report, compare, and rerun tooling (`python -m harness`).
- `runs/`: evidence from individual executions; see [runs/README.md](runs/README.md). Git-ignored except curated example runs (without bulky result CSVs).
- `.claude/skills/`: executable Claude Code skills.
- `tests/`: pytest suite (67 tests), including negative tests showing that the checks catch wrong models and invalid assumptions.

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

Not yet done: heat transfer in the CFD path, 3D developing flow, nonlinear models (tire lift-off, bump stops, contact), any physical validation data.

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

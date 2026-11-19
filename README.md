# Engineering Agent Lab

A personal project for building an agent harness that translates engineering requirements into repeatable models, simulation runs, and reviewable evidence.

## Background

The intended user is an automotive engineer with a master's degree in mechanical engineering. Current professional work includes using AI agents to run virtual models and translating functional requirements into tools that automate engineering workflows. This project develops similar skills using personal hardware and public or synthetic examples in preparation for potential contract work.

## Start here

Read [CAD-TOOLS.md](CAD-TOOLS.md) for the software shortlist, official documentation, hardware context, and recommended starting paths.

The first milestone is one reproducible engineering example with independent checks. Choose the tool path after deciding whether that example concerns systems modeling, structural analysis, or geometry automation.

## Project folders

- `cases/`: case files (TOML) with parameters, numerics, verification tolerances, and requirements.
- `models/`: source models under test.
- `validation/`: independent reference solutions; these must not import from `models/`.
- `harness/`: run, verify, report, and rerun tooling (`python -m harness`).
- `runs/`: generated evidence from individual executions (git-ignored); see [runs/README.md](runs/README.md).
- `.claude/skills/`: executable Claude Code skills; see [skills/README.md](skills/README.md).
- `tests/`: pytest suite, including negative tests showing that the checks catch a wrong model.

## Current status

Working baseline: **Python + SciPy, mass-spring-damper step response** ([cases/msd_step.toml](cases/msd_step.toml)). A damping-ratio sweep is checked against overshoot, settling-time, and deflection requirements. Every point is verified against a closed-form solution, an energy balance, a steady-state check, and a solver-convergence check. Reruns from the saved inputs are bit-identical.

Environment: Python 3.14 in `.venv`; package versions pinned in [requirements-lock.txt](requirements-lock.txt).

```powershell
# one-time setup
py -3.14 -m venv .venv   # or the full path to python 3.14
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt

.venv\Scripts\python.exe -m harness pipeline cases\msd_step.toml   # run + verify + report
.venv\Scripts\python.exe -m harness rerun runs\<run_id>            # reproduce
.venv\Scripts\python.exe -m pytest -q                              # tests
```

Not yet done: OpenModelica cross-check, structural (FreeCAD/CalculiX) path, any physical validation data.

## First implementation milestone

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

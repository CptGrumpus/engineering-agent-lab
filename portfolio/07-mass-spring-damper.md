# Mass-spring-damper baseline

[Portfolio index](../PORTFOLIO.md) · Workflow validation

| | |
|---|---|
| **Answer** | All 72 checks pass, and the two tools agree to a few parts per million. |
| **Discipline** | Workflow validation |
| **Tools** | Python (SciPy), OpenModelica 1.26 |
| **Methods** | Exact textbook solution, energy balance, solver convergence, a second tool as cross-check |

## What it is

This was the first example, used to prove the workflow on a problem with a known answer. It's a single mass on a spring and damper, pushed by a step force, at six different damping levels. The results are checked against the exact textbook solution, an energy balance, the final resting position, and the solver's own convergence. All 72 checks pass. The same system built in OpenModelica agrees with the Python version to a few parts per million.

## What the checks caught

While I was connecting OpenModelica, the check that results land on the requested time points failed. It turned out OpenModelica was silently ignoring some of the simulation settings I was passing it. I changed how the settings are passed, and the check has guarded against it since.

## Limits

- A textbook problem used to prove the workflow, not a design study.

## Evidence

Each report traces every requirement to its result, the checks behind it, and the saved inputs that reproduce it.

- [Python version](../runs/20261118-200205_msd_step/report.md)
- [OpenModelica version](../runs/20261118-213145_msd_step_modelica/report.md)

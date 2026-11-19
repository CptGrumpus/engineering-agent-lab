# Engineering modeling portfolio

Requirements-driven simulation with independent verification, built on open-source tools and driven by an AI coding agent. Each example turns written requirements into a model, runs a parameter sweep, checks every result against an independent reference, and produces a traceable review report. Model failures and invalid assumptions are reported, not hidden.

All examples use synthetic, public-domain problems. Every number below links to a committed evidence run that can be reproduced from its saved inputs.

## Examples

| # | Problem | Tools | Independent verification | Result |
|---|---|---|---|---|
| 1 | [Quarter-car ride and road holding](#1-quarter-car-ride-and-road-holding) | SciPy, OpenModelica (MSL) | Matrix-exponential solution; closed-form transfer-function RMS; energy balance; SciPy vs Modelica cross-check | Damper window found; validity check caught wheel lift-off |
| 2 | [Cantilever, 3D solid FEA](#2-cantilever-3d-solid-fea-mesh-convergence) | FreeCAD, Gmsh, CalculiX | Timoshenko beam theory; reaction equilibrium; Grid Convergence Index | Converged to 0.02 % discretization uncertainty; linear-tet stiffness error exposed |
| 3 | [Parametric mounting plate](#3-parametric-mounting-plate-geometry-automation) | CadQuery (OpenCASCADE) | Closed-form volume; geometry measured back from the B-rep; STEP round trip | One hole size meets all design rules |
| 4 | [Mass-spring-damper baseline](#4-mass-spring-damper-baseline) | SciPy, OpenModelica | Closed-form step response; energy balance; cross-tool check | 72 / 72 checks pass; tools agree to 2.5e-6 |

## Workflow

```
case file (TOML)          model under test           independent reference
requirements, units,  ->  SciPy / Modelica /    vs   closed form, state space,
tolerances (fixed         FreeCAD+CalculiX /         beam theory, conservation,
before the first run)     CadQuery                   convergence, second tool
        |                         |                           |
        +----------> runs/<id>/  inputs (hashed), environment, logs, results,
                     checks, figures, requirement -> result -> check -> evidence report
```

- **Tolerances are written before the first run.** Changing one needs a written reason and a new run.
- **Two kinds of check.** *Numerical* checks ask whether the equations were solved correctly. *Validity* checks ask whether the model's assumptions hold for the result (wheel stays on the road, stress below yield, small deflection). Either kind failing marks the requirement verdicts *unverified*.
- **Reproducible.** Saved inputs and model sources are hashed; `python -m harness rerun` reproduces a run and compares every result column (bit-identical on the same machine).
- **Agent skills.** `run-case`, `verify-against-reference`, and `requirements-report` ([.claude/skills/](.claude/skills/)) let Claude Code drive the workflow without improvising: they never loosen tolerances or accept a design.

## 1. Quarter-car ride and road holding

Linear 2-DOF quarter car (C-segment front-corner wheel rates). The damper rate is swept from 600 to 3500 N·s/m against comfort, suspension-travel, and dynamic-tire-load requirements.

**Speed bump, 40 mm × 1 m at 18 km/h** ([report](runs/20261119-085019_qc_speed_bump/report.md), 30 / 30 checks pass). Damper rates of 600–1000 N·s/m meet all three requirements; 1500 just misses the comfort limit (4.18 vs 4.0 m/s²); 3500 fails tire load. The same case built from Modelica Standard Library components and solved in OpenModelica agrees with SciPy to 1.2e-6 of peak displacement ([report](runs/20261119-085040_qc_speed_bump_modelica/report.md)).

![Speed bump sweep](runs/20261119-085019_qc_speed_bump/sweep.png)

**ISO 8608 class C road at 72 km/h** ([report](runs/20261119-084926_qc_iso_road/report.md)). Simulated RMS values match the closed-form transfer-function prediction to 1e-10. No damper rate meets the 1.0 m/s² comfort target, and travel and tire load need at least ~1500 N·s/m: the conflict calls for a spring-rate change, not a damper change. At 600 N·s/m the wheel briefly lifts off, so that point is marked unverified.

![ISO road spectrum: simulation vs transfer function](runs/20261119-084926_qc_iso_road/points/p02_damping_N_s_per_m-1500/response.png)

**What the checks caught.** The first bump case (same bump at 36 km/h, [report](runs/20261119-084857_qc_bump/report.md)) passed every numerical check, but the `no_wheel_lift` validity check failed at every damper rate: dynamic tire load reached 1.5–1.7× static. A linear tire model cannot represent lift-off, so every requirement verdict was withheld. The case was kept as evidence and a documented revision at 18 km/h was added.

## 2. Cantilever, 3D solid FEA, mesh convergence

Steel cantilever 200 × 20 × 20 mm, 1 kN tip load. FreeCAD builds geometry, material, constraints, and a Gmsh tetrahedral mesh; CalculiX solves; results are parsed directly from the CalculiX output files. The sweep is a mesh-refinement study (8 → 1.95 mm, ratio 1.6). The native `.FCStd` model and CalculiX deck are kept with each run.

**Quadratic tets, TET10** ([report](runs/20261119-085818_cantilever_tet10/report.md), 22 / 22 checks pass). Tip deflection converges monotonically (observed order 2.04) to 0.953 mm, between Euler-Bernoulli (0.952) and Timoshenko (0.960) as expected for a fully clamped 3D solid. Discretization uncertainty (GCI, Celik 2008 / ASME V&V 20): 0.02 %. Reactions balance the load to 1e-11. Root bending stress, extrapolated from the top fibre away from the singular clamp corners, is 150.0 MPa against 150 MPa from beam theory; the raw peak von Mises stress at the corner grows from 150 to 217 MPa with refinement, which is why it is not used for the requirement.

![Cantilever deflection and stress vs beam theory](runs/20261119-085818_cantilever_tet10/points/p03_mesh_size_mm-1.95312/response.png)

**What the checks caught.** The same study with linear tets (TET4, [report](runs/20261119-090004_cantilever_tet4/report.md)) under-predicts deflection by 4–33 % and root stress by 7–45 %. That would make the stiffness requirement look comfortably met; the beam-theory and GCI checks fail instead and the verdicts are marked unverified.

![TET4 sweep with unverified points](runs/20261119-090004_cantilever_tet4/sweep.png)

## 3. Parametric mounting plate, geometry automation

CadQuery builds a 120 × 80 × 6 mm aluminium plate with R8 corners and a 3 × 2 hole grid; the hole diameter is swept over M5–M12 clearance sizes. Every metric is measured back from the B-rep rather than taken from the design intent: volume, bounding box, and each hole's centre and diameter. The STEP export is re-imported and compared ([report](runs/20261119-090540_mounting_plate/report.md), 40 / 40 checks pass; volume matches the closed form to 1e-16).

Mass (≤ 150 g) needs large holes; edge distance (≥ 2 d) needs small ones. Only the 9 mm (M8) hole meets both.

![Mounting plate sweep](runs/20261119-090540_mounting_plate/sweep.png)

## 4. Mass-spring-damper baseline

The first harness example: a 1-DOF step response with a damping-ratio sweep, checked against the closed-form solution, an energy balance, steady state, and solver convergence ([SciPy report](runs/20261118-200205_msd_step/report.md)). The same system built from MSL components in OpenModelica agrees with SciPy to 2.5e-6 of the static deflection ([Modelica report](runs/20261118-213145_msd_step_modelica/report.md)).

While integrating OpenModelica, the harness's output-grid check revealed that OpenModelica 1.26 silently ignores experiment settings passed through `-override`; the backend now uses the dedicated flags.

## Reproduce

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.venv\Scripts\python.exe -m harness pipeline cases\qc_speed_bump.toml   # run + verify + report
.venv\Scripts\python.exe -m harness rerun runs\<run_id>                 # reproduce a run
.venv\Scripts\python.exe -m pytest -q                                   # 43 tests
```

Tool versions: Python 3.14.10, NumPy 2.5.5, SciPy 1.18.1, OpenModelica 1.26.3 with MSL 4.1.0, FreeCAD 1.1.4 with CalculiX 2.22 and Gmsh, CadQuery 2.8.0. Every run records the exact versions, platform, and git commit in its manifest.

## Limitations

- Synthetic parameters throughout; nothing is calibrated to a real product.
- The checks establish numerical verification and model-validity limits. Physical validation needs test data, which these examples do not have.
- Comfort metrics are unweighted (no ISO 2631 frequency weighting).
- Engineering acceptance is left to human review; reports end with "Pending human review" by design.

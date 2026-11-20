# Engineering Modeling Portfolio

Nine worked case studies in structural analysis, vibration, fatigue, fluids and heat transfer, vehicle dynamics, and CAD automation. Each one starts from a written question and measurable requirements, builds a model to answer it, and checks the result against something independent: an exact solution, a conservation law, a handbook value, a second tool, or a mesh-convergence study. Each ends with a clear answer and a statement of how sure that answer is.

I also show what the checks caught along the way. In several studies the first version of the model gave an answer that looked reasonable and was wrong, and the checks are what exposed it.

All problems are synthetic, so no client data is involved. Every number comes from a saved run that can be reproduced from its recorded inputs.

## Capabilities

| Capability | Tools | Shown in |
|---|---|---|
| Structural finite element analysis: 3D solids and plane stress, mesh convergence, stress-concentration and singularity judgement | FreeCAD, Gmsh, CalculiX | [1](portfolio/01-cantilever-bracket.md), [2](portfolio/02-strap-cable-hole.md) |
| Vibration: modal analysis, mode identification, frequency targets against engine orders | CadQuery, Gmsh, CalculiX | [4](portfolio/04-bracket-modal.md) |
| Fatigue: notch factors, mean-stress correction, S-N curves from published test data, life ratings | CalculiX, Python | [3](portfolio/03-strap-fatigue.md) |
| Scripted CAD-to-analysis pipelines: parametric geometry, STEP exchange, meshing, solving | CadQuery, Gmsh, CalculiX | [2](portfolio/02-strap-cable-hole.md), [4](portfolio/04-bracket-modal.md), [8](portfolio/08-mounting-plate.md) |
| Computational fluid dynamics: internal laminar flow, pressure budgets, 2D and 3D | OpenFOAM | [5](portfolio/05-coolant-channel.md) |
| Heat transfer: conduction with surface convection | CalculiX | [6](portfolio/06-heat-sink-fin.md) |
| Vehicle and system dynamics: ride, road holding, frequency response | Python (SciPy), OpenModelica | [7](portfolio/07-quarter-car.md), [9](portfolio/09-mass-spring-damper.md) |
| Verification and uncertainty: exact and handbook references, Grid Convergence Index, tolerance and sensitivity studies | Python | All |

## Sample deliverable

[Technical memo: cold-plate coolant passage](portfolio/deliverables/coolant-channel-memo.md). This is what a client receives at the end of a study: the answer and a recommendation on page one, then the requirements, inputs, method, verification, results, uncertainty, the design options with their numbers, and next steps, all traced to the evidence.

## Case studies

### Structures and vibration

| | Question | Answer |
|---|---|---|
| [1. Cantilever bracket, 3D finite elements](portfolio/01-cantilever-bracket.md) | Does a steel cantilever meet its stiffness and stress limits, and how accurate is the model? | Yes: 0.953 mm deflection and 150 MPa root stress, with 0.02 % mesh uncertainty. |
| [2. Cable hole in a strap, CAD to FEA](portfolio/02-strap-cable-hole.md) | How large can a cable hole in an aluminium strap be before the stress at its edge exceeds the allowable? | About 16.7 mm. A 16 mm hole passes at 117 MPa; 18 mm fails at 125 MPa. |
| [3. Strap fatigue life, chained analysis](portfolio/03-strap-fatigue.md) | Does the strap survive ten million service cycles, and what cyclic load can it be rated for? | Yes, by a wide margin; rated to about 7.8 kN cyclic for 3 × 10⁷ cycles. |
| [4. Bracket arm vibration, modal analysis](portfolio/04-bracket-modal.md) | How thin can an engine-mounted bracket arm be and keep its first mode above 250 Hz within a mass budget? | 7 mm: 261.7 Hz at 206 g. |

### Thermal and fluids

| | Question | Answer |
|---|---|---|
| [5. Coolant channel pressure budget](portfolio/05-coolant-channel.md) | Does a cold-plate passage stay within its pump budget across manufacturing tolerance and coolant temperature? | No. It needs 33.4 Pa against a 30 Pa budget, and no gap size satisfies both requirements. |
| [6. Heat-sink fin temperature](portfolio/06-heat-sink-fin.md) | Does the tip of an aluminium heat-sink fin stay above 60 °C, and what would make it fail? | Yes, at 73.2 °C. Even with every input at its worst it stays at 65.9 °C. |

### Vehicle and system dynamics

| | Question | Answer |
|---|---|---|
| [7. Quarter-car ride and road holding](portfolio/07-quarter-car.md) | Which damper rates meet comfort, suspension travel, and tire-load targets? | 600 to 1000 N·s/m over a speed bump. On a rough road, the spring rate has to change too. |

### Geometry automation

| | Question | Answer |
|---|---|---|
| [8. Parametric mounting plate](portfolio/08-mounting-plate.md) | Which hole size keeps an aluminium plate light enough while keeping enough material around each hole? | Only the 9 mm (M8 clearance) hole meets both rules. |

### Workflow validation

| | Question | Answer |
|---|---|---|
| [9. Mass-spring-damper baseline](portfolio/09-mass-spring-damper.md) | Can the workflow reproduce a textbook result exactly, in two different tools? | Yes. All 72 checks pass, and the two tools agree to a few parts per million. |

## Highlights: what the checks caught

- **A model that converged cleanly to the wrong answer** ([strap](portfolio/02-strap-cable-hole.md)). A textbook-perfect mesh study settled 2 % off the handbook. Running an exact case through the same pipeline exposed a solver formulation issue that no amount of mesh refinement would have shown.
- **An idealized inlet that reversed the verdict** ([coolant channel](portfolio/05-coolant-channel.md)). The simple model said the channel passed. It never converged at the inlet corner, and the realistic model fails the budget.
- **A wheel that left the road** ([quarter car](portfolio/07-quarter-car.md)). Every numerical check passed, but the model's assumptions didn't hold, so no verdict was reported.
- **Elements that made the bracket look too stiff** ([cantilever](portfolio/01-cantilever-bracket.md)). The simplest element type overstated stiffness by up to a third; the checks withheld every result.

## How I work

1. **I write the requirements and the acceptance tolerances before running anything.** That way a passing result can't be the product of moving the goalposts. If a tolerance or a requirement has to change later, the reason is written down and the earlier run is kept.
2. **I check every reported number against an independent reference.** That might be an exact solution, a conservation law, a published correlation, or the same model built in a second tool.
3. **I check that the model is valid for each case, not just that it solved.** For example: does the wheel stay on the road, is the stress below yield, is the flow still laminar? If an assumption breaks, the result is marked unverified rather than reported as a pass or fail.
4. **I measure how much the answer depends on the mesh or time step,** and I report that uncertainty next to the answer.
5. **I keep the evidence.** Inputs, tool versions, logs, results, figures, and a report that traces each requirement to its result and its checks. Any run can be repeated, and it reproduces exactly on the same machine.

The workflow is driven by an AI coding agent working through fixed, documented procedures. Those procedures are written as reusable skills, and they never loosen a tolerance or accept a design on their own. Engineering acceptance is always left to a person.

## What every study delivers

- A case file with the requirements, assumptions, and acceptance tolerances, written before the first run.
- The model source, saved and hashed with each run, and the native solver files (CAD, mesh, solver input).
- A report that traces each requirement to its result, the checks behind it, and the evidence files, ending with "pending human review".
- Figures comparing the model with its references, and the mesh or time-step uncertainty.
- One command to reproduce the run; it reproduces exactly on the same machine.

## Limits of these examples

- The parameters and requirement limits are synthetic. Nothing here is calibrated to a real product.
- The checks show the equations were solved correctly and the models were used within their valid range. Showing that a model matches real hardware needs test data, which these examples don't have.
- The ride-comfort figures are unweighted. A production study would apply the ISO 2631 human-sensitivity weighting.
- The coolant-channel model covers flow and pressure, not heat transfer. The fin model takes the air-side heat-transfer coefficient as an input rather than computing the airflow.
- Every report ends with "pending human review". Accepting a design is an engineering decision, and it stays with a person.

## Reproducing the work

Each run records its exact inputs, tool versions, and code version. Setup and commands are in the [README](README.md), and the tool stack and versions are in [CAD-TOOLS.md](CAD-TOOLS.md).

# Check catalog

Independent checks used in this repo, by problem type. Pick at least one
reference per requirement metric, plus conservation, convergence, a field-level
comparison, and one validity check per assumption that can fail.

## Time-domain dynamics (ODEs)

| Check | Kind | Example |
|---|---|---|
| Closed-form solution | numerical | MSD step response vs analytical |
| Matrix exponential / `lsim` on a 10x finer grid | numerical | quarter-car bump (linear system with arbitrary input) |
| Closed-form spectral RMS from transfer functions | numerical | quarter car on an ISO 8608 road |
| Energy balance (input work = stored + dissipated, Simpson rule) | numerical | MSD, quarter car |
| Solver convergence: rerun with tightened tolerances | numerical | `tolerance_scale` in the backend |
| Steady state / return to rest / transient decayed before the window | numerical | MSD steady state, quarter-car `transient_decayed` |
| Second tool (same model in Modelica vs SciPy) | numerical | `[cross_check]` in the case |
| Wheel stays on the road (dynamic / static tire load < 1) | validity | `no_wheel_lift` |

## Structural FEA

| Check | Kind | Example |
|---|---|---|
| Beam theory (Euler-Bernoulli, Timoshenko with Cowper shear coefficient) | model form | cantilever tip deflection |
| Bending stress extrapolated from the smooth region, not the singular corner | numerical | root stress fit over 0.25L-0.75L |
| Reaction equilibrium (sum of reactions = applied load) | numerical | from the CalculiX `.dat` totals |
| Applied load recomputed from the solver deck; reactions balance the load on the non-fixed nodes | numerical | needed when a loaded face touches the clamp (uniform load on a cantilever's top face) |
| Deflection field along a free fibre vs beam theory, not only the tip value | numerical | catches a wrong load distribution that a single tip value can hide |
| GCI over the 3 finest meshes, regime-aware (monotone / oscillatory / divergent) | numerical | `discretization_<metric>` |
| Stress / yield < 1 | validity | `linear_material` |
| Deflection / length below a limit | validity | `small_deflection` |

## Heat conduction (CalculiX)

| Check | Kind | Example |
|---|---|---|
| Energy balance: base reaction heat flow vs convective loss integrated from nodal temperatures | numerical | fin `energy_balance` |
| 1D fin theory with convective tip (tip temperature, heat rate), labelled model form | model form | fin `tip_reference`, `heat_flow_reference` |
| Cross-section-mean temperature profile vs 1D theory | numerical | fin `profile_reference` |
| The requirement metric finds the coldest / hottest point of the whole part | numerical | fin `tip_is_coldest` |
| GCI on the requirement metric | numerical | fin mesh study |
| Biot number below 0.1 for the 1D reference | validity | `one_d_reference_valid` |

## Geometry automation (CAD)

| Check | Kind | Example |
|---|---|---|
| Closed-form area / volume | numerical | plate with corner radii and holes |
| Geometry measured back from the B-rep (bounding box, hole centres, diameters) | numerical | `measure()` in the mounting-plate study |
| Exchange-file round trip (STEP re-import: volume, hole count) | numerical | `step_roundtrip_*` |
| Valid solid | numerical | `shape.isValid()` |

## CFD (incompressible, laminar)

| Check | Kind | Example |
|---|---|---|
| Exact solution (plane Poiseuille; rectangular-duct series) for profile, gradient, wall shear | numerical | channel, duct |
| Full-field comparison against the exact field (max error / u_max) | numerical | duct `velocity_field_reference` |
| Mass conservation (outlet vs inlet face flux) and imposed flow rate | numerical | `mass_conservation`, `inlet_flow` |
| Force balance (wall shear vs pressure gradient x H/2) | numerical | `momentum_balance` |
| Correlation for developing flow (Shah & London), labelled model form | model form | `pressure_drop_correlation` |
| Lubrication theory through slowly varying sections | model form | header + contraction estimate |
| Iterative convergence on the quantity of interest (history over the last 10 % of iterations) | numerical | duct `pressure_gradient_converged` |
| No cross-flow where the exact cross-flow is zero | numerical | duct `no_cross_flow` |
| GCI on every requirement metric | numerical | channel, duct |
| Re below transition | validity | `laminar` |
| Entrance length ends before the measurement window; centreline constant across it | validity | `entrance_before_window`, `fully_developed` |
| checkMesh passes | numerical | `mesh_quality` |

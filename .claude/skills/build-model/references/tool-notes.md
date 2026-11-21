# Tool notes

Traps found while building the studies in this repo, by tool.

## Python model sources

- Generated text (solver dictionaries, input decks) must not contain numpy
  reprs: numpy 2 prints `np.float64(0.5)`. Cast with `float()` first.
- When writing files from a bash heredoc that contains Python, `\n` inside a
  string literal can become a real newline. Prefer the Write/Edit tools for
  source files.
- Load model sources in `prepare()` from the run's saved `inputs/` with
  `importlib.util.spec_from_file_location`, so reruns use the saved version.

## OpenModelica (omc 1.26)

- Experiment settings passed through `-override` (stopTime, stepSize,
  tolerance) are silently ignored. Use `-stopTime`, `-stepSize`, `-tolerance`,
  `-s`. `-tol` is not a valid flag.
- Use absolute paths for `loadFile` and for the executable.
- Compile once per run; run the executable per point with `-overrideFile`.
- The harness calls `omc` directly rather than through OMPython: one compile per
  run, every setting as an explicit flag, and no background session. Use the
  same pattern for new Modelica models unless there is a reason not to.
- Missing MSL shows as `Failed to load package Modelica` in the build log;
  install with an omc script `installPackage(Modelica);`.

## FreeCAD + Gmsh + CalculiX

- Run scripts headless with `freecadcmd`. This repo passes inputs through an
  environment variable (`CANTILEVER_INPUT`) pointing to a JSON file, and the
  script writes a summary JSON that the backend reads back.
- Check the force direction after building the constraint (the `Reversed` flag
  depends on the reference edge).
- Parse results from the `.frd` file directly (fixed-width fields: node id at
  columns 3-13, then 12-character values that can touch each other) and
  reaction totals from the `.dat` file.
- Keep the `.FCStd`, `.inp`, `.dat` files with each point.
- When a loaded face shares an edge with a fixed face (pressure on the top of a
  cantilever), the share of the load on the fixed nodes goes straight into the
  support and is missing from the `.dat` reaction total (0.57 % at an 8 mm mesh,
  shrinking with element size). Compare the reaction with the load on the
  non-fixed nodes, recomputed from the `.inp` deck.
- `makeConstraintPressure`: positive pressure pushes into the face; CalculiX
  writes it as `*DLOAD` element-face loads (`P1` to `P4` for tetrahedra).
- The same reaction-total gap appears in heat transfer: see the next section.

## CalculiX heat transfer (ccx run directly)

- A structured hex deck written in Python avoids a FreeCAD session for box-like
  parts; run `ccx -i <job>` in the work folder.
- `NALL` exists only if the `*NODE` card says `NSET=NALL`; `*INITIAL
  CONDITIONS` on it fails otherwise.
- The `*NODE PRINT ... RFL, TOTALS=ONLY` total for fixed-temperature nodes is
  the conduction part only: the film load lumped on those same nodes is not in
  it (1.3 % of the fin heat flow at 1 mm elements). Add it back before an
  energy balance.
- The `.frd` prints temperatures with 6 significant digits; a `*NODE PRINT`
  of the nodes that matter gives 7 in the `.dat`. Check this is enough for the
  differences a GCI must resolve.

## CAD to mesh to solver (CadQuery -> STEP -> Gmsh -> CalculiX)

- Export a planar face with a +z normal. A face with a -z normal makes Gmsh
  number the triangles clockwise, and CalculiX rejects every element
  ("nonpositive jacobian").
- Gmsh CLI: `gmsh mesh.geo -2 -format inp -o mesh.inp` with
  `Mesh.ElementOrder = 2` writes 6-node `CPS6` triangles that CalculiX reads
  with `*INCLUDE`. Refine at a feature with a Distance + Threshold field on
  curves picked by `Curve In BoundingBox{...}`.
- Build the deck from the node numbers of the mesh it includes. After a
  remesh, a deck written for the previous mesh still runs and still balances
  its reactions, so equilibrium alone will not catch it.
- Apply a uniform edge traction on quadratic edges as consistent nodal forces:
  1/6, 4/6, 1/6 of each segment's load on corner, mid-side, corner nodes.
- **CalculiX plane-stress elements are not plane stress for a thick section.**
  They are expanded into one-layer 3D wedges of the section thickness. At a
  hole in a 4 mm plate (t/d = 0.4) that added part of the 3D thickness effect:
  Kt 3.045 against Kirsch's exact 3.000, converging to the wrong value with a
  clean observed order. For true plane stress, analyse a thin layer (about
  1 % of the feature size) and scale the forces by the same factor; stresses
  are unchanged, and reactions scale back.
- Write `*NODE FILE, OUTPUT=2D` and `*EL FILE, OUTPUT=2D` to get results on the
  2D nodes, which `harness/calculix.py` reads.
- **3D quadratic tets: Gmsh's second-order curving can invert an element.** The log says
  `1 elements with jac. < 0` (only a warning) and CalculiX then stops with "nonpositive
  jacobian" (exit 201). Remesh once with `Mesh.HighOrderOptimize = 1`: it moves the nodes of a
  small patch (0.2 s; minimum scaled Jacobian -0.019 -> +0.086) and changes nothing where no
  element is bad. The clevis backend does this automatically (8 of 21 candidates in one run).
- **`Mesh.MeshSizeFromCurvature` is a count per circle, independent of `MeshSizeMax`, and
  `MeshSizeMin` clamps it.** With a fixed count and `MeshSizeMin = h/4`, halving the global
  size barely refined a 3 mm fillet, so a global mesh study at the fillet peak was not a mesh
  study. Sweep a separate fillet element size (count = 2 pi r / h_f, minimum h_f / 2) or scale
  both with h.
- **A fillet peak needs local refinement.** At 3 mm fillets the peak von Mises under-read by
  6 % with 4 mm global tets (about 1.6 mm on the fillet) and settled only with fillet elements
  of r/3 or smaller; global refinement to 2.67 mm (180 k nodes) was still short. Once resolved,
  the peak (a nodal maximum on a tet mesh) wobbles by about +-0.5 to 0.8 % from mesh to mesh, so
  a three-level order test reads it as oscillatory or divergent by chance (clevis c011: 96.6 /
  97.6 / 96.8 / 96.7 MPa at 1.0 / 0.85 / 0.75 / 0.667 mm; design D: 97.36 / 97.54 / 98.33).
  Declare the measured scatter as the study's noise floor (`verification.mesh_noise_rel`).

## CalculiX equation solvers (the FreeCAD 1.1 build of ccx 2.22)

- SPOOLES runs on one core whatever `OMP_NUM_THREADS` / `CCX_NPROC_*` say; threads only speed
  assembly and stress recovery (1214 s -> 1150 s at 316 k nodes). Time goes up steeply with
  size: 140 k nodes about 4 min, 316 k about 20 min, about 700 k did not finish in 2 h.
- `SOLVER=ITERATIVE CHOLESKY` was 11 times faster but 0.6 % off in peak stress and 0.5 % in
  deflection, with no tolerance setting in the deck: not for verification evidence.
- `SOLVER=PARDISO` fails: "the PARDISO library is not linked".
- For throughput, run independent solves as parallel processes (24 cores here).

## CalculiX frequency (modal) analysis

- Units N, mm, tonne, s: steel density is 7.85e-9 t/mm^3 and frequencies come
  out in Hz. `*FREQUENCY` with the number of modes, `*NODE FILE` U.
- The .frd holds one DISP block per mode; `read_frd(...)["blocks"]` keeps them
  all in order (`out["DISP"]` alone is only the last mode).
- The .dat prints the eigenvalue table and the effective modal mass table
  (x, y, z, rx, ry, rz); `read_dat_frequency` parses both. Classify modes from
  the effective mass fractions instead of assuming an order.
- The totals leave out the mass of constrained nodes (about 0.5 % here), so
  compare effective-mass fractions, not absolute masses.
- Frequencies of quadratic tetrahedra on a fully clamped root converged at
  order 1.8, not the textbook 4: the clamp corners are singular. A rate below
  the design order is fine for the GCI; only a rate far above it is suspect.

## CalculiX structural, NLGEOM (static and dynamic; the Turek-Hron flag)

- **Plane strain from hexes:** one layer of C3D8I with every node held in z. The flag's
  benchmark is plane strain although it does not say so; the elastica only matched it with
  E / (1 - nu^2) (plane stress missed by 17 %).
- **Reaction totals leave out loads applied on the constrained nodes**, mechanical as well as
  thermal: under gravity the clamp's `RF, TOTALS=ONLY` was 0.357 % short of the weight, exactly
  the body load lumped on the clamp nodes (half the first element column). Compute that share
  from the mesh (consistent load, 2 x 2 Gauss on the first column) and add it back.
- **`*NODE PRINT` FREQUENCY is one setting for the whole step: the last request wins.** A
  centreline print with `FREQUENCY=10` (to get only the last increment) silently cut the
  point-A history, printed every increment, down to one block. Print everything at the same
  frequency and keep the last block in Python.
- The `.dat` prints 7 significant digits, so an equilibrium check closes to about 2e-7, not to
  the Newton tolerance; set its tolerance at 1e-6.
- St. Venant-Kirchhoff is plain `*ELASTIC` under `NLGEOM`; `*STATIC, DIRECT` with a fixed
  increment and `*CONTROLS, PARAMETERS=FIELD` `1.e-8, 1.e-6` converged in 2 iterations per step.

- **`*DYNAMIC, ALPHA=0` (trapezoidal rule) gains energy in a large-rotation problem.** It conserves
  energy only for linear problems. The released Turek-Hron flag climbed above its start height by
  2.9 / 1.27 / 0.45 / 0.07 % of its swing at dt 0.01 / 0.005 / 0.0025 / 0.00125 s over 6 s (about 4x
  less per halving), and the extra energy stiffened the swing and raised its frequency. Check the
  energy directly (an undamped body released from rest must return to its start height), and keep only
  the steps that pass in the GCI. ALPHA < 0 would damp the drift and the physics with it.
- **Measure a period from mid-level crossings, not from local extrema.** A sudden release also excites
  higher modes, which never decay without damping; a mode at 6.6 Hz riding on a 1.07 Hz swing made an
  extremum search find false troughs (a synthetic two-mode test read 1.71 Hz) and made the last-period
  frequency jitter between time steps. Downward crossings of the mid level with a quarter-amplitude
  hysteresis gave 1.0949-1.0952 Hz at every step. Test any signal-processing metric on a synthetic
  signal with the contamination you expect before trusting it.

## CalculiX contact (surface-to-surface, penalty)

- Two bodies that touch at a point: in a Gmsh .geo on the built-in kernel set
  `Geometry.AutoCoherence = 0`, or the coincident points merge and the bodies
  are glued at one node.
- Load by displacement, not force: before the contact closes, a force-loaded
  body is unconstrained and the solve is singular. Read the load back from
  `*NODE PRINT ... TOTALS=ONLY` RF and compare references at that load.
- Surfaces: `*SURFACE` from element faces (C3D8 S1..S6 = 1234, 5876, 1562,
  2673, 3784, 4851); build them from the mesh by testing face nodes against
  the analytic boundary. Slave = convex/finer body.
- `*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=LINEAR` with K about 50 E / h;
  check the penetration (COPEN in `*CONTACT FILE`) against the approach.
- Read contact pressure from `*CONTACT FILE` CPRESS, not from element stresses
  at the surface: on linear hexes the extrapolated surface stress read 3.5-6.5 %
  high while CPRESS was within 0.2 % of Hertz. The .frd CONTACT block lists all
  nodes (zeros away from the slave surface); filter to surface nodes.
- `*NODE FILE, FREQUENCY=10000` keeps only the last increment; otherwise every
  increment of the nonlinear step is written.
- Grade the mesh only near the contact: a size field graded over the whole
  model cost 7.6x the nodes for the same answer (0.2 %).
- A sampled maximum (largest nodal value) is not smooth in h and can fail a
  GCI while agreeing to 0.06 %; locate peaks between nodes (parabola) instead.
- **Coulomb friction itself is exact in CalculiX 2.22 surface-to-surface penalty contact.** A
  block sliding on a block (C3D8I, K and stick slope 50 E / h, mu 0.2) carried mu p A to 5e-5
  under uniform pressure and to 6e-7 under a central patch load. Use that exact case to separate
  a solver effect from a model effect before blaming the contact formulation.
- **Contact is evaluated on the deformed surfaces even with `NLGEOM=NO`.** In the bolted joint
  the interface tilts by about the strain under the side load, so the slip plateau fell short of
  mu F_V by 1.3e-3, independent of mesh, mu and penalty, but exactly linear in 1/E (1.31e-3 /
  1.32e-4 / 1.33e-5 at E / 10 E / 100 E) and 10 times larger for thin plates. Coulomb mu F_V is
  exact only for a rigid interface. To keep an exact check, add a companion solve at 100 E and
  extrapolate the slip load linearly in 1/E (`rigid_limit_slip`, numerics
  `rigid_limit_stiffness_factor`): 2e-7 from mu F_V. Report the deformable value as model form.
- Contact stresses at the end of a step: `*CONTACT FILE` / `CSTR` (read with
  `harness.calculix.read_frd`, blocks named CONTACT: CPRESS, CSHEAR1/2). Nodal values are fine
  for the ratio shear / (mu p) and the shear direction, but integrating them for a force total
  was 9 % off (extrapolation at the contact edge). `*CONTACT PRINT` with `CF` stopped with "no
  existing contact pair defined" for this surface-to-surface pair.
- One contact solve can stall on a particular mesh: the 0.7 mm joint hit a 4 h timeout while
  0.5 mm took 22 min. Swap the level (0.75 mm) rather than raise the timeout.

## CadQuery (OpenCASCADE)

- Measure every reported quantity back from the B-rep (faces, closed circular
  edges), not from the parameters.
- Re-import the STEP export and compare volume and features.
- **`+` on selectors (`SumSelector`) returns `list(set(...))`, and shapes hash by memory
  address**, so the edge order changes from run to run. Fed to `.fillet()`, that changed the
  fillet's face split (40 or 41 faces, same volume to 10 digits) and so the mesh: the same
  parameters gave 93.97 or 94.94 MPa, or a crash. Collect the edges yourself and pass them in a
  fixed geometric order (`models/fea/clevis_bracket.py`); test that two builds give a
  byte-identical STEP body (`tests/test_clevis_bracket.py`).

## OpenFOAM (openfoam.org v14, in WSL)

- Install: the openfoam.org apt repository downloads through SourceForge
  mirrors, which can time out. Download the `.deb` over HTTPS, check its SHA256
  against `apt-cache show`, then have the user `apt-get install` the local file
  (sudo needs the user's password).
- Calling from Windows: `wsl -- bash <script> <case> <bashrc>` with paths mapped
  `C:\x` → `/mnt/c/x`. Use a script file rather than an inline `bash -c` from
  PowerShell, which expands `$` first. From Git Bash, call `wsl` through
  PowerShell to avoid path mangling.
- blockMesh `simpleGrading` is last cell / first cell along each block edge.
  Check which end is the wall before choosing the ratio.
- `polyLine` edges give smooth curved walls (cosine contraction).
- `flowRateInletVelocity` with `profile laminarBL` gives a fully developed
  inlet at an exact flow rate; it needs `wallDist { method meshWave; }` in
  fvSchemes. Its written `U` contains nested sub-dictionaries with their own
  `value`, so a patch parser must match braces and take only the top-level
  `value`.
- `meanVelocityForce` is an fvConstraint in `system/fvConstraints`; it prints
  `pressure gradient = <kinematic>` each iteration.
- All-Neumann pressure (cyclic, walls, symmetry) needs `pRefCell` / `pRefValue`.
  Cyclic patches need at least two cells across.
- Use `foamPostProcess -func writeCellCentres -latestTime` for cell centres; its
  boundary values are face centres, useful for matching patch faces to cells.
- Pressure is kinematic (p/rho); multiply by density.
- Steady laminar SIMPLE: `residualControl` uses normalised initial residuals,
  which stall for fields that are exactly zero or uniform. See
  convergence-diagnosis.md.
- Write ASCII fields with `writePrecision 12` so mesh-convergence differences
  are resolved.


- **`flowRateInletVelocity` with `profile laminarBL` is not an exact parabola.** It normalises each
  face's wall distance by the largest distance among the inlet faces, not by the half-height, then
  rescales to the flow rate: on 22 inlet faces the Turek-Hron profile was +1.5 % at the walls and
  -1.6 % mid-channel (the heated channel's 0.57 % peak error at 20 cells was the same effect). When a
  benchmark prescribes the profile, use `fixedProfile` (`direction (0 1 0); origin 0; profile table
  (...)`, a few thousand points) and check the face values against it; the flow rate then carries
  the midpoint-sampling error 0.5 (face width / H)^2, which converges with the mesh.
- **Budget wall time per mesh level from a measured cost per iteration, and keep timeouts in the case.**
  The heated channel's SIMPLE iteration took 0.39 s at 80 cells across and 7.4 s at 160 (19x for 4x the
  cells, with the CPU shared by other runs), so the 160-cell point hit a fixed 2-hour backend timeout
  halfway through. Set `flow_iterations` from where the residuals actually reach the convergence check's
  limit (here about 1e-8 by iteration 940), and give the backend a `solver_timeout_s` numerics setting.
- **Gmsh `-setnumber` did not override a `DefineNumber` in the .geo** (the mesh came out unchanged);
  write the sizes into the .geo itself. `gmshToFoam` names patches after the physical groups and types
  them all `patch`: set `empty`, `wall` with `foamDictionary constant/polyMesh/boundary -entry
  entry0/<name>/type -set <type>`.

### OpenFOAM heat transfer (temperature as a passive scalar)

- Constant properties make temperature a passive scalar: keep `incompressibleFluid` and add
  the `scalarTransport` function object (`diffusivity viscosity; alphal 1/Pr`), with
  `div(phi,T)` in fvSchemes and a `T` solver in fvSolution.
- A `fixedGradient` wall (heat flux q/k) writes no wall value. Evaluate it as the BC does:
  wall-cell value + gradient x centre-to-wall distance.
- `linearUpwind` overshoots at a step in the wall condition (heated to adiabatic): +0.06 to
  +0.11 K at the last heated cell, exactly where the peak wall temperature is. **Bounded TVD
  schemes were not the fix** (heated channel, revision 2): `limitedLinear 1`, `limitedLinear 0.2`,
  `vanLeer` and `Minmod` all cycled from one iteration to the next (a cell flipping 0.025-0.1 K,
  the energy balance stuck at 4-7e-5), and under-relaxing T only masked it. Keep `linearUpwind`,
  which converges exactly; its overshoot is conservative and shrinks with the mesh, and the
  peak-vs-reference and GCI checks bound it. Where the overshoot is at the inflow (a flux spike),
  `cellLimited Gauss linear 1` for `grad(T)` removed it (cold plate, below).
- Judge scalar convergence on the field itself (keep two writes with `purgeWrite 2`, compare
  them), not on the normalised residual, which a limiter can hold near 1e-5.
- Validate a thermal-entry model against the Graetz solution (validation/graetz.py), not the
  fully developed Nusselt number: at Pe ~ 1400 a 50 mm channel never reaches it.
- **Don't solve each outer iteration's T system to machine precision.** With `relTol 0` and
  `tolerance 1e-14` every one of 1000 outer iterations took about 200 BiCGStab sweeps at 90 k
  cells (8 min per coupling pass, growing about 12x per mesh doubling). The outer iterations only
  converge the deferred `linearUpwind` correction, so `relTol 0.01` gave the same field to 5e-7
  at a third of the time (cold plate: numerics `temperature_solver_rel_tol`). Keep the tight
  absolute tolerance; judge convergence on the field, as above.
- **A step in the wall flux is a singular point for any wall-temperature reference.** Where a
  conducting plate starts, the flux jumps from zero and the wall temperature goes like x^(1/3)
  (Leveque); the maximum error against the no-axial-conduction reference sat in the cell at the
  step and did not converge (5.5 / 2.8 / 6.3 % at 20 / 40 / 80 cells). Compare outside a band of
  about 2 gap heights round each step (verification `wall_edge_exclusion_gaps`): there it
  converged at second order (1.04 / 0.27 / 0.08 %).

### CalculiX nodal stresses from full-integration hexes

- The `.frd` nodal stresses of C3D8 and C3D8I are about 4e-5 low even for a uniform field
  (uniform thermal rise, fully restrained: integration points and reactions exact, `.frd`
  0.99996 of it; C3D8R is exact). Negligible for most decisions, but it fails an exact-case
  check at 1e-6. When that precision matters, write `*EL PRINT, ELSET=EALL` / `S` and
  extrapolate the 8 integration points yourself (`harness/calculix.py`, `hex8_nodal_stress`:
  Gauss points at +-1/sqrt(3), xi fastest).
- An exact case run through the same deck writer and solver (uniform temperature, homogeneous
  strain) is what exposed it; the beam-theory comparison at 1 % never would have.

## Partitioned coupling (OpenFOAM <-> CalculiX, cold-plate chain)

- Match the meshes at the interface one to one (same cell size along the wall), so heat passes
  across exactly and the handoff energy check can be tight (1e-6 or better).
- Robin-Neumann coupling: the CFD takes the wall flux from the solid (fixedGradient,
  nonuniform list), the solid takes a film with a constant coefficient h* and sink
  T_wall,CFD - q/h*. Keep h* constant if an exact series reference for the solid needs it.
- **Coupling passes scale with the mesh, so budget for them.** The cold plate needed 21 passes at
  20 cells and 26 at 40 (Aitken, about 0.75 contraction per pass), not the under-10 a plate Biot
  number of 0.045 suggested: the rate is set by the coolant's local coefficient at the plate's
  leading edge, far above h*. Set `coupling_max_iterations` from a pilot run (60 here), and make
  each pass cheap (inner T tolerance, above) rather than cutting passes.
- The plain fixed point converges only as fast as 1 - h*/h_fluid for short-wavelength errors;
  where the coolant's local coefficient is far above h* (start of heating) that was 0.81 per
  iteration. Aitken dynamic relaxation fixes it (allow omega up to about 10).
- Aitken steps with omega > 2 amplify the rounding error of the total heat by |1 - omega| each
  pass (1.4e-6 after 20 passes). Rescale the flux to the known total after every step.
- The `functions` solver restarting from a temperature-stage time directory needs the frozen
  flow fields there (`p`, `U`, `phi`): the temperature stage writes only `T`. Copy them from the
  flow time before each pass.
- When the heated wall reaches the inlet cells, the fixed-temperature inlet draws heat back
  out, and an outlet column misses the last half cell of heating (5e-4 of the energy balance).
  Let the channel run past the heated region with adiabatic walls at both ends.
- A plate that conducts dumps a flux spike into the fresh coolant at its leading edge. With
  plain linearUpwind the cell just upstream undershot below the inlet temperature (24.58 C
  for a 25 C inlet). A cell-limited reconstruction gradient (`cellLimited Gauss linear 1`
  for `grad(T)` in the `linearUpwind` scheme) removed it and still converged exactly; the TVD
  flux limiters that cycled in the heated-channel study were not needed.

## Optimisation loops (harness/optimize.py)

- An optimiser pushes the design onto a constraint, so the verdict there depends on the
  discretisation error: give the constraints a design margin and confirm the optimum with a
  separate mesh study.
- **Size the margin from a measurement, not a guess.** 0.5 % was right for a smooth beam stress
  (tapered bracket: GCI 0.005 %). For a fillet peak, 1 % failed (clevis_opt) and 9 %, sized from
  a global mesh study, failed too (clevis_opt_r1), because that study never refined the fillet.
  What worked: at a candidate, refine where the peak sits until it settles; measure the scatter
  between designs a few hundredths of a mm apart; margin = offset of the optimisation mesh from
  the refined levels + their oscillation + the scatter (clevis_opt_r2: 1.05 + 0.65 + 0.25 ->
  2.5 %).
- **Mesh noise in the constraint stops COBYLA among slightly infeasible points**: at 4 mm the
  clevis stress scattered 1.5 % between near-identical designs, the trust region shrank onto
  the noise, and the reported optimum (the best candidate meeting the margin) was an early
  step. Resolving the peak helps, but the scatter is design-dependent: 0.23 % near one design,
  1.5 % where the next run converged (clevis_opt_r2), whose only feasible point was then the
  start. Measure the scatter where the optimiser ends, not where it began.
- **When the optimiser stalls in noise, choose the design from a local response surface**
  (`harness/response_surface.py`): fit the constraint linearly over the converged candidates
  (residual sd = the noise), start at their centroid, move the most mass-efficient dimensions
  until the fit sits 2 sd inside the limit, and never leave the sampled range. Then give that
  design its own verified run and mesh study; the fit only chooses it. The objective there was
  flat (370 +- 1 g), so the safe design cost 0.4 % of mass.
- Never let the optimiser see an unverified result: a candidate that fails any check returns
  an infeasible constraint vector. The smoke run rejected a candidate whose tip deflection
  broke the small-deflection assumption.
- SLSQP on the beam-theory reference stops with "positive directional derivative" at a corner
  where several constraints are active; judge it by constraint satisfaction, not its flag.
  The peak of a tapered beam's stress has a kink where it leaves the root (h_t / h_r = 1/2):
  constrain the stress at stations along the span as well as the analytic peak.

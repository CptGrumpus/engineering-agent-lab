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
- Solver outputs pass through the privacy redaction before `verify_point` sees them: the home folder becomes `~`.
  A work-folder path stored in the outputs then does not exist at verify time (study 7 thermal: the FE logs were never
  copied and the temp folders were left behind). `os.path.expanduser` it, or keep the path on the backend.

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
  differences a GCI must resolve. A nodal maximum that reads the same at 6 digits on all three meshes
  (139.363 C, a 74 K rise: 1.4e-5 per step) is above `discretization_uncertainty`'s default 1e-5 noise floor and
  gets classed divergent; pass `noise_floor` from the output's precision (study 7 thermal used 1e-4).

## CAD to mesh to solver (CadQuery -> STEP -> Gmsh -> CalculiX)

- Export a planar face with a +z normal. A face with a -z normal makes Gmsh
  number the triangles clockwise, and CalculiX rejects every element
  ("nonpositive jacobian"). In a hand-written .geo each surface follows its curve loop's direction, so a model
  with several surfaces easily mixes both: reorient the clockwise triangles when reading the mesh (corners 1 3 2,
  midsides 6 5 4; `models/motor/stator_section_ccx.py`).
- Gmsh's .inp writes the elements per geometric surface (`ELSET=Surface1` ...) and each physical group as a
  separate `*ELSET` listing element ids: read the regions from those lists, not from the element blocks' names.
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
- Modes are mass-normalised; the .dat also prints PARTICIPATION FACTORS (x, y, z, rx, ry, rz), Gamma_i = phi_i^T M r,
  with effective mass = Gamma_i^2 (study C prototype, 2026-11-23).
- **Input fields are at most 20 characters.** A node line rewritten with Python's `repr` (e.g. `1.2371056560109001e-15`,
  22 characters) stops ccx with a bare "*ERROR reading *NODE. Card image:" and exit 201. Write coordinates with
  `:.12g` (study H's thickness scaling, 2026-11-23).
- **`*NODE FILE` / `*EL FILE` requests carry over into later steps.** A `*STEADY STATE DYNAMICS` step after a
  `*FREQUENCY` step that wrote U and S writes them again for the whole mesh at every frequency point, real and
  imaginary: 16.5 GB of .frd on study C's 1.22 mm mesh, and reading it took 38 of 64 GB of RAM before the run was
  stopped (2026-11-23). Restate the requests in each later step, limited to what it needs (`*NODE FILE, NSET=TIP` /
  `*EL FILE, NSET=TIP`; 10x smaller on a coarse test, .dat printout unchanged). Check the .frd size on the coarsest
  mesh before a mesh study: it scales with the node count.
- **Harmonic base excitation** (`*FREQUENCY, STORAGE=YES`, then `*STEADY STATE DYNAMICS` f1, f2, n, bias with
  `*MODAL DAMPING` and `*BASE MOTION, DOF=3, AMPLITUDE=.., TYPE=ACCELERATION`): the output is the ABSOLUTE
  displacement (relative + the base's -a / w^2), one real and one imaginary block per frequency, with points added at
  the eigenfrequencies. Its modal damping acts on the absolute velocity, base included: each mode gets an extra
  forcing 2 j zeta w_i Gamma_i a / w, so q_i = (-Gamma_i + 2 j zeta w_i Gamma_i / w) a / (w_i^2 - w^2 + 2 j zeta w_i w).
  A Python modal sum with that term matches ccx to 1e-5 at every frequency (bar, 20 modes); without it the real part
  at resonance is off by Gamma phi / w_i^2 (4 % of the peak at zeta 0.02) and low-frequency imaginary parts by several
  times. Physical structural damping acts on the relative velocity: use ccx to verify the modal sum (with the term),
  then report the response without it.

## CalculiX axisymmetric (CAX8, study 18 head-to-shell junction)

- x is radial, y axial; nodes on the axis need u_r = 0 (dof 1). CalculiX expands CAX elements into a 2-degree wedge,
  and `*NODE PRINT ... RF` totals are for that segment: the axial reaction matched p pi Ri^2 to 6e-8 only after
  dividing by 2/360. The .frd keeps the 2D node numbers; S is SXX radial, SYY axial, SZZ hoop.
- A structured quad mesh written in Python (no CAD, no Gmsh) puts classification lines on element boundaries, so a
  line's corner and mid-side nodes are 2 n + 1 equally spaced points for Simpson's rule: no field sampling needed
  (`models/fea/vessel_head_axi.py`).

## CalculiX hyperelastic contact (study 12, O-ring)

- **Surface-to-surface contact would not converge** for a near-incompressible neo-Hookean ring (K = 1000 G, CAX8R)
  pressed by a steel plate: too many cutbacks in the first increment. Node-to-surface converged at once.
- **The second value of `*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=LINEAR` is sigma_inf, the tension carried at large
  clearance.** 1.0 MPa (fine for steel on steel) let the edges of a 2-3 MPa rubber contact pull, and the pressure
  integral missed the reaction by up to 47 %; use a small fraction of the expected pressure (0.01 MPa here).
- **Node-to-surface on quadratic faces lumps about equal areas per slave node**: corner and mid-side pressures alternate
  by about 30 %, and the trapezoid rule over the nodes reproduces the reaction (1.6 %) where Simpson's 1/6-2/3-1/6 does
  not (+11 %). Report contact pressure as a two-node average; CPRESS is written on the expanded 3D nodes of CAX
  elements (no simple map to the 2D numbers), so compute it as k x overclosure on the 2D nodes.
- **An axisymmetric ring squeezed between plates grows in diameter**: the incompressible squeeze spreads into the hoop
  too, so a ring with no radial restraint drifts outward (1.7-2.0 mm for a 3.53 mm ring at 20 %). A 2D plane-strain
  model hides it. Model the groove wall that locates the ring; the free ring is Lindley's case (his force relation
  matched the free FE ring within 0.6-10 % from 10 to 30 % squeeze).

## CalculiX linear buckling (`*BUCKLE`, study 13)

- **The .dat prints the static pre-buckling solution before the first eigenvector.** A parser that takes the first
  displacement block as mode 1 reads the axial pre-buckling field, and the mode-shape check fails (two wrong
  explanations came first: solver accuracy, support layout). Reuse `studies/strut_buckling.py` `read_dat_blocks` /
  the mode parser, which skip it (`tests/test_strut_buckling.py`).

## CalculiX structural, NLGEOM (static and dynamic; the Turek-Hron flag)

- **Plane strain from hexes:** one layer of C3D8I with every node held in z. The flag's
  benchmark is plane strain although it does not say so; the elastica only matched it with
  E / (1 - nu^2) (plane stress missed by 17 %).
- **`RF` is the internal nodal force, not the reaction**, mechanical as well as thermal: at a
  constrained dof it is the reaction minus the load applied on that node, and at a free dof it
  equals the load applied there. So a set's `RF, TOTALS=ONLY` (1) leaves out the loads on the
  constrained nodes: under gravity the flag clamp's total was 0.357 % short of the weight, exactly
  the body load lumped on the clamp nodes (compute it from the mesh and add it back); and (2)
  picks up loads in the free directions: on the rotor's symmetry edges about 135 N of centrifugal
  load showed up as a "reaction" along the edge and broke equilibrium by 1.6 % until only the
  constrained components were used (study 7). For nodes under `*TRANSFORM` the printed totals
  were in global axes.
- **`*NODE PRINT` FREQUENCY is one setting for the whole step: the last request wins.** A
  centreline print with `FREQUENCY=10` (to get only the last increment) silently cut the
  point-A history, printed every increment, down to one block. Print everything at the same
  frequency and keep the last block in Python.
- The `.dat` prints 7 significant digits, so an equilibrium check closes to about 2e-7, not to
  the Newton tolerance; set its tolerance at 1e-6.
- **Long undamped NLGEOM dynamics with small steps can diverge late: add a little HHT damping.** With `*DYNAMIC,
  ALPHA=0` (trapezoidal) the Turek-Hron flag at dt 0.000625 s saw its Newton iterations creep from 2 to 12 per step
  over 9300 steps, then diverge, while 0.00125 s never needed more than 4. Loosening the force criterion (1e-8 to
  1e-6) changed nothing, to the increment, so that was NOT the cause (the first diagnosis, now corrected). The cause
  was energy building up in the stiff high-frequency modes, which a smaller step resolves and the undamped rule never
  removes. `ALPHA=-0.05` (CalculiX's default) fixed it and moved the 1.1 Hz swing's frequency by under 1e-4. Check
  with a small-amplitude companion run and an energy (return-height) check. Use ALPHA = 0 only for short runs, or
  where the energy check proves the drift harmless.
- With HHT damping and the trapezoidal energy gain pulling in opposite directions, last-period amplitudes moved by
  only 0.03-0.09 % between steps, not monotonically, and the GCI gave no estimate. At that level the band of the
  published reference matters more: report the spread, and do not chase it.
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

## CalculiX plane stress under rotation (rotor overspeed, study 7)

- `*DLOAD, CENTRIF, omega^2, 0,0,0, 0,0,1` works on plane-stress elements (CalculiX expands them to wedges); keep the
  thin analysed layer of the strap study and scale concentrated loads by the same factor.
- A symmetry line that is not a coordinate axis: `*TRANSFORM, NSET=..., TYPE=R` with the line's direction as the first
  vector, then fix local dof 2 (the normal).
- **CalculiX rejects numbers longer than about 21 characters, on any card** ("ERROR reading *CLOAD" / "*NODE", card
  image shown): Python's repr of a small load (17 digits plus an exponent) crossed it only on a finer mesh, and a node
  at r = 3.07e-14 (cos 90 deg) did in study 18's head model. Write every number with `:.12g` / `:.12e`, and snap
  points that belong on an axis or plane to exactly 0.
- Check the pipeline on a plain annulus against the exact rotating disk (plane stress, free edges) before the pocketed
  part: 4e-4 on CPS6.
- Sharp pocket corners make the corner peak a singularity (742 / 929 / 1221 MPa over three meshes): judge a bridge by
  linearized stress along radial lines (`models/fea/rotor_ccx.py` `linearize`, Simpson's rule so a linear stress is
  integrated exactly).

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
- **Gmsh's quad recombination (`Mesh.Algorithm = 8; Recombine`) can wrap one cell around a convex corner.** At a 1.72 mm size
  (turek_hron_fsi1_noise_a) the flag's upper tip corner was shared by two quads (165 and 105 deg) instead of three of
  about 90; checkMesh said OK (max skewness 0.994, limit 4), every check passed, and uy(A) came out 28 % low; at 1.75
  mm the corner was clean again. It depends on the exact size, so nothing warns you: check the angles of the cells on
  the measured surface (`studies/turek_hron_fsi.py` `flag_cell_quality`), and rebuild a suspect mesh from the kept
  mesh.geo: Gmsh regenerates it exactly (same cell count), so a defect can be located after the run.
- **Gmsh `-setnumber` did not override a `DefineNumber` in the .geo** (the mesh came out unchanged);
  write the sizes into the .geo itself. `gmshToFoam` names patches after the physical groups and types
  them all `patch`: set `empty`, `wall` with `foamDictionary constant/polyMesh/boundary -entry
  entry0/<name>/type -set <type>`.

### OpenFOAM turbulent pipe flow (RANS on a periodic wedge, study 19)

- **checkMesh's aspect ratio on a wedge is about axial length / radial cell height.** A wedge mesh is 2D, so the
  3D measure is skipped and the face-area ratio in the two solution directions is what counts. A fixed axial
  length (D/50) against sub-micron wall cells at Re 2e6 gave 2884 and failed the mesh check.
  `numerics.axial_length_rule = "geometric_mean"` ties the length to the cells (sqrt(wall x axis cell), ratio about
  19 at both ends), and the converged f does not change (4e-8). **But it slows SIMPLE's convergence by orders of
  magnitude on wall-resolved grids** (study 19, r1): the same n160 mesh converged to 3e-11 in 15000 iterations with
  2 mm, and only to 9e-5 after 80000 with 0.10 mm; n320 and a probe at n640 never converged. Use the default D/50
  wherever checkMesh allows it (at Re 1e5 up to n320, ratio 759). Where it does not, shorten the length only as far as
  checkMesh needs, not to the geometric mean: n640 at Re 1e5 with 1 mm (half the default, ratio 760) converged, slowly
  (gradient steady to 1.6e-10 within the 300000-iteration cap; residuals never reach 1e-9), and n160 / n320 repeated
  their 2 mm values exactly (r3). Wall-function meshes converged fine with the rule.
- **The pressure residual never falls in a fully periodic domain** (pressure is a constant there): set its
  residual control to 1 and judge convergence on the meanVelocityForce gradient's history and on U, k, omega.
- **Until converged, the two routes to f disagree:** the wall shear and the meanVelocityForce gradient differ by the
  momentum still changing in the domain (7e-3 on the unconverged n320). The force-balance check is therefore also a
  convergence check; do not report the wall-shear f of a point that fails it.
- **k-omega SST with the sublayer resolved (y+ below 1) converges at about first order in f.** 0.01730 / 0.01783 /
  0.01813 / 0.01828 on 40 / 80 / 160 / 320 cells (wall cell halved each time; observed order 0.84, then 0.98),
  extrapolating to +2.4 % on Prandtl: the -0.9 % agreement at 80 cells was mesh error with the wrong sign. Do not
  quote one mesh's agreement; extrapolate, and expect a GCI near 1 % even at 320 cells.
- **Wall functions (nutkWallFunction, kqRWallFunction, omegaWallFunction, v14) sit about 5 % below Prandtl's
  smooth-pipe law** at Re 1e5 to 2e6, independent of the core mesh (GCI 0.02 %) and only weakly dependent on
  where the first cell sits (-5.23 to -4.75 % over cell-centre y+ 29-196). For a 5 % pressure-drop
  requirement, resolve the sublayer instead.
- **A wall-function mesh study must hold the wall cell and refine the core,** which needs room: at Re 1e5 the
  pipe radius is only about 2400 wall units, so a first cell of 100 leaves the grading uniform and refining
  shrinks the wall cell. Use a higher Reynolds number for that study.

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

## FEMM 4.2 and Pyleecan (electric machines, study 7)

- **FEMM 4.2, not FEMM 5, for Pyleecan.** pyFEMM drives FEMM's ActiveX server through win32com, which is
  what Pyleecan uses; FEMM 5 talks to scripts over TCP instead. After installing, open FEMM once so it
  registers `femm.ActiveFEMM`. `pip install pyfemm pywin32`. `femm.openfemm(1)` runs it hidden.
- First check through the whole chain: a 100 A wire, where B = mu0 I / (2 pi r) holds outside it whatever
  the mesh, with an A = 0 circle far out. FEMM's default mesh gave 0.1-0.5 %.
- **Pyleecan: use GitHub master, in its own environment.** The PyPI release (1.5.2, 2024) needs Python
  < 3.11 and pins numpy 1.23; master uses numpy 2 and PySide6 and installs on Python 3.14. Its setup.py
  reads a file with the Windows default encoding and fails: set `PYTHONUTF8=1`. Its bundled
  `Toyota_Prius.json` is the 2004 Prius (48 slots, 8 poles, 0.75 mm air gap).

- **The environment is pinned in `models/motor/pyleecan-env.txt`** (pip freeze, with the recreate steps).
- **SciDataTool from GitHub master too.** The PyPI 2.5.0 calls `numpy.string_`, which numpy 2 removed; master (2.5.1,
  commit c6f2497) works. Study 7 pins Pyleecan master 1e940df.
- **`Nt_tot` counts a mechanical revolution**, not an electrical period: set it to steps per electrical period x pole
  pairs (24 for the 4-pole-pair Prius gave only 6 samples per electrical period).
- **`OPdq(Id_ref, Iq_ref)` are RMS currents** (the class docstring says so; an early runner docstring said peak). Guard
  it: compare the imposed phase-current fundamental with sqrt(2) x the requested rms (`motor_torque`
  `current_amplitude`, exact to 1e-16). That check cannot catch a peak value put into `current_rms_A`: convert any
  quoted peak current (an inverter rating, a datasheet) to rms first and say so (eval `motor-peak-current-trap`).
- **Pyleecan's phase flux linkage has the opposite sign to the motor convention** v = R i + d(psi)/dt: with its currents
  and torque, mean(sum i d(phi)/dt) = minus torque x omega_m (magnitudes agreed to 0.05-0.1 %). Apply the sign
  explicitly in a power-balance check rather than comparing magnitudes, so a convention change fails loudly.
- **`out.elec.get_Is()` ignores time periodicity**: `get_along("time[oneperiod]")` returns a whole mechanical revolution
  (192 samples) while the flux linkage returns one electrical period (48). The time steps coincide, so select the
  current samples on the flux-linkage time axis.
- **`out.mag.Tem` "oneperiod" is the torque's own period**, shorter than the electrical period. At 48 steps per
  electrical period the slot-ripple cycle (6 x electrical for 48 slots / 8 poles) gets about 4 samples: the mean torque
  is fine, the peak-to-peak ripple is only approximate. Use more steps when ripple is a requirement.
- **SlotW11**: depth = H0 + H1 + H2 (H2 includes the round end); W1 is the width at the top of H1, W2 the width where
  the round starts; R1 = W2/2 gives a semicircular end.
- **HoleM50**: H3 is the magnet thickness AND the pocket thickness (the magnet fills it), and it grows inward from the
  outer edge, whose apex sits at depth H0. The arm angle is set by H0, H1 (bridge) and W0 together, so changing H0
  alone tilts the arms: re-solve W0 to keep a measured angle (study 7 machine build).
- **A magnet thinner than its pocket needs a user-defined hole.** HoleM50 always fills the pocket thickness (H3)
  with magnet; H2 only adds a vertex on the pocket side. Build the pocket with HoleM50, `convert_to_UD()` (keeps the
  magnetization angles), then replace each magnet rectangle by the magnet plus air strips (labels containing
  `HoleMag` / `HoleVoid`; magnets are numbered in list order). `get_magnet_dict()` works on both; `hole.magnet_0`
  does not exist on HoleUD (`models/motor/build_prius_ornl.py --design-magnet`, study 7 revision 4).
- **A new machine file must be added to `studies/motor_em.py`'s MACHINES** before a case can name it; otherwise the
  runner looks in Pyleecan's own data folder and every point fails in `load_json` (study 7 revision 4's first run).
- **Bundled machine files carry absolute material paths from Pyleecan's authors' computer** (`mat_type.path`).
  `tests/test_privacy.py` catches them once committed; strip them to file names when you build a machine
  (`models/motor/build_prius_ornl.py`).
- **Pyleecan's generic magnet** (Br 1.24 T, recoil permeability 1.05) matched the Prius sample's Br but not its recoil
  permeability (1.129, ORNL's measured line). Check both, and the temperature the source assumes.
- **FEMM through Pyleecan reproduces itself bit for bit** on the same machine, mesh fineness and rotor positions: a
  supplementary dq table that repeats one row of the main table matched it exactly in every column (torque, dq flux,
  all six iron-loss coefficients). That is what makes merging tables safe; keep one shared row as the check.
- **Hot magnets lose more flux than Br.** At 80 C (Br -6 %) the open-circuit flux fell 7.0 %: the saturated rotor
  bridges carry a roughly fixed leakage flux, so the loss comes out of the useful flux. Do not scale flux with Br.
- **A 25 A dq grid does not resolve light load at high speed.** Below 30 N m above 4000 rpm the loss-optimal current
  has iq 2-5 A, inside the first grid cell; the map from the half grid differed from the full one by up to 10
  efficiency points there (0.1 point median). Check the map itself (half table against full table), and refine the
  table's low-iq rows (6.25 A steps) rather than the whole grid. With 6.25 A rows the map resolved to 0.9 point from
  20 N m up (cold, verified), but the 10 N m row above 4000 rpm still switches between field-weakening branches
  (iq 2-4 A, id jumping up to 47 A between neighbouring speeds): report that row as unresolved rather than chase it.
  Revision 5 (2026-11-24) settled it: with rows at 3.125 and 9.375 A added the half-table check fell from 2.3 to 0.3
  points, and the old table already matched FEMM within 0.06 % there. The failing 'row' was the HALF table lacking
  low-iq rows, not the full table. Measure the full table at new nodes before calling a map row unresolved.
- **An every-second-node (half-table) check must keep both grid ends:** with an even node count (a merged column at
  -37.5 A) `[::2]` dropped id = 0 and the check extrapolated out of bounds (fixed: append the last index).
- **The dq torque equation drifts at low iq deep in field weakening:** at iq 6.25-12.5 A and id -175 to -300 A the
  mean torque is 33-70 N m with 18-27 N m of ripple, and 3 p (phi_d iq - phi_q id) from the mean fluxes missed FEMM's
  torque by up to 1 % (0.3 N m). Interpolate FEMM's torque for the map; the dq fluxes are for the voltage limit.
- **A loss-temperature iteration over a discrete loss search can have no fixed point:** study 7's thermal
  network picks the minimum-loss operating point at each iterate's magnet temperature; at 5500 rpm, 34 N m
  (revision 5, jacket h 1000) the chosen point jumps from id -46 to -39 A between 105 and 106 C (total loss
  -16 % for 1 K, in the low-iq field-weakening rows), and the iteration cycles between two states (8.8 K)
  for all 200 iterations. The coupling-convergence check caught it. Diagnose by scanning the operating point
  against the coupled temperature: a jump means the fixed point does not exist, so report it; relaxation
  would only hide it.
  Confirmed real (not interpolation) on tables refined at the jump's cell: the cycle survived unchanged (8.83 K).

- **FEMM returns B = 0 inside Pyleecan's air-gap element** (about 80.3-80.8 mm of the Prius's 0.775 mm gap): it has no
  mesh there. Sample the meshed air between it and the bore (or the rotor side), and say which radius.
- **Aligning a measured air-gap field by its zero crossings is degenerate for an IPM rotor**: the model's field stays
  near zero over about two slot pitches between poles, so "zeros at slots 1, 7, 13" fits a range of angles. Fit the
  angle by least squares on the normalised shapes (one parameter, amplitude free), and compare on the plateau: the
  flank slots move most with a degree of position error (ORNL's own half-poles disagree there by up to 20 %).
- **Pyleecan overwrites FEMM's solution per machine name** (`<pyleecan>/Results/em/Femm/<machine>_model.ans`): the
  next run of the same machine replaces it, so revision 5's open-circuit solution was lost to its torque run. The
  backend now copies it into each point as `solver/femm_last_step.ans` (the last operating point's last time step).

## ElmerFEM 2D magnetostatics (the independent motor model, study 7)

Install: the official Windows zip (`ElmerFEM-nogui-nompi-Windows-AMD64-rel26.1.zip`, CSC mirror
nic.funet.fi/pub/sci/physics/elmer/bin/windows/rel26.1/) unpacked to `~/tools/elmer-26.1/`; no admin rights. Set
`ELMER_HOME` to the unpacked folder and put its `bin` and `lib` on PATH (`models/motor/elmer_em.elmer_env`). The
26.1 package's solver banner says "9.0" (compiled 2026-01-20): record both. Mesh with the `gmsh` Python wheel
(4.15, optional dependency `em`), write MSH 2.2, convert with `ElmerGrid 14 2 machine.msh -out mesh`.
- **Magnetisation convention:** MagnetoDynamics2D uses B = mu (H + M) ('Magnetization 1/2'), so M = Hc = Br /
  (mu0 mu_r), the same number FEMM takes. Verified on a closed form (uniformly magnetised cylinder in air: B inside =
  Br / (1 + mu_r), -0.07 %); the other convention would read -11 %, the size of the effect study 7 was chasing.
- **'H-B Curve'** is H as a function of |B| (first column B). A plain `Real` table is piecewise linear and
  extrapolates its last segment; densify a sparse datasheet table with a monotone interpolation (PCHIP) so Newton
  sees a smooth slope.
- **VTU output is in metres** when `Coordinate Scaling = 0.001` is set (the mesh was in mm), and the `<Points>`
  array has no Name attribute. A post-processor that assumed mm read a field 1000x off and fitted the wrong nodes.
- **OpenCASCADE arcs:** dedupe points on rounded keys but create them at exact coordinates; rounding the
  coordinates to 1e-6 mm made an arc's start and end radii differ by ~2e-6 mm and `addCircleArc` failed. Split arcs
  near pi (OCC draws the shorter arc). `getParametrizationBounds` returns one-element arrays: unpack them.
- **Ring surfaces (Pyleecan SurfRing: an outer and an inner loop):** `addPlaneSurface([outer, inner])` in the OCC
  kernel gave outer + inner area, not a hole: the steel filled the shaft, bore and slots, the magnets were shorted
  and the flux linkage came out 10x low while the mesh study converged and nothing failed. Cut the inner face out
  (`occ.cut`) and check that the bodies' areas tile the domain exactly once (`build_mesh` raises otherwise).
- **Newton and B-H tables:** a piecewise-linear `Real` table put Newton in a two-state limit cycle (change alternating
  at 1e-4); `Real Cubic` removed it. On the Prius the change norm still stalls at 1.4e-3 while the flux linkages
  move under 1e-9 Wb from 30 to 120 iterations: judge convergence on the quantity you report, measured.
- **Mesh size:** with second-order triangles, gap 0.40 mm / holes 0.80 mm / far 6 mm (refinement 1.0) is about
  90,000 nodes on the full Prius machine, 162,000 at 0.7; one solve at 0.7 with 30 iterations takes about 80 s.

## Reading dimensions from published PDFs (PyMuPDF, study 7)

- Engineering figures in reports are often vector drawings: `page.get_text("words")` gives the dimension labels
  exactly, and `page.get_drawings()` the outline as line segments you can measure.
- Scale from a labelled circle, then **check the aspect ratio**: fit an ellipse to a feature that must be round (a rotor
  OD). ORNL/TM-2005/33 Fig. 21 was stretched 1.1 % in x; it showed as one pole's OD reading 0.7 mm larger than the next.
  Correct x and y separately before measuring positions; widths and thicknesses suffer less.
- Measure every repeat of a feature (8 poles, 48 slots) and report the spread; a small spread is the evidence that
  the reading is right.
- Labels govern; the outline confirms and fills gaps. Then overlay the model you built on the drawing's outline: that
  overlay is the check (it found Pyleecan's slot 50 % too large, and a pocket thickened on the wrong side).
- A dimension arrow placed loosely on a tapered feature is ambiguous; measure the outline at the parameter's own
  definition point (slot width at the shoulder, not where the arrow happens to sit).

## preCICE coupling (OpenFOAM v2512 + CalculiX, study 6)

- The preCICE OpenFOAM adapter (v1.4.0) supports the openfoam.com line v1812 to v2606, not
  openfoam.org v14 (its newest .org branch is OpenFOAM 10). Install openfoam.com v2512 beside v14; its
  bashrc is `/usr/lib/openfoam/openfoam2512/etc/bashrc`, outside the `/opt/openfoam*` the harness
  searches.
- preCICE 3.5 has no Ubuntu 22.04 package; 3.4.1 does. A simulated install (`apt-get install -s ./*.deb`)
  showed the dependencies (about 137 packages, Boost and PETSc) without sudo.
- `apt-get install openfoam2512-dev` downloads well over 1 GB; it can look stalled for minutes.
- The OpenFOAM adapter v1.4.0 builds without sudo: unpack the release tarball, source the v2512 bashrc,
  run `./Allwmake`. The library lands in `$FOAM_USER_LIBBIN`.
- **Smoke test the adapter pair before your own case:** the tutorials' `perpendicular-flap` with
  `fluid-openfoam` and `solid-calculix` (2026-11-21: 5 s run in about 10 min). Compare the flap-tip
  watchpoint (`solid-calculix/precice-Solid-watchpoint-Flap-Tip.log`) with
  `reference-results/watchpoints.tar.gz`. Its peak matched the OpenFOAM v2404 reference to 5 digits,
  with the largest difference 0.7 % of the peak.
- The tutorials' `reference-results/*.tar.gz` are Git LFS pointers in a plain clone. Fetch the real file from
  `https://media.githubusercontent.com/media/precice/tutorials/develop/<path>` and check it against the
  pointer's sha256.
- Use the tutorials' develop branch with adapter v1.4.0; the last tutorials release dates from 2024.
- **Clear the positional arguments before sourcing the openfoam.com bashrc in a script** (`set --`).
  `source` passes the script's own arguments on, and the v2512 bashrc parses them as its options: with a case
  path and a bashrc path inherited it crawled through `foamEtcFile` for minutes; cleared, it loads in 0.4 s.
  The openfoam.org v14 bashrc did not care, which is why run_heated.sh never showed it.
- Wetted node set for `ccx_preCICE`: leave out the clamped nodes. CalculiX drops loads on constrained nodes
  from its reaction totals, which breaks a force-transfer check (fluid force on the body + clamp reaction = 0);
  preCICE's conservative mapping hands their share to the neighbours.
- Coupled start-up from rest: relative convergence on near-zero forces costs 5-8 iterations per window at
  first, falling to 2-3 once the flow builds. A ramped channel inflow puts large unsteady forces on the body
  (the whole channel accelerates): drag ran ahead of the ramp (13 N/m at half speed in FSI1).
- **Lift jitter at every coupling window is coupling noise, not shedding** (FSI1, Re 20): about 600 sign changes in
  800 steps, +-2 % peak to peak, zero mean. A peak-to-peak steadiness check and an end-of-run value both pick it up.
  Judge steadiness by drift (the mean of each half of the last window) and report window means
  (`numerics.metric_average_s`, `verification.steady_measure = "drift"`); a coupling tolerance of 1e-6 instead of
  1e-4 cut the jitter 72 x for 19 % more coupling iterations and left the means unchanged to 5 digits.
- **Refining the solid is expensive and, for FSI1, nearly irrelevant:** 1.25 mm instead of 2.5 mm moved uy(A) by
  0.035 % and took 3 h 45 min instead of 51 min (ccx dominates once the solid has about 9500 nodes).
- **Under the adapter, CalculiX writes its `.dat` (`*NODE PRINT`) only at the last increment**, whatever FREQUENCY
  says: FSI3's flag.dat stayed 0 bytes for 7.7 h and 15000 increments, and FSI1's "2 s mean" of the clamp reaction
  equalled the end value to every digit. Fine for a steady case; a periodic case cannot average the reaction over
  whole periods from it, and the end-of-run balance of an oscillating body includes its inertia (FSI2's check read
  1.52 against 1e-2 and meant nothing). For a periodic force-transfer check compare what the solid RECEIVES each
  window with the fluid's force at the same instant: `<watch-integral mesh="..." name="Wet"
  scale-with-connectivity="false" />` in each participant writes `precice-<Participant>-watchintegral-Wet.log`
  (Time and the sums of every data on the mesh, columns named `Force0 Force1 ...`, every window; preCICE 3.4.1).
  FSI1 smoke (5 mm, 40 windows): received against written 0.0 (the conservative RBF mapping keeps the sum exactly),
  written against OpenFOAM's forcesFlag 2.8e-9. Take per-window histories from these logs and the watchpoint log,
  not from the `.dat`.
- **Test that a fallback path cannot replace the quantity a check is defined on.** The periodic force-transfer
  check fell back, silently, to end values when its whole-period means were empty; report "not evaluable"
  (a NaN value fails visibly) instead.
- Turek-Hron FSI2 (density ratio 10, Re 100) at fluid 2.5 mm, dt 0.001: the oscillation grows from rest with no
  imposed perturbation (from about 5 s) and is periodic by 9 s; 7.2 coupling iterations per window at 1e-5 (twice
  FSI1's), 15000 windows in 7 h 42 min while sharing the CPU; every quantity within 2.1 % of the benchmark.

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

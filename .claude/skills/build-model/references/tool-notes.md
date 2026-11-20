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

## CadQuery (OpenCASCADE)

- Measure every reported quantity back from the B-rep (faces, closed circular
  edges), not from the parameters.
- Re-import the STEP export and compare volume and features.

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

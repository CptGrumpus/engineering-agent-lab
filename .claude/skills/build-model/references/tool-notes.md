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

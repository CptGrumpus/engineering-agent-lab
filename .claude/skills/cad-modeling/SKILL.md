---
name: cad-modeling
description: Build detailed CAD for a study in CadQuery (the real part with the features a drawing shows: keyways, fillets, chamfers, grooves, holes, welds, bolts), export STEP, mesh it in Gmsh, and check the detailed model against the study's verified idealised one and against hand volumes. Use when a study needs a 3D part or assembly, when upgrading an idealised model (beam, 2D, axisymmetric) to real geometry, when a feature might change a verdict, or when a page needs a CAD deliverable (STEP, drawing, render).
---

# Detailed CAD for a study

The geometry should be the part a client would hand over, not a stand-in. A detailed model earns its place only
when the study shows whether each feature matters: keep the verified idealised model and use it as the check.
Worked example: study 26 (`models/fea/keyed_shaft.py` for the analysed half model, `models/cad/intermediate_shaft.py`
for the whole part, `tests/test_intermediate_shaft.py`).

## Two models, one source of dimensions

- **The analysed model** (in the study's model module): only the region the verdict depends on, cut to symmetry,
  built from the case parameters.
- **The deliverable part** (`models/cad/<part>.py`): the whole part with every drawing feature, as a dict of named
  designs (`DESIGNS = {"d36": {...}, "d40": {...}}`), `build(design)`, `hand_volume(design)`, `export(design, path)`,
  and a `__main__` that writes `portfolio/cad/<part>_<design>.step`. A design per verdict: the one that fails, the
  one recommended, any alternative the study found.
- The dimensions the study analysed come from the study; every other dimension is a plausible layout, marked
  `[synthetic]` in the source and said so on the page. Standard features (DIN 6885 keyways, DIN 471 grooves,
  bearing seats) from published tables, with the source named; a paid standard not read is said so.

## Build

- CadQuery (`.venv`, 2.8): a half profile revolved (`Workplane("XZ")`, `radiusArc` for concave fillets, revolve
  about the axis) or a sketch extruded, then features cut or added as solids. No hand-edited geometry.
- Fillets: round the cutter, not the part (`cutter.faces("<X").edges().fillet(r)` before `cut`): concave fillets
  on the part fail more often in OpenCASCADE than convex ones on a tool. An end-milled keyway is `slot2D` on a
  YZ workplane, extruded past the surface, its bottom edges filleted to the corner radius.
- Symmetry: cut to the half or quarter with `intersect(box)` only when the geometry is symmetric about that plane;
  a reflection reverses a torque, so torsion takes the antisymmetric condition (u_x = u_z = 0 on y = 0).
- Check every solid: `isValid()`, then its volume against a hand calculation, as a test:
  - the revolved body by cylinders plus Pappus for fillets and chamfers (concave fillet r on radius a: spandrel area
    r^2 (1 - pi/4), centroid at a + r (10 - 3 pi) / (3 (4 - pi))): agrees to 1e-9;
  - each cut feature against the analysed model's (twice the half model's removed volume): agrees to about 1e-4,
    OpenCASCADE's volume integration on blended faces differs 1-2.5e-5 between a whole and a half solid.
  Parametrize the tests over `DESIGNS`, so a new design is checked without new code.
- Sketch signs: `radiusArc(end, r)` bulges one way, `-r` the other. A W-section's root fillets drawn with the wrong
  sign came out 4.7 % heavy (portal knee): only the hand volume showed it.
- Rolled shapes: root fillets r = kdes - tf reproduce the tabulated area (0.5 %) but not the tabulated Ix (0.3-0.8 %
  low: the rolled profile differs). Beam theory checked against the solid uses the drawn section's own Ix, or the gap
  lands in whatever the check is meant to measure (a 4 % bias on the knee's spring).
- Assemblies (bolted joints): each part a separate solid in a `cq.Assembly`, saved as one STEP (`asm.export(...,
  exportType="STEP")`; `save` is deprecated in 2.8; 1.2-1.6 MB for a 56-72 part knee, 126 kB for a 6-part rotor).
  A keyway's curved top: integrate it (`models/cad/fan_rotor.keyway_volume`) and test the quadrature on a closed
  form. Test by part type (plate with holes, hex head and nut with
  its hole, washer annulus, shank from the grip, weld triangle x length) against hand volumes, and pairs of
  neighbours for interference (`a.intersect(b)` empty). See `models/cad/portal_knee.py`.
- Welds on a saddle (a nozzle in a shell): fuse the parts, fillet the corner edge (select it as the edges lying on
  both cylinders), and take the weld as the filleted union minus the union: the weld then matches the analysed
  model's fillet exactly. Hand volume: Pappus in each meridional plane of the nozzle, V = integral of A(phi)
  rho_c(phi) d phi, the section a fillet spandrel whose corner opens from 90 deg (plane along the shell) to 90 deg +
  asin(rho / R) (across it): 0.8 % at a 10 mm fillet on a 112 mm nozzle, shrinking as f^2; test that shrinkage too
  (`models/cad/vessel_nozzle.py`). Saddle-cut layers (shell, pad) integrate exactly over the disk in the (y, z)
  plane: wall thickness sqrt(R2^2 - y^2) - sqrt(R1^2 - y^2), with y = a sin(theta) to keep the integrand smooth.
- **Check a deliverable's supports against the analysis's end conditions, not only its volume.** Study 13's strut
  was first drawn with its pins through the 16 mm thickness, which clamps the weak axis the analysis assumed
  pinned (the buckling load would be about 4x the analysed); the volume test passed. Pins across the width, eyes in
  the plane of the thickness (models/cad/strut.py, tested by a probe along the pin axis).
- A hand volume catches a drill that breaks out of a face: a 6 mm port centred 2.5 mm under a cold plate's top
  face cut through it under the brazed cover (a leak path); the CAD removed less than the hand formula, 3e-4 off
  (models/cad/cold_plate.py, 2026-11-27). Intended overlaps (an O-ring drawn free against its cover, a screw's
  shank in its tapped hole) are measured against their own hand formulas, not exempted (models/cad/oring_cover.py).
- OpenCASCADE's default `Volume()` is good to only about 1e-6 on saddle-cut faces; for a 1e-8 test call
  `BRepGProp.VolumeProperties_s(shape, props, 1e-9)` (agrees with the quadrature to 1e-13).
- **An extruded section with many features (a lamination): one closed outline, no booleans.** Write every feature
  (ears, notches, reliefs) as edges of the outer wire and the slots as the inner wire, then `Face.makeFromWires` and
  `Solid.extrudeLinear`. A relief tangent to an ear's flank is the tangent contact OCC booleans fail on. Check the
  face by its exact area: lines plus each arc's circular segment by Green's theorem (`loop_area`, 1e-13 on a
  400-edge stator); check each feature's edges by closing them with the outer circle and comparing a closed form or an
  independent grid count (`models/cad/prius_motor.py`, 2026-11-27).
- Repeated parts in a STEP assembly: add one shape several times with a rotated `cq.Location`; the writer instances
  it. 48 windings and 16 magnets as instances cut the motor from 4.3 to 2.8 MB. Test the round trip: solid count,
  total volume, and the instances' centres against the built parts.
- **Undimensioned features from a client's PDF drawing:** measure the vector paths (PyMuPDF `get_drawings`). Scale by
  a dimensioned circle with an ellipse fit (pages are scaled unevenly, 1.1 % on the motor drawing), then check against
  a second dimensioned circle and the dimensioned features. Dimension and extension lines land in the measurement
  windows: plot each feature locally before trusting a number (`scripts/motor_drawing_stator.py`). Check each view's
  registration against the model frame: the drawing's slots sat half a pitch from the model's, so features placed by
  angle alone would have landed on slots instead of teeth. Read the drawing, not an audit's summary of it (an audit
  recorded four hub keys; the drawing shows two).
- Weigh the part against the client's bill of materials. The motor core was 0.9 % light without the drawing's ears and
  notches and 0.02 % off with them: the check confirms the features and the density together.

## Mesh

- Gmsh imports the STEP (`occ.importShapes`). Find feature faces by bounding box (a fillet face has an extent of
  r in one direction), not by tag: tags change with the CAD.
- Size by distance to the feature faces (`Distance` field, `SurfacesList`) plus a growth rate; Gmsh's MathEval
  has no `Atan2` and rejects `*-1`, so write angular bands as distances outside a wedge, coefficients in parentheses.
- Quadratic tetrahedra invert where one element spans a small arc: size every small radius at no more than 0.75 r,
  also in a coarse global model, run `optimize("HighOrderElastic")` and check the minimum scaled Jacobian. A rare
  inversion can still occur (1 in 54 k elements on the keyed shaft): keep the mesh-quality check on every point.
- Thin walls (a W-shape's half web is 3.4 mm in a half model) and fillets: let Gmsh size by curvature
  (`Mesh.MeshSizeFromCurvature` 10 per circle) and keep the far size near 4 x the wall; 25 mm elements on the knee's
  3.4 mm half web inverted 23-45 elements.
- CalculiX's SPOOLES (the FreeCAD build) stalls past about 350 k nodes (a 540 k-node solve gave nothing in 25 min; a
  399 k-node knee crashed with a segmentation fault after 2 min). Plan mesh studies to finish under about 300 k.
  Past that, submodel: a coarse global model, then the part cut by a box around each feature, meshed finely, its cut
  faces driven by the global displacements (`*SUBMODEL, TYPE=NODE, INPUT=global.frd`, `*BOUNDARY, SUBMODEL, STEP=1`).
  - Scan the global model's peak along each feature before drawing the box: a neighbouring feature moves it (the
    keyway moved the shoulder fillet's torsion peak to the far side of the shaft).
  - Read no peak within about 1 mm of a driven face.
  - Check the path with a case the idealised model already answered (the keyless shaft, within 0.4 %), and compare
    the global and submodel peaks where the global mesh resolves the feature; check separately that the global
    peak lies inside a submodel box (a small Kt gap does not prove it: r0's near box missed the peak at 1 %).
- Decks: at most 20 characters per field; write numbers with `f"{v:.14g}"`.

## Deliver

- STEP files in `portfolio/cad/` (about 150 kB for a shaft); check the header holds no user or path
  (`FILE_NAME` reads 'Author'), and run `tests/test_privacy.py`.
- A dimensioned drawing and a render from the same solid are the dashboard session's (`scripts/make_drawings.py`,
  `render-results`): send it the STEP paths and the feature to show.
- The page links the STEP files, says which dimensions are analysed and which synthetic, and states the checks
  (hand volume, feature volume against the analysed model). Record in the case header what the detailed model adds
  over the idealised one, and what it changed in the answer.

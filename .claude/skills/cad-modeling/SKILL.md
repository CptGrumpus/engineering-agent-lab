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

## Mesh

- Gmsh imports the STEP (`occ.importShapes`). Find feature faces by bounding box (a fillet face has an extent of
  r in one direction), not by tag: tags change with the CAD.
- Size by distance to the feature faces (`Distance` field, `SurfacesList`) plus a growth rate; Gmsh's MathEval
  has no `Atan2` and rejects `*-1`, so write angular bands as distances outside a wedge, coefficients in parentheses.
- Quadratic tetrahedra invert where one element spans a small arc: size every small radius at no more than 0.75 r,
  also in a coarse global model, run `optimize("HighOrderElastic")` and check the minimum scaled Jacobian. A rare
  inversion can still occur (1 in 54 k elements on the keyed shaft): keep the mesh-quality check on every point.
- CalculiX's SPOOLES (the FreeCAD build) stalls past about 350 k nodes (a 540 k-node solve gave nothing in 25 min).
  Past that, submodel: a coarse global model, then the part cut by a box around each feature, meshed finely, its cut
  faces driven by the global displacements (`*SUBMODEL, TYPE=NODE, INPUT=global.frd`, `*BOUNDARY, SUBMODEL, STEP=1`).
  - Scan the global model's peak along each feature before drawing the box: a neighbouring feature moves it (the
    keyway moved the shoulder fillet's torsion peak to the far side of the shaft).
  - Read no peak within about 1 mm of a driven face.
  - Check the path with a case the idealised model already answered (the keyless shaft, within 0.4 %), and compare
    the global and submodel peaks where the global mesh resolves the feature, with the distance between the peaks.
- Decks: at most 20 characters per field; write numbers with `f"{v:.14g}"`.

## Deliver

- STEP files in `portfolio/cad/` (about 150 kB for a shaft); check the header holds no user or path
  (`FILE_NAME` reads 'Author'), and run `tests/test_privacy.py`.
- A dimensioned drawing and a render from the same solid are the dashboard session's (`scripts/make_drawings.py`,
  `render-results`): send it the STEP paths and the feature to show.
- The page links the STEP files, says which dimensions are analysed and which synthetic, and states the checks
  (hand volume, feature volume against the analysed model). Record in the case header what the detailed model adds
  over the idealised one, and what it changed in the answer.

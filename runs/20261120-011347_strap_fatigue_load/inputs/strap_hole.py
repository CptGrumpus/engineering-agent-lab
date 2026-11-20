"""CAD-to-FEA pipeline: strap with a central hole in tension.

1. CadQuery builds the quarter plate (symmetry about x = 0 and y = 0) as a
   planar face with a +z normal and exports STEP.
2. A Gmsh .geo script meshes the STEP face with 6-node triangles, refined at
   the hole edge by a distance field, and writes an Abaqus .inp.
3. This module writes the CalculiX deck from that mesh: plane stress section,
   symmetry constraints, and consistent nodal forces for a uniform traction on
   the loaded end.

Traps handled here (found in the hand run):
- numpy floats must be cast to float before formatting (numpy 2 prints
  np.float64(...)).
- The face must have a +z normal, or Gmsh orders the triangles clockwise and
  CalculiX reports negative Jacobians.
- The deck must be built from the node numbers of the mesh it includes.
- CalculiX expands plane-stress elements into one-layer 3D wedges of the
  section thickness. For a thick plate at a hole that adds part of the 3D
  thickness effect (Kt +1.5 % at t/d = 0.4 against Kirsch's exact 3.000), so
  it is not plane stress. The deck therefore analyses a thin layer
  (ANALYSIS_THICKNESS_RATIO x hole diameter) with the load scaled by the same
  factor: stresses are those of true plane stress; forces are scaled back.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

PARAMS = ("length_mm", "width_mm", "thickness_mm", "hole_diameter_mm", "axial_load_N",
          "youngs_modulus_MPa", "poisson_ratio", "yield_strength_MPa",
          "hole_element_size_mm", "far_element_size_mm")

TOL = 1e-6  # mm, for picking nodes on straight edges
ANALYSIS_THICKNESS_RATIO = 0.01  # analysed layer thickness / hole diameter (see docstring)


def hole_element_size(params: dict) -> float:
    if "hole_element_ratio" in params:
        return float(params["hole_element_ratio"]) * float(params["hole_diameter_mm"])
    return float(params["hole_element_size_mm"])


def build_step(params: dict, path: Path) -> float:
    """Quarter-plate face (+z normal, at z = 0) to STEP. Returns its area (mm^2)."""
    import cadquery as cq

    L2, W2 = float(params["length_mm"]) / 2, float(params["width_mm"]) / 2
    r = float(params["hole_diameter_mm"]) / 2
    solid = (cq.Workplane("XY").rect(L2, W2, centered=False).extrude(1)
             .cut(cq.Workplane("XY").circle(r).extrude(1)))
    face = solid.faces(">Z").val().translate(cq.Vector(0, 0, -1))
    if face.normalAt().z <= 0:
        raise RuntimeError("quarter face normal is not +z")
    cq.exporters.export(cq.Workplane().add(face), str(path))
    return float(face.Area())


def write_geo(params: dict, path: Path, step_name: str = "quarter.step") -> None:
    r = float(params["hole_diameter_mm"]) / 2
    h_hole, h_far = hole_element_size(params), float(params["far_element_size_mm"])
    e = 1e-3
    path.write_text(f"""SetFactory("OpenCASCADE");
Merge "{step_name}";
hole() = Curve In BoundingBox{{{-e}, {-e}, -1, {r + e}, {r + e}, 1}};
Field[1] = Distance; Field[1].CurvesList = {{hole()}}; Field[1].Sampling = 400;
Field[2] = Threshold; Field[2].InField = 1;
Field[2].SizeMin = {h_hole!r}; Field[2].SizeMax = {h_far!r};
Field[2].DistMin = {r / 2!r}; Field[2].DistMax = {6 * r!r};
Background Field = 2;
Mesh.MeshSizeExtendFromBoundary = 0; Mesh.MeshSizeFromPoints = 0; Mesh.MeshSizeFromCurvature = 0;
Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 0;
Physical Surface("PLATE") = Surface{{:}};
""", encoding="utf-8")


def read_mesh_nodes(mesh_inp: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    text = Path(mesh_inp).read_text(encoding="utf-8")
    block = text.split("*NODE", 1)[1].split("*", 1)[0]
    rows = np.array([[float(v) for v in ln.split(",")] for ln in block.strip().splitlines()])
    return rows[:, 0].astype(int), rows[:, 1], rows[:, 2]


def write_deck(params: dict, mesh_inp: Path, deck: Path) -> dict:
    """CalculiX deck for the quarter model. Returns load bookkeeping."""
    ids, x, y = read_mesh_nodes(mesh_inp)
    L2, W2 = float(params["length_mm"]) / 2, float(params["width_mm"]) / 2
    t, F = float(params["thickness_mm"]), float(params["axial_load_N"])
    ta = ANALYSIS_THICKNESS_RATIO * float(params["hole_diameter_mm"])
    scale = ta / t  # forces in the analysed layer / forces in the real plate
    xsym = ids[np.isclose(x, 0.0, atol=TOL)]
    ysym = ids[np.isclose(y, 0.0, atol=TOL)]
    end = np.isclose(x, L2, atol=TOL)
    order = np.argsort(y[end])
    eids, ey = ids[end][order], y[end][order]
    if len(eids) < 3 or len(eids) % 2 == 0:
        raise RuntimeError(f"loaded edge has {len(eids)} nodes; expected an odd count")
    q = scale * (F / 2) / W2              # N/mm along the loaded edge, thin analysed layer
    load = np.zeros(len(eids))
    for k in range(0, len(eids) - 2, 2):  # corner, mid-side, corner on each quadratic edge
        seg = ey[k + 2] - ey[k]
        load[k] += q * seg / 6
        load[k + 1] += q * seg * 4 / 6
        load[k + 2] += q * seg / 6

    def nset(name, arr):
        return f"*NSET, NSET={name}\n" + "\n".join(str(int(i)) for i in arr) + "\n"

    E, nu = float(params["youngs_modulus_MPa"]), float(params["poisson_ratio"])
    cload = "".join(f"{int(i)}, 1, {float(f)!r}\n" for i, f in zip(eids, load))
    deck.write_text(
        f"*INCLUDE, INPUT={Path(mesh_inp).name}\n" + nset("XSYM", xsym) + nset("YSYM", ysym)
        + f"*MATERIAL, NAME=AL\n*ELASTIC\n{E!r}, {nu!r}\n"
        + f"*SOLID SECTION, ELSET=PLATE, MATERIAL=AL\n{ta!r}\n"
        + "*BOUNDARY\nXSYM, 1, 1, 0.\nYSYM, 2, 2, 0.\n"
        + "*STEP\n*STATIC\n*CLOAD\n" + cload
        + "*NODE FILE, OUTPUT=2D\nU\n*EL FILE, OUTPUT=2D\nS\n"
        + "*NODE PRINT, NSET=XSYM, TOTALS=ONLY\nRF\n*END STEP\n",
        encoding="utf-8")
    return {"nodes": int(len(ids)), "loaded_edge_nodes": int(len(eids)),
            "applied_load_N": float(load.sum()) / scale, "xsym_nodes": int(len(xsym)),
            "analysis_thickness_mm": ta, "force_scale": scale}

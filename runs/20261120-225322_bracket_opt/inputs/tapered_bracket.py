"""CAD-to-FEA static pipeline: linearly tapered cantilever bracket with a tip load.

1. CadQuery builds the bracket (x along the length from the clamped root at x = 0, y across
   the constant width, z through the height, centred; height h_r at the root tapering
   linearly to h_t at the tip) and exports STEP.
2. A Gmsh .geo script meshes the solid with 10-node tetrahedra of uniform size and writes an
   Abaqus .inp.
3. This module writes the CalculiX deck: steel, the root face fully fixed, the tip load as a
   uniform shear traction on the tip face (consistent nodal forces on the quadratic faces:
   the corner nodes of a 6-node triangle take nothing, each mid-side node a third), static
   step, nodal displacements and stresses.

Units: N, mm, MPa, tonne. numpy floats are cast before formatting; the deck is always built
from the node numbers of the mesh it includes.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

PARAMS = ("length_mm", "width_mm", "root_height_mm", "tip_height_mm", "youngs_modulus_MPa",
          "poisson_ratio", "density_t_per_mm3", "tip_load_N", "element_size_mm")
TOL = 1e-6
# C3D10 faces: corner nodes and mid-side nodes (0-based, CalculiX/Abaqus order)
TET10_FACES = (((0, 1, 2), (4, 5, 6)), ((0, 1, 3), (4, 8, 7)), ((1, 2, 3), (5, 9, 8)),
               ((0, 2, 3), (6, 9, 7)))


def build_step(params: dict, path: Path) -> float:
    """Bracket solid to STEP. Returns its volume (mm^3), measured from the B-rep."""
    import cadquery as cq

    L, b = float(params["length_mm"]), float(params["width_mm"])
    hr, ht = float(params["root_height_mm"]), float(params["tip_height_mm"])
    pts = [(0.0, -hr / 2), (L, -ht / 2), (L, ht / 2), (0.0, hr / 2)]
    solid = cq.Workplane("XZ").polyline(pts).close().extrude(b / 2, both=True)
    cq.exporters.export(solid, str(path))
    return float(solid.val().Volume())


def write_geo(params: dict, path: Path, step_name: str = "bracket.step") -> None:
    hsize = float(params["element_size_mm"])
    path.write_text(f"""SetFactory("OpenCASCADE");
Merge "{step_name}";
Mesh.MeshSizeMax = {hsize!r}; Mesh.MeshSizeMin = {hsize!r};
Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 0;
Mesh.Optimize = 1;
Physical Volume("BRACKET") = Volume{{:}};
""", encoding="utf-8")


def read_mesh(mesh_inp: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(node ids, coordinates, C3D10 connectivity as node ids) from the Gmsh .inp."""
    text = Path(mesh_inp).read_text(encoding="utf-8")
    block = text.split("*NODE", 1)[1].split("*", 1)[0]
    rows = np.array([[float(v) for v in ln.split(",")] for ln in block.strip().splitlines()])
    ids, xyz = rows[:, 0].astype(int), rows[:, 1:4]
    elems = []
    for part in text.split("*ELEMENT")[1:]:
        head, _, body = part.partition("\n")
        if "C3D10" not in head.upper():
            continue
        buf = []
        for ln in body.splitlines():
            if ln.startswith("*"):
                break
            buf += [int(v) for v in ln.replace(",", " ").split()]
        elems += [buf[k + 1:k + 11] for k in range(0, len(buf), 11)]
    return ids, xyz, np.array(elems, dtype=int)


def tip_loads(params: dict, ids, xyz, elems) -> tuple[dict, float]:
    """Consistent nodal forces (z) for a uniform shear traction F / A_tip on the tip face.

    Returns ({node id: Fz}, tip face area measured from the mesh)."""
    L, F = float(params["length_mm"]), float(params["tip_load_N"])
    pos = {int(i): k for k, i in enumerate(ids)}
    on_tip = np.isclose(xyz[:, 0], L, atol=TOL)
    faces = []
    for conn in elems:
        tip = [on_tip[pos[n]] for n in conn]
        for corners, mids in TET10_FACES:
            if all(tip[c] for c in corners) and all(tip[m] for m in mids):
                P = xyz[[pos[conn[c]] for c in corners]]
                area = 0.5 * float(np.linalg.norm(np.cross(P[1] - P[0], P[2] - P[0])))
                faces.append(([conn[m] for m in mids], area))
    a_tip = sum(a for _, a in faces)
    loads: dict = {}
    for mids, area in faces:
        for m in mids:
            loads[int(m)] = loads.get(int(m), 0.0) - F * area / a_tip / 3.0   # -z
    return loads, a_tip


def write_deck(params: dict, mesh_inp: Path, deck: Path) -> dict:
    ids, xyz, elems = read_mesh(mesh_inp)
    root = ids[np.isclose(xyz[:, 0], 0.0, atol=TOL)]
    if len(root) < 3:
        raise RuntimeError("no nodes found on the root face x = 0")
    loads, a_tip = tip_loads(params, ids, xyz, elems)
    if not loads:
        raise RuntimeError("no element faces found on the tip face x = L")
    tip = ids[np.isclose(xyz[:, 0], float(params["length_mm"]), atol=TOL)]
    E, nu = float(params["youngs_modulus_MPa"]), float(params["poisson_ratio"])
    rho = float(params["density_t_per_mm3"])
    lines = [f"*INCLUDE, INPUT={Path(mesh_inp).name}", "*NSET, NSET=ROOT"]
    lines += [", ".join(str(int(i)) for i in root[s:s + 12]) for s in range(0, len(root), 12)]
    lines += ["*NSET, NSET=TIP"]
    lines += [", ".join(str(int(i)) for i in tip[s:s + 12]) for s in range(0, len(tip), 12)]
    lines += [f"*MATERIAL, NAME=STEEL", "*ELASTIC", f"{E!r}, {nu!r}", "*DENSITY", f"{rho!r}",
              "*SOLID SECTION, ELSET=BRACKET, MATERIAL=STEEL",
              "*BOUNDARY", "ROOT, 1, 3, 0.", "*STEP", "*STATIC", "*CLOAD"]
    lines += [f"{n}, 3, {float(f)!r}" for n, f in sorted(loads.items())]
    lines += ["*NODE FILE", "U", "*EL FILE", "S", "*NODE PRINT, NSET=ROOT, TOTALS=ONLY", "RF",
              "*END STEP"]
    deck.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"nodes": int(len(ids)), "elements": int(len(elems)), "root_nodes": int(len(root)),
            "tip_nodes": int(len(tip)), "tip_area_mm2": a_tip,
            "applied_load_N": float(sum(loads.values()))}

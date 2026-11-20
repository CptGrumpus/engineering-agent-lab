"""Contact FEA: elastic roller pressed onto a flat block (plane strain), CalculiX.

Half model about x = 0 (symmetry). The roller is a quarter disc of radius R
whose lowest point touches the block's top face at the origin; the block is
W wide (half) and H deep. Both bodies are meshed by Gmsh from a .geo script
(built-in kernel, no CAD needed): quads refined at the contact point by a
distance field, then extruded one layer in z to 8-node hexahedra. All nodes
have uz = 0, so the slab is in plane strain.

Load: displacement control. The roller's flat top face moves down by
`approach_mm`; the reaction there is the contact force. Displacement control
avoids an unconstrained roller before the contact closes. The line load
P' = 2 * |RF_y| / slab thickness (both halves, per mm of roller length).

Contact: CalculiX surface-to-surface penalty contact (*CONTACT PAIR, TYPE =
SURFACE TO SURFACE) with a linear pressure-overclosure law. The roller (convex,
slave) and the block top (master) surfaces are built here from the element
faces whose nodes lie on the arc / on y = 0 near the contact.

Traps handled here:
- Gmsh's built-in kernel merges coincident points by default
  (Geometry.AutoCoherence); the two bodies touch at the origin, so it is
  switched off, or the bodies would be glued at one node.
- numpy floats are cast before formatting (numpy 2 reprs).
Must not import from validation/.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

PARAMS = ("roller_radius_mm", "block_half_width_mm", "block_depth_mm", "slab_thickness_mm",
          "approach_mm", "youngs_modulus_MPa", "poisson_ratio",
          "contact_element_size_mm", "far_element_size_mm", "penalty_stiffness_factor",
          "yield_strength_MPa")

# C3D8 faces (Abaqus/CalculiX numbering S1..S6), as 0-based node positions
HEX_FACES = {"S1": (0, 1, 2, 3), "S2": (4, 7, 6, 5), "S3": (0, 4, 5, 1),
             "S4": (1, 5, 6, 2), "S5": (2, 6, 7, 3), "S6": (3, 7, 4, 0)}


def write_geo(params: dict, path: Path) -> None:
    R = float(params["roller_radius_mm"])
    W, H = float(params["block_half_width_mm"]), float(params["block_depth_mm"])
    t = float(params["slab_thickness_mm"])
    h0, h1 = float(params["contact_element_size_mm"]), float(params["far_element_size_mm"])
    zone = float(params.get("refined_zone_mm", 40 * h0))      # radius of the uniform fine zone
    path.write_text(f"""Geometry.AutoCoherence = 0;
// block (half): top face y = 0, contact point at the origin
Point(1) = {{0, 0, 0}}; Point(2) = {{{W!r}, 0, 0}}; Point(3) = {{{W!r}, {-H!r}, 0}}; Point(4) = {{0, {-H!r}, 0}};
Line(1) = {{1, 2}}; Line(2) = {{2, 3}}; Line(3) = {{3, 4}}; Line(4) = {{4, 1}};
Curve Loop(1) = {{1, 2, 3, 4}}; Plane Surface(1) = {{1}};
// roller (quarter disc), lowest point at the origin, centre at (0, R)
Point(11) = {{0, 0, 0}}; Point(12) = {{0, {R!r}, 0}}; Point(13) = {{{R!r}, {R!r}, 0}};
Circle(11) = {{11, 12, 13}}; Line(12) = {{13, 12}}; Line(13) = {{12, 11}};
Curve Loop(2) = {{11, 12, 13}}; Plane Surface(2) = {{2}};
Field[1] = Distance; Field[1].PointsList = {{1, 11}};
Field[2] = Threshold; Field[2].InField = 1;
Field[2].SizeMin = {h0!r}; Field[2].SizeMax = {h1!r};
Field[2].DistMin = {zone!r}; Field[2].DistMax = {zone + 8 * h1!r};
Background Field = 2;
Mesh.MeshSizeExtendFromBoundary = 0; Mesh.MeshSizeFromPoints = 0; Mesh.MeshSizeFromCurvature = 0;
Mesh.Algorithm = 8; Mesh.RecombineAll = 1; Mesh.SubdivisionAlgorithm = 1;
Mesh.ElementOrder = 1;
b[] = Extrude {{0, 0, {t!r}}} {{ Surface{{1}}; Layers{{1}}; Recombine; }};
r[] = Extrude {{0, 0, {t!r}}} {{ Surface{{2}}; Layers{{1}}; Recombine; }};
Physical Volume("BLOCK") = {{b[1]}};
Physical Volume("ROLLER") = {{r[1]}};
""", encoding="utf-8")


def read_mesh(mesh_inp: Path):
    """Nodes (ids, xyz) and C3D8 elements per physical set from the Gmsh .inp."""
    text = Path(mesh_inp).read_text(encoding="latin-1").splitlines()
    nodes, conn, sets, mode, cur = {}, {}, {}, None, None
    for line in text:
        s = line.strip()
        if not s or s.startswith("**"):
            continue
        if s.startswith("*"):
            key = s.upper().replace(" ", "")
            if key.startswith("*NODE"):
                mode = "n"
            elif key.startswith("*ELEMENT,") and "C3D8" in key:
                mode = "e"
            elif key.startswith("*ELSET,"):          # Gmsh writes physical groups as element lists
                cur = key.split("ELSET=")[1].split(",")[0]
                sets.setdefault(cur, [])
                mode = "s"
            else:
                mode = None
            continue
        v = [c for c in s.split(",") if c.strip()]
        if mode == "n":
            nodes[int(v[0])] = tuple(float(c) for c in v[1:4])
        elif mode == "e":
            conn[int(v[0])] = [int(c) for c in v[1:9]]
        elif mode == "s":
            sets[cur] += [int(c) for c in v]
    ids = np.array(sorted(nodes))
    xyz = np.array([nodes[i] for i in ids])
    elems = {name: np.array([[e] + conn[e] for e in members if e in conn])
             for name, members in sets.items() if name in ("BLOCK", "ROLLER")}
    return ids, xyz, elems


def contact_faces(elements: np.ndarray, coord: dict, on_surface) -> list[tuple[int, str]]:
    """(element id, face label) for every hex face whose four nodes satisfy on_surface(x, y)."""
    out = []
    for row in elements:
        eid, conn = int(row[0]), row[1:9]
        for label, f in HEX_FACES.items():
            if all(on_surface(*coord[int(conn[k])][:2]) for k in f):
                out.append((eid, label))
    return out


def write_deck(params: dict, mesh_inp: Path, deck: Path) -> dict:
    R = float(params["roller_radius_mm"])
    H = float(params["block_depth_mm"])
    E, nu = float(params["youngs_modulus_MPa"]), float(params["poisson_ratio"])
    h0 = float(params["contact_element_size_mm"])
    delta = float(params["approach_mm"])
    ids, xyz, elems = read_mesh(mesh_inp)
    if set(elems) != {"BLOCK", "ROLLER"}:
        raise RuntimeError(f"expected BLOCK and ROLLER element sets, got {sorted(elems)}")
    coord = {int(i): p for i, p in zip(ids, xyz)}
    tol = 1e-6 * R
    reach = float(params.get("contact_reach_mm", 0.25 * R))   # candidate contact zone half-width
    on_arc = lambda x, y: abs(math.hypot(x, y - R) - R) < 1e-4 * R and x <= reach  # noqa: E731
    on_top = lambda x, y: abs(y) < tol and x <= 1.5 * reach  # noqa: E731
    slave = contact_faces(elems["ROLLER"], coord, on_arc)
    master = contact_faces(elems["BLOCK"], coord, on_top)
    if not slave or not master:
        raise RuntimeError(f"contact surfaces empty: {len(slave)} roller faces, {len(master)} block faces")
    x, y = xyz[:, 0], xyz[:, 1]
    sym = ids[np.abs(x) < tol]
    bottom = ids[np.abs(y + H) < tol]
    top = ids[np.abs(y - R) < tol]
    k_pen = float(params["penalty_stiffness_factor"]) * E / h0

    def nset(name, arr):
        rows = [", ".join(str(int(v)) for v in arr[i:i + 12]) for i in range(0, len(arr), 12)]
        return f"*NSET, NSET={name}\n" + "\n".join(rows) + "\n"

    def surf(name, faces):
        return f"*SURFACE, NAME={name}\n" + "".join(f"{e}, {f}\n" for e, f in faces)

    deck.write_text(
        f"*INCLUDE, INPUT={Path(mesh_inp).name}\n"
        + nset("NALL", ids) + nset("SYM", sym) + nset("BOTTOM", bottom) + nset("TOP", top)
        + surf("SROLL", slave) + surf("SBLOCK", master)
        + f"*MATERIAL, NAME=STEEL\n*ELASTIC\n{E!r}, {nu!r}\n"
        + "*SOLID SECTION, ELSET=BLOCK, MATERIAL=STEEL\n*SOLID SECTION, ELSET=ROLLER, MATERIAL=STEEL\n"
        + "*CONTACT PAIR, INTERACTION=SI1, TYPE=SURFACE TO SURFACE\nSROLL, SBLOCK\n"
        + f"*SURFACE INTERACTION, NAME=SI1\n*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=LINEAR\n{k_pen!r}, 1.0\n"
        + "*BOUNDARY\nNALL, 3, 3, 0.\nSYM, 1, 1, 0.\nBOTTOM, 2, 2, 0.\n"
        + "*STEP, INC=1000\n*STATIC\n0.05, 1.0, 1e-6, 0.1\n"
        + f"*BOUNDARY\nTOP, 2, 2, {-delta!r}\n"
        + "*NODE FILE, FREQUENCY=10000\nU\n*EL FILE, FREQUENCY=10000\nS\n"   # last increment only
        + "*CONTACT FILE, FREQUENCY=10000\nCSTR, CDIS\n"
        + "*NODE PRINT, NSET=TOP, TOTALS=ONLY\nRF\n*NODE PRINT, NSET=BOTTOM, TOTALS=ONLY\nRF\n*END STEP\n",
        encoding="utf-8")
    return {"nodes": int(len(ids)), "roller_elements": int(len(elems["ROLLER"])),
            "block_elements": int(len(elems["BLOCK"])), "slave_faces": len(slave),
            "master_faces": len(master), "penalty_N_per_mm3": k_pen}

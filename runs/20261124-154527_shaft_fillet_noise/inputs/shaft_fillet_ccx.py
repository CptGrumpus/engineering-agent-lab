"""Stepped shaft with a shoulder fillet under bending and under torsion (machine-elements study): Gmsh -> CalculiX C3D10.

Geometry (mm): the shaft's axis is z. The small section (diameter d) runs from the loaded end z = 0 to the shoulder
face z = zs; a fillet of radius r (a quarter arc, centre at radius d/2 + r, z = zs - r) joins the small cylinder to
the shoulder face; the large section (diameter D) runs from zs to zs + L_large. Half model: the profile is revolved
by 180 degrees about z (y >= 0), so y = 0 is a plane through the axis.
Mesh: 10-node tetrahedra (Gmsh, second order). The size is h_fillet within refine_radius of the fillet's arc in the
plane y = 0 on the x > 0 side (where both peaks are: bending in the x-z plane puts the tension peak at x > 0, y = 0;
torsion's peak is the same all round), growing linearly at mesh_growth per mm to h_far.
Load cases (one deck each, linear elastic, the same mesh):
  bending  the moment M about y: tractions sigma_z = M x / I (I = pi d^4 / 64) on the loaded end, consistent nodal
           forces (7-point triangle rule on the 6-node faces); symmetry on y = 0 (u_y = 0);
  torsion  the torque T about z: shear tractions T rho / J (J = pi d^4 / 32) on the loaded end; antisymmetry on
           y = 0 (u_x = u_z = 0: pure torsion of a solid of revolution has only a hoop displacement);
  both     the far end of the large section clamped (u = 0). The applied end tractions are the exact beam stress
           fields, so the small section is in the beam state from the loaded end on.
Outputs: nodal stresses (CalculiX's extrapolation, averaged), clamp reactions per node.

Must not import from validation/.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np

PARAMS = ("D_mm", "d_mm", "fillet_radius_mm", "small_length_mm", "large_length_mm", "bending_moment_Nm",
          "torque_Nm", "youngs_modulus_MPa", "poisson_ratio", "element_size_fillet_mm", "element_size_far_mm",
          "refine_radius_mm", "mesh_growth")
#: C3D10 faces (CalculiX numbering, 0-based) as corner triples, and the mid-side node of each edge
FACES = ((0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0))
EDGE_MID = {frozenset((0, 1)): 4, frozenset((1, 2)): 5, frozenset((0, 2)): 6, frozenset((0, 3)): 7,
            frozenset((1, 3)): 8, frozenset((2, 3)): 9}
#: 7-point degree-5 rule on a triangle: (L1, L2, L3, weight); weights sum to 1
_A1, _B1, _W1 = 0.0597158717, 0.4701420641, 0.1323941527
_A2, _B2, _W2 = 0.7974269853, 0.1012865073, 0.1259391805
TRI7 = ((1 / 3, 1 / 3, 1 / 3, 0.225),
        (_A1, _B1, _B1, _W1), (_B1, _A1, _B1, _W1), (_B1, _B1, _A1, _W1),
        (_A2, _B2, _B2, _W2), (_B2, _A2, _B2, _W2), (_B2, _B2, _A2, _W2))


def dims(p: dict) -> dict:
    D, d, r = float(p["D_mm"]), float(p["d_mm"]), float(p["fillet_radius_mm"])
    h = (D - d) / 2
    if not 0 < r < h:
        raise ValueError(f"fillet radius {r} must be positive and below the shoulder height {h}")
    zs = float(p["small_length_mm"])
    return {"D": D, "d": d, "r": r, "h": h, "zs": zs, "zc": zs - r, "R0": d / 2 + r,
            "z_end": zs + float(p["large_length_mm"])}


def size_formula(p: dict) -> str:
    """Gmsh MathEval size: fine near the fillet's arc in y = 0, x > 0."""
    g = dims(p)
    hl, hf = float(p["element_size_fillet_mm"]), float(p["element_size_far_mm"])
    r0, k = float(p["refine_radius_mm"]), float(p["mesh_growth"])
    w = float(p.get("refine_halfwidth_mm", 0.0))          # the fine band's extent around the shaft from y = 0
    dist = (f"Sqrt((Sqrt((Sqrt(x^2+y^2)-{g['R0']!r})^2+(z-{g['zc']!r})^2)-{g['r']!r})^2"
            f"+Max(0,y-{w!r})^2+Max(0,-x)^2)")
    return f"Min({hf!r}, {hl!r} + {k!r}*Max(0, {dist} - {r0!r}))"


def build_mesh(p: dict, inp: Path) -> dict:
    """Mesh the half shaft and write Gmsh's Abaqus export (C3D10 only)."""
    import gmsh

    g = dims(p)
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("shaft")
        o = gmsh.model.occ
        pts = [o.addPoint(0, 0, 0), o.addPoint(g["d"] / 2, 0, 0), o.addPoint(g["d"] / 2, 0, g["zc"]),
               o.addPoint(g["R0"], 0, g["zs"]), o.addPoint(g["D"] / 2, 0, g["zs"]),
               o.addPoint(g["D"] / 2, 0, g["z_end"]), o.addPoint(0, 0, g["z_end"])]
        centre = o.addPoint(g["R0"], 0, g["zc"])
        curves = [o.addLine(pts[0], pts[1]), o.addLine(pts[1], pts[2]), o.addCircleArc(pts[2], centre, pts[3]),
                  o.addLine(pts[3], pts[4]), o.addLine(pts[4], pts[5]), o.addLine(pts[5], pts[6]),
                  o.addLine(pts[6], pts[0])]
        face = o.addPlaneSurface([o.addCurveLoop(curves)])
        out = o.revolve([(2, face)], 0, 0, 0, 0, 0, 1, math.pi)
        o.remove([(0, centre)])
        o.synchronize()
        vols = [t for dim, t in out if dim == 3]
        gmsh.model.addPhysicalGroup(3, vols, name="SHAFT")
        f = gmsh.model.mesh.field
        f.add("MathEval", 1)
        f.setString(1, "F", size_formula(p))
        f.setAsBackgroundMesh(1)
        for k in ("MeshSizeExtendFromBoundary", "MeshSizeFromPoints", "MeshSizeFromCurvature"):
            gmsh.option.setNumber(f"Mesh.{k}", 0)
        gmsh.option.setNumber("Mesh.ElementOrder", 2)
        gmsh.option.setNumber("Mesh.SecondOrderLinear", 0)
        gmsh.option.setNumber("Mesh.Optimize", 1)
        gmsh.option.setNumber("Mesh.SaveAll", 0)
        gmsh.model.mesh.generate(3)
        gmsh.write(str(inp))
        vol = o.getMass(3, vols[0])
    finally:
        gmsh.finalize()
    return {"volume_mm3": float(vol)}


def read_mesh(mesh_inp: Path):
    """(node ids, xyz, element ids, C3D10 connectivity in CalculiX order) from Gmsh's .inp."""
    text = Path(mesh_inp).read_text(encoding="utf-8")
    block = text.split("*NODE", 1)[1].split("*", 1)[0]
    rows = np.array([[float(v) for v in ln.split(",")] for ln in block.strip().splitlines()])
    ids, xyz = rows[:, 0].astype(int), rows[:, 1:4]
    elems, eids = [], []
    for part in text.split("*ELEMENT")[1:]:
        head, _, body = part.partition("\n")
        if "C3D10" not in head.upper():
            continue
        buf = []
        for ln in body.splitlines():
            if ln.startswith("*"):
                break
            buf += [int(v) for v in ln.replace(",", " ").split()]
        for k in range(0, len(buf), 11):
            eids.append(buf[k])
            elems.append(buf[k + 1:k + 11])
    return ids, xyz, np.array(eids, dtype=int), np.array(elems, dtype=int)


def end_faces(xyz, conn_rows, on_surface):
    """[(element row, (corner rows a, b, c), (mid rows ab, bc, ca))] of faces whose corners satisfy on_surface."""
    flags = on_surface(xyz)
    out = []
    for a, b, c in FACES:
        hit = np.flatnonzero(flags[conn_rows[:, a]] & flags[conn_rows[:, b]] & flags[conn_rows[:, c]])
        mids = (EDGE_MID[frozenset((a, b))], EDGE_MID[frozenset((b, c))], EDGE_MID[frozenset((c, a))])
        for e in hit:
            out.append((int(e), tuple(int(conn_rows[e, i]) for i in (a, b, c)),
                        tuple(int(conn_rows[e, i]) for i in mids)))
    return out


def consistent_forces(xyz, faces, traction) -> dict:
    """{node row: force (3,)} of a traction field t(x) (N/mm^2, callable on (n,3) points) over 6-node triangles."""
    F: dict = {}
    for _, (a, b, c), (ab, bc, ca) in faces:
        P = xyz[[a, b, c, ab, bc, ca]]
        for L1, L2, L3, w in TRI7:
            # isoparametric 6-node triangle (curved edges on the shaft's circle), xi = L2, eta = L3
            N = np.array([L1 * (2 * L1 - 1), L2 * (2 * L2 - 1), L3 * (2 * L3 - 1), 4 * L1 * L2, 4 * L2 * L3,
                          4 * L3 * L1])
            dxi = np.array([1 - 4 * L1, 4 * L2 - 1, 0.0, 4 * (L1 - L2), 4 * L3, -4 * L3])
            deta = np.array([1 - 4 * L1, 0.0, 4 * L3 - 1, -4 * L2, 4 * L2, 4 * (L1 - L3)])
            dA = 0.5 * np.linalg.norm(np.cross(dxi @ P, deta @ P))     # the reference triangle's area is 1/2
            t = traction((N @ P)[None, :])[0]
            for n, Nn in zip((a, b, c, ab, bc, ca), N):
                F[n] = F.get(n, np.zeros(3)) + w * dA * Nn * t
    return F


def tractions(p: dict, load: str):
    """The end traction (on the loaded face z = 0, outward normal -z) of the beam stress field."""
    d = float(p["d_mm"])
    if load == "bending":
        M, I = float(p["bending_moment_Nm"]) * 1e3, math.pi * d ** 4 / 64
        return lambda X: np.column_stack([0 * X[:, 0], 0 * X[:, 0], -M * X[:, 0] / I])
    if load == "torsion":
        T, J = float(p["torque_Nm"]) * 1e3, math.pi * d ** 4 / 32
        return lambda X: np.column_stack([T * X[:, 1] / J, -T * X[:, 0] / J, 0 * X[:, 0]])
    raise ValueError(load)


def write_deck(p: dict, mesh_inp: Path, deck: Path, load: str) -> dict:
    g = dims(p)
    ids, xyz, eids, elems = read_mesh(mesh_inp)
    row = {int(n): k for k, n in enumerate(ids)}
    conn = np.vectorize(row.get)(elems)
    tol = 1e-6 * g["D"]
    faces = end_faces(xyz, conn, lambda X: np.abs(X[:, 2]) < tol)
    F = consistent_forces(xyz, faces, tractions(p, load))
    sym = ids[np.abs(xyz[:, 1]) < tol]
    clamp = ids[np.abs(xyz[:, 2] - g["z_end"]) < tol]

    def nset(name, arr):
        arr = [int(v) for v in arr]
        rows = [", ".join(str(v) for v in arr[i:i + 12]) for i in range(0, len(arr), 12)]
        return f"*NSET, NSET={name}\n" + "\n".join(rows) + "\n"

    lines = ["*NODE"] + [f"{int(n)}, {float(x)!r}, {float(y)!r}, {float(z)!r}" for n, (x, y, z) in zip(ids, xyz)]
    lines.append("*ELEMENT, TYPE=C3D10, ELSET=SHAFT")
    lines += [f"{e}, " + ", ".join(str(v) for v in c) for e, c in zip(eids, elems)]
    bc_sym = "SYM, 2, 2, 0.\n" if load == "bending" else "SYM, 1, 1, 0.\nSYM, 3, 3, 0.\n"
    cl = "".join(f"{int(ids[n])}, {k + 1}, {float(v)!r}\n" for n, f in sorted(F.items()) for k, v in enumerate(f)
                 if v != 0.0)
    deck.write_text(
        "\n".join(lines) + "\n" + nset("SYM", sym) + nset("CLAMP", clamp)
        + f"*MATERIAL, NAME=STEEL\n*ELASTIC\n{float(p['youngs_modulus_MPa'])!r}, {float(p['poisson_ratio'])!r}\n"
        + "*SOLID SECTION, ELSET=SHAFT, MATERIAL=STEEL\n"
        + "*BOUNDARY\n" + bc_sym + "CLAMP, 1, 3, 0.\n"
        + "*STEP\n*STATIC\n*CLOAD\n" + cl
        + "*NODE FILE\nU\n*EL FILE\nS\n*NODE PRINT, NSET=CLAMP\nRF\n*END STEP\n", encoding="utf-8")
    Fa = np.array([f for f in F.values()])
    Xa = np.array([xyz[n] for n in F])
    return {"nodes": int(len(ids)), "elements": int(len(eids)), "end_faces": len(faces),
            "applied_force_N": Fa.sum(axis=0).tolist(), "applied_moment_Nmm": np.cross(Xa, Fa).sum(axis=0).tolist()}


_RF_HEAD = re.compile(r"forces \(fx,fy,fz\) for set CLAMP and time")


def read_node_forces(dat: Path) -> dict:
    """{node id: (fx, fy, fz)} from the last per-node RF print of set CLAMP."""
    lines = Path(dat).read_text(encoding="latin-1").splitlines()
    start = max((i for i, ln in enumerate(lines) if _RF_HEAD.search(ln)), default=None)
    if start is None:
        raise RuntimeError("no CLAMP reaction print in the .dat file")
    out = {}
    for ln in lines[start + 1:]:
        v = ln.split()
        if not v:
            if out:
                break
            continue
        try:
            out[int(v[0])] = tuple(float(s) for s in v[1:4])
        except ValueError:
            break
    return out


def fillet_surface_mask(xyz, p: dict, tol_frac: float = 1e-3):
    """Nodes on the fillet's surface (any angle)."""
    g = dims(p)
    rho = np.hypot(xyz[:, 0], xyz[:, 1])
    dc = np.hypot(rho - g["R0"], xyz[:, 2] - g["zc"])
    return (np.abs(dc - g["r"]) < tol_frac * g["r"]) & (xyz[:, 2] >= g["zc"] - 1e-9) & (rho <= g["R0"] + 1e-9)


def fillet_angle_deg(xyz, p: dict):
    """Position on the fillet arc: 0 deg at the small cylinder's tangent point, 90 deg at the shoulder face."""
    g = dims(p)
    rho = np.hypot(xyz[:, 0], xyz[:, 1])
    return np.degrees(np.arctan2(xyz[:, 2] - g["zc"], g["R0"] - rho))

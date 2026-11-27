"""The portal frame's knee as a 3D solid (steel frame study, part 2): a W-shape column stub, the W-shape beam stub,
the bolted flange-plated moment connection (top and bottom flange plates shop-welded to the column flange, a shear
tab, continuity plates at the top plate's level) -> CadQuery -> Gmsh C3D10 -> CalculiX. Output: the rotations of a
beam section and a column section clear of the joint, from which the connection's rotational stiffness follows.

Axes (mm): X along the beam (the column's centreline at X = 0, its flange face at X = dc / 2), Y up (the column's
top, flush with the top flange plate's top face, at Y = 0), Z out of the frame's plane. Both webs lie in Z = 0: the
half model Z >= 0 is exact for in-plane loading (u_z = 0 on Z = 0). The shear tab is one plate on one side of the
beam web in the real joint; here it is two plates of half its thickness, one each side (the same in-plane stiffness
and strength, and symmetric).

Idealisation (stated on the page): every contact is bonded, so the bolts neither slip nor deform (the stiffness of a
slip-critical joint below its slip load, or of a bearing joint after it has slipped into bearing); welds are not
modelled (the parts are fused along their weld lines); bolt holes are not cut. W-shape root fillets are modelled
(r = kdes - tf, which reproduces the tabulated area).

Load: a downward shear at the beam's tip (uniform traction over the tip section, consistent nodal forces); the column
clamped at its base. The knee carries the tip load times its lever arm as a moment, the beam's shear as the column's
axial force, as in the frame.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

INCH = 25.4


def g14(v) -> str:
    return f"{float(v):.14g}"


def section_mm(shape: dict) -> dict:
    """A Shapes Database W-shape (inch) in mm, with its root fillet radius r = kdes - tf."""
    d, bf, tf, tw, k = (shape[k] * INCH for k in ("d", "bf", "tf", "tw", "kdes"))
    return {"d": d, "bf": bf, "tf": tf, "tw": tw, "r": k - tf, "Ix": shape["Ix"] * INCH ** 4,
            "A": shape["A"] * INCH ** 2}


def half_area(s: dict) -> float:
    """Area of the half section Z >= 0, by hand: flanges, web, two root fillet spandrels (r^2 (1 - pi/4) each)."""
    return s["bf"] * s["tf"] + (s["d"] - 2 * s["tf"]) * s["tw"] / 2 + 2 * s["r"] ** 2 * (1 - math.pi / 4)


def dims(p: dict) -> dict:
    """Positions of every part, from the parameters (mm)."""
    from validation import aisc360

    col, beam = section_mm(aisc360.shape(p["column_shape"])), section_mm(aisc360.shape(p["beam_shape"]))
    tp = float(p["plate_thickness_mm"])
    face = col["d"] / 2
    y_beam_top = -tp
    y_beam_bot = y_beam_top - beam["d"]
    return {"col": col, "beam": beam, "tp": tp, "bp": float(p["plate_width_mm"]), "Lp": float(p["plate_length_mm"]),
            "face": face, "x_beam0": face + float(p["setback_mm"]), "x_tip": face + float(p["beam_length_mm"]),
            "y_beam_top": y_beam_top, "y_beam_bot": y_beam_bot, "y_beam_cl": y_beam_top - beam["d"] / 2,
            "y_base": y_beam_bot - tp - float(p["column_length_mm"]),
            "y_plate_bot": y_beam_bot - tp,
            "tab": (float(p["tab_width_mm"]), float(p["tab_height_mm"]), float(p["tab_thickness_mm"])),
            "cont": float(p.get("continuity_plate_thickness_mm", 0) or 0)}


def _w_half(wp, s: dict, length: float):
    """Half W-section (local x across the depth, centred; local y >= 0 across the half width), root fillets as
    arcs, extruded along the workplane's normal by `length`."""
    d, bf, tf, tw, r = s["d"], s["bf"], s["tf"], s["tw"], s["r"]
    xi = d / 2 - tf                                     # inner face of a flange
    w = (wp.moveTo(-d / 2, 0).lineTo(-d / 2, bf / 2).lineTo(-xi, bf / 2).lineTo(-xi, tw / 2 + r)
         .radiusArc((-xi + r, tw / 2), -r).lineTo(xi - r, tw / 2).radiusArc((xi, tw / 2 + r), -r)
         .lineTo(xi, bf / 2).lineTo(d / 2, bf / 2).lineTo(d / 2, 0).close())
    return w.extrude(length)


def build_cad(p: dict, step: Path) -> dict:
    """The fused half solid (Z >= 0), written as STEP; its volume and a hand volume of the same parts."""
    import cadquery as cq

    g = dims(p)
    col, beam = g["col"], g["beam"]
    col_len = -g["y_base"]
    # column: section in X-Z, extruded down from Y = 0 (local y = Z: normal x xDir = (0,-1,0) x (1,0,0) = +Z)
    column = _w_half(cq.Workplane(cq.Plane(origin=(0, 0, 0), xDir=(1, 0, 0), normal=(0, -1, 0))), col, col_len)
    # beam: section in Y-Z (local x = Y), extruded along +X from the beam's end
    blen = g["x_tip"] - g["x_beam0"]
    beam_s = _w_half(cq.Workplane(cq.Plane(origin=(g["x_beam0"], g["y_beam_cl"], 0), xDir=(0, 1, 0),
                                           normal=(1, 0, 0))), beam, blen)
    box = lambda x0, x1, y0, y1, z0, z1: cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False) \
        .translate((x0, y0, z0))  # noqa: E731
    face, Lp, tp, bp = g["face"], g["Lp"], g["tp"], g["bp"]
    top = box(face, face + Lp, g["y_beam_top"], 0.0, 0.0, bp / 2)
    bot = box(face, face + Lp, g["y_plate_bot"], g["y_beam_bot"], 0.0, bp / 2)
    tw_, th_, tt_ = g["tab"]
    tab = box(face, face + tw_, g["y_beam_cl"] - th_ / 2, g["y_beam_cl"] + th_ / 2, beam["tw"] / 2,
              beam["tw"] / 2 + tt_ / 2)
    solid = column.union(beam_s).union(top).union(bot).union(tab)
    parts_v = [col_len * half_area(col), blen * half_area(beam), 2 * Lp * tp * bp / 2, tw_ * th_ * tt_ / 2]
    if g["cont"] > 0:
        clip = col["r"] + 6.0                           # corner clips clear of the root fillets
        xi = col["d"] / 2 - col["tf"]
        cp = box(-xi, xi, -g["cont"], 0.0, col["tw"] / 2, col["bf"] / 2)
        for sx in (-1, 1):
            cp = cp.cut(box(sx * xi - (clip if sx > 0 else 0), sx * xi + (clip if sx < 0 else 0), -g["cont"], 0.0,
                            col["tw"] / 2, col["tw"] / 2 + clip))
        solid = solid.union(cp)
        parts_v.append(g["cont"] * (2 * xi * (col["bf"] - col["tw"]) / 2 - 2 * clip * clip))
    solids = solid.solids().vals()
    if len(solids) != 1 or not solid.val().isValid():
        raise RuntimeError(f"knee solid: {len(solids)} solids, valid {solid.val().isValid()}")
    cq.exporters.export(solid, str(step))
    return {"volume_mm3": float(solid.val().Volume()), "hand_volume_mm3": float(sum(parts_v)),
            "faces": len(solid.faces().vals())}


def build_mesh(p: dict, step: Path, inp: Path, *, h_joint: float, h_far: float, growth: float = 0.25,
               seed: int = 0) -> dict:
    """C3D10 mesh: h_joint inside the joint region (the column from the bottom plate up, the plates, the beam to
    the plates' end), growing by `growth` per mm outside it to h_far."""
    import gmsh

    g = dims(p)
    gmsh.initialize(["-noenv"])
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("Mesh.RandomSeed", seed)
        gmsh.model.occ.importShapes(str(step))
        gmsh.model.occ.synchronize()
        vols = gmsh.model.getEntities(3)
        if len(vols) != 1:
            raise RuntimeError(f"expected one volume, found {vols}")
        gmsh.model.addPhysicalGroup(3, [vols[0][1]], name="KNEE")
        x0, x1 = -g["face"] - 1.0, g["face"] + g["Lp"] + 1.0
        y0, y1 = g["y_plate_bot"] - 1.0, 1.0
        f = gmsh.model.mesh.field
        out_x = f"Max(0, Max({g14(x0)} - x, x - ({g14(x1)})))"
        out_y = f"Max(0, Max({g14(y0)} - y, y - ({g14(y1)})))"
        ms = f.add("MathEval")
        f.setString(ms, "F", f"Min({g14(h_far)}, {g14(h_joint)} + {g14(growth)}*({out_x} + {out_y}))")
        f.setAsBackgroundMesh(ms)
        for k in ("MeshSizeExtendFromBoundary", "MeshSizeFromPoints"):
            gmsh.option.setNumber(f"Mesh.{k}", 0)
        # curved surfaces (the root fillets, r 10-13 mm) take about 10 elements per circle, 0.6 r: one quadratic
        # element across a fillet at the far size inverts (45 inverted at 25 mm, smoke 2026-11-27)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 10)
        for k, v in (("Mesh.ElementOrder", 2), ("Mesh.SecondOrderLinear", 0), ("Mesh.Algorithm3D", 10),
                     ("Mesh.SaveAll", 0)):
            gmsh.option.setNumber(k, v)
        gmsh.model.mesh.generate(3)
        gmsh.model.mesh.optimize("HighOrderElastic")
        et = gmsh.model.mesh.getElementsByType(11)[0]
        sj = np.asarray(gmsh.model.mesh.getElementQualities(et, "minSJ"))
        worst = []
        for i in np.argsort(sj)[:5]:                    # where the worst elements are, for diagnosis
            nodes = gmsh.model.mesh.getElement(int(et[i]))[1][:4]
            worst.append([round(float(v), 1) for v in np.mean([gmsh.model.mesh.getNode(int(n))[0] for n in nodes],
                                                               axis=0)] + [round(float(sj[i]), 3)])
        gmsh.write(str(inp))
        return {"elements": int(len(et)), "min_scaled_jacobian": float(sj.min()),
                "inverted_elements": int((sj <= 0).sum()), "worst": worst, "gmsh": gmsh.__version__}
    finally:
        gmsh.finalize()


def write_deck(p: dict, mesh_inp: Path, deck: Path) -> dict:
    """Half model: u_z = 0 on Z = 0, the column's base clamped, a downward uniform shear traction on the beam's tip
    section totalling half the tip load. *NODE FILE U; reaction print at the base."""
    from models.fea import keyed_shaft as ks
    from models.fea import shaft_fillet_ccx as sf

    g = dims(p)
    ids, xyz, eids, elems = ks.read_mesh(mesh_inp)
    tol = 1e-6 * g["x_tip"]
    P_half = float(p["tip_load_kN"]) * 1e3 / 2
    row = {int(n): k for k, n in enumerate(ids)}
    conn = np.vectorize(row.get)(elems)
    faces = sf.end_faces(xyz, conn, lambda X: np.abs(X[:, 0] - g["x_tip"]) < tol)
    F = sf.consistent_forces(xyz, faces, lambda X: np.column_stack([0 * X[:, 0], -1.0 + 0 * X[:, 0], 0 * X[:, 0]]))
    scale = P_half / -sum(f[1] for f in F.values())        # unit traction over the meshed face, scaled to P / 2
    F = {n: f * scale for n, f in F.items()}
    sym, base = ids[np.abs(xyz[:, 2]) < tol], ids[np.abs(xyz[:, 1] - g["y_base"]) < tol]

    def nset(name, arr):
        arr = [int(v) for v in arr]
        return f"*NSET, NSET={name}\n" + "\n".join(", ".join(map(str, arr[i:i + 12])) for i in range(0, len(arr), 12))

    lines = ["*NODE"] + [f"{int(n)}, {g14(x)}, {g14(y)}, {g14(z)}" for n, (x, y, z) in zip(ids, xyz)]
    lines.append("*ELEMENT, TYPE=C3D10, ELSET=KNEE")
    lines += [f"{e}, " + ", ".join(str(v) for v in c) for e, c in zip(eids, elems)]
    lines += [nset("SYM", sym), nset("BASE", base),
              f"*MATERIAL, NAME=STEEL\n*ELASTIC\n{g14(p['youngs_modulus_MPa'])}, {g14(p['poisson_ratio'])}",
              "*SOLID SECTION, ELSET=KNEE, MATERIAL=STEEL", "*BOUNDARY", "SYM, 3, 3, 0.", "BASE, 1, 3, 0.",
              "*STEP", "*STATIC", "*CLOAD"]
    lines += [f"{int(ids[n])}, {k + 1}, {g14(v)}" for n, f in sorted(F.items()) for k, v in enumerate(f) if v != 0.0]
    lines += ["*NODE FILE", "U", "*NODE PRINT, NSET=BASE", "RF", "*END STEP"]
    deck.write_text("\n".join(lines) + "\n", encoding="utf-8")
    Fa = np.array(list(F.values()))
    return {"nodes": int(len(ids)), "elements": int(len(eids)), "applied_force_N": Fa.sum(axis=0).tolist(),
            "tip_faces": len(faces)}


def section_rotation(X: np.ndarray, U: np.ndarray, axis: str, at: float, halfwidth: float) -> dict:
    """Least-squares rotation (about Z, counterclockwise positive) of the cross-section at X = at (axis "beam": fit
    u_x = a + b y + c x over the nodes within halfwidth, rotation -b) or Y = at (axis "column": fit u_y = a + b x +
    c y, rotation b)."""
    if axis == "beam":
        m = np.abs(X[:, 0] - at) <= halfwidth
        A = np.column_stack([np.ones(m.sum()), X[m, 1], X[m, 0] - at])
        coef, res, *_ = np.linalg.lstsq(A, U[m, 0], rcond=None)
        theta = -coef[1]
    else:
        m = np.abs(X[:, 1] - at) <= halfwidth
        A = np.column_stack([np.ones(m.sum()), X[m, 0], X[m, 1] - at])
        coef, res, *_ = np.linalg.lstsq(A, U[m, 1], rcond=None)
        theta = coef[1]
    return {"theta": float(theta), "nodes": int(m.sum())}


def centreline_rotations(p: dict, x_b: float, y_c: float) -> dict:
    """Beam theory on the centreline model (rigid joint at the centreline intersection, members flexible up to it):
    the hogging rotation of the beam section at x_b relative to the joint, and of the joint relative to the column
    section at y_c (column moment constant: the tip load times the tip's lever arm). Magnitudes, radians."""
    g = dims(p)
    E, P = float(p["youngs_modulus_MPa"]), float(p["tip_load_kN"]) * 1e3
    a = g["x_tip"]
    db = P / (E * g["beam"]["Ix"]) * (a * x_b - x_b ** 2 / 2)          # int_0^x_b P (a - x) dx / EI
    dc = P * a * (g["y_beam_cl"] - y_c) / (E * g["col"]["Ix"])
    return {"beam": db, "column": dc, "M_joint_Nmm": P * a}


def aisc_index(p: dict, theta_b: float, x_b: float, theta_c: float, y_c: float) -> dict:
    """AISC Commentary B3.4b's index K_s = M / theta: the beam's rotation at the column face relative to the column's
    rotation at the bottom of the joint (the bottom plate's underside), both carried from the measured sections by
    beam theory, so theta holds the connecting elements, the member ends inside the joint and the panel zone (as a
    test measures it). M is the moment at the column face. Magnitudes; hogging under a downward tip load."""
    g = dims(p)
    E, P = float(p["youngs_modulus_MPa"]), float(p["tip_load_kN"]) * 1e3
    a, xf = g["x_tip"], g["face"]
    db = P / (E * g["beam"]["Ix"]) * ((a * x_b - x_b ** 2 / 2) - (a * xf - xf ** 2 / 2))      # face -> station
    tb = abs(theta_b) - db
    tc = abs(theta_c) + P * a * (g["y_plate_bot"] - y_c) / (E * g["col"]["Ix"])            # station -> joint bottom
    M = P * (a - xf)
    return {"theta_rad": tb - tc, "M_face_Nmm": M, "Ks_Nmm_per_rad": M / (tb - tc)}

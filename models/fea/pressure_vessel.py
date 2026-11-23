"""Pressure vessel shell with a radial nozzle under internal pressure: CadQuery -> Gmsh C3D10 -> CalculiX (study 18).

Geometry (mm), a quarter model by symmetry:
  shell   cylinder along z, inside radius Ri, thickness t, from z = 0 (symmetry plane through the nozzle axis) to z = L
  nozzle  cylinder along +x, inside radius rni, thickness tn, set in (its bore runs through the shell wall), ending at
          x = Ro + Ln; an outer weld fillet of radius rf where the nozzle meets the shell; the inner corner is sharp
  cuts    y >= 0 (the plane through both axes) and z >= 0 (the transverse plane through the nozzle axis)
Mesh: 10-node tetrahedra; size h_local within r_local of the junction (the point (Ro, 0, 0)), growing linearly at
mesh_growth per mm to h_far.
Loads: internal pressure p on the shell bore and the nozzle bore; the closed-end thrusts as axial tension on the far
shell end (p Ri^2 / (Ro^2 - Ri^2)) and on the nozzle end (p rni^2 / (rno^2 - rni^2)), so the far field is the Lame
solution of a closed cylinder exactly. Supports: symmetry (u_y = 0 on y = 0, u_z = 0 on z = 0) and u_x = 0 at one
node on the back of the shell (x = -Ro, y = 0, z = 0): the pressure on a closed vessel is self-balanced, so its
reaction is a check (it should be zero).
Stress classification lines (SCLs) are straight lines through the wall, listed by scl_lines().
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

PARAMS = ("shell_inner_radius_mm", "shell_thickness_mm", "shell_half_length_mm", "nozzle_inner_radius_mm",
          "nozzle_thickness_mm", "nozzle_length_mm", "weld_fillet_radius_mm", "pressure_MPa", "youngs_modulus_MPa",
          "poisson_ratio", "element_size_local_mm", "element_size_far_mm", "refine_radius_mm", "mesh_growth")
#: C3D10 / C3D4 faces (CalculiX numbering) as corner-node triples
FACES = ((0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0))


def _f(p, k):
    return float(p[k])


def dims(p):
    Ri, t, rni, tn = _f(p, "shell_inner_radius_mm"), _f(p, "shell_thickness_mm"), _f(p, "nozzle_inner_radius_mm"), \
        _f(p, "nozzle_thickness_mm")
    Ro, rno = Ri + t, rni + tn
    return {"Ri": Ri, "Ro": Ro, "t": t, "L": _f(p, "shell_half_length_mm"), "rni": rni, "rno": rno, "tn": tn,
            "Xend": Ro + _f(p, "nozzle_length_mm"), "rf": _f(p, "weld_fillet_radius_mm")}


def build_solid(p):
    import cadquery as cq

    d = dims(p)
    Ri, Ro, L, rni, rno, Xend, rf = (d[k] for k in ("Ri", "Ro", "L", "rni", "rno", "Xend", "rf"))
    shell = cq.Workplane("XY").workplane(offset=-L).circle(Ro).extrude(2 * L)
    noz = cq.Workplane("YZ").circle(rno).extrude(Xend)
    sh = shell.union(noz).val()
    if rf > 0:
        # the weld edge: the saddle curve where the nozzle's outer surface meets the shell's, i.e. the edge whose
        # points all lie on both outer cylinders (selecting by length also catches the nozzle-end circle)
        def on_both(e):
            pts = [e.positionAt(k / 8) for k in range(9)]
            return all(abs(math.hypot(q.x, q.y) - Ro) < 1e-3 * Ro and abs(math.hypot(q.y, q.z) - rno) < 1e-3 * rno
                       for q in pts)
        weld = [e for e in sh.Edges() if on_both(e)]  # OCC splits the closed saddle into several B-spline edges
        total = sum(e.Length() for e in weld)
        if not weld or not 2 * math.pi * rno <= total <= 1.1 * 2 * math.pi * rno:
            raise RuntimeError(f"weld edge not found: {len(weld)} edges, {total:.1f} mm")
        sh = sh.fillet(rf, weld)
    body = cq.Workplane("XY").newObject([sh])
    body = body.cut(cq.Workplane("XY").workplane(offset=-L - 1).circle(Ri).extrude(2 * L + 2))
    body = body.cut(cq.Workplane("YZ").circle(rni).extrude(Xend + 1))
    box = cq.Workplane("XY").box(2 * Xend + 10, Ro + 10, L, centered=(True, False, False))
    return body.intersect(box)


def build_step(p, path: Path) -> dict:
    import cadquery as cq

    solid = build_solid(p)
    cq.exporters.export(solid, str(path))
    v = solid.val()
    d = dims(p)
    # volume without the fillet (hand formula): half shell + quarter nozzle outside the shell - quarter hole
    # through the shell (the bore inside the wall, approximated as a straight plug of length t)
    approx = (math.pi * (d["Ro"] ** 2 - d["Ri"] ** 2) / 2 * d["L"]
              + math.pi * (d["rno"] ** 2 - d["rni"] ** 2) / 4 * (d["Xend"] - d["Ro"])
              - math.pi * d["rni"] ** 2 / 4 * d["t"])
    return {"volume_mm3": float(v.Volume()), "volume_hand_mm3": approx, "faces": len(v.Faces()),
            "valid": bool(v.isValid())}


def write_geo(p, path: Path, step_name: str = "vessel.step") -> None:
    d = dims(p)
    hl, hf = _f(p, "element_size_local_mm"), _f(p, "element_size_far_mm")
    r0, g = _f(p, "refine_radius_mm"), _f(p, "mesh_growth")
    path.write_text(f"""SetFactory("OpenCASCADE");
Merge "{step_name}";
Field[1] = MathEval;
Field[1].F = "Min({hf!r}, {hl!r} + {g!r}*Max(0, Sqrt((x-{d['Ro']!r})^2+y^2+z^2) - {r0!r}))";
Background Field = 1;
Mesh.MeshSizeExtendFromBoundary = 0; Mesh.MeshSizeFromPoints = 0; Mesh.MeshSizeFromCurvature = 0;
Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 0; Mesh.Optimize = 1;
Physical Volume("VESSEL") = Volume{{:}};
""", encoding="utf-8")


def read_mesh(mesh_inp: Path):
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


def loaded_faces(xyz_by_row, conn_rows, on_surface):
    """[(element index, face number 1-4)] whose three corner nodes all satisfy on_surface(xyz) (vectorised)."""
    out = []
    flags = on_surface(xyz_by_row)
    corner = conn_rows[:, :4]
    for f, (a, b, c) in enumerate(FACES):
        hit = flags[corner[:, a]] & flags[corner[:, b]] & flags[corner[:, c]]
        out += [(int(e), f + 1) for e in np.flatnonzero(hit)]
    return out


def write_deck(p, mesh_inp: Path, deck: Path) -> dict:
    d = dims(p)
    ids, xyz, eids, elems = read_mesh(mesh_inp)
    row = {int(n): k for k, n in enumerate(ids)}
    conn = np.vectorize(row.get)(elems)
    tol = 1e-4 * d["Ro"]
    rxy, ryz = np.hypot(xyz[:, 0], xyz[:, 1]), np.hypot(xyz[:, 1], xyz[:, 2])
    surf = {
        "shell_bore": lambda X: np.abs(np.hypot(X[:, 0], X[:, 1]) - d["Ri"]) < tol,
        "nozzle_bore": lambda X: (np.abs(np.hypot(X[:, 1], X[:, 2]) - d["rni"]) < tol) & (X[:, 0] > 0),
        "shell_end": lambda X: np.abs(X[:, 2] - d["L"]) < tol,
        "nozzle_end": lambda X: np.abs(X[:, 0] - d["Xend"]) < tol,
    }
    faces = {k: loaded_faces(xyz, conn, f) for k, f in surf.items()}
    pr = _f(p, "pressure_MPa")
    q_shell = pr * d["Ri"] ** 2 / (d["Ro"] ** 2 - d["Ri"] ** 2)
    q_noz = pr * d["rni"] ** 2 / (d["rno"] ** 2 - d["rni"] ** 2)
    sym_y = ids[np.abs(xyz[:, 1]) < tol]
    sym_z = ids[np.abs(xyz[:, 2]) < tol]
    back = ids[int(np.argmin(np.linalg.norm(xyz - np.array([-d["Ro"], 0.0, 0.0]), axis=1)))]
    rows = lambda a: [", ".join(str(int(v)) for v in a[s:s + 12]) for s in range(0, len(a), 12)]  # noqa: E731
    E, nu = _f(p, "youngs_modulus_MPa"), _f(p, "poisson_ratio")
    lines = [f"*INCLUDE, INPUT={Path(mesh_inp).name}", "*NSET, NSET=NSYMY"] + rows(sym_y) + ["*NSET, NSET=NSYMZ"] + \
        rows(sym_z) + ["*NSET, NSET=NBACK", str(int(back)),
                       "*MATERIAL, NAME=STEEL", "*ELASTIC", f"{E!r}, {nu!r}",
                       "*SOLID SECTION, ELSET=VESSEL, MATERIAL=STEEL",
                       "*BOUNDARY", "NSYMY, 2, 2, 0.", "NSYMZ, 3, 3, 0.", "NBACK, 1, 1, 0.",
                       "*STEP", "*STATIC", "*DLOAD"]
    for key, val in (("shell_bore", pr), ("nozzle_bore", pr), ("shell_end", -q_shell), ("nozzle_end", -q_noz)):
        lines += [f"{int(eids[e])}, P{f}, {val!r}" for e, f in faces[key]]
    lines += ["*NODE FILE", "U", "*EL FILE", "S",
              "*NODE PRINT, NSET=NSYMY, TOTALS=ONLY", "RF", "*NODE PRINT, NSET=NSYMZ, TOTALS=ONLY", "RF",
              "*NODE PRINT, NSET=NBACK", "RF", "*END STEP"]
    deck.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"nodes": int(len(ids)), "elements": int(len(eids)), "faces_shell_bore": len(faces["shell_bore"]),
            "faces_nozzle_bore": len(faces["nozzle_bore"]), "faces_shell_end": len(faces["shell_end"]),
            "faces_nozzle_end": len(faces["nozzle_end"]), "back_node": int(back),
            "axial_traction_shell_MPa": q_shell, "axial_traction_nozzle_MPa": q_noz}


def expected_reactions(p) -> dict:
    """Exact resultants the supports must carry (pressure times projected wetted area, plus the end thrusts):
    on y = 0, Ry = -p (2 Ri L + rni (Xend - Ri)); on z = 0, Rz = -(p pi Ri^2 / 2 + p A_bore), A_bore the projection of
    the nozzle bore on z = 0 (y from 0 to rni, x from the shell bore to the nozzle end); at the back node, Rx = 0."""
    d = dims(p)
    pr = _f(p, "pressure_MPa")
    y = np.linspace(0, d["rni"], 20001)
    a_bore = float(np.trapezoid(d["Xend"] - np.sqrt(d["Ri"] ** 2 - y ** 2), y))
    return {"Ry_N": -pr * (2 * d["Ri"] * d["L"] + d["rni"] * (d["Xend"] - d["Ri"])),
            "Rz_N": -(pr * math.pi * d["Ri"] ** 2 / 2 + pr * a_bore), "Rx_back_N": 0.0,
            "nozzle_thrust_scale_N": pr * math.pi * d["rni"] ** 2 / 4}


def scl_lines(p, n_points: int = 21) -> dict:
    """Stress classification lines: name -> (points (n, 3), axes (3, 3) rows n/m/h, class). Junction lines sit at the
    weld-fillet toes (shell: rno + rf from the nozzle axis; nozzle: rf above the shell surface), in the two planes of
    symmetry; FAR is on the back of the shell, half way along, where the shell is the Lame cylinder.

    Optional parameter scl_toe_offset_mm (default 0) moves the four toe lines that far further from the junction
    (along the shell surface, or up the nozzle), for a placement sensitivity. In the transverse plane (z = 0) the toe
    lines sit where the shell's or the nozzle's outer surface is rno + rf from the other axis, about 2 mm outboard of
    the true fillet toe (the ball centre is at y = rno + rf on the circle Ro + rf); in the longitudinal plane they are
    exact. CROTCH_LONG and CROTCH_TRANS run from the sharp inner corner towards the fillet's centre (the rolling ball's
    centre lies in each symmetry plane) and end on the fillet surface: the shortest line through the corner, the usual
    alternative placement at a nozzle crotch."""
    d = dims(p)
    Ri, Ro, rni, rno, rf, L = (d[k] for k in ("Ri", "Ro", "rni", "rno", "rf", "L"))
    off = float(p.get("scl_toe_offset_mm", 0.0))
    s = np.linspace(0, 1, n_points)[:, None]
    out = {}
    zt = rno + rf + off
    a, b = np.array([Ri, 0, zt]), np.array([Ro, 0, zt])
    out["shell_long"] = (a + s * (b - a), np.array([[1, 0, 0], [0, 0, 1], [0, 1, 0]], float), "junction")
    th = math.asin((rno + rf) / Ro) + off / Ro
    c, sn = math.cos(th), math.sin(th)
    a, b = np.array([Ri * c, Ri * sn, 0]), np.array([Ro * c, Ro * sn, 0])
    out["shell_trans"] = (a + s * (b - a), np.array([[c, sn, 0], [-sn, c, 0], [0, 0, 1]], float), "junction")
    xn = Ro + rf + off
    a, b = np.array([xn, 0, rni]), np.array([xn, 0, rno])
    out["nozzle_long"] = (a + s * (b - a), np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]], float), "junction")
    xn = math.sqrt(Ro ** 2 - rno ** 2) + rf + off
    a, b = np.array([xn, rni, 0]), np.array([xn, rno, 0])
    out["nozzle_trans"] = (a + s * (b - a), np.array([[0, 1, 0], [1, 0, 0], [0, 0, 1]], float), "junction")
    a, b = np.array([-Ri, 0, L / 2]), np.array([-Ro, 0, L / 2])
    out["far"] = (a + s * (b - a), np.array([[-1, 0, 0], [0, 0, 1], [0, 1, 0]], float), "general")
    # crotch lines: inner corner A, fillet ball centre C, end on the fillet surface C - rf u
    for name, A, C, h in (("crotch_long", (Ri, 0.0, rni), (Ro + rf, 0.0, rno + rf), (0.0, 1.0, 0.0)),
                          ("crotch_trans", (math.sqrt(Ri ** 2 - rni ** 2), rni, 0.0),
                           (math.sqrt((Ro + rf) ** 2 - (rno + rf) ** 2), rno + rf, 0.0), (0.0, 0.0, 1.0))):
        A, C, h = np.array(A), np.array(C), np.array(h)
        u = (C - A) / np.linalg.norm(C - A)
        b = C - rf * u
        out[name] = (A + s * (b - A), np.array([u, np.cross(h, u), h], float), "crotch")
    return out


def lame(p, r):
    """Closed-end thick cylinder: (radial, hoop, axial) stresses at radius r."""
    d = dims(p)
    pr = _f(p, "pressure_MPa")
    A = pr * d["Ri"] ** 2 / (d["Ro"] ** 2 - d["Ri"] ** 2)
    B = pr * d["Ri"] ** 2 * d["Ro"] ** 2 / (d["Ro"] ** 2 - d["Ri"] ** 2)
    r = np.asarray(r, float)
    return A - B / r ** 2, A + B / r ** 2, np.full_like(r, A)

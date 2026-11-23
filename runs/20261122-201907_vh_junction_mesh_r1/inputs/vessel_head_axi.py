"""Cylindrical shell closed by a hemispherical head, internal pressure, axisymmetric CAX8 in CalculiX (study 18,
the head-to-shell junction).

Geometry (mm), in the (r, z) plane: the shell from z = -L (a symmetry plane: the vessel's mid-length) to z = 0,
inside radius Ri, thickness t; the head a hemisphere on z >= 0, centre at the origin, the same inside radius (flush
bore), thickness t_h. With t_h < t the shell's outer edge steps down to the head at z = 0 (no taper).
Mesh: structured 8-node quadrilaterals, generated here (no CAD): radial size dr through both walls (t / dr and
t_h / dr must be whole numbers), length dl = element_aspect x dr along the wall. Classification lines sit on
element boundaries, so the nodes on each line (corner and mid-side) are 2 n + 1 equally spaced points through the
wall.
Loads: pressure p on the bore of the shell and the head. Supports: u_z = 0 on z = -L, u_r = 0 on the axis.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

PARAMS = ("shell_inner_radius_mm", "shell_thickness_mm", "head_thickness_mm", "shell_length_mm", "pressure_MPa",
          "youngs_modulus_MPa", "poisson_ratio", "element_size_mm", "element_aspect")


def _f(p, k):
    return float(p[k])


def dims(p):
    Ri, t, th = _f(p, "shell_inner_radius_mm"), _f(p, "shell_thickness_mm"), _f(p, "head_thickness_mm")
    dr = _f(p, "element_size_mm")
    dl = dr * _f(p, "element_aspect")
    nc, nh = t / dr, th / dr
    if abs(nc - round(nc)) > 1e-9 or abs(nh - round(nh)) > 1e-9:
        raise ValueError(f"element_size_mm {dr} must divide both thicknesses ({t}, {th})")
    L = _f(p, "shell_length_mm")
    na = max(1, round(L / dl))
    nphi = max(2, round(0.5 * math.pi * (Ri + th / 2) / dl))
    return {"Ri": Ri, "t": t, "th": th, "L": L, "dr": dr, "nc": int(round(nc)), "nh": int(round(nh)), "na": na,
            "nphi": nphi, "Rm": Ri + t / 2, "Rmh": Ri + th / 2}


def build_mesh(p):
    """Nodes {id: (r, z)}, CAX8 elements [(id, (8 node ids), block, i0, j0)] and the node grids:
    cyl[(i, j)] (i through the wall, 0..2 nc; j along z, 0..2 na) and head[(i, k)] (k along phi, 0..2 nphi)."""
    d = dims(p)
    Ri, dr, L = d["Ri"], d["dr"], d["L"]
    nc, nh, na, nphi = d["nc"], d["nh"], d["na"], d["nphi"]
    nodes, cyl, head = {}, {}, {}
    nid = 0

    def add(r, z):
        nonlocal nid
        nid += 1
        nodes[nid] = (r, z)
        return nid

    for j in range(2 * na + 1):
        z = -L + j * L / (2 * na)
        for i in range(2 * nc + 1):
            if i % 2 and j % 2:
                continue
            cyl[(i, j)] = add(Ri + i * dr / 2, z)
    for k in range(2 * nphi + 1):
        phi = k * (math.pi / 2) / (2 * nphi)
        for i in range(2 * nh + 1):
            if i % 2 and k % 2:
                continue
            if k == 0:  # the interface z = 0: shared with the shell's top row
                head[(i, 0)] = cyl[(i, 2 * na)]
                continue
            rho = Ri + i * dr / 2
            r = 0.0 if k == 2 * nphi else rho * math.cos(phi)  # exactly on the axis
            head[(i, k)] = add(r, rho * math.sin(phi))
    elems = []
    eid = 0
    for grid, ni, nj, block in ((cyl, nc, na, "shell"), (head, nh, nphi, "head")):
        for j0 in range(0, 2 * nj, 2):
            for i0 in range(0, 2 * ni, 2):
                g = lambda a, b: grid[(i0 + a, j0 + b)]  # noqa: E731
                eid += 1
                elems.append((eid, (g(0, 0), g(2, 0), g(2, 2), g(0, 2), g(1, 0), g(2, 1), g(1, 2), g(0, 1)),
                              block, i0, j0))
    return nodes, elems, cyl, head


def write_deck(p, deck: Path) -> dict:
    d = dims(p)
    nodes, elems, cyl, head = build_mesh(p)
    pr, E, nu = _f(p, "pressure_MPa"), _f(p, "youngs_modulus_MPa"), _f(p, "poisson_ratio")
    rows = lambda a: [", ".join(str(int(v)) for v in a[s:s + 12]) for s in range(0, len(a), 12)]  # noqa: E731
    bottom = [cyl[(i, 0)] for i in range(2 * d["nc"] + 1) if (i, 0) in cyl]
    axis = [head[(i, 2 * d["nphi"])] for i in range(2 * d["nh"] + 1) if (i, 2 * d["nphi"]) in head]
    # CalculiX rejects numbers longer than about 20 characters (a repr such as 3.0738634658598566e-14)
    lines = ["*NODE"] + [f"{n}, {r:.12g}, {z:.12g}" for n, (r, z) in nodes.items()]
    lines += ["*ELEMENT, TYPE=CAX8, ELSET=VESSEL"] + [f"{e}, " + ", ".join(map(str, c)) for e, c, *_ in elems]
    lines += ["*NSET, NSET=NBOTTOM"] + rows(bottom) + ["*NSET, NSET=NAXIS"] + rows(axis)
    lines += ["*MATERIAL, NAME=STEEL", "*ELASTIC", f"{E:.12g}, {nu:.12g}", "*SOLID SECTION, ELSET=VESSEL, MATERIAL=STEEL",
              "*BOUNDARY", "NBOTTOM, 2, 2, 0.", "NAXIS, 1, 1, 0.", "*STEP", "*STATIC", "*DLOAD"]
    # bore: face 4 (nodes 4-1, the i0 = 0 side) of the first element column in both blocks
    lines += [f"{e}, P4, {pr:.12g}" for e, c, block, i0, j0 in elems if i0 == 0]
    lines += ["*NODE FILE", "U", "*EL FILE", "S", "*NODE PRINT, NSET=NBOTTOM, TOTALS=ONLY", "RF", "*END STEP"]
    deck.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"nodes": len(nodes), "elements": len(elems), "bore_faces": sum(1 for e in elems if e[3] == 0),
            "n_shell_through": d["nc"], "n_head_through": d["nh"], "n_along_shell": d["na"], "n_along_head": d["nphi"]}


def scl_shell(p, cyl, x_max_mm: float):
    """Classification lines through the shell wall at the element boundaries with distance x = -z <= x_max from the
    junction: [(x, [node ids from bore to outside])]."""
    d = dims(p)
    out = []
    for j in range(2 * d["na"], -1, -2):
        x = d["L"] * (1 - j / (2 * d["na"]))
        if x > x_max_mm + 1e-9:
            break
        out.append((x, [cyl[(i, j)] for i in range(2 * d["nc"] + 1)]))
    return out


def scl_head(p, head, s_max_mm: float):
    """Lines through the head wall at the element boundaries with arc distance s = Rmh phi <= s_max from the
    junction: [(s, phi, [node ids from bore to outside])]."""
    d = dims(p)
    out = []
    for k in range(0, 2 * d["nphi"] + 1, 2):
        phi = k * (math.pi / 2) / (2 * d["nphi"])
        s = d["Rmh"] * phi
        if s > s_max_mm + 1e-9:
            break
        out.append((s, phi, [head[(i, k)] for i in range(2 * d["nh"] + 1)]))
    return out


def head_line_at(p, head, phi_target: float):
    """The head line nearest the angle phi_target (rad): (phi, node ids)."""
    d = dims(p)
    k = 2 * round(phi_target / (math.pi / 2) * d["nphi"])
    return k * (math.pi / 2) / (2 * d["nphi"]), [head[(i, k)] for i in range(2 * d["nh"] + 1)]


def lame_cylinder(p, r):
    """Closed-end thick cylinder (shell): radial, hoop, axial stress and radial displacement at r."""
    Ri, t = _f(p, "shell_inner_radius_mm"), _f(p, "shell_thickness_mm")
    Ro, pr, E, nu = Ri + t, _f(p, "pressure_MPa"), _f(p, "youngs_modulus_MPa"), _f(p, "poisson_ratio")
    A = pr * Ri ** 2 / (Ro ** 2 - Ri ** 2)
    B = A * Ro ** 2
    r = np.asarray(r, float)
    return A - B / r ** 2, A + B / r ** 2, np.full_like(r, A), r / E * (A * (1 - 2 * nu) + (1 + nu) * B / r ** 2)


def lame_sphere(p, r, thickness=None):
    """Thick sphere under internal pressure: radial and tangential stress and radial displacement at r."""
    Ri = _f(p, "shell_inner_radius_mm")
    th = _f(p, "head_thickness_mm") if thickness is None else thickness
    Ro, pr, E, nu = Ri + th, _f(p, "pressure_MPa"), _f(p, "youngs_modulus_MPa"), _f(p, "poisson_ratio")
    c = pr * Ri ** 3 / (Ro ** 3 - Ri ** 3)
    r = np.asarray(r, float)
    sr, st = c * (1 - Ro ** 3 / r ** 3), c * (1 + Ro ** 3 / (2 * r ** 3))
    return sr, st, r / E * ((1 - nu) * st - nu * sr)


def discontinuity_theory(p) -> dict:
    """Equal-thickness hemisphere on a cylinder by thin-shell bending theory (Geckeler's approximation for the
    sphere near its edge: the same beta and D as the cylinder). The membrane radial displacements differ by delta
    (taken here from the exact thick-wall solutions at the mid-surface radius); the edge moment is zero by symmetry
    and the edge shear Q0 = delta beta^3 D closes the gap (p / (8 beta) in the thin limit). Cylinder, x from the
    junction: M(x) = (Q0 / beta) exp(-beta x) sin(beta x), largest at beta x = pi / 4; the junction moves by -delta / 2
    from the cylinder's membrane position, so the hoop membrane there is the Lame mean minus E delta / (2 Rm)."""
    d = dims(p)
    if abs(d["t"] - d["th"]) > 1e-12:
        return {}
    E, nu, Rm, t = _f(p, "youngs_modulus_MPa"), _f(p, "poisson_ratio"), d["Rm"], d["t"]
    beta = (3 * (1 - nu ** 2) / (Rm * t) ** 2) ** 0.25
    D = E * t ** 3 / (12 * (1 - nu ** 2))
    delta = float(lame_cylinder(p, Rm)[3] - lame_sphere(p, Rm)[2])
    Q0 = delta * beta ** 3 * D
    m_max = Q0 / beta * math.exp(-math.pi / 4) * math.sin(math.pi / 4)
    pr = _f(p, "pressure_MPa")
    return {"beta_per_mm": beta, "delta_mm": delta, "Q0_N_per_mm": Q0, "Q0_thin_N_per_mm": pr / (8 * beta),
            "bending_max_MPa": 6 * m_max / t ** 2, "x_bending_max_mm": math.pi / (4 * beta),
            "hoop_membrane_junction_MPa": pr * d["Ri"] / t - E * delta / (2 * Rm)}

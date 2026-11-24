"""O-ring face seal, squeezed by a cover (study 12): CalculiX, axisymmetric, hyperelastic, penalty contact.

Model: the upper half of the ring's cross-section (the groove bottom and the cover are flat and the ring sits centred,
so the mid-plane is a symmetry plane), a circle of diameter d centred at radius Rc, pressed by a steel cover moved
down by squeeze x d / 2. Gmsh (Python API) meshes the half disc with 8-node quads (second order, incomplete),
refined towards the top where contact grows; the cover is a coarse steel block above it, its bottom touching the
ring's top point, not merged with it. CAX8R (CAX6 for any triangle Gmsh leaves) for both bodies.

Material: neo-Hookean, C10 = G / 2 = E / 6 (incompressible), D1 = 2 / K with K = bulk_to_shear x G (near
incompressible); E from the case (Gent's relation is applied by the study, not here).
Contact: node-to-surface (surface-to-surface did not converge here), linear penalty, with the tension at large
clearance sigma_inf = contact_tension_MPa (default 0.01; the Hertz model's 1.0 let the contact edges pull: the pressure
integral missed the reaction by -14 / +40 %), k = penalty_factor x E / h_contact; the ring's arc is the slave.
Outputs per increment: the cover's reaction (2-degree segment, as CalculiX expands CAX elements) and the time.

Must not import from validation/.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np

PARAMS = ("cross_section_mm", "mean_radius_mm", "squeeze", "youngs_modulus_MPa", "bulk_to_shear",
          "contact_element_size_mm", "far_element_size_mm", "penalty_factor")
SEGMENT = 2.0 / 360.0          # CalculiX expands CAX elements into a 2-degree wedge
QUAD_FACES = ((0, 1), (1, 2), (2, 3), (3, 0))
TRI_FACES = ((0, 1), (1, 2), (2, 0))


def build_mesh(params: dict) -> dict:
    """Nodes {id: (r, z)} and elements {"RING": [(eid, type, nodes)], "COVER": [...]} from Gmsh."""
    import gmsh

    d, Rc = float(params["cross_section_mm"]), float(params["mean_radius_mm"])
    a = d / 2
    hc, hf = float(params["contact_element_size_mm"]), float(params["far_element_size_mm"])
    cover_half = float(params.get("cover_half_width_mm", 1.5 * d))
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("Geometry.AutoCoherence", 0)       # the bodies touch at one point: do not merge
        gmsh.model.add("oring")
        g = gmsh.model.geo
        C, A, T, B = g.addPoint(Rc, 0, 0), g.addPoint(Rc - a, 0, 0), g.addPoint(Rc, a, 0), g.addPoint(Rc + a, 0, 0)
        arc1, arc2, base = g.addCircleArc(B, C, T), g.addCircleArc(T, C, A), g.addLine(A, B)
        ring = g.addPlaneSurface([g.addCurveLoop([arc1, arc2, base])])
        h = float(params.get("cover_thickness_mm", a))
        walls = groove(params)
        if walls:   # the cover spans the groove and lands on the wall tops at full squeeze
            cover_half = max(cover_half, max(abs(walls["r_in"] - Rc), abs(walls["r_out"] - Rc)) + 1.0)
        p = [g.addPoint(Rc - cover_half, a, 0), g.addPoint(Rc + cover_half, a, 0),
             g.addPoint(Rc + cover_half, a + h, 0), g.addPoint(Rc - cover_half, a + h, 0)]
        lines = [g.addLine(p[i], p[(i + 1) % 4]) for i in range(4)]
        cover = g.addPlaneSurface([g.addCurveLoop(lines)])
        wall_surfs = {}
        if walls:
            t_w, z_top = 1.0, walls["half_depth"]
            for name, r0, r1 in (("WALLIN", walls["r_in"] - t_w, walls["r_in"]),
                                 ("WALLOUT", walls["r_out"], walls["r_out"] + t_w)):
                q = [g.addPoint(r0, 0, 0), g.addPoint(r1, 0, 0), g.addPoint(r1, z_top, 0), g.addPoint(r0, z_top, 0)]
                wl = [g.addLine(q[i], q[(i + 1) % 4]) for i in range(4)]
                wall_surfs[name] = (g.addPlaneSurface([g.addCurveLoop(wl)]), wl[1] if name == "WALLIN" else wl[3])
        g.synchronize()
        gmsh.model.addPhysicalGroup(2, [ring], name="RING")
        gmsh.model.addPhysicalGroup(2, [cover], name="COVER")
        f = gmsh.model.mesh.field
        f.add("Distance", 1)
        f.setNumbers(1, "PointsList", [T])
        f.setNumbers(1, "CurvesList", [lines[0]] + [c for _, c in wall_surfs.values()])
        f.setNumber(1, "Sampling", 200)
        f.add("Threshold", 2)
        f.setNumber(2, "InField", 1)
        f.setNumber(2, "SizeMin", hc)
        f.setNumber(2, "SizeMax", hf)
        f.setNumber(2, "DistMin", float(params.get("refine_distance_mm", 0.6 * a)))
        f.setNumber(2, "DistMax", float(params.get("refine_distance_mm", 0.6 * a)) + a)
        f.setAsBackgroundMesh(2)
        for k in ("MeshSizeExtendFromBoundary", "MeshSizeFromPoints", "MeshSizeFromCurvature"):
            gmsh.option.setNumber(f"Mesh.{k}", 0)
        gmsh.option.setNumber("Mesh.RecombineAll", 1)
        gmsh.option.setNumber("Mesh.Algorithm", 8)                # frontal-Delaunay for quads
        gmsh.option.setNumber("Mesh.SecondOrderIncomplete", 1)
        gmsh.model.mesh.generate(2)
        gmsh.model.mesh.setOrder(2)
        tags, xyz, _ = gmsh.model.mesh.getNodes()
        nodes = {int(t): (float(xyz[3 * i]), float(xyz[3 * i + 1])) for i, t in enumerate(tags)}
        elems = {}
        for name, s in [("RING", ring), ("COVER", cover)] + [(k, v[0]) for k, v in wall_surfs.items()]:
            out = []
            types, etags, enodes = gmsh.model.mesh.getElements(2, s)
            for typ, et, en in zip(types, etags, enodes):
                n = {16: 8, 9: 6}.get(int(typ))
                if n is None:
                    raise RuntimeError(f"unexpected Gmsh element type {typ}")
                conn = np.asarray(en, int).reshape(-1, n)
                for e, c in zip(et, conn):
                    out.append((int(e), "CAX8R" if n == 8 else "CAX6", [int(v) for v in c]))
            elems[name] = out
    finally:
        gmsh.finalize()
    # counter-clockwise corners in (r, z) for positive Jacobians
    for name in elems:
        fixed = []
        for e, t, c in elems[name]:
            k = 4 if t == "CAX8R" else 3
            P = np.array([nodes[v] for v in c[:k]])
            area = 0.5 * np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1])
            if area < 0:
                c = _reverse(c, k)
            fixed.append((e, t, c))
        elems[name] = fixed
    return {"nodes": nodes, "elems": elems, "a": a, "Rc": Rc, "walls": walls}


def groove(params: dict) -> dict | None:
    """The groove's walls in the half model, or None (a laterally unrestrained ring, Lindley's case). The groove depth
    is d (1 - squeeze); the half model's walls reach half of it, where the cover lands."""
    if not params.get("groove_inner_radius_mm"):
        return None
    d = float(params["cross_section_mm"])
    r_in = float(params["groove_inner_radius_mm"])
    return {"r_in": r_in, "r_out": r_in + float(params["groove_width_mm"]),
            "half_depth": d * (1.0 - float(params["squeeze"])) / 2.0}


def _reverse(c, k):
    """Reverse an element's node order (corners and mid-sides together)."""
    if k == 4:   # corners 0 1 2 3, mid-sides 4(0-1) 5(1-2) 6(2-3) 7(3-0)  ->  corners 0 3 2 1, mid 7 6 5 4
        return [c[0], c[3], c[2], c[1], c[7], c[6], c[5], c[4]]
    return [c[0], c[2], c[1], c[5], c[4], c[3]]             # 6-node: mid 3(0-1) 4(1-2) 5(2-0)


def element_polygon(nodes, t, c):
    """Boundary points of an element in order (corner, mid-side, corner ...)."""
    order = (0, 4, 1, 5, 2, 6, 3, 7) if t == "CAX8R" else (0, 3, 1, 4, 2, 5)
    return np.array([nodes[c[i]] for i in order])


def faces_on(elems, nodes, test):
    """(element id, face label) for faces whose two corners satisfy test(r, z)."""
    out = []
    for e, t, c in elems:
        for k, (i, j) in enumerate(QUAD_FACES if t == "CAX8R" else TRI_FACES):
            if test(*nodes[c[i]]) and test(*nodes[c[j]]):
                out.append((e, f"S{k + 1}"))
    return out


def arc_edges(mesh: dict) -> list[tuple[int, int, int]]:
    """(corner, mid-side, corner) node triples of the ring's element edges on the arc (the contact surface)."""
    nodes, a, Rc = mesh["nodes"], mesh["a"], mesh["Rc"]
    on = lambda n: abs(math.hypot(nodes[n][0] - Rc, nodes[n][1]) - a) < 1e-5 * a and nodes[n][1] > 1e-6 * a  # noqa: E731
    out = []
    for _, t, c in mesh["elems"]["RING"]:
        faces, mid0 = (QUAD_FACES, 4) if t == "CAX8R" else (TRI_FACES, 3)
        for k, (i, j) in enumerate(faces):
            if on(c[i]) and on(c[j]):
                out.append((c[i], c[mid0 + k], c[j]))
    return out


def write_deck(mesh: dict, params: dict, deck: Path) -> dict:
    nodes, elems, a, Rc = mesh["nodes"], mesh["elems"], mesh["a"], mesh["Rc"]
    E = float(params["youngs_modulus_MPa"])
    G = E / 3.0
    K = float(params["bulk_to_shear"]) * G
    C10, D1 = G / 2.0, 2.0 / K
    delta = float(params["squeeze"]) * 2 * a / 2               # half model: the cover moves half the squeeze
    tol = 1e-6 * a
    ring_nodes = sorted({v for _, _, c in elems["RING"] for v in c})
    cover_nodes = sorted({v for _, _, c in elems["COVER"] for v in c})
    on_arc = lambda r, z: abs(math.hypot(r - Rc, z) - a) < 1e-5 * a and z > tol  # noqa: E731
    on_cover_bottom = lambda r, z: abs(z - a) < tol  # noqa: E731
    slave = faces_on(elems["RING"], nodes, on_arc)
    master = faces_on(elems["COVER"], nodes, on_cover_bottom)
    walls = mesh.get("walls")
    wall_faces, wall_nodes = {}, []
    if walls:
        wall_faces["WALLIN"] = faces_on(elems["WALLIN"], nodes, lambda r, z: abs(r - walls["r_in"]) < tol)
        wall_faces["WALLOUT"] = faces_on(elems["WALLOUT"], nodes, lambda r, z: abs(r - walls["r_out"]) < tol)
        wall_nodes = sorted({v for k in ("WALLIN", "WALLOUT") for _, _, c in elems[k] for v in c})
    sym = [n for n in ring_nodes if abs(nodes[n][1]) < tol]
    top = [n for n in cover_nodes if abs(nodes[n][1] - max(nodes[m][1] for m in cover_nodes)) < tol]
    k_pen = float(params["penalty_factor"]) * E / float(params["contact_element_size_mm"])

    def nset(name, arr):
        rows = [", ".join(str(int(v)) for v in arr[i:i + 12]) for i in range(0, len(arr), 12)]
        return f"*NSET, NSET={name}\n" + "\n".join(rows) + "\n"

    lines = ["*NODE"] + [f"{n}, {x!r}, {y!r}" for n, (x, y) in sorted(nodes.items())]
    for name in [k for k in ("RING", "COVER", "WALLIN", "WALLOUT") if k in elems]:
        for t in ("CAX8R", "CAX6"):
            es = [(e, c) for e, tt, c in elems[name] if tt == t]
            if es:
                lines.append(f"*ELEMENT, TYPE={t}, ELSET={name}")
                lines += [f"{e}, " + ", ".join(map(str, c)) for e, c in es]
    deck.write_text(
        "\n".join(lines) + "\n" + nset("NRING", ring_nodes) + nset("SYM", sym) + nset("CTOP", top)
        + "*SURFACE, NAME=SRING\n" + "".join(f"{e}, {f}\n" for e, f in slave)
        + "*SURFACE, NAME=SCOVER\n" + "".join(f"{e}, {f}\n" for e, f in master)
        + "".join(f"*SURFACE, NAME=S{k}\n" + "".join(f"{e}, {f}\n" for e, f in v) for k, v in wall_faces.items())
        + (nset("NWALL", wall_nodes) if wall_nodes else "")
        + f"*MATERIAL, NAME=RUBBER\n*HYPERELASTIC, NEO HOOKE\n{C10!r}, {D1!r}\n"
        + "*MATERIAL, NAME=STEEL\n*ELASTIC\n200000., 0.3\n"
        + "*SOLID SECTION, ELSET=RING, MATERIAL=RUBBER\n*SOLID SECTION, ELSET=COVER, MATERIAL=STEEL\n"
        + "".join(f"*SOLID SECTION, ELSET={k}, MATERIAL=STEEL\n" for k in wall_faces)
        + "*CONTACT PAIR, INTERACTION=SI1, TYPE=NODE TO SURFACE\nSRING, SCOVER\n"
        + "".join(f"*CONTACT PAIR, INTERACTION=SI1, TYPE=NODE TO SURFACE\nSRING, S{k}\n" for k in wall_faces)
        + f"*SURFACE INTERACTION, NAME=SI1\n*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=LINEAR\n"
        + f"{k_pen!r}, {float(params.get('contact_tension_MPa', 0.01))!r}\n"
        + "*BOUNDARY\nSYM, 2, 2, 0.\nCTOP, 1, 1, 0.\n" + ("NWALL, 1, 2, 0.\n" if wall_nodes else "")
        + f"*STEP, NLGEOM, INC={int(params.get('max_increments', 2000))}\n*STATIC\n"
        + f"{float(params.get('first_increment', 0.01))!r}, 1.0, 1e-8, {float(params.get('max_increment', 0.02))!r}\n"
        + f"*BOUNDARY\nCTOP, 2, 2, {-delta!r}\n"
        + "*NODE FILE, FREQUENCY=10000\nU\n*EL FILE, FREQUENCY=10000\nS, E\n"
        + "*CONTACT FILE, FREQUENCY=10000\nCSTR, CDIS\n"
        + "*NODE PRINT, NSET=CTOP, TOTALS=ONLY, FREQUENCY=1\nRF\n*NODE PRINT, NSET=SYM, TOTALS=ONLY\nRF\n"
        + ("*NODE PRINT, NSET=NWALL, TOTALS=ONLY\nRF\n" if wall_nodes else "") + "*END STEP\n", encoding="utf-8")
    return {"nodes": len(nodes), "ring_elements": len(elems["RING"]), "cover_elements": len(elems["COVER"]),
            "slave_faces": len(slave), "master_faces": len(master), "penalty_MPa_per_mm": k_pen,
            "wall_faces": {k: len(v) for k, v in wall_faces.items()},
            "C10_MPa": C10, "D1_per_MPa": D1, "cover_travel_mm": delta}


_RF = re.compile(r"total force \(fx,fy,fz\) for set CTOP and time\s+([-+0-9.eE]+)")


def read_force_history(dat: Path) -> list[tuple[float, float]]:
    """(time, axial reaction on the cover, 2-degree segment) for every increment printed."""
    lines = Path(dat).read_text(encoding="latin-1").splitlines()
    out = []
    for i, ln in enumerate(lines):
        m = _RF.search(ln)
        if m:
            for nxt in lines[i + 1:i + 4]:
                vals = nxt.split()
                if len(vals) >= 3:
                    out.append((float(m.group(1)), float(vals[1])))
                    break
    return out


def ring_volume_mm3(nodes, ring_elems) -> float:
    """Volume of revolution of the ring half (Pappus: 2 pi * sum of area x centroid radius over elements)."""
    V = 0.0
    for e, t, c in ring_elems:
        P = element_polygon(nodes, t, c)
        x, y = P[:, 0], P[:, 1]
        cr = x * np.roll(y, -1) - np.roll(x, -1) * y
        A = 0.5 * cr.sum()
        cx = np.sum((x + np.roll(x, -1)) * cr) / (6 * A)
        V += 2 * math.pi * A * cx
    return V

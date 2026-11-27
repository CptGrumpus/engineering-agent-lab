"""Study 25 part 2: the pump cover between its bolts. Part 1 took the cover as flat and rigid; a real cover is a plate
held at its bolts, and the 3 bar inside the seal and the O-ring's own reaction push it away from the pump between
them. The cover's lift at the seal line takes squeeze straight off the O-ring.

Geometry (mm): a circular aluminium cover of diameter Dc and thickness t, its underside on z = 0 against the pump
flange, N bolts on a circle; a quarter model (x >= 0, y >= 0) with the bolts placed so that both symmetry planes are
symmetry planes of the bolt pattern (N = 4: bolts at 45 deg; N = 6: at 30 and 90 deg; N = 8: 22.5 and 67.5 deg). The
underside is split by CadQuery at the radii where the loads begin and end, so each load sits on its own faces.

Loads (on the underside, upward): the sealed pressure inside the groove's outer diameter (conservative: the pressure
reaches the ring's outer contact), and the O-ring's line load from part 1 (N per mm of seal at its centroid radius),
spread over an annulus of the contact width.

Supports: the bolts hold the cover on a rigid flange: underside nodes within the washer's footprint around each bolt
hole are held against lifting (clamp = "z", free to slide and pivot: the softer bound) or in every direction
(clamp = "full": the stiffest). The flange is rigid and the rim beyond the bolts is not supported (a real flange
would push back on the rim as the cover lifts between bolts, and lower the lift). Symmetry on x = 0 and y = 0.
CalculiX's RF is a node's internal force: at a support node that also carries load it includes that load, so the
reaction check needs a support free of load (true for the washer footprints, not for the edge-supported reference).

Reference: support = "edge" replaces the bolts by a simple support along the underside's outer edge with the
pressure over the whole underside: the plate-theory centre deflection w = q a^4 (5 + nu) / (64 D (1 + nu)) (Kirchhoff)
times the transverse-shear correction of Mindlin's plate, 1 + 32 (1 + nu) t^2 / (12 (1 - nu) k (5 + nu) a^2), k = 5/6.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

PARAMS = ("cover_diameter_mm", "cover_thickness_mm", "bolt_count", "bolt_circle_diameter_mm", "bolt_hole_diameter_mm",
          "washer_diameter_mm", "pressure_MPa", "pressure_radius_mm", "oring_line_load_N_per_mm", "oring_radius_mm",
          "oring_contact_width_mm", "youngs_modulus_MPa", "poisson_ratio", "element_size_mm", "support")
FACES4 = ((0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0))


def bolt_angles(n: int) -> list[float]:
    """Bolt angles (rad) in the first quadrant (including the axes), for a pattern symmetric about both axes."""
    if n % 2 or n < 4:
        raise ValueError("the quarter model needs an even bolt count of at least 4")
    step = 2 * math.pi / n
    first = step / 2 if (n // 2) % 2 == 0 else step / 2       # n = 4, 8: offset by half a pitch; n = 6: 30 deg
    out = [first + k * step for k in range(n) if -1e-9 <= first + k * step <= math.pi / 2 + 1e-9]
    return out


def mindlin_centre_deflection(p: dict) -> float:
    a, t = float(p["cover_diameter_mm"]) / 2, float(p["cover_thickness_mm"])
    E, nu, q = float(p["youngs_modulus_MPa"]), float(p["poisson_ratio"]), float(p["pressure_MPa"])
    D = E * t ** 3 / (12 * (1 - nu ** 2))
    wk = q * a ** 4 * (5 + nu) / (64 * D * (1 + nu))
    return wk * (1 + 32 * (1 + nu) * t ** 2 / (12 * (1 - nu) * (5 / 6) * (5 + nu) * a ** 2))


def build_step(p: dict, path: Path) -> dict:
    import cadquery as cq

    R, t = float(p["cover_diameter_mm"]) / 2, float(p["cover_thickness_mm"])
    body = cq.Workplane("XY").circle(R).extrude(t)
    rb, dh = float(p["bolt_circle_diameter_mm"]) / 2, float(p["bolt_hole_diameter_mm"])
    angles = bolt_angles(int(p["bolt_count"])) if p["support"] == "bolts" else []
    for th in angles:
        body = body.cut(cq.Workplane("XY").center(rb * math.cos(th), rb * math.sin(th)).circle(dh / 2).extrude(t + 1)
                        .translate((0, 0, -0.5)))
    body = body.intersect(cq.Workplane("XY").box(R + 1, R + 1, t + 2, centered=False).translate((0, 0, -1)))
    # split the underside: the load radii (and the washer footprints) as their own faces
    radii = sorted({float(p["pressure_radius_mm"]), float(p["oring_radius_mm"]) - float(p["oring_contact_width_mm"]) / 2,
                    float(p["oring_radius_mm"]) + float(p["oring_contact_width_mm"]) / 2}) if p["support"] == "bolts" else []
    sh = body.val()
    edges = []
    for r in radii:
        edges.append(cq.Edge.makeCircle(r, cq.Vector(0, 0, 0), cq.Vector(0, 0, 1)))
    for th in angles:
        edges.append(cq.Edge.makeCircle(float(p["washer_diameter_mm"]) / 2,
                                        cq.Vector(rb * math.cos(th), rb * math.sin(th), 0), cq.Vector(0, 0, 1)))
    if edges:
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Splitter
        from OCP.TopTools import TopTools_ListOfShape

        args, tls = TopTools_ListOfShape(), TopTools_ListOfShape()
        args.Append(sh.wrapped)
        for e in edges:
            tls.Append(e.wrapped)
        sp = BRepAlgoAPI_Splitter()
        sp.SetArguments(args)
        sp.SetTools(tls)
        sp.Build()
        sh = cq.Shape.cast(sp.Shape())
    sol = sh.Solids() if hasattr(sh, "Solids") else [sh]
    cq.exporters.export(cq.Workplane("XY").newObject([sh]), str(path))
    return {"volume_mm3": float(sum(s.Volume() for s in sol)), "solids": len(sol),
            "valid": bool(all(s.isValid() for s in sol)), "bolt_angles_deg": [math.degrees(a) for a in angles]}


def write_geo(p: dict, path: Path, step_name: str = "cover.step") -> None:
    h = float(p["element_size_mm"])
    # curvature sizing (elements per circle): 12 in the first runs; 0 (off) for a mesh study, where it would keep the
    # bolt holes' and washers' element counts fixed while the rest refines (oring_cover_mesh_r1)
    nc = int(p.get("curvature_elements_per_circle", 12))
    path.write_text(f"""SetFactory("OpenCASCADE");
Merge "{step_name}";
Mesh.MeshSizeMax = {h!r}; Mesh.MeshSizeMin = {0.2 * h!r}; Mesh.MeshSizeFromCurvature = {nc};
Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 0; Mesh.Optimize = 1;
Physical Volume("COVER") = Volume{{:}};
""", encoding="utf-8")


def read_mesh(mesh_inp: Path):
    from models.fea import pressure_vessel as pv

    return pv.read_mesh(mesh_inp)


def write_deck(p: dict, mesh_inp: Path, deck: Path) -> dict:
    ids, xyz, eids, elems = read_mesh(mesh_inp)
    row = {int(n): k for k, n in enumerate(ids)}
    conn = np.vectorize(row.get)(elems)
    tol = 1e-6 * float(p["cover_diameter_mm"])
    x, y, z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    r = np.hypot(x, y)
    under = np.abs(z) < tol
    # element faces on the underside, sorted by the radius of their centroid
    faces = []
    for f, tri in enumerate(FACES4):
        hit = np.all(under[conn[:, list(tri)]], axis=1)
        for e in np.flatnonzero(hit):
            c = xyz[conn[e, list(tri)]].mean(axis=0)
            faces.append((int(eids[e]), f + 1, float(math.hypot(c[0], c[1]))))
    q, Rp = float(p["pressure_MPa"]), float(p["pressure_radius_mm"])
    loads, applied = [], 0.0
    if p["support"] == "edge":
        loads = [(e, f, q) for e, f, rc in faces]
        R = float(p["cover_diameter_mm"]) / 2
        applied = q * math.pi * R ** 2 / 4
    else:
        ro, w = float(p["oring_radius_mm"]), float(p["oring_contact_width_mm"])
        qo = float(p["oring_line_load_N_per_mm"]) / w
        for e, f, rc in faces:
            v = (q if rc < Rp else 0.0) + (qo if ro - w / 2 < rc < ro + w / 2 else 0.0)
            if v:
                loads.append((e, f, v))
        applied = q * math.pi * Rp ** 2 / 4 + float(p["oring_line_load_N_per_mm"]) * math.pi * ro / 2
    sets = {"XSYM": ids[np.abs(x) < tol], "YSYM": ids[np.abs(y) < tol]}
    if p["support"] == "edge":
        R = float(p["cover_diameter_mm"]) / 2
        sets["SUPPORT"] = ids[under & (np.abs(r - R) < 1e-4 * R)]
    else:
        rb, rw = float(p["bolt_circle_diameter_mm"]) / 2, float(p["washer_diameter_mm"]) / 2
        clamp = np.zeros(len(ids), bool)
        for th in bolt_angles(int(p["bolt_count"])):
            d = np.hypot(x - rb * math.cos(th), y - rb * math.sin(th))
            clamp |= under & (d <= rw + 1e-6)
        sets["SUPPORT"] = ids[clamp]
    E, nu = float(p["youngs_modulus_MPa"]), float(p["poisson_ratio"])
    rows = lambda a: [", ".join(str(int(v)) for v in a[s:s + 12]) for s in range(0, len(a), 12)]  # noqa: E731
    lines = [f"*INCLUDE, INPUT={Path(mesh_inp).name}"]
    for k, v in sets.items():
        lines += [f"*NSET, NSET={k}"] + rows(v)
    lines += ["*MATERIAL, NAME=AL", "*ELASTIC", f"{E!r}, {nu!r}", "*SOLID SECTION, ELSET=COVER, MATERIAL=AL",
              "*BOUNDARY", "XSYM, 1, 1, 0.", "YSYM, 2, 2, 0."]
    # clamp = "z" (default): the washer footprint held against lifting only, free to slide and pivot (the softer, and
    # here conservative, bound); "full": held in every direction (the stiffest bound)
    full = p["support"] == "bolts" and str(p.get("clamp", "z")) == "full"
    lines += ["SUPPORT, 1, 3, 0."] if full else ["SUPPORT, 3, 3, 0."]
    # CalculiX: a positive *DLOAD pressure pushes into the face (along -n); the underside's outward normal is -z, so a
    # positive value pushes the cover up (+z)
    lines += ["*STEP", "*STATIC", "*DLOAD"] + [f"{e}, P{f}, {v!r}" for e, f, v in loads]
    lines += ["*NODE FILE", "U", "*EL FILE", "S", "*NODE PRINT, NSET=SUPPORT, TOTALS=ONLY", "RF", "*END STEP"]
    deck.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"nodes": int(len(ids)), "elements": int(len(eids)), "loaded_faces": len(loads),
            "support_nodes": int(len(sets["SUPPORT"])), "applied_quarter_load_N": applied}


def seal_line_lift(ids, xyz, elems, uz: dict, p: dict, n: int = 181) -> tuple[np.ndarray, np.ndarray, float]:
    """The underside's upward displacement on the O-ring's centroid circle (0 to 90 deg), interpolated with the
    elements' quadratic shape functions at n points exactly on the circle; and the largest barycentric violation of
    those points. (The first evidence runs, 20261127-161204 and -161311, read the nodes within half an element of the
    circle instead: nodes at slightly different radii, a sawtooth of up to 5 % in the lift and in its maximum.)"""
    from harness.linearize import Tet10Sampler

    ro = float(p["oring_radius_mm"])
    th = np.linspace(0.0, 90.0, n)
    pts = np.column_stack([ro * np.cos(np.radians(th)), ro * np.sin(np.radians(th)), np.zeros(n)])
    field = np.array([[uz[int(k)]] for k in ids])
    vals, viol = Tet10Sampler(ids, xyz, elems).sample(pts, field)
    return th, vals[:, 0], float(viol)

"""Semi-elliptical surface crack in a plate in tension (study 24 part 2): Gmsh quarter model -> CalculiX -> K(phi).

Quarter model 0 <= x <= W/2 (width), 0 <= y <= H (load direction), 0 <= z <= t (thickness). The crack lies in the
plane y = 0 (symmetry), its mouth on the face z = 0, centred on x = 0 (symmetry): the quarter ellipse
(x / c)^2 + (z / a)^2 <= 1, depth a, half surface length c. Its face is free; the rest of y = 0 (the ligament) has
uy = 0; x = 0 has ux = 0; one node has uz = 0. A uniform traction sigma acts on y = H through consistent nodal forces
(10-node tetrahedra: the 6-node face triangles load only their mid-side nodes, sigma A / 3 each), so the external
work is exact: U_q = 1/2 sum(f uy) over y = H.

The crack front point at parametric angle phi is (c cos phi, 0, a sin phi): phi = 0 at the surface, pi / 2 at the
deepest point (Newman and Raju's angle).

Two routes to K, no singular elements:
- crack opening: behind the front, along its in-plane normal, uy = 4 (1 - nu^2) K / E sqrt(r / 2 pi) (plane strain,
  half the opening). The apparent K of each crack-face node near a station is fitted linearly in r (and in the
  arc-length offset from the station) and extrapolated to r = 0. Plane strain does not hold at the free surface,
  so the surface point itself is reported, not checked;
- energy (an average along the front): scaling the crack by (1 + eps) moves each front point eps X normal to the
  front by eps X.n, and X.n ds = a c dphi on an ellipse, so for the quarter model
  dU_q / deps = 1/2 a c int_0^(pi/2) G(phi) dphi, G = K^2 (1 - nu^2) / E (the full body's energy is 4 U_q and its
  front is two quarter fronts). The central difference of U_q over three solves is compared with the integral of
  the opening route's K profile (and with Newman-Raju's).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

TOL = 1e-6  # mm, for picking nodes on planes
# CalculiX C3D10 mid-side nodes (0-based) and the corner pair each sits on
C3D10_EDGES = {4: (0, 1), 5: (1, 2), 6: (2, 0), 7: (0, 3), 8: (1, 3), 9: (2, 3)}
FACES = ((0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0))


def mesh(path: Path, *, a: float, c: float, Wh: float, H: float, t: float, h_front: float, h_far: float,
         r_fine: float, growth: float = 0.25, seed: int = 0) -> dict:
    """Mesh the quarter plate with Gmsh (OpenCASCADE kernel) and write `path` (Abaqus .inp, C3D10 only).
    Elements within r_fine of the front are h_front; beyond, the size grows by `growth` per mm of distance up to
    h_far. Returns counts and the Gmsh version."""
    import gmsh

    gmsh.initialize(["-noenv"])
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("Mesh.RandomSeed", seed)
        gmsh.model.add("sc")
        occ = gmsh.model.occ
        box = occ.addBox(0, 0, 0, Wh, H, t)
        disk = occ.addDisk(0, 0, 0, c, a)                  # in the xy plane, rx = c, ry = a
        occ.rotate([(2, disk)], 0, 0, 0, 1, 0, 0, np.pi / 2)  # y -> z: the ellipse now lies in y = 0
        quarter, _ = occ.intersect([(2, disk)], [(3, box)], removeObject=True, removeTool=False)
        occ.fragment([(3, box)], quarter)
        occ.synchronize()
        e = 1e-6 * max(Wh, H)
        arc = [tag for _, tag in gmsh.model.getEntitiesInBoundingBox(-e, -e, -e, c + e, e, a + e, dim=1)
               if _span(gmsh.model.getBoundingBox(1, tag)) > 0.5 * min(a, c)]
        if len(arc) != 1:
            raise RuntimeError(f"expected one crack-front curve, found {arc}")
        vols = gmsh.model.getEntities(3)
        if len(vols) != 1:
            raise RuntimeError(f"expected one volume after the fragment, found {vols}")
        gmsh.model.addPhysicalGroup(3, [vols[0][1]], name="PLATE")
        f = gmsh.model.mesh.field
        d = f.add("Distance")
        f.setNumbers(d, "CurvesList", arc)
        f.setNumber(d, "Sampling", max(200, int(4 * np.pi / 2 * max(a, c) / h_front)))
        m = f.add("MathEval")
        f.setString(m, "F", f"Min({h_far!r}, Max({h_front!r}, {h_front!r} + {growth!r} * (F{d} - {r_fine!r})))")
        f.setAsBackgroundMesh(m)
        for k, v in (("Mesh.MeshSizeExtendFromBoundary", 0), ("Mesh.MeshSizeFromPoints", 0),
                     ("Mesh.MeshSizeFromCurvature", 0), ("Mesh.ElementOrder", 2), ("Mesh.SecondOrderLinear", 0),
                     ("Mesh.Algorithm3D", 10), ("Mesh.SaveAll", 0)):
            gmsh.option.setNumber(k, v)
        gmsh.model.mesh.generate(3)
        types, tags, _ = gmsh.model.mesh.getElements(3)
        n_el = int(sum(len(x) for x in tags))
        gmsh.write(str(path))
        return {"elements": n_el, "element_types": [int(x) for x in types], "gmsh": gmsh.__version__}
    finally:
        gmsh.finalize()


def _span(bb):
    return min(bb[3] - bb[0], bb[5] - bb[2])        # x and z extents: both non-zero only for the arc


def read_mesh(mesh_inp: Path):
    """Nodes (ids, xyz) and C3D10 connectivity (node ids) from Gmsh's .inp."""
    text = Path(mesh_inp).read_text(encoding="utf-8")
    nblock = text.split("*NODE", 1)[1].split("*", 1)[0]
    rows = np.array([[float(v) for v in ln.split(",")] for ln in nblock.strip().splitlines()])
    ids, xyz = rows[:, 0].astype(int), rows[:, 1:4]
    conn = []
    for part in text.split("*ELEMENT")[1:]:
        head, body = part.split("\n", 1)
        if "C3D10" not in head.upper():
            continue
        body = body.split("*", 1)[0]
        vals = [int(v) for v in body.replace("\n", ",").split(",") if v.strip()]
        conn.extend(vals[i + 1:i + 11] for i in range(0, len(vals), 11))
    if not conn:
        raise RuntimeError("no C3D10 elements in the mesh")
    return ids, xyz, np.array(conn, dtype=int)


def write_deck(mesh_inp: Path, deck: Path, *, a: float, c: float, Wh: float, H: float, t: float, sigma: float,
               E: float, nu: float) -> dict:
    ids, xyz, conn = read_mesh(mesh_inp)
    x, y, z = xyz.T
    pos = {int(i): k for k, i in enumerate(ids)}
    on0 = np.abs(y) < TOL
    rho = (x / c) ** 2 + (z / a) ** 2
    lig = ids[on0 & (rho >= 1 - 1e-9)]
    crack = ids[on0 & (rho < 1 - 1e-9)]
    sym = ids[np.abs(x) < TOL]
    far = np.where(on0 & (np.abs(x - Wh) < TOL) & (np.abs(z - t) < TOL))[0]
    if len(far) != 1:
        raise RuntimeError(f"corner node (W/2, 0, t): found {len(far)}")
    # consistent loads on y = H: each flat 6-node face triangle puts sigma A / 3 on each mid-side node
    load: dict[int, float] = {}
    mid_of = {frozenset(pair): m for m, pair in C3D10_EDGES.items()}
    for el in conn:
        p = xyz[[pos[n] for n in el[:4]]]
        for f in FACES:
            if np.all(np.abs(p[list(f), 1] - H) < TOL):
                A = 0.5 * np.linalg.norm(np.cross(p[f[1]] - p[f[0]], p[f[2]] - p[f[0]]))
                for i, j in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
                    n = int(el[mid_of[frozenset((i, j))]])
                    load[n] = load.get(n, 0.0) + float(sigma * A / 3)   # numpy repr would break the deck
    if not load:
        raise RuntimeError("no element faces on y = H")
    lids = np.array(sorted(load))
    top = ids[np.abs(y - H) < TOL]

    def nset(name, arr):
        arr = [int(i) for i in arr]
        return f"*NSET, NSET={name}\n" + "\n".join(", ".join(map(str, arr[k:k + 12])) for k in range(0, len(arr), 12)) + "\n"

    deck.write_text(
        f"*INCLUDE, INPUT={Path(mesh_inp).name}\n" + nset("LIG", lig) + nset("CRACK", crack) + nset("SYM", sym)
        + nset("CORNER", ids[far]) + nset("TOP", top)
        + f"*MATERIAL, NAME=STEEL\n*ELASTIC\n{float(E)!r}, {float(nu)!r}\n*SOLID SECTION, ELSET=PLATE, MATERIAL=STEEL\n"
        + "*BOUNDARY\nLIG, 2, 2, 0.\nSYM, 1, 1, 0.\nCORNER, 3, 3, 0.\n"
        + "*STEP\n*STATIC\n*CLOAD\n" + "".join(f"{int(i)}, 2, {load[int(i)]!r}\n" for i in lids)
        + "*NODE PRINT, NSET=TOP\nU\n*NODE PRINT, NSET=CRACK\nU\n*NODE PRINT, NSET=LIG, TOTALS=ONLY\nRF\n*END STEP\n",
        encoding="utf-8")
    return {"nodes": int(len(ids)), "elements": int(len(conn)), "crack_nodes": int(len(crack)),
            "ligament_nodes": int(len(lig)), "loaded_nodes": int(len(lids)),
            "applied_load_N": float(sum(load.values())), "area_check": float(sum(load.values()) / (sigma * Wh * t)),
            "load_ids": lids.tolist(), "loads": [load[int(i)] for i in lids],
            "crack_xyz": {int(i): xyz[pos[int(i)]].tolist() for i in crack}}


def read_node_print(dat: Path) -> tuple[dict, dict, float]:
    """(TOP displacements {id: (ux, uy, uz)}, CRACK displacements, total ligament reaction in y) from job.dat."""
    blocks, cur = {}, None
    for ln in Path(dat).read_text(encoding="utf-8", errors="replace").splitlines():
        s = ln.strip()
        if s.startswith("displacements (vx,vy,vz) for set"):
            cur = blocks.setdefault(s.split("set")[1].split()[0], {})
            continue
        if s.startswith("total force (fx,fy,fz) for set"):
            cur = blocks.setdefault("RF_" + s.split("set")[1].split()[0], {})
            continue
        parts = s.split()
        if cur is None or not parts:
            continue
        try:
            vals = [float(v) for v in parts]
        except ValueError:
            cur = None
            continue
        if len(vals) == 3:
            cur["total"] = vals
        else:
            cur[int(vals[0])] = tuple(vals[1:4])
    rf = blocks.get("RF_LIG", {}).get("total")
    return blocks["TOP"], blocks["CRACK"], float(rf[1]) if rf else float("nan")


def quarter_energy(top_disp: dict, info: dict) -> float:
    """U_q = 1/2 sum(f uy) over the loaded face (N mm)."""
    return 0.5 * float(sum(f * top_disp[i][1] for i, f in zip(info["load_ids"], info["loads"])))


def front_coords(px, pz, a: float, c: float):
    """Nearest point on the ellipse x = c cos phi, z = a sin phi to each (px, pz): (phi, distance r, arc length s
    of that point from phi = 0). Newton on the stationarity condition, started from the angle of the scaled point."""
    px, pz = np.asarray(px, float), np.asarray(pz, float)
    phi = np.arctan2(pz / a, px / c)
    for _ in range(30):
        cs, sn = np.cos(phi), np.sin(phi)
        g = (c * cs - px) * (-c * sn) + (a * sn - pz) * (a * cs)
        dg = (c * sn) ** 2 + (c * cs - px) * (-c * cs) + (a * cs) ** 2 + (a * sn - pz) * (-a * sn)
        phi = np.clip(phi - g / dg, 0.0, np.pi / 2)
    r = np.hypot(c * np.cos(phi) - px, a * np.sin(phi) - pz)
    return phi, r, arc_length(phi, a, c)


def arc_length(phi, a: float, c: float, n: int = 2000):
    grid = np.linspace(0, np.pi / 2, n)
    ds = np.hypot(c * np.sin(grid), a * np.cos(grid))
    s = np.concatenate([[0], np.cumsum(0.5 * (ds[1:] + ds[:-1]) * np.diff(grid))])
    return np.interp(phi, grid, s)


def k_profile(crack_disp: dict, info: dict, *, a: float, c: float, E: float, nu: float, stations_deg, r_min: float,
              r_max: float, band: float) -> list[dict]:
    """Plane-strain K (N/mm^1.5) at each station from the crack-face opening; see the module docstring."""
    nid = np.array(list(crack_disp))
    uy = np.array([crack_disp[i][1] for i in nid])
    p = np.array([info["crack_xyz"][int(i)] for i in nid])
    phi, r, s = front_coords(p[:, 0], p[:, 2], a, c)
    kapp = uy * E / (4 * (1 - nu ** 2)) * np.sqrt(2 * np.pi / np.maximum(r, 1e-12))
    out = []
    for deg in stations_deg:
        s0 = float(arc_length(np.radians(deg), a, c))
        sel = (r >= r_min) & (r <= r_max) & (np.abs(s - s0) <= band)
        if sel.sum() < 6:
            out.append({"phi_deg": float(deg), "K": float("nan"), "points": int(sel.sum())})
            continue
        A = np.column_stack([np.ones(sel.sum()), r[sel], s[sel] - s0])
        coef, *_ = np.linalg.lstsq(A, kapp[sel], rcond=None)
        out.append({"phi_deg": float(deg), "K": float(coef[0]), "points": int(sel.sum())})
    return out


def newman_raju_F(a: float, c: float, t: float, b: float, phi):
    """Newman and Raju (1981) surface crack in a finite plate under tension, a/c <= 1: K = sigma sqrt(pi a / Q) F.
    Returns F / sqrt(Q), so K = sigma sqrt(pi a) * this. b is the plate's half width. Stated accuracy +-5 %
    for 0 < a/c <= 1, a/t < 0.8 (their fit to Raju and Newman's 1979 FE)."""
    r, at = a / c, a / t
    M1 = 1.13 - 0.09 * r
    M2 = -0.54 + 0.89 / (0.2 + r)
    M3 = 0.5 - 1 / (0.65 + r) + 14 * (1 - r) ** 24
    g = 1 + (0.1 + 0.35 * at ** 2) * (1 - np.sin(phi)) ** 2
    fphi = (r ** 2 * np.cos(phi) ** 2 + np.sin(phi) ** 2) ** 0.25
    fw = (1 / np.cos(np.pi * c / (2 * b) * np.sqrt(at))) ** 0.5
    Q = 1 + 1.464 * r ** 1.65
    return (M1 + M2 * at ** 2 + M3 * at ** 4) * g * fphi * fw / np.sqrt(Q)


def energy_integral(phi_deg, K, a: float, c: float, E: float, nu: float) -> float:
    """1/2 a c int G dphi over [0, pi/2] (trapezoid on the given stations, which must span 0-90 degrees)."""
    ph = np.radians(np.asarray(phi_deg, float))
    G = np.asarray(K, float) ** 2 * (1 - nu ** 2) / E
    return float(0.5 * a * c * np.trapezoid(G, ph))

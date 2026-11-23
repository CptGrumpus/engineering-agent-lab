"""Edge-cracked plate in tension (study F): Gmsh half model on the crack plane -> CalculiX plane strain -> K.

Half model 0 <= x <= W, 0 <= y <= H (symmetry about the crack plane y = 0). The crack runs along y = 0 from the
free edge x = 0 to the tip x = a: its face is free; the ligament a <= x <= W has uy = 0; one node (W, 0) has ux = 0.
A uniform traction sigma acts on y = H (the plate's ends are free to rotate, as in Tada's edge-crack solution).
Analysis thickness 1 mm, so forces are per mm of thickness.

Two routes to K, neither needs singular elements (CalculiX expands 2D elements into one-layer 3D ones, which
makes collapsed quarter-point elements risky):
- energy: G = dU_full / da per unit thickness, with U_half = 1/2 sum(f u) over the loaded edge (exact for a linear
  model) and U_full = 2 U_half; central difference at a (1 -+ eps); K = sqrt(E G / (1 - nu^2)) (plane strain);
- crack opening: near the tip uy = 4 (1 - nu^2) K / E sqrt(r / 2 pi) (plane strain, half the opening); the apparent
  K(r) from each crack-face node is fitted linearly in r and extrapolated to r = 0.

Traps handled here:
- numpy floats are cast to float before formatting;
- Gmsh writes 6-node triangles as CPS6 (plane stress); they are renamed CPE6 for plane strain;
- the points run counter-clockwise, so the face normal is +z and CalculiX sees positive Jacobians.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

TOL = 1e-7  # mm, for picking nodes on straight edges


def write_geo(path: Path, *, a: float, W: float, H: float, h_tip: float, h_far: float) -> None:
    path.write_text(f"""Point(1) = {{0, 0, 0, {h_far!r}}};
Point(2) = {{{a!r}, 0, 0, {h_tip!r}}};
Point(3) = {{{W!r}, 0, 0, {h_far!r}}};
Point(4) = {{{W!r}, {H!r}, 0, {h_far!r}}};
Point(5) = {{0, {H!r}, 0, {h_far!r}}};
Line(1) = {{1, 2}}; Line(2) = {{2, 3}}; Line(3) = {{3, 4}}; Line(4) = {{4, 5}}; Line(5) = {{5, 1}};
Curve Loop(1) = {{1, 2, 3, 4, 5}};
Plane Surface(1) = {{1}};
Field[1] = Distance; Field[1].PointsList = {{2}};
Field[2] = Threshold; Field[2].InField = 1;
Field[2].SizeMin = {h_tip!r}; Field[2].SizeMax = {h_far!r};
Field[2].DistMin = {10 * h_tip!r}; Field[2].DistMax = {0.5 * W!r};
Background Field = 2;
Mesh.MeshSizeExtendFromBoundary = 0; Mesh.MeshSizeFromPoints = 0; Mesh.MeshSizeFromCurvature = 0;
Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 0;
Physical Surface("PLATE") = {{1}};
""", encoding="utf-8")


def read_mesh_nodes(mesh_inp: Path):
    text = Path(mesh_inp).read_text(encoding="utf-8")
    block = text.split("*NODE", 1)[1].split("*", 1)[0]
    rows = np.array([[float(v) for v in ln.split(",")] for ln in block.strip().splitlines()])
    return rows[:, 0].astype(int), rows[:, 1], rows[:, 2]


def to_plane_strain(mesh_inp: Path) -> int:
    text = Path(mesh_inp).read_text(encoding="utf-8")
    n = text.count("type=CPS6")
    if n == 0:
        raise RuntimeError("mesh has no CPS6 elements (expected Gmsh's 6-node triangles)")
    Path(mesh_inp).write_text(text.replace("type=CPS6", "type=CPE6"), encoding="utf-8")
    return n


def write_deck(mesh_inp: Path, deck: Path, *, a: float, W: float, H: float, sigma: float, E: float,
               nu: float) -> dict:
    ids, x, y = read_mesh_nodes(mesh_inp)
    on0 = np.isclose(y, 0.0, atol=TOL)
    lig = ids[on0 & (x >= a - TOL)]
    crack = ids[on0 & (x < a - TOL)]
    corner = ids[np.isclose(x, W, atol=TOL) & on0]
    top = np.isclose(y, H, atol=TOL)
    order = np.argsort(x[top])
    tids, tx = ids[top][order], x[top][order]
    if len(tids) < 3 or len(tids) % 2 == 0 or len(corner) != 1:
        raise RuntimeError(f"top edge {len(tids)} nodes (need odd), corner nodes {len(corner)}")
    load = np.zeros(len(tids))
    for k in range(0, len(tids) - 2, 2):  # consistent forces on each quadratic edge: 1/6, 4/6, 1/6
        seg = tx[k + 2] - tx[k]
        load[k] += sigma * seg / 6
        load[k + 1] += sigma * seg * 4 / 6
        load[k + 2] += sigma * seg / 6

    def nset(name, arr):
        return f"*NSET, NSET={name}\n" + "\n".join(str(int(i)) for i in arr) + "\n"

    deck.write_text(
        f"*INCLUDE, INPUT={Path(mesh_inp).name}\n" + nset("LIG", lig) + nset("CRACK", crack)
        + nset("CORNER", corner) + nset("TOP", tids)
        + f"*MATERIAL, NAME=STEEL\n*ELASTIC\n{E!r}, {nu!r}\n"
        + "*SOLID SECTION, ELSET=PLATE, MATERIAL=STEEL\n1.0\n"
        + "*BOUNDARY\nLIG, 2, 2, 0.\nCORNER, 1, 1, 0.\n"
        + "*STEP\n*STATIC\n*CLOAD\n" + "".join(f"{int(i)}, 2, {float(f)!r}\n" for i, f in zip(tids, load))
        + "*NODE PRINT, NSET=TOP\nU\n*NODE PRINT, NSET=CRACK\nU\n*NODE PRINT, NSET=LIG, TOTALS=ONLY\nRF\n*END STEP\n",
        encoding="utf-8")
    return {"nodes": int(len(ids)), "top_nodes": int(len(tids)), "crack_nodes": int(len(crack)),
            "ligament_nodes": int(len(lig)), "applied_load_N_per_mm": float(load.sum()),
            "top_ids": tids.tolist(), "top_loads": load.tolist(), "crack_ids": crack.tolist(),
            "node_x": dict(zip(ids.tolist(), x.tolist()))}


def read_node_print(dat: Path) -> tuple[dict, dict, float]:
    """(top displacements {id: (ux, uy)}, crack-face displacements, total ligament reaction in y) from job.dat."""
    lines = Path(dat).read_text(encoding="utf-8", errors="replace").splitlines()
    blocks, cur = [], None
    for ln in lines:
        s = ln.strip()
        if s.startswith("displacements (vx,vy,vz) for set"):
            cur = {"set": s.split("set")[1].split()[0], "rows": {}}
            blocks.append(cur)
            continue
        if s.startswith("total force (fx,fy,fz) for set"):
            cur = {"set": "RF_" + s.split("set")[1].split()[0], "rows": {}}
            blocks.append(cur)
            continue
        parts = s.split()
        if cur is not None and parts:
            try:
                vals = [float(v) for v in parts]
            except ValueError:
                cur = None
                continue
            if cur["set"].startswith("RF_"):
                cur["total"] = vals
            else:
                cur["rows"][int(vals[0])] = tuple(vals[1:4])
    by = {b["set"]: b for b in blocks}
    rf = by.get("RF_LIG", {}).get("total")
    return by["TOP"]["rows"], by["CRACK"]["rows"], float(rf[1]) if rf else float("nan")


def half_energy(top_disp: dict, info: dict) -> float:
    """U_half = 1/2 sum(f uy) over the loaded edge (N mm per mm of thickness)."""
    return 0.5 * float(sum(f * top_disp[i][1] for i, f in zip(info["top_ids"], info["top_loads"])))


def k_from_opening(crack_disp: dict, info: dict, *, a: float, E: float, nu: float, r_min: float,
                   r_max: float) -> tuple[float, int]:
    """Plane-strain K (N/mm^1.5) from the crack-face opening: K_app(r) = uy E / (4 (1 - nu^2)) sqrt(2 pi / r),
    fitted linearly in r over r_min <= r <= r_max and extrapolated to r = 0. Returns (K, points used)."""
    r, k = [], []
    for nid, (ux, uy, uz) in crack_disp.items():
        ri = a - info["node_x"][nid]
        if r_min <= ri <= r_max:
            r.append(ri)
            k.append(uy * E / (4 * (1 - nu ** 2)) * np.sqrt(2 * np.pi / ri))
    if len(r) < 3:
        return float("nan"), len(r)
    c = np.polyfit(np.array(r), np.array(k), 1)
    return float(c[1]), len(r)


def tada_F(alpha: float) -> float:
    """Tada's edge crack in a finite-width strip under uniform tension, 0.5 % for a/W <= 0.6."""
    return 1.12 - 0.231 * alpha + 10.55 * alpha ** 2 - 21.72 * alpha ** 3 + 30.39 * alpha ** 4

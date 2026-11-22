"""Stator slot-pitch section, steady 2D heat conduction in CalculiX (study 7 thermal network check).

Half a slot pitch by symmetry: from the slot axis (angle 0, the +x axis) to the tooth centreline (angle pi / Zs), from
the bore to the stator OD. Four regions, each with uniform heat generation and its own conductivity:
  WIND   the winding inside the liner (homogenised: impregnant + copper strands), from the slot shoulder down
  LINER  the slot liner along the slot sides and the round end
  TEETH  iron below the slot-bottom radius r_sb (tooth, tooth tip)
  YOKE   iron from r_sb to the OD
The slot opening and the wedge space above the shoulder are left out (adiabatic edges), as are the symmetry lines.
Boundary conditions: film on the OD (the network's series interface + housing + jacket resistance as one h on the OD
area, sink the coolant) and on the bore (the air-gap h, sink the rotor surface temperature).

Geometry from the network's geometry() dict (SI), the same numbers the network uses. Gmsh (built-in kernel) meshes
6-node triangles; CalculiX expands them to one layer of wedges of unit thickness (per metre of stack). Body flux
(*DFLUX BF) per region; film (*FILM) on the triangle edges: edge labels F1 = nodes 1-2, F2 = 2-3, F3 = 3-1.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

REGIONS = ("WIND", "LINER", "TEETH", "YOKE")


def points(g: dict) -> dict:
    a = math.pi / g["Zs"]
    rb, rso, rsb = g["r_bore"], g["r_so"], g["r_sb"]
    x1, xc, R1, t = g["x1"], g["xc"], g["R1"], g["t_l"]
    w0h = g["slot_opening"] / 2
    return {
        "O": (0.0, 0.0), "C": (xc, 0.0),
        "A1": (math.sqrt(rb ** 2 - w0h ** 2), w0h), "A2": (x1, w0h), "A3": (x1, g["w1"] / 2), "A4": (xc, R1),
        "A5": (xc + R1, 0.0),
        "B0": (x1, 0.0), "B3": (x1, g["w1"] / 2 - t), "B4": (xc, R1 - t), "B5": (xc + R1 - t, 0.0),
        "Y0": (rso, 0.0), "TS": (rsb * math.cos(a), rsb * math.sin(a)), "TO": (rso * math.cos(a), rso * math.sin(a)),
        "TB": (rb * math.cos(a), rb * math.sin(a)),
    }


def write_geo(g: dict, h: float, path: Path) -> None:
    """h: element size in the winding (m); liner h / 1.6, iron 3 h."""
    P = points(g)
    size = {k: h for k in P}
    for k in ("A3", "A4", "A5", "B3", "B4", "B5"):
        size[k] = h / 1.6
    for k in ("Y0", "TO", "TB", "TS", "A1", "A2"):
        size[k] = 3 * h
    names = list(P)
    pid = {k: i + 1 for i, k in enumerate(names)}
    out = [f"Point({pid[k]}) = {{{x:.12e}, {y:.12e}, 0, {size[k]:.6e}}};" for k, (x, y) in P.items()]
    lines = {}

    def seg(a, b):
        lines[(a, b)] = len(lines) + 1
        out.append(f"Line({lines[(a, b)]}) = {{{pid[a]}, {pid[b]}}};")

    def arc(a, c, b):
        lines[(a, b)] = len(lines) + 1
        out.append(f"Circle({lines[(a, b)]}) = {{{pid[a]}, {pid[c]}, {pid[b]}}};")

    def ref(a, b):
        return lines[(a, b)] if (a, b) in lines else -lines[(b, a)]

    seg("B0", "B3"); seg("B3", "B4"); arc("B4", "C", "B5"); seg("B5", "B0")                    # winding
    seg("B3", "A3"); seg("A3", "A4"); arc("A4", "C", "A5"); seg("A5", "B5")                    # liner (+ B3-B4, B4-B5)
    seg("A1", "A2"); seg("A2", "A3"); arc("A5", "O", "TS"); seg("TS", "TB"); arc("TB", "O", "A1")  # teeth
    seg("A5", "Y0"); arc("Y0", "O", "TO"); seg("TO", "TS")                                   # yoke
    loops = {
        "WIND": [("B0", "B3"), ("B3", "B4"), ("B4", "B5"), ("B5", "B0")],
        "LINER": [("B3", "A3"), ("A3", "A4"), ("A4", "A5"), ("A5", "B5"), ("B5", "B4"), ("B4", "B3")],
        "TEETH": [("A1", "A2"), ("A2", "A3"), ("A3", "A4"), ("A4", "A5"), ("A5", "TS"), ("TS", "TB"), ("TB", "A1")],
        "YOKE": [("A5", "Y0"), ("Y0", "TO"), ("TO", "TS"), ("TS", "A5")],
    }
    for i, (name, lp) in enumerate(loops.items(), start=1):
        out.append(f"Curve Loop({i}) = {{{', '.join(str(ref(a, b)) for a, b in lp)}}};")
        out.append(f"Plane Surface({i}) = {{{i}}};")
        out.append(f'Physical Surface("{name}") = {{{i}}};')
    out.append("Mesh.MeshSizeExtendFromBoundary = 1; Mesh.MeshSizeFromPoints = 1; Mesh.MeshSizeFromCurvature = 0;")
    out.append("Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 0;")
    Path(path).write_text("\n".join(out) + "\n", encoding="utf-8")


def read_mesh(mesh_inp: Path) -> tuple[np.ndarray, np.ndarray, dict]:
    """(node ids, xy (n, 2), {region: CPS6 connectivity (m, 7): element id + 6 nodes})."""
    text = Path(mesh_inp).read_text(encoding="utf-8")
    nb = text.split("*NODE", 1)[1].split("*", 1)[0]
    rows = np.array([[float(v) for v in ln.split(",")] for ln in nb.strip().splitlines()])
    conn = {}
    for blk in text.split("*ELEMENT")[1:]:
        head, body = blk.split("\n", 1)
        if "CPS6" not in head.upper():
            continue
        for ln in body.split("*", 1)[0].strip().splitlines():
            row = [int(v) for v in ln.split(",") if v.strip()]
            conn[row[0]] = row
    # Gmsh writes the elements per geometric surface and each physical group as an *ELSET of element ids
    regions = {}
    for blk in text.split("*ELSET")[1:]:
        head, body = blk.split("\n", 1)
        name = head.upper().split("ELSET=")[1].strip().strip(",")
        if name in REGIONS:
            ids_ = [int(v) for v in body.split("*", 1)[0].replace("\n", ",").split(",") if v.strip()]
            regions[name] = np.array([conn[e] for e in ids_])
    if set(regions) != set(REGIONS) or sum(len(v) for v in regions.values()) != len(conn):
        raise ValueError(f"mesh regions incomplete: {sorted(regions)}, {len(conn)} elements")
    ids, xy = rows[:, 0].astype(int), rows[:, 1:3]
    # CalculiX needs counter-clockwise triangles (+z normal; a clockwise one has a negative Jacobian). Gmsh orients
    # each surface by its curve loop, so flip the clockwise ones: corners 1 2 3 -> 1 3 2, midsides 4 5 6 -> 6 5 4.
    pos = {int(n): i for i, n in enumerate(ids)}
    for name, c in regions.items():
        for row in c:
            (x1, y1), (x2, y2), (x3, y3) = (xy[pos[int(n)]] for n in row[1:4])
            if (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1) < 0:
                row[1:7] = row[[1, 3, 2, 6, 5, 4]]
    return ids, xy, regions


EDGES = ((0, 1, 3), (1, 2, 4), (2, 0, 5))  # corner, corner, midside (0-based within the 6 nodes); label F1..F3


def boundary_edges(ids, xy, regions, radius: float, tol: float = 1e-7) -> list[tuple[int, int, tuple]]:
    """(element id, edge label 1-3, (n_a, n_b, n_mid)) for every element edge whose three nodes lie on `radius`."""
    r = dict(zip(ids.tolist(), np.hypot(xy[:, 0], xy[:, 1]).tolist()))
    out = []
    for conn in regions.values():
        for row in conn:
            e, nodes = int(row[0]), [int(v) for v in row[1:7]]
            for lab, (i, j, m) in enumerate(EDGES, start=1):
                if all(abs(r[nodes[k]] - radius) < tol * max(radius, 1e-9) * 1e3 for k in (i, j, m)):
                    out.append((e, lab, (nodes[i], nodes[j], nodes[m])))
    return out


def tri_area(xy6: np.ndarray) -> float:
    (x1, y1), (x2, y2), (x3, y3) = xy6[:3]
    return 0.5 * abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))


def write_deck(g: dict, bc: dict, mesh_inp: Path, deck: Path) -> dict:
    """bc: k_<region> (W/m K), q_<region> (W/m^3), h_od, t_od, h_bore, t_bore. Returns mesh facts."""
    ids, xy, regions = read_mesh(mesh_inp)
    od = boundary_edges(ids, xy, regions, g["r_so"])
    bore = boundary_edges(ids, xy, regions, g["r_bore"])
    out = ["*HEADING", "Stator slot-pitch section, steady conduction", "*NODE, NSET=NALL"]
    out += [f"{int(n)}, {x:.12e}, {y:.12e}, 0.0" for n, (x, y) in zip(ids, xy)]
    for name, conn in regions.items():
        out.append(f"*ELEMENT, TYPE=CPS6, ELSET={name}")
        out += [", ".join(str(int(v)) for v in row) for row in conn]
    for name in REGIONS:
        out += [f"*MATERIAL, NAME=M{name}", "*CONDUCTIVITY", f"{float(bc['k_' + name]):.12e}",
                f"*SOLID SECTION, ELSET={name}, MATERIAL=M{name}", "1.0"]
    t0 = float(bc["t_od"])
    out += ["*INITIAL CONDITIONS, TYPE=TEMPERATURE", f"NALL, {t0:.12e}",
            "*STEP", "*HEAT TRANSFER, STEADY STATE", "1., 1.", "*DFLUX"]
    out += [f"{name}, BF, {float(bc['q_' + name]):.12e}" for name in REGIONS]
    out.append("*FILM")
    out += [f"{e}, F{lab}, {float(bc['t_od']):.12e}, {float(bc['h_od']):.12e}" for e, lab, _ in od]
    out += [f"{e}, F{lab}, {float(bc['t_bore']):.12e}, {float(bc['h_bore']):.12e}" for e, lab, _ in bore]
    out += ["*NODE FILE", "NT", "*END STEP", ""]
    Path(deck).write_text("\n".join(out), encoding="utf-8")
    return {"nodes": len(ids), "elements": int(sum(len(c) for c in regions.values())), "od_edges": len(od),
            "bore_edges": len(bore)}


def results(g: dict, bc: dict, mesh_inp: Path, temps: dict) -> dict:
    """Region means (exact for the quadratic field on straight 6-node triangles: the mean of the midside values),
    region peaks (nodal), areas, generation and the film heat out (Simpson along each quadratic edge)."""
    ids, xy, regions = read_mesh(mesh_inp)
    pos = {int(n): i for i, n in enumerate(ids)}
    out = {}
    q_gen = 0.0
    for name, conn in regions.items():
        A, TA, tmax = 0.0, 0.0, -1e9
        for row in conn:
            nodes = [int(v) for v in row[1:7]]
            a = tri_area(np.array([xy[pos[n]] for n in nodes]))
            A += a
            TA += a * np.mean([temps[n] for n in nodes[3:]])
            tmax = max(tmax, max(temps[n] for n in nodes))
        out[f"{name}_area_m2"], out[f"{name}_mean_C"], out[f"{name}_max_C"] = A, TA / A, tmax
        q_gen += float(bc["q_" + name]) * A
    q_film = 0.0
    for radius, h, ts in ((g["r_so"], bc["h_od"], bc["t_od"]), (g["r_bore"], bc["h_bore"], bc["t_bore"])):
        for _, _, (na, nb, nm) in boundary_edges(ids, xy, regions, radius):
            length = math.dist(xy[pos[na]], xy[pos[nm]]) + math.dist(xy[pos[nm]], xy[pos[nb]])
            q_film += float(h) * length * (temps[na] + 4 * temps[nm] + temps[nb]) / 6 - float(h) * length * float(ts)
    out["q_generated_W_per_m"] = q_gen
    out["q_film_W_per_m"] = q_film
    out["balance_rel"] = abs(q_gen - q_film) / abs(q_gen)
    return out

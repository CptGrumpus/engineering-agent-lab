"""Single-bay portal frame with fixed bases and rigid knees (steel frame study): CalculiX B32 beams, first or second order.

Geometry (mm): columns from (0, 0) and (B, 0) up to height H, the beam between the column tops; plane x-y, gravity -y.
Members: quadratic beams (B32), `n_per_member` elements each (P-delta inside a member needs several); each section an
equivalent rectangle with the member's area A and in-plane moment of inertia I (h = sqrt(12 I / A), b = A / h): exact
for in-plane axial and bending stiffness; out of plane the frame is held (u_z and the two out-of-plane rotations fixed
at every node: braced out of plane, an assumption of the case).
Loads: a uniform load w on the beam (consistent nodal loads of the quadratic element: 1/6, 2/3, 1/6 of w L_e), a lateral
load at the beam level (left knee), and optional notional loads N = notional_fraction x (the gravity load on the level),
added to the lateral load (the Direct Analysis Method's minimum lateral load). Stiffness reduction: E x
stiffness_factor for every member (0.8 tau_b in the Direct Analysis Method; 1 for a plain analysis).
Analysis: `second_order` 1 = NLGEOM (P-Delta and P-delta), in increments; 0 = linear.
Outputs (OUTPUT=2D, on the beam nodes): displacements, section forces (component 3 = axial force, component 5 = the
in-plane bending moment; nodal values are extrapolated, so members are subdivided); base reactions (forces).

Must not import from validation/.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np

PARAMS = ("height_mm", "span_mm", "column_area_mm2", "column_I_mm4", "beam_area_mm2", "beam_I_mm4", "youngs_modulus_MPa",
          "stiffness_factor", "beam_udl_N_per_mm", "lateral_load_N", "notional_fraction", "n_per_member", "second_order")


def build(p: dict) -> dict:
    """Nodes {id: (x, y)}, elements [(id, (n1, nmid, n2), member)], member node chains, special nodes."""
    H, B, n = float(p["height_mm"]), float(p["span_mm"]), int(p["n_per_member"])
    nodes, elems, chains = {}, [], {}

    def add(x, y):
        for k, (a, b) in nodes.items():
            if abs(a - x) < 1e-9 and abs(b - y) < 1e-9:
                return k
        k = len(nodes) + 1
        nodes[k] = (x, y)
        return k

    def chain(name, x0, y0, x1, y1):
        ids = [add(x0 + (x1 - x0) * i / (2 * n), y0 + (y1 - y0) * i / (2 * n)) for i in range(2 * n + 1)]
        chains[name] = ids
        for e in range(n):
            elems.append((len(elems) + 1, (ids[2 * e], ids[2 * e + 1], ids[2 * e + 2]), name))

    chain("COLL", 0.0, 0.0, 0.0, H)
    chain("BEAM", 0.0, H, B, H)
    chain("COLR", B, H, B, 0.0)
    return {"nodes": nodes, "elems": elems, "chains": chains,
            "base_left": chains["COLL"][0], "base_right": chains["COLR"][-1],
            "knee_left": chains["COLL"][-1], "knee_right": chains["COLR"][0]}


def rect(A: float, I: float) -> tuple[float, float]:
    """(b, h) of the rectangle with area A and moment of inertia I about its b axis."""
    h = math.sqrt(12 * I / A)
    return A / h, h


def write_deck(p: dict, deck: Path) -> dict:
    g = build(p)
    nodes, elems, chains = g["nodes"], g["elems"], g["chains"]
    w = float(p["beam_udl_N_per_mm"])
    B = float(p["span_mm"])
    E = float(p["youngs_modulus_MPa"]) * float(p["stiffness_factor"])
    lateral = float(p["lateral_load_N"]) + float(p["notional_fraction"]) * w * B
    F: dict[int, np.ndarray] = {k: np.zeros(2) for k in nodes}
    for _, (a, m, b), name in elems:
        if name == "BEAM":
            Le = abs(nodes[b][0] - nodes[a][0])
            for nd, c in ((a, 1 / 6), (m, 2 / 3), (b, 1 / 6)):
                F[nd][1] -= c * w * Le
    F[g["knee_left"]][0] += lateral
    bc, hc = rect(float(p["column_area_mm2"]), float(p["column_I_mm4"]))
    bb, hb = rect(float(p["beam_area_mm2"]), float(p["beam_I_mm4"]))

    def nset(name, arr):
        arr = [int(v) for v in arr]
        rows = [", ".join(str(v) for v in arr[i:i + 12]) for i in range(0, len(arr), 12)]
        return f"*NSET, NSET={name}\n" + "\n".join(rows) + "\n"

    L = ["*NODE"] + [f"{k}, {float(x)!r}, {float(y)!r}, 0." for k, (x, y) in sorted(nodes.items())]
    for name in ("COLL", "BEAM", "COLR"):
        L.append(f"*ELEMENT, TYPE=B32, ELSET={name}")
        L += [f"{e}, {a}, {m}, {b}" for e, (a, m, b), nm in elems if nm == name]
    L.append("*ELSET, ELSET=COLS\nCOLL, COLR")
    second = int(p["second_order"])
    s = (nset("NALL", sorted(nodes)) + nset("BASES", [g["base_left"], g["base_right"]])
         + f"*MATERIAL, NAME=STEEL\n*ELASTIC\n{E!r}, 0.3\n"
         + f"*BEAM SECTION, ELSET=COLS, MATERIAL=STEEL, SECTION=RECT\n{bc!r}, {hc!r}\n0., 0., 1.\n"
         + f"*BEAM SECTION, ELSET=BEAM, MATERIAL=STEEL, SECTION=RECT\n{bb!r}, {hb!r}\n0., 0., 1.\n"
         + "*BOUNDARY\nNALL, 3, 5, 0.\nBASES, 1, 6, 0.\n"
         + ("*STEP, NLGEOM, INC=1000\n*STATIC\n0.05, 1.0, 1e-6, 0.1\n" if second else "*STEP\n*STATIC\n")
         + "*CLOAD\n" + "".join(f"{k}, {d + 1}, {float(v)!r}\n" for k, f in sorted(F.items())
                                for d, v in enumerate(f) if v != 0.0)
         + "*NODE FILE, OUTPUT=2D\nU\n*EL FILE, SECTION FORCES, OUTPUT=2D\nS\n*NODE PRINT, NSET=BASES\nRF\n*END STEP\n")
    deck.write_text("\n".join(L) + "\n" + s, encoding="utf-8")
    Fa = np.array(list(F.values()))
    return {"nodes": len(nodes), "elements": len(elems), "applied_Fx_N": float(Fa[:, 0].sum()),
            "applied_Fy_N": float(Fa[:, 1].sum()), "lateral_total_N": lateral, "E_used_MPa": E,
            "column_rect_mm": [bc, hc], "beam_rect_mm": [bb, hb], **{k: g[k] for k in
            ("base_left", "base_right", "knee_left", "knee_right")}, "chains": chains}


_RF = re.compile(r"forces \(fx,fy,fz\) for set BASES and time\s+([-+0-9.eE]+)")


def read_base_reactions(dat: Path) -> dict:
    """{node: (fx, fy)} from the last RF print of set BASES."""
    lines = Path(dat).read_text(encoding="latin-1").splitlines()
    start = max(i for i, ln in enumerate(lines) if _RF.search(ln))
    out = {}
    for ln in lines[start + 1:]:
        v = ln.split()
        if not v:
            if out:
                break
            continue
        out[int(v[0])] = (float(v[1]), float(v[2]))
    return out

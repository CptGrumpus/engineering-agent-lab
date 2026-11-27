"""Study 27's sealed enclosure as a detailed assembly in CadQuery: the extruded aluminium housing with its corner
bosses, two end caps on screws, a cable gland, the board on four standoffs, the regulator U1 and the bulk capacitor C1.

Axes (mm): the section in x (width, 150) and y (height, 60), the box's depth along z from 0 to 200; the board at
mid-height (y from -1 to 1), centred in x.

From the study: the section (150 x 60 mm, outer), the depth (200 mm), the shell (2 mm aluminium: the redesign's
shell_thickness_mm), the board (100 mm long, 2 mm thick, at mid-height), U1 (20 mm long, at the board's middle), C1
(5-15 mm from the board's left end). [synthetic]: the board's extent along the depth (180 mm), U1's package (20 x 20
x 4 mm on the board's top), C1's can (10 mm diameter, 16 mm tall), the corner bosses (8 x 8 mm, a 2.5 mm tap drill
along them), the end caps (3 mm), the screws (M3: 3 mm shank, 5.5 x 3 mm head; 10 mm into the bosses, 8 mm into the
standoffs), the standoffs (6 mm diameter, from the floor to the board), the gland (an M16 body simplified: 22 mm
across, 14 mm proud, 16 mm through the cap). In the 2D model U1 is the board's own middle 20 mm; here it is drawn as a
package. The threads are not drawn: each screw's shank overlaps its tap drill by the thread engagement, measured.
"""

from __future__ import annotations

import math
from pathlib import Path

DESIGNS = {
    "as_drawn": {"W": 150.0, "H": 60.0, "D": 200.0, "t": 2.0, "boss": 8.0, "tap_d": 2.5, "cap_t": 3.0,
                 "board_l": 100.0, "board_t": 2.0, "board_d": 180.0, "u1_l": 20.0, "u1_w": 20.0, "u1_h": 4.0,
                 "c1_d": 10.0, "c1_h": 16.0, "c1_x_from_left": 10.0, "screw_d": 3.0, "head_d": 5.5, "head_h": 3.0,
                 "cap_screw_l": 13.0, "standoff_d": 6.0, "board_hole_d": 3.2, "board_screw_l": 10.0,
                 "standoff_inset": 5.0, "gland_od": 22.0, "gland_proud": 14.0, "gland_hole": 16.0},
}


def boss_xy(s: dict):
    c = (s["W"] / 2 - s["t"] - s["boss"] / 2, s["H"] / 2 - s["t"] - s["boss"] / 2)
    return [(sx * c[0], sy * c[1]) for sx in (1, -1) for sy in (1, -1)]


def standoff_xz(s: dict):
    x = s["board_l"] / 2 - s["standoff_inset"]
    z0, z1 = (s["D"] - s["board_d"]) / 2 + s["standoff_inset"], (s["D"] + s["board_d"]) / 2 - s["standoff_inset"]
    return [(sx * x, z) for sx in (1, -1) for z in (z0, z1)]


def build(design: str = "as_drawn") -> dict:
    import cadquery as cq

    s = DESIGNS[design]
    W, H, D, t, b = s["W"], s["H"], s["D"], s["t"], s["boss"]
    prof = cq.Workplane("XY").rect(W, H).extrude(D).cut(cq.Workplane("XY").rect(W - 2 * t, H - 2 * t).extrude(D + 2)
                                                        .translate((0, 0, -1)))
    for x, y in boss_xy(s):
        prof = prof.union(cq.Workplane("XY").center(x, y).rect(b, b).extrude(D))
    for x, y in boss_xy(s):
        prof = prof.cut(cq.Workplane("XY").center(x, y).circle(s["tap_d"] / 2).extrude(D + 2).translate((0, 0, -1)))
    parts = {"housing": prof}
    for name, z0, gland in (("cap_front", D, True), ("cap_back", -s["cap_t"], False)):
        cap = cq.Workplane("XY").rect(W, H).extrude(s["cap_t"]).translate((0, 0, z0))
        for x, y in boss_xy(s):
            cap = cap.cut(cq.Workplane("XY").center(x, y).circle(s["screw_d"] / 2 + 0.2).extrude(s["cap_t"] + 2)
                          .translate((0, 0, z0 - 1)))
        if gland:
            cap = cap.cut(cq.Workplane("XY").circle(s["gland_hole"] / 2).extrude(s["cap_t"] + 2).translate((0, 0, z0 - 1)))
        parts[name] = cap
    zg = D + s["cap_t"]
    parts["gland"] = cq.Workplane("XY").circle(s["gland_od"] / 2).extrude(s["gland_proud"]).translate((0, 0, zg)).union(
        cq.Workplane("XY").circle(s["gland_hole"] / 2).extrude(s["cap_t"]).translate((0, 0, D)))
    for k, (x, y) in enumerate(boss_xy(s)):
        for name, zc, sign in ((f"cap_screw_front_{k}", D + s["cap_t"], 1), (f"cap_screw_back_{k}", -s["cap_t"], -1)):
            head = cq.Workplane("XY").center(x, y).circle(s["head_d"] / 2).extrude(s["head_h"])
            shank = cq.Workplane("XY").center(x, y).circle(s["screw_d"] / 2).extrude(s["cap_screw_l"])
            if sign > 0:
                sc = head.translate((0, 0, zc)).union(shank.translate((0, 0, zc - s["cap_screw_l"])))
            else:
                sc = head.translate((0, 0, zc - s["head_h"])).union(shank.translate((0, 0, zc)))
            parts[name] = sc
    yb0, yb1 = -s["board_t"] / 2, s["board_t"] / 2
    zb0 = (D - s["board_d"]) / 2
    board = cq.Workplane("XY").box(s["board_l"], s["board_t"], s["board_d"], centered=(True, False, False)) \
        .translate((0, yb0, zb0))
    for x, z in standoff_xz(s):
        board = board.cut(cq.Workplane("XZ").center(x, z).circle(s["board_hole_d"] / 2).extrude(-(s["board_t"] + 2))
                          .translate((0, yb0 - 1, 0)))
    parts["board"] = board
    parts["U1"] = cq.Workplane("XY").box(s["u1_l"], s["u1_h"], s["u1_w"], centered=(True, False, True)) \
        .translate((0, yb1, D / 2))
    xc1 = -s["board_l"] / 2 + s["c1_x_from_left"]
    parts["C1"] = cq.Workplane("XZ").center(xc1, D / 2 + 40).circle(s["c1_d"] / 2).extrude(-s["c1_h"]).translate((0, yb1, 0))
    y_floor = -H / 2 + t
    for k, (x, z) in enumerate(standoff_xz(s)):
        so = cq.Workplane("XZ").center(x, z).circle(s["standoff_d"] / 2).extrude(-(yb0 - y_floor)).translate((0, y_floor, 0))
        so = so.cut(cq.Workplane("XZ").center(x, z).circle(s["tap_d"] / 2).extrude(-(yb0 - y_floor) - 2)
                    .translate((0, y_floor - 1, 0)))
        parts[f"standoff_{k}"] = so
        head = cq.Workplane("XZ").center(x, z).circle(s["head_d"] / 2).extrude(-s["head_h"]).translate((0, yb1, 0))
        shank = cq.Workplane("XZ").center(x, z).circle(s["screw_d"] / 2).extrude(-s["board_screw_l"]) \
            .translate((0, yb1 - s["board_screw_l"], 0))
        parts[f"board_screw_{k}"] = head.union(shank)
    for name, w in parts.items():
        sol = w.solids().vals()
        if len(sol) != 1 or not sol[0].isValid():
            raise RuntimeError(f"part {name}: {len(sol)} solids or invalid")
    return parts


def hand_volumes(design: str = "as_drawn") -> dict:
    s = DESIGNS[design]
    a = lambda d: math.pi * d * d / 4  # noqa: E731
    W, H, D, t, b = s["W"], s["H"], s["D"], s["t"], s["boss"]
    out = {"housing": ((W * H - (W - 2 * t) * (H - 2 * t)) + 4 * b * b - 4 * a(s["tap_d"])) * D}
    capA = W * H - 4 * a(s["screw_d"] + 0.4)
    out["cap_front"] = (capA - a(s["gland_hole"])) * s["cap_t"]
    out["cap_back"] = capA * s["cap_t"]
    out["gland"] = a(s["gland_od"]) * s["gland_proud"] + a(s["gland_hole"]) * s["cap_t"]
    screw = a(s["head_d"]) * s["head_h"] + a(s["screw_d"]) * s["cap_screw_l"]
    for k in range(4):
        out[f"cap_screw_front_{k}"] = screw
        out[f"cap_screw_back_{k}"] = screw
    out["board"] = s["board_l"] * s["board_t"] * s["board_d"] - 4 * a(s["board_hole_d"]) * s["board_t"]
    out["U1"] = s["u1_l"] * s["u1_w"] * s["u1_h"]
    out["C1"] = a(s["c1_d"]) * s["c1_h"]
    h_so = (-s["board_t"] / 2) - (-s["H"] / 2 + s["t"])
    for k in range(4):
        out[f"standoff_{k}"] = (a(s["standoff_d"]) - a(s["tap_d"])) * h_so
        out[f"board_screw_{k}"] = a(s["head_d"]) * s["head_h"] + a(s["screw_d"]) * s["board_screw_l"]
    return out


def thread_overlaps(design: str = "as_drawn") -> dict:
    """The intended overlaps: each screw's shank in its tap drill over the engaged length."""
    s = DESIGNS[design]
    ann = math.pi / 4 * (s["screw_d"] ** 2 - s["tap_d"] ** 2)
    return {"cap": ann * (s["cap_screw_l"] - s["cap_t"]), "board": ann * (s["board_screw_l"] - s["board_t"])}


def export(design: str, step: Path) -> dict:
    import cadquery as cq

    parts = build(design)
    col = {"housing": (0.62, 0.66, 0.70), "board": (0.10, 0.40, 0.20), "U1": (0.12, 0.12, 0.12),
           "C1": (0.15, 0.25, 0.55), "gland": (0.10, 0.10, 0.10)}
    asm = cq.Assembly(name=f"enclosure_{design}")
    for name, w in parts.items():
        c = col.get(name, (0.68, 0.71, 0.74) if name.startswith("cap_") and "screw" not in name else (0.35, 0.35, 0.37))
        asm.add(w, name=name, color=cq.Color(*c))
    asm.export(str(step), exportType="STEP")
    return {k: float(w.val().Volume()) for k, w in parts.items()}

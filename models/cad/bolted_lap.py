"""Study 16's bolted joint as a detailed assembly in CadQuery: two lapped steel strips, an M8 hex bolt and its nut.

Axes (mm): the bolt's axis along z, the plates' interface at z = 0 (the top strip above, the bottom strip below), the
side load along x.

From the study: the plates (6 mm each, steel), the 9 mm hole, the M8 bolt with a 12 mm grip (no washers: the study's
clamp length is the two plates), the head's bearing face (13 mm across flats). [synthetic]: the strips (40 mm wide,
80 mm long, overlapping 40 mm), the bolt's length (25 mm: the grip, the nut's 6.8 mm and 6.2 mm protruding, about
five threads), the head (ISO 4017: 5.3 mm high) and nut (ISO 4032: 6.8 mm) as plain hex prisms. The thread form and
the chamfers are not drawn (the hand volumes stay exact); the nut's bore is drawn at the bolt's 8 mm, so bolt and nut
touch without overlap.
"""

from __future__ import annotations

import math
from pathlib import Path

DESIGNS = {
    "m8": {"t": 6.0, "hole_d": 9.0, "strip_w": 40.0, "strip_l": 80.0, "overlap": 40.0, "d": 8.0, "bolt_l": 25.0,
           "s": 13.0, "head_k": 5.3, "nut_m": 6.8},
}


def hex_area(s: float) -> float:
    return math.sqrt(3) / 2 * s * s


def build(design: str = "m8") -> dict:
    import cadquery as cq

    p = DESIGNS[design]
    t, L, w, ov = p["t"], p["strip_l"], p["strip_w"], p["overlap"]
    top = cq.Workplane("XY").box(L, w, t, centered=(False, True, False)).translate((-ov / 2, 0, 0))
    bot = cq.Workplane("XY").box(L, w, t, centered=(False, True, False)).translate((ov / 2 - L, 0, -t))
    hole = cq.Workplane("XY").circle(p["hole_d"] / 2).extrude(2 * t + 2).translate((0, 0, -t - 1))
    parts = {"plate_top": top.cut(hole), "plate_bottom": bot.cut(hole)}
    across_corners = 2 * p["s"] / math.sqrt(3)
    head = cq.Workplane("XY").polygon(6, across_corners).extrude(p["head_k"]).translate((0, 0, t))
    shank = cq.Workplane("XY").circle(p["d"] / 2).extrude(p["bolt_l"]).translate((0, 0, t - p["bolt_l"]))
    parts["bolt"] = head.union(shank)
    nut = cq.Workplane("XY").polygon(6, across_corners).circle(p["d"] / 2).extrude(p["nut_m"]) \
        .translate((0, 0, -t - p["nut_m"]))
    parts["nut"] = nut
    for name, wp in parts.items():
        sol = wp.solids().vals()
        if len(sol) != 1 or not sol[0].isValid():
            raise RuntimeError(f"part {name}: {len(sol)} solids or invalid")
    return parts


def hand_volumes(design: str = "m8") -> dict:
    p = DESIGNS[design]
    a = lambda d: math.pi * d * d / 4  # noqa: E731
    plate = p["strip_l"] * p["strip_w"] * p["t"] - a(p["hole_d"]) * p["t"]
    return {"plate_top": plate, "plate_bottom": plate,
            "bolt": hex_area(p["s"]) * p["head_k"] + a(p["d"]) * p["bolt_l"],
            "nut": (hex_area(p["s"]) - a(p["d"])) * p["nut_m"]}


def export(design: str, step: Path) -> dict:
    import cadquery as cq

    parts = build(design)
    col = {"plate_top": (0.62, 0.66, 0.70), "plate_bottom": (0.52, 0.56, 0.60), "bolt": (0.30, 0.30, 0.32),
           "nut": (0.36, 0.36, 0.38)}
    asm = cq.Assembly(name=f"bolted_lap_{design}")
    for name, wp in parts.items():
        asm.add(wp, name=name, color=cq.Color(*col[name]))
    asm.export(str(step), exportType="STEP")
    return {k: float(wp.val().Volume()) for k, wp in parts.items()}

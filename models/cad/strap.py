"""Studies 2, 3 and 14's strap as a deliverable part in CadQuery: the 6061-T6 strap with its cable hole and a pin hole
at each end.

Axes (mm): the strap along x (centred), across y, its thickness along z from 0 to t; the cable hole at the origin.

From the studies: 160 x 40 x 4 mm, the cable hole (16 mm: the recommendation; part 2 puts the limit at 16.3 mm),
smooth and unchamfered (as analysed: a chamfer would change the hole-edge stress). [synthetic]: the pin holes (10.5 mm,
M10 clearance, 15 mm from each end, 65 mm from the cable hole: the studies' uniform end traction stands in for them,
by St Venant far enough from the cable hole not to change its stress).
"""

from __future__ import annotations

import math
from pathlib import Path

DESIGNS = {
    "d16": {"L": 160.0, "W": 40.0, "t": 4.0, "hole_d": 16.0, "pin_d": 10.5, "pin_from_end": 15.0},
    "d14": {"L": 160.0, "W": 40.0, "t": 4.0, "hole_d": 14.0, "pin_d": 10.5, "pin_from_end": 15.0},
}


def build(design: str = "d16") -> dict:
    import cadquery as cq

    s = DESIGNS[design]
    body = cq.Workplane("XY").rect(s["L"], s["W"]).extrude(s["t"])
    body = body.cut(cq.Workplane("XY").circle(s["hole_d"] / 2).extrude(s["t"] + 2).translate((0, 0, -1)))
    for x in (-s["L"] / 2 + s["pin_from_end"], s["L"] / 2 - s["pin_from_end"]):
        body = body.cut(cq.Workplane("XY").center(x, 0).circle(s["pin_d"] / 2).extrude(s["t"] + 2).translate((0, 0, -1)))
    if len(body.solids().vals()) != 1 or not body.val().isValid():
        raise RuntimeError("strap is not one valid solid")
    return {"strap": body}


def hand_volumes(design: str = "d16") -> dict:
    s = DESIGNS[design]
    a = lambda d: math.pi * d * d / 4  # noqa: E731
    return {"strap": (s["L"] * s["W"] - a(s["hole_d"]) - 2 * a(s["pin_d"])) * s["t"]}


def export(design: str, step: Path) -> dict:
    import cadquery as cq

    parts = build(design)
    asm = cq.Assembly(name=f"strap_{design}")
    asm.add(parts["strap"], name="strap", color=cq.Color(0.70, 0.73, 0.76))
    asm.export(str(step), exportType="STEP")
    return {k: float(w.val().Volume()) for k, w in parts.items()}

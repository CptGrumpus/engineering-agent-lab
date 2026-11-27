"""Study 13's pinned strut as a deliverable part in CadQuery: the 25 x 16 mm 6061-T6 bar at the longest acceptable
length, with an eye at each end for its pin.

Axes (mm): the strut along x, the 25 mm width along y, the 16 mm thickness (the weak axis: the strut bows in z) along
z, the first pin's axis on the y axis.

The pins run across the width (along y), so the strut turns freely about y and bows through its thickness: pinned for
the weak-axis buckling the study's capacity rests on. (A first draft put the pins through the thickness, which would
have clamped the weak axis: caught by checking the drawing against the study's end condition.)

From the study: the section (25 x 16 mm), the length between the pins (587 mm: the longest that reaches 16 kN at first
yield with an L/1000 bow), ideal pins about the weak axis. [synthetic]: the eyes (round ends of radius 8 mm, the
half-thickness, in the x-z plane), the pin holes (8 mm: in double shear 159 MPa at 16 kN, bearing 80 MPa, the eyes'
ligaments 80 MPa against 6061-T6's 276). About the strong axis the pin clamps the strut over its 25 mm width; that
axis does not govern.
"""

from __future__ import annotations

import math
from pathlib import Path

DESIGNS = {"l587": {"L": 587.0, "b": 25.0, "h": 16.0, "pin_d": 8.0}}


def build(design: str = "l587") -> dict:
    import cadquery as cq

    s = DESIGNS[design]
    r = s["h"] / 2
    # the side profile in the x-z plane (a slot of the thickness), extruded across the width (y)
    body = cq.Workplane("XZ").center(s["L"] / 2, 0).slot2D(s["L"] + 2 * r, s["h"]).extrude(s["b"] / 2, both=True)
    for x in (0.0, s["L"]):
        body = body.cut(cq.Workplane("XZ").center(x, 0).circle(s["pin_d"] / 2).extrude(s["b"], both=True))
    if len(body.solids().vals()) != 1 or not body.val().isValid():
        raise RuntimeError("strut is not one valid solid")
    return {"strut": body}


def hand_volumes(design: str = "l587") -> dict:
    s = DESIGNS[design]
    r = s["h"] / 2
    return {"strut": (s["L"] * s["h"] + math.pi * r * r - 2 * math.pi * (s["pin_d"] / 2) ** 2) * s["b"]}


def export(design: str, step: Path) -> dict:
    import cadquery as cq

    parts = build(design)
    asm = cq.Assembly(name=f"strut_{design}")
    asm.add(parts["strut"], name="strut", color=cq.Color(0.70, 0.73, 0.76))
    asm.export(str(step), exportType="STEP")
    return {k: float(w.val().Volume()) for k, w in parts.items()}

"""Study 12's optimised clevis bracket as a deliverable part: the analysed solid (models/fea/clevis_bracket.build_solid,
the same function the optimiser and the mesh study used) at the chosen design, with the base's mounting pattern.

Axes (mm): as the study: the base centred on x and y, its bottom face on z = 0; the lug in the x-z plane, the pin hole
along y at height 70.

From the study: every analysed dimension (design D of clevis_confirm_r2b: lug 10.17 mm, gussets 9.07 x 36.36 mm,
3 mm fillets; 371.94 g with a plain base). [synthetic]: the base's mounting pattern, which the study treats as a rigid
fixed face: four 9 mm (M8 clearance) bolt holes at (+-40, +-40) and two 8 mm dowel holes at (+-40, 0), clear of the lug
(x within +-20) and the gussets (|y| < 30.5 at |x| < 4.6). They remove about 10 g from the base.
"""

from __future__ import annotations

import math
from pathlib import Path

DESIGNS = {
    "D": {"base_length_mm": 100.0, "base_width_mm": 100.0, "base_thickness_mm": 10.0, "lug_radius_mm": 20.0,
          "pin_height_mm": 70.0, "pin_diameter_mm": 16.0, "lug_thickness_mm": 10.169620442413608,
          "gusset_thickness_mm": 9.06916365232668, "gusset_height_mm": 36.36016009772356, "gusset_aspect": 0.7,
          "fillet_radius_mm": 3.0,
          "bolt_holes": [(40.0, 40.0), (-40.0, 40.0), (40.0, -40.0), (-40.0, -40.0)], "bolt_d": 9.0,
          "dowel_holes": [(40.0, 0.0), (-40.0, 0.0)], "dowel_d": 8.0},
}


def analysed_solid(design: str = "D"):
    from models.fea.clevis_bracket import build_solid

    return build_solid(DESIGNS[design])


def build(design: str = "D") -> dict:
    import cadquery as cq

    s = DESIGNS[design]
    body = analysed_solid(design)
    tb = s["base_thickness_mm"]
    for (x, y), d in [(xy, s["bolt_d"]) for xy in s["bolt_holes"]] + [(xy, s["dowel_d"]) for xy in s["dowel_holes"]]:
        body = body.cut(cq.Workplane("XY").center(x, y).circle(d / 2).extrude(tb + 2).translate((0, 0, -1)))
    if len(body.solids().vals()) != 1 or not body.val().isValid():
        raise RuntimeError("clevis is not one valid solid")
    return {"clevis": body}


def hole_volume(design: str = "D") -> float:
    s = DESIGNS[design]
    a = lambda d: math.pi * d * d / 4  # noqa: E731
    return (len(s["bolt_holes"]) * a(s["bolt_d"]) + len(s["dowel_holes"]) * a(s["dowel_d"])) * s["base_thickness_mm"]


def export(design: str, step: Path) -> dict:
    import cadquery as cq

    parts = build(design)
    asm = cq.Assembly(name=f"clevis_{design}")
    asm.add(parts["clevis"], name="clevis", color=cq.Color(0.70, 0.73, 0.76))
    asm.export(str(step), exportType="STEP")
    return {k: float(w.val().Volume()) for k, w in parts.items()}

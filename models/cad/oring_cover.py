"""Study 25's face seal as a detailed assembly in CadQuery: the pump flange with its O-ring groove, the O-ring (free,
uncompressed), the cover, four M6 socket-head cap screws and their washers.

Axes (mm): the seal's axis along z, the flange's sealing face at z = 0 (the flange below, the cover above), the bolts
at 45 deg as in part 2's cover model.

From the study: the groove (outer diameter 57.06, width 4.80, depth 2.79), the O-ring (3.53 mm section, 50 mm inside
diameter: nominal), the cover (96 mm across, 4 x M6 on a 76 mm circle, 6.6 mm holes, 12 mm washers; 6 mm thick, one
of part 2's thicknesses). [synthetic]: the flange (110 mm across, 15 mm thick, a 40 mm bore), the tapped holes (5 mm
drill, 12 mm deep: the thread not drawn), the screws (head 10 x 6 mm, shank 6 mm, 16 mm long under the head), the
washers (1.6 mm thick). The O-ring is drawn free: it stands 0.74 mm proud of the sealing face, so it overlaps the
cover by its squeeze, which the test measures instead of forbidding.
"""

from __future__ import annotations

import math
from pathlib import Path

DESIGNS = {
    "nominal": {"flange_d": 110.0, "flange_t": 15.0, "bore_d": 40.0, "groove_od": 57.06, "groove_w": 4.80,
                "groove_h": 2.79, "cs": 3.53, "ring_id": 50.0, "cover_d": 96.0, "cover_t": 6.0, "bolt_circle_d": 76.0,
                "hole_d": 6.6, "tap_d": 5.0, "tap_depth": 12.0, "head_d": 10.0, "head_h": 6.0, "shank_d": 6.0,
                "shank_l": 16.0, "washer_od": 12.0, "washer_id": 6.4, "washer_t": 1.6, "n_bolts": 4},
}


def bolt_xy(s: dict):
    r = s["bolt_circle_d"] / 2
    return [(r * math.cos(math.radians(45 + 90 * k)), r * math.sin(math.radians(45 + 90 * k)))
            for k in range(int(s["n_bolts"]))]


def build(design: str = "nominal") -> dict:
    import cadquery as cq

    s = DESIGNS[design]
    ft, gh = s["flange_t"], s["groove_h"]
    flange = cq.Workplane("XY").circle(s["flange_d"] / 2).circle(s["bore_d"] / 2).extrude(ft).translate((0, 0, -ft))
    groove = cq.Workplane("XY").circle(s["groove_od"] / 2).circle(s["groove_od"] / 2 - s["groove_w"]).extrude(gh + 1) \
        .translate((0, 0, -gh))
    flange = flange.cut(groove)
    for x, y in bolt_xy(s):
        flange = flange.cut(cq.Workplane("XY").center(x, y).circle(s["tap_d"] / 2).extrude(s["tap_depth"] + 1)
                            .translate((0, 0, -s["tap_depth"])))
    parts = {"flange": flange}
    # the O-ring: a torus of section cs, inside diameter ring_id, resting on the groove's bottom (z = -gh)
    Rc, rc = s["ring_id"] / 2 + s["cs"] / 2, s["cs"] / 2
    ring = cq.Solid.makeTorus(Rc, rc, pnt=cq.Vector(0, 0, -gh + rc), dir=cq.Vector(0, 0, 1))
    parts["oring"] = cq.Workplane("XY").newObject([ring])
    cover = cq.Workplane("XY").circle(s["cover_d"] / 2).extrude(s["cover_t"])
    for x, y in bolt_xy(s):
        cover = cover.cut(cq.Workplane("XY").center(x, y).circle(s["hole_d"] / 2).extrude(s["cover_t"] + 2)
                          .translate((0, 0, -1)))
    parts["cover"] = cover
    zt = s["cover_t"]
    for k, (x, y) in enumerate(bolt_xy(s)):
        parts[f"washer_{k}"] = cq.Workplane("XY").center(x, y).circle(s["washer_od"] / 2).circle(s["washer_id"] / 2) \
            .extrude(s["washer_t"]).translate((0, 0, zt))
        z0 = zt + s["washer_t"]
        head = cq.Workplane("XY").center(x, y).circle(s["head_d"] / 2).extrude(s["head_h"]).translate((0, 0, z0))
        shank = cq.Workplane("XY").center(x, y).circle(s["shank_d"] / 2).extrude(s["shank_l"]) \
            .translate((0, 0, z0 - s["shank_l"]))
        parts[f"screw_{k}"] = head.union(shank)
    for name, w in parts.items():
        sol = w.solids().vals()
        if len(sol) != 1 or not sol[0].isValid():
            raise RuntimeError(f"part {name}: {len(sol)} solids or invalid")
    return parts


def hand_volumes(design: str = "nominal") -> dict:
    s = DESIGNS[design]
    a = lambda d: math.pi * d * d / 4  # noqa: E731
    gi = s["groove_od"] - 2 * s["groove_w"]
    out = {"flange": (a(s["flange_d"]) - a(s["bore_d"])) * s["flange_t"] - (a(s["groove_od"]) - a(gi)) * s["groove_h"]
           - s["n_bolts"] * a(s["tap_d"]) * s["tap_depth"],
           "oring": 2 * math.pi ** 2 * (s["ring_id"] / 2 + s["cs"] / 2) * (s["cs"] / 2) ** 2,
           "cover": a(s["cover_d"]) * s["cover_t"] - s["n_bolts"] * a(s["hole_d"]) * s["cover_t"]}
    for k in range(int(s["n_bolts"])):
        out[f"washer_{k}"] = (a(s["washer_od"]) - a(s["washer_id"])) * s["washer_t"]
        out[f"screw_{k}"] = a(s["head_d"]) * s["head_h"] + a(s["shank_d"]) * s["shank_l"]
    return out


def squeeze_overlap_volume(design: str = "nominal") -> float:
    """The free torus's volume above the sealing face (z > 0), where the cover sits: the cap of each section circle
    above a chord at height (cs - groove_h) from its top, swept around the axis (Pappus, with the cap's centroid
    radius equal to the section centre's, the cap being symmetric about the vertical through it)."""
    s = DESIGNS[design]
    rc, h = s["cs"] / 2, s["cs"] - s["groove_h"]          # cap height above the face
    seg = rc * rc * math.acos((rc - h) / rc) - (rc - h) * math.sqrt(2 * rc * h - h * h)
    return 2 * math.pi * (s["ring_id"] / 2 + rc) * seg


def export(design: str, step: Path) -> dict:
    import cadquery as cq

    parts = build(design)
    colours = {"flange": (0.55, 0.58, 0.62), "cover": (0.70, 0.73, 0.76), "oring": (0.10, 0.10, 0.10)}
    asm = cq.Assembly(name=f"oring_seal_{design}")
    for name, w in parts.items():
        c = colours.get(name, (0.30, 0.30, 0.32) if name.startswith("screw") else (0.75, 0.75, 0.70))
        asm.add(w, name=name, color=cq.Color(*c))
    asm.export(str(step), exportType="STEP")
    return {k: float(w.val().Volume()) for k, w in parts.items()}

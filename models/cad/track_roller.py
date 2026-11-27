"""Study 10's track roller as a detailed assembly in CadQuery: the crowned outer ring, a full complement of needle
rollers, the inner ring, two side washers, and a length of the rail plate it runs on.

Axes (mm): the roller's axis along z, its mid-plane at z = 0, the rail's top surface tangent to the outer ring at
y = -R_o (the contact line along z at x = 0).

From the study: the outer diameter (100 mm), the width (30 mm), the logarithmic crown of part 2 (A = 1.3 x Lundberg's
1.379 um, z_m 30 um, models/fea/roller_3d.drop_um), the rail plate wider than the roller (60 mm). [synthetic]: the
bore and ring sections (outer ring 100 / 80 mm, needles 26 x 5 mm diameter on a 75 mm pitch circle, 22 mm long, inner
ring 70 / 50 mm), the 1 mm x 45 deg edge chamfers, the side washers (2 mm, 52 / 78 mm), the rail plate's section
(60 x 25 mm, 160 mm long). The outer ring's crown is in its profile, a few microns: invisible in a render, exact in the
STEP (the revolved profile follows the drop at 61 points).
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

DESIGNS = {
    "crowned": {"D": 100.0, "W": 30.0, "d_or_in": 80.0, "chamfer": 1.0, "crown_A_factor": 1.3, "crown_zm_um": 30.0,
                "n_needles": 26, "needle_d": 5.0, "needle_l": 22.0, "pitch_d": 75.0,
                "d_ir_out": 70.0, "d_ir_in": 50.0, "ir_W": 30.0,
                "washer_t": 2.0, "washer_in": 52.0, "washer_out": 78.0,
                "rail_w": 60.0, "rail_h": 25.0, "rail_l": 160.0, "profile_points": 61},
}


def crown_profile(s: dict):
    """(z, r) of the outer ring's crowned surface from z = -W/2 + chamfer to W/2 - chamfer: R - drop(z)."""
    from models.fea import roller_3d as R3

    p = {"roller_length_mm": s["W"], "youngs_modulus_MPa": 210000.0, "poisson_ratio": 0.3, "line_load_N_per_mm": 500.0,
         "profile": "log", "crown_zm_um": s["crown_zm_um"], "cap_um": 200.0}
    p["crown_A_um"] = s["crown_A_factor"] * R3.lundberg_A_um(p)
    c = s["chamfer"]
    z = np.linspace(-s["W"] / 2 + c, s["W"] / 2 - c, int(s["profile_points"]))
    return z, s["D"] / 2 - 1e-3 * R3.drop_um(p, z), p["crown_A_um"]


def outer_ring_volume(s: dict) -> float:
    """By Pappus on the half section: the crowned band between the chamfers (trapezoidal rule on r^2 over 4001
    points of the same drop function), the two chamfer cones, less the bore."""
    from models.fea import roller_3d as R3

    c, W, Ro, Ri = s["chamfer"], s["W"], s["D"] / 2, s["d_or_in"] / 2
    p = {"roller_length_mm": W, "youngs_modulus_MPa": 210000.0, "poisson_ratio": 0.3, "line_load_N_per_mm": 500.0,
         "profile": "log", "crown_zm_um": s["crown_zm_um"], "cap_um": 200.0}
    p["crown_A_um"] = s["crown_A_factor"] * R3.lundberg_A_um(p)
    z = np.linspace(-W / 2 + c, W / 2 - c, 4001)
    r = Ro - 1e-3 * R3.drop_um(p, z)
    band = math.pi * float(np.trapezoid(r * r, z))
    re = float(r[0])                                        # the radius where the chamfer starts (the drop there)
    cones = 2 * math.pi * c / 3 * (re ** 2 + re * (re - c) + (re - c) ** 2)     # two 45 deg frusta, re - c to re
    return band + cones - math.pi * Ri ** 2 * W


def build(design: str = "crowned") -> dict:
    import cadquery as cq

    s = DESIGNS[design]
    Ro, Ri, W, c = s["D"] / 2, s["d_or_in"] / 2, s["W"], s["chamfer"]
    z, r, _ = crown_profile(s)
    # outer ring: revolve the half section (r, z) drawn in the XY plane as (x = r, y = z), about the y axis, then
    # turn the axis onto z
    pts = [(Ri, -W / 2), (float(r[0]) - c, -W / 2)] + [(float(ri), float(zi)) for zi, ri in zip(z, r)] + \
          [(float(r[-1]) - c, W / 2), (Ri, W / 2)]
    prof = cq.Workplane("XY").moveTo(*pts[0]).lineTo(*pts[1]).lineTo(*pts[2])
    prof = prof.spline([q for q in pts[3:-2]], includeCurrent=True).lineTo(*pts[-2]).lineTo(*pts[-1]).close()
    outer = prof.revolve(360, (0, 0, 0), (0, 1, 0)).rotate((0, 0, 0), (1, 0, 0), 90)
    parts = {"outer_ring": outer}
    inner = cq.Workplane("XY").circle(s["d_ir_out"] / 2).circle(s["d_ir_in"] / 2).extrude(s["ir_W"]) \
        .translate((0, 0, -s["ir_W"] / 2))
    parts["inner_ring"] = inner
    for k in range(int(s["n_needles"])):
        a = 2 * math.pi * k / s["n_needles"]
        n = cq.Workplane("XY").center(s["pitch_d"] / 2 * math.cos(a), s["pitch_d"] / 2 * math.sin(a)) \
            .circle(s["needle_d"] / 2).extrude(s["needle_l"]).translate((0, 0, -s["needle_l"] / 2))
        parts[f"needle_{k:02d}"] = n
    for side, z0 in (("washer_front", W / 2), ("washer_back", -W / 2 - s["washer_t"])):
        parts[side] = cq.Workplane("XY").circle(s["washer_out"] / 2).circle(s["washer_in"] / 2) \
            .extrude(s["washer_t"]).translate((0, 0, z0))
    parts["rail"] = cq.Workplane("XY").box(s["rail_l"], s["rail_h"], s["rail_w"]) \
        .translate((0, -Ro - s["rail_h"] / 2, 0))
    for name, w in parts.items():
        sol = w.solids().vals()
        if len(sol) != 1 or not sol[0].isValid():
            raise RuntimeError(f"part {name}: {len(sol)} solids or invalid")
    return parts


def hand_volumes(design: str = "crowned") -> dict:
    s = DESIGNS[design]
    out = {"outer_ring": outer_ring_volume(s),
           "inner_ring": math.pi / 4 * (s["d_ir_out"] ** 2 - s["d_ir_in"] ** 2) * s["ir_W"],
           "washer_front": math.pi / 4 * (s["washer_out"] ** 2 - s["washer_in"] ** 2) * s["washer_t"],
           "rail": s["rail_l"] * s["rail_h"] * s["rail_w"]}
    out["washer_back"] = out["washer_front"]
    for k in range(int(s["n_needles"])):
        out[f"needle_{k:02d}"] = math.pi / 4 * s["needle_d"] ** 2 * s["needle_l"]
    return out


def export(design: str, step: Path) -> dict:
    import cadquery as cq

    parts = build(design)
    colours = {"outer_ring": (0.62, 0.66, 0.70), "inner_ring": (0.55, 0.58, 0.62), "rail": (0.45, 0.48, 0.52)}
    asm = cq.Assembly(name=f"track_roller_{design}")
    for name, w in parts.items():
        c = colours.get(name, (0.80, 0.70, 0.40) if name.startswith("needle") else (0.70, 0.72, 0.74))
        asm.add(w, name=name, color=cq.Color(*c))
    asm.export(str(step), exportType="STEP")
    return {k: float(w.val().Volume()) for k, w in parts.items()}

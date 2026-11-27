"""The fan rotor (study 23) as a detailed assembly, in CadQuery: the 65 mm shaft with its bearing journals, the
impeller's hub on a keyed seat (DIN 6885 form A key), and the 400 x 25 mm disc welded to the hub.

Axes (mm): the shaft along z, the bearing centres at z = 0 and z = L (the analysed span; the shaft ends there, as in
both models of study 23); the disc and hub centred at L / 2.

From the study: the span (1 m), shaft 65 mm, disc 400 x 25 mm, and, from part 2, the hub (130 x 100 mm) and journals
(55 x 50 mm). [synthetic]: the shoulder fillets (r 1.5), end chamfers (1 mm), the weld size (6 mm fillets, both sides
of the disc), the key's length (90 mm). Keyway sizes are DIN 6885-1 form A as published tables reproduce them for
58-65 mm shafts: key 18 x 11, shaft depth t1 7.0, hub depth t2 4.4 (the standard itself was not read). The solid study
(models/fea/rotor_solid.py) bonds hub and shaft and leaves the keyway out: a tight key restores the section.
"""

from __future__ import annotations

import math
from pathlib import Path

DESIGNS = {"d65": {"L": 1000.0, "d": 65.0, "dj": 55.0, "lj": 50.0, "dh": 130.0, "lh": 100.0, "D": 400.0, "w": 25.0,
                   "key_b": 18.0, "key_h": 11.0, "t1": 7.0, "t2": 4.4, "key_l": 90.0, "r_fillet": 1.5,
                   "chamfer": 1.0, "weld": 6.0}}


def _spandrel_ring(r_small: float, f: float) -> float:
    """Volume of a concave fillet ring of radius f in the corner at radius r_small (Pappus)."""
    return f ** 2 * (1 - math.pi / 4) * 2 * math.pi * (r_small + f * (10 - 3 * math.pi) / (3 * (4 - math.pi)))


def keyway_volume(R: float, b: float, L: float, depth_below_edge: float, n: int = 4000) -> float:
    """Volume an end-milled keyway (stadium b x L in plan, flat bottom at R - depth below the shaft's surface edge,
    i.e. at x = R - t1) removes from a solid cylinder of radius R: the integral over the plan area of the height from
    the bottom up to the circle, sqrt(R^2 - y^2) - (R - t1). Midpoint rule in y, exact in z."""
    x0 = R - depth_below_edge
    tot = 0.0
    for i in range(n):
        y = -b / 2 + (i + 0.5) * b / n
        h = math.sqrt(R * R - y * y) - x0
        # stadium: straight length L - b plus the two semicircle chords at this y
        length = (L - b) + 2 * math.sqrt(max((b / 2) ** 2 - y * y, 0.0))
        tot += h * length * (b / n)
    return tot


def build(design: str = "d65") -> dict:
    import cadquery as cq

    s = DESIGNS[design]
    L, zc = s["L"], s["L"] / 2
    rj, r, rh, R = s["dj"] / 2, s["d"] / 2, s["dh"] / 2, s["D"] / 2
    f, c = s["r_fillet"], s["chamfer"]
    prof = (cq.Workplane("XZ").moveTo(0, 0).lineTo(rj - c, 0).lineTo(rj, c).lineTo(rj, s["lj"] - f)
            .radiusArc((rj + f, s["lj"]), f).lineTo(r, s["lj"]).lineTo(r, L - s["lj"]).lineTo(rj + f, L - s["lj"])
            .radiusArc((rj, L - s["lj"] + f), f).lineTo(rj, L - c).lineTo(rj - c, L).lineTo(0, L).close())
    shaft = prof.revolve(360, (0, 0, 0), (0, 1, 0))
    kb, kl = s["key_b"], s["key_l"]
    cutter = (cq.Workplane("YZ", origin=(r - s["t1"], 0, zc)).slot2D(kl, kb, angle=90).extrude(s["t1"] + 5.0))
    shaft = shaft.cut(cutter)
    key = (cq.Workplane("YZ", origin=(r - s["t1"], 0, zc)).slot2D(kl, kb, angle=90).extrude(s["key_h"]))
    hub = cq.Workplane("XY").circle(rh).circle(r).extrude(s["lh"]).translate((0, 0, zc - s["lh"] / 2))
    hub_kw = cq.Workplane("XY").rect(2 * (r + s["t2"]), kb).extrude(s["lh"] + 2).translate((0, 0, zc - s["lh"] / 2 - 1))
    hub_kw = hub_kw.intersect(cq.Workplane("XY").box(r + s["t2"] + 1, kb, s["lh"] + 2, centered=(False, True, False))
                              .translate((0, 0, zc - s["lh"] / 2 - 1)))
    hub = hub.cut(hub_kw)
    disc = cq.Workplane("XY").circle(R).circle(rh).extrude(s["w"]).translate((0, 0, zc - s["w"] / 2))
    a = s["weld"]
    welds = {}
    for side, z0 in (("front", zc - s["w"] / 2), ("back", zc + s["w"] / 2)):
        sgn = -1 if side == "front" else 1
        tri = (cq.Workplane("XZ").moveTo(rh, z0).lineTo(rh + a, z0).lineTo(rh, z0 + sgn * a).close())
        welds[f"weld_{side}"] = tri.revolve(360, (0, 0, 0), (0, 1, 0))
    parts = {"shaft": shaft, "key": key, "hub": hub, "disc": disc} | welds
    for name, w in parts.items():
        if not w.val().isValid():
            raise RuntimeError(f"fan rotor: {name} is not a valid solid")
    return parts


def hand_volumes(design: str = "d65") -> dict:
    s = DESIGNS[design]
    L = s["L"]
    rj, r, rh, R = s["dj"] / 2, s["d"] / 2, s["dh"] / 2, s["D"] / 2
    f, c = s["r_fillet"], s["chamfer"]
    body = math.pi * (rj ** 2 * 2 * s["lj"] + r ** 2 * (L - 2 * s["lj"]))
    body += 2 * _spandrel_ring(rj, f) - 2 * (c ** 2 / 2) * 2 * math.pi * (rj - c / 3)
    kw = keyway_volume(r, s["key_b"], s["key_l"], s["t1"])
    kb, kl = s["key_b"], s["key_l"]
    key_area = (kl - kb) * kb + math.pi * (kb / 2) ** 2
    # hub: annulus minus its keyway, the slot from the bore up to r + t2 across the key's width (a flat top)
    hub_kw = s["lh"] * (kb * (r + s["t2"]) - 2 * (r * r * math.asin(kb / (2 * r)) / 2
                                                    + (kb / 2) * math.sqrt(r * r - kb * kb / 4) / 2))
    hub = math.pi * (rh ** 2 - r ** 2) * s["lh"] - hub_kw
    a = s["weld"]
    weld = a * a / 2 * 2 * math.pi * (rh + a / 3)
    return {"shaft": body - kw, "key": key_area * s["key_h"], "hub": hub,
            "disc": math.pi * (R ** 2 - rh ** 2) * s["w"], "weld_front": weld, "weld_back": weld}


def export(design: str, step: Path) -> dict:
    import cadquery as cq

    parts = build(design)
    asm = cq.Assembly(name=f"fan_rotor_{design}")
    for name, w in parts.items():
        asm.add(w, name=name)
    step = Path(step)
    step.parent.mkdir(parents=True, exist_ok=True)
    asm.export(str(step), exportType="STEP")      # Assembly.save is deprecated in CadQuery 2.8
    return {"design": design, "parts": len(parts), "mass_kg": 7850e-9 * sum(w.val().Volume() for w in parts.values()),
            "step": step.name}


if __name__ == "__main__":
    import json
    import sys

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("portfolio/cad")
    print(json.dumps([export(d, out / f"fan_rotor_{d}.step") for d in DESIGNS], indent=1))

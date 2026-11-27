"""The two-stage gearbox's intermediate shaft as a detailed part (study 26), in CadQuery.

Left to right along z (z = 0 at the left end; units mm):
  left bearing journal (deep-groove ball bearing, circlip groove to DIN 471 outboard, 1 x 45 deg chamfer)
  -> gear seat (the stage 1 wheel, DIN 6885 form A keyway, end-milled) -> shoulder fillet -> collar
  -> pinion seat (the stage 2 pinion, its own keyway) -> right bearing journal (circlip groove, chamfer).

What the study analysed and therefore fixes: the gear seat diameter d, the collar D, the shoulder fillet at z = 90,
and the seat's keyway (width, depth, corner radius, 40 mm long, ending 2 mm before the fillet starts), as in
models/fea/keyed_shaft.py. Everything else (bearings, journals, grooves, pinion seat, lengths) is [synthetic]: a
plausible layout for the drawing and the render, not a client's dimension. The fillet here is the nominal 0.05 d
(the study assessed its lower tolerance, 0.2 mm smaller).

Keyway table values (DIN 6885-1 form A, from published reproductions; the standard itself was not read):
  30-38 mm: 10 x 8, t1 5.0;  38-44 mm: 12 x 8, t1 5.0;  44-50 mm: 14 x 9, t1 5.5; bottom corner 0.25-0.40 mm.
Circlip grooves (DIN 471): 30 mm shaft d2 28.6, m 1.6; 35 mm shaft d2 33.0, m 1.6.
"""

from __future__ import annotations

import math
from pathlib import Path

DESIGNS = {
    # part 1's recommended step with the keyway that fails it (study 26 part 2)
    "d36": {"journal": 30.0, "bearing_width": 16.0, "groove_d": 28.6, "groove_m": 1.6,      # 6206 [synthetic]
            "seat": 36.0, "collar": 45.0, "fillet": 1.8, "key_seat": (10.0, 5.0, 0.4),
            "pinion": 40.0, "key_pinion": (12.0, 5.0, 0.4)},
    # the smallest keyed seat that passes with a 0.40 mm keyway corner (study 26 part 2, design run)
    "d40": {"journal": 35.0, "bearing_width": 17.0, "groove_d": 33.0, "groove_m": 1.6,      # 6207 [synthetic]
            "seat": 40.0, "collar": 50.0, "fillet": 2.0, "key_seat": (12.0, 5.0, 0.4),
            "pinion": 45.0, "key_pinion": (14.0, 5.5, 0.4)},
}
# axial layout [synthetic except the shoulder at 90 and the seat keyway's 40 mm / 2 mm gap]
Z_SEAT, Z_SHOULDER, Z_COLLAR_END, Z_PINION_END, Z_END = 20.0, 90.0, 100.0, 150.0, 170.0
CHAMFER, R_JOURNAL, R_COLLAR = 1.0, 0.6, 1.0      # end chamfers, journal step fillets, collar-to-pinion fillet
SEAT_KEY_LENGTH, SEAT_KEY_GAP, PINION_KEY_LENGTH, PINION_KEY_GAP = 40.0, 2.0, 36.0, 3.0


def keyways(s: dict) -> list[dict]:
    """Each keyway: seat radius, width, depth, corner radius, z range (ends included)."""
    B, t1, rk = s["key_seat"]
    z1 = Z_SHOULDER - s["fillet"] - SEAT_KEY_GAP
    Bp, t1p, rkp = s["key_pinion"]
    z0p = Z_COLLAR_END + R_COLLAR + PINION_KEY_GAP
    return [{"R": s["seat"] / 2, "B": B, "t1": t1, "rk": rk, "z0": z1 - SEAT_KEY_LENGTH, "z1": z1},
            {"R": s["pinion"] / 2, "B": Bp, "t1": t1p, "rk": rkp, "z0": z0p, "z1": z0p + PINION_KEY_LENGTH}]


def grooves(s: dict) -> list[tuple[float, float]]:
    """Circlip grooves (z0, z1), outboard of each bearing, which seats against the journal's step."""
    w, m = s["bearing_width"], s["groove_m"]
    return [(Z_SEAT - w - m, Z_SEAT - w), (Z_PINION_END + w, Z_PINION_END + w + m)]


def build(design: str | dict = "d36", with_keyways: bool = True):
    """The whole shaft as a CadQuery Workplane (valid solid checked)."""
    import cadquery as cq

    s = DESIGNS[design] if isinstance(design, str) else design
    rj, rs, rc, rp = s["journal"] / 2, s["seat"] / 2, s["collar"] / 2, s["pinion"] / 2
    f, c = s["fillet"], CHAMFER
    # half profile in the XZ plane (x = radius, second coordinate = z), revolved about z; concave fillets as arcs
    w = (cq.Workplane("XZ").moveTo(0, 0).lineTo(rj - c, 0).lineTo(rj, c)
         .lineTo(rj, Z_SEAT - R_JOURNAL).radiusArc((rj + R_JOURNAL, Z_SEAT), R_JOURNAL).lineTo(rs, Z_SEAT)
         .lineTo(rs, Z_SHOULDER - f).radiusArc((rs + f, Z_SHOULDER), f).lineTo(rc, Z_SHOULDER)
         .lineTo(rc, Z_COLLAR_END).lineTo(rp + R_COLLAR, Z_COLLAR_END)
         .radiusArc((rp, Z_COLLAR_END + R_COLLAR), R_COLLAR)
         .lineTo(rp, Z_PINION_END).lineTo(rj + R_JOURNAL, Z_PINION_END)
         .radiusArc((rj, Z_PINION_END + R_JOURNAL), R_JOURNAL)
         .lineTo(rj, Z_END - c).lineTo(rj - c, Z_END).lineTo(0, Z_END).close())
    shaft = w.revolve(360, (0, 0, 0), (0, 1, 0))
    for z0, z1 in grooves(s):
        ring = cq.Workplane("XY").circle(rj + 1.0).circle(s["groove_d"] / 2).extrude(z1 - z0).translate((0, 0, z0))
        shaft = shaft.cut(ring)
    for k in keyways(s) if with_keyways else []:    # end-milled: stadium in plan, rounded bottom corners
        cutter = (cq.Workplane("YZ", origin=(k["R"] - k["t1"], 0, 0.5 * (k["z0"] + k["z1"])))
                  .slot2D(k["z1"] - k["z0"], k["B"], angle=90).extrude(k["t1"] + 0.25 * 2 * k["R"])
                  .faces("<X").edges().fillet(k["rk"]))
        shaft = shaft.cut(cutter)
    if not shaft.val().isValid():
        raise RuntimeError("intermediate shaft: CadQuery solid is not valid")
    return shaft


def hand_volume(design: str | dict = "d36") -> float:
    """The revolved body by hand (cylinders, Pappus for fillets and chamfers, grooves), without the keyways."""
    s = DESIGNS[design] if isinstance(design, str) else design
    rj, rs, rc, rp = s["journal"] / 2, s["seat"] / 2, s["collar"] / 2, s["pinion"] / 2
    cyl = math.pi * (rj ** 2 * (Z_SEAT + Z_END - Z_PINION_END) + rs ** 2 * (Z_SHOULDER - Z_SEAT)
                     + rc ** 2 * (Z_COLLAR_END - Z_SHOULDER) + rp ** 2 * (Z_PINION_END - Z_COLLAR_END))

    def spandrel(r_small, f):   # concave fillet in the corner at radius r_small: area f^2 (1 - pi/4), Pappus
        return f ** 2 * (1 - math.pi / 4) * 2 * math.pi * (r_small + f * (10 - 3 * math.pi) / (3 * (4 - math.pi)))

    fil = 2 * spandrel(rj, R_JOURNAL) + spandrel(rs, s["fillet"]) + spandrel(rp, R_COLLAR)
    cham = 2 * (CHAMFER ** 2 / 2) * 2 * math.pi * (rj - CHAMFER / 3)
    grv = sum(math.pi * (rj ** 2 - (s["groove_d"] / 2) ** 2) * (z1 - z0) for z0, z1 in grooves(s))
    return cyl + fil - cham - grv


def export(design: str, step: Path) -> dict:
    import cadquery as cq

    shaft = build(design)
    step = Path(step)
    step.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(shaft, str(step))
    bb = shaft.val().BoundingBox()
    return {"design": design, "volume_mm3": float(shaft.val().Volume()), "faces": len(shaft.faces().vals()),
            "length_mm": bb.zlen, "max_diameter_mm": max(bb.xlen, bb.ylen), "step": step.name}


if __name__ == "__main__":
    import json
    import sys

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("portfolio/cad")
    print(json.dumps([export(d, out / f"intermediate_shaft_{d}.step") for d in DESIGNS], indent=1))

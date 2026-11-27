"""The steel portal's knee (study 28 part 2) as a detailed assembly, in CadQuery: the W10x33 column's top, the W14x30
beam's end, and the bolted flange-plated moment connection as it would be detailed: flange plates and a single shear
tab shop-welded to the column flange (1/4 in. fillet welds), a pair of clipped continuity plates at the top plate's
level, and 3/4 in. heavy-hex structural bolts with nuts and hardened washers through standard holes.

Axes as models/fea/moment_connection.py (mm): X along the beam (the column's centreline at X = 0), Y up (the
column's top at Y = 0, flush with the top plate), Z out of the frame's plane; here the whole joint, both sides of
Z = 0. The analysed solid (moment_connection) is half of this, bonded, without holes, bolts or welds.

From the study (validation/flange_plated.DESIGNS): plate sizes, bolt layout (3/4 in. at 3 in. pitch on a 3.5 in.
gage, 1 1/2 in. edges, 1/2 in. setback), the shear tab, continuity plates, weld size. [synthetic]: stub lengths,
the weld returns, bolt lengths (grip + washer + nut + about two threads, to the next 1/4 in.). Bolt, nut and washer
dimensions are the nominal values published tables give for 3/4 in. heavy-hex structural bolts, heavy-hex nuts and
hardened washers (the ASTM and ASME standards themselves were not read).
"""

from __future__ import annotations

import math
from pathlib import Path

IN = 25.4
BOLT = {"d": 0.75 * IN, "hole": (0.75 + 1 / 16) * IN, "head_af": 1.25 * IN, "head_h": 15 / 32 * IN,
        "nut_af": 1.25 * IN, "nut_h": 47 / 64 * IN, "washer_od": 1.469 * IN, "washer_t": 0.177 * IN}
WELD_LEG = 0.25 * IN
COLUMN_BELOW, BEAM_LENGTH = 600.0, 800.0          # [synthetic] stub lengths, mm

DESIGNS = {
    # slip-critical (Class A), three bolts per line: the study's recommendation
    "slip_critical6": {"n": 3},
    # bearing-type (snug-tight), two bolts per line: fails the frame's REQ-A1 once the bolts slip (study 28 part 2)
    "bearing4": {"n": 2},
}
COMMON = {"plate_t": 0.5 * IN, "plate_b": 6.0 * IN, "gage": 3.5 * IN, "pitch": 3.0 * IN, "edge": 1.5 * IN,
          "setback": 0.5 * IN, "tab_t": 0.375 * IN, "tab_w": 3.5 * IN, "tab_h": 9.0 * IN, "tab_n": 3,
          "cont_t": 0.5 * IN, "cont_clip": 0.75 * IN}


def sections():
    from models.fea.moment_connection import section_mm
    from validation import aisc360

    return section_mm(aisc360.shape("W10X33")), section_mm(aisc360.shape("W14X30"))


def layout(design: str = "slip_critical6") -> dict:
    """Positions (mm) of every part and bolt."""
    col, beam = sections()
    c = COMMON | DESIGNS[design]
    face, tp = col["d"] / 2, c["plate_t"]
    y_bt = -tp                                    # beam's top
    y_bb = y_bt - beam["d"]
    y_cl = y_bt - beam["d"] / 2
    Lp = c["setback"] + c["edge"] + (c["n"] - 1) * c["pitch"] + c["edge"]
    xs = [face + c["setback"] + c["edge"] + k * c["pitch"] for k in range(c["n"])]           # flange bolt lines
    tab_x = face + c["setback"] + c["edge"]                                                 # web bolt line
    tab_y = [y_cl + (k - (c["tab_n"] - 1) / 2) * c["pitch"] for k in range(c["tab_n"])]
    return {"col": col, "beam": beam, "c": c, "face": face, "y_bt": y_bt, "y_bb": y_bb, "y_cl": y_cl, "Lp": Lp,
            "flange_bolts": [(x, z) for x in xs for z in (-c["gage"] / 2, c["gage"] / 2)],
            "web_bolts": [(tab_x, y) for y in tab_y], "y_col_bot": y_bb - tp - COLUMN_BELOW}


def _w_full(wp, s: dict, length: float):
    """Whole W-section (local x across the depth, local y across the width, both centred) with its four root
    fillets, extruded along the workplane's normal."""
    d, bf, tf, tw, r = s["d"], s["bf"], s["tf"], s["tw"], s["r"]
    xi = d / 2 - tf
    w = (wp.moveTo(-d / 2, -bf / 2).lineTo(-d / 2, bf / 2).lineTo(-xi, bf / 2).lineTo(-xi, tw / 2 + r)
         .radiusArc((-xi + r, tw / 2), -r).lineTo(xi - r, tw / 2).radiusArc((xi, tw / 2 + r), -r)
         .lineTo(xi, bf / 2).lineTo(d / 2, bf / 2).lineTo(d / 2, -bf / 2).lineTo(xi, -bf / 2)
         .lineTo(xi, -tw / 2 - r).radiusArc((xi - r, -tw / 2), -r).lineTo(-xi + r, -tw / 2)
         .radiusArc((-xi, -tw / 2 - r), -r).lineTo(-xi, -bf / 2).close())
    return w.extrude(length)


def _box(x0, x1, y0, y1, z0, z1):
    import cadquery as cq

    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def _hex(af: float, h: float, axis: str, centre, hole: float = 0.0):
    """Hexagonal prism (across flats af, height h) centred on `centre`, its axis "Y" or "Z"; an optional hole."""
    import cadquery as cq

    plane = cq.Plane(origin=centre, xDir=(1, 0, 0), normal=(0, 1, 0) if axis == "Y" else (0, 0, 1))
    w = cq.Workplane(plane).workplane(offset=-h / 2).polygon(6, af / math.cos(math.pi / 6)).extrude(h)
    if hole:
        w = w.cut(cq.Workplane(plane).workplane(offset=-h).circle(hole / 2).extrude(2 * h))
    return w


def _cyl(dia: float, h: float, axis: str, centre, hole: float = 0.0):
    import cadquery as cq

    plane = cq.Plane(origin=centre, xDir=(1, 0, 0), normal=(0, 1, 0) if axis == "Y" else (0, 0, 1))
    w = cq.Workplane(plane).workplane(offset=-h / 2).circle(dia / 2)
    if hole:
        w = w.circle(hole / 2)
    return w.extrude(h)


def _fillet_weld(p0, axis: str, length: float, legs):
    """A fillet weld: right triangle with legs (dx, dy_or_dz) at corner p0, swept `length` along `axis` (Z or Y)."""
    import cadquery as cq

    (x, y, z), (a, b) = p0, legs
    if axis == "Z":           # triangle in the XY plane at the corner (x, y), swept along +Z from z
        return cq.Workplane("XY", origin=(0, 0, z)).polyline([(x, y), (x + a, y), (x, y + b)]).close().extrude(length)
    # axis "Y": triangle in the XZ plane at the corner (x, z), swept along +Y from y
    pl = cq.Plane(origin=(0, y, 0), xDir=(1, 0, 0), normal=(0, 1, 0))     # local y = normal x xDir = -Z
    return cq.Workplane(pl).polyline([(x, -z), (x + a, -z), (x, -(z + b))]).close().extrude(length)


def bolt_length(grip: float) -> float:
    """Grip + washer + nut + about two threads (2 x 0.1 in. pitch, UNC 3/4-10), up to the next 1/4 in."""
    need = grip + BOLT["washer_t"] + BOLT["nut_h"] + 2 * 0.1 * IN
    return math.ceil(need / (0.25 * IN) - 1e-9) * 0.25 * IN


def build(design: str = "slip_critical6") -> dict:
    """The assembly's parts as {name: Workplane}; each a valid solid."""
    import cadquery as cq

    L = layout(design)
    col, beam, c = L["col"], L["beam"], L["c"]
    face, tp, bp = L["face"], c["plate_t"], c["plate_b"]
    parts = {}
    parts["column"] = _w_full(cq.Workplane(cq.Plane(origin=(0, 0, 0), xDir=(1, 0, 0), normal=(0, -1, 0))), col,
                              -L["y_col_bot"])
    x_b0 = face + c["setback"]
    beam_s = _w_full(cq.Workplane(cq.Plane(origin=(x_b0, L["y_cl"], 0), xDir=(0, 1, 0), normal=(1, 0, 0))), beam,
                     BEAM_LENGTH)
    hole = BOLT["hole"]
    for x, z in L["flange_bolts"]:
        beam_s = beam_s.cut(_cyl(hole, beam["d"] + 10, "Y", (x, L["y_cl"], z)))
    for x, y in L["web_bolts"]:
        beam_s = beam_s.cut(_cyl(hole, beam["tw"] + 10, "Z", (x, y, 0.0)))
    parts["beam"] = beam_s
    for name, (y0, y1) in (("top_plate", (L["y_bt"], 0.0)), ("bottom_plate", (L["y_bb"] - tp, L["y_bb"]))):
        pl = _box(face, face + L["Lp"], y0, y1, -bp / 2, bp / 2)
        for x, z in L["flange_bolts"]:
            pl = pl.cut(_cyl(hole, tp + 10, "Y", (x, (y0 + y1) / 2, z)))
        parts[name] = pl
    z0 = beam["tw"] / 2
    tab = _box(face, face + c["tab_w"], L["y_cl"] - c["tab_h"] / 2, L["y_cl"] + c["tab_h"] / 2, z0, z0 + c["tab_t"])
    for x, y in L["web_bolts"]:
        tab = tab.cut(_cyl(hole, c["tab_t"] + 10, "Z", (x, y, z0 + c["tab_t"] / 2)))
    parts["shear_tab"] = tab
    xi, k = col["d"] / 2 - col["tf"], c["cont_clip"]
    for side, sz in (("continuity_plate_front", 1), ("continuity_plate_back", -1)):
        za, zb = sorted((sz * col["tw"] / 2, sz * col["bf"] / 2))
        cp = _box(-xi, xi, -c["cont_t"], 0.0, za, zb)
        zc0, zc1 = sorted((sz * col["tw"] / 2, sz * (col["tw"] / 2 + k)))
        for sx in (-1, 1):
            xa, xb = sorted((sx * xi, sx * (xi - k)))
            cp = cp.cut(_box(xa, xb, -c["cont_t"], 0.0, zc0, zc1))
        parts[side] = cp
    # fillet welds: each flange plate to the column flange on both faces, across its width; the tab both sides
    wl = WELD_LEG
    for name, y_face in (("top_plate", (L["y_bt"], 0.0)), ("bottom_plate", (L["y_bb"] - tp, L["y_bb"]))):
        lo, hi = y_face
        parts[f"weld_{name}_upper"] = _fillet_weld((face, hi, -bp / 2), "Z", bp, (wl, wl)) if hi < 0 else None
        parts[f"weld_{name}_lower"] = _fillet_weld((face, lo, -bp / 2), "Z", bp, (wl, -wl))
    parts = {k: v for k, v in parts.items() if v is not None}
    y_t0 = L["y_cl"] - c["tab_h"] / 2
    # the tab both sides: the inner weld sits in the setback gap, clear of the beam web (setback 12.7 > leg 6.35)
    parts["weld_tab_outer"] = _fillet_weld((face, y_t0, z0 + c["tab_t"]), "Y", c["tab_h"], (wl, wl))
    parts["weld_tab_inner"] = _fillet_weld((face, y_t0, z0), "Y", c["tab_h"], (wl, -wl))
    # bolts: flange bolts vertical, head above the top plate / below the bottom plate, nut on the beam flange's
    # inside; web bolts horizontal, head on the tab's side
    gf = tp + beam["tf"]
    gw = c["tab_t"] + beam["tw"]
    for k, (x, z) in enumerate(L["flange_bolts"]):
        for where, (y_out, sgn) in (("t", (0.0, -1)), ("b", (L["y_bb"] - tp, 1))):
            parts.update(_bolt(f"bolt_{where}{k}", (x, y_out, z), "Y", sgn, gf))
    for k, (x, y) in enumerate(L["web_bolts"]):
        parts.update(_bolt(f"bolt_w{k}", (x, y, z0 + c["tab_t"]), "Z", -1, gw))
    for name, w in parts.items():
        if not w.val().isValid():
            raise RuntimeError(f"portal knee: {name} is not a valid solid")
    return parts


def _bolt(name: str, at, axis: str, sgn: int, grip: float) -> dict:
    """Bolt head on the outer face `at` (the shank going in the direction sgn along axis), washer and nut on the far
    side of the grip."""
    import numpy as np

    u = np.array([0.0, 1.0, 0.0]) if axis == "Y" else np.array([0.0, 0.0, 1.0])
    p0 = np.asarray(at, float)
    Lb = bolt_length(grip)
    head = _hex(BOLT["head_af"], BOLT["head_h"], axis, tuple(p0 - sgn * u * BOLT["head_h"] / 2))
    shank = _cyl(BOLT["d"], Lb, axis, tuple(p0 + sgn * u * Lb / 2))
    far = p0 + sgn * u * grip
    washer = _cyl(BOLT["washer_od"], BOLT["washer_t"], axis, tuple(far + sgn * u * BOLT["washer_t"] / 2),
                  hole=BOLT["hole"])
    nut = _hex(BOLT["nut_af"], BOLT["nut_h"], axis,
               tuple(far + sgn * u * (BOLT["washer_t"] + BOLT["nut_h"] / 2)), hole=BOLT["d"])
    return {f"{name}_head": head, f"{name}_shank": shank, f"{name}_washer": washer, f"{name}_nut": nut}


def hand_volumes(design: str = "slip_critical6") -> dict:
    """Each part type's volume by hand (mm^3)."""
    from models.fea.moment_connection import half_area

    L = layout(design)
    col, beam, c = L["col"], L["beam"], L["c"]
    tp, bp, hole = c["plate_t"], c["plate_b"], BOLT["hole"]
    ah = math.pi * hole ** 2 / 4
    nf, nw = len(L["flange_bolts"]), len(L["web_bolts"])
    hexa = lambda af: math.sqrt(3) / 2 * af ** 2       # noqa: E731
    xi, k = col["d"] / 2 - col["tf"], c["cont_clip"]
    gf, gw = tp + beam["tf"], c["tab_t"] + beam["tw"]
    return {
        "column": 2 * half_area(col) * -L["y_col_bot"],
        "beam": 2 * half_area(beam) * BEAM_LENGTH - ah * (2 * nf * beam["tf"] + nw * beam["tw"]),
        "plate": bp * tp * L["Lp"] - nf * ah * tp,
        "shear_tab": c["tab_w"] * c["tab_h"] * c["tab_t"] - nw * ah * c["tab_t"],
        "continuity_plate": c["cont_t"] * (2 * xi * (col["bf"] - col["tw"]) / 2 - 2 * k * k),
        "weld_plate": WELD_LEG ** 2 / 2 * bp,
        "weld_tab": WELD_LEG ** 2 / 2 * c["tab_h"],
        "head": hexa(BOLT["head_af"]) * BOLT["head_h"],
        "nut": (hexa(BOLT["nut_af"]) - math.pi * BOLT["d"] ** 2 / 4) * BOLT["nut_h"],
        "washer": math.pi / 4 * (BOLT["washer_od"] ** 2 - hole ** 2) * BOLT["washer_t"],
        "shank_flange": math.pi * BOLT["d"] ** 2 / 4 * bolt_length(gf),
        "shank_web": math.pi * BOLT["d"] ** 2 / 4 * bolt_length(gw),
    }


def export(design: str, step: Path) -> dict:
    """The assembly as one STEP (a compound of its parts, each a separate solid)."""
    import cadquery as cq

    parts = build(design)
    asm = cq.Assembly(name=f"portal_knee_{design}")
    for name, w in parts.items():
        asm.add(w, name=name)
    step = Path(step)
    step.parent.mkdir(parents=True, exist_ok=True)
    asm.save(str(step), exportType="STEP")
    bolts = sum(1 for n in parts if n.endswith("_shank"))
    return {"design": design, "parts": len(parts), "bolts": bolts,
            "volume_mm3": float(sum(w.val().Volume() for w in parts.values())), "step": step.name}


if __name__ == "__main__":
    import json
    import sys

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("portfolio/cad")
    print(json.dumps([export(d, out / f"portal_knee_{d}.step") for d in DESIGNS], indent=1))

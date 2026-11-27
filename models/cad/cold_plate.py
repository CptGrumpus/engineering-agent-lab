"""Studies 11 and 15's cold plate as a detailed assembly in CadQuery: the base with its milled passage, the manifold
wells and the drilled ports, the brazed cover, two hose fittings, and the two heated components.

Axes (mm): the flow along +x, the passage centred on y = 0, the passage's floor at z = 0 and its roof (the cover's
underside) at z = 1; the heated length from x = 5 to 55 (study 11: entry 5 mm, heated 50, exit 5).

From the studies: the passage (1 mm deep, 20 mm wide: study 5's synthetic width, also study 11 part 2's; 60 mm long:
entry 5, heated 50, exit 5), the cover (3 mm 6061-T6: study 15), the components' footprint (50 mm long over the
passage's width: both faces heated). [synthetic]: the base (100 x 50 x 8 mm, the passage milled into its top), the
manifold wells (10 mm diameter, 6 mm deep, centred 5 mm beyond each end of the passage), the side ports (5 mm drilled
from the base's ends to the wells' axes, 0.75 mm under the top face), the fittings (12 mm hex simplified to a 12 mm
cylinder, 15 mm long, 5 mm bore), the components (50 x 20 x 2.5 mm blocks, one on the cover, one under the base). The cover is
vacuum-brazed to the base: no seal or screws drawn.
"""

from __future__ import annotations

import math
from pathlib import Path

DESIGNS = {
    "study11": {"base_l": 100.0, "base_w": 50.0, "base_t": 8.0, "pass_l": 60.0, "pass_w": 20.0, "pass_h": 1.0,
                "well_d": 10.0, "well_h": 6.0, "well_off": 5.0, "port_d": 5.0, "port_cover": 0.75,
                "cover_t": 3.0, "fit_d": 12.0, "fit_l": 15.0, "fit_bore": 5.0, "comp_l": 50.0, "comp_w": 20.0, "comp_t": 2.5,
                "heated_x0": 5.0},
}


def geometry(s: dict) -> dict:
    """Key coordinates: the passage from x = 0 to pass_l on the base's top face (z = 0 is the passage floor, so the
    base's top face is at z = pass_h and its bottom at z = pass_h - base_t)."""
    x0 = -(s["base_l"] - s["pass_l"]) / 2                      # the base's upstream end
    return {"x0": x0, "x1": x0 + s["base_l"], "z_top": s["pass_h"], "z_bot": s["pass_h"] - s["base_t"],
            "well_x": (-s["well_off"], s["pass_l"] + s["well_off"]),
            # the port's axis: port_cover of metal between its top and the base's top face (the first draft centred it
            # 2.5 mm down and a 6 mm drill broke out under the cover: found by the hand volume)
            "port_z": s["pass_h"] - s["port_cover"] - s["port_d"] / 2}


def build(design: str = "study11") -> dict:
    import cadquery as cq

    s = DESIGNS[design]
    g = geometry(s)
    if g["port_z"] - s["port_d"] / 2 < s["pass_h"] - s["well_h"]:
        raise ValueError("the port reaches below the well's floor")
    base = cq.Workplane("XY").box(s["base_l"], s["base_w"], s["base_t"], centered=(False, True, False)) \
        .translate((g["x0"], 0, g["z_bot"]))
    # the passage: milled from the top face down to z = 0
    base = base.cut(cq.Workplane("XY").box(s["pass_l"], s["pass_w"], s["pass_h"] + 1, centered=(False, True, False))
                    .translate((0, 0, 0)))
    # the manifold wells, open to the passage, and the ports drilled from the ends into them
    for k, xw in enumerate(g["well_x"]):
        base = base.cut(cq.Workplane("XY").center(xw, 0).circle(s["well_d"] / 2).extrude(s["well_h"] + 1)
                        .translate((0, 0, s["pass_h"] - s["well_h"])))
        xe = g["x0"] if k == 0 else g["x1"]
        length = abs(xw - xe)
        drill = cq.Workplane("YZ").center(0, g["port_z"]).circle(s["port_d"] / 2).extrude(length) \
            .translate((min(xw, xe), 0, 0))
        base = base.cut(drill)
    parts = {"base": base}
    parts["cover"] = cq.Workplane("XY").box(s["base_l"], s["base_w"], s["cover_t"], centered=(False, True, False)) \
        .translate((g["x0"], 0, g["z_top"]))
    for name, xe, sign in (("fitting_in", g["x0"], -1), ("fitting_out", g["x1"], 1)):
        f = cq.Workplane("YZ").center(0, g["port_z"]).circle(s["fit_d"] / 2).circle(s["fit_bore"] / 2) \
            .extrude(s["fit_l"])
        parts[name] = f.translate((xe if sign > 0 else xe - s["fit_l"], 0, 0))
    hx = s["heated_x0"]
    parts["component_top"] = cq.Workplane("XY").box(s["comp_l"], s["comp_w"], s["comp_t"], centered=(False, True, False)) \
        .translate((hx, 0, g["z_top"] + s["cover_t"]))
    parts["component_bottom"] = cq.Workplane("XY").box(s["comp_l"], s["comp_w"], s["comp_t"], centered=(False, True, False)) \
        .translate((hx, 0, g["z_bot"] - s["comp_t"]))
    for name, w in parts.items():
        sol = w.solids().vals()
        if len(sol) != 1 or not sol[0].isValid():
            raise RuntimeError(f"part {name}: {len(sol)} solids or invalid")
    return parts


def hand_volumes(design: str = "study11") -> dict:
    s = DESIGNS[design]
    g = geometry(s)
    a = lambda d: math.pi * d * d / 4  # noqa: E731
    passage = s["pass_l"] * s["pass_w"] * s["pass_h"]
    # each well: a cylinder well_h deep from the top face; the part of it inside the passage's footprint (above z = 0)
    # is already removed by the passage, so count the well below z = 0 plus the part above z = 0 outside the passage
    def well_extra(xw):
        # the well's circle and the passage rectangle: the well is centred well_off beyond the passage end, radius r
        r = s["well_d"] / 2
        d = s["well_off"]
        # area of the circle inside x < 0 side for the upstream well (the passage covers x in [0, pass_l]): the circular
        # segment beyond a chord at distance d from the centre (|y| < pass_w / 2 always holds: r < pass_w / 2)
        seg = r * r * math.acos(min(d / r, 1.0)) - d * math.sqrt(max(r * r - d * d, 0.0)) if d < r else 0.0
        return a(s["well_d"]) * (s["well_h"] - s["pass_h"]) + (a(s["well_d"]) - seg) * s["pass_h"]
    wells = sum(well_extra(xw) for xw in g["well_x"])
    # each port: a cylinder from the base's end to the well's axis, less the part inside the well (a cylinder of the
    # port's section cut by the well's cylinder: computed as the port length to the well's wall plus the lens inside;
    # the drill stops at the well's axis, so inside the well it runs r_w; that part is already removed by the well)
    rw, rp = s["well_d"] / 2, s["port_d"] / 2
    # inside the well, the drilled length along x at offset (y, z) from the port axis is from the well's wall
    # x = sqrt(rw^2 - y^2) to the axis, so the drill's own extra volume is the port's length to the well's centre less
    # the integral over the port's disc of sqrt(rw^2 - y^2): by quadrature
    import numpy as np
    n = 4000
    th = (np.arange(n) + 0.5) * math.pi / n - math.pi / 2
    yy = rp * np.sin(th)
    inside = float(np.sum(2 * rp * rp * np.cos(th) ** 2 * np.sqrt(rw * rw - yy * yy)) * math.pi / n)
    ports = 0.0
    for k, xw in enumerate(g["well_x"]):
        xe = g["x0"] if k == 0 else g["x1"]
        ports += a(s["port_d"]) * abs(xw - xe) - inside
    base = s["base_l"] * s["base_w"] * s["base_t"] - passage - wells - ports
    out = {"base": base, "cover": s["base_l"] * s["base_w"] * s["cover_t"],
           "fitting_in": (a(s["fit_d"]) - a(s["fit_bore"])) * s["fit_l"],
           "component_top": s["comp_l"] * s["comp_w"] * s["comp_t"]}
    out["fitting_out"] = out["fitting_in"]
    out["component_bottom"] = out["component_top"]
    return out


def export(design: str, step: Path) -> dict:
    import cadquery as cq

    parts = build(design)
    colours = {"base": (0.62, 0.66, 0.70), "cover": (0.72, 0.75, 0.78), "component_top": (0.15, 0.35, 0.20),
               "component_bottom": (0.15, 0.35, 0.20)}
    asm = cq.Assembly(name=f"cold_plate_{design}")
    for name, w in parts.items():
        asm.add(w, name=name, color=cq.Color(*colours.get(name, (0.80, 0.65, 0.30))))
    asm.export(str(step), exportType="STEP")
    return {k: float(w.val().Volume()) for k, w in parts.items()}

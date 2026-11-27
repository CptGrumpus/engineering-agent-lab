"""The study-18 nozzle as a detailed assembly in CadQuery: the shell course, the set-in nozzle, its welds, an optional
reinforcing pad with its two fillet welds and tell-tale hole, and a weld-neck flange.

Axes (mm), as models/fea/pressure_vessel.py: the shell along z from -L to L, the nozzle along +x; the analysed model
is the quarter y >= 0, z >= 0 of the same metal (shell, nozzle and weld up to the nozzle end x = Xend).

From the study: shell Ri 500 x 16, nozzle ri 100 x 12, the 10 mm weld fillet (a rolling-ball fillet, as analysed), the
shell course length 2 L = 2000 mm and the nozzle length to Xend. [synthetic]: the pad (400 mm across, 16 mm thick, as
the shell: twice the opening, a usual first choice), its fillet welds (12 mm pad to shell, 10 mm pad to nozzle), the
10 mm tell-tale hole, and the weld-neck flange beyond Xend (a plain synthetic flange, 380 mm across, 12 holes of 25 mm
on a 330 mm circle; not taken from ASME B16.5). The nozzle is set in and bonded to the shell through the wall (a full
penetration weld, not drawn separately: its metal is the shell's and the nozzle's).

Welds are made as the analysed fillet is: the parts are fused, the weld edge is filleted, and the weld is what the
fillet added (filleted union minus the union). Their hand volumes integrate the fillet's cross-section, f^2 (cot(a/2)
- (pi - a) / 2) for a corner of opening angle a, around the saddle curve, where a varies with the angle around the
nozzle: an approximation (the section is taken normal to the nozzle axis, its centroid on the corner line), so the
test holds them to 1 % and not to round-off.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

BASE = {"Ri": 500.0, "t": 16.0, "L": 1000.0, "rni": 100.0, "tn": 12.0, "Ln": 350.0, "rf": 10.0,
        # weld-neck flange beyond the analysed nozzle end [synthetic]
        "neck_len": 40.0, "neck_rise": 10.0, "flange_t": 36.0, "flange_R": 190.0, "bolt_circle_R": 165.0,
        "bolt_hole_d": 25.0, "bolt_holes": 12}
DESIGNS = {
    "t12": BASE | {"pad": False},
    "t12_pad": BASE | {"pad": True, "pad_R": 200.0, "pad_t": 16.0, "weld_pad_shell": 12.0, "weld_pad_nozzle": 10.0,
                       "telltale_d": 10.0},
}


def dims(s: dict) -> dict:
    Ro, rno = s["Ri"] + s["t"], s["rni"] + s["tn"]
    return {"Ro": Ro, "rno": rno, "Xend": Ro + s["Ln"]}


# ---------------------------------------------------------------- hand volumes (quadrature, independent of CadQuery)

def _disk_integral(a: float, g, n: int = 20000) -> float:
    """Integral over the disk rho < a in the (y, z) plane of g(y): with y = a sin(theta), the chord 2 sqrt(a^2 - y^2)
    times g, integrated in theta (a smooth integrand: the midpoint rule converges fast)."""
    th = (np.arange(n) + 0.5) * math.pi / n - math.pi / 2
    y = a * np.sin(th)
    return float(np.sum(2 * a * a * np.cos(th) ** 2 * g(y)) * math.pi / n)


def wall_in_disk(a: float, R1: float, R2: float) -> float:
    """Volume of the cylindrical layer R1 < sqrt(x^2 + y^2) < R2 (axis z, x > 0) over the disk rho < a around the x
    axis (any z centre: the layer does not depend on z)."""
    return _disk_integral(a, lambda y: np.sqrt(R2 * R2 - y * y) - np.sqrt(R1 * R1 - y * y))


def spandrel(alpha: np.ndarray, f: float, m: int = 2000) -> tuple[np.ndarray, np.ndarray]:
    """Area and centroid distance from the first leg of the region between two lines meeting at opening angle alpha
    and the circle of radius f tangent to both (a fillet's section): first leg the line u = 0 along +v, second leg
    along (sin alpha, cos alpha); polygon formula with the arc in m segments."""
    a = np.asarray(alpha, float)[:, None]
    c = 1 / np.tan(a / 2)
    centre = np.concatenate([np.full_like(a, f), f * c], axis=1)[:, :, None]          # (n, 2, 1)
    # the arc from the tangent point on leg 1 (angle pi from the centre) to the one on leg 2 (angle pi + (pi - a))
    t = math.pi + (math.pi - a) * np.linspace(0, 1, m + 1)[None, :]
    arc = centre + f * np.stack([np.cos(t), np.sin(t)], axis=1)                        # (n, 2, m+1)
    zero = np.zeros((len(a), 2, 1))
    P = np.concatenate([zero, arc[:, :, ::-1]], axis=2)    # corner, then T2 -> T1 along the arc (counter-clockwise)
    u, v = P[:, 0, :], P[:, 1, :]
    un, vn = np.roll(u, -1, axis=1), np.roll(v, -1, axis=1)
    cr = u * vn - un * v
    A = cr.sum(axis=1) / 2
    uc = ((u + un) * cr).sum(axis=1) / (6 * A)
    return np.abs(A), uc


def fillet_ring(rho: float, R: float, f: float, n: int = 4000) -> float:
    """A rolling-ball fillet of radius f in the corner between the cylinder rho (axis x) and the cylinder R (axis z),
    outside both, by Pappus in each meridional plane of the nozzle: V = integral of A(phi) rho_c(phi) d phi (exact for
    any solid), with A the section in the plane at angle phi around the nozzle axis and rho_c its centroid's distance
    from the axis. The section is taken as the spandrel of a circle of radius f tangent to the nozzle's wall and to the
    shell's surface line at the corner, which opens at alpha = pi/2 + atan(rho cos^2 phi / x), x = sqrt(R^2 - rho^2
    cos^2 phi): the approximation is the surface's curvature across the fillet and the ball's section off its normal
    plane."""
    phi = (np.arange(n) + 0.5) * 2 * math.pi / n
    c2 = np.cos(phi) ** 2
    alpha = math.pi / 2 + np.arctan(rho * c2 / np.sqrt(R * R - rho * rho * c2))
    A, uc = spandrel(alpha, f)
    return float(np.sum(A * (rho + uc)) * 2 * math.pi / n)


def flange_volume(s: dict) -> float:
    """The weld-neck flange: a revolved polygon (Pappus, exact) less its bolt holes (straight through flat faces)."""
    d = dims(s)
    r0, r1, r2, R = s["rni"], d["rno"], d["rno"] + s["neck_rise"], s["flange_R"]
    x0, x1, x2 = 0.0, s["neck_len"], s["neck_len"] + s["flange_t"]
    poly = [(r0, x0), (r1, x0), (r2, x1), (R, x1), (R, x2), (r0, x2)]   # (radius, axial)
    A = Cr = 0.0
    for (ra, xa), (rb, xb) in zip(poly, poly[1:] + poly[:1]):
        cr = ra * xb - rb * xa
        A += cr / 2
        Cr += (ra + rb) * cr / 6
    vol = 2 * math.pi * abs(Cr)          # Pappus: 2 pi x (first moment about the axis)
    return vol - s["bolt_holes"] * math.pi * s["bolt_hole_d"] ** 2 / 4 * s["flange_t"]


def hand_volumes(design: str) -> dict:
    s = DESIGNS[design]
    d = dims(s)
    Ri, Ro, L, rni, rno, Xend = s["Ri"], d["Ro"], s["L"], s["rni"], d["rno"], d["Xend"]
    shell = math.pi * (Ro ** 2 - Ri ** 2) * 2 * L - wall_in_disk(rno, Ri, Ro)
    # the nozzle from the shell's bore to Xend: the annulus times Xend less the bore's x under it
    nozzle = (math.pi * (rno ** 2 - rni ** 2) * Xend
              - (_disk_integral(rno, lambda y: np.sqrt(Ri * Ri - y * y))
                 - _disk_integral(rni, lambda y: np.sqrt(Ri * Ri - y * y))))
    out = {"shell": shell, "nozzle": nozzle, "flange": flange_volume(s)}
    if not s["pad"]:
        out["weld_nozzle"] = fillet_ring(rno, Ro, s["rf"])
        return out
    Rp, tp = s["pad_R"], s["pad_t"]
    out["pad"] = (wall_in_disk(Rp, Ro, Ro + tp) - wall_in_disk(rno, Ro, Ro + tp)
                  - wall_in_disk(s["telltale_d"] / 2, Ro, Ro + tp))
    out["weld_pad_nozzle"] = fillet_ring(rno, Ro + tp, s["weld_pad_nozzle"])
    out["weld_pad_shell"] = fillet_ring(Rp, Ro, s["weld_pad_shell"])
    return out


# ---------------------------------------------------------------------------------------------------------- CadQuery

def _saddle_edges(solid, rho: float, R: float, tol: float = 1e-3):
    """Edges of solid lying on both the cylinder rho about x and the cylinder R about z (a weld's corner line)."""
    def on_both(e):
        pts = [e.positionAt(k / 8) for k in range(9)]
        return all(abs(math.hypot(q.x, q.y) - R) < tol * R and abs(math.hypot(q.y, q.z) - rho) < tol * rho
                   for q in pts)
    edges = [e for e in solid.Edges() if on_both(e)]
    total = sum(e.Length() for e in edges)
    if not edges or not 2 * math.pi * rho <= total <= 1.2 * 2 * math.pi * rho:
        raise RuntimeError(f"weld edge rho={rho} R={R}: {len(edges)} edges, {total:.1f} mm")
    return edges


def build(design: str = "t12") -> dict:
    """{part name: Workplane}; every part a single valid solid."""
    import cadquery as cq

    s = DESIGNS[design]
    d = dims(s)
    Ri, Ro, L, rni, rno, Xend = s["Ri"], d["Ro"], s["L"], s["rni"], d["rno"], d["Xend"]
    zcyl = lambda r, z0, z1: cq.Workplane("XY").workplane(offset=z0).circle(r).extrude(z1 - z0)  # noqa: E731
    xcyl = lambda r, x0, x1: cq.Workplane("YZ").workplane(offset=x0).circle(r).extrude(x1 - x0)  # noqa: E731
    shell = zcyl(Ro, -L, L).cut(zcyl(Ri, -L - 1, L + 1)).cut(xcyl(rno, 0, Ro + 50))
    nozzle = xcyl(rno, 0, Xend).cut(xcyl(rni, -1, Xend + 1)).cut(zcyl(Ri, -L - 1, L + 1))
    parts = {"shell": shell, "nozzle": nozzle}
    if s["pad"]:
        Rp, tp = s["pad_R"], s["pad_t"]
        zt = (rno + Rp) / 2
        pad = (zcyl(Ro + tp, -Rp - 1, Rp + 1).cut(zcyl(Ro, -Rp - 2, Rp + 2))
               .intersect(xcyl(Rp, 0, Ro + tp + 10)).cut(xcyl(rno, 0, Ro + tp + 10))
               .cut(cq.Workplane("YZ").workplane(offset=Ro - 5).center(0, zt).circle(s["telltale_d"] / 2)
                    .extrude(tp + 20)))
        parts["pad"] = pad
    union = shell.union(nozzle)
    if s["pad"]:
        union = union.union(parts["pad"])
    u = union.val()
    if s["pad"]:
        f1 = u.fillet(s["weld_pad_nozzle"], _saddle_edges(u, rno, Ro + s["pad_t"]))
        f2 = f1.fillet(s["weld_pad_shell"], _saddle_edges(f1, s["pad_R"], Ro))
        welds = cq.Workplane("XY").newObject([f2]).cut(union)
        split = xcyl((rno + s["pad_R"]) / 2, 0, Xend)
        parts["weld_pad_nozzle"] = welds.intersect(split)
        parts["weld_pad_shell"] = welds.cut(split)
    else:
        f1 = u.fillet(s["rf"], _saddle_edges(u, rno, Ro))
        parts["weld_nozzle"] = cq.Workplane("XY").newObject([f1]).cut(union)
    # weld-neck flange beyond Xend (butt-welded to the nozzle end) [synthetic]
    r2 = rno + s["neck_rise"]
    x1, x2 = Xend + s["neck_len"], Xend + s["neck_len"] + s["flange_t"]
    prof = (cq.Workplane("XY").moveTo(Xend, rni).lineTo(Xend, rno).lineTo(x1, r2).lineTo(x1, s["flange_R"])
            .lineTo(x2, s["flange_R"]).lineTo(x2, rni).close())
    flange = prof.revolve(360, (0, 0, 0), (1, 0, 0))
    for k in range(s["bolt_holes"]):
        a = 2 * math.pi * (k + 0.5) / s["bolt_holes"]          # holes straddle the centre lines, as usual
        hole = (cq.Workplane("YZ").workplane(offset=x1 - 1)
                .center(s["bolt_circle_R"] * math.cos(a), s["bolt_circle_R"] * math.sin(a))
                .circle(s["bolt_hole_d"] / 2).extrude(s["flange_t"] + 2))
        flange = flange.cut(hole)
    parts["flange"] = flange
    for name, w in parts.items():
        sol = w.solids().vals()
        if len(sol) != 1 or not sol[0].isValid():
            raise RuntimeError(f"{design}: part {name} is {len(sol)} solids or invalid")
    return parts


def analysed_metal(parts: dict) -> float:
    """Volume of the metal the FE model analyses, for the unpadded design: shell, nozzle and weld (the flange lies
    beyond the nozzle end)."""
    return sum(parts[k].val().Volume() for k in ("shell", "nozzle", "weld_nozzle"))


def export(design: str, step: Path) -> dict:
    import cadquery as cq

    parts = build(design)
    colours = {"shell": (0.62, 0.66, 0.70), "nozzle": (0.55, 0.60, 0.66), "pad": (0.70, 0.62, 0.45),
               "flange": (0.45, 0.50, 0.56)}
    asm = cq.Assembly(name=f"vessel_nozzle_{design}")
    for name, w in parts.items():
        c = colours.get(name, (0.85, 0.55, 0.20))                # welds orange
        asm.add(w, name=name, color=cq.Color(*c))
    asm.export(str(step), exportType="STEP")
    return {k: float(w.val().Volume()) for k, w in parts.items()}

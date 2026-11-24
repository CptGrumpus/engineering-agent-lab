"""2D drawings of the parts and models on the portfolio site: dimensioned views, sections and schematics.

    .venv\\Scripts\\python.exe scripts\\make_drawings.py [key ...]

Every dimension, load and material value is read from the study's case file (cases/*.toml) or its recorded
result, so a drawing can't drift from the model it describes. The clevis bracket's views are hidden-line
projections of its CadQuery solid; the motor's cross-section is Pyleecan's own geometry, exported once by
scripts/export_motor_geometry.py (run in the Pyleecan environment). Writes site/v2/dwg_<key>.webp;
site/build_v2.py puts each drawing in its study's model section.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Arc, Circle, Polygon  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
OUT = REPO / "site" / "v2"
INK, DIMC, FILL, CUT, ACC, HOT, PLATE = "#121821", "#5b6672", "#e6ebf2", "#aab6c6", "#1f4e9c", "#a5521c", "#fbfbfa"
plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans"]
U = 1.0            # data units per millimetre of paper, set by new()


def case(name: str) -> dict:
    return tomllib.loads((REPO / "cases" / f"{name}.toml").read_text(encoding="utf-8"))["parameters"]


def new(width_in: float, xlim, ylim):
    """A sheet whose height follows the content, so the drawing is to scale in both directions."""
    global U
    aw, ah = 0.96, 0.86
    h = width_in * aw * (ylim[1] - ylim[0]) / (xlim[1] - xlim[0]) / ah
    fig = plt.figure(figsize=(width_in, h), dpi=200)
    fig.patch.set_facecolor(PLATE)
    ax = fig.add_axes([0.02, 0.11, aw, ah])
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")
    U = (xlim[1] - xlim[0]) / (width_in * 25.4 * aw)
    return fig, ax


def finish(fig, key: str, title: str, units: str = "dimensions in mm"):
    fig.text(0.02, 0.035, title, fontsize=8, color=INK, fontweight="bold")
    fig.text(0.98, 0.035, f"Drawn from the case file's inputs · {units}", fontsize=7, color=DIMC, ha="right")
    fig.add_artist(plt.Line2D([0.02, 0.98], [0.085, 0.085], color=CUT, lw=0.6))
    png = OUT / f"dwg_{key}.png"
    fig.savefig(png, dpi=200, facecolor=PLATE)
    plt.close(fig)
    from PIL import Image
    Image.open(png).convert("RGB").save(OUT / f"dwg_{key}.webp", "WEBP", quality=92, method=6)
    png.unlink()
    print("dwg", key)


def poly(ax, pts, fc=FILL, ec=INK, lw=1.2, hatch=None, z=2, ls="-"):
    if hatch:
        ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=CUT, lw=0, hatch=hatch, zorder=z))
        ax.add_patch(Polygon(pts, closed=True, fc="none", ec=ec, lw=lw, zorder=z + 0.1, ls=ls))
    else:
        ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=ec, lw=lw, zorder=z, ls=ls))


def rect(ax, x0, y0, x1, y1, **kw):
    poly(ax, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], **kw)


def text(ax, x, y, s, fs=7.5, color=DIMC, ha="center", va="center", rot=0, bold=False, box=True):
    ax.text(x, y, s, fontsize=fs, color=color, ha=ha, va=va, rotation=rot, rotation_mode="anchor",
            fontweight="bold" if bold else "normal", zorder=6,
            bbox=dict(fc=PLATE, ec="none", pad=1.0) if box else None)


def dim(ax, p1, p2, off, label=None, fs=7.5, outside=False, tshift=0.0):
    """A dimension between p1 and p2, drawn `off` (data units, signed) to the left of the direction p1 -> p2."""
    p1, p2 = np.array(p1, float), np.array(p2, float)
    d = p2 - p1
    L = float(np.hypot(*d))
    u, n = d / L, np.array([-d[1], d[0]]) / L
    a, b = p1 + n * off, p2 + n * off
    s = np.sign(off) or 1.0
    for p, q in ((p1, a), (p2, b)):
        ax.plot(*zip(p + n * s * 0.8 * U, q + n * s * 1.2 * U), color=DIMC, lw=0.55, zorder=4)
    kw = dict(arrowstyle="-|>", color=DIMC, lw=0.6, mutation_scale=6, shrinkA=0, shrinkB=0)
    ang = np.degrees(np.arctan2(u[1], u[0]))
    if ang > 90 or ang <= -90:
        ang += 180
    lab = f"{L:g}" if label is None else label
    if outside:                                     # a small gap: arrows from outside, the label beside it
        ax.annotate("", a, a - u * 5 * U, arrowprops=kw, zorder=4)
        ax.annotate("", b, b + u * 5 * U, arrowprops=kw, zorder=4)
        ax.plot(*zip(a, b), color=DIMC, lw=0.55, zorder=4)
        m = b + u * (6 * U + tshift)
        text(ax, m[0], m[1], lab, fs=fs, ha="left" if abs(u[0]) > 0.5 else "center",
             va="center" if abs(u[0]) > 0.5 else "bottom", rot=0)
    else:
        ax.annotate("", a, b, arrowprops=dict(kw, arrowstyle="<|-|>"), zorder=4)
        m = (a + b) / 2 + u * tshift
        text(ax, m[0], m[1], lab, fs=fs, rot=ang)


def force(ax, tail, head, label="", ha="left", va="center", color=ACC, dx=0.0, dy=0.0, fs=8, lw=1.5):
    ax.annotate("", head, tail, arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, mutation_scale=11,
                                                 shrinkA=0, shrinkB=0), zorder=5)
    if label:
        text(ax, tail[0] + dx, tail[1] + dy, label, fs=fs, color=color, ha=ha, va=va, bold=True)


def note(ax, xy, xytext, s, ha="left", va="center", color=DIMC, fs=7.5):
    ax.annotate(s, xy, xytext, fontsize=fs, color=color, ha=ha, va=va, zorder=6,
                arrowprops=dict(arrowstyle="-", color=color, lw=0.55, shrinkA=2, shrinkB=0),
                bbox=dict(fc=PLATE, ec="none", pad=1.0))
    ax.add_patch(Circle(xy, 0.5 * U, fc=color, ec="none", zorder=6))


def wall(ax, p1, p2, side=1.0, ticks=None):
    """A fixed support along p1 -> p2: a heavy line with ground hatching on its left (side = 1) or right."""
    p1, p2 = np.array(p1, float), np.array(p2, float)
    d = p2 - p1
    L = float(np.hypot(*d))
    u, n = d / L, np.array([-d[1], d[0]]) / L * side
    ax.plot(*zip(p1, p2), color=INK, lw=2.2, zorder=5, solid_capstyle="butt")
    k = ticks or max(4, int(L / (2.2 * U)))
    for t in np.linspace(0, L, k + 1):
        a = p1 + u * t
        ax.plot(*zip(a, a + (n + u * 0.7) * 2.6 * U), color=INK, lw=0.6, zorder=4)


def centre(ax, p1, p2):
    ax.plot(*zip(p1, p2), color=DIMC, lw=0.6, ls=(0, (9, 3, 2, 3)), zorder=3)


def spring(ax, p1, p2, n=6, w=None, color=INK):
    p1, p2 = np.array(p1, float), np.array(p2, float)
    d = p2 - p1
    L = float(np.hypot(*d))
    u, nn = d / L, np.array([-d[1], d[0]]) / L
    w = w or 0.09 * L
    pts = [p1, p1 + u * 0.15 * L]
    for k in range(2 * n):
        pts.append(p1 + u * (0.15 + 0.7 * (k + 0.5) / (2 * n)) * L + nn * w * (1 if k % 2 == 0 else -1))
    pts += [p1 + u * 0.85 * L, p2]
    ax.plot(*zip(*pts), color=color, lw=1.2, zorder=4, solid_joinstyle="miter")


def damper(ax, p1, p2, w=None, color=INK):
    p1, p2 = np.array(p1, float), np.array(p2, float)
    d = p2 - p1
    L = float(np.hypot(*d))
    u, nn = d / L, np.array([-d[1], d[0]]) / L
    w = w or 0.07 * L
    a, b, c = p1 + u * 0.4 * L, p1 + u * 0.62 * L, p1 + u * 0.52 * L
    ax.plot(*zip(p1, a), color=color, lw=1.2, zorder=4)
    ax.plot(*zip(a - nn * w, a + nn * w), color=color, lw=1.2, zorder=4)             # cylinder end
    for s in (-1, 1):
        ax.plot(*zip(a + nn * w * s, b + nn * w * s), color=color, lw=1.2, zorder=4)  # cylinder walls
    ax.plot(*zip(c - nn * w * 0.7, c + nn * w * 0.7), color=color, lw=1.6, zorder=4)  # piston
    ax.plot(*zip(c, p2), color=color, lw=1.2, zorder=4)


# ---------------------------------------------------------------------------------------- structures

def fea():
    p = case("cantilever_tet10")
    L, h, b = p["length_mm"], p["height_mm"], p["width_mm"]
    fig, ax = new(9, (-40, 300), (-48, 62))
    rect(ax, 0, 0, L, h)
    wall(ax, (0, -14), (0, h + 14), side=1)
    force(ax, (L, h + 30), (L, h + 1), f"{p['tip_load_N'] / 1000:g} kN", ha="left", dx=5)
    dim(ax, (0, 0), (L, 0), -18)
    dim(ax, (L, 0), (L, h), -14)
    text(ax, L / 2, h / 2, f"steel · E {p['youngs_modulus_MPa'] / 1000:g} GPa", fs=7.5, color=INK, box=False)
    text(ax, -9, -30, "root face fixed", ha="center", fs=7)
    rect(ax, 255, 0, 255 + b, h, hatch="////")
    dim(ax, (255, 0), (255 + b, 0), -18)
    text(ax, 255 + b / 2, h + 9, "section", fs=7)
    finish(fig, "fea", "Study 1 · cantilever bracket · side view and section")


def cantilever_opt():
    p = case("bracket_opt")
    rec = json.loads((REPO / "runs/20261120-225744_bracket_opt_confirm/points/p02_element_size_mm-2/point.json").read_text())
    hr, ht = rec["parameters"]["root_height_mm"], rec["parameters"]["tip_height_mm"]
    L, b = p["length_mm"], p["width_mm"]
    fig, ax = new(9, (-40, 300), (-52, 62))
    rect(ax, 0, -12.5, L, 12.5, fc="none", ec=DIMC, lw=0.7, ls=(0, (5, 3)))
    poly(ax, [(0, -hr / 2), (L, -ht / 2), (L, ht / 2), (0, hr / 2)])
    wall(ax, (0, -30), (0, 30), side=1)
    force(ax, (L, 40), (L, ht / 2 + 1), "1 kN", ha="left", dx=5)
    dim(ax, (0, -hr / 2), (L, -hr / 2), -22, f"{L:g}")
    dim(ax, (0, hr / 2), (0, -hr / 2), -14, f"{hr:.1f}")
    dim(ax, (L, -ht / 2), (L, ht / 2), -14, f"{ht:.1f}")
    note(ax, (130, 12.5), (95, 36), "the lightest straight bar that passes: 20 × 25, 785 g", ha="center", va="bottom")
    text(ax, L * 0.42, 0, f"optimised taper · {rec['metrics']['mass_g']:.0f} g", color=INK, box=False)
    rect(ax, 255, -hr / 2, 255 + b, hr / 2, hatch="////")
    dim(ax, (255, -hr / 2), (255 + b, -hr / 2), -22, f"{b:g}")
    text(ax, 255 + b / 2, hr / 2 + 9, "root section", fs=7)
    finish(fig, "cantilever_opt", "Study 1b · the optimised cantilever · side view against the straight bar")


def strap():
    p = case("strap_hole_size")
    L, w, t, d = p["length_mm"], p["width_mm"], p["thickness_mm"], 16.0
    fig, ax = new(9, (-125, 125), (-58, 44))
    rect(ax, -L / 2, -w / 2, L / 2, w / 2)
    rect(ax, 0, 0, L / 2, w / 2, fc="#d3dceb", ec="none", z=2.2)
    ax.add_patch(Circle((0, 0), d / 2, fc=PLATE, ec=INK, lw=1.2, zorder=3))
    centre(ax, (-L / 2 - 8, 0), (L / 2 + 8, 0))
    centre(ax, (0, -w / 2 - 6), (0, w / 2 + 6))
    for s in (-1, 1):
        force(ax, (s * (L / 2 + 2), 0), (s * (L / 2 + 30), 0), "5 kN", ha="center", dx=s * 16, dy=7)
    dim(ax, (-L / 2, w / 2), (L / 2, w / 2), 12)
    dim(ax, (-L / 2, -w / 2), (-L / 2, w / 2), 10)
    note(ax, (d / 2 * 0.71, -d / 2 * 0.71), (34, -30), f"cable hole Ø{d:g} (6 to 18 tried)", va="top")
    text(ax, 52, 11, "quarter modelled", fs=7, color=INK, box=False)
    rect(ax, -L / 2, -50, L / 2, -50 + t, hatch="////")
    dim(ax, (L / 2, -50), (L / 2, -50 + t), -8, f"{t:g}", outside=True)
    text(ax, -L / 2 - 4, -48, "edge", ha="right", fs=7)
    finish(fig, "strap", "Study 2 · strap with a cable hole · plan and edge view")


def modal():
    p = case("bracket_modal_thickness")
    L, w, t = p["length_mm"], p["width_mm"], p["thickness_mm"]
    fig, ax = new(9, (-36, 196), (-52, 46))
    rect(ax, 0, 0, L, w)
    wall(ax, (0, -8), (0, w + 8), side=1)
    dim(ax, (0, w), (L, w), 10)
    dim(ax, (L, 0), (L, w), -12)
    text(ax, L / 2, w / 2, "steel arm · plan view", color=INK, box=False)
    rect(ax, 0, -40, L, -40 + t, hatch="////")
    wall(ax, (0, -48), (0, -24), side=1)
    dim(ax, (L, -40), (L, -40 + t), -12, f"{t:g}", outside=True)
    text(ax, L / 2, -47.5, "side view · 5 to 9 thick tried, 7 chosen", fs=7)
    ax.plot([0, L * 0.5, L], [-36.5, -32, -24], color=ACC, lw=1.1, ls=(0, (4, 2)), zorder=5)
    text(ax, L * 0.74, -22.5, "first mode, flapwise · 261.7 Hz", fs=7, color=ACC)
    finish(fig, "modal", "Study 4 · bracket arm · plan and side view, with the first mode")


def strut():
    p = case("strut_length")
    L, w, t = p["length_mm"], p["width_mm"], p["thickness_mm"]
    fig, ax = new(9, (-90, 690), (-110, 80))
    rect(ax, 0, -t / 2, L, t / 2)
    xs = np.linspace(0, L, 60)
    ax.plot(xs, 40 * L * p["imperfection_over_length"] * np.sin(np.pi * xs / L), color=ACC, lw=1.1, ls=(0, (4, 2)), zorder=5)
    centre(ax, (-20, 0), (L + 20, 0))
    for x, roller in ((0, False), (L, True)):
        poly(ax, [(x, -t / 2), (x - 11, -t / 2 - 18), (x + 11, -t / 2 - 18)], fc=PLATE)
        if roller:
            for dx in (-6, 6):
                ax.add_patch(Circle((x + dx, -t / 2 - 22.5), 4, fc=PLATE, ec=INK, lw=1, zorder=3))
        wall(ax, (x + 16, -t / 2 - (27 if roller else 18)), (x - 16, -t / 2 - (27 if roller else 18)), side=1, ticks=5)
    force(ax, (-62, 0), (-3, 0), "P", ha="center", dy=11, dx=28)
    force(ax, (L + 62, 0), (L + 3, 0), "P", ha="center", dy=11, dx=-28)
    dim(ax, (0, -t / 2 - 50), (L, -t / 2 - 50), -14, f"{L:g}  (400 to 700 tried)")
    dim(ax, (L * 0.3, -t / 2), (L * 0.3, t / 2), 10, f"{t:g}", outside=True)
    note(ax, (L / 2, 20), (L / 2, 52), "initial bow L/1000 = 0.5 mm, a half sine (drawn 40 times larger)", ha="center", va="bottom", color=ACC)
    rect(ax, 615, 28, 615 + w, 28 + t, hatch="////")
    dim(ax, (615, 28 + t), (615 + w, 28 + t), 9, f"{w:g}")
    text(ax, 615 + w / 2, 18, "section", fs=7)
    finish(fig, "strut", "Study 13 · pinned strut with an initial bow · side view and section")


def contact():
    p = case("contact_roller_mesh")
    R, bw, bd = p["roller_radius_mm"], p["block_half_width_mm"], p["block_depth_mm"]
    fig, ax = new(9, (-150, 190), (-78, 132))
    rect(ax, -bw, -bd, bw, 0)
    ax.add_patch(Circle((0, R), R, fc=FILL, ec=INK, lw=1.2, zorder=2))
    th = np.linspace(-np.pi / 2, 0, 40)
    poly(ax, [(0, R)] + [(R * np.cos(a), R + R * np.sin(a)) for a in th] + [(R, R), (0, R)], fc="#d3dceb", ec="none", z=2.2)
    rect(ax, 0, -bd, bw, 0, fc="#d3dceb", ec="none", z=2.2)
    centre(ax, (0, -bd - 10), (0, 2 * R + 14))
    wall(ax, (bw + 6, -bd), (-bw - 6, -bd), side=1)
    force(ax, (0, 2 * R + 26), (0, 2 * R + 1), "500 N per mm of width", ha="left", dx=6)
    dim(ax, (-R, R), (R, R), 0, f"Ø{2 * R:g}", tshift=-22)
    dim(ax, (-bw, -bd), (bw, -bd), -19, f"{2 * bw:g}")
    dim(ax, (-bw, -bd), (-bw, 0), 12, f"{bd:g}")
    text(ax, 30, 62, "half modelled", fs=7, color=INK, box=False)
    ax.add_patch(Circle((0, 0), 7, fc="none", ec=HOT, lw=1, zorder=6))
    cx, cy, r = 138, 38, 44
    ax.add_patch(Circle((cx, cy), r, fc=PLATE, ec=HOT, lw=1, zorder=6))
    ax.plot([5, cx - r * 0.9], [5, cy + r * 0.43], color=HOT, lw=0.6, zorder=5)
    ax.plot([5, cx - r * 0.9], [-5, cy - r * 0.43], color=HOT, lw=0.6, zorder=5)
    k = 26.0                                                # the zoom: 26 times
    xs = np.linspace(-1.55, 1.55, 60)
    ax.fill_between(cx + xs * k, cy - 12, cy - np.sqrt(np.maximum(0, r ** 2 - (xs * k) ** 2)), color=FILL, zorder=6.1, lw=0)
    ax.plot(cx + xs * k, cy - 12 + 0 * xs, color=INK, lw=1, zorder=6.3)
    ax.plot(cx + xs * k, cy - 12 + (xs ** 2) / (2 * R) * k * 14, color=INK, lw=1, zorder=6.3)
    a = 0.526
    ax.plot([cx - a * k, cx + a * k], [cy - 12, cy - 12], color=HOT, lw=2.4, zorder=6.4, solid_capstyle="butt")
    ax.text(cx, cy + 20, "contact strip\n1.05 mm wide", fontsize=7, color=HOT, ha="center", va="center", zorder=7)
    ax.add_patch(Circle((cx, cy - 12 - 0.41 * k), 1.6, fc=HOT, ec="none", zorder=7))
    ax.text(cx + 5, cy - 12 - 0.41 * k, "highest shear,\n0.41 mm down", fontsize=6.5, color=HOT, ha="left", va="center", zorder=7)
    finish(fig, "contact", "Study 10 · roller on a plate · the model and the contact, enlarged")


def bolted_joint():
    p = case("bolted_joint_mesh_r1")
    Ro, rh, rw, t = p["plate_outer_diameter_mm"] / 2, p["hole_diameter_mm"] / 2, p["washer_diameter_mm"] / 2, p["top_thickness_mm"]
    fig, ax = new(9, (-44, 46), (-23, 25))
    for s in (-1, 1):
        rect(ax, s * rh, 0, s * Ro, t, hatch="////")
        rect(ax, s * rh, -t, s * Ro, 0, hatch="\\\\\\\\")
    bolt = dict(fc="none", ec=DIMC, lw=0.7, ls=(0, (4, 2.5)), z=3)
    rect(ax, -4, -t - 6.5, 4, t + 5.3, **bolt)
    rect(ax, -rw, t, rw, t + 5.3, **bolt)
    rect(ax, -rw, -t - 6.5, rw, -t, **bolt)
    centre(ax, (0, -t - 10), (0, t + 9))
    for s in (-1, 1):
        for x in (rh + 0.5, rw - 0.5):
            force(ax, (s * x, t + 4.2), (s * x, t + 0.15), lw=1.1)
            force(ax, (s * x, -t - 4.2), (s * x, -t - 0.15), lw=1.1)
    note(ax, (rw - 0.5, t + 4.2), (11, t + 9.5), f"{p['preload_N'] / 1000:g} kN clamp force on the washer faces (Ø{2 * rw:g})", color=ACC, va="center")
    note(ax, (4, -t - 5), (9, -t - 10.5), "bolt: M8, drawn for reference; represented by its clamp force", va="center")
    force(ax, (-Ro - 13, t / 2), (-Ro - 0.3, t / 2), "side load", ha="center", dy=2.4, dx=6)
    force(ax, (Ro + 13, -t / 2), (Ro + 0.3, -t / 2), "reaction", ha="center", dy=2.4, dx=-6)
    ax.plot([rh, Ro], [0, 0], color=HOT, lw=2, zorder=5, solid_capstyle="butt")
    ax.plot([-Ro, -rh], [0, 0], color=HOT, lw=2, zorder=5, solid_capstyle="butt")
    note(ax, (-15, 0), (-43, -11), f"friction interface, μ = {p['friction_coefficient']:g}", color=HOT, va="center")
    dim(ax, (-Ro, -t), (Ro, -t), -13.5, f"Ø{2 * Ro:g}")
    dim(ax, (-Ro, 0), (-Ro, -t), -3.5, f"{t:g}")
    dim(ax, (Ro, 0), (Ro, t), -3.5, f"{t:g}")
    dim(ax, (-rh, t), (rh, t), 13, f"Ø{2 * rh:g} hole")
    finish(fig, "bolted_joint", "Study 16 · bolted joint · section through the bolt axis")


def pv_nozzle():
    p = case("pv_nozzle_mesh")
    Ri, t, rni, tn = p["shell_inner_radius_mm"], p["shell_thickness_mm"], p["nozzle_inner_radius_mm"], p["nozzle_thickness_mm"]
    Ro, rno, rf, Xe = Ri + t, rni + tn, p["weld_fillet_radius_mm"], Ri + t + p["nozzle_length_mm"]
    zc = 330.0
    fig, ax = new(9, (-470, 470), (395, 935))
    arc = [(rno + rf + rf * np.cos(a), Ro + rf + rf * np.sin(a)) for a in np.radians(np.linspace(270, 180, 14))]
    half = [(rni, Ri), (zc, Ri), (zc, Ro)] + arc + [(rno, Xe), (rni, Xe)]
    for s in (-1, 1):
        poly(ax, [(s * x, y) for x, y in half], hatch="////")
        ax.plot([s * zc, s * zc], [Ri - 9, Ro + 9], color=PLATE, lw=5, zorder=4)            # the shell runs on
        ax.plot([s * zc - 6, s * zc + 6, s * zc - 6, s * zc + 6], np.linspace(Ri - 8, Ro + 8, 4), color=DIMC, lw=0.7, zorder=5)
    centre(ax, (0, Ri - 60), (0, Xe + 25))
    text(ax, 0, Xe + 32, "nozzle axis", fs=7)
    for z in (-250, -170, 170, 250):                        # pressure on the wetted faces
        force(ax, (z, Ri - 34), (z, Ri - 2), lw=1.0)
    for y in (620, 720, 820):
        for s in (-1, 1):
            force(ax, (s * (rni - 36), y), (s * (rni - 2), y), lw=1.0)
    text(ax, 0, Ri - 44, f"{p['pressure_MPa']:g} MPa inside", color=ACC, bold=True, fs=8)
    zs = rno + rf                                            # classification lines at the fillet toes
    ax.plot([zs, zs], [Ri, Ro], color=HOT, lw=2.2, zorder=6, solid_capstyle="butt")
    ax.plot([rni, rno], [Ro + rf, Ro + rf], color=HOT, lw=2.2, zorder=6, solid_capstyle="butt")
    note(ax, (zs, Ri + t / 2), (205, 590), "line at the weld toe, through the shell:\nPL 205.1 MPa, passes against 207", color=HOT, va="center")
    # the line through the crotch: from the sharp inner corner towards the fillet's centre, ending on the fillet
    c0, cc = np.array([-rni, Ri]), np.array([-(rno + rf), Ro + rf])
    u = (cc - c0) / np.linalg.norm(cc - c0)
    c1 = c0 + u * (np.linalg.norm(cc - c0) - rf)
    ax.plot([c0[0], c1[0]], [c0[1], c1[1]], color=HOT, lw=2.2, zorder=6, solid_capstyle="butt")
    note(ax, tuple((c0 + c1) / 2), (-205, 600), "line through the corner:\nPL 256.7 MPa, fails against 207", color=HOT, ha="right", va="center")
    note(ax, (rni + tn / 2, Ro + rf), (205, 760), "line through the nozzle wall:\nPL 181.7 MPa", color=HOT, va="center")
    note(ax, (rno + 3, Ro + 3), (205, 675), f"weld fillet R{rf:g}, both sides", ha="left")
    note(ax, (-rni, Ri), (-150, 440), "inner corner left sharp", ha="right")
    dim(ax, (-rni, Xe), (rni, Xe), 14, f"Ø{2 * rni:g} bore")
    dim(ax, (-rno, 700), (-rni, 700), 0, f"{tn:g}", outside=True)
    dim(ax, (-290, Ri), (-290, Ro), 0, f"{t:g}", outside=True)
    dim(ax, (-rno, Ro), (-rno, Xe), 62, f"{p['nozzle_length_mm']:g}")
    text(ax, 320, Ri - 44, f"shell bore Ø{2 * Ri:g}", fs=7)
    # key: the whole vessel, with this detail marked
    k, x0, y0 = 0.11, -330, 795
    L = p["shell_half_length_mm"]
    rect(ax, x0 - L * k, y0 - Ro * k, x0 + L * k, y0 + Ro * k, fc=FILL, lw=0.8, z=6)
    rect(ax, x0 - rno * k, y0 + Ro * k, x0 + rno * k, y0 + Xe * k, fc=FILL, lw=0.8, z=6)
    rect(ax, x0 - 470 * k, y0 + 395 * k, x0 + 470 * k, y0 + 935 * k, fc="none", ec=HOT, lw=0.9, z=7)
    text(ax, x0, y0 - Ro * k - 13, f"the vessel as modelled, {2 * L:g} long;\nthis detail is boxed", fs=6.5)
    finish(fig, "pv_nozzle", "Study 18 · nozzle junction · section through both axes")


def hlr(shape, direction):
    """Visible and hidden edges of a CadQuery shape seen along `direction`, as lists of 2D polylines."""
    from cadquery.occ_impl.exporters.svg import getSVG
    svg = getSVG(shape, opts={"projectionDir": direction, "showHidden": True, "showAxes": False, "width": 800, "height": 600})
    groups = re.findall(r'<g\s+stroke="rgb\((\d+),[^>]*>(.*?)</g>', svg, re.S)
    out = {"hidden": [], "visible": []}
    for shade, body in groups:
        key = "visible" if shade == "0" else "hidden"
        for d in re.findall(r'<path d="([^"]+)"', body):
            nums = [float(v) for v in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", d)]
            out[key].append(np.array(nums).reshape(-1, 2))
    return out


def upright(v):
    """Turn a projection by a multiple of 90 degrees so the part's base (its widest feature) is at the bottom:
    the projector's own up direction is arbitrary."""
    best, score = None, -1e9
    for k in range(4):
        c, s = round(np.cos(k * np.pi / 2)), round(np.sin(k * np.pi / 2))
        rot = lambda a: np.column_stack([c * a[:, 0] - s * a[:, 1], s * a[:, 0] + c * a[:, 1]])  # noqa: E731
        pts = rot(np.vstack(v["visible"]))
        y0, y1 = pts[:, 1].min(), pts[:, 1].max()
        low, high = pts[pts[:, 1] < y0 + 0.15 * (y1 - y0)], pts[pts[:, 1] > y1 - 0.15 * (y1 - y0)]
        sc = np.ptp(low[:, 0]) - np.ptp(high[:, 0])
        if sc > score:
            best, score = {key: [rot(a) for a in v[key]] for key in v}, sc
    return best


def bracket_opt():
    sys.path.insert(0, str(REPO / "models" / "fea"))
    import clevis_bracket as cb
    p = case("clevis_confirm_r2b")
    shape = cb.build_solid(p).val()
    views = [("front", (0, -1, 0)), ("side", (1, 0, 0)), ("three-quarter", (1.0, -1.4, 0.9))]
    drawn, x = [], 0.0
    for name, direction in views:
        v = hlr(shape, direction)
        v = upright(v)
        pts = np.vstack(v["visible"])
        lo, hi = pts.min(0), pts.max(0)
        drawn.append((name, v, np.array([x - lo[0], -lo[1]]), hi - lo, x))
        x += hi[0] - lo[0] + 46
    width = x - 46
    fig, ax = new(9.5, (-30, width + 14), (-36, 128))
    for name, v, off, size, left in drawn:
        if name != "three-quarter":
            for ln in v["hidden"]:
                ax.plot(ln[:, 0] + off[0], ln[:, 1] + off[1], color=CUT, lw=0.6, ls=(0, (3, 2)), zorder=2)
        for ln in v["visible"]:
            ax.plot(ln[:, 0] + off[0], ln[:, 1] + off[1], color=INK, lw=1.0, zorder=3, solid_capstyle="round")
        text(ax, left + size[0] / 2, -28, name + " view", fs=7)
    (_, _, _, s1, x1), (_, _, _, s2, x2) = drawn[0], drawn[1]
    Lb, tb, H, R, dp = p["base_length_mm"], p["base_thickness_mm"], p["pin_height_mm"], p["lug_radius_mm"], p["pin_diameter_mm"]
    cx = x1 + s1[0] / 2
    dim(ax, (x1, 0), (x1 + Lb, 0), -11, f"{Lb:g}")
    dim(ax, (x1, 0), (x1, H), 12, f"{H:g} to the pin")
    dim(ax, (cx - R, H + R), (cx + R, H + R), 8, f"{2 * R:g}")
    note(ax, (cx + dp / 2 * 0.7, H + dp / 2 * 0.7), (cx + 30, H + 3), f"pin Ø{dp:g}")
    c2 = x2 + s2[0] / 2
    tl, tg, hg = p["lug_thickness_mm"], p["gusset_thickness_mm"], p["gusset_height_mm"]
    dim(ax, (c2 - tl / 2, H + R), (c2 + tl / 2, H + R), 8, f"lug {tl:.1f}", outside=True)
    dim(ax, (x2 + s2[0], tb), (x2 + s2[0], tb + hg), -9, f"gusset {hg:.1f} high")
    dim(ax, (x2, 0), (x2, tb), 9, f"{tb:g}", outside=True)
    note(ax, (c2 + tl / 2 + 1.2, tb + 1.2), (c2 + 24, 66), f"fillets R{p['fillet_radius_mm']:g}:\nthe stress peaks here", color=HOT)
    force(ax, (cx - 30, H + 40), (cx - 2, H + 3), "4.8 kN on the pin,\ninclined", ha="right", dx=-3, dy=2)
    finish(fig, "bracket_opt", "Study 12 · the optimised clevis bracket (design D) · views from the CAD model")


def cad():
    p = case("mounting_plate")
    L, w, t, r, d = p["length_mm"], p["width_mm"], p["thickness_mm"], p["corner_radius_mm"], p["hole_diameter_mm"]
    px, py = p["hole_pitch_x_mm"], p["hole_pitch_y_mm"]
    fig, ax = new(9, (-100, 112), (-74, 62))
    pts = []
    for cx, cy, a0 in ((L / 2 - r, w / 2 - r, 0), (-L / 2 + r, w / 2 - r, 90), (-L / 2 + r, -w / 2 + r, 180), (L / 2 - r, -w / 2 + r, 270)):
        pts += [(cx + r * np.cos(a), cy + r * np.sin(a)) for a in np.radians(np.linspace(a0, a0 + 90, 10))]
    poly(ax, pts)
    for i in (-1, 0, 1):
        for j in (-0.5, 0.5):
            ax.add_patch(Circle((i * px, j * py), d / 2, fc=PLATE, ec=INK, lw=1.1, zorder=3))
            ax.plot([i * px - 7, i * px + 7], [j * py, j * py], color=DIMC, lw=0.5, zorder=4)
            ax.plot([i * px, i * px], [j * py - 7, j * py + 7], color=DIMC, lw=0.5, zorder=4)
    dim(ax, (-L / 2, w / 2), (L / 2, w / 2), 12)
    dim(ax, (L / 2, -w / 2), (L / 2, w / 2), -12)
    dim(ax, (-px, py / 2), (0, py / 2), 9, f"{px:g}")
    dim(ax, (-px, -py / 2), (-px, py / 2), 12, f"{py:g}")
    edge = w / 2 - py / 2
    dim(ax, (px, -w / 2), (px, -py / 2), -9, f"{edge:g}")
    text(ax, px + 8, -w / 2 - 7, f"edge distance {edge:g} = {edge / d:.2f} × the hole size", fs=7)
    note(ax, (px + d / 2 * 0.7, py / 2 + d / 2 * 0.7), (70, 52), f"6 holes Ø{d:g} (M8 clearance)", ha="center", va="bottom")
    note(ax, (-L / 2 + r * 0.3, -w / 2 + r * 0.3), (-84, -52), f"R{r:g}", ha="right")
    rect(ax, -L / 2, -66, L / 2, -66 + t, hatch="////")
    dim(ax, (L / 2, -66), (L / 2, -66 + t), -9, f"{t:g}", outside=True)
    finish(fig, "cad", "Study 8 · parametric mounting plate · plan and edge view (the 9 mm hole size)")


# ---------------------------------------------------------------------------------------- thermal, fluids

def cfd():
    p = case("channel_header_tolerance")
    g, L, hs, ls, lc = p["gap_mm"], p["length_mm"], p["supply_height_mm"], p["supply_length_mm"], p["contraction_length_mm"]
    k = 2.5                                                   # heights drawn 2.5 times larger
    fig, ax = new(9, (-10.5, 23.5), (-8.2, 8.4))
    xs = np.linspace(-lc, 0, 30)
    hh = (g + (hs - g) * 0.5 * (1 - np.cos(np.pi * (-xs) / lc))) / 2 * k
    top = [(-ls - lc, hs / 2 * k)] + list(zip(xs, hh)) + [(L, g / 2 * k)]
    ax.fill([q[0] for q in top] + [L, -ls - lc], [q[1] for q in top] + [-g / 2 * k, -hs / 2 * k], color="#dbe7f6", zorder=1, lw=0)
    ax.fill([q[0] for q in top[::-1]] + [-ls - lc], [-q[1] for q in top[::-1]] + [-hs / 2 * k], color="#dbe7f6", zorder=1, lw=0)
    for s in (1, -1):
        xy = [(q[0], s * q[1]) for q in top]
        poly(ax, xy + [(L, s * (hs / 2 * k + 1.4)), (-ls - lc, s * (hs / 2 * k + 1.4))], hatch="////", lw=1.1)
    rect(ax, p["window_start_mm"], -g / 2 * k, p["window_end_mm"], g / 2 * k, fc="#bcd0ee", ec="none", z=1.5)
    text(ax, (p["window_start_mm"] + p["window_end_mm"]) / 2, 0, "measured here", fs=6.5, color=INK, box=False)
    force(ax, (-9.8, 0), (-6.6, 0), "water in", ha="left", dy=1.3, dx=-0.3)
    force(ax, (L + 0.3, 0), (L + 3, 0), "out", ha="center", dy=1.3, dx=1.3)
    dim(ax, (0, -hs / 2 * k - 1.4), (L, -hs / 2 * k - 1.4), -1.6, f"channel {L:g}")
    dim(ax, (-lc, -hs / 2 * k - 1.4), (0, -hs / 2 * k - 1.4), -1.6, f"{lc:g}")
    dim(ax, (-ls - lc, -hs / 2 * k - 1.4), (-lc, -hs / 2 * k - 1.4), -1.6, f"{ls:g}")
    dim(ax, (L * 0.22, -g / 2 * k), (L * 0.22, g / 2 * k), 0, f"gap {g:g} (0.95 to 1.05)", outside=True)
    dim(ax, (-ls - lc + 0.9, -hs / 2 * k), (-ls - lc + 0.9, hs / 2 * k), 0, f"{hs:g}")
    text(ax, -4.6, hs / 2 * k + 2.7, "supply header and\nsmooth contraction", fs=7)
    finish(fig, "cfd", "Study 5 · coolant channel · the 2D flow domain", "dimensions in mm, heights drawn 2.5 times larger")


def thermal():
    p = case("fin_tolerance")
    L, w, t = p["length_mm"], p["width_mm"], p["thickness_mm"]
    fig, ax = new(9, (-58, 82), (-17, 55))
    for x0, ww, lab in ((-28, w, "front"), (34, t, "side")):
        rect(ax, x0 - 7, -8, x0 + ww + 7, 0, hatch="////")
        rect(ax, x0, 0, x0 + ww, L)
        text(ax, x0 + ww / 2, -12.5, lab, fs=7)
    dim(ax, (-28, L), (-28 + w, L), 5, f"{w:g}")
    dim(ax, (-28, 0), (-28, L), 6, f"{L:g}")
    dim(ax, (34, L), (34 + t, L), 5, f"{t:g}", outside=True)
    text(ax, -18, -4, f"base held at {p['base_temperature_C']:g} °C", fs=7, color=INK, box=True)
    for y in (8, 20, 32):
        for x0, x1 in ((34 + t + 1.2, 34 + t + 9), (33, 25.2)):
            ax.annotate("", (x1, y + 2.5), (x0, y), arrowprops=dict(arrowstyle="-|>", color=ACC, lw=1, mutation_scale=8,
                                                                    connectionstyle="arc3,rad=0.35"), zorder=5)
    text(ax, 58, 21, f"heat lost to air at {p['air_temperature_C']:g} °C\nfrom every exposed face,\n{p['htc_W_per_m2K']:g} W/m²K", fs=7, color=ACC, ha="left")
    note(ax, (-28 + w / 2, L - 0.6), (-40, L + 9), "tip: 73.2 °C against a 60 °C minimum", ha="center", va="bottom", color=HOT)
    text(ax, -18, L / 2, f"6061 aluminium\n{p['conductivity_W_per_mK']:g} W/mK", fs=7, color=INK, box=False)
    finish(fig, "thermal", "Study 6 · heat-sink fin · front and side view")


def _channel(ax, x0, x1, g, k, fc="#dbe7f6"):
    ax.fill([x0, x1, x1, x0], [-g / 2 * k, -g / 2 * k, g / 2 * k, g / 2 * k], color=fc, zorder=1, lw=0)


def heat():
    p = case("heated_channel_mesh_r2")
    g, Lh, Le, Lx = p["gap_mm"], p["heated_length_mm"], p["entry_length_mm"], p["exit_length_mm"]
    k = 5.0
    fig, ax = new(9, (-17, 73), (-17, 19))
    _channel(ax, -Le, Lh + Lx, g, k)
    for s in (1, -1):
        y0 = s * g / 2 * k
        rect(ax, -Le, min(y0, y0 + s * 2.2), Lh + Lx, max(y0, y0 + s * 2.2), hatch="////", lw=1.0)
        ax.plot([0, Lh], [y0, y0], color=HOT, lw=2.4, zorder=5, solid_capstyle="butt")
        for x in np.linspace(4, Lh - 4, 8):
            force(ax, (x, s * (g / 2 * k + 7)), (x, s * (g / 2 * k + 2.4)), color=HOT, lw=1.0)
    text(ax, Lh / 2, g / 2 * k + 9.5, f"{p['wall_heat_flux_W_per_m2'] / 1000:g} kW/m² into both walls", color=HOT, bold=True, fs=8)
    force(ax, (-15.5, 0), (-6, 0), f"water, {p['inlet_temperature_C']:g} °C,\n{p['mean_velocity_m_per_s']:g} m/s", ha="left", dy=5.2, dx=-1)
    force(ax, (Lh + Lx + 1, 0), (Lh + Lx + 9, 0))
    dim(ax, (0, -g / 2 * k - 2.2), (Lh, -g / 2 * k - 2.2), -9.2, f"heated {Lh:g}")
    dim(ax, (-Le, -g / 2 * k - 2.2), (0, -g / 2 * k - 2.2), -9.2, f"{Le:g}")
    dim(ax, (Lh, -g / 2 * k - 2.2), (Lh + Lx, -g / 2 * k - 2.2), -9.2, f"{Lx:g}")
    dim(ax, (Lh * 0.5, -g / 2 * k), (Lh * 0.5, g / 2 * k), 0, f"gap {g:g}")
    note(ax, (Lh, g / 2 * k), (Lh + 3, g / 2 * k + 12.5), "hottest point on the wall:\n44.03 °C against 45", color=INK, ha="left")
    finish(fig, "heat", "Study 11 · heated coolant channel · the 2D model", "dimensions in mm, heights drawn 5 times larger")


def cold_plate():
    p = case("cold_plate_mesh_r1")
    g, Lf, Le, Lx, Lu, tp = (p[k] for k in ("gap_mm", "footprint_length_mm", "entry_length_mm", "exit_length_mm",
                                             "unplated_length_mm", "plate_thickness_mm"))
    k = 3.0
    fig, ax = new(9, (-24, 82), (-23, 25))
    _channel(ax, -Le - Lu, Lf + Lx + Lu, g, k)
    for s in (1, -1):
        y0, y1 = s * g / 2 * k, s * (g / 2 + tp) * k
        rect(ax, -Le, min(y0, y1), Lf + Lx, max(y0, y1), hatch="////", lw=1.1)
        ax.plot([0, Lf], [y1, y1], color=HOT, lw=2.4, zorder=5, solid_capstyle="butt")
        for x in np.linspace(4, Lf - 4, 8):
            force(ax, (x, y1 + s * 5.5), (x, y1 + s * 0.4), color=HOT, lw=1.0)
        for x, d in ((-Le, 1), (Lf + Lx, -1)):
            wall(ax, (x, min(y0, y1)), (x, max(y0, y1)), side=d, ticks=4)
    text(ax, Lf / 2, (g / 2 + tp) * k + 8.2, f"{p['component_heat_flux_W_per_m2'] / 1000:g} kW/m² from the components, over the footprint", color=HOT, bold=True, fs=8)
    force(ax, (-22, 0), (-11.5, 0), "water,\n25 °C", ha="left", dy=4.4, dx=-1)
    force(ax, (Lf + Lx + Lu + 1, 0), (Lf + Lx + Lu + 9, 0))
    yb = -(g / 2 + tp) * k
    dim(ax, (0, yb), (Lf, yb), -10.5, f"footprint {Lf:g}")
    dim(ax, (-Le, yb), (0, yb), -10.5, f"{Le:g}")
    dim(ax, (Lf, yb), (Lf + Lx, yb), -10.5, f"{Lx:g}")
    dim(ax, (Lf * 0.72, g / 2 * k), (Lf * 0.72, (g / 2 + tp) * k), 0, f"plate {tp:g}", outside=True)
    dim(ax, (Lf * 0.3, -g / 2 * k), (Lf * 0.3, g / 2 * k), 0, f"gap {g:g}")
    note(ax, (Lf + Lx, (g / 2 + tp / 2) * k), (Lf + Lx + 4, 17), "plate ends held rigidly,\nassembled at 20 °C", ha="left")
    text(ax, Lf * 0.2, (g / 2 + tp / 2) * k, "6061-T6 plate", fs=7, color=INK, box=True)
    finish(fig, "cold_plate", "Study 15 · cold plate on its coolant channel · the 2D model", "dimensions in mm, heights drawn 3 times larger")


def pipe():
    p = case("pipe_rans_mesh_r3")
    R = p["diameter_m"] * 500
    fig, ax = new(9, (-70, 200), (-66, 66))
    ax.add_patch(Circle((0, 0), R, fc="#dbe7f6", ec=INK, lw=1.3, zorder=2))
    a = np.radians(2.5)
    poly(ax, [(0, 0), (R * np.cos(a), R * np.sin(a)), (R * np.cos(a), -R * np.sin(a))], fc=ACC, ec=ACC, lw=0.6, z=3)
    centre(ax, (-R - 8, 0), (R + 8, 0))
    centre(ax, (0, -R - 8), (0, R + 8))
    dim(ax, (-R, -R), (R, -R), -9, f"Ø{2 * R:g} bore")
    note(ax, (R * 0.75, 0), (30, 40), "the 5° wedge that is modelled", color=ACC, va="bottom", ha="center")
    # the wedge, enlarged and widened: radial cells graded towards the wall
    x0, x1, hh = 84, 190, 26
    poly(ax, [(x0, 0), (x1, hh), (x1, -hh)], fc="#dbe7f6", lw=1.1)
    rs = 1 - np.geomspace(1, 0.004, 15)
    rs = rs / rs[-1]
    for r in rs[1:-1]:
        x = x0 + (x1 - x0) * r
        ax.plot([x, x], [-hh * r, hh * r], color=INK, lw=0.45, zorder=3)
    ax.plot([x1, x1], [-hh, hh], color=INK, lw=2.2, zorder=5, solid_capstyle="butt")
    text(ax, x1 + 3, 0, "wall", ha="left", fs=7, color=INK)
    text(ax, x0 - 3, 0, "axis", ha="right", fs=7)
    text(ax, (x0 + x1) / 2, -hh - 12, "cells graded towards the wall: 160, 320 and 640 across the radius,\nthe first one inside the thin viscous layer", fs=7)
    text(ax, (x0 + x1) / 2, hh + 9, "front and back faces joined, so the flow repeats", fs=7, color=ACC)
    finish(fig, "pipe", "Study 19 · turbulent pipe flow · the periodic wedge and its mesh", "dimensions in mm, the wedge drawn wider than 5°")


# ---------------------------------------------------------------------------------------- dynamics

def suspension():
    p = case("qc_speed_bump")
    fig, ax = new(9, (-70, 170), (-22, 108))
    xs = np.linspace(-70, 170, 400)
    bump = np.where((xs > 30) & (xs < 110), 7 * (1 - np.cos(2 * np.pi * (xs - 30) / 80)) / 2, 0)
    ax.fill_between(xs, -22, bump - 10, color=FILL, zorder=1, lw=0)
    ax.plot(xs, bump - 10, color=INK, lw=1.2, zorder=2)
    rect(ax, -22, 70, 22, 96)
    text(ax, 0, 83, f"body\n{p['sprung_mass_kg']:g} kg", color=INK, box=False, fs=8)
    rect(ax, -15, 24, 15, 40)
    text(ax, 0, 32, f"wheel {p['unsprung_mass_kg']:g} kg", color=INK, box=False, fs=7)
    spring(ax, (-9, 40), (-9, 70), n=5, w=4)
    damper(ax, (9, 40), (9, 70), w=3.2)
    spring(ax, (0, -10), (0, 24), n=4, w=4)
    text(ax, -17, 55, f"spring\n{p['suspension_stiffness_N_per_m'] / 1000:g} kN/m", ha="right", fs=7)
    text(ax, 17, 55, "damper\n600 to 3500 N·s/m,\nthe thing being chosen", ha="left", fs=7, color=ACC)
    text(ax, 8, 6, f"tire {p['tire_stiffness_N_per_m'] / 1000:g} kN/m\n(can lift off the road)", ha="left", fs=7)
    force(ax, (-55, 12), (-28, 12), "18 or 36 km/h", ha="left", dy=7, dx=-4)
    dim(ax, (30, -10), (110, -10), -6, f"bump {p['bump_length_m']:g} m long")
    dim(ax, (118, -10), (118, -3), 0, f"{p['bump_height_m'] * 1000:g} mm high", outside=True)
    text(ax, 96, 98, "what is measured", ha="left", fs=7, color=DIMC)
    for y, lab in ((88, "body acceleration ≤ 4.0 m/s²"), (78, "suspension travel ≤ 40 mm"), (68, "tire load within ±70 % of static")):
        ax.plot([88, 94], [y, y], color=HOT, lw=1.6, zorder=5)
        text(ax, 97, y, lab, ha="left", fs=7.5, color=HOT)
    finish(fig, "suspension", "Study 7 · quarter-car model · one corner of the car crossing a speed bump", "a schematic, not to scale")


def baseline():
    p = case("msd_step")
    fig, ax = new(9, (-60, 180), (-30, 56))
    wall(ax, (0, -18), (0, 44), side=1)
    spring(ax, (0, 26), (62, 26), n=6, w=5)
    damper(ax, (0, 2), (62, 2), w=4)
    rect(ax, 62, -10, 102, 38)
    text(ax, 82, 14, f"mass\n{p['mass_kg']:g} kg", color=INK, box=False, fs=8)
    for x in (70, 94):
        ax.add_patch(Circle((x, -14), 4, fc=PLATE, ec=INK, lw=1, zorder=3))
    ax.plot([40, 140], [-18, -18], color=INK, lw=1.2, zorder=2)
    force(ax, (104, 14), (136, 14), f"{p['step_force_N']:g} N, applied suddenly", ha="left", dx=34)
    text(ax, 31, 38, f"spring {p['stiffness_N_per_m']:g} N/m", fs=7)
    text(ax, 31, -9, "damper: six damping ratios, 0.1 to 2.0", fs=7, color=ACC)
    ax.annotate("", (118, 46), (82, 46), arrowprops=dict(arrowstyle="-|>", color=DIMC, lw=0.7, mutation_scale=7))
    text(ax, 124, 46, "x, comes to rest at 10 mm", fs=7, ha="left")
    finish(fig, "baseline", "Study 9 · mass-spring-damper · the system", "a schematic, not to scale")


def motor():
    # the client-data machine (models/motor/Toyota_Prius_ORNL_rev5centre.json): magnet 18.9 x 6.5 mm from the
    # bill of materials, centred in its 6.80 mm pocket
    src = REPO / "build" / "drawings" / "motor_geometry_rev5.json"
    if not src.exists():
        print("skip motor: run scripts/export_motor_geometry.py in the Pyleecan environment first")
        return
    d = json.loads(src.read_text())
    Re = d["Rext"] * 1000
    fig, ax = new(9.5, (-Re - 12, Re * 3.25), (-Re - 12, Re + 12))
    col = {"Stator-0_Lamination": FILL, "Rotor-0_Lamination": "#d3dceb", "Winding": "#d98a4e", "HoleMag": ACC, "HoleVoid": PLATE,
           "Shaft": "#c4cbd6"}

    def draw(ox, oy, k, clip=None, geo=None):
        for s in (geo or d)["surfaces"]:
            pts = np.array(s["pts"]) * 1000 * k + [ox, oy]
            kind = next((v for key, v in col.items() if key in s["label"]), FILL)
            z = 2 if "Lamination" in s["label"] or "Shaft" in s["label"] else 3
            patch = Polygon(pts, closed=True, fc=kind, ec=INK, lw=0.45 if k == 1 else 0.8, zorder=z)
            ax.add_patch(patch)
            if clip is not None:
                patch.set_clip_path(clip)
    draw(0, 0, 1)
    # Pyleecan closes each lamination's outline with a seam along 0 degrees (through a tooth and a pole): hide them
    ax.plot([d["Rbore"] * 1000 + 0.4, Re - 0.4], [0, 0], color=FILL, lw=1.6, zorder=2.5, solid_capstyle="butt")
    ax.plot([d["Rint"] * 1000 + 0.4, d["Rrot"] * 1000 - 0.4], [0, 0], color=col["Rotor-0_Lamination"], lw=1.6, zorder=2.5,
            solid_capstyle="butt")
    ax.add_patch(Circle((0, 0), d["Rint"] * 1000, fc=PLATE, ec=INK, lw=0.6, zorder=4))
    dim(ax, (-Re, -Re), (Re, -Re), -5, f"Ø{2 * Re:.1f}")
    # one pole, enlarged
    f0, f1 = Re * 1.3, Re * 3.2
    ax.add_patch(Polygon([(f0, -Re - 4), (f1, -Re - 4), (f1, Re + 6), (f0, Re + 6)], closed=True, fc=PLATE, ec=CUT, lw=0.8, zorder=1.5))
    k, r0 = 2.25, 50.0
    cx, cy = (f0 + f1) / 2, -8 - k * (r0 * np.cos(np.radians(22.5)) + Re + 1) / 2
    P = lambda r, a: (cx + k * r * np.cos(np.radians(a)), cy + k * r * np.sin(np.radians(a)))  # noqa: E731
    th = np.linspace(67.5, 112.5, 30)
    wedge = Polygon([P(r0, a) for a in th] + [P(Re + 1, a) for a in th[::-1]], closed=True, transform=ax.transData)
    draw(cx, cy, k, clip=wedge)
    ax.add_patch(Polygon([(r0 * np.cos(np.radians(a)), r0 * np.sin(np.radians(a))) for a in th] +
                         [((Re + 1) * np.cos(np.radians(a)), (Re + 1) * np.sin(np.radians(a))) for a in th[::-1]],
                         closed=True, fc="none", ec=HOT, lw=0.9, zorder=6))
    top = P(Re + 1, 90)[1]
    note(ax, P(66, 104), (f0 + 5, P(46, 90)[1]), "magnets in a V,\n18.9 × 6.5 mm in\n6.80 mm pockets", color=ACC, ha="left", va="top")
    note(ax, P(100, 86.25), (f1 - 5, top - 14), "48 slots,\ncopper winding", color="#a8581f", ha="right", va="top")
    note(ax, P(79.0, 72), (f1 - 5, P(64, 90)[1]), "thin steel bridges\nhold the magnets", color=HOT, ha="right")
    note(ax, P(80.6, 104), (f0 + 5, P(92, 90)[1]), "air gap\n0.775 mm", ha="left")
    text(ax, cx, top + 5, "one of eight poles, enlarged", fs=7, va="bottom")
    text(ax, 0, 0, "shaft", fs=7, color=DIMC, box=False)
    finish(fig, "motor", "Study 20 · 2004 Prius traction motor · cross-section, as rebuilt from the published drawings")


# ---------------------------------------------------------------------------------------- study 19 part 2, the step

def step():
    p = case("step_mesh")
    H = p["step_height_m"] * 1000
    hin = p["inlet_height_ratio"]                  # inlet duct height, in step heights
    xr = 6.40                                      # the finest mesh's reattachment length (comparison.json)
    x0, x1 = -7.0, 33.0
    fig, ax = new(9.5, (x0 - 1.5, x1 + 1.5), (-3.2, hin + 2.6))
    # walls: top wall, upstream floor at the step lip (y = 1), the step face, the downstream floor (y = 0)
    ax.fill_between([x0, 0], 1, -0.6, color=FILL, lw=0, zorder=1)
    ax.fill_between([0, x1], 0, -0.6, color=FILL, lw=0, zorder=1)
    ax.fill_between([x0, x1], 1 + hin, 1 + hin + 0.6, color=FILL, lw=0, zorder=1)
    ax.plot([x0, 0, 0, x1], [1, 1, 0, 0], color=INK, lw=1.3, zorder=3)
    ax.plot([x0, x1], [1 + hin, 1 + hin], color=INK, lw=1.3, zorder=3)
    for xb in (x0, x1):                            # the channel carries on beyond the drawing
        ax.plot([xb, xb], [0 if xb > 0 else 1, 1 + hin], color=CUT, lw=0.8, ls=(0, (2, 2)), zorder=2)
    # the flow and the separation bubble
    for y in (3.0, 5.5, 7.5):
        force(ax, (x0 + 0.6, y), (x0 + 3.2, y), "", color=ACC, lw=1.2)
    text(ax, x0 + 0.6, 1 + hin - 0.7, "air, 44.2 m/s", fs=7, ha="left", color=ACC, box=False)
    bx = np.linspace(0, xr, 60)
    ax.plot(bx, 1.0 * np.sqrt(np.clip(1 - (bx / xr) ** 2, 0, 1)) * (1 - 0.15 * bx / xr), color=ACC, lw=1.0, ls=(0, (4, 2)), zorder=4)
    text(ax, xr * 0.42, 0.38, "flow turns back here", fs=6.5, color=ACC, box=False)
    ax.plot([xr], [0], marker="o", ms=4.5, color=HOT, zorder=6)
    note(ax, (xr, 0), (xr + 2.5, 2.4), f"flow reattaches: {xr:.2f} step heights\n(measured 6.26)", color=HOT, ha="left")
    # what is scored
    ax.plot([10, 30], [-1.75, -1.75], color=HOT, lw=2.2, solid_capstyle="butt", zorder=5)
    text(ax, 20, -2.15, "skin friction scored from 10 to 30 step heights", fs=7, color=HOT, va="top", box=False)
    ax.plot([-4, -4], [1, 0.55], color=DIMC, lw=0.8, zorder=5)
    ax.plot([30, 30], [0, -0.45], color=DIMC, lw=0.8, zorder=5)
    text(ax, -4, 1.35, "pressure from −4 H …", fs=6.5, va="bottom", box=False)
    text(ax, 30, 0.35, "… to 30 H", fs=6.5, va="bottom", box=False)
    dim(ax, (0, 0), (0, 1), 1.0, f"step {H:g}", outside=True)
    dim(ax, (x0 + 4.5, 1), (x0 + 4.5, 1 + hin), -0.9, f"{hin:g} H")
    for xt in (0, 10, 20, 30):
        ax.plot([xt, xt], [-0.6, -0.8], color=DIMC, lw=0.6)
        text(ax, xt, -0.95, f"{xt} H", fs=6.5, va="top", box=False)
    text(ax, (x0 + x1) / 2, 1 + hin + 1.4, "inlet 1.15 m upstream of the step · outlet 50 step heights downstream, both off the drawing",
         fs=6.5, box=False)
    finish(fig, "step", "Study 19, part 2 · backward-facing step · the channel, with what is compared",
           "dimensions in mm and step heights (H); heights drawn to scale, the channel cut short")


# ---------------------------------------------------------------------------------------- study 21, random vibration

def random_vib():
    p = case("bracket_random_mesh")
    L, w, t_ = p["length_mm"], p["width_mm"], p["thickness_mm"]
    fig, ax = new(9.5, (-60, 215), (-78, 42))
    # the clamp block on the shaker table, and the arm in side view
    rect(ax, -34, -14, 0, 24, hatch="////")
    rect(ax, -50, -24, 60, -14, fc="#d3dceb")
    text(ax, 5, -19, "shaker table", fs=7, color=INK, box=False)
    rect(ax, 0, 0, L, t_)
    text(ax, 62, t_ + 5, f"steel arm, {L:g} × {w:g} × {t_:g} (side view)", fs=7.5, color=INK, box=False, va="bottom")
    dim(ax, (0, 0), (L, 0), -10)
    dim(ax, (L, 0), (L, t_), -12, f"{t_:g}", outside=True)
    # the tip clearance
    ax.plot([L - 14, L], [t_ + 6, t_ + 6], color=HOT, lw=1.0, ls=(0, (3, 2)), zorder=5)
    text(ax, L - 16, t_ + 6, "tip may move 1 mm (3-sigma,\ndrawn 6× larger)", fs=7, color=HOT, ha="right")
    # hot-spot read points beside the clamp
    note(ax, (2, t_), (40, 30), "stress read at 0.4 and 1.0 × the thickness\nfrom the clamp and extrapolated to it", ha="left")
    # the input: shaken on each axis in turn
    ox, oy = -40, -56
    force(ax, (ox, oy), (ox, oy + 20), "", color=ACC)
    force(ax, (ox, oy), (ox + 22, oy), "", color=ACC)
    ax.add_patch(Circle((ox, oy), 2.2, fc=PLATE, ec=ACC, lw=1.2, zorder=6))
    ax.plot([ox], [oy], marker="o", ms=1.6, color=ACC, zorder=7)
    text(ax, ox + 3, oy + 19, "z, flapwise", fs=7.5, color=ACC, ha="left", box=False, bold=True)
    text(ax, ox + 25, oy, "x, along the arm", fs=7.5, color=ACC, ha="left", box=False, bold=True)
    text(ax, ox + 3, oy - 5, "y, sideways (out of the page)", fs=7.5, color=ACC, ha="left", va="top", box=False, bold=True)
    text(ax, -50, -72, "shaken on one axis at a time, one hour each", fs=7, ha="left", va="center", box=False)
    # the input spectrum, inset
    gx0, gx1, gy0, gy1 = 105, 205, -70, -26
    rect(ax, gx0, gy0, gx1, gy1, fc=PLATE, ec=CUT, lw=0.8)
    fx = lambda f: gx0 + 8 + (gx1 - gx0 - 16) * (np.log10(f) - 1) / 2.5          # noqa: E731
    ax.plot([fx(20), fx(20), fx(2000), fx(2000)], [gy0 + 6, gy0 + 26, gy0 + 26, gy0 + 6], color=ACC, lw=1.4, zorder=4)
    ax.plot([gx0 + 6, gx1 - 6], [gy0 + 6, gy0 + 6], color=DIMC, lw=0.6)
    text(ax, (gx0 + gx1) / 2, gy0 + 30, "input: flat 0.04 g²/Hz, about 8.9 g rms", fs=7, color=ACC, va="bottom", box=False)
    text(ax, fx(20), gy0 + 3, "20 Hz", fs=6.5, va="top", box=False)
    text(ax, fx(2000), gy0 + 3, "2,000 Hz", fs=6.5, va="top", box=False)
    finish(fig, "random_vib", "Study 21 · bracket arm on a shaker table · the test and what is measured",
           "dimensions in mm, the clamp and table schematic")


def fan_rotor():
    p = case("rotor_fan_design")
    L = p["bearing_span_m"] * 1000
    R, W = p["disc_diameter_m"] * 500, p["disc_width_m"] * 1000
    d = 50.0                                               # as drawn; 60 and 65 are the sweep's other shafts
    rho, E = p["density_kg_per_m3"], p["youngs_modulus_Pa"]
    m_disc = rho * np.pi * ((R / 1000) ** 2 - (d / 2000) ** 2) * W / 1000
    fig, ax = new(9.5, (-170, 1170), (-610, 290))
    # shaft, impeller, centre line
    centre(ax, (-60, 0), (L + 60, 0))
    rect(ax, 0, -d / 2, L, d / 2)
    rect(ax, L / 2 - W / 2, -R, L / 2 + W / 2, R, hatch="////")
    note(ax, (L / 2 - W / 2, 120), (250, 165), f"impeller: a steel disc, about {m_disc:.0f} kg,\nwith the blades lumped in", ha="right")
    note(ax, (300, d / 2), (300, 85), "shaft Ø50 as drawn;\nØ60 and Ø65 also run", ha="center", va="bottom")
    # the unbalance on the disc
    ax.add_patch(Circle((L / 2, R - 22), 9, fc=HOT, ec="none", zorder=6))
    text(ax, L / 2 + 30, R - 22, "unbalance 84 to 106 g·mm\n(API 684's standard amount)", ha="left", fs=7.5, color=HOT)
    # bearings on their pedestals: a spring and a damper to ground at each end
    for x in (0, L):
        rect(ax, x - 32, -d / 2 - 22, x + 32, d / 2 + 22, fc="#d3dceb")
        spring(ax, (x - 16, -d / 2 - 22), (x - 16, -195), n=5, w=11)
        damper(ax, (x + 16, -d / 2 - 22), (x + 16, -195), w=9)
        wall(ax, (x - 48, -195), (x + 48, -195), side=-1)
    text(ax, 55, -125, "bearing and pedestal:\nspring 10⁷ to 10⁸ N/m (not known well),\ndamper 500 N·s/m", ha="left", fs=7.5)
    # rotation, seen side-on
    cx = L + 75
    ax.add_patch(Arc((cx, 0), 34, 120, theta1=40, theta2=320, color=ACC, lw=1.2, zorder=5))
    t2 = np.radians(320)
    ax.annotate("", (cx + 17 * np.cos(t2) + 4, 60 * np.sin(t2) + 6), (cx + 17 * np.cos(t2), 60 * np.sin(t2)),
                arrowprops=dict(arrowstyle="-|>", color=ACC, lw=1.2, mutation_scale=9), zorder=5)
    text(ax, cx, 85, "1,000 to\n3,000 rpm", fs=7.5, color=ACC, bold=True, va="bottom")
    # dimensions
    dim(ax, (0, -215), (L, -215), -30)
    dim(ax, (0, R), (L / 2 - W / 2, R), 35, f"{L / 2 - W / 2:g}")
    dim(ax, (L / 2 + W / 2, -R), (L / 2 + W / 2, R), -150, f"Ø{2 * R:g}", tshift=-110)
    dim(ax, (L / 2 - W / 2, -R), (L / 2 + W / 2, -R), -22, f"{W:g}", outside=True)
    # inset: the bent shape under the disc's weight, near enough the first mode's shape, for the 65 mm shaft
    I = np.pi * 0.065 ** 4 / 64
    xs = np.linspace(0, L, 201) / 1000
    Lm = L / 1000
    xm = np.minimum(xs, Lm - xs)
    bend = xm * (3 * Lm ** 2 - 4 * xm ** 2) / (48 * E * I)         # per newton at mid-span
    y0, A, x0 = -470, 95, 0
    centre(ax, (-40, y0), (L + 40, y0))
    text(ax, -150, y0 + 120, "How the 65 mm shaft bends in its first mode (approximately; drawn exaggerated):",
         ha="left", fs=7.5, color=INK, bold=True, box=False)
    for i, (k, col, ls, lab) in enumerate(((1e7, ACC, "-", "soft pedestals, 10⁷ N/m"), (1e8, DIMC, (0, (5, 3)), "stiff pedestals, 10⁸ N/m"))):
        end = 1 / (2 * k)
        y = (bend + end) / (bend.max() + end)
        ax.plot(x0 + xs * 1000, y0 - A * y, color=col, lw=1.6, ls=ls, zorder=5)
        f = end / (bend.max() + end)
        ky = y0 + 75 - 32 * i                              # a key above the curves
        ax.plot([0, 60], [ky, ky], color=col, lw=1.6, ls=ls, zorder=5)
        text(ax, 75, ky, f"{lab}: the ends move {100 * f:.0f} % as much as the middle", ha="left", fs=7.5, color=col, box=False)
    for x in (0, L):
        ax.plot([x], [y0], marker="^", ms=6, color=INK, zorder=6)
    text(ax, L / 2, y0 - A - 30, "On soft pedestals the whole shaft moves, so more of its mass takes part and the critical speed drops.",
         fs=7, va="top", box=False)
    finish(fig, "fan_rotor", "Study 23 · centre-hung fan rotor · the model: shaft, impeller and two bearings on springs",
           "dimensions in mm, to scale; bearings and the bend schematic")


def _cycle(ax, x0, x1, y0, y1, n=4, lo=0.0, hi=1.0, color=ACC):
    """A few load cycles between lo and hi (fractions of the box height), drawn in the box x0..x1, y0..y1."""
    t = np.linspace(0, n, 400)
    v = lo + (hi - lo) * 0.5 * (1 - np.cos(2 * np.pi * t))
    ax.plot(x0 + (x1 - x0) * t / n, y0 + (y1 - y0) * v, color=color, lw=1.4, zorder=4)
    ax.plot([x0, x1], [y0, y0], color=DIMC, lw=0.6, zorder=3)


def _strap_plan(ax, L, w, d, x=0.0, y=0.0):
    rect(ax, x - L / 2, y - w / 2, x + L / 2, y + w / 2)
    ax.add_patch(Circle((x, y), d / 2, fc=PLATE, ec=INK, lw=1.2, zorder=3))
    centre(ax, (x - L / 2 - 8, y), (x + L / 2 + 8, y))
    centre(ax, (x, y - w / 2 - 6), (x, y + w / 2 + 6))


def fatigue():
    p = case("strap_fatigue_load")
    L, w, d = p["length_mm"], p["width_mm"], p["hole_diameter_mm"]
    F = p["axial_load_N"] / 1000
    fig, ax = new(9, (-125, 265), (-54, 44))
    _strap_plan(ax, L, w, d)
    for s_ in (-1, 1):
        force(ax, (s_ * (L / 2 + 2), 0), (s_ * (L / 2 + 26), 0), "", color=ACC)
    text(ax, 0, w / 2 + 12, f"the strap from study 2: {L:g} × {w:g} × {p['thickness_mm']:g}, Ø{d:g} hole, 6061-T6",
         fs=7.5, color=INK, box=False)
    note(ax, (0, -d / 2), (-40, -38), "fatigue is judged at the hole edge,\nwhere the stress is highest", ha="center", va="top")
    gx0, gx1, gy0, gy1 = 135, 250, -22, 18
    _cycle(ax, gx0, gx1, gy0, gy1, n=4)
    text(ax, gx0 - 4, gy1, f"{F:g} kN", ha="right", fs=7.5, color=ACC)
    text(ax, gx0 - 4, gy0, "0", ha="right", fs=7.5, color=ACC)
    text(ax, (gx0 + gx1) / 2, gy1 + 10, f"the service load, 0 to {F:g} kN and back", fs=7.5, color=ACC, bold=True, box=False)
    text(ax, (gx0 + gx1) / 2, gy0 - 8, "about 10 million times; with a scatter\nfactor of 3 the computed life must reach 3 × 10⁷",
         fs=7, va="top", box=False)
    finish(fig, "fatigue", "Study 3 · strap fatigue · the part and its load cycle", "dimensions in mm, the load cycle schematic")


def strap_proof():
    p = case("strap_proof_r1")
    L, w, d = p["length_mm"], p["width_mm"], p["hole_diameter_mm"]
    F = p["axial_load_N"] / 1000
    fig, ax = new(9, (-125, 265), (-56, 44))
    _strap_plan(ax, L, w, d)
    th = np.radians(np.linspace(55, 125, 30))         # the yielded zone at the hole edge, from the result: 1.8 mm deep
    for sg in (1, -1):
        outer = [(9.8 * np.cos(a), sg * (d / 2 + 1.8) * np.sin(a) / np.sin(np.pi / 2)) for a in th]
        inner = [(d / 2 * np.cos(a), sg * d / 2 * np.sin(a)) for a in th[::-1]]
        poly(ax, outer + inner, fc=HOT, ec="none", z=3.2)
    for s_ in (-1, 1):
        force(ax, (s_ * (L / 2 + 2), 0), (s_ * (L / 2 + 26), 0), "", color=ACC)
    text(ax, 0, w / 2 + 12, f"the same strap: {L:g} × {w:g} × {p['thickness_mm']:g}, Ø{d:g} hole", fs=7.5, color=INK, box=False)
    note(ax, (0, -d / 2 - 1.5), (-40, -38), "the hole edge yields in a small zone (1.8 mm deep,\nfrom the result) while the rest stays elastic",
         ha="center", va="top", color=HOT)
    gx0, gx1, gy0, gy1 = 135, 250, -22, 18
    t = np.linspace(0, 1, 100)
    ax.plot(gx0 + 35 * t, gy0 + (gy1 - gy0) * np.sin(np.pi * t), color=ACC, lw=1.6, zorder=4)
    _cycle(ax, gx0 + 45, gx1, gy0, gy0 + (gy1 - gy0) / 3, n=4, color=DIMC)
    ax.plot([gx0, gx0 + 45], [gy0, gy0], color=DIMC, lw=0.6)
    text(ax, gx0 + 17, gy1 + 6, f"proof test, {F:g} kN once", fs=7.5, color=ACC, bold=True, box=False)
    text(ax, gx0 + 82, gy0 + (gy1 - gy0) / 3 + 7, "then service, 0 to 5 kN", fs=7.5, color=DIMC, box=False, ha="left")
    text(ax, (gx0 + gx1) / 2, gy0 - 8, "the test is three times the service load", fs=7, va="top", box=False)
    finish(fig, "strap_proof", "Study 14 · strap proof test · one overload before service", "dimensions in mm, the loads schematic")


def bracket_uq():
    p = case("bracket_random_uq")
    L, t_ = p["length_mm"], p["thickness_mm"]
    fig, ax = new(9.5, (-60, 290), (-92, 44))
    rect(ax, -34, -14, 0, 24, hatch="////")
    rect(ax, -50, -24, 60, -14, fc="#d3dceb")
    text(ax, 5, -19, "shaker table", fs=7, color=INK, box=False)
    rect(ax, 0, 0, L, t_)
    text(ax, L / 2, t_ + 5, f"the arm from studies 4 and 21: steel, {L:g} × {p['width_mm']:g} × {t_:g}", fs=7.5, color=INK,
         box=False, va="bottom")
    text(ax, 175, 12, "the same shaker test, but four inputs\nare only known within a range:", ha="left", fs=7.5,
         color=INK, bold=True, box=False)
    # four small distributions
    from math import erf  # noqa: F401
    panels = [
        ("damping", "median 2 %, 9 in 10\nbetween 1 and 4 %", "logn", (1.0, 4.0)),
        ("test level", "anywhere within\n±1.5 dB of the spec", "unif", None),
        ("fatigue strength", "design curve × a factor\nwith 10 % scatter", "logn10", None),
        ("thickness", "7.0 mm, standard\ndeviation 0.1 mm", "norm", None),
    ]
    x = -40
    for name, sub, kind, _ in panels:
        bx0, bx1, by0, by1 = x, x + 58, -72, -40
        u = np.linspace(0, 1, 200)
        if kind == "logn":
            z = np.linspace(np.log(0.6), np.log(6.5), 200)
            yv = np.exp(-0.5 * ((z - np.log(2.0)) / p["damping_sigma_ln"]) ** 2)
        elif kind == "unif":
            yv = np.where((u > 0.2) & (u < 0.8), 0.8, 0.0)
        elif kind == "logn10":
            yv = np.exp(-0.5 * ((u - 0.5) / 0.12) ** 2)
        else:
            yv = np.exp(-0.5 * ((u - 0.5) / 0.13) ** 2)
        ax.fill_between(bx0 + (bx1 - bx0) * u, by0, by0 + (by1 - by0) * yv, color="#d3dceb", lw=0, zorder=3)
        ax.plot(bx0 + (bx1 - bx0) * u, by0 + (by1 - by0) * yv, color=ACC, lw=1.3, zorder=4)
        ax.plot([bx0, bx1], [by0, by0], color=DIMC, lw=0.6, zorder=4)
        text(ax, (bx0 + bx1) / 2, by1 + 6, name, fs=7.5, color=ACC, bold=True, box=False)
        text(ax, (bx0 + bx1) / 2, by0 - 3, sub, fs=6.8, va="top", box=False)
        x += 82
    finish(fig, "bracket_uq", "Study 22 · bracket arm on a shaker table · the four uncertain inputs",
           "dimensions in mm; the distributions schematic, their values from the case file")


def crack():
    p = case("edge_crack_mesh_r2")
    W, H, t_ = p["width_mm"], 2 * p["half_height_mm"], p["thickness_mm"]
    a0, a_crit = p["initial_crack_mm"], 37.0           # critical crack: the result, run 20261123-164649_edge_crack_mesh_r2
    smax = p["sigma_max_MPa"]
    smin = smax * p["stress_ratio"]
    fig, ax = new(9.5, (-300, 300), (-120, 150))
    rect(ax, -H / 2, 0, H / 2, W)
    rect(ax, 0, 0, H / 2, W, fc="#d3dceb", ec="none", z=2.2)
    text(ax, 100, W - 12, "half modelled (symmetric about the crack)", fs=7, color=INK, box=False)
    ax.plot([0, 0], [0, a_crit], color=HOT, lw=1.2, ls=(0, (4, 2)), zorder=5)
    ax.plot([0, 0], [0, a0], color=HOT, lw=3.0, zorder=6, solid_capstyle="butt")
    note(ax, (0, a0), (-70, 22), f"edge crack, {a0:g} mm: the smallest\ninspection can find (drawn to scale)", ha="right", color=HOT)
    note(ax, (0, a_crit), (-70, 62), f"critical crack, {a_crit:g} mm (the result):\nwhere the toughness is reached", ha="right", color=HOT)
    for s_ in (-1, 1):
        for yy in (15, 50, 85):
            force(ax, (s_ * (H / 2 + 2), yy), (s_ * (H / 2 + 34), yy), "", color=ACC, lw=1.2)
    text(ax, H / 2 + 20, W + 16, f"{smin:g} to {smax:g} MPa,\ncycled", fs=7.5, color=ACC, bold=True)
    text(ax, -H / 2 - 20, W + 16, f"{smin:g} to {smax:g} MPa,\ncycled", fs=7.5, color=ACC, bold=True)
    dim(ax, (-H / 2, W), (H / 2, W), 14, f"{H:g}, long enough that the ends don't matter")
    dim(ax, (H / 2 + 40, 0), (H / 2 + 40, W), -12, f"{W:g}")
    text(ax, -H / 2, -14, f"S355 steel, {t_:g} mm thick; toughness {p['k_mat_MPa_sqrt_m']:g} MPa√m", ha="left", fs=7.5, box=False)
    gx0, gx1, gy0, gy1 = -60, 80, -105, -40
    _cycle(ax, gx0, gx1, gy0, gy1, n=4, lo=smin / smax, hi=1.0)
    text(ax, gx0 - 5, gy1, f"{smax:g}", ha="right", fs=7, color=ACC)
    text(ax, gx0 - 5, gy0 + (gy1 - gy0) * smin / smax, f"{smin:g}", ha="right", fs=7, color=ACC)
    text(ax, gx1 + 6, (gy0 + gy1) / 2, "MPa, each cycle;\nthe crack grows a\nlittle every time", ha="left", fs=7, box=False)
    finish(fig, "crack", "Study 24 · edge-cracked steel plate in cyclic tension", "dimensions in mm, to scale; the load cycle schematic")


ALL = {f.__name__: f for f in (fea, cantilever_opt, strap, modal, strut, contact, bolted_joint, pv_nozzle, bracket_opt, cad,
                               cfd, thermal, heat, cold_plate, pipe, suspension, baseline, motor, step, random_vib, fan_rotor,
                               fatigue, strap_proof, bracket_uq, crack)}

if __name__ == "__main__":
    for name in sys.argv[1:] or ALL:
        ALL[name]()

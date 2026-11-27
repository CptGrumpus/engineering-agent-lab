"""The site's charts, redrawn from the runs' saved data in the house style (scripts/figkit.py).

    .venv\\Scripts\\python.exe scripts\\make_figures.py [name ...]

Each function reads a committed run (point.json, cells.csv, verification.json) and its case file, and writes
site/v2/fig_<name>.svg. Limits come from the case file's requirements, statuses from the run's verification
record, and reference curves from the same validation modules the study's checks use, so a chart can't say
something the run didn't.
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
import figkit as fk  # noqa: E402
from figkit import FULL, GRID, INK, INK2, MODEL, MUTED, REF, SURFACE  # noqa: E402

from harness.runio import read_series  # noqa: E402

RUNS = REPO / "runs"


def thumb(fig, ax, key: str):
    """The gallery card's thumbnail (site/v2/th_<key>.webp, 800 x 500): one panel of the chart, with its labels.
    Call before fk.save, which closes the figure. Keeps a card's picture in step with its chart."""
    import io
    from PIL import Image
    dpi = 220
    fig.canvas.draw()
    bb = ax.get_tightbbox(fig.canvas.get_renderer()).padded(6)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, facecolor=SURFACE)
    im = Image.open(buf).convert("RGB")
    s = dpi / fig.dpi
    H = im.height
    im = im.crop((int(bb.x0 * s), int(H - bb.y1 * s), int(bb.x1 * s), int(H - bb.y0 * s)))
    im.thumbnail((760, 470), Image.LANCZOS)
    canvas = Image.new("RGB", (800, 500), (252, 252, 251))
    canvas.paste(im, ((800 - im.width) // 2, (500 - im.height) // 2))
    canvas.save(fk.OUT / f"th_{key}.webp", "WEBP", quality=88, method=6)


def point(run: str, label: str) -> dict:
    return json.loads((RUNS / run / "points" / label / "point.json").read_text(encoding="utf-8"))


def limits(case: str) -> dict:
    d = tomllib.loads((REPO / "cases" / f"{case}.toml").read_text(encoding="utf-8"))
    return {r["metric"]: (r["operator"], r["limit"]) for r in d["requirements"]}


def verified(run: str) -> dict:
    v = json.loads((RUNS / run / "verification.json").read_text(encoding="utf-8"))
    return {p["label"]: p["status"] == "PASS" for p in v["points"]}


# ---------------------------------------------------------------------------------------- study 5, coolant channel

def cfd_tolerance():
    """Both requirements at the corners of the gap tolerance and coolant temperature range."""
    run = "20261119-200202_channel_header_tolerance"
    cases = [("p00_nominal_20C", "Nominal", "1.00 mm gap, 20 °C"), ("p01_min_gap_15C", "Narrow gap, cold", "0.95 mm, 15 °C"),
             ("p02_min_gap_40C", "Narrow gap, warm", "0.95 mm, 40 °C"), ("p03_max_gap_15C", "Wide gap, cold", "1.05 mm, 15 °C"),
             ("p04_max_gap_40C", "Wide gap, warm", "1.05 mm, 40 °C")]
    lim, ok = limits("channel_header_tolerance"), verified(run)
    fig, gs = fk.new(FULL, 3.7, 1, 2, wspace=0.10, top=0.95)
    gs.update(left=0.235)
    panels = [("required_pressure_Pa", "Supply pressure needed, Pa", (20, 46), "{:.1f}", "budget 30 Pa"),
              ("wall_shear_stress_Pa", "Shear on the walls, Pa", (0.28, 0.82), "{:.2f}", "minimum 0.5 Pa")]
    for k, (metric, title, xlim, fmt, limtext) in enumerate(panels):
        ax = fig.add_subplot(gs[0, k])
        fk.style(ax, grid="x")
        ax.set_xlim(*xlim)
        ax.set_ylim(len(cases) - 0.45, -0.75)
        op, L = lim[metric]
        fk.limit(ax, L, limtext, bad="above" if op == "<=" else "below", at=0.985)
        for row, (lab, name, spec) in enumerate(cases):
            v = point(run, lab)["metrics"][metric]
            meets = v <= L if op == "<=" else v >= L
            status = "held" if not ok[lab] else ("meets" if meets else "misses")
            color = fk.MARK[status]["color"]
            ax.plot([L, v], [row, row], color=color, linewidth=2.2, alpha=0.35, zorder=3, solid_capstyle="butt")
            fk.status_dot(ax, v, row, status)
            right = v >= L
            if ok[lab]:
                fk.label(ax, v, row, fmt.format(v), dx=9 if right else -9, ha="left" if right else "right")
            else:                                   # above its stem, clear of the row's name
                fk.label(ax, v, row, fmt.format(v) + ", not verified", dx=-4, dy=8, ha="left", va="bottom", color=INK2,
                         size=8.5)
            if k == 0:
                ax.text(-0.04, row - 0.02, name, transform=ax.get_yaxis_transform(), ha="right", va="bottom", fontsize=9.5,
                        color=INK, fontweight="bold")
                ax.text(-0.04, row + 0.06, spec, transform=ax.get_yaxis_transform(), ha="right", va="top", fontsize=8.5,
                        color=INK2)
        ax.set_yticks([])
        fk.panel(ax, title)
    fk.heading(fig, "No gap meets both limits",
               "Cold coolant in a narrow gap needs too much pressure; warm coolant leaves too little shear on the walls")
    fk.key(fig, [("meets", "meets", None), ("misses", "misses", None), ("not verified", "held", None)])
    fk.save(fig, "cfd_tolerance")


def cfd_duct():
    """The 3D side-wall check: the velocity field against the exact rectangular-duct solution."""
    from studies.duct_flow import exact_field
    from validation import channel_flow as ref

    run, lab = "20261119-204111_duct_side_walls", "p03_cells_across_gap-80"
    rec = point(run, lab)
    p, d, m = rec["parameters"], rec["derived"], rec["metrics"]
    s = read_series(RUNS / run / "points" / lab / "cells.csv")
    ue = exact_field(s, p, d["pressure_gradient_exact_Pa_per_m"])
    H, U = float(p["gap_mm"]), float(p["mean_velocity_m_per_s"])
    sl = np.isclose(s["x_mm"], s["x_mm"].min(), rtol=0, atol=1e-9)           # one periodic slice
    y, z, u, ue = s["y_mm"][sl], s["z_mm"][sl], s["ux_m_per_s"][sl], ue[sl]
    fig, gs = fk.new(FULL, 3.9, 1, 2, width_ratios=(1.55, 1), wspace=0.2, top=1.0)

    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax)
    row = np.isclose(y, y.max(), rtol=0, atol=1e-9)                           # the cells nearest mid-gap
    o = np.argsort(z[row])
    zz, uu, ee = z[row][o], u[row][o] / U, ue[row][o] / U
    flat = float(ref.velocity_profile(y.max() * 1e-3, U, H * 1e-3)) / U
    ax.axhline(flat, color=fk.AXIS, linewidth=1.1, zorder=1)
    fk.label(ax, zz.max(), flat, "with no side walls, 1.50", dx=0, dy=-6, ha="right", va="top", color=INK2, size=8.5)
    ax.plot(zz, ee, color=REF, zorder=3)
    pick = np.unique(np.round(np.geomspace(1, len(zz), 30)).astype(int) - 1)   # denser near the wall
    fk.dots(ax, zz[pick], uu[pick])
    ax.set_xlim(-0.25, zz.max() + 0.25)
    ax.set_ylim(0, 1.72)
    ax.set_xlabel("distance from the side wall, mm (the middle of the channel is at 10)")
    ax.set_ylabel("speed at mid-gap ÷ mean speed")
    fk.callout(ax, (1.0, float(np.interp(1.0, zz, ee))), (38, -46), "the side wall slows the flow\nwithin about one gap height of it")
    fk.panel(ax, "Across the width")

    ax = fig.add_subplot(gs[0, 1])
    fk.style(ax, grid="x")
    near = z[z > 0].min() if (z > 0).any() else z.min()
    for zc, text, at in ((z.max(), "middle of\nthe channel", 0.42), (near, "first cell from\nthe side wall", 0.80)):
        col = np.isclose(z, zc, rtol=0, atol=1e-9)
        o = np.argsort(y[col])
        yy, cu, ce = y[col][o], u[col][o] / U, ue[col][o] / U
        ax.plot(ce, yy, color=REF, zorder=3)
        fk.dots(ax, cu[::5], yy[::5])
        k = int(at * (len(yy) - 1))
        fk.label(ax, ce[k], yy[k], text, dx=-10 if zc == z.max() else 9, ha="right" if zc == z.max() else "left",
                 color=INK2, size=8.5)
    ax.set_xlim(0, 1.72)
    ax.set_ylim(0, 0.56)
    ax.set_xlabel("speed ÷ mean speed")
    ax.set_ylabel("distance from the plate, mm (mid-gap is at 0.5)")
    fk.panel(ax, "Across the gap")
    fk.heading(fig, f"The side walls add {m['side_wall_effect'] * 100:.1f} % to the friction; the exact solution says "
                    f"{d['side_wall_effect_exact'] * 100:.2f} %",
               "3D model of a 20 mm wide, 1 mm deep channel against the exact solution for a rectangular duct")
    fk.key(fig, [("exact solution", "line", REF), ("3D model", "dot", MODEL)], y_in=0.66)
    fk.save(fig, "cfd_duct")


def _channel(run="20261119-200042_channel_header_mesh", lab="p03_cells_across_gap-80"):
    rec = point(run, lab)
    return rec, read_series(RUNS / run / "points" / lab / "cells.csv")


def cfd_response():
    """The settled flow against the exact parallel-plate solution, and the pressure along the channel."""
    from studies.channel_flow import profile_station
    from validation import channel_flow as ref

    rec, s = _channel()
    p, d = rec["parameters"], rec["derived"]
    blocks = rec["solver_outputs"]["blocks"]
    H, L, U = float(p["gap_mm"]), float(p["length_mm"]), float(p["mean_velocity_m_per_s"])
    x0, x1 = float(p["window_start_mm"]), float(p["window_end_mm"])
    st = profile_station(s, p)
    fig, gs = fk.new(FULL, 5.4, 2, 2, width_ratios=(1, 2.15), wspace=0.22, hspace=0.42, top=1.0)

    ax = fig.add_subplot(gs[:, 0])
    fk.style(ax, grid="x")
    ys = np.linspace(0, H, 200)
    ax.plot(ref.velocity_profile(ys * 1e-3, U, H * 1e-3), ys, color=REF, zorder=3)
    o = np.argsort(s["y_mm"][st])
    fk.dots(ax, s["ux_m_per_s"][st][o][1::3], s["y_mm"][st][o][1::3])
    ax.set_xlim(0, 0.165)
    ax.set_ylim(0, H)
    ax.set_xlabel("speed, m/s")
    ax.set_ylabel("position across the gap, mm")
    fk.panel(ax, "Speed across the gap")

    # mid-gap cells of every block (cell order: block by block, x fastest; two rows straddle the centre line)
    xu, pc, uc, start = [], [], [], 0
    for nx, ny in blocks:
        rows = [ny // 2] if ny % 2 else [ny // 2 - 1, ny // 2]
        idx = [start + j * nx + np.arange(nx) for j in rows]
        xu.append(np.mean([s["x_mm"][i] for i in idx], axis=0))
        pc.append(np.mean([s["p_Pa"][i] for i in idx], axis=0))
        uc.append(np.mean([s["ux_m_per_s"][i] for i in idx], axis=0))
        start += nx * ny
    xu, pc, uc = (np.concatenate(a) for a in (xu, pc, uc))
    nxl, nyl = blocks[-1]
    rows = [nyl // 2] if nyl % 2 else [nyl // 2 - 1, nyl // 2]
    cl = np.zeros(len(s["x_mm"]), bool)
    for j in rows:
        cl[start - nxl * nyl + j * nxl + np.arange(nxl)] = True
    G = d["pressure_gradient_exact_Pa_per_m"]

    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 1], sharex=ax2)
    for ax in (ax2, ax3):
        fk.style(ax)
        ax.axvspan(xu.min(), 0, color=MODEL, alpha=0.06, linewidth=0, zorder=0.5)
        ax.axvspan(x0, x1, color=INK2, alpha=0.07, linewidth=0, zorder=0.5)
        ax.set_xlim(xu.min(), L)
    ax2.plot([0, L], [G * L * 1e-3, 0], color=REF, zorder=3)
    ax2.plot(xu, pc, color=MODEL, zorder=4)
    ax2.set_ylabel("pressure, Pa")
    ax2.set_ylim(0, pc.max() * 1.08)
    ax2.text(xu.min() / 2, pc.max() * 0.16, "header and\ncontraction", ha="center", va="center", fontsize=8.5, color=INK2)
    ax2.text((x0 + x1) / 2, pc.max() * 0.93, "measured here", ha="center", va="center", fontsize=8.5, color=INK2)
    fk.label(ax2, L * 0.30, G * L * 0.70e-3, f"exact slope, {G:,.0f} Pa/m", dx=8, dy=8, color=INK2, size=8.5)
    plt_tick = ax2.tick_params
    plt_tick(labelbottom=False)
    fk.panel(ax2, "Pressure along the channel")

    yc = np.unique(np.round(s["y_mm"][cl], 9)) * 1e-3                         # compare like with like
    u_fd = float(np.mean(ref.velocity_profile(yc, U, H * 1e-3))) / U
    ax3.axhline(u_fd, color=REF, zorder=3)
    ax3.plot(xu, uc / U, color=MODEL, zorder=4)
    Le = d["entrance_length_mm"]
    ax3.axvline(Le, color=INK2, linewidth=1.1, zorder=2)
    fk.label(ax3, Le, 0.62, f"predicted entrance length, {Le:.1f} mm", dx=6, color=INK2, size=8.5)
    fk.label(ax3, L, u_fd, f"exact, {u_fd:.3f}", dx=-4, dy=-9, ha="right", va="top", color=INK2, size=8.5)
    ax3.set_ylim(0.4, 1.62)
    ax3.set_ylabel("centre-line speed ÷ mean")
    ax3.set_xlabel("distance along the channel, mm (0 is the channel entry)")
    fk.panel(ax3, "Speed on the centre line")
    fk.heading(fig, "Once the flow settles, the model sits on the exact solution",
               "Velocity profile, pressure gradient and wall shear all within 0.02 % of flow between parallel plates")
    fk.key(fig, [("exact solution", "line", REF), ("model", "line", MODEL)], y_in=0.66)
    fk.save(fig, "cfd_response")


def cfd_field():
    """Axial velocity over the whole flow domain, heights stretched so the channel can be seen."""
    import matplotlib

    rec, s = _channel()
    blocks = rec["solver_outputs"]["blocks"]
    p = rec["parameters"]
    fig, gs = fk.new(FULL, 2.95, 1, 1, top=0.72)
    gs.update(right=0.99, bottom=0.2)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax, grid="")
    u = s["ux_m_per_s"]
    norm = matplotlib.colors.Normalize(vmin=0.0, vmax=float(u.max()))
    grids, start = [], 0
    for nx, ny in blocks:
        sl = slice(start, start + nx * ny)
        start += nx * ny
        grids.append([s[k][sl].reshape(ny, nx) for k in ("x_mm", "y_mm", "ux_m_per_s")])
    for i, (X, Y, Z) in enumerate(grids):
        if i + 1 < len(grids) and grids[i + 1][0].shape[0] == X.shape[0]:      # join to the next block's first column
            X, Y, Z = (np.hstack([a, b[:, :1]]) for a, b in zip((X, Y, Z), grids[i + 1]))
        mesh = ax.pcolormesh(X, Y, Z, cmap=fk.SEQ, norm=norm, shading="gouraud", rasterized=True)
    ax.set_facecolor(GRID)
    cb = fig.colorbar(mesh, ax=ax, pad=0.015, aspect=14, shrink=0.92)
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=0, labelsize=8.5, colors=INK2)
    cb.set_label("speed along the channel, m/s", color=INK2, fontsize=9)
    ax.set_xlabel("distance along the channel, mm (0 is the channel entry)")
    ax.set_ylabel("height, mm")
    ax.set_xlim(s["x_mm"].min(), float(p["length_mm"]))
    y0, y1 = float(s["y_mm"].min()), float(s["y_mm"].max())
    ax.set_ylim(y0 - 0.3, y1 + 0.3)
    for x, text in ((-4.5, "supply header"), (-1.5, "contraction"), (10.0, "1 mm channel")):
        ax.text(x, y1 + 0.42, text, ha="center", va="bottom", fontsize=8.5, color=INK2, clip_on=False)
    ax.text(10.0, y0 + 0.25, "solid wall", ha="center", va="center", fontsize=8.5, color=MUTED)
    fk.heading(fig, "The water speeds up as it squeezes into the channel",
               "Axial velocity through the supply header, the contraction and the channel; heights are stretched")
    fig.savefig(fk.OUT / "fig_cfd_field.svg", format="svg", dpi=300, metadata={"Date": None, "Creator": None})
    fk.plt.close(fig)
    print("fig cfd_field", f"{(fk.OUT / 'fig_cfd_field.svg').stat().st_size // 1024} KB")



# ---------------------------------------------------------------------------------------- shared: a result against a limit

def pts(run: str) -> list:
    """Every point of a run, in order: (label, record, verified)."""
    ok = verified(run)
    out = []
    for d in sorted((RUNS / run / "points").iterdir()):
        if (d / "point.json").exists():
            out.append((d.name, json.loads((d / "point.json").read_text(encoding="utf-8")), ok.get(d.name, False)))
    return out


def sweep_panel(ax, xs, ys, oks, op, L, limtext, fmt="{:.0f}", ylim=None, logx=False, logy=False, labels=None, at=0.98):
    """A metric at each value of the swept input, with its limit: a faint line through the points, a status
    marker on each, and the value beside it. `labels` picks which points get their value written."""
    fk.style(ax)
    if logx:
        ax.set_xscale("log")
    if logy:
        ax.set_yscale("log")
    ax.plot(xs, ys, color=MODEL, linewidth=1.6, alpha=0.45, zorder=3)
    if ylim:
        ax.set_ylim(*ylim)
    ax.margins(x=0.08)
    fk.limit(ax, L, limtext, bad="above" if op == "<=" else "below", axis="y", at=at)
    for k, (x, y, ok) in enumerate(zip(xs, ys, oks)):
        meets = y <= L if op == "<=" else y >= L
        fk.status_dot(ax, x, y, "held" if not ok else ("meets" if meets else "misses"))
        if labels is None or k in labels:
            fk.label(ax, x, y, fmt.format(y), dy=10, ha="center", va="bottom", size=8.5)


# ---------------------------------------------------------------------------------------- structures

def fea_tet4():
    """Tip deflection against element size, linear and quadratic tetrahedra, with the beam-theory band."""
    lin, quad = pts("20261119-090004_cantilever_tet4"), pts("20261119-085818_cantilever_tet10")
    fig, gs = fk.new(fk.HALF, 3.9, top=0.95)
    gs.update(left=0.17, right=0.96)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax)
    ax.axhspan(0.952, 0.960, color=REF, alpha=0.18, linewidth=0, zorder=1)
    ax.axhline(0.956, color=REF, linewidth=1.2, zorder=1)
    for rows, status, text in ((quad, "meets", "quadratic elements"), (lin, "held", "linear elements,\nheld back by the checks")):
        xs = [r["parameters"]["mesh_size_mm"] for _, r, _ in rows]
        ys = [r["metrics"]["tip_deflection_mm"] for _, r, _ in rows]
        ax.plot(xs, ys, color=fk.MARK[status]["color"], linewidth=1.6, alpha=0.5, zorder=3)
        for x, y in zip(xs, ys):
            fk.status_dot(ax, x, y, status)
        if status == "held":
            fk.label(ax, xs[0], ys[0], f"{ys[0]:.2f} mm: a third too stiff", dx=10, dy=-3, va="top", size=8.5)
            fk.label(ax, xs[1], ys[1], text, dx=10, dy=-6, va="top", color=INK2, size=8.5)
        else:
            fk.label(ax, xs[0], ys[0], text, dx=0, dy=-10, va="top", color=INK2, size=8.5)
    ax.set_xlim(8.6, 1.3)
    ax.set_ylim(0.58, 1.04)
    fk.label(ax, 1.5, 0.960, "beam theory, 0.952 to 0.960", dx=0, dy=6, ha="right", va="bottom", color=INK2, size=8.5)
    ax.set_xlabel("element size, mm (finer to the right)")
    ax.set_ylabel("tip deflection, mm")
    fk.heading(fig, "Linear elements make the bracket look too stiff", "Tip deflection against element size, for two element types")
    fk.save(fig, "fea_tet4")


def strap_sweep():
    rows = pts("20261119-235211_strap_hole_size")
    op, L = limits("strap_hole_size")["peak_hole_stress_MPa"]
    fig, gs = fk.new(fk.HALF, 3.7, top=0.95)
    gs.update(left=0.15, right=0.96)
    ax = fig.add_subplot(gs[0, 0])
    xs = [r["parameters"]["hole_diameter_mm"] for _, r, _ in rows]
    ys = [r["metrics"]["peak_hole_stress_MPa"] for _, r, _ in rows]
    sweep_panel(ax, xs, ys, [ok for *_, ok in rows], op, L, f"allowable {L:g} MPa", ylim=(85, 132), labels={0, 5, 6}, at=0.03)
    ax.set_xlabel("hole diameter, mm")
    ax.set_ylabel("peak stress at the hole edge, MPa")
    fk.heading(fig, "A 16 mm hole passes; 18 mm does not", "Peak stress at the hole edge against hole size")
    fk.save(fig, "strap_sweep")


def fatigue_sweep():
    rows = pts("20261120-011347_strap_fatigue_load")
    op, L = limits("strap_fatigue_load")["fatigue_life_cycles"]
    fig, gs = fk.new(fk.HALF, 3.7, top=0.95)
    gs.update(left=0.16, right=0.96)
    ax = fig.add_subplot(gs[0, 0])
    xs = [r["parameters"]["axial_load_N"] / 1000 for _, r, _ in rows]
    ys = [r["metrics"]["fatigue_life_cycles"] for _, r, _ in rows]
    sweep_panel(ax, xs, ys, [ok for *_, ok in rows], op, L, "needed: 3 × 10⁷ cycles", logy=True, ylim=(4e5, 3e10), labels=set(), at=0.03)
    lx, ly = np.array(xs), np.log10(ys)
    k = int(np.argmax(ly < np.log10(L)))
    rated = lx[k - 1] + (np.log10(L) - ly[k - 1]) * (lx[k] - lx[k - 1]) / (ly[k] - ly[k - 1])
    ax.plot([rated, rated], [4e5, L], color=INK2, linewidth=0.9, zorder=2)
    fk.label(ax, rated, 5.5e5, f"rated {rated:.1f} kN", dx=-5, ha="right", va="bottom", size=8.5)
    fk.label(ax, xs[0], ys[0], "service load: about 8 × 10⁹ cycles", dx=9, dy=2, size=8.5)
    ax.set_xlabel("peak cyclic load, kN")
    ax.set_ylabel("predicted life, cycles")
    fk.heading(fig, f"Rated to about {rated:.1f} kN", "Predicted fatigue life against the peak of the load cycle")
    fk.save(fig, "fatigue_sweep")


def strut_sweep():
    rows = pts("20261120-232856_strut_length")
    op, L = limits("strut_length")["first_yield_load_N"]
    fig, gs = fk.new(fk.HALF, 3.7, top=0.95)
    gs.update(left=0.14, right=0.96)
    ax = fig.add_subplot(gs[0, 0])
    xs = [r["parameters"]["length_mm"] for _, r, _ in rows]
    ys = [r["metrics"]["first_yield_load_N"] / 1000 for _, r, _ in rows]
    pc = [r["metrics"]["critical_load_N"] / 1000 for _, r, _ in rows]
    ax.plot(xs, pc, color=fk.AXIS, linewidth=1.6, zorder=2)
    fk.label(ax, xs[0], pc[0], "elastic buckling load", dx=10, dy=6, color=INK2, size=8.5)
    sweep_panel(ax, xs, ys, [ok for *_, ok in rows], op, L / 1000, f"must reach {L / 1000:g} kN", fmt="{:.1f}", ylim=(6, 40), at=0.03)
    ax.set_xlabel("strut length, mm")
    ax.set_ylabel("load at first yield, kN")
    fk.heading(fig, "The strut can be about 587 mm long", "Load at first yield against length, with the buckling load above it")
    fk.save(fig, "strut_sweep")


def strut_response():
    rec = point("20261120-232856_strut_length", "p01_length_mm-500")
    so, m, p = rec["solver_outputs"], rec["metrics"], rec["parameters"]
    P, dlt, vm = (np.array(so[k]) for k in ("load_N", "midspan_deflection_mm", "midspan_peak_von_mises_MPa"))
    Pcr, Py, e0 = m["critical_load_N"], m["first_yield_load_N"], p["length_mm"] * p["imperfection_over_length"]
    fig, gs = fk.new(FULL, 3.9, 1, 3, wspace=0.34, top=1.0)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax)
    Pl = np.linspace(0, P.max(), 200)
    ax.plot(e0 / (1 - Pl / Pcr), Pl / 1000, color=REF, zorder=3)
    fk.dots(ax, dlt, P / 1000)
    ax.axhline(Pcr / 1000, color=INK2, linewidth=1.1, zorder=1)
    fk.label(ax, 0, Pcr / 1000, f"buckling load, {Pcr / 1000:.1f} kN", dx=2, dy=6, va="bottom", color=INK2, size=8.5)
    ax.set_xlim(0, dlt.max() * 1.05)
    ax.set_ylim(0, Pcr / 1000 * 1.15)
    ax.set_xlabel("sideways deflection at mid-length, mm")
    ax.set_ylabel("load, kN")
    fk.panel(ax, "The bow grows with load")

    ax = fig.add_subplot(gs[0, 1])
    fk.style(ax)
    w = dlt - e0
    sel = P <= 0.8 * Pcr
    fit = np.polyfit(w[sel], (w / P)[sel] * 1000, 1)
    ax.plot(w, np.polyval(fit, w), color=REF, zorder=3)
    fk.dots(ax, w, w / P * 1000)
    ax.set_xlim(0, w.max() * 1.05)
    ax.set_ylim(0, None)
    ax.set_xlabel("growth of the bow, mm")
    ax.set_ylabel("growth ÷ load, mm per kN")
    fk.label(ax, w.max() * 0.45, np.polyval(fit, w.max() * 0.45), f"a straight line: its slope\ngives {m['southwell_load_N'] / 1000:.2f} kN",
             dx=10, dy=-16, color=INK2, size=8.5)
    fk.panel(ax, "Southwell plot")

    ax = fig.add_subplot(gs[0, 2])
    fk.style(ax)
    ax.plot(P / 1000, vm, color=MODEL, zorder=4)
    ax.set_xlim(0, P.max() / 1000 * 1.04)
    ax.set_ylim(0, 320)
    fk.limit(ax, 276.0, "yield, 276 MPa", bad="above", axis="y", at=0.6)
    ax.plot([Py / 1000], [276.0], marker="o", markersize=8, color=fk.FAIL, markeredgecolor=SURFACE, markeredgewidth=1.4, zorder=5)
    fk.label(ax, Py / 1000, 276.0, f"first yield\n{Py / 1000:.1f} kN", dx=-9, dy=-4, ha="right", va="top", size=8.5)
    ax.set_xlabel("load, kN")
    ax.set_ylabel("highest stress, MPa")
    fk.panel(ax, "Stress climbing to yield")
    fk.heading(fig, f"The bowed strut yields at {100 * Py / Pcr:.0f} % of its buckling load",
               "The 500 mm strut with an initial bow of 0.5 mm, loaded step by step")
    fk.key(fig, [("beam-column theory", "line", REF), ("model", "dot", MODEL)], y_in=0.66)
    fk.save(fig, "strut_response")


def proof_response():
    run, lab = "20261120-233830_strap_proof_r1", "p02_hole_element_ratio-0.00625"
    rec = point(run, lab)
    p, d, m = rec["parameters"], rec["derived"], rec["metrics"]
    s = read_series(RUNS / run / "points" / lab / "ligament.csv")
    r = p["hole_diameter_mm"] / 2
    x = s["y_mm"] - r
    fig, gs = fk.new(FULL, 3.9, 1, 2, width_ratios=(1.25, 1), wspace=0.24, top=1.0)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax)
    ax.axhline(0, color=fk.AXIS, linewidth=1.0, zorder=1)
    ax.plot(x, s["sxx_elastic_MPa"], color=fk.AXIS, zorder=2)
    ax.plot(x, s["sxx_proof_MPa"], color=MODEL, zorder=4)
    ax.plot(x, s["sxx_residual_MPa"], color=fk.THIRD, zorder=4)
    ax.set_xlim(0, x.max())
    ax.set_ylim(-135, 380)
    fk.callout(ax, (0.3, float(np.interp(0.3, x, s["sxx_elastic_MPa"]))), (62, 2), "if it stayed elastic")
    fk.label(ax, 3.0, np.interp(3.0, x, s["sxx_proof_MPa"]), "at the 15 kN proof load", dx=4, dy=10, va="bottom", color=INK2, size=8.5)
    fk.label(ax, 3.0, np.interp(3.0, x, s["sxx_residual_MPa"]), "after unloading", dx=4, dy=9, va="bottom", color=INK2, size=8.5)
    fk.label(ax, 0.0, m["residual_stress_MPa"], f"{m['residual_stress_MPa']:.0f} MPa left at the hole edge", dx=26, dy=-8, va="center", size=8.5)
    ax.axvspan(0, m["plastic_zone_mm"], color=fk.FAIL, alpha=0.07, linewidth=0, zorder=0.5)
    fk.label(ax, m["plastic_zone_mm"], 372, f"yielded, {m['plastic_zone_mm']:.1f} mm deep", dx=6, va="top", color=INK2, size=8.5)
    ax.set_xlabel("distance from the hole edge, mm")
    ax.set_ylabel("stress along the strap, MPa")
    fk.panel(ax, "Stress across the ligament")

    ax = fig.add_subplot(gs[0, 1])
    fk.style(ax)
    E = p["youngs_modulus_MPa"]
    sp, ep = np.array(p["plastic_stress_MPa"]), np.array(p["plastic_strain"])
    ax.plot(np.concatenate([[0], 100 * (sp / E + ep)]), np.concatenate([[0], sp]), color=fk.AXIS, zorder=2)
    for name, e, sg in (("Neuber", d["neuber_strain"], d["neuber_stress_MPa"]), ("Glinka", d["glinka_strain"], d["glinka_stress_MPa"])):
        fk.dots(ax, [100 * e], [sg], color=REF, size=52)
        left = name == "Glinka"
        fk.label(ax, 100 * e, sg, f"{name}, {100 * e:.2f} %", dx=-4 if left else 4, dy=-12, ha="right" if left else "left", va="top",
                 color=INK2, size=8.5)
    fk.dots(ax, [m["notch_strain_percent"]], [m["notch_stress_MPa"]], size=62)
    fk.label(ax, m["notch_strain_percent"], m["notch_stress_MPa"], f"model, {m['notch_strain_percent']:.2f} %", dy=12, ha="center", va="bottom", size=8.5)
    ax.set_xlim(0, 1.3)
    ax.set_ylim(0, 320)
    fk.limit(ax, 1.0, "limit 1 %", bad="above", axis="x", at=0.2)
    fk.label(ax, 0.2, np.interp(0.2, np.concatenate([[0], 100 * (sp / E + ep)]), np.concatenate([[0], sp])), "the material's curve", dx=6, dy=-14,
             color=INK2, size=8.5)
    ax.set_xlabel("strain at the hole edge, %")
    ax.set_ylabel("stress at the hole edge, MPa")
    fk.panel(ax, "The hole edge at the proof load")
    fk.heading(fig, f"The hole edge yields to {m['notch_strain_percent']:.2f} % and is left in compression",
               "The proof test on the strap: a pocket of material yields, and the elastic material around it squeezes it on unloading")
    fk.key(fig, [("classical estimates", "dot", REF), ("model", "dot", MODEL)], y_in=0.66)
    fk.save(fig, "proof_response")


def joint_response():
    run, lab = "20261121-110554_bolted_joint_mesh_r1", "p02_element_size_mm-0.5"
    rec = point(run, lab)
    p, d, so, m = rec["parameters"], rec["derived"], rec["solver_outputs"], rec["metrics"]
    s = read_series(RUNS / run / "points" / lab / "interface_pressure.csv")
    fig, gs = fk.new(FULL, 3.8, 1, 2, wspace=0.24, top=1.0)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax)
    u = np.concatenate([[0], np.array(so["slip_displacement_mm"]) * 1000])
    F = np.concatenate([[0], np.abs(np.array(so["rim_force_top_N"])) * 2])       # half model: twice the rim force
    lim = p["friction_coefficient"] * p["preload_N"]
    ax.axhline(lim, color=REF, zorder=3)
    ax.plot(u, F, color=MODEL, zorder=4)
    fk.dots(ax, u[1:], F[1:])
    ax.set_xlim(0, u.max() * 1.04)
    ax.set_ylim(0, lim * 1.2)
    fk.label(ax, u.max(), lim, f"friction × clamp force = {lim:,.0f} N", dx=0, dy=7, ha="right", va="bottom", color=INK2, size=8.5)
    fk.label(ax, u[2], F[2], f"the whole joint slides at {m['slip_load_N']:,.0f} N", dx=8, dy=-14, color=INK, size=8.5)
    ax.set_xlabel("sideways movement of the top plate, µm")
    ax.set_ylabel("side load carried, N")
    fk.panel(ax, "Side load until the joint slides")

    ax = fig.add_subplot(gs[0, 1])
    fk.style(ax)
    ax.fill_between(s["r_mm"], s["contact_pressure_MPa"], color=MODEL, alpha=0.10, linewidth=0, zorder=2)
    ax.plot(s["r_mm"], s["contact_pressure_MPa"], color=MODEL, zorder=4)
    rc = d["cone_limit_diameter_mm"] / 2
    ax.axvline(rc, color=REF, zorder=3)
    ax.set_xlim(0, p["plate_outer_diameter_mm"] / 2)
    ax.set_ylim(0, None)
    ax.axvspan(0, p["hole_diameter_mm"] / 2, color=fk.GRID, linewidth=0, zorder=1)
    fk.label(ax, p["hole_diameter_mm"] / 4, ax.get_ylim()[1] * 0.5, "bolt\nhole", ha="center", color=INK2, size=8.5)
    fk.label(ax, rc, ax.get_ylim()[1] * 0.86, f"VDI 2230's estimate of where\ncontact ends, {2 * rc:.1f} mm across", dx=7, color=INK2, size=8.5)
    fk.label(ax, m["contact_diameter_mm"] / 2, 0, f"contact ends, {m['contact_diameter_mm']:.1f} mm across", dx=4, dy=16, va="bottom", size=8.5)
    ax.set_xlabel("distance from the bolt axis, mm")
    ax.set_ylabel("pressure between the plates, MPa")
    fk.panel(ax, "Where the plates press together")
    fk.heading(fig, "Friction holds 3.0 kN at full clamp, and only the middle of the plates does the clamping",
               "Two 6 mm plates clamped at 15 kN: the side load until slip, and the pressure between the plates")
    fk.key(fig, [("hand method (VDI 2230)", "line", REF), ("model", "line", MODEL)], y_in=0.66)
    fk.save(fig, "joint_response")


def contact_response():
    from validation import hertz

    run, lab = "20261120-120243_contact_roller_mesh", "p02_contact_element_size_mm-0.02"
    rec = point(run, lab)
    p, m, so = rec["parameters"], rec["metrics"], rec["solver_outputs"]
    s = read_series(RUNS / run / "points" / lab / "contact_profile.csv")
    h = hertz.line_contact(m["line_load_N_per_mm"], p["roller_radius_mm"], p["youngs_modulus_MPa"], p["poisson_ratio"])
    a, p0 = h["half_width_mm"], h["peak_pressure_MPa"]
    lim = limits("contact_roller_mesh")
    fig, gs = fk.new(FULL, 3.9, 1, 2, wspace=0.24, top=1.0)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax)
    xs = np.linspace(-a, a, 300)
    ax.plot(xs, hertz.pressure(np.abs(xs), a, p0), color=REF, zorder=3)
    inside = s["x_mm"] <= 1.25 * a
    xf, pf = s["x_mm"][inside], s["contact_pressure_MPa"][inside]
    step = max(1, len(xf) // 14)
    fk.dots(ax, np.concatenate([-xf[::step][::-1], xf[::step]]), np.concatenate([pf[::step][::-1], pf[::step]]))
    ax.set_xlim(-1.5 * a, 1.5 * a)
    ax.set_ylim(0, 720)
    op, L = lim["peak_contact_pressure_MPa"]
    fk.limit(ax, L, f"limit {L:g} MPa", bad="above", axis="y")
    fk.label(ax, 0, m["peak_contact_pressure_MPa"], f"peak {m['peak_contact_pressure_MPa']:.0f} MPa", dy=-16, ha="center", va="top", size=8.5)
    ax.set_xlabel("position across the contact, mm")
    ax.set_ylabel("contact pressure, MPa")
    fk.panel(ax, "Pressure across the contact")

    ax = fig.add_subplot(gs[0, 1])
    fk.style(ax, grid="x")
    z = np.linspace(0, 2.0, 300)
    ax.plot(hertz.subsurface_shear(z, a, p0), z, color=REF, zorder=3)
    dz, tau = np.array(so["axis"]["depth_mm"]), np.array(so["axis"]["tau_MPa"])
    keep = dz <= 2.0
    step = max(1, keep.sum() // 22)
    fk.dots(ax, tau[keep][::step], dz[keep][::step])
    ax.set_xlim(0, 262)
    ax.set_ylim(2.0, 0)
    op, L = lim["max_subsurface_shear_MPa"]
    fk.limit(ax, L, f"limit {L:g} MPa", bad="above", axis="x", at=0.08)
    fk.label(ax, m["max_subsurface_shear_MPa"], m["max_shear_depth_mm"], f"{m['max_subsurface_shear_MPa']:.0f} MPa,\n{m['max_shear_depth_mm']:.2f} mm down",
             dx=-10, dy=-4, ha="right", va="top", size=8.5)
    ax.set_xlabel("shear stress, MPa")
    ax.set_ylabel("depth below the surface, mm")
    fk.panel(ax, "Shear below the centre of the contact")
    fk.heading(fig, "The contact model lands on Hertz's exact solution",
               f"Peak pressure within 0.4 %; the highest shear sits {m['max_shear_depth_mm']:.2f} mm below the surface, where cracks start")
    fk.key(fig, [("Hertz, exact", "line", REF), ("model", "dot", MODEL)], y_in=0.66)
    fk.save(fig, "contact_response")



def fea_response():
    """Deflection and top-face stress along the bar against beam theory."""
    from validation import beam_theory as beam

    run, lab = "20261119-085818_cantilever_tet10", "p03_mesh_size_mm-1.95312"
    rec = point(run, lab)
    p, m = rec["parameters"], rec["metrics"]
    s = read_series(RUNS / run / "points" / lab / "nodal_results.csv")
    L, b, h = float(p["length_mm"]), float(p["width_mm"]), float(p["height_mm"])
    E, nu, F = float(p["youngs_modulus_MPa"]), float(p["poisson_ratio"]), float(p["tip_load_N"])
    x, y, z = s["x_mm"], s["y_mm"], s["z_mm"]
    xs = np.linspace(0, L, 200)
    fig, gs = fk.new(FULL, 3.9, 1, 2, wspace=0.24, top=1.0)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax)
    line = np.isclose(z, h, atol=1e-6) & np.isclose(y, y[np.argmin(np.abs(y - (y.min() + y.max()) / 2))], atol=1e-6)
    o = np.argsort(x[line])
    step = max(1, line.sum() // 22)
    ax.plot(xs, beam.timoshenko_deflection(xs, F, L, E, nu, b, h), color=REF, zorder=3)
    fk.dots(ax, x[line][o][::step], -s["uz_mm"][line][o][::step])
    ax.set_xlim(0, L * 1.03)
    ax.set_ylim(0, 1.12)
    op, lim = limits("cantilever_tet10")["tip_deflection_mm"]
    fk.limit(ax, lim, f"limit {lim:g} mm", bad="above", axis="y", at=0.03)
    fk.label(ax, L, m["tip_deflection_mm"], f"{m['tip_deflection_mm']:.3f} mm", dx=-8, dy=-10, ha="right", va="top", size=8.5)
    ax.set_xlabel("distance from the fixed end, mm")
    ax.set_ylabel("downward deflection, mm")
    fk.panel(ax, "Deflection along the bar")

    ax = fig.add_subplot(gs[0, 1])
    fk.style(ax)
    top = np.isclose(z, h, atol=1e-6) & (np.abs(y - (y.min() + y.max()) / 2) < 0.26 * b)
    o = np.argsort(x[top])
    step = max(1, top.sum() // 60)
    ax.axvspan(0.25 * L, 0.75 * L, color=INK2, alpha=0.07, linewidth=0, zorder=0.5)
    ax.plot(xs, beam.bending_stress(F, L, b, h, xs), color=REF, zorder=3)
    fk.dots(ax, x[top][o][::step], s["sxx_MPa"][top][o][::step], size=22)
    ax.set_xlim(0, L * 1.03)
    ax.set_ylim(0, 235)
    fk.label(ax, L / 2, 14, "the stress is read here,\nwhere it's smooth", ha="center", va="bottom", color=INK2, size=8.5)
    fk.callout(ax, (1.5, 184), (30, 12), "at the clamped corner it climbs\nwithout limit as the mesh is refined")
    ax.set_xlabel("distance from the fixed end, mm")
    ax.set_ylabel("stress on the top face, MPa")
    fk.panel(ax, "Bending stress along the bar")
    fk.heading(fig, f"The model matches beam theory: {m['tip_deflection_mm']:.3f} mm at the tip, {m['root_bending_stress_MPa']:.0f} MPa at the root",
               "The finest mesh of the study against the hand calculation")
    fk.key(fig, [("beam theory", "line", REF), ("model", "dot", MODEL)], y_in=0.66)
    fk.save(fig, "fea_response")


def strap_response():
    """Stress across the section beside the hole, with the handbook peak."""
    run, lab = "20261119-235201_strap_hole_mesh", "p03_hole_element_size_mm-0.125"
    rec = point(run, lab)
    p, d, m = rec["parameters"], rec["derived"], rec["metrics"]
    s = read_series(RUNS / run / "points" / lab / "nodal_results.csv")
    r = float(p["hole_diameter_mm"]) / 2
    lig = np.isclose(s["x_mm"], 0.0, atol=1e-6)
    o = np.argsort(s["y_mm"][lig])
    yy, sg = s["y_mm"][lig][o] - r, s["sxx_MPa"][lig][o]
    fig, gs = fk.new(fk.HALF, 3.8, top=0.95)
    gs.update(left=0.15, right=0.96)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax)
    ax.axhline(d["net_stress_MPa"], color=fk.AXIS, linewidth=1.1, zorder=1)
    ax.fill_between(yy, sg, color=MODEL, alpha=0.10, linewidth=0, zorder=2)
    ax.plot(yy, sg, color=MODEL, zorder=4)
    fk.dots(ax, [0], [d["peak_stress_peterson_MPa"]], color=REF, size=62)
    ax.set_xlim(-0.4, yy.max())
    ax.set_ylim(0, m["peak_hole_stress_MPa"] * 1.22)
    fk.label(ax, 0, m["peak_hole_stress_MPa"], f"model {m['peak_hole_stress_MPa']:.1f} MPa\nhandbook {d['peak_stress_peterson_MPa']:.1f} MPa", dx=10, dy=2, size=8.5)
    fk.label(ax, yy.max(), d["net_stress_MPa"], f"average over the section, {d['net_stress_MPa']:.1f} MPa", dx=-2, dy=6, ha="right", va="bottom", color=INK2, size=8.5)
    ax.set_xlabel("distance from the hole edge, mm")
    ax.set_ylabel("stress along the strap, MPa")
    fk.heading(fig, f"The stress peaks at {m['kt_net']:.2f} times the average", "Across the section beside a 10 mm hole, from its edge outward")
    fk.key(fig, [("handbook peak", "dot", REF), ("model", "line", MODEL)], y_in=0.66)
    fk.save(fig, "strap_response")


def fatigue_sn():
    """The published test points, the fitted curve, the independent long-life value and the service cycle."""
    from matplotlib.ticker import FixedLocator, NullFormatter, ScalarFormatter

    from studies.strap_fatigue import _SN as sn

    rec = point("20261120-011347_strap_fatigue_load", "p00_axial_load_N-5000")
    out, m = rec["solver_outputs"], rec["metrics"]
    fig, gs = fk.new(FULL, 4.0, top=1.0)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax)
    ax.set_xscale("log")
    ax.set_yscale("log")
    n = np.logspace(1.5, 10.5, 200)
    for name in ("chung_abel", "brodrick_spiering"):
        f = sn.fit_basquin(name)
        ax.plot(n, sn.amplitude_at(2 * n, f), color=fk.AXIS, linewidth=1.2, zorder=2)
    f = out["sn_fit"]
    ax.plot(n, sn.amplitude_at(2 * n, f), color=MODEL, zorder=4)
    for name, mk in (("chung_abel", "o"), ("brodrick_spiering", "s")):
        data = sn.DATA_SETS[name]
        ax.scatter([r / 2 for _, r in data], [sg * sn.KSI for sg, _ in data], s=30, marker=mk, facecolor=fk.THIRD,
                   edgecolor=SURFACE, linewidth=1.0, zorder=5)
    fk.dots(ax, [5e8], [96.5], color=REF, size=62)
    fk.callout(ax, (5e8, 96.5), (-150, 70), "an independent handbook value,\n96.5 MPa at 5 × 10⁸ cycles", ha="center")
    life = m["fatigue_life_cycles"]
    amp = float(sn.amplitude_at(2 * life, f))
    ax.scatter([life], [amp], s=70, marker="D", facecolor=INK, edgecolor=SURFACE, linewidth=1.2, zorder=6)
    fk.label(ax, life, amp, f"the service cycle:\n{amp:.0f} MPa, about 8 × 10⁹ cycles", dx=6, dy=-12, ha="right", va="top", size=8.5)
    ax.axvline(3e7, color=INK2, linewidth=1.1, zorder=1)
    fk.label(ax, 3e7, 440, "life needed, 3 × 10⁷", dx=5, va="top", color=INK2, size=8.5)
    ax.axvspan(30, 5e4 / 2 * 2, color=INK2, alpha=0.06, linewidth=0, zorder=0.5)
    fk.label(ax, 40, 55, "all the test data is in this range", dx=0, va="bottom", color=INK2, size=8.5)
    fk.label(ax, 3e9, float(sn.amplitude_at(6e9, sn.fit_basquin("brodrick_spiering"))), "each data set on its own", dx=0, dy=12, ha="right", va="bottom", color=INK2, size=8.5)
    ax.set_xlim(30, 3e10)
    ax.set_ylim(50, 500)
    ax.yaxis.set_major_locator(FixedLocator([50, 70, 100, 150, 200, 300, 500]))
    ax.yaxis.set_major_formatter(ScalarFormatter())
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel("cycles to failure")
    ax.set_ylabel("stress amplitude, MPa")
    fk.heading(fig, "The life is an extrapolation far beyond the test data, checked at one independent point",
               "Published tests of 6061-T6, the curve fitted to them, and where the strap's service cycle falls")
    fk.key(fig, [("published test points", "dot", fk.THIRD), ("fitted curve", "line", MODEL), ("independent value", "dot", REF)], y_in=0.66)
    fk.save(fig, "fatigue_sn")


def fin_response():
    """Temperature along the fin, the 3D model against 1D fin theory."""
    from validation import fin_conduction as ref

    run, lab = "20261119-221454_fin_mesh", "p03_element_size_mm-0.25"
    rec = point(run, lab)
    p, m = rec["parameters"], rec["metrics"]
    s = read_series(RUNS / run / "points" / lab / "profile.csv")
    z = s["z_mm"]
    fig, gs = fk.new(fk.HALF, 3.8, top=0.95)
    gs.update(left=0.15, right=0.96)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax)
    ax.plot(z, ref.temperature_C(p, z * 1e-3), color=REF, zorder=3)
    step = max(1, len(z) // 16)
    fk.dots(ax, z[::step], s["T_mean_C"][::step])
    ax.set_xlim(0, z.max() * 1.04)
    ax.set_ylim(56, 82)
    op, L = limits("fin_mesh")["tip_temperature_min_C"]
    fk.limit(ax, L, f"the tip must stay above {L:g} °C", bad="below", axis="y", at=0.03)
    fk.label(ax, z.max(), m["tip_temperature_min_C"], f"tip {m['tip_temperature_min_C']:.1f} °C", dx=-4, dy=10, ha="right", va="bottom", size=8.5)
    ax.set_xlabel("distance from the base, mm")
    ax.set_ylabel("temperature, °C")
    fk.heading(fig, "The 3D model sits on the textbook fin solution", "Temperature along the fin, from the 80 °C base to the tip")
    fk.key(fig, [("fin theory", "line", REF), ("3D model", "dot", MODEL)], y_in=0.66)
    fk.save(fig, "fin_response")


def fin_h_sweep():
    rows = pts("20261119-221655_fin_h_sweep")
    op, L = limits("fin_h_sweep")["tip_temperature_min_C"]
    fig, gs = fk.new(fk.HALF, 3.8, top=0.95)
    gs.update(left=0.15, right=0.96)
    ax = fig.add_subplot(gs[0, 0])
    xs = [r["parameters"]["htc_W_per_m2K"] for _, r, _ in rows]
    ys = [r["metrics"]["tip_temperature_min_C"] for _, r, _ in rows]
    sweep_panel(ax, xs, ys, [ok for *_, ok in rows], op, L, f"the tip must stay above {L:g} °C", fmt="{:.1f}", ylim=(50, 80), at=0.03)
    k = int(np.argmax(np.array(ys) < L))
    cross = xs[k - 1] + (L - ys[k - 1]) * (xs[k] - xs[k - 1]) / (ys[k] - ys[k - 1])
    ax.plot([cross, cross], [50, L], color=INK2, linewidth=0.9, zorder=2)
    fk.label(ax, cross, 51, f"about {cross:.0f}", dx=-5, ha="right", va="bottom", size=8.5)
    fk.label(ax, xs[0], ys[0], "the estimate, 25", dx=-2, dy=-12, ha="left", va="top", color=INK2, size=8.5)
    ax.set_xlabel("air-side heat-transfer coefficient, W/m²K")
    ax.set_ylabel("tip temperature, °C")
    fk.heading(fig, "It takes four times the estimated cooling to fail", "Tip temperature as the air-side coefficient rises")
    fk.save(fig, "fin_h_sweep")


def qc_bump_sweep():
    rows = pts("20261119-085019_qc_speed_bump")
    lim = limits("qc_speed_bump")
    xs = [r["parameters"]["damping_N_s_per_m"] for _, r, _ in rows]
    oks = [ok for *_, ok in rows]
    fig, gs = fk.new(FULL, 3.7, 1, 3, wspace=0.3, top=1.0)
    spec = [("peak_body_accel_m_per_s2", "Peak body acceleration, m/s²", "{:.2f}", (2.4, 9.4), "limit 4.0 m/s²"),
            ("max_suspension_travel_mm", "Suspension travel, mm", "{:.0f}", (0, 48), "limit 40 mm"),
            ("max_tire_load_ratio", "Tire load swing, share of static", "{:.2f}", (0.3, 0.92), "limit 0.70")]
    for k, (metric, title, fmt, ylim, text) in enumerate(spec):
        ax = fig.add_subplot(gs[0, k])
        op, L = lim[metric]
        ys = [r["metrics"][metric] for _, r, _ in rows]
        sweep_panel(ax, xs, ys, oks, op, L, text, fmt=fmt, ylim=ylim, logx=True, at=0.97 if k == 1 else 0.03)
        ax.set_xticks(xs)
        ax.set_xticklabels([f"{x:g}" for x in xs])
        ax.minorticks_off()
        ax.set_xlabel("damper rate, N·s/m")
        fk.panel(ax, title)
    fk.heading(fig, "Over the bump at 18 km/h, 600 to 1000 N·s/m meets all three targets",
               "Each target against damper rate: a stiffer damper passes more of the bump into the body and the tire")
    fk.key(fig, [("meets", "meets", None), ("misses", "misses", None)], y_in=0.66)
    fk.save(fig, "qc_bump_sweep")


def cad_sweep():
    rows = pts("20261119-090540_mounting_plate")
    lim = limits("mounting_plate")
    xs = [r["parameters"]["hole_diameter_mm"] for _, r, _ in rows]
    oks = [ok for *_, ok in rows]
    fig, gs = fk.new(FULL, 3.6, 1, 2, wspace=0.24, top=1.0)
    spec = [("mass_g", "Plate mass, g", "{:.1f}", (128, 160), "limit 150 g"),
            ("edge_distance_ratio", "Edge distance ÷ hole diameter", "{:.2f}", (1.0, 4.2), "at least 2")]
    for k, (metric, title, fmt, ylim, text) in enumerate(spec):
        ax = fig.add_subplot(gs[0, k])
        op, L = lim[metric]
        ys = [r["metrics"][metric] for _, r, _ in rows]
        sweep_panel(ax, xs, ys, oks, op, L, text, fmt=fmt, ylim=ylim, at=0.97 if k == 0 else 0.5)
        ax.set_xticks(xs)
        ax.set_xticklabels([f"{x:g}" for x in xs])
        ax.set_xlabel("hole diameter, mm (M5, M6, M8, M10, M12 clearance)")
        fk.panel(ax, title)
    fk.heading(fig, "Only the 9 mm hole meets both rules", "Bigger holes save weight but eat into the edge distance; smaller ones leave the plate too heavy")
    fk.key(fig, [("meets", "meets", None), ("misses", "misses", None)], y_in=0.66)
    fk.save(fig, "cad_sweep")


def heat_response():
    """Wall and coolant temperature along the heated channel, and the local Nusselt number, against Graetz."""
    from studies.heated_channel import props, wall_profile
    from validation import graetz

    run, lab = "20261121-151154_heated_channel_mesh_r2", "p02_cells_across_gap-160"
    rec = point(run, lab)
    prm, m = rec["parameters"], rec["metrics"]
    s = read_series(RUNS / run / "points" / lab / "cells.csv")
    pr = props(prm)
    xs, tw = wall_profile(s, prm)
    xr = np.linspace(xs[0], xs[-1], 160)
    ref = graetz.thermal_entry(xr * 1e-3, n_cells=400, **pr)
    bulk = lambda x: graetz.bulk_temperature(x * 1e-3, pr["T_in"], pr["q"], pr["H"], pr["U"], pr["rho"], pr["cp"])  # noqa: E731
    fig, gs = fk.new(FULL, 3.9, 1, 2, wspace=0.24, top=1.0)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax)
    pick = np.unique(np.round(np.linspace(0, len(xs) - 1, 26)).astype(int))
    ax.plot(xr, bulk(xr), color=fk.AXIS, zorder=2)
    ax.plot(xr, ref["T_wall"], color=REF, zorder=3)
    fk.dots(ax, xs[pick], tw[pick])
    ax.set_xlim(0, xs.max() * 1.04)
    ax.set_ylim(24, 47.5)
    op, L = limits("heated_channel_mesh_r2")["max_wall_temperature_C"]
    fk.limit(ax, L, f"wall limit {L:g} °C", bad="above", axis="y", at=0.03)
    fk.label(ax, xs.max(), m["max_wall_temperature_C"], f"{m['max_wall_temperature_C']:.2f} °C", dx=-6, dy=-10, ha="right", va="top", size=8.5)
    fk.label(ax, xs.max() * 0.62, float(bulk(np.array(xs.max() * 0.62))), "the coolant, on average", dx=4, dy=-8, va="top", color=INK2, size=8.5)
    fk.label(ax, xs.max() * 0.3, float(np.interp(xs.max() * 0.3, xr, ref["T_wall"])), "the wall", dx=-4, dy=8, ha="right", va="bottom", color=INK2, size=8.5)
    ax.set_xlabel("distance from the start of heating, mm")
    ax.set_ylabel("temperature, °C")
    fk.panel(ax, "Wall and coolant temperature")

    ax = fig.add_subplot(gs[0, 1])
    fk.style(ax)
    nu = pr["q"] * 2 * pr["H"] / (pr["k"] * (tw - bulk(xs)))
    ax.axhline(graetz.NU_FULLY_DEVELOPED, color=fk.AXIS, linewidth=1.2, zorder=1)
    ax.plot(xr, ref["Nu"], color=REF, zorder=3)
    fk.dots(ax, xs[pick], nu[pick])
    ax.set_xlim(0, xs.max() * 1.04)
    ax.set_ylim(7, 20)
    fk.label(ax, xs.max(), graetz.NU_FULLY_DEVELOPED, "the textbook value for settled flow, 8.24", dx=0, dy=-6, ha="right", va="top", color=INK2, size=8.5)
    fk.callout(ax, (xs.max(), float(nu[-1])), (-70, 46), f"still settling at the end\nof the heating: {nu[-1]:.2f}", ha="center")
    ax.set_xlabel("distance from the start of heating, mm")
    ax.set_ylabel("Nusselt number (how well the flow cools the wall)")
    fk.panel(ax, "Heat transfer along the channel")
    fk.heading(fig, f"The wall peaks at {m['max_wall_temperature_C']:.2f} °C, just under its limit, and matches the thermal-entry solution",
               "A 1 mm water channel heated on both walls at 30 kW/m², against the Graetz solution")
    fk.key(fig, [("Graetz solution", "line", REF), ("model", "dot", MODEL)], y_in=0.66)
    fk.save(fig, "heat_response")



# ---------------------------------------------------------------------------------------- dynamics

def qc_liftoff():
    """The wheel leaving the road at 36 km/h: tire load and body acceleration, model against the exact solution."""
    from studies.quarter_car import body_accel

    run, lab = "20261120-105126_qc_bump_liftoff", "p00_damping_N_s_per_m-600"
    rec = point(run, lab)
    prm = rec["parameters"]
    s = read_series(RUNS / run / "points" / lab / "timeseries.csv")
    r = read_series(RUNS / run / "points" / lab / "reference.csv")
    rs = {"t_s": r["t_s"], "zs_m": r["zs_ref_m"], "vs_m_per_s": r["vs_ref_m_per_s"], "zu_m": r["zu_ref_m"],
          "vu_m_per_s": r["vu_ref_m_per_s"], "zr_m": np.interp(r["t_s"], s["t_s"], s["zr_m"])}
    W = (prm["sprung_mass_kg"] + prm["unsprung_mass_kg"]) * 9.80665
    load = lambda q: np.maximum(0.0, 1 + prm["tire_stiffness_N_per_m"] * (q["zr_m"] - q["zu_m"]) / W)  # noqa: E731
    tmax = 1.2
    sel, rsel = s["t_s"] <= tmax, rs["t_s"] <= tmax
    fig, gs = fk.new(FULL, 5.0, 2, 1, hspace=0.42, top=1.0)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax)
    ld = load(s)
    air = (ld <= 1e-9) & sel
    edges = np.flatnonzero(np.diff(np.concatenate([[0], air.astype(int), [0]])))
    for a, b in zip(edges[::2], edges[1::2]):
        ax.axvspan(s["t_s"][a], s["t_s"][min(b, len(ld) - 1)], color=fk.FAIL, alpha=0.10, linewidth=0, zorder=0.5)
    ax.axhline(1.0, color=fk.AXIS, linewidth=1.0, zorder=1)
    ax.plot(rs["t_s"][rsel], load(rs)[rsel], color=REF, zorder=3)
    ax.plot(s["t_s"][sel], ld[sel], color=MODEL, linewidth=1.3, zorder=4)
    k = int(np.argmax(np.where(sel, ld, 0)))
    fk.label(ax, s["t_s"][k], ld[k], f"the landing: {ld[k]:.1f} times the static load", dx=8, dy=-2, size=8.5)
    if len(edges) >= 4:
        fk.label(ax, s["t_s"][min(edges[3], len(ld) - 1)], 0.0, "shaded: the wheel is in the air", dx=52, dy=3, va="bottom", color=INK2, size=8.5)
    ax.set_xlim(0, tmax)
    ax.set_ylim(0, ld[sel].max() * 1.12)
    ax.set_ylabel("tire load ÷ static load")
    ax.tick_params(labelbottom=False)
    fk.panel(ax, "Load on the tire")

    ax = fig.add_subplot(gs[1, 0])
    fk.style(ax)
    acc, acc_ref = body_accel(s, prm), body_accel(rs, prm)
    ax.axhline(0, color=fk.AXIS, linewidth=1.0, zorder=1)
    ax.plot(rs["t_s"][rsel], acc_ref[rsel], color=REF, zorder=3)
    ax.plot(s["t_s"][sel], acc[sel], color=MODEL, linewidth=1.3, zorder=4)
    ax.set_xlim(0, tmax)
    lim = max(6.2, float(np.abs(acc[sel]).max()) * 1.15)
    ax.set_ylim(-lim, lim)
    fk.limit(ax, 4.0, "comfort limit 4.0 m/s²", bad="above", axis="y", at=0.985)
    ax.axhspan(-lim, -4.0, color=fk.FAIL, alpha=0.07, linewidth=0, zorder=0.5)
    ax.axhline(-4.0, color=INK2, linewidth=1.1, zorder=1)
    ax.set_xlabel("time, s")
    ax.set_ylabel("body acceleration, m/s²")
    fk.panel(ax, "Acceleration of the body")
    fk.heading(fig, "At 36 km/h the wheel leaves the road twice, and the landing is the worst moment for the tire",
               "The lightest damper, 600 N·s/m: the simulation follows the exact solution through both lift-offs")
    fk.key(fig, [("exact solution", "line", REF), ("model", "line", MODEL)], y_in=0.66)
    fk.save(fig, "qc_liftoff")


def qc_iso():
    """Rough road at 72 km/h: the body's vibration, and its spectrum against the frequency-response prediction."""
    from studies.quarter_car import Road, body_accel, window_slice
    from validation import quarter_car_reference as ref

    run, lab = "20261120-124907_qc_iso_road", "p01_damping_N_s_per_m-1000"
    rec = point(run, lab)
    prm = rec["parameters"]
    s = read_series(RUNS / run / "points" / lab / "timeseries.csv")
    t = s["t_s"]
    w = window_slice(t, prm)
    acc = body_accel(s, prm)[w]
    tw = t[w]
    road = Road(prm)
    f = road.sines.freq_hz
    expected = np.abs(ref.frequency_response(prm, f)["body_accel"]) * road.sines.amp_m
    fig, gs = fk.new(FULL, 3.9, 1, 2, width_ratios=(1, 1.25), wspace=0.24, top=1.0)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax)
    sel = tw <= tw[0] + 4.0
    ax.axhline(0, color=fk.AXIS, linewidth=1.0, zorder=1)
    ax.plot(tw[sel] - tw[0], acc[sel], color=MODEL, linewidth=1.1, zorder=4)
    ax.set_xlim(0, 4.0)
    ax.set_xlabel("time, s")
    ax.set_ylabel("body acceleration, m/s²")
    fk.panel(ax, "Four seconds of the ride")

    ax = fig.add_subplot(gs[0, 1])
    fk.style(ax)
    ax.set_yscale("log")
    n = len(acc)
    spec = np.abs(np.fft.rfft(acc) * 2 / n)
    idx = np.searchsorted(np.fft.rfftfreq(n, d=tw[1] - tw[0]), f)
    ax.plot(f, expected, color=REF, zorder=3)
    pick = np.unique(np.round(np.geomspace(1, len(f), 46)).astype(int) - 1)
    fk.dots(ax, f[pick], spec[idx][pick], size=24)
    ax.set_xlim(0, 20.5)
    ax.set_ylim(0.02, 1.0)
    ax.set_yticks([0.02, 0.05, 0.1, 0.2, 0.5, 1.0])
    ax.set_yticklabels(["0.02", "0.05", "0.1", "0.2", "0.5", "1"])
    ax.minorticks_off()
    kb = int(np.argmax(expected * (f < 4)))
    fk.label(ax, f[kb], expected[kb], f"the body bouncing,\nabout {f[kb]:.1f} Hz", dx=10, dy=4, color=INK2, size=8.5)
    kw = int(np.argmax(expected * (f > 7)))
    fk.label(ax, f[kw], expected[kw], f"the wheel hopping,\nabout {f[kw]:.0f} Hz", dx=0, dy=12, ha="center", va="bottom", color=INK2, size=8.5)
    ax.set_xlabel("frequency, Hz")
    ax.set_ylabel("acceleration at each frequency, m/s²")
    fk.panel(ax, "What the ride is made of")
    fk.heading(fig, "On a rough road the simulation matches the prediction at every frequency",
               "An average-quality road at 72 km/h with the 1000 N·s/m damper: body acceleration, and its content by frequency")
    fk.key(fig, [("frequency-response prediction", "line", REF), ("simulation", "dot", MODEL)], y_in=0.66)
    fk.save(fig, "qc_iso")


# ---------------------------------------------------------------------------------------- thermal chain, pipe

def coldplate_response():
    """The plate's temperature field, its face temperatures, and its thermal stress against beam theory."""
    from studies.cold_plate import interior_window, stress_reference, to_grid, von_mises

    run, lab = "20261121-094235_cold_plate_mesh_r1", "p02_cells_across_gap-80"
    rec = point(run, lab)
    p, m = rec["parameters"], rec["metrics"]
    xs, ys, g = to_grid(read_series(RUNS / run / "points" / lab / "plate_nodes.csv"))
    lim = limits("cold_plate_mesh_r1")
    fig, gs = fk.new(FULL, 6.2, 2, 2, hspace=0.5, wspace=0.24, top=1.0, height_ratios=(0.72, 1))
    ax = fig.add_subplot(gs[0, :])
    fk.style(ax, grid="")
    X, Y = np.meshgrid(xs, ys - ys.min(), indexing="ij")
    mesh = ax.pcolormesh(X, Y, g["T_C"], cmap="YlOrRd", shading="gouraud", rasterized=True)
    cb = fig.colorbar(mesh, ax=ax, pad=0.015, aspect=10)
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=0, labelsize=8.5, colors=INK2)
    cb.set_label("temperature, °C", color=INK2, fontsize=9)
    Lf = float(p["footprint_length_mm"])
    top = float((ys - ys.min()).max())
    ax.plot([0, Lf], [top, top], color=INK, linewidth=2.2, solid_capstyle="butt", clip_on=False, zorder=5)
    ax.text(Lf, top * 1.06, "components heat this face, over the 50 mm footprint", ha="right", va="bottom", fontsize=8.5, color=INK2)
    ax.text(xs.min() + 1, -top * 0.16, "coolant runs along this face, left to right", ha="left", va="top", fontsize=8.5, color=INK2)
    ax.set_ylim(0, top)
    ax.set_yticks([0, top])
    ax.set_yticklabels(["0", f"{top:g}"])
    ax.set_ylabel("through the\nplate, mm")
    ax.tick_params(labelbottom=False)
    fk.panel(ax, "Temperature in the plate")

    ax = fig.add_subplot(gs[1, 0])
    fk.style(ax)
    ax.plot(xs, g["T_C"][:, -1], color=MODEL, zorder=4)
    ax.plot(xs, g["T_C"][:, 0], color=fk.THIRD, zorder=4)
    ax.set_xlim(xs.min(), xs.max())
    ax.set_ylim(24, 47.5)
    op, L = lim["component_face_max_temperature_C"]
    fk.limit(ax, L, f"limit {L:g} °C", bad="above", axis="y", at=0.03)
    k = int(np.argmax(g["T_C"][:, -1]))
    fk.label(ax, xs[k], g["T_C"][k, -1], f"{m['component_face_max_temperature_C']:.2f} °C", dx=0, dy=8, ha="center", va="bottom", size=8.5)
    fk.label(ax, xs[len(xs) // 3], g["T_C"][len(xs) // 3, -1], "component face", dx=-4, dy=10, ha="right", va="bottom", color=INK2, size=8.5)
    fk.label(ax, xs[len(xs) // 2], g["T_C"][len(xs) // 2, 0], "coolant face", dx=6, dy=-10, va="top", color=INK2, size=8.5)
    ax.set_xlabel("distance along the flow, mm")
    ax.set_ylabel("temperature, °C")
    fk.panel(ax, "The plate's two faces")

    ax = fig.add_subplot(gs[1, 1])
    fk.style(ax)
    vm = von_mises(g["sxx_MPa"], g["syy_MPa"], g["szz_MPa"], g["sxy_MPa"])
    ref = stress_reference(p, xs, ys, g["T_C"])
    win = interior_window(xs, p)
    ax.axvspan(xs[0], xs[win][0], color=fk.GRID, linewidth=0, zorder=0.6)
    ax.axvspan(xs[win][-1], xs[-1], color=fk.GRID, linewidth=0, zorder=0.6)
    ax.plot(xs[win], ref["von_mises"][win][:, -1], color=REF, zorder=3)
    ax.plot(xs, vm[:, -1], color=MODEL, linewidth=1.4, zorder=4)
    ax.set_xlim(xs.min(), xs.max())
    ax.set_ylim(0, 72)
    op, L = lim["interior_von_mises_max_MPa"]
    fk.limit(ax, L, f"limit {L:g} MPa", bad="above", axis="y", at=0.5)
    fk.label(ax, xs[len(xs) // 2], vm[len(xs) // 2, -1], f"peak {m['interior_von_mises_max_MPa']:.1f} MPa", dx=0, dy=-10, ha="center", va="top", size=8.5)
    fk.label(ax, xs[0], 4, "near the\nclamps:\nnot assessed", dx=3, va="bottom", color=INK2, size=8)
    ax.set_xlabel("distance along the flow, mm")
    ax.set_ylabel("stress on the component face, MPa")
    fk.panel(ax, "Thermal stress, plate held at both ends")
    fk.heading(fig, "The plate stays 4 °C under its limit, and the stress it builds by not being free to expand is 46.8 MPa",
               "The last two stages of the chain: conduction through the plate, then the stress from holding it at both ends")
    fk.key(fig, [("beam theory", "line", REF), ("model", "line", MODEL)], y_in=0.66)
    fig.savefig(fk.OUT / "fig_coldplate_response.svg", format="svg", dpi=300, metadata={"Date": None, "Creator": None})
    fk.plt.close(fig)
    print("fig coldplate_response")


def pipe_friction():
    """Friction factor against Prandtl's law: the mesh study, across Reynolds numbers, and wall-function placement."""
    from matplotlib.ticker import NullFormatter, ScalarFormatter

    def dev(run, key):
        rows = sorted((r for _, r, _ in pts(run)), key=lambda r: r["parameters" if key != "yplus_first_cell" else "metrics"][key])
        return rows

    fig, gs = fk.new(FULL, 3.9, 1, 3, wspace=0.16, top=1.0)
    axes = [fig.add_subplot(gs[0, k]) for k in range(3)]
    for ax in axes:
        fk.style(ax)
        ax.set_ylim(-7.4, 7.4)
        ax.axhspan(5, 7.4, color=fk.FAIL, alpha=0.07, linewidth=0, zorder=0.5)
        ax.axhspan(-7.4, -5, color=fk.FAIL, alpha=0.07, linewidth=0, zorder=0.5)
        for y in (-5, 5):
            ax.axhline(y, color=INK2, linewidth=1.1, zorder=1)
        ax.axhline(0, color=fk.AXIS, linewidth=1.0, zorder=1)
    for ax in axes[1:]:
        ax.tick_params(labelleft=False)
    axes[0].set_ylabel("friction factor against Prandtl's law, %")
    fk.label(axes[0], 0.027, 5, "limit ±5 %", dx=0, dy=6, ha="right", va="bottom", color=INK2, size=8.5)

    ax = axes[0]
    first, rev = dev("20261122-104218_pipe_rans_mesh", "n_radial"), dev("20261122-153857_pipe_rans_mesh_r2", "n_radial")
    fin = dev("20261122-202459_pipe_rans_mesh_r3", "n_radial")
    seen = {}
    for rows in (first, rev, fin):
        for r in rows:
            seen[r["parameters"]["n_radial"]] = r["metrics"]["friction_dev_prandtl_pct"]
    ns = sorted(seen)
    ax.plot([1 / n for n in ns], [seen[n] for n in ns], color=MODEL, linewidth=1.6, alpha=0.5, zorder=3)
    fk.dots(ax, [1 / n for n in ns], [seen[n] for n in ns], size=44)
    place = {40: (6, 8, "left", "bottom"), 80: (6, -9, "left", "top"), 160: (7, -6, "left", "top"),
             320: (0, -10, "center", "top"), 640: (7, 3, "left", "bottom")}
    for n in ns:
        dx, dy, ha, va = place.get(n, (6, -9, "left", "top"))
        fk.label(ax, 1 / n, seen[n], f"{n}", dx=dx, dy=dy, ha=ha, va=va, color=INK2, size=8.5)
    v = json.loads((RUNS / "20261122-202459_pipe_rans_mesh_r3" / "verification.json").read_text(encoding="utf-8"))
    u = v["run_check_detail"]["friction_factor"]
    m0 = fin[0]["metrics"]
    pr = m0["friction_factor"] / (1 + m0["friction_dev_prandtl_pct"] / 100)
    ye, ue = 100 * (u["extrapolated"] / pr - 1), 100 * u["uncertainty"] * u["extrapolated"] / pr
    ax.errorbar([0.0006], [ye], yerr=[ue], color=INK, marker="D", markersize=6, capsize=3, linewidth=1.2, zorder=5)
    fk.label(ax, 0.0006, ye + ue, f"extrapolated to zero\ncell size: {ye:+.1f} ± {ue:.1f} %", dx=8, dy=2, va="bottom", size=8.5)
    fk.label(ax, 1 / ns[1], seen[ns[1]], "one mesh alone\nreads −0.9 %", dx=-4, dy=-22, ha="center", va="top", color=INK2, size=8.5)
    ax.set_xlim(0, 0.028)
    ax.set_xlabel("1 ÷ cells across the radius (finer to the left)")
    fk.panel(ax, "Refining the mesh")
    mesh_ax = ax

    ax = axes[1]
    rows = [r for _, r, _ in pts("20261122-104744_pipe_rans_reynolds")]
    for treat, color, text, dy in (("low_re", MODEL, "wall layer resolved", 12), ("wall_function", REF, "wall functions", -12)):
        sel = sorted((r for r in rows if r["parameters"]["wall_treatment"] == treat), key=lambda r: r["parameters"]["reynolds_number"])
        xs = [r["parameters"]["reynolds_number"] for r in sel]
        ys = [r["metrics"]["friction_dev_prandtl_pct"] for r in sel]
        ax.plot(xs, ys, color=color, linewidth=1.6, alpha=0.5, zorder=3)
        fk.dots(ax, xs, ys, color=color, size=44)
        fk.label(ax, xs[-1], ys[-1], text, dx=0, dy=dy, ha="right", va="bottom" if dy > 0 else "top", color=INK2, size=8.5)
    ax.set_xscale("log")
    ax.set_xlim(1e4, 4e6)
    ax.set_xlabel("Reynolds number")
    fk.panel(ax, "Across flow speeds")

    ax = axes[2]
    rows = dev("20261122-140211_pipe_rans_wf_yplus", "yplus_first_cell")
    xs = [r["metrics"]["yplus_first_cell"] for r in rows]
    ys = [r["metrics"]["friction_dev_prandtl_pct"] for r in rows]
    ax.plot(xs, ys, color=REF, linewidth=1.6, alpha=0.5, zorder=3)
    fk.dots(ax, xs, ys, color=REF, size=44)
    ax.set_xscale("log")
    ax.set_xlim(20, 300)
    ax.set_xticks([30, 50, 100, 200])
    ax.xaxis.set_major_formatter(ScalarFormatter())
    ax.xaxis.set_minor_formatter(NullFormatter())
    fk.label(ax, xs[len(xs) // 2], ys[len(xs) // 2], "about 5 % low wherever\nthe first cell sits", dx=0, dy=14, ha="center", va="bottom", color=INK2, size=8.5)
    ax.set_xlabel("where the first cell sits (y+)")
    fk.panel(ax, "Wall functions: moving the first cell")
    fk.heading(fig, "Resolved at the wall, the model lands 2.4 % above the measured law; wall functions sit 5 % low",
               "Smooth-pipe friction factor from the turbulence model against Prandtl's law, the fit to Nikuradse's measurements")
    fk.key(fig, [("wall layer resolved", "dot", MODEL), ("wall functions", "dot", REF)], y_in=0.66)
    thumb(fig, mesh_ax, "pipe")
    fk.save(fig, "pipe_friction")


# ---------------------------------------------------------------------------------------- study 20, the motor

def motor_comparison():
    """The client-data model against the laboratory's test: back-EMF over speed and locked-rotor torque over current.

    Back-EMF from the open-circuit run (fundamental, line to line); torque as the test reports it, the largest over
    shaft angle with the rotor locked, from scripts/motor_locked_rotor.py on the torque run's saved torque."""
    import re
    import subprocess
    oc = point("20261123-141642_motor_prius_rev5_oc", "p00_gap0775")["metrics"]["back_emf_LL_rms_per_krpm_V"]
    oc2 = point("20261123-141642_motor_prius_rev5_oc", "p01_gap0730")["metrics"]["back_emf_LL_rms_per_krpm_V"]
    ref = 89.38                                  # the test's fundamental, V rms line to line per 1000 rpm (CLIENT_DATA.md)
    emf = read_series(REPO / "validation" / "motor_ornl" / "tm2006_423_back_emf.csv")
    out = subprocess.run([sys.executable, str(REPO / "scripts" / "motor_locked_rotor.py"),
                          str(RUNS / "20261123-151023_motor_prius_rev5_torque")], capture_output=True, text=True, check=True).stdout
    rows = [tuple(map(float, m)) for m in re.findall(r"(\d+) A peak:.*locked-rotor max\s+([\d.]+) N m.*ORNL (\d+):", out)]
    assert len(rows) == 7, out
    I, T, R = (np.array(c) for c in zip(*rows))
    e = 100 * (T / R - 1)
    fig, gs = fk.new(FULL, 3.9, 1, 2, wspace=0.28, top=1.0)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax)
    rpm = np.array([0, 6200.0])
    ax.plot(rpm, oc * rpm / 1000, color=MODEL, zorder=3)
    fk.dots(ax, emf["motor_shaft_speed_rpm"], emf["back_emf_Vrms"], color=REF, size=40)
    ax.set_xlim(0, 6300)
    ax.set_ylim(0, 720)
    fk.label(ax, 4200, oc * 4.2, f"model\n{oc:.1f} V per 1,000 rpm\n({oc2:.1f} at a 0.730 mm gap)", dx=-8, dy=6, ha="right", va="bottom", color=INK2, size=8.5)
    fk.label(ax, 5000, ref * 5.0, f"measured\n{ref:.1f}", dx=14, dy=-22, va="top", color=INK2, size=8.5)
    ax.set_xlabel("speed, rpm")
    ax.set_ylabel("back-EMF, V rms line to line")
    fk.panel(ax, f"Back-EMF: {100 * (oc / ref - 1):+.1f} % (limit 5 %)")
    emf_ax = ax
    ax = fig.add_subplot(gs[0, 1])
    fk.style(ax)
    ax.plot(I, T, color=MODEL, zorder=3)
    fk.dots(ax, I, R, color=REF, size=40)
    ax.set_xlim(35, 265)
    ax.set_ylim(0, 480)
    fk.label(ax, I[0], T[0], f"{e[0]:+.0f} %", dx=0, dy=10, ha="center", va="bottom", size=8.5)
    fk.label(ax, I[-1], T[-1], f"{e[-1]:+.0f} %", dx=-4, dy=8, ha="right", va="bottom", size=8.5)
    ax.set_xlabel("current, A peak")
    ax.set_ylabel("locked-rotor torque, N m")
    band = (e > 16) & (e < 20)
    fk.panel(ax, f"Torque: {e[band].min():.0f} to {e[band].max():.0f} % high at {band.sum()} of {len(e)} currents (limit 10 %)")
    fk.heading(fig, "Built from the client's data, the model reads about 18 % high on both back-EMF and torque",
               "2D FEMM model against Oak Ridge National Laboratory's test; torque as the test reports it, the largest over shaft angle")
    fk.key(fig, [("measured", "dot", REF), ("model", "line", MODEL)], y_in=0.66)
    thumb(fig, emf_ax, "motor")
    fk.save(fig, "motor_comparison")


def motor_efficiency():
    """The client-data model's efficiency map, hot, with the rated-power line; beside it, how far the model sits from the
    laboratory's 393 measured points. The per-point comparison comes from scripts/export_motor_eff_points.py, which
    repeats the study's scoring and is gated on its recorded median."""
    import matplotlib

    run, lab = "20261124-062847_motor_prius_efficiency_rev5", "p01_hot"
    rec = point(run, lab)
    so, m = rec["solver_outputs"], rec["metrics"]
    s = read_series(RUNS / run / "points" / lab / "efficiency_map.csv")
    sp, tq = np.unique(s["speed_rpm"]), np.unique(s["target_torque_Nm"])
    Z = np.full((len(tq), len(sp)), np.nan)
    Z[np.searchsorted(tq, s["target_torque_Nm"]), np.searchsorted(sp, s["speed_rpm"])] = s["efficiency_pct"]
    cmp_ = json.loads((REPO / "build" / "drawings" / "motor_eff_vs_ornl.json").read_text(encoding="utf-8"))
    scored = json.loads((REPO / "validation" / "motor_ornl" / "rev5_efficiency_vs_ornl.json").read_text(encoding="utf-8"))["ornl"]
    assert cmp_["summary"]["hot_minus_ornl_median_pts"] == scored["hot_minus_ornl_median_pts"]
    pts = cmp_["points"]
    gap = np.array([p["hot"] - p["ornl_pct"] for p in pts])
    med = float(np.median(gap))
    fig, gs = fk.new(FULL, 4.5, 1, 2, wspace=0.42, top=0.78, width_ratios=[1.55, 1])
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax, grid="")
    levels = [80, 85, 88, 90, 92, 93, 94, 95, 96, 97]
    cmap = matplotlib.colormaps[fk.SEQ].resampled(len(levels))
    norm = matplotlib.colors.BoundaryNorm(levels, cmap.N, extend="min")
    mesh = ax.pcolormesh(sp, tq, np.ma.masked_invalid(Z), cmap=cmap, norm=norm, shading="nearest", rasterized=True)
    cb = fig.colorbar(mesh, ax=ax, pad=0.02, aspect=18, ticks=levels, extend="min")
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=0, labelsize=8.5, colors=INK2)
    cb.set_label("efficiency, %", color=INK2, fontsize=9)
    ax.scatter([p["speed_rpm"] for p in pts], [p["torque_Nm"] for p in pts], s=5, facecolor="none", edgecolor=INK,
               linewidth=0.5, alpha=0.55, zorder=3)
    ax.plot(so["speeds_rpm"], so["t_max_design_Nm"], color=INK, linewidth=1.6, zorder=4)
    n50 = np.linspace(50e3 / (400 * np.pi / 30), 6000, 200)
    ax.plot(n50, 50e3 / (n50 * np.pi / 30), color=REF, linewidth=1.6, linestyle=(0, (4, 2.5)), zorder=4)
    fk.label(ax, 2900, 470, f"black: most torque within\n212 A and 500 V, "
             f"{m['min_power_rated_speed_range_kW']:.1f} kW\nat the worst speed\norange: the rated 50 kW",
             va="top", color=INK, size=8.5)
    ax.scatter([m["peak_efficiency_speed_rpm"]], [m["peak_efficiency_torque_Nm"]], s=44, facecolor=SURFACE, edgecolor=INK,
               linewidth=1.3, zorder=5)
    fk.label(ax, m["peak_efficiency_speed_rpm"], m["peak_efficiency_torque_Nm"], f"peak {m['peak_efficiency_pct']:.1f} %",
             dx=8, dy=-2, size=8.5, color=SURFACE, bold=True)
    ax.set_xlim(sp.min() - 125, sp.max() + 125)
    ax.set_ylim(0, 480)
    ax.set_xlabel("speed, rpm")
    ax.set_ylabel("torque, N m")
    fk.panel(ax, "The model's map, hot; circles: where the test measured")
    ax = fig.add_subplot(gs[0, 1])
    fk.style(ax)
    ax.axvspan(-2, 2, color=MODEL, alpha=0.10, linewidth=0, zorder=0.5)
    ax.hist(gap, bins=np.arange(-4.5, 11.01, 0.5), color=fk.HELD, edgecolor=SURFACE, linewidth=0.8, zorder=2)
    top = ax.get_ylim()[1] * 1.12
    ax.set_ylim(0, top)
    ax.axvline(med, color=fk.FAIL, linewidth=1.6, zorder=3)
    fk.label(ax, med, top * 0.97, f"median +{med:.1f}", dx=5, va="top", color=INK, size=8.5, bold=True)
    within = int(np.sum(np.abs(gap) <= 2))
    fk.label(ax, 0, top * 0.97, f"goal:\nwithin 2\n{within} of {len(gap)}", dx=0, va="top", ha="center", color=INK2, size=8.5)
    ax.set_xlim(-4.5, 11)
    ax.set_xlabel("model minus test, efficiency points")
    ax.set_ylabel("test points")
    fk.panel(ax, f"Against the {len(gap)} test points")
    fk.heading(fig, f"Rated power holds, but the model's efficiency reads {med:.1f} points above the test",
               "The client-data model, motor only (copper and iron loss), winding 100 °C, magnets 80 °C; Oak Ridge National Laboratory's test")
    fig.savefig(fk.OUT / "fig_motor_efficiency.svg", format="svg", dpi=300, metadata={"Date": None, "Creator": None})
    fk.plt.close(fig)
    print("fig motor_efficiency")


def motor_airgap():
    """ORNL's measured no-load air-gap flux density (TM-2004/137 Fig. 13) against the client-data model, by stator slot,
    from scripts/motor_fig13.py's output. The slot-1 angle isn't stored relative to the saved profile, so it is
    recovered here and gated: the profile sampled at the slots must give the study's 13 model values back."""
    d = json.loads((REPO / "validation" / "motor_ornl" / "fig13" / "fig13_comparison.json").read_text(encoding="utf-8"))
    g, s = np.array(d["ornl_2004_gauss"]), np.array(d["model_gauss"])
    prof = d["model_profile_one_pole_pair"]
    pa, pb = np.array(prof["angle_deg"]), np.array(prof["br_T"]) * 1e4
    period, pitch = pa[-1], 360.0 / 48
    f = lambda t: np.interp(np.mod(t, period), pa, pb)  # noqa: E731
    cand = np.linspace(0, period, 7201)
    z = float(cand[int(np.argmin([np.abs(f(c + pitch * np.arange(13)) - s).max() for c in cand]))])
    err = np.abs(f(z + pitch * np.arange(13)) - s).max() / d["plateau_model_gauss"]
    assert err < 0.01, f"the saved profile doesn't reproduce the study's slot values ({err:.3%})"
    ratio = d["plateau_ratio_model_over_ornl"]
    assert abs(d["plateau_model_gauss"] / d["plateau_ornl_gauss"] - ratio) < 1e-9
    plateau_slots = [2, 3, 4, 8, 9, 10]          # 0-based: the level part of each half, slots 3-5 and 9-11
    assert max(abs(d["normalised_difference_by_slot"][i]) for i in plateau_slots) < 0.035
    slot = np.linspace(1, 13, 1201)
    ang = z + (slot - 1) * pitch
    fig, gs = fk.new(FULL, 4.0, 1, 1, top=0.80)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax)
    ax.axhline(0, color=GRID, linewidth=0.8, zorder=1)
    k = np.arange(1, 14)
    ax.plot(slot, f(ang) / 1e4, color=MODEL, linewidth=0.8, alpha=0.28, zorder=2)
    ax.plot(k, s / 1e4, color=MODEL, linewidth=1.8, zorder=3)
    ax.scatter(k, s / 1e4, s=34, facecolor=SURFACE, edgecolor=MODEL, linewidth=1.5, zorder=4)
    ax.plot(k, s / ratio / 1e4, color=MODEL, linewidth=1.3, linestyle=(0, (4, 2.5)), zorder=3)
    ax.scatter(k, g / 1e4, marker="s", s=46, color=REF, edgecolor=SURFACE, linewidth=1.0, zorder=5)
    fk.label(ax, 9.5, s[8] / 1e4, "the model", dy=11, ha="center", color=INK, size=9, bold=True)
    fk.label(ax, 9.5, g[8] / 1e4, f"the test (squares), and the\nmodel ÷ {ratio:.3f} (dashed)", dy=-20, ha="center", va="top",
             color=INK, size=9, bold=True)
    fk.label(ax, 13.2, -0.22, f"where the field is level:\nmodel {d['plateau_model_gauss'] / 1e4:.3f} T,"
             f" test {d['plateau_ornl_gauss'] / 1e4:.3f} T;\nsame shape within 3.4 %", ha="right", va="top", color=INK2, size=8.5)
    fk.label(ax, 0.75, 0.93, "faint line: the model's full field,\nwith a dip at each slot opening", va="top", color=INK2, size=8)
    ax.set_xlim(0.6, 13.4)
    ax.set_xticks(k)
    ax.set_ylim(-1.05, 1.05)
    ax.set_xlabel("stator slot (one pair of poles)")
    ax.set_ylabel("radial flux density, T")
    fk.heading(fig, f"The model's air-gap field has the test's shape, {100 * (ratio - 1):.1f} % stronger",
               "No current in the winding; flux density at the stator bore; Oak Ridge National Laboratory's test "
               "against the client-data model")
    fig.savefig(fk.OUT / "fig_motor_airgap.svg", format="svg", dpi=300, metadata={"Date": None, "Creator": None})
    fk.plt.close(fig)
    print(f"fig motor_airgap (slot-1 angle recovered to {err:.2%} of the plateau)")


def oring_seal():
    """The O-ring face seal at the three corners of its tolerance stack: the contact pressure across the cover, the
    closing force as the cover comes down, and the groove fill, each against its requirement. Gated on the saved
    profile and force history reproducing the recorded peak pressure and closing force."""
    import matplotlib

    run, case = "20261124-100619_oring_seal_corners", "oring_seal_corners"
    L = limits(case)
    ok = verified(run)
    names = [("p00_loosest", "loosest"), ("p01_nominal", "nominal"), ("p02_tightest", "tightest")]
    blues = matplotlib.colormaps[fk.SEQ]
    cols = [blues(0.45), blues(0.68), blues(0.92)]
    recs = []
    for lab, nm in names:
        r = point(run, lab)
        a = np.loadtxt(RUNS / run / "points" / lab / "contact_profile.csv", delimiter=",", skiprows=1)
        fh = r["solver_outputs"]["force_history"]
        m = r["metrics"]
        assert abs(a[:, 1].max() - m["peak_contact_pressure_MPa"]) < 1e-9
        assert abs(fh["force_N_per_mm"][-1] - m["force_per_length_N_per_mm"]) < 1e-9
        recs.append((nm, r, a, fh, m))
    fig, gs = fk.new(FULL, 4.3, 1, 3, wspace=0.42, top=0.80, width_ratios=[1.25, 1.1, 0.85])

    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax)
    ax.set_xlim(22.4, 29.0)
    ax.set_ylim(0, 4.0)
    fk.limit(ax, L["peak_contact_pressure_MPa"][1], f"{L['peak_contact_pressure_MPa'][1]:g} MPa needed", bad="below", axis="y", at=0.02)
    r_out = recs[0][1]["solver_outputs"]["groove"]["r_out"]
    ax.axvline(r_out, color=INK, linewidth=1.6, zorder=2)
    fk.label(ax, r_out, 3.85, "groove's\nouter wall", dx=-4, ha="right", va="top", color=INK2, size=8.5)
    for (nm, r, a, fh, m), c in zip(recs, cols):
        ax.plot(a[:, 0], a[:, 1], color=c, linewidth=1.8, zorder=3)
        fk.label(ax, 22.55, m["peak_contact_pressure_MPa"], f"{nm} {m['peak_contact_pressure_MPa']:.2f}",
                 color=INK, size=8.5, bold=nm == "loosest")
    ax.set_xlabel("radius, mm")
    ax.set_ylabel("contact pressure on the cover, MPa")
    fk.panel(ax, "Sealing pressure: the loosest governs")

    ax = fig.add_subplot(gs[0, 1])
    fk.style(ax)
    ax.set_xlim(0, 32)
    ax.set_ylim(0, 13.5)
    req = {q["id"]: q["limit"] for q in tomllib.loads((REPO / "cases" / f"{case}.toml").read_text(encoding="utf-8"))["requirements"]}
    lo, hi = req["REQ-E1a"], req["REQ-E1b"]        # both squeeze limits share one metric, so limits() keeps only one
    ax.axvspan(lo, hi, color=MODEL, alpha=0.08, linewidth=0, zorder=0.5)
    fk.label(ax, (lo + hi) / 2, 9.3, "squeeze\nallowed", ha="center", color=INK2, size=8.5)
    fk.limit(ax, L["force_per_length_N_per_mm"][1], "bolt budget, 12 N/mm", bad="above", axis="y", at=0.97)
    for (nm, r, a, fh, m), c in zip(recs, cols):
        s = 100 * np.array(fh["squeeze"])
        ax.plot(s, fh["force_N_per_mm"], color=c, linewidth=1.8, zorder=3)
        fk.status_dot(ax, s[-1], fh["force_N_per_mm"][-1], "meets" if ok[[l for l, n in names if n == nm][0]] else "held", size=40)
        fk.label(ax, s[-1], fh["force_N_per_mm"][-1], f"{m['force_per_length_N_per_mm']:.2f}", dx=7, color=INK, size=8.5,
                 bold=nm == "tightest")
    ax.set_xlabel("squeeze, % of the cross-section")
    ax.set_ylabel("closing force, N per mm of seal")
    fk.panel(ax, "Closing force: the tightest governs")

    ax = fig.add_subplot(gs[0, 2])
    fk.style(ax, grid="x")
    fills = [m["groove_fill_pct"] for nm, r, a, fh, m in recs]
    y = np.arange(3)[::-1]
    ax.barh(y, fills, color=cols, height=0.56, zorder=2)
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.6, 2.9)
    fk.limit(ax, L["groove_fill_pct"][1], "", bad="above", axis="x")
    fk.label(ax, L["groove_fill_pct"][1], 2.75, f"limit {L['groove_fill_pct'][1]:g} %", dx=-4, ha="right", color=INK2, size=8.5)
    for yy, f_ in zip(y, fills):
        fk.label(ax, f_, yy, f"{f_:.1f} %", dx=-4, ha="right", color=SURFACE, size=8.5, bold=True)
    ax.set_yticks(y, [nm for nm, *_ in recs])
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("groove fill, %")
    fk.panel(ax, "Groove fill")
    # the card's thumbnail is the 3D render's (make_study_renders.py)
    fk.heading(fig, "The seal passes at all three corners of its tolerance stack",
               "O-ring face seal, 3.53 mm NBR 70 in a 2.79 × 4.80 mm groove, coolant at 3 bar; CalculiX, axisymmetric, "
               "the ring's upper half")
    fig.savefig(fk.OUT / "fig_oring_seal.svg", format="svg", dpi=300, metadata={"Date": None, "Creator": None})
    fk.plt.close(fig)
    print("fig oring_seal")


def shaft_fillet():
    """The gearbox shaft's shoulder: fatigue and yield safety against the fillet radius on the drawn step, against
    the shaft's size when the step is scaled, and the stress along the fillet. Each point's dot is its verdict
    (hollow: that point's checks failed). Gated on each saved fillet profile reproducing the recorded Kt and Kts."""
    import matplotlib

    case = "shaft_fillet_radius"
    L = limits(case)
    s1, s2 = L["fatigue_safety"][1], L["static_safety"][1]
    runs = {"radius": "20261124-152828_shaft_fillet_radius", "radius_r1": "20261124-160916_shaft_fillet_radius_r1",
            "size": "20261124-155125_shaft_fillet_size"}
    ok = {k: verified(v) for k, v in runs.items()}

    def rec(key, lab):
        r = point(runs[key], lab)
        a = np.loadtxt(RUNS / runs[key] / "points" / lab / "fillet_stress.csv", delimiter=",", skiprows=1)
        m = r["metrics"]
        assert abs(a[:, 1].max() - m["kt_bending"]) < 1e-9 and abs(a[:, 3].max() - m["kt_torsion"]) < 1e-9
        return r, a, m, ok[key][lab]

    rad = [rec("radius", f"p0{i}_fillet_radius_mm-{v:g}") for i, v in enumerate([1.4, 1.6, 2.0, 2.5, 3.0, 3.5])]
    rad += [rec("radius_r1", f"p0{i}_fillet_radius_mm-{v:g}") for i, v in ((1, 3.7), (2, 3.9))]
    same = rec("radius_r1", "p00_fillet_radius_mm-3.5")[2]["fatigue_safety"]
    assert abs(same / rad[5][2]["fatigue_safety"] - 1) < 1e-3           # the re-meshed 3.5 mm point agrees
    siz = [rec("size", lab) for lab in ("p00_d32", "p01_d34", "p02_d35", "p03_d36", "p04_d38")]
    blues = matplotlib.colormaps[fk.SEQ]
    c_fat, c_yld = blues(0.92), blues(0.55)

    def safety_panel(ax, x, recs):
        for metric, lim, col in (("fatigue_safety", s1, c_fat), ("static_safety", s2, c_yld)):
            y = [m[metric] for _, _, m, _ in recs]
            ax.plot(x, y, color=col, linewidth=1.8, zorder=3)
            for xx, yy, (_, _, _, good) in zip(x, y, recs):
                fk.status_dot(ax, xx, yy, "held" if not good else ("meets" if yy >= lim else "misses"), size=34)
        for lim, txt in ((s1, f"fatigue needs {s1:g}"), (s2, f"yield needs {s2:g}")):
            ax.axhline(lim, color=INK2, linewidth=1.0, linestyle=(0, (4, 2)), zorder=1)

    D, d = rad[0][0]["parameters"]["D_mm"], rad[0][0]["parameters"]["d_mm"]
    h = (D - d) / 2
    fig, gs = fk.new(FULL, 4.3, 1, 3, wspace=0.45, top=0.80, width_ratios=[1.15, 1.0, 1.0])

    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax)
    x = [r["parameters"]["fillet_radius_mm"] for r, *_ in rad]
    ax.set_xlim(1.0, 4.4)
    ax.set_ylim(1.0, 3.1)
    sw = tomllib.loads((REPO / "cases" / f"{case}.toml").read_text(encoding="utf-8"))
    lo, nom, hi = sw["sweep"]["values"][:3]
    assert nom == sw["parameters"]["fillet_radius_mm"] and "tolerance band" in sw["case"]["description"]
    ax.axvspan(lo, hi, color=MODEL, alpha=0.08, linewidth=0, zorder=0.5)
    fk.label(ax, (lo + hi) / 2, 2.98, f"as drawn,\n{nom:g} +{hi - nom:.1f} / -{nom - lo:.1f}", ha="center", va="top",
             color=INK2, size=8)
    ax.axvline(h, color=INK, linewidth=1.6, zorder=2)
    fk.label(ax, h, 2.98, f"shoulder\nheight {h:g}", dx=-4, ha="right", va="top", color=INK2, size=8)
    safety_panel(ax, x, rad)
    fk.label(ax, 2.25, s1, f"fatigue needs {s1:g}", dy=6, color=INK2, size=8)
    fk.label(ax, 2.95, s2, f"yield needs {s2:g}", dy=-8, va="top", color=INK2, size=8)
    fk.label(ax, x[-1], rad[-1][2]["fatigue_safety"], f"best that fits:\n{rad[-1][2]['fatigue_safety']:.2f}", dx=-4,
             dy=-12, ha="right", va="top", color=INK, size=8.5, bold=True)
    fk.label(ax, x[1], rad[1][2]["static_safety"], "yield", dx=-2, dy=10, ha="right", color=INK, size=8.5)
    fk.label(ax, x[1], rad[1][2]["fatigue_safety"], "fatigue", dx=-2, dy=-10, ha="right", color=INK, size=8.5)
    ax.set_xlabel(f"fillet radius, mm (D {D:g} / d {d:g})")
    ax.set_ylabel("safety factor")
    fk.panel(ax, "As drawn: no fillet that fits reaches 1.5")

    ax = fig.add_subplot(gs[0, 1])
    fk.style(ax)
    x = [r["parameters"]["d_mm"] for r, *_ in siz]
    ax.set_xlim(31.2, 38.8)
    ax.set_ylim(1.0, 3.1)
    safety_panel(ax, x, siz)
    y = np.array([m["fatigue_safety"] for _, _, m, _ in siz])
    d_min = float(np.interp(s1, y, x))
    ax.axvline(d_min, color=INK2, linewidth=0.8, zorder=1)
    fk.label(ax, d_min, 3.0, f"fatigue reaches {s1:g}\nat d {d_min:.1f}", dx=-4, ha="right", va="top", color=INK2, size=8)
    r36, _, m36, _ = siz[3]
    assert r36["parameters"]["d_mm"] == 36           # the panel's title names it
    fk.label(ax, 36, m36["fatigue_safety"], f"{m36['fatigue_safety']:.2f}", dx=8, dy=-2, color=INK, size=8.5, bold=True)
    fk.label(ax, 36, m36["static_safety"], f"{m36['static_safety']:.2f}", dx=8, dy=-2, color=INK, size=8.5, bold=True)
    fk.label(ax, x[0], siz[0][2]["static_safety"], "yield", dx=2, dy=10, va="bottom", color=INK, size=8.5)
    fk.label(ax, x[0], siz[0][2]["fatigue_safety"], "fatigue", dx=6, dy=-6, va="top", color=INK, size=8.5)
    ax.set_xlabel("small diameter d, mm (D = 1.25 d)")
    fk.panel(ax, "Scaled up: a 36 mm seat passes")

    ax = fig.add_subplot(gs[0, 2])
    fk.style(ax)
    r16, a, m, _ = rad[1]
    ax.plot(a[:, 0], a[:, 1], color=c_fat, linewidth=1.8, zorder=3)
    ax.plot(a[:, 2], a[:, 3], color=c_yld, linewidth=1.8, zorder=3)
    i = int(np.argmax(a[:, 1]))
    fk.dots(ax, [a[i, 0]], [a[i, 1]], color=c_fat, size=34)
    fk.label(ax, a[i, 0], a[i, 1], f"bending, peak Kt {m['kt_bending']:.2f}\nat {a[i, 0]:.0f}°", dx=6, dy=8, va="bottom",
             color=INK, size=8.5)
    k62 = int(np.argmin(abs(a[:, 2] - 62)))
    fk.label(ax, a[k62, 2], a[k62, 3], f"torsion,\npeak Kts {m['kt_torsion']:.2f}", dx=4, dy=10, va="bottom", color=INK, size=8.5)
    ax.set_xlim(0, 90)
    ax.set_xticks([0, 30, 60, 90])
    ax.set_ylim(0, 2.75)
    ax.set_xlabel("along the fillet, ° (0 = small diameter)")
    ax.set_ylabel("stress / nominal stress")
    fk.panel(ax, f"Where it peaks, R{r16['parameters']['fillet_radius_mm']:g} as drawn")
    # the card's thumbnail is the 3D render's (make_study_renders.py)
    fk.heading(fig, "The shaft fails as drawn; a 36 mm seat with a 45 mm shoulder passes",
               f"Gearbox shaft, 42CrMo4: rotating bending {rad[0][0]['parameters']['bending_moment_Nm']:g} N m, steady torque "
               f"{rad[0][0]['parameters']['torque_Nm']:g} N m · CalculiX and Shigley's method · hollow: point unverified")
    fig.savefig(fk.OUT / "fig_shaft_fillet.svg", format="svg", dpi=300, metadata={"Date": None, "Creator": None})
    fk.plt.close(fig)
    print("fig shaft_fillet")


def motor_thermal():
    """The continuous rating from the thermal network, and the temperatures along it."""
    rec = point("20261122-174925_motor_prius_thermal_r1", "p00_nominal")
    e = {k: np.array(v) for k, v in rec["solver_outputs"]["envelope"].items()}
    fig, gs = fk.new(FULL, 3.9, 1, 3, wspace=0.3, top=1.0)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax)
    ax.plot(e["speed_rpm"], e["continuous_torque_Nm"], color=MODEL, zorder=4)
    ax.set_xlim(0, 6200)
    ax.set_ylim(0, 260)
    ax.set_xlabel("speed, rpm")
    ax.set_ylabel("torque it can hold, N m")
    fk.panel(ax, "Continuous torque")

    ax = fig.add_subplot(gs[0, 1])
    fk.style(ax)
    ax.plot(e["speed_rpm"], e["continuous_power_kW"], color=MODEL, zorder=4)
    ax.set_xlim(0, 6200)
    ax.set_ylim(0, 56)
    op, L = limits("motor_prius_thermal_r1")["min_continuous_power_kW"] if "min_continuous_power_kW" in limits("motor_prius_thermal_r1") else (">=", 25.0)
    fk.limit(ax, L, f"at least {L:g} kW from 1,250 rpm", bad="below", axis="y", at=0.97)
    ax.set_xlabel("speed, rpm")
    ax.set_ylabel("power it can hold, kW")
    fk.panel(ax, "Continuous power")

    ax = fig.add_subplot(gs[0, 2])
    fk.style(ax)
    ax.plot(e["speed_rpm"], e["winding_hotspot_C"], color=MODEL, zorder=4)
    ax.plot(e["speed_rpm"], e["magnet_C"], color=fk.THIRD, zorder=4)
    ax.set_xlim(0, 6200)
    ax.set_ylim(120, 190)
    ax.axhline(180, color=INK2, linewidth=1.1, zorder=1)
    ax.axhline(150, color=INK2, linewidth=1.1, zorder=1)
    fk.label(ax, 6100, 180, "winding limit 180 °C", dx=0, dy=5, ha="right", va="bottom", color=INK2, size=8.5)
    fk.label(ax, 200, 150, "magnet limit 150 °C", dx=0, dy=5, va="bottom", color=INK2, size=8.5)
    fk.label(ax, 3000, float(np.interp(3000, e["speed_rpm"], e["winding_hotspot_C"])), "winding hotspot", dx=8, dy=10, va="bottom", color=INK2, size=8.5)
    fk.label(ax, 4300, 150, "magnets, at their limit\nat every speed", dx=0, dy=-12, ha="center", va="top", color=INK2, size=8.5)
    ax.set_xlabel("speed, rpm")
    ax.set_ylabel("temperature, °C")
    fk.panel(ax, "What limits it")
    fk.heading(fig, "In the model, the magnets set the continuous rating, not the winding",
               "The thermal network with its assumed 65 °C water jacket. With the model's flux 24 % high, the power shown is optimistic")
    fk.save(fig, "motor_thermal")


def motor_rotor():
    """Linearised stress across the rotor bridge at overspeed, against the lamination's yield."""
    run, lab = "20261124-063835_motor_prius_rotor_overspeed_rev5_mesh", "p02_bridge_element_size_mm-0.05"
    rec = point(run, lab)
    m = rec["metrics"]
    s = read_series(RUNS / run / "points" / lab / "bridge_scl.csv")
    a = s["scl_angle_deg"]
    fig, gs = fk.new(fk.HALF, 3.8, top=0.95)
    gs.update(left=0.15, right=0.96)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax)
    ax.plot(a, s["membrane_vm_MPa"], color=fk.AXIS, zorder=3)
    ax.plot(a, s["membrane_bending_vm_MPa"], color=MODEL, zorder=4)
    ax.set_xlim(a.min(), a.max())
    ax.set_xticks([15.5, 16.0, 16.5, 17.0])
    ax.set_ylim(0, 470)
    op, L = limits("motor_prius_rotor_overspeed_rev5_mesh")["bridge_linearized_vm_MPa"]
    fk.limit(ax, L, f"yield, {L:g} MPa", bad="above", axis="y", at=0.03)
    k = int(np.argmax(s["membrane_bending_vm_MPa"]))
    fk.label(ax, a[k], s["membrane_bending_vm_MPa"][k], f"{m['bridge_linearized_vm_MPa']:.0f} MPa", dx=-8, dy=4, ha="right", va="bottom", size=8.5)
    fk.label(ax, a[len(a) // 2], s["membrane_vm_MPa"][len(a) // 2], "average through the bridge", dx=0, dy=-8, ha="center", va="top", color=INK2, size=8.5)
    fk.label(ax, a[len(a) // 2], s["membrane_bending_vm_MPa"][len(a) // 2], "with bending", dx=-12, dy=10, ha="right", va="bottom", color=INK2, size=8.5)
    ax.set_xlabel("position along the bridge, degrees from the pole axis")
    ax.set_ylabel("stress across the bridge, MPa")
    fk.heading(fig, "The rotor bridge is past yield at overspeed", "At 7,200 rpm, 20 % over the maximum speed")
    fk.save(fig, "motor_rotor")


# ---------------------------------------------------------------------------------------- study 18, pressure vessel

def pv_nozzle():
    """Where the classification line is drawn decides the verdict: the line through the crotch corner, and the
    membrane stress against nozzle wall on the weld-toe line and on the crotch line."""
    from harness.linearize import von_mises

    rec = point("20261122-201431_pv_nozzle_crotch_mesh_r1", "p02_element_size_local_mm-2.6667")
    line = rec["solver_outputs"]["lines"]["crotch_long"]
    prof = rec["solver_outputs"]["profiles"]["crotch_long"]
    sx, vm = np.asarray(prof["s_mm"]), np.asarray(prof["vm_MPa"])
    th, mem, ben = line["thickness"], np.asarray(line["membrane"]), np.asarray(line["bending"])
    lin = von_mises(mem[None, :] + ben[None, :] * (1 - 2 * sx[:, None] / th))
    pl = line["membrane_vm"]
    L = limits("pv_nozzle_crotch_mesh_r1" if (REPO / "cases" / "pv_nozzle_crotch_mesh_r1.toml").exists()
               else "pv_nozzle_mesh").get("pl_max_MPa", ("<=", 207.0))[1]
    fig, gs = fk.new(FULL, 3.9, 1, 2, wspace=0.24, top=1.0)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax)
    ax.plot(sx, vm, color=MODEL, zorder=4)
    ax.plot(sx, lin, color=fk.THIRD, zorder=3)
    ax.axhline(pl, color=fk.THIRD, linewidth=1.2, zorder=3)
    ax.set_xlim(0, th)
    ax.set_ylim(150, 380)
    fk.limit(ax, L, f"membrane limit {L:g} MPa", bad="above", axis="y", at=0.97)
    fk.label(ax, 0.4, pl, f"membrane: {pl:.1f} MPa", dx=0, dy=-5, va="top", size=8.5)
    fk.label(ax, 0.4, vm[0], f"corner peak {vm[0]:.0f} MPa, excluded by design", dx=4, dy=0, va="center", color=INK2, size=8.5)
    m = int(np.argmin(abs(sx - 8)))
    fk.label(ax, sx[m], vm[m], "stress from the model", dx=-6, dy=-6, ha="right", va="top", color=MODEL, size=8.5)
    fk.label(ax, sx[-1], lin[-1], "straight-line fit", dx=-4, dy=-8, ha="right", va="top", color=fk.THIRD, size=8.5)
    ax.set_xlabel("from the sharp inner corner to the weld fillet, mm")
    ax.set_ylabel("stress, MPa")
    fk.panel(ax, "The line through the corner, 12 mm nozzle")

    ax = fig.add_subplot(gs[0, 1])
    fk.style(ax)
    toe = pts("20261122-103521_pv_nozzle_thickness")
    cro = pts("20261122-200149_pv_nozzle_crotch_thickness")
    series = [("weld-toe line", [(r["parameters"]["nozzle_thickness_mm"], r["metrics"]["pl_max_MPa"], ok) for _, r, ok in toe], MODEL),
              ("line through the corner", [(r["parameters"]["nozzle_thickness_mm"], r["metrics"]["pl_crotch_max_MPa"], ok) for _, r, ok in cro], fk.THIRD)]
    ax.set_xlim(6.5, 25.5)
    ax.set_ylim(140, 290)
    fk.limit(ax, L, f"limit {L:g} MPa", bad="above", axis="y", at=0.97)
    needs = []
    for name, rows, color in series:
        xs, ys = [r[0] for r in rows], [r[1] for r in rows]
        ax.plot(xs, ys, color=color, linewidth=1.8, zorder=3)
        for x, y, ok in rows:
            fk.status_dot(ax, x, y, "held" if not ok else ("meets" if y <= L else "misses"))
        k = int(np.argmax(np.array(ys) <= L))
        needs.append(xs[k - 1] + (L - ys[k - 1]) * (xs[k] - xs[k - 1]) / (ys[k] - ys[k - 1]))
        fk.label(ax, xs[-1], ys[-1], name, dx=-2, dy=-12, ha="right", va="top", color=color, size=8.5, bold=True)
    for x, text in ((needs[0], f"{needs[0]:.1f}"), (16.0, "rule 16"), (needs[1], f"{needs[1]:.1f}")):
        ax.plot([x, x], [140, L], color=INK2, linewidth=0.9, linestyle=(0, (3, 2)), zorder=2)
        fk.label(ax, x, 143, text, dx=3, ha="left", va="bottom", color=INK2, size=8.5)
    ax.axvline(12, color=MUTED, linewidth=0.8, zorder=1)
    fk.label(ax, 12, 288, "the 12 mm design", dx=3, va="top", color=INK2, size=8.5)
    ax.set_xlabel("nozzle wall thickness, mm")
    ax.set_ylabel("membrane stress PL, MPa")
    fk.panel(ax, "Wall needed on each line")
    fk.heading(fig, f"Where the line is drawn decides it: 12 mm passes at the weld toe and fails through the corner",
               f"Through the corner PL is {pl:.1f} MPa against {L:g}; that line needs about {needs[1]:.1f} mm, the toe line {needs[0]:.1f}")
    fk.key(fig, [("meets the limit", "meets", None), ("misses it", "misses", None)], y_in=0.66)
    fk.save(fig, "pv_nozzle")


# ---------------------------------------------------------------------------------------- study 19 part 2, the step

STEP_RUN, STEP_PT = "20261122-233146_step_mesh", "p02_mesh_level-1.4142"


def step_comparison():
    """The step against Driver and Seegmiller: skin friction and pressure along the step-side wall."""
    import csv
    sys.path.insert(0, str(REPO / "validation" / "step_driver_seegmiller"))
    import compare as sc                       # the same readers the one scored comparison used
    data = Path.home() / "data" / "ercoftac_case030" / "files"
    res = json.loads((REPO / "validation" / "step_driver_seegmiller" / "comparison.json").read_text(encoding="utf-8"))
    assert res["run"] == STEP_RUN and res["point"] == STEP_PT
    cf_m, cp_m = sc.measured_cf(data), sc.measured_cp(data)
    pdir = RUNS / STEP_RUN / "points" / STEP_PT
    with open(pdir / "wall.csv", newline="", encoding="utf-8") as f:
        rows = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(f)]
    o = point(STEP_RUN, STEP_PT)["solver_outputs"]
    xs, cfs = np.array([r["x_over_h"] for r in rows]), np.array([r["cf"] for r in rows])
    xu, cfu = np.array(o["profiles"]["x_up_over_h"]), np.array(o["profiles"]["cf_up"])
    xp, cp = np.array(o["profiles"]["x_p_over_h"]), np.array(o["profiles"]["cp"])

    fig, gs = fk.new(FULL, 3.9, 1, 2, wspace=0.22, top=1.0)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax)
    ax.axvspan(10, 30, color=MODEL, alpha=0.06, linewidth=0, zorder=0.5)
    ax.axhline(0, color=fk.AXIS, linewidth=1.0, zorder=1)
    for x_, c_ in ((xu, cfu), (xs, cfs)):              # the wall before the step, then the floor after it
        k = (x_ >= -4) & (x_ <= 32)
        ax.plot(x_[k], 1e3 * c_[k], color=MODEL, zorder=3)
    m = (cf_m[:, 0] >= -4) & (cf_m[:, 0] <= 32)
    ax.errorbar(cf_m[m, 0], 1e3 * cf_m[m, 1], yerr=1e3 * np.abs(cf_m[m, 1]) * cf_m[m, 2], fmt="none", ecolor=REF,
                elinewidth=1, capsize=2, zorder=3)
    fk.dots(ax, cf_m[m, 0], 1e3 * cf_m[m, 1], color=REF, size=34)
    s1 = res["REQ-S1"]
    ax.set_xlim(-4.5, 32)
    ax.set_ylim(-2.0, 3.9)
    fk.status_dot(ax, s1["ours"], 0, "meets" if s1["pass"] else "misses", size=48)
    fk.label(ax, s1["ours"], 0, f"reattaches at {s1['ours']:.2f} H\n(measured {s1['measured']:.2f})", dx=6, dy=-8, va="top",
             color=INK2, size=8.5)
    fk.label(ax, 20, 3.8, f"scored from 10 to 30 H: {100 * res['REQ-S2']['rms_rel_error']:.1f} % rms, limit 15 %", ha="center",
             va="top", color=INK2, size=8.5)
    ax.set_xlabel("distance from the step, step heights")
    ax.set_ylabel("skin friction coefficient × 1000")
    fk.panel(ax, "Skin friction along the floor: passes")

    ax = fig.add_subplot(gs[0, 1])
    fk.style(ax)
    sel = (xp >= -4) & (xp <= 32)
    ax.plot(xp[sel], cp[sel], color=MODEL, zorder=3)
    m = (cp_m[:, 0] >= -4) & (cp_m[:, 0] <= 32)
    fk.dots(ax, cp_m[m, 0], cp_m[m, 1], color=REF, size=34)
    s3 = res["REQ-S3"]
    ax.set_xlim(-4.5, 32)
    y30 = float(np.interp(30, xp, cp))
    fk.status_dot(ax, 30, y30, "meets" if s3["pass"] else "misses", size=48)
    fk.label(ax, 31, 0.03, f"recovery to 30 H: {s3['ours']:.3f}\nmeasured {s3['measured']:.3f}, limit ±0.02", ha="right",
             va="center", color=INK2, size=8.5)
    ax.set_xlabel("distance from the step, step heights")
    ax.set_ylabel("pressure coefficient")
    fk.panel(ax, f"Pressure along the floor: recovery {s3['difference']:+.3f}, misses")
    fk.heading(fig, "Behind the step the model passes on reattachment and friction, but the pressure recovers too far",
               "2D k-omega SST on the finest mesh against Driver and Seegmiller's measurements, scored once against limits agreed beforehand")
    fk.key(fig, [("measured", "dot", REF), ("model", "line", MODEL), ("meets", "meets", None), ("misses", "misses", None)], y_in=0.66)
    fk.save(fig, "step_comparison")


# ---------------------------------------------------------------------------------------- study 21, random vibration

RV_RUN, RV_PT = "20261123-100907_bracket_random_mesh", "p02_element_size_mm-1.2207"


def random_vibration():
    """The root stress spectrum on each axis, and each requirement as a share of its limit."""
    from matplotlib.ticker import FixedLocator, NullFormatter
    s = read_series(RUNS / RV_RUN / "points" / RV_PT / "response_psd.csv")
    pt = point(RV_RUN, RV_PT)
    mt = pt["metrics"]
    L = limits("bracket_random_mesh")
    ok = verified(RV_RUN)[RV_PT]
    fig, gs = fk.new(FULL, 3.9, 1, 2, wspace=0.12, top=1.0, width_ratios=[1.5, 1])
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax, grid="both")
    f = np.asarray(s["f_Hz"])
    for axis, color, text, at in (("z", MODEL, "shaken flapwise (z)", None), ("y", REF, "shaken sideways (y)", None),
                                  ("x", fk.THIRD, "shaken along the arm (x)", 60.0)):
        y = np.asarray(s[f"sxx_psd_{axis}_MPa2_per_Hz"])
        ax.plot(f, y, color=color, linewidth=1.6, zorder=3)
        i = int(np.argmax(y)) if at is None else int(np.argmin(abs(f - at)))
        fk.label(ax, f[i], y[i], text, dx=6 if at is None else 0, dy=2 if at is None else 5, ha="left" if at is None else "center",
                 va="bottom", color=INK2, size=8.5)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(20, 2000)
    ax.set_ylim(1e-6, 1e2)
    fq = pt["solver_outputs"]["frequency_Hz"]
    ax.axvline(fq[0], color=fk.AXIS, linewidth=0.8, linestyle=(0, (3, 3)), zorder=1)
    fk.label(ax, fq[0], 1e2, f"first mode,\n{fq[0]:.0f} Hz", dx=-4, dy=-4, ha="right", va="top", color=INK2, size=8.5)
    ax.set_xlabel("frequency, Hz (input flat at 0.04 g²/Hz)")
    ax.set_ylabel("stress at the clamp, MPa²/Hz")
    fk.panel(ax, "Where the stress comes from")

    ax = fig.add_subplot(gs[0, 1])
    fk.style(ax, grid="x")
    reqs = [("3-sigma stress", "stress_3sigma_MPa", "{:.1f} of {:.1f} MPa"), ("fatigue damage", "damage_dirlik", "{:.4f} of {:.1f}"),
            ("3-sigma tip movement", "tip_disp_3sigma_mm", "{:.3f} of {:.1f} mm")]
    ax.set_xscale("log")
    ax.set_xlim(1e-3, 3)
    ax.set_ylim(2.7, -0.7)
    for i, (name, key_, fmt) in enumerate(reqs):
        lim = L[key_][1]
        r = mt[key_] / lim
        fk.status_dot(ax, r, i, ("meets" if r <= 1 else "misses") if ok else "held")
        fk.label(ax, r, i, name, dx=0, dy=10, ha="center", va="bottom", size=9)
        fk.label(ax, r, i, fmt.format(mt[key_], lim), dx=0, dy=-10, ha="center", va="top", color=INK2, size=8.5)
    ax.set_yticks([])
    fk.limit(ax, 1.0, "limit", "above", axis="x", at=0.99)
    ax.xaxis.set_major_locator(FixedLocator([1e-3, 1e-2, 1e-1, 1]))
    ax.set_xticklabels(["0.001", "0.01", "0.1", "1"])
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel("share of the limit used")
    fk.panel(ax, "Each requirement against its limit")
    fk.heading(fig, "The arm passes one hour per axis on the shaker, with room to spare on all three limits",
               "Modal superposition on the finest of three meshes (1.22 mm), 2 % damping; the test level and damping are assumed")
    fk.key(fig, [("meets", "meets", None)], y_in=0.66)
    fk.save(fig, "random_vibration")


# ---------------------------------------------------------------------------------------- study 22, uncertainty

UQ_RUN, UQ_PT = "20261123-104847_bracket_random_uq", "p02_n_samples-32768"


def bracket_uncertainty():
    """Which input drives each output (Sobol total indices), and each requirement's failure probability."""
    from matplotlib.ticker import FixedLocator, NullFormatter
    pt = point(UQ_RUN, UQ_PT)
    so = pt["solver_outputs"]
    ok = verified(UQ_RUN)[UQ_PT]
    fig, gs = fk.new(FULL, 4.4, 1, 2, wspace=0.14, top=1.0, width_ratios=[1.2, 1])
    gs.update(left=0.15)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax, grid="x")
    inputs = [("damping", "damping"), ("test_level_dB", "test level"), ("sn_factor", "fatigue strength"),
              ("thickness_mm", "plate thickness")]
    outs = [("stress", "3-sigma stress", MODEL), ("tip", "tip movement", REF), ("logdamage", "fatigue damage", fk.THIRD)]
    h = 0.24
    for j, (ok_, name, color) in enumerate(outs):
        st = so["sobol"][ok_]["ST"]
        ys = [i + (j - 1) * (h + 0.03) for i in range(len(inputs))]
        ax.barh(ys, [max(st[k], 0.0) for k, _ in inputs], height=h, color=color, zorder=3)
    for i, (k, _) in enumerate(inputs):
        top = max(so["sobol"][o]["ST"][k] for o, _, _ in outs)
        if top > 0.05:
            fk.label(ax, top, i, f"{top:.2f}", dx=5, ha="left", color=INK2, size=8.5)
    ax.set_yticks(range(len(inputs)))
    ax.set_yticklabels([n for _, n in inputs])
    ax.set_ylim(len(inputs) - 0.5, -0.5)
    ax.set_xlim(0, 1)
    ax.set_xlabel("share of the output's variance (Sobol total index)")
    fk.panel(ax, "What drives each result")

    ax = fig.add_subplot(gs[0, 1])
    fk.style(ax, grid="x")
    rel = {r["output"]: r for r in so["reliability"]}
    rows = [("3-sigma stress", "stress_3sigma_MPa"), ("fatigue damage", "damage"), ("3-sigma tip movement", "tip_disp_3sigma_mm")]
    lim = limits("bracket_random_uq")["pf_any"][1]
    ax.set_xscale("log")
    ax.set_xlim(1e-17, 1)
    ax.set_ylim(3.6, -0.75)
    for i, (name, key_) in enumerate(rows):
        r = rel[key_]
        fk.status_dot(ax, r["pf_is"], i, ("meets" if r["pf_is"] <= lim else "misses") if ok else "held")
        fk.label(ax, r["pf_is"], i, name, dx=0, dy=10, ha="center", va="bottom", size=9)
        fk.label(ax, r["pf_is"], i, f"{r['pf_is']:.1e}, reliability index {r['beta']:.1f}", dx=0, dy=-10, ha="center", va="top",
                 color=INK2, size=8.5)
    pf = so["pf_any"]
    fk.status_dot(ax, pf, 3, ("meets" if pf <= lim else "misses") if ok else "held")
    fk.label(ax, pf, 3, "any of the three", dx=0, dy=10, ha="center", va="bottom", size=9, bold=True)
    fk.label(ax, pf, 3, f"{pf:.1e}", dx=0, dy=-10, ha="center", va="top", color=INK2, size=8.5)
    ax.set_yticks([])
    fk.limit(ax, lim, "limit", "above", axis="x", at=0.99)
    ax.xaxis.set_major_locator(FixedLocator([1e-15, 1e-12, 1e-9, 1e-6, 1e-3]))
    ax.set_xticklabels(["10⁻¹⁵", "10⁻¹²", "10⁻⁹", "10⁻⁶", "10⁻³"])
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel("probability of failing, per test")
    fk.panel(ax, "Chance of failing each requirement")
    fk.heading(fig, "Damping drives the result, and the chance of the arm failing its test is about 2 in a million",
               "Monte Carlo, Sobol indices and FORM with importance sampling on study 21's finest mesh; the input ranges are assumed")
    fk.key(fig, [(n, "line", c) for _, n, c in outs] + [("meets", "meets", None)], y_in=0.66)
    fk.save(fig, "bracket_uncertainty")


# ---------------------------------------------------------------------------------------- study 23, fan rotor

ROTOR_RUN = "20261123-162721_rotor_fan_design"


def fan_rotor():
    """Unbalance response over the operating range, and the first forward critical speed against the keep-out band."""
    from matplotlib.ticker import FixedLocator, NullFormatter
    L = limits("rotor_fan_design")
    ok = verified(ROTOR_RUN)
    pts_ = sorted((RUNS / ROTOR_RUN / "points").iterdir())
    rec = [(p.name, point(ROTOR_RUN, p.name)) for p in pts_]
    fig, gs = fk.new(FULL, 3.9, 1, 2, wspace=0.26, top=1.0, width_ratios=[1.2, 1])
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax, grid="both")
    colors = {0.05: fk.FAIL, 0.06: REF, 0.065: MODEL}
    for name, r in rec:
        d, kb = r["parameters"]["shaft_diameter_m"], r["parameters"]["bearing_stiffness_N_per_m"]
        s = read_series(RUNS / ROTOR_RUN / "points" / name / "unbalance_response.csv")
        ax.plot(s["speed_rpm"], np.asarray(s["disc_amp_x_m"]) * 1e6, color=colors[d], linewidth=1.8 if kb < 5e7 else 1.2,
                linestyle="-" if kb < 5e7 else (0, (4, 3)), zorder=3)
        if kb < 5e7:
            y = np.asarray(s["disc_amp_x_m"]) * 1e6
            fk.label(ax, 3000, y[-1], f"{d * 1000:.0f} mm", dx=5, ha="left", color=INK2, size=8.5)
    ax.set_yscale("log")
    ax.set_xlim(1000, 3250)
    ax.set_ylim(0.1, 1000)
    op, lim = L["unbalance_amp_max_um"]
    fk.limit(ax, lim, f"limit, {lim:g} µm", "above", axis="y", at=0.03)
    ax.yaxis.set_major_locator(FixedLocator([0.1, 1, 10, 100, 1000]))
    ax.set_yticklabels(["0.1", "1", "10", "100", "1000"])
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks([1000, 1500, 2000, 2500, 3000])
    ax.set_xlabel("running speed, rpm (the operating range)")
    ax.set_ylabel("impeller vibration, µm")
    fk.panel(ax, "Response to the standard unbalance")
    resp_ax = ax

    ax = fig.add_subplot(gs[0, 1])
    fk.style(ax, grid="x")
    ax.set_xlim(0, 6400)                            # keep-out: 15 % outside the 1000-3000 rpm range (REQ-G1)
    ax.set_ylim(2.6, -0.6)
    ax.axvspan(850, 3450, color=fk.FAIL, alpha=0.07, linewidth=0, zorder=0.5)
    ax.axvspan(1000, 3000, color=fk.FAIL, alpha=0.07, linewidth=0, zorder=0.6)
    ax.annotate("keep out: 850 to 3,450 rpm", (2150, 0.99), xycoords=("data", "axes fraction"), ha="center", va="top",
                fontsize=8.5, color=INK2)
    for i, dia in enumerate((0.05, 0.06, 0.065)):
        rr = [(r["parameters"]["bearing_stiffness_N_per_m"], r["metrics"], ok[n]) for n, r in rec
              if r["parameters"]["shaft_diameter_m"] == dia]
        xs = [m["first_forward_critical_rpm"] for _, m, _ in rr]
        ax.plot(xs, [i, i], color=fk.AXIS, linewidth=1.2, zorder=2)
        for kb, m, v in rr:
            good = m["separation_margin_pct"] >= L["separation_margin_pct"][1]
            fk.status_dot(ax, m["first_forward_critical_rpm"], i, ("meets" if good else "misses") if v else "held")
        fk.label(ax, min(xs), i, f"{dia * 1000:.0f} mm shaft", dx=0, dy=11, ha="left", va="bottom", size=9)
        fk.label(ax, max(xs), i, f"{min(xs):,.0f} to {max(xs):,.0f} rpm", dx=8, ha="left", color=INK2, size=8.5)
    ax.set_yticks([])
    ax.set_xlabel("first critical speed, rpm (soft to stiff bearings)")
    fk.panel(ax, "First critical speed against the keep-out band")
    fk.heading(fig, "The 50 mm shaft passes through a critical speed in service; a 65 mm shaft clears the range",
               "ROSS rotor model, bearing stiffness 10⁷ (solid) to 10⁸ N/m (dashed); geometry, speeds and bearings are assumed")
    fk.key(fig, [("meets", "meets", None), ("misses", "misses", None)], y_in=0.66)
    # the card's thumbnail is the 3D render's (make_study_renders.py)
    fk.save(fig, "fan_rotor")


def fan_rotor_campbell():
    """Campbell diagram on soft bearings (the governing case) for the three shafts, and the 65 mm shaft's first two
    mode shapes. Frequencies from the run; shapes from scripts/export_fan_modes.py (the run's own model, rebuilt and
    gated on the run's frequencies)."""
    from scipy.interpolate import CubicSpline
    L = limits("rotor_fan_design")
    ok = verified(ROTOR_RUN)
    md = json.loads((REPO / "build" / "drawings" / "fan_rotor_modes.json").read_text(encoding="utf-8"))
    assert md["run"] == ROTOR_RUN
    fig, gs = fk.new(FULL, 4.3, 2, 2, wspace=0.22, hspace=0.75, top=1.0, width_ratios=[1.15, 1])
    ax = fig.add_subplot(gs[:, 0])
    fk.style(ax, grid="both")
    ax.set_xlim(0, 9000)
    ax.set_ylim(0, 6000)
    lo, hi = 1000 * 0.85, 3000 * 1.15                       # keep-out: 15 % outside the 1000-3000 rpm range (REQ-G1)
    ax.axvspan(lo, hi, color=fk.FAIL, alpha=0.07, linewidth=0, zorder=0.5)
    ax.axvspan(1000, 3000, color=fk.FAIL, alpha=0.07, linewidth=0, zorder=0.6)
    ax.annotate("operating range,\nand 15 % either side", (2150, 0.985), xycoords=("data", "axes fraction"), ha="center",
                va="top", fontsize=8.5, color=INK2)
    ax.plot([0, 6000], [0, 6000], color=INK2, linewidth=1.1, zorder=2)
    fk.label(ax, 5000, 5000, "running speed", dx=6, dy=-6, ha="left", va="top", color=INK2, size=8.5)
    colors = {0.05: fk.FAIL, 0.06: REF, 0.065: MODEL}
    for name in ("p00_d50_kb1e7", "p02_d60_kb1e7", "p04_d65_kb1e7"):
        r = point(ROTOR_RUN, name)
        d = r["parameters"]["shaft_diameter_m"]
        o = r["solver_outputs"]
        sp = np.asarray(o["campbell_rpm"])
        wd = np.asarray(o["campbell_wd_rpm"])
        wh = np.asarray(o["campbell_whirl"])
        fwd = np.where(wh[:, 1] < 0.25, wd[:, 1], wd[:, 0])  # the first forward mode
        keep = sp <= 9000
        ax.plot(sp[keep], fwd[keep], color=colors[d], linewidth=2.0, zorder=3)
        crit = r["metrics"]["first_forward_critical_rpm"]
        good = r["metrics"]["separation_margin_pct"] >= L["separation_margin_pct"][1]
        fk.status_dot(ax, crit, crit, ("meets" if good else "misses") if ok[name] else "held")
        up = d == 0.065
        fk.label(ax, 9000, fwd[keep][-1], f"{d * 1000:.0f} mm shaft: critical at {crit:,.0f} rpm", dx=-2, dy=5 if up else -5,
                 ha="right", va="bottom" if up else "top", color=INK2, size=8.5)
    ax.set_xticks([0, 1500, 3000, 4500, 6000, 7500, 9000])
    ax.set_yticks([0, 1000, 2000, 3000, 4000, 5000, 6000])
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:,.0f}")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:,.0f}")
    ax.set_xlabel("running speed, rpm")
    ax.set_ylabel("first natural frequency, rpm")
    fk.panel(ax, "Campbell diagram, soft bearings (10⁷ N/m)")

    m = md["points"]["p04_d65_kb1e7"]
    z = np.asarray(m["nodes_m"]) * 1000
    zs = np.linspace(0, z[-1], 201)
    for row, (j, ttl) in enumerate(((1, "65 mm shaft, first mode: it bows"), (3, "Second mode: the impeller tilts"))):
        ax = fig.add_subplot(gs[row, 1])
        fk.style(ax, grid=None)
        x = np.asarray(m["modes"][j]["x"])
        if x[len(x) // 2 + 2] < 0:
            x = -x
        y = CubicSpline(z, x)(zs)
        ax.axhline(0, color=fk.AXIS, linewidth=0.8, linestyle=(0, (6, 3)), zorder=1)
        ax.plot(zs, y, color=MODEL, linewidth=2.2, zorder=3)
        ax.set_xlim(-60, 1060)
        ax.set_ylim(-1.3, 2.4)
        # the impeller: a 400 mm disc, drawn at the shaft's slope at mid-span (display coordinates, so it looks square on)
        fig.canvas.draw()
        slope = CubicSpline(z, x)(500, 1)
        p0, p1 = ax.transData.transform([(500, CubicSpline(z, x)(500)), (501, CubicSpline(z, x)(500) + slope)])
        t = (p1 - p0) / np.hypot(*(p1 - p0))
        n_ = np.array([-t[1], t[0]])
        c = ax.transData.transform((500, float(CubicSpline(z, x)(500))))
        half = 0.5 * 400 / 1060 * ax.get_window_extent().width * 0.42
        a_, b_ = ax.transData.inverted().transform([c - n_ * half, c + n_ * half])
        ax.plot([a_[0], b_[0]], [a_[1], b_[1]], color=INK, linewidth=4.5, solid_capstyle="butt", zorder=4)
        for zb in (0, z[-1]):
            ax.scatter([zb], [CubicSpline(z, x)(zb)], marker="^", s=55, color=INK, zorder=5)
        ax.set_xticks([0, 500, 1000], ["0", "500", "1,000"])
        ax.set_yticks([])
        ax.spines["bottom"].set_visible(False)
        ax.tick_params(axis="x", labelbottom=row == 1)
        f_b, f_f = m["modes"][j - 1]["wd_rpm"], m["modes"][j]["wd_rpm"]
        sub = (f"{f_f:,.0f} rpm at every speed: the impeller doesn't tilt" if j == 1 else
               f"{f_b:,.0f} and {f_f:,.0f} rpm at 3,000 rpm: the spin splits it in two")
        fk.panel(ax, ttl)
        ax.annotate(sub, (0, 1), xycoords="axes fraction", xytext=(0, -2), textcoords="offset points", ha="left", va="top",
                    fontsize=8.5, color=INK2)
        if row == 1:
            ax.set_xlabel("along the 65 mm shaft, mm (bearings at 0 and 1,000)")
    fk.heading(fig, "Only the 65 mm shaft's critical speed stays clear of the operating range",
               "ROSS rotor model on soft bearings, the governing case; a critical speed is where a mode meets the running speed")
    fk.key(fig, [("meets", "meets", None), ("misses", "misses", None)], y_in=0.66)
    fk.save(fig, "fan_rotor_campbell")


# ---------------------------------------------------------------------------------------- study 24, cracked plate

CRACK_RUN, CRACK_PT = "20261123-164649_edge_crack_mesh_r2", "p02_tip_element_size_mm-0.025"


def crack_growth():
    """K against crack length with the toughness, and the crack's growth from the detectable size to critical."""
    from scipy.integrate import cumulative_simpson
    from scipy.interpolate import CubicSpline
    from studies.edge_crack import MPA_SQRT_M
    pt = point(CRACK_RUN, CRACK_PT)
    p, m = pt["parameters"], pt["metrics"]
    ok = verified(CRACK_RUN)[CRACK_PT]
    s = read_series(RUNS / CRACK_RUN / "points" / CRACK_PT / "k_of_a.csv")
    a = np.asarray(s["a_mm"])
    K = np.asarray(s["K_energy"]) / MPA_SQRT_M
    Kt = np.asarray(s["K_tada"]) / MPA_SQRT_M
    kmat = float(p["k_mat_MPa_sqrt_m"])
    fig, gs = fk.new(FULL, 3.9, 1, 2, wspace=0.26, top=1.0)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax)
    ax.plot(a, Kt, color=REF, zorder=2)
    fk.dots(ax, a, K, color=MODEL, size=36)
    ax.set_xlim(0, 47)
    ax.set_ylim(0, 150)
    fk.limit(ax, kmat, f"fracture toughness, {kmat:g} MPa√m", "above", axis="y", at=0.03)
    ac = m["crit_crack_mm"]
    ax.axvline(ac, color=fk.AXIS, linewidth=0.8, linestyle=(0, (3, 3)), zorder=1)
    fk.label(ax, ac, 8, f"critical crack\n{ac:.1f} mm", dx=-5, ha="right", va="bottom", color=INK2, size=8.5)
    fk.status_dot(ax, float(p["initial_crack_mm"]), m["K_a0_MPa_sqrt_m"], "meets" if ok else "held")
    fk.label(ax, float(p["initial_crack_mm"]), m["K_a0_MPa_sqrt_m"], f"at 2 mm: {m['K_a0_MPa_sqrt_m']:.1f}\n(limit {kmat / 2:g})",
             dx=10, dy=-6, ha="left", va="top", color=INK2, size=8.5)
    ax.set_xlabel("crack length, mm")
    ax.set_ylabel("stress intensity at peak load, MPa√m")
    fk.panel(ax, "Stress intensity: model against Tada's handbook")

    # the life curve: the study's own growth law and geometry factor, integrated cumulatively
    smax, R = float(p["sigma_max_MPa"]), float(p["stress_ratio"])
    F = CubicSpline(a, np.asarray(s["K_energy"]) / (smax * np.sqrt(np.pi * a)))
    xs = np.linspace(float(p["initial_crack_mm"]), ac, 4001)
    dK = (1 - R) * F(xs) * smax * np.sqrt(np.pi * xs)
    N = cumulative_simpson(1 / (float(p["paris_C"]) * dK ** float(p["paris_m"])), x=xs, initial=0)
    assert abs(N[-1] / m["growth_life_cycles"] - 1) < 2e-3, (N[-1], m["growth_life_cycles"])
    ax = fig.add_subplot(gs[0, 1])
    fk.style(ax)
    ax.plot(N / 1000, xs, color=MODEL, zorder=3)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 40)
    life = m["growth_life_cycles"]
    insp = m["inspection_interval_cycles"]
    ax.axvline(insp / 1000, color=fk.AXIS, linewidth=0.8, linestyle=(0, (3, 3)), zorder=1)
    fk.label(ax, insp / 1000, 38, f"inspect at least\nevery {insp / 1000:,.0f},000", dx=-5, ha="right", va="top", color=INK2, size=8.5)
    fk.status_dot(ax, life / 1000, ac, "meets" if ok else "held")
    fk.label(ax, life / 1000, ac, f"{life / 1000:,.0f},000 cycles", dx=-8, dy=0, ha="right", va="center", size=9)
    ax.set_xlabel("load cycles, thousands")
    ax.set_ylabel("crack length, mm")
    fk.panel(ax, "Growth from the detectable 2 mm crack")
    fk.heading(fig, "A 2 mm edge crack takes about 92,000 cycles to reach the critical 37 mm: inspect at least every 46,000",
               "CalculiX plane strain, K by energy release on the finest tip mesh; BS 7910 growth law; loads and toughness are assumed")
    fk.key(fig, [("model", "dot", MODEL), ("handbook", "line", REF)], y_in=0.66)
    # the card's thumbnail is the 3D render's (make_study_renders.py)
    fk.save(fig, "crack_growth")


ENC_SCORES = REPO / "validation" / "enclosure" / "client_requirements_revB_scores.json"


def _enc_scores() -> dict:
    """The 14 settled enclosure runs scored against the client's revision B list, keyed by design:
    ('drawn', board_k, eps) and ('fix', bridge, eps) with bridge 0 for the shell alone. Every run must have passed
    its own verification, and each value is checked against the run's point.json where the run recorded it."""
    import re
    d = json.loads(ENC_SCORES.read_text(encoding="utf-8"))
    out = {}
    for r in d["runs"]:
        run = r["run"]
        v = json.loads((RUNS / run / "verification.json").read_text(encoding="utf-8"))
        assert v["status"] == "PASS", (run, v["status"])
        (label,) = [p.name for p in (RUNS / run / "points").iterdir()]
        pm = point(run, label).get("metrics", {})
        vals = r["values"]
        for k in ("component_max_C", "air_mean_C", "board_max_C", "C1_board_max_C"):
            if k in pm:
                assert abs(pm[k] - vals[k]) < 0.01, (run, k)
        m = re.search(r"enclosure_k(\d+)_eps0p(\d)_e$", run)
        if m:
            out[("drawn", int(m.group(1)), int(m.group(2)) / 10)] = vals
            continue
        m = re.search(r"enclosure_fix_k5_eps0p(\d)_(shell|br\d+)_long$", run)
        assert m, run
        br = 0 if m.group(2) == "shell" else int(m.group(2)[2:])
        out[("fix", br, int(m.group(1)) / 10)] = vals
    assert len(out) == 14, len(out)
    return d, out


def _c1_limit(rated_C: float) -> float:
    """The client's capacitor rule (CLIENT_REQUIREMENTS.md, REQ-E3): life doubles per 10 K under the rating;
    5,000 h at the rating must reach 50,000 h; then 1.8 K off for ripple self-heating."""
    return rated_C - 10 * np.log2(50000 / 5000) - 1.8


def enclosure_revb():
    """The sealed enclosure against the client's revision B list: each part against its limit as drawn (bare and
    painted, both board conductivities) and with the recommended bridge (painted, 2 and 5 W/mK); and the board's
    temperature along its length, which shows why no bridge saves the capacitor at the board's end."""
    d, s = _enc_scores()
    lim = {k: v[1] for k, v in d["limits"].items()}
    c1_lo, c1_hi = d["c1_span_mm"]
    c1_105, c1_125 = _c1_limit(105), _c1_limit(125)
    assert abs(c1_105 - lim["REQ-E3"]) < 0.05, c1_105            # the rule reproduces the client's 70 C
    new_c1 = round(c1_125)                                          # 90 C, as the page states
    assert abs(c1_125 - new_c1) < 0.05, c1_125

    fig, gs = fk.new(FULL, 5.0, 1, 2, wspace=0.30, top=0.84, width_ratios=[1.12, 1.0])
    gs.update(left=0.235, right=0.88, bottom=0.62 / 5.0)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax, grid="x")

    drawn = lambda eps, key: [s[("drawn", k, eps)][key] for k in (5, 20)]          # noqa: E731
    fixed = lambda key: [s[("fix", b, 0.9)][key] for b in (2, 5)]                    # noqa: E731
    groups = [
        ("U1 regulator", "component_max_C", lim["REQ-E1"], [("bare, as drawn", drawn(0.1, "component_max_C")),
                                                            ("painted, as drawn", drawn(0.9, "component_max_C")),
                                                            ("painted, with bridge", fixed("component_max_C"))]),
        ("Board, anywhere", "board_max_C", lim["REQ-E2"], [("bare, as drawn", drawn(0.1, "board_max_C")),
                                                           ("painted, as drawn", drawn(0.9, "board_max_C")),
                                                           ("painted, with bridge", fixed("board_max_C"))]),
        ("Air inside", "air_mean_C", lim["REQ-E4"], [("bare, as drawn", drawn(0.1, "air_mean_C")),
                                                     ("painted, as drawn", drawn(0.9, "air_mean_C")),
                                                     ("painted, with bridge", fixed("air_mean_C"))]),
        ("C1, as specified", "C1_board_max_C", lim["REQ-E3"], [("bare, as drawn", drawn(0.1, "C1_board_max_C")),
                                                                          ("painted, as drawn", drawn(0.9, "C1_board_max_C")),
                                                                          ("painted, with bridge", fixed("C1_board_max_C"))]),
        ("C1 as a 125 °C part", "C1_board_max_C", float(new_c1), [("painted, as drawn", drawn(0.9, "C1_board_max_C")),
                                                                   ("painted, with bridge", fixed("C1_board_max_C"))]),
    ]
    x0, x1 = 50, 172
    ax.set_xlim(x0, x1)
    y, ticks, names = 0.0, [], []
    for title, _, limit_C, rows in groups:
        top = y + 0.55
        for name, vals in rows:
            lo, hi = min(vals), max(vals)
            ax.plot([lo, hi], [y, y], color=fk.AXIS, linewidth=2.2, zorder=3)
            for v in vals:
                fk.status_dot(ax, v, y, "meets" if v <= limit_C else "misses", size=48)
            if "C1" in title or ("bridge" in name and title != "Air inside"):
                txt = f"{lo:.0f}" if round(lo) == round(hi) else f"{lo:.0f}–{hi:.0f}"
                if hi < limit_C < hi + 14:                                  # the text would cross the limit line
                    fk.label(ax, lo, y, txt, dx=-7, ha="right", size=8.5, color=INK2)
                else:
                    fk.label(ax, hi, y, txt, dx=7, size=8.5, color=INK2)
            ticks.append(y); names.append(name)
            y -= 1.0
        bot = y + 0.45
        ax.fill_betweenx([bot, top], limit_C, x1, color=fk.FAIL, alpha=0.07, linewidth=0, zorder=0.5)
        ax.plot([limit_C, limit_C], [bot, top], color=INK2, linewidth=1.1, zorder=1)
        ax.text(limit_C, top + 0.05, f"{limit_C:.0f} °C", ha="center", va="bottom", fontsize=8, color=INK2)
        ax.text(-0.53, top + 0.05, title, transform=ax.get_yaxis_transform(), ha="left", va="bottom", fontsize=9,
                fontweight="bold", color=INK)
        y -= 0.95
    ax.set_yticks(ticks, names)
    ax.set_ylim(y + 0.55, 1.05)
    ax.set_xlabel("temperature, °C")
    fk.panel(ax, "Each part against its limit")

    # the board's temperature along its length
    bx = fig.add_subplot(gs[0, 1])
    fk.style(bx, grid="y")
    order = [("as drawn", ("drawn", 5, 0.9), fk.MUTED, (0, (4, 3))), ("shell, no bridge", ("fix", 0, 0.9), "#9ecae1", "-"),
             ("2 W/mK bridge", ("fix", 2, 0.9), "#4292c6", "-"), ("5 W/mK", ("fix", 5, 0.9), "#2171b5", "-"),
             ("20 W/mK", ("fix", 20, 0.9), "#08306b", "-")]
    bx.set_xlim(0, 100)
    bx.set_ylim(55, 101)
    bx.axvspan(c1_lo, c1_hi, color=fk.GRID, alpha=0.9, linewidth=0, zorder=0.3)
    bx.axvspan(40, 60, color=fk.GRID, alpha=0.5, linewidth=0, zorder=0.3)
    bx.text((c1_lo + c1_hi) / 2, 100.2, "C1", ha="center", va="top", fontsize=8.5, color=INK2, fontweight="bold")
    bx.text(50, 100.2, "U1", ha="center", va="top", fontsize=8.5, color=INK2, fontweight="bold")
    for name, key, color, ls in order:
        prof = np.array(s[key]["board_profile"])
        left, right = prof[prof[:, 0] < 50], prof[prof[:, 0] > 50]
        for part in (left, right):
            bx.plot(part[:, 0], part[:, 1], color=color, linestyle=ls, linewidth=2.0, zorder=3)
        bx.plot([41, 59], [s[key]["component_max_C"]] * 2, color=color, linestyle=ls, linewidth=2.0, zorder=3)
        fk.label(bx, 100, right[-1, 1], name, dx=4, dy={"as drawn": 5, "shell, no bridge": -4}.get(name, 0), size=8.2,
                 color=INK2)
    for val, text in ((lim["REQ-E3"], "105 °C part"), (float(new_c1), "125 °C part")):
        bx.fill_between([c1_lo, c1_hi], val, 101, color=fk.FAIL, alpha=0.06, linewidth=0, zorder=0.4)
        bx.plot([c1_lo, c1_hi], [val, val], color=INK2, linewidth=1.1, zorder=1)
    bx.text(1, 56.2, f"C1's limit: {lim['REQ-E3']:.0f} °C as specified, {new_c1:.0f} °C as a 125 °C part", ha="left",
            va="bottom", fontsize=8, color=INK2)
    bx.set_xlabel("position along the board, mm")
    bx.set_ylabel("temperature, °C")
    fk.panel(bx, "Along the board, painted inside")

    fk.heading(fig, "No bridge saves the capacitor; a 125 °C capacitor with a bridge passes every limit",
               "The client's per-part limits · settled OpenFOAM runs · each pair: the two board conductivities, or "
               "2 and 5 W/mK bridges")
    # the card's thumbnail is the 3D render's (make_study_renders.py)
    fig.savefig(fk.OUT / "fig_enclosure_revb.svg", format="svg", dpi=300, metadata={"Date": None, "Creator": None})
    fk.plt.close(fig)
    print("fig enclosure_revb")


def _foam_field(path: Path, vector: bool = False) -> np.ndarray:
    import re
    s = path.read_text(encoding="utf-8")
    m = re.search(r"internalField\s+nonuniform\s+List<\w+>\s*\n?(\d+)\s*\n?\(", s)
    n, body = int(m.group(1)), s[m.end():]
    if vector:
        a = np.array(re.findall(r"\(([-\d.e+]+) ([-\d.e+]+) ([-\d.e+]+)\)", body)[:n], float)
    else:
        a = np.array(body.split(")")[0].split(), float)
    assert len(a) == n, (path, len(a), n)
    return a


def _enc_section(run: str):
    """Every region's final cell temperatures (C) on one grid, from the run's kept final fields."""
    (label,) = [p.name for p in (RUNS / run / "points").iterdir()]
    solver = RUNS / run / "points" / label / "solver"
    (tdir,) = [p for p in solver.iterdir() if p.name.isdigit()]
    cells = []
    for reg in sorted(tdir.iterdir()):
        C = _foam_field(reg / "C", vector=True) * 1000
        T = _foam_field(reg / "T") - 273.15
        cells.append((reg.name, C[:, 0], C[:, 1], T))
    xs = np.unique(np.round(np.concatenate([c[1] for c in cells]), 3))
    ys = np.unique(np.round(np.concatenate([c[2] for c in cells]), 3))
    edge = lambda c: np.concatenate([[c[0] - (c[1] - c[0]) / 2], (c[1:] + c[:-1]) / 2, [c[-1] + (c[-1] - c[-2]) / 2]])  # noqa: E731
    grid = np.full((len(ys), len(xs)), np.nan)
    for _, x, yy, T in cells:
        i = np.searchsorted(ys, np.round(yy, 3)); j = np.searchsorted(xs, np.round(x, 3))
        assert np.all(np.isnan(grid[i, j])), "two regions share a cell"
        grid[i, j] = T
    return edge(xs), edge(ys), grid, {name: (x, yy, T) for name, x, yy, T in cells}


def enclosure_field():
    """Where the heat sits in the box: the final temperature field of the as-drawn painted corner (5 W/mK board)
    and of the recommended design (painted, 2 W/mK bridge), on one colour scale, read from each run's kept final
    fields and gated on the scores the requirements were judged on."""
    d, s = _enc_scores()
    runs = {r["run"]: r for r in d["runs"]}
    pick = [("As drawn, painted inside", next(k for k in runs if k.endswith("enclosure_k5_eps0p9_e")), ("drawn", 5, 0.9)),
            ("Recommended: shell and a 2 W/mK bridge to the lid", next(k for k in runs if k.endswith("enclosure_fix_k5_eps0p9_br2_long")),
             ("fix", 2, 0.9))]
    secs = []
    for title, run, key in pick:
        ex, ey, grid, reg = _enc_section(run)
        sc = s[key]
        assert abs(np.nanmax(reg["component"][2]) - sc["component_max_C"]) < 0.01, run
        assert abs(np.nanmax(reg["board"][2]) - sc["board_max_C"]) < 0.01, run
        assert abs(np.mean(reg["fluid"][2]) - sc["air_mean_C"]) < 1.5, run           # a cell average, not volume-weighted
        secs.append((title, ex, ey, grid, reg, sc))
    vmin = np.floor(min(np.nanmin(g) for _, _, _, g, _, _ in secs) / 5) * 5
    vmax = np.ceil(max(np.nanmax(g) for _, _, _, g, _, _ in secs) / 5) * 5

    fig = fk.plt.figure(figsize=(FULL, 3.05))
    gs = fig.add_gridspec(1, 3, left=0.02, right=0.93, bottom=0.05, top=1 - 0.80 / 3.05, wspace=0.06, width_ratios=[1, 1, 0.035])
    for i, (title, ex, ey, grid, reg, sc) in enumerate(secs):
        ax = fig.add_subplot(gs[0, i])
        pm = ax.pcolormesh(ex, ey, np.ma.masked_invalid(grid), cmap="turbo", vmin=vmin, vmax=vmax, shading="flat", rasterized=True)
        ax.set_aspect("equal")
        ax.set_xlim(ex[0] - 1, ex[-1] + 1); ax.set_ylim(ey[0] - 14, ey[-1] + 1)
        ax.axis("off")
        ax.set_title(title, loc="left", fontsize=9.5, fontweight="bold", color=INK, pad=4)
        bx_, _, _ = reg["board"]
        x_left = bx_.min() - 1
        c1 = (x_left + d["c1_span_mm"][0], x_left + d["c1_span_mm"][1])
        ax.plot(c1, [ey[0] - 3] * 2, color=INK, linewidth=1.4)
        ax.text(sum(c1) / 2, ey[0] - 4.5, f"C1 {sc['C1_board_max_C']:.0f} °C", ha="center", va="top", fontsize=8.2, color=INK)
        ux, _, _ = reg["component"]
        ax.plot([ux.min() - 1, ux.max() + 1], [ey[0] - 3] * 2, color=INK, linewidth=1.4)
        ax.text(ux.mean(), ey[0] - 4.5, f"U1 {sc['component_max_C']:.0f} °C", ha="center", va="top", fontsize=8.2, color=INK)
        ax.text(ex[-1], ey[0] - 4.5, f"air {sc['air_mean_C']:.0f} °C", ha="right", va="top", fontsize=8.2, color=INK2)
        if "bridge" in reg:
            bxx, byy, _ = reg["bridge"]
            ax.add_patch(fk.plt.Rectangle((bxx.min() - 1, byy.min() - 1.04), bxx.max() - bxx.min() + 2, byy.max() - byy.min() + 2.07,
                                          fill=False, edgecolor=INK, linewidth=0.9, linestyle=(0, (3, 2))))
            ax.text(bxx.max() + 2, byy.max() - 2, "bridge", ha="left", va="top", fontsize=8, color=INK)
    cax = fig.add_subplot(gs[0, 2])
    cb = fig.colorbar(pm, cax=cax)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=8.5, length=0, colors=INK2)
    cb.set_label("°C", color=INK2, fontsize=9)
    fk.heading(fig, "The bridge pulls U1's heat into the lid; the board's ends, where C1 sits, stay warm",
               "Final temperature in the 150 × 60 mm section · 15 W inside, 40 °C outside · settled OpenFOAM runs")
    fig.savefig(fk.OUT / "fig_enclosure_field.svg", format="svg", dpi=200, metadata={"Date": None, "Creator": None})
    fk.plt.close(fig)
    print("fig enclosure_field")


def steel_frame():
    """The steel portal frame to AISC 360-22: the second-order moment diagram on the frame (gravity plus lateral,
    the governing case), every check as a share of its limit, and the beam's bracing against the largest ratio."""
    import csv
    run, brace_run = "20261125-231923_steel_frame_portal", "20261125-231927_steel_frame_beam_bracing"
    for r in (run, brace_run):
        assert all(verified(r).values()), r
    pt = point(run, "p00_baseline")
    m, mc = pt["metrics"], pt["solver_outputs"]["member_checks"]
    L_ = limits("steel_frame_portal")
    prm = pt["parameters"]
    H, L = prm["frame_height_m"], prm["bay_span_m"]
    rows = list(csv.DictReader((RUNS / run / "points" / "p00_baseline" / "moment_diagrams.csv").open(encoding="utf-8")))
    s = np.array([float(r["position_along_member"]) for r in rows])
    M = {k: np.array([float(r[f"M_kNm_gravity_lateral_{k}"]) for r in rows]) for k in ("left_column", "right_column", "beam")}
    for k in M:                                        # the saved diagram is the one the member checks used
        assert np.allclose(M[k], mc["gravity_lateral"][k]["moments_kNm"]), k
    # a rigid knee carries the moment round the corner: the sign convention is tension on the member's left
    # (columns run base to top, the beam left to right), so the knees must match in size
    assert abs(abs(M["left_column"][-1]) - abs(M["beam"][0])) < 1e-6 and abs(abs(M["right_column"][-1]) - abs(M["beam"][-1])) < 1e-6

    fig, gs = fk.new(FULL, 3.9, 1, 3, wspace=0.62, top=0.80, width_ratios=[1.55, 1.0, 0.75])
    gs.update(left=0.01, bottom=0.62 / 3.9)
    ax = fig.add_subplot(gs[0, 0])
    sc = 1.15 / max(abs(v).max() for v in M.values())               # m of offset per kN m
    members = {"left_column": (np.zeros_like(s), H * s, (-1.0, 0.0)), "right_column": (np.full_like(s, L), H * s, (-1.0, 0.0)),
               "beam": (L * s, np.full_like(s, H), (0.0, 1.0))}
    for k, (x, y, (nx, ny)) in members.items():
        xd, yd = x + nx * sc * M[k], y + ny * sc * M[k]
        ax.fill(np.r_[x, xd[::-1]], np.r_[y, yd[::-1]], color=MODEL, alpha=0.16, linewidth=0, zorder=2)
        ax.plot(xd, yd, color=MODEL, linewidth=1.8, zorder=3)
    ax.plot([0, 0, L, L], [0, H, H, 0], color=INK, linewidth=2.4, zorder=4, solid_joinstyle="miter")
    for x in (0, L):
        ax.plot([x - 0.45, x + 0.45], [0, 0], color=INK, linewidth=1.4, zorder=4)
        for t in np.linspace(x - 0.45, x + 0.45, 6):
            ax.plot([t, t - 0.18], [0, -0.22], color=INK, linewidth=0.6, zorder=4)
    mid = int(np.argmax(abs(M["beam"])))
    lab = [(0 - sc * M["left_column"][-1], H, abs(M["left_column"][-1]), "right", 0),
           (L - sc * M["right_column"][-1], H, abs(M["right_column"][-1]), "left", 0),
           (L * s[mid], H + sc * M["beam"][mid], abs(M["beam"][mid]), "center", -1),
           (-0.5, 0.35, abs(M["left_column"][0]), "right", 0),
           (L + 0.5, 0.35, abs(M["right_column"][0]), "left", 0)]
    for x, y, v, ha, vpos in lab:
        fk.label(ax, x, y, f"{v:.0f}", dx={"right": -5, "left": 5, "center": 0}[ha], dy=-9 * vpos if vpos else 0,
                 ha=ha, va="top" if vpos == -1 else "center", size=8.5, color=INK2)
    ax.text(L / 2, -0.35, "drawn on the tension side · wind from the left", fontsize=7.8, color=INK2, ha="center", va="top")
    ax.set_aspect("equal")
    ax.set_xlim(-2.0, L + 1.7); ax.set_ylim(-1.0, H + 1.4)
    ax.axis("off")
    fk.panel(ax, "Bending moment, kN m")

    # every check as a share of its limit
    bx = fig.add_subplot(gs[0, 1])
    fk.style(bx, grid="x")
    a1 = L_["max_interaction_ratio"][1]
    checks = [("Beam, Eq. H1-1", [mc[c]["beam"]["H1_ratio"] / a1 for c in ("gravity_lateral", "gravity_notional")]),
              ("Leeward column", [mc[c]["right_column"]["H1_ratio"] / a1 for c in ("gravity_lateral", "gravity_notional")]),
              ("Windward column", [mc[c]["left_column"]["H1_ratio"] / a1 for c in ("gravity_lateral", "gravity_notional")]),
              ("Live-load deflection", [m["live_deflection_mm"] / L_["live_deflection_mm"][1]]),
              ("Service drift", [m["service_drift_mm"] / L_["service_drift_mm"][1]])]
    assert abs(max(max(v) for _, v in checks[:3]) * a1 - m["max_interaction_ratio"]) < 1e-9
    bx.set_xlim(0, 1.25)
    bx.set_ylim(len(checks) - 0.4, -0.7)
    for i, (name, vals) in enumerate(checks):
        bx.plot([0, max(vals)], [i, i], color=fk.AXIS, linewidth=2.2, zorder=2)
        for j, v in enumerate(vals):
            if j == 0:
                fk.status_dot(bx, v, i, "meets" if v <= 1 else "misses", size=52)
            else:
                bx.scatter([v], [i], s=40, facecolor=fk.SURFACE, edgecolor=MODEL, linewidth=1.5, zorder=4)
        fk.label(bx, max(vals), i, f"{max(vals):.2f}", dx=8, size=8.5, color=INK2)
    bx.set_yticks(range(len(checks)), [c[0] for c in checks])
    fk.limit(bx, 1.0, "limit", "above", at=0.99)
    bx.set_xlabel("share of the limit")
    fk.panel(bx, "Every check against its limit")

    # the beam's bracing
    cx = fig.add_subplot(gs[0, 2])
    fk.style(cx, grid="y")
    bp = []
    for d in sorted((RUNS / brace_run / "points").iterdir()):
        q = json.loads((d / "point.json").read_text(encoding="utf-8"))
        bp.append((q["parameters"]["beam_unbraced_length_m"], q["metrics"]["beam_interaction_max"], q["metrics"]["column_interaction_max"]))
    bp.sort()
    lb = [b[0] for b in bp]
    cx.set_xlim(0.8, 6.7); cx.set_ylim(0, 1.15)
    fk.limit(cx, 1.0, "limit 1.0", "above", axis="y", at=0.98)
    cx.plot(lb, [b[1] for b in bp], color=MODEL, zorder=3)
    cx.plot(lb, [b[2] for b in bp], color=fk.MUTED, linestyle=(0, (4, 3)), linewidth=1.6, zorder=3)
    for x, b, c in bp:
        fk.status_dot(cx, x, b, "meets" if b <= 1 else "misses", size=44)
        fk.label(cx, x, b, f"{b:.2f}", dy=9 if b > c else -9, ha="center", va="bottom" if b > c else "top", size=8.2, color=INK2)
    fk.label(cx, lb[-1], bp[-1][2], "columns", dy=-8, ha="right", va="top", size=8.2, color=INK2)
    fk.label(cx, lb[-1], bp[-1][1], "beam", dx=-10, dy=10, ha="right", size=8.2, color=INK2)
    assert lb[-1] == prm["beam_unbraced_length_m"]
    cx.set_xticks(lb, [f"{x:g}" for x in lb])
    cx.set_xlabel("beam unbraced length, m")
    cx.set_ylabel("largest H1-1 ratio")
    fk.panel(cx, "Bracing the beam")

    fk.heading(fig, "Every member and both deflections pass; the unbraced beam sets the margin, at 0.80",
               "AISC 360-22, Direct Analysis Method, second order · filled: gravity plus lateral · ring: gravity plus "
               "notional load")
    # the card's thumbnail is the 3D render's (make_study_renders.py)
    fig.savefig(fk.OUT / "fig_steel_frame.svg", format="svg", dpi=300, metadata={"Date": None, "Creator": None})
    fk.plt.close(fig)
    print("fig steel_frame")


def keyed_shaft():
    """Study 26 part 2: the study session's figure (scripts/make_keyed_shaft_figure.py), converted for the site."""
    from PIL import Image
    src = REPO / "portfolio" / "img" / "keyed_shaft_seat.png"
    Image.open(src).convert("RGB").save(fk.OUT / "fig_keyed_shaft.webp", "WEBP", quality=90, method=6)
    print("fig keyed_shaft")


def steel_knee():
    """Study 28 part 2: the study session's figure (scripts/make_steel_knee_figure.py), converted for the site."""
    from PIL import Image
    src = REPO / "portfolio" / "img" / "steel_knee_frame.png"
    Image.open(src).convert("RGB").save(fk.OUT / "fig_steel_knee.webp", "WEBP", quality=90, method=6)
    print("fig steel_knee")


def crack_surface():
    """Study 24 part 2: the semi-elliptical surface crack. K along the front for the four shapes on the growth path,
    FE against Newman-Raju, and the FE / Newman-Raju ratio by two independent routes against the stated accuracy."""
    import csv
    run, lab = "20261126-204858_surface_crack_mesh_r1", "p02_front_element_rel-0.0125"
    v = json.loads((RUNS / run / "verification.json").read_text(encoding="utf-8"))
    pv = next(p for p in v["points"] if p["label"] == lab)
    failed = [c["id"] for c in pv.get("checks", []) if c["status"] != "PASS"]
    assert all("profile" in c for c in failed), failed          # only the front-shape check, a finding about the reference
    pt = point(run, lab)
    so, m = pt["solver_outputs"], pt["metrics"]
    phi = np.array(so["stations_deg"])
    rows = list(csv.DictReader((RUNS / run / "points" / lab / "k_shapes.csv").open(encoding="utf-8")))
    k = 1 / np.sqrt(1000.0)                                      # MPa√mm to MPa√m
    assert abs(so["rows"][0]["K_fe"][-1] * k - m["K_a0_MPa_sqrt_m"]) < 1e-9

    fig, gs = fk.new(FULL, 3.9, 1, 2, wspace=0.62, top=0.80, width_ratios=[1.35, 1.0])
    gs.update(right=0.84)
    ax = fig.add_subplot(gs[0, 0])
    fk.style(ax, grid="y")
    for r in so["rows"]:
        kf, kn = np.array(r["K_fe"]) * k, np.array(r["K_nr"]) * k
        ax.plot(phi, kn, color=MUTED, linewidth=1.6, zorder=2)
        fk.dots(ax, phi, kf, color=MODEL, size=22)
        fk.label(ax, 90, kn[-1], f"a {r['a_mm']:g} mm", dx=8, size=8.2, color=INK2)
    ax.set_xlim(-3, 93)
    ax.set_xticks([0, 30, 60, 90], ["0\nsurface", "30", "60", "90\ndeepest"])
    ax.set_xlabel("position along the crack front, °")
    ax.set_ylabel("K, MPa√m")
    fk.panel(ax, "K along the front, four shapes as the crack grows")

    bx = fig.add_subplot(gs[0, 1])
    fk.style(bx, grid="y")
    a = [float(r["a_mm"]) for r in rows]
    bx.set_xlim(1.4, 8.1)
    bx.set_ylim(-6.5, 3)
    bx.axhspan(-5, 5, color=GRID, alpha=0.45, linewidth=0, zorder=0)
    bx.axhline(0, color=INK2, linewidth=1.0, zorder=1)
    fk.label(bx, 1.5, 0, "Newman-Raju", dy=5, va="bottom", size=8.2, color=INK2)
    fk.label(bx, 1.5, -5, "its stated accuracy, ±5 %", dy=4, va="bottom", size=8.2, color=INK2)
    series = [("energy_ratio", "energy, whole front", MODEL, "-"), ("opening_ratio", "crack opening", MUTED, "-"),
              ("deep_energy_ratio", "energy, deepest point", MODEL, (0, (4, 2)))]
    for key_, name, col, ls in series:
        y = [100 * (float(r[key_]) - 1) for r in rows]
        bx.plot(a, y, color=col, linestyle=ls, linewidth=1.8, zorder=3)
        fk.dots(bx, a, y, color=col, size=24)
        fk.label(bx, a[-1], y[-1], name, dx=7, size=8.2, color=INK2)
    bx.set_xticks(a, [f"{x:g}" for x in a])
    bx.set_xlabel("crack depth a, mm (plate 10 mm)")
    bx.set_ylabel("FE against Newman-Raju, %")
    fk.panel(bx, "Two independent routes")
    fk.heading(fig, f"The surface flaw: K {m['K_a0_MPa_sqrt_m']:.1f} MPa√m, and at least {round(m['growth_life_cycles'], -2):,.0f} cycles to 80 % of the thickness",
               f"2 mm deep, 10 mm long · {m['life_over_edge_crack']:.2f} × the edge crack's life, so Part 1 is the conservative answer · "
               "dots: FE · lines: Newman-Raju")
    fig.savefig(fk.OUT / "fig_crack_surface.svg", format="svg", dpi=300, metadata={"Date": None, "Creator": None})
    fk.plt.close(fig)
    print("fig crack_surface")


FLAG_STAGES = [   # (row label, run, point): each stage of the Turek-Hron benchmark on its finest level
    ("Solid, static (CSM1)", "20261121-131111_flag_csm1_mesh", "p02_element_size_mm-1.25"),
    ("Solid, static (CSM2)", "20261121-131133_flag_csm2_mesh", "p02_element_size_mm-1.25"),
    ("Solid, swinging (CSM3)", "20261121-184353_flag_csm3_dt_r3", "p02_time_step_s-0.000625"),
    ("Fluid, Re 20 (CFD1)", "20261125-185354_turek_hron_cfd1_nested", "p02_cell_size_m-0.000625"),
    ("Fluid, Re 100 (CFD2)", "20261125-193110_turek_hron_cfd2_nested_r1", "p02_cell_size_m-0.0003125"),
    ("Coupled, steady (FSI1)", "20261123-070600_turek_hron_fsi1_mesh_r2", "p02_fluid_cell_size_m-0.00125"),
    ("Coupled, slow swing (FSI2)", "20261126-011223_turek_hron_fsi2_mesh_c_alpha", "p00_baseline"),
    ("Coupled, fast swing (FSI3)", "20261123-161128_turek_hron_fsi3_mesh_c", "p00_baseline")]
FLAG_WORD = {"uy_A": "tip", "ux_A": "tip, along", "drag": "drag", "lift": "lift", "uy_A_amp": "tip swing",
             "uy_A_freq_Hz": "frequency", "drag_mean": "mean drag", "drag_amp": "drag swing", "lift_amp": "lift swing",
             "ux_A_mean": "tip, along", "frequency_band": "frequency", "uy_mean_band": "tip mean",
             "uy_amplitude_band": "tip swing", "ux_mean_band": "tip, along"}


def flag_fsi():
    """Study 17, the Turek-Hron flag: every stage against its published values as a share of the limit, the
    damped FSI3 time-step check against the 1 % target, and FSI2's swing drifting from the benchmark as the mesh
    is refined (the stated limit)."""
    H = 6.3
    fig, gs = fk.new(FULL, H, 2, 2, wspace=0.62, hspace=0.50, top=0.80, height_ratios=[1.15, 1.0])
    gs.update(left=0.20, right=0.86, bottom=0.55 / H)

    # every stage against the benchmark, each requirement as a share of its limit
    ax = fig.add_subplot(gs[0, :])
    fk.style(ax, grid="x")
    ax.set_xlim(0, 1.25)
    ax.set_ylim(len(FLAG_STAGES) - 0.45, -0.7)
    fk.limit(ax, 1.0, "limit", "above", at=0.995)
    for i, (name, run, lab) in enumerate(FLAG_STAGES):
        ok = verified(run)[lab]                 # CFD2's finest: forces settled to 2.4e-6 against 1e-6, so held
        assert ok or run.endswith("cfd2_nested_r1"), (run, lab)
        m = point(run, lab)["metrics"]
        lim = limits(run.split("_", 1)[1])
        share = []
        for metric, (op, L) in lim.items():
            assert op == "<=" and m[metric] <= L, (run, metric)      # every published-value requirement passes
            share.append((m[metric] / L, metric, m[metric], L))
        share.sort()
        ax.plot([0, share[-1][0]], [i, i], color=fk.AXIS, linewidth=2.2, zorder=2)
        for s, *_ in share[:-1]:
            ax.scatter([s], [i], s=26, facecolor=SURFACE, edgecolor=MODEL, linewidth=1.2, zorder=4)
        s, metric, v, L = share[-1]
        fk.status_dot(ax, s, i, "meets" if ok else "held", size=50)
        word = FLAG_WORD[metric.replace("_deviation_pct", "").replace("_dev_pct", "")]
        fk.label(ax, s, i, f"{word}: {v:.2f} % off, limit {L:g} %" + ("" if ok else ", not verified"), dx=8,
                 size=8.2, color=INK2)
        ax.text(-0.03, i, name, transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=8.8, color=INK)
    ax.set_yticks([])
    ax.set_xlabel("distance from the published value, share of the limit")
    fk.panel(ax, "Each stage against the benchmark")

    # the damped FSI3 time-step check
    dt = json.loads((RUNS / "20261126-011226_turek_hron_fsi3_dt_c_alpha" / "fsi3_dt_alpha_3level_t7999.json").read_text(encoding="utf-8"))
    rows = [(c["metric"].replace("_deviation_pct", ""), 100 * c["value"], 100 * c["tolerance"], c["status"]) for c in dt["run_checks"]
            if c["id"].startswith("discretization_")]
    assert len(rows) == 6 and sum(r[3] == "FAIL" for r in rows) == 1
    rows.sort(key=lambda r: r[1])
    bx = fig.add_subplot(gs[1, 0])
    fk.style(bx, grid="x")
    tol = rows[0][2]
    assert all(r[2] == tol for r in rows)
    bx.set_xlim(0, 1.6)
    bx.set_ylim(len(rows) - 0.45, -0.7)
    fk.limit(bx, tol, f"target {tol:g} %", "above", at=0.995)
    for i, (q, u, _, st) in enumerate(rows):
        ok = st == "PASS"
        assert ok == (u <= tol)
        bx.plot([0, u], [i, i], color=fk.AXIS, linewidth=2.2, zorder=2)
        fk.status_dot(bx, u, i, "meets" if ok else "misses", size=50)
        fk.label(bx, u, i, f"{u:.2f} %", dx=8 if u < 1.3 else -6, dy=0 if u < 1.3 else 10, ha="left", size=8.2, color=INK2)
    bx.set_yticks(range(len(rows)), [FLAG_WORD[r[0]] for r in rows])
    bx.set_xlabel("time-step uncertainty, %")
    fk.panel(bx, "FSI3: three time steps")

    # FSI2: the swing moves away from the benchmark as the mesh is refined
    cx = fig.add_subplot(gs[1, 1])
    fk.style(cx, grid="y")
    f2 = [("20261126-011217_turek_hron_fsi2_mesh_a_alpha", 3.54), ("20261126-011220_turek_hron_fsi2_mesh_b_alpha", 2.5),
          ("20261126-011223_turek_hron_fsi2_mesh_c_alpha", 1.77)]
    series = {"uy_A_amp": [], "drag_amp": [], "lift_amp": [], "uy_A_freq_Hz": []}
    for run, h in f2:
        p = point(run, "p00_baseline")
        assert verified(run)["p00_baseline"] and abs(p["parameters"]["fluid_cell_size_m"] * 1000 - h) < 0.01
        for q in series:
            series[q].append(100 * (p["metrics"][q] / p["parameters"][f"benchmark_{q}"] - 1))
    hs = [h for _, h in f2]
    cx.axhline(0, color=INK2, linewidth=1.1, zorder=1)
    fk.label(cx, hs[1], 0, "published", dy=-6, ha="center", va="top", size=8.2, color=INK2)
    styles = {"uy_A_amp": (MODEL, "-"), "drag_amp": (MODEL, (0, (4, 2))), "lift_amp": (MUTED, "-"), "uy_A_freq_Hz": (MUTED, (0, (1.5, 2)))}
    nudge = {"lift_amp": 5, "drag_amp": -5, "uy_A_amp": 0, "uy_A_freq_Hz": 0}      # the two top ends sit 0.2 % apart
    for q, ys in series.items():
        col, ls = styles[q]
        cx.plot(hs, ys, color=col, linestyle=ls, linewidth=1.8, zorder=3)
        fk.dots(cx, hs, ys, color=col, size=26)
        fk.label(cx, hs[-1], ys[-1], f"{FLAG_WORD[q]} {ys[-1]:+.1f} %", dx=7, dy=nudge[q], size=8.2, color=INK2)
    cx.set_xlim(3.8, 1.5)
    cx.set_xticks(hs, [f"{h:g}" for h in hs])
    cx.set_xlabel("fluid cell size, mm (finer →)")
    cx.set_ylabel("from the published value, %")
    fk.panel(cx, "FSI2: finer isn't closer")

    fk.heading(fig, "Every stage reproduces the published benchmark; three convergence results are reported, not tuned",
               "Turek-Hron flag behind a cylinder · CalculiX, OpenFOAM, preCICE · filled: largest share of its limit · "
               "ring: the stage's other checks")
    thumb(fig, ax, "flag")
    fig.savefig(fk.OUT / "fig_flag.svg", format="svg", dpi=300, metadata={"Date": None, "Creator": None})
    fk.plt.close(fig)
    print("fig flag_fsi")


ALL = {f.__name__: f for f in (cfd_tolerance, cfd_duct, cfd_response, cfd_field, fea_tet4, strap_sweep, fatigue_sweep,
                               strut_sweep, strut_response, proof_response, joint_response, contact_response, fea_response, strap_response,
                               fatigue_sn, fin_response, fin_h_sweep, qc_bump_sweep, cad_sweep, heat_response,
                               qc_liftoff, qc_iso, coldplate_response, pipe_friction, motor_comparison,
                               motor_rotor, pv_nozzle, step_comparison, random_vibration, bracket_uncertainty,
                               fan_rotor, fan_rotor_campbell, crack_growth, motor_efficiency, motor_airgap, oring_seal, shaft_fillet,
                               enclosure_revb, enclosure_field, steel_frame, flag_fsi, crack_surface, keyed_shaft, steel_knee)}
# not on the site (the earlier model's thermal result): motor_thermal

if __name__ == "__main__":
    for name in sys.argv[1:] or ALL:
        ALL[name]()

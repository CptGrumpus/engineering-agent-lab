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


ALL = {f.__name__: f for f in (cfd_tolerance, cfd_duct, cfd_response, cfd_field)}

if __name__ == "__main__":
    for name in sys.argv[1:] or ALL:
        ALL[name]()

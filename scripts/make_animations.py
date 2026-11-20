"""Animated result visuals for the portfolio (portfolio/img/anim_*.gif).

Run from the repository root:  .venv\\Scripts\\python.exe scripts\\make_animations.py

Every frame is drawn from a saved evidence run (time series CSVs are local;
rerun the named case if one is missing). The schematics are drawn to scale in
time; motions are exaggerated by a stated factor so millimetres are visible.

  anim_quarter_car.gif   qc_bump_liftoff, 600 N.s/m at 36 km/h: the wheel
                         leaves the road twice; tire load and body
                         acceleration traced beside it.
  anim_msd.gif           msd_step: the same step force on three damping
                         ratios, with the exact solution overlaid.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.animation import FuncAnimation, PillowWriter  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from harness.plotting import GRID, SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2  # noqa: E402
from harness.runio import read_json, read_series  # noqa: E402

OUT = REPO / "portfolio" / "img"
HOT, BODY, WHEEL = "#d9481c", "#3b4a63", "#56657d"


def zigzag(x, y0, y1, n=7, w=18):
    """Spring polyline from (x, y0) to (x, y1)."""
    ys = np.linspace(y0, y1, 2 * n + 3)
    xs = np.full_like(ys, x)
    xs[2:-2] += np.where(np.arange(2 * n - 1) % 2 == 0, w, -w)
    return xs, ys


def damper(ax, x, y0, y1, color):
    mid = (y0 + y1) / 2
    ax.plot([x, x], [y0, mid - 12], color=color, lw=1.6)
    ax.add_patch(Rectangle((x - 14, mid - 22), 28, 44, fill=False, ec=color, lw=1.6))
    ax.plot([x, x], [mid + 4, y1], color=color, lw=1.6)
    ax.plot([x - 10, x + 10], [mid + 4, mid + 4], color=color, lw=1.6)


def style(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(color=GRID, lw=0.6)
    ax.tick_params(colors=TEXT_2, labelsize=8)
    for s in ax.spines.values():
        s.set_color(GRID)


# --------------------------------------------------------------------------- quarter car

def quarter_car():
    run = REPO / "runs/20261120-105126_qc_bump_liftoff"
    pt = read_json(run / "manifest.json")["points"][0]
    prm = pt["parameters"]
    s = read_series(run / "points" / pt["label"] / "timeseries.csv")
    ms, mu, kt = prm["sprung_mass_kg"], prm["unsprung_mass_kg"], prm["tire_stiffness_N_per_m"]
    ks, cs = prm["suspension_stiffness_N_per_m"], prm["damping_N_s_per_m"]
    V, L, h = prm["speed_m_per_s"], prm["bump_length_m"], prm["bump_height_m"]
    W = (ms + mu) * 9.80665
    t, zs, zu, zr, vs, vu = (s[k] for k in ("t_s", "zs_m", "zu_m", "zr_m", "vs_m_per_s", "vu_m_per_s"))
    load = np.maximum(W + kt * (zr - zu), 0.0) / W                    # total tire load / static
    acc = -(ks * (zs - zu) + cs * (vs - vu)) / ms
    events = pt["solver_outputs"]["tire_events"]
    air = [(events[i][0], events[i + 1][0]) for i in range(0, len(events) - 1, 2)]

    E = 3.0                                                           # motion exaggeration
    dts = W / kt                                                      # static tire deflection, m
    t_end, n = 0.40, 80
    frames = np.linspace(-0.04, t_end, n)

    def road(tt):
        tt = np.asarray(tt)
        return np.where((tt >= 0) & (tt <= L / V), h / 2 * (1 - np.cos(2 * np.pi * tt / (L / V))), 0.0)

    fig = plt.figure(figsize=(10.5, 4.6), facecolor=SURFACE)
    axs = fig.add_axes((0.02, 0.06, 0.40, 0.80))
    axl = fig.add_axes((0.50, 0.53, 0.47, 0.33))
    axa = fig.add_axes((0.50, 0.10, 0.47, 0.33))
    for ax in (axl, axa):
        style(ax)
        for a, b in air:
            ax.axvspan(a, b, color=HOT, alpha=0.12, lw=0)
    axl.plot(t, load, color=SERIES_1, lw=1.6)
    axl.axhline(0.3, color=TEXT_2, lw=0.8, ls="--")
    axl.axhline(1.7, color=TEXT_2, lw=0.8, ls="--")
    axl.text(t_end, 1.72, "limit ±70 %", color=TEXT_2, fontsize=7.5, ha="right", va="bottom")
    axl.set_xlim(frames[0], t_end); axl.set_ylim(-0.1, 2.8)
    axl.set_ylabel("tire load / static", color=TEXT_2, fontsize=8.5)
    axl.set_xticklabels([])
    axa.plot(t, acc, color=SERIES_2, lw=1.6)
    axa.axhline(4.0, color=TEXT_2, lw=0.8, ls="--"); axa.axhline(-4.0, color=TEXT_2, lw=0.8, ls="--")
    axa.set_xlim(frames[0], t_end); axa.set_ylim(-6.5, 6.5)
    axa.set_ylabel("body accel. (m/s²)", color=TEXT_2, fontsize=8.5)
    axa.set_xlabel("time (s); shaded: wheel in the air", color=TEXT_2, fontsize=8.5)
    cur_l = axl.axvline(0, color=TEXT, lw=1.0)
    cur_a = axa.axvline(0, color=TEXT, lw=1.0)
    dot_l, = axl.plot([], [], "o", color=SERIES_1, ms=5)
    dot_a, = axa.plot([], [], "o", color=SERIES_2, ms=5)

    def draw(i):
        tt = frames[i]
        k = int(np.clip(np.searchsorted(t, tt), 0, len(t) - 1))
        z_s, z_u, z_r, ld = (zs[k], zu[k], zr[k], load[k]) if tt >= 0 else (0, 0, 0, 1.0)
        axs.clear()
        axs.set_xlim(-520, 520); axs.set_ylim(-60, 860); axs.set_aspect("equal"); axs.axis("off")
        sx = np.linspace(-520, 520, 300)                              # road, moving under the car (mm)
        ry = 1e3 * E * road(tt + sx / 1e3 / V)
        axs.fill_between(sx, -60, ry, color="#c9ced6", lw=0)
        axs.plot(sx, ry, color=TEXT_2, lw=1.2)
        y_ub = 1e3 * E * (dts + z_u) + 150 - 1e3 * E * dts            # unsprung block bottom
        free = 150 + 1e3 * E * dts                                    # tire spring drawn free length
        contact = ld > 0
        y_c = 1e3 * E * z_r if contact else y_ub - free
        col = TEXT_2 if contact else HOT
        xs_, ys_ = zigzag(0, y_c, y_ub, n=5, w=16)
        axs.plot(xs_, ys_, color=col, lw=1.6)
        axs.plot([-24, 24], [y_c, y_c], color=col, lw=2.5)
        if not contact:
            axs.annotate("wheel in the air", (30, y_c), (120, y_c - 30), color=HOT, fontsize=9,
                         arrowprops=dict(arrowstyle="-", color=HOT, lw=0.8))
        axs.add_patch(FancyBboxPatch((-110, y_ub), 220, 80, boxstyle="round,pad=0,rounding_size=8",
                                     fc=WHEEL, ec="none"))
        axs.text(0, y_ub + 40, "wheel 45 kg", color="white", fontsize=8, ha="center", va="center")
        y_sb = 520 + 1e3 * E * z_s
        xs_, ys_ = zigzag(-45, y_ub + 80, y_sb, n=6, w=16)
        axs.plot(xs_, ys_, color=TEXT_2, lw=1.6)
        damper(axs, 45, y_ub + 80, y_sb, TEXT_2)
        axs.add_patch(FancyBboxPatch((-230, y_sb), 460, 150, boxstyle="round,pad=0,rounding_size=10",
                                     fc=BODY, ec="none"))
        axs.text(0, y_sb + 75, "body 350 kg", color="white", fontsize=9, ha="center", va="center")
        axs.text(-515, 840, f"t = {max(tt, 0) * 1e3:5.0f} ms", color=TEXT, fontsize=10, family="monospace")
        tk = max(tt, 0)
        for cur in (cur_l, cur_a):
            cur.set_xdata([tk, tk])
        dot_l.set_data([tk], [ld]); dot_a.set_data([tk], [acc[k] if tt >= 0 else 0])
        return []

    fig.suptitle("Quarter car over a 40 mm bump at 36 km/h, 600 N·s/m damping (tire that can lift off)",
                 color=TEXT, fontsize=11, x=0.02, ha="left", y=0.98)
    fig.text(0.02, 0.905, "Drawn from the simulation: motions exaggerated 3×, time slowed about 60×.",
             color=TEXT_2, fontsize=8.5)
    anim = FuncAnimation(fig, draw, frames=n, interval=80)
    anim.save(OUT / "anim_quarter_car.gif", writer=PillowWriter(fps=12), dpi=80,
              savefig_kwargs={"facecolor": SURFACE})
    plt.close(fig)


# --------------------------------------------------------------------------- mass-spring-damper

def mass_spring_damper():
    run = REPO / "runs/20261118-200205_msd_step"
    pts = {p["parameters"]["damping_ratio"]: p for p in read_json(run / "manifest.json")["points"]}
    pick = [0.1, 0.3, 0.7]
    data = []
    for z in pick:
        p = pts[z]
        s = read_series(run / "points" / p["label"] / "timeseries.csv")
        ref = np.genfromtxt(run / "points" / p["label"] / "reference.csv", delimiter=",", names=True) \
            if (run / "points" / p["label"] / "reference.csv").exists() else None
        data.append((z, s["t_s"], s["x_m"], ref))
    x_static = max(abs(d[2][-1]) for d in data)
    t_end, n = 1.0, 70
    frames = np.linspace(0, t_end, n)
    cols = ["#2f6fd6", "#1aa36f", "#d9481c"]
    fig = plt.figure(figsize=(10.5, 4.4), facecolor=SURFACE)
    axs = fig.add_axes((0.02, 0.06, 0.36, 0.80))
    axt = fig.add_axes((0.46, 0.14, 0.51, 0.70))
    style(axt)
    for (z, t, x, ref), c in zip(data, cols):
        axt.plot(t, x / x_static, color=c, lw=1.6, label=f"ζ = {z:g}")
        if ref is not None:
            rx = ref[ref.dtype.names[1]]
            axt.plot(ref[ref.dtype.names[0]], rx / x_static, color=TEXT, lw=0.8, ls=":")
    axt.plot([], [], color=TEXT, lw=0.8, ls=":", label="exact solution")
    axt.set_xlim(0, t_end); axt.set_ylim(-0.05, 1.9)
    axt.set_xlabel("time (s)", color=TEXT_2, fontsize=8.5)
    axt.set_ylabel("displacement / static deflection", color=TEXT_2, fontsize=8.5)
    axt.legend(frameon=False, fontsize=8.5, labelcolor=TEXT_2, loc="upper right")
    cur = axt.axvline(0, color=TEXT, lw=1.0)
    dots = [axt.plot([], [], "o", color=c, ms=5)[0] for c in cols]
    E = 160.0                                                          # drawing mm per static deflection

    def draw(i):
        tt = frames[i]
        axs.clear()
        axs.set_xlim(-60, 660); axs.set_ylim(-40, 520); axs.set_aspect("equal"); axs.axis("off")
        axs.add_patch(Rectangle((-40, 470), 680, 18, color="#c9ced6", lw=0))
        for j, ((z, t, x, _), c) in enumerate(zip(data, cols)):
            k = int(np.clip(np.searchsorted(t, tt), 0, len(t) - 1))
            xc = 100 + 200 * j
            y_top = 330 - E * x[k] / x_static
            xs_, ys_ = zigzag(xc - 28, 470, y_top + 60, n=6, w=12)
            axs.plot(xs_, ys_, color=TEXT_2, lw=1.4)
            damper(axs, xc + 28, y_top + 60, 470, TEXT_2)
            axs.add_patch(FancyBboxPatch((xc - 60, y_top), 120, 60, boxstyle="round,pad=0,rounding_size=6",
                                         fc=c, ec="none"))
            axs.text(xc, y_top + 30, f"ζ = {z:g}", color="white", fontsize=9, ha="center", va="center")
            dots[j].set_data([tt], [x[k] / x_static])
        axs.plot([20, 620], [330 - E, 330 - E], color=TEXT_2, lw=0.8, ls="--")
        axs.text(625, 330 - E, "static\nposition", color=TEXT_2, fontsize=7.5, va="center")
        axs.text(-40, -30, f"t = {tt:4.2f} s", color=TEXT, fontsize=10, family="monospace")
        cur.set_xdata([tt, tt])
        return []

    fig.suptitle("Mass-spring-damper: the same step force at three damping ratios",
                 color=TEXT, fontsize=11, x=0.02, ha="left", y=0.98)
    fig.text(0.02, 0.905, "Drawn from the SciPy runs; dotted lines are the exact solution, which every run "
             "matches to its tolerance.", color=TEXT_2, fontsize=8.5)
    anim = FuncAnimation(fig, draw, frames=n, interval=80)
    anim.save(OUT / "anim_msd.gif", writer=PillowWriter(fps=12), dpi=80, savefig_kwargs={"facecolor": SURFACE})
    plt.close(fig)


if __name__ == "__main__":
    quarter_car()
    mass_spring_damper()
    for f in ("anim_quarter_car.gif", "anim_msd.gif"):
        print(f, (OUT / f).stat().st_size // 1024, "KB")

"""Study 18 part 2 portfolio figure, from runs 20261127-143302_nozzle_limit_mesh and _thickness.

(a) Load factor against the crotch corner's displacement for the 12 mm nozzle (finest mesh): elastic, then the
    collapse; the required 1.5 and the collapse load marked.
(b) Collapse load factor against the nozzle wall, with the wall where it reaches 1.5 and part 1's three answers (toe
    line 11.7 mm, pressure-area rule 16 mm, crotch line 20.1 mm).
(c) Where it yields: the equivalent plastic strain on the section along the vessel (y = 0) at 1.5 times the design
    pressure, 12 mm wall, finest mesh.

    .venv/Scripts/python.exe scripts/make_nozzle_limit_figure.py [out.png]
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harness.plotting import GRID, SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2, _style, plt  # noqa: E402

MESH = ROOT / "runs" / "20261127-143302_nozzle_limit_mesh"
THICK = ROOT / "runs" / "20261127-143302_nozzle_limit_thickness"
PART1 = [(11.7, "toe line"), (16.0, "pressure-area\nrule"), (20.1, "crotch line")]


def _point(run: Path, prefix: str) -> tuple[dict, Path]:
    d = sorted((run / "points").glob(prefix + "*"))[0]
    return json.loads((d / "point.json").read_text(encoding="utf-8")), d


def main(out: Path) -> None:
    fine, fine_dir = _point(MESH, "p02")
    o = fine["solver_outputs"]
    h = o["history"]
    lam_c = o["collapse_load_factor"]
    fig = plt.figure(figsize=(13.5, 4.5))
    fig.patch.set_facecolor(SURFACE)
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1.1, 1.25], wspace=0.3)

    ax = fig.add_subplot(gs[0])
    _style(ax)
    u = [0.0] + h["u_crotch_mm"]
    lam = [0.0] + h["lambda"]
    ax.plot(u, lam, "o-", color=SERIES_1, ms=4, lw=1.6, label="crotch corner")
    ax.plot([0, u[1]], [0, lam[1]], ":", color=TEXT_2, lw=0.9)
    ax.plot([0, u[1] * lam_c], [0, lam_c], ":", color=TEXT_2, lw=0.9, label="elastic, extended")
    ax.axhline(1.5, color=TEXT, lw=0.8, ls="--")
    ax.text(0.02, 1.5, " required: 1.5 x design", fontsize=7.5, va="bottom", color=TEXT, transform=ax.get_yaxis_transform())
    ax.axhline(lam_c, color=SERIES_1, lw=0.8, ls="--")
    ax.text(0.02, lam_c, f" collapse: {lam_c:.3f} ({lam_c * 3.5:.2f} MPa)", fontsize=7.5, va="bottom", color=SERIES_1,
            transform=ax.get_yaxis_transform())
    ax.set_ylim(0, 2.0)
    ax.set_xlabel("displacement of the crotch corner (mm)")
    ax.set_ylabel("load factor (pressure / 3.5 MPa)")
    ax.set_title("(a) 12 mm nozzle, no pad", loc="left", fontsize=10, color=TEXT)
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")

    bx = fig.add_subplot(gs[1])
    _style(bx)
    pts = sorted((json.loads(p.read_text(encoding="utf-8")) for p in (THICK / "points").glob("*/point.json")),
                 key=lambda q: float(q["parameters"]["nozzle_thickness_mm"]))
    tn = np.array([float(q["parameters"]["nozzle_thickness_mm"]) for q in pts])
    lc = np.array([q["metrics"]["collapse_load_factor"] for q in pts])
    bx.plot(tn, lc, "o-", color=SERIES_1, lw=1.6, ms=5, label="limit load (this part)")
    bx.axhline(1.5, color=TEXT, lw=0.8, ls="--")
    cyl = pts[0]["solver_outputs"]["cylinder_collapse_pressure_MPa"] / 3.5
    bx.axhline(cyl, color=TEXT_2, lw=0.8, ls=":")
    bx.text(tn[0], cyl, f" the shell without a nozzle: {cyl:.2f}", fontsize=7.5, va="bottom", color=TEXT_2)
    if lc.min() >= 1.5:
        pe = [q["solver_outputs"].get("peeq_max_at_1p5", float("nan")) for q in pts]
        note = "\n".join([f"every wall swept passes; at {tn[0]:g} mm", f"the plastic strain at 1.5 reaches "
                          f"{100 * pe[0]:.0f} %", f"({tn[2]:g} mm: {100 * pe[2]:.1f} %)"])
        bx.text(tn[0] - 0.8, 1.30, note, fontsize=7.5, color=SERIES_1, va="bottom")
    if lc.min() < 1.5 < lc.max():
        t15 = float(np.interp(1.5, lc, tn))
        bx.plot([t15], [1.5], "o", color=SERIES_1, mfc=SURFACE, ms=8)
        bx.annotate(f"passes from\nabout {t15:.1f} mm", (t15, 1.5), xytext=(t15 + 0.6, 1.33), fontsize=8, color=SERIES_1,
                    arrowprops={"arrowstyle": "-", "color": SERIES_1, "lw": 0.7})
    for t, lab in PART1:
        bx.axvline(t, color=SERIES_2, lw=0.8, ls="-.")
        bx.text(t, 1.12, " " + lab, fontsize=7, color=SERIES_2, rotation=90, va="bottom", ha="right")
    bx.set_xlim(7, 21)
    bx.set_ylim(1.1, 2.25)
    bx.set_xlabel("nozzle wall (mm)")
    bx.set_ylabel("collapse load factor")
    bx.set_title("(b) The wall each method asks for", loc="left", fontsize=10, color=TEXT)
    bx.text(0.98, 0.02, "dash-dot: part 1's elastic answers", transform=bx.transAxes, fontsize=7, color=SERIES_2,
            ha="right")

    cx = fig.add_subplot(gs[2])
    _style(cx)
    rows = list(csv.DictReader(open(next(fine_dir.rglob("plastic_zone.csv")), encoding="utf-8")))
    key15 = [k for k in rows[0] if k.startswith("peeq_at_1.5")][0]
    sec = [(float(r["z_mm"]), float(r["x_mm"]), float(r[key15])) for r in rows
           if abs(float(r["y_mm"])) < 1e-6 and float(r[key15]) > 0]
    z, x, e = (np.array(v) for v in zip(*sec)) if sec else (np.zeros(0),) * 3
    # the section outline: shell wall (x 500-516) and nozzle wall (z 100-112), with the 10 mm fillet
    cx.fill_between([100, 260], 500, 516, color=GRID, lw=0)          # the shell wall from the bore's edge
    cx.fill_betweenx([500, 700], 100, 112, color=GRID, lw=0)
    s = cx.scatter(z, x, c=100 * e, s=7, cmap="viridis", vmin=0, vmax=max(0.5, 100 * float(np.percentile(e, 98))))
    cb = fig.colorbar(s, ax=cx, fraction=0.05, pad=0.02)
    cb.set_label("equivalent plastic strain (%)", fontsize=8)
    cx.set_xlim(60, 260)
    cx.set_ylim(470, 600)
    cx.set_aspect("equal")
    cx.set_xlabel("along the vessel from the nozzle axis, z (mm)")
    cx.set_ylabel("radial, x (mm)")
    cx.set_title("(c) Plastic strain at 1.5 x design", loc="left", fontsize=10, color=TEXT)
    cx.text(0.98, 0.04, "section through both axes", transform=cx.transAxes, fontsize=7.5, color=TEXT_2, ha="right")
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "portfolio" / "img" / "nozzle_limit.png")

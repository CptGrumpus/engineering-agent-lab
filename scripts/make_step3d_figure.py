"""Study 19 part 3 portfolio figure: the backward-facing step with the tunnel's side walls, from the committed runs.

(a) Pressure along the step-side wall at mid-span from x = -4 H: the measurements, part 2's 2D model (finest mesh),
    the 3D model with the side walls (its finest spanwise level) and, when run, the thinner side-wall layer; the
    REQ-S3 window at 30 H (measured +- 0.02).
(b) Skin friction at mid-span against the measurements (with their uncertainty).
(c) Skin friction over the floor behind the step, mid-span to side wall, from the 3D model: where the flow reattaches
    across the span (Cf = 0).

The measured tables stay outside the repo (validation/step_driver_seegmiller/compare.py reads them from
~/data/ercoftac_case030/files).

    .venv/Scripts/python.exe scripts/make_step3d_figure.py [out.png]
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from matplotlib.colors import TwoSlopeNorm  # noqa: E402

from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2, _style, plt  # noqa: E402

PART2 = ROOT / "runs" / "20261122-233146_step_mesh" / "points" / "p02_mesh_level-1.4142"
DATA = Path.home() / "data" / "ercoftac_case030" / "files"
LABEL_BOX = {"facecolor": SURFACE, "alpha": 0.85, "edgecolor": "none", "pad": 1.5}
_spec = importlib.util.spec_from_file_location("step_compare", ROOT / "validation" / "step_driver_seegmiller" / "compare.py")
CMP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CMP)


def latest_run(case: str) -> Path | None:
    runs = sorted(p for p in (ROOT / "runs").glob(f"*_{case}") if (p / "report.md").exists())
    return runs[-1] if runs else None


def finest_point(run: Path, param: str = "spanwise_level") -> Path:
    pts = [p for p in (run / "points").glob("*/point.json")
           if json.loads(p.read_text(encoding="utf-8")).get("status") == "completed"]
    return max(pts, key=lambda p: float(json.loads(p.read_text(encoding="utf-8"))["parameters"][param])).parent


def wall(pdir: Path) -> tuple[np.ndarray, np.ndarray]:
    with open(pdir / "wall.csv", newline="", encoding="utf-8") as f:
        rows = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(f)]
    return np.array([r["x_over_h"] for r in rows]), np.array([r["cf"] for r in rows])


def main(out: Path) -> None:
    side = latest_run("step3d_sidewalls")
    thin = latest_run("step3d_sidewall_start")
    p3 = finest_point(side)
    o3 = json.loads((p3 / "point.json").read_text(encoding="utf-8"))["solver_outputs"]
    o2 = json.loads((PART2 / "point.json").read_text(encoding="utf-8"))["solver_outputs"]
    cf_m, cp_m = CMP.measured_cf(DATA), CMP.measured_cp(DATA)
    cp_m0 = np.interp(-4.0, cp_m[:, 0], cp_m[:, 1])
    meas = float(np.interp(30.0, cp_m[:, 0], cp_m[:, 1]) - cp_m0)

    fig, (ax, bx, cx) = plt.subplots(1, 3, figsize=(16, 4.6), gridspec_kw={"width_ratios": [1, 1, 1.15]})
    fig.patch.set_facecolor(SURFACE)
    for a in (ax, bx, cx):
        _style(a)

    # (a) pressure along the wall at mid-span
    ax.plot(o2["profiles"]["x_p_over_h"], o2["profiles"]["cp"], color=SERIES_2, lw=1.4,
            label=f"2D, no side walls (part 2): {o2['cp_recovery_30h']:.3f}")
    ax.plot(o3["profiles"]["x_p_over_h"], o3["profiles"]["cp"], color=SERIES_1, lw=2,
            label=f"3D with side walls: {o3['cp_recovery_30h']:.3f}")
    if thin:
        ot = json.loads((finest_point(thin) / "point.json").read_text(encoding="utf-8"))["solver_outputs"]
        ax.plot(ot["profiles"]["x_p_over_h"], ot["profiles"]["cp"], color=SERIES_1, lw=1.2, ls=(0, (4, 2)),
                label=f"3D, thinner side-wall layer: {ot['cp_recovery_30h']:.3f}")
    ax.plot(cp_m[:, 0], cp_m[:, 1] - cp_m0, "o", ms=4.5, color=TEXT, mfc="none", label=f"measured: {meas:.3f}")
    ax.errorbar([30.0], [meas], yerr=[[0.02], [0.02]], fmt="none", ecolor=TEXT_2, elinewidth=1.4, capsize=4, zorder=5)
    ax.text(30.0, meas - 0.024, "REQ-S3 window:
measured +- 0.02", fontsize=7.5, color=TEXT_2, ha="center", va="top")
    ax.set_xlim(-6, 36)
    ax.set_xlabel("x / H (step at 0)")
    ax.set_ylabel("C_p - C_p(-4 H), step-side wall, mid-span")
    ax.set_title("(a) Pressure recovery", fontsize=10, color=TEXT, loc="left")
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")

    # (b) skin friction at mid-span
    x2, c2 = wall(PART2)
    x3, c3 = wall(p3)
    bx.plot(x2, c2 * 1e3, color=SERIES_2, lw=1.4, label="2D (part 2)")
    bx.plot(x3, c3 * 1e3, color=SERIES_1, lw=2, label="3D, mid-span")
    bx.errorbar(cf_m[:, 0], cf_m[:, 1] * 1e3, yerr=np.abs(cf_m[:, 1] * cf_m[:, 2]) * 1e3, fmt="o", ms=4.5,
                color=TEXT, mfc="none", capsize=2, label="measured")
    bx.axhline(0, color=TEXT_2, lw=0.6)
    bx.axvspan(10, 30, color=TEXT_2, alpha=0.06)
    bx.set_xlim(-2, 36)
    bx.set_xlabel("x / H")
    bx.set_ylabel("C_f x 1000")
    bx.set_title(f"(b) Skin friction; reattachment {o3['xr_over_h']:.2f} H (2D {o2['xr_over_h']:.2f}, measured 6.26)",
                 fontsize=10, color=TEXT, loc="left")
    bx.legend(frameon=False, fontsize=7.5, loc="lower right")

    # (c) floor skin friction map
    m = o3["floor_cf_map"]
    xs, zs, cf = np.asarray(m["x_over_h"]), np.asarray(m["z_mm"]), np.asarray(m["cf"]) * 1e3
    sel = xs <= 36
    # the mid-span plane is a symmetry plane (zero spanwise gradient): its values are the first layer's
    first = sel & (zs <= zs[sel].min() + 1e-9)
    xs, zs, cf = np.concatenate([xs, xs[first]]), np.concatenate([zs, 0 * zs[first]]), np.concatenate([cf, cf[first]])
    sel = np.concatenate([sel, first[first]])
    lim = float(np.percentile(np.abs(cf[sel]), 99))
    tc = cx.tricontourf(xs[sel], zs[sel], cf[sel], levels=24, cmap="RdBu_r", norm=TwoSlopeNorm(0, -lim, lim))
    cx.tricontour(xs[sel], zs[sel], cf[sel], levels=[0.0], colors=TEXT, linewidths=1.2)
    cb = fig.colorbar(tc, ax=cx, pad=0.02)
    cb.set_label("C_f x 1000 (blue: reversed flow)", fontsize=8, color=TEXT_2)
    cb.ax.tick_params(labelsize=8, colors=TEXT_2)
    cx.axhline(o3["half_span_m"] * 1e3, color=TEXT, lw=2)
    cx.text(35, o3["half_span_m"] * 1e3 - 2, "side wall", fontsize=8, color=TEXT, va="top", ha="right", bbox=LABEL_BOX)
    cx.text(35, 2, "mid-span (symmetry plane)", fontsize=8, color=TEXT, va="bottom", ha="right", bbox=LABEL_BOX)
    cx.set_xlim(0, 36)
    cx.set_ylim(0, o3["half_span_m"] * 1e3)
    cx.set_xlabel("x / H")
    cx.set_ylabel("z from mid-span (mm)")
    cx.set_title("(c) Floor behind the step: black line, C_f = 0", fontsize=10, color=TEXT, loc="left")
    fig.tight_layout()
    fig.savefig(out, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    print(out)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "portfolio" / "img" / "step3d_sidewalls.png")

"""Study 11 part 2 portfolio figure, from runs 20261127-170409_duct_section_plate and -170502_duct_section_bounds.

(a) The broad wall's excess over the bulk across the half width, for aluminium plates of 0.1 to 4 mm and the
    perfect-spreading bound, against the parallel plates of study 11.
(b) The peak wall temperature against the plate's thickness, against the 45 C limit and study 11's 2D value.

    .venv/Scripts/python.exe scripts/make_duct_section_figure.py [out.png]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2, _style, plt  # noqa: E402

PLATE = ROOT / "runs" / "20261127-170409_duct_section_plate"
BOUNDS = ROOT / "runs" / "20261127-170502_duct_section_bounds"
SHADES = ["#b5d3f5", "#86b6ec", "#5795e0", "#2a78d6", "#14559e", "#0b3d78"]


def _pts(run):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((run / "points").glob("*/point.json"))]


def main(out: Path) -> None:
    plates = sorted(_pts(PLATE), key=lambda q: float(q["parameters"]["plate_thickness_mm"]))
    bounds = _pts(BOUNDS)
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(11.5, 4.3), gridspec_kw={"width_ratios": [1.2, 1]})
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    for q, col in zip(plates, SHADES):
        o = q["solver_outputs"]
        s, z, tw = o["qH_over_k_K"], np.asarray(o["zc_mm"]), np.asarray(o["tw_z_rel"])
        tb = tw.mean() - o["wall_mean_excess_rel"]
        ax.plot(z, s * (tw - tb), color=col, lw=1.5, label=f"{float(q['parameters']['plate_thickness_mm']):g} mm")
    h1 = next(q for q in bounds if float(q["parameters"]["plate_conductivity_W_per_mK"]) > 1)
    o = h1["solver_outputs"]
    s = o["qH_over_k_K"]
    ax.axhline(s * o["wall_peak_excess_rel"], color=TEXT_2, lw=0.9, ls=":", label="perfect spreading")
    ax.axhline(s * 17 / 70, color=SERIES_2, lw=1.2, ls="--", label="parallel plates (study 11)")
    ax.set_xlim(0, 10)
    ax.set_ylim(11.0, 14.0)
    ax.set_xlabel("across the passage from mid-width (mm); the side wall at 10")
    ax.set_ylabel("wall minus bulk temperature (K)")
    ax.set_title("(a) The wall runs hot near the side wall", loc="left", fontsize=10, color=TEXT)
    ax.legend(frameon=False, fontsize=7.5, loc="upper left", ncol=2, title="aluminium plate", title_fontsize=7.5)

    _style(bx)
    t = np.array([float(q["parameters"]["plate_thickness_mm"]) for q in plates])
    T = np.array([q["metrics"]["wall_peak_temperature_C"] for q in plates])
    bx.semilogx(t, T, "o-", color=SERIES_1, lw=1.6, ms=5, label="peak wall, with the side walls")
    bx.axhline(45.0, color=TEXT, lw=0.9, ls=":", label="limit 45 C")
    bx.axhline(float(plates[0]["parameters"]["wall_temperature_2D_C"]), color=SERIES_2, lw=1.2, ls="--",
               label="study 11 (parallel plates): 44.03 C")
    for ti, Ti in zip(t, T):
        bx.annotate(f"{Ti:.2f}", (ti, Ti), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=7.5,
                    color=SERIES_1)
    bx.set_xticks(t, [f"{v:g}" for v in t])
    bx.set_ylim(43.9, 46.1)
    bx.set_xlabel("aluminium plate thickness (mm)")
    bx.set_ylabel("peak wall temperature (C)")
    bx.set_title("(b) Any plate over 0.25 mm keeps the verdict", loc="left", fontsize=10, color=TEXT)
    bx.legend(frameon=False, fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(out, dpi=150, facecolor=SURFACE)
    plt.close(fig)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "portfolio" / "img" / "duct_section.png")

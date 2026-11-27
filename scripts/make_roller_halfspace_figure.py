"""Study 10 part 2 portfolio figure, from runs 20261127-172125_roller_hs_crown, -172428_roller_hs_mesh,
-172625_roller_hs_plain and -172828_roller_hs_square.

(a) The peak contact pressure along the roller (finest grid) for square ends, a 1 mm edge radius and the chosen
    logarithmic crown, against the 650 MPa limit and the long roller of study 10.
(b) The peak pressure against the crown's size (A in multiples of Lundberg's value).

    .venv/Scripts/python.exe scripts/make_roller_halfspace_figure.py [out.png]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2, _style, plt  # noqa: E402

RUNS = ROOT / "runs"
CROWN = RUNS / "20261127-172125_roller_hs_crown"
CASES = [("20261127-172828_roller_hs_square", "square ends", "#9a9a9a"),
         ("20261127-172625_roller_hs_plain", "1 mm edge radius", SERIES_2),
         ("20261127-172428_roller_hs_mesh", "log crown, A = 1.3 x Lundberg", SERIES_1)]


def _finest(run: Path) -> dict:
    pts = [json.loads(p.read_text(encoding="utf-8")) for p in (run / "points").glob("*/point.json")]
    return max(pts, key=lambda q: float(q["parameters"]["grid_scale"]))


def main(out: Path) -> None:
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(11.5, 4.3), gridspec_kw={"width_ratios": [1.25, 1]})
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    long_roller = None
    for run, lab, col in CASES:
        q = _finest(RUNS / run)
        o = q["solver_outputs"]
        long_roller = q["derived"]["long_roller_hertz_MPa"]
        ax.plot(o["y_mm"], o["peak_along_MPa"], "-", color=col, lw=1.6, label=f"{lab}: peak {o['peak_MPa']:.0f} MPa")
    ax.axhline(650, color=TEXT, lw=0.9, ls=":", label="limit 650 MPa")
    ax.axhline(long_roller, color=TEXT_2, lw=0.9, ls="--", label=f"long roller (study 10): {long_roller:.0f} MPa")
    ax.set_yscale("log")
    ax.set_ylim(300, 4000)
    from matplotlib.ticker import NullFormatter
    ax.set_yticks([300, 400, 500, 650, 1000, 2000, 3000], ["300", "400", "500", "650", "1000", "2000", "3000"])
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_xlim(0, 15)
    ax.set_xlabel("along the roller from mid-length (mm); the end at 15")
    ax.set_ylabel("peak contact pressure across the contact (MPa)")
    ax.set_title("(a) A straight roller loads its ends; a crown does not", loc="left", fontsize=10, color=TEXT)
    ax.legend(frameon=False, fontsize=7.5, loc="upper left")
    ax.text(0.99, 0.03, "square and edge-radius peaks grow with the grid (finest shown)", transform=ax.transAxes,
            fontsize=7, color=TEXT_2, ha="right")

    _style(bx)
    pts = sorted((json.loads(p.read_text(encoding="utf-8")) for p in (CROWN / "points").glob("*/point.json")),
                 key=lambda q: float(q["parameters"]["crown_A_factor"]))
    f = np.array([float(q["parameters"]["crown_A_factor"]) for q in pts])
    pk = np.array([q["metrics"]["peak_contact_pressure_MPa"] for q in pts])
    at_end = np.array([q["metrics"]["peak_from_end_mm"] < 1.0 for q in pts])
    bx.plot(f, pk, "-", color=SERIES_1, lw=1.4)
    bx.plot(f[at_end], pk[at_end], "s", color=SERIES_2, ms=6, label="peak near the end")
    bx.plot(f[~at_end], pk[~at_end], "o", color=SERIES_1, ms=6, label="peak at mid-length")
    bx.axhline(650, color=TEXT, lw=0.9, ls=":")
    bx.axhline(long_roller, color=TEXT_2, lw=0.9, ls="--")
    k = int(np.argmin(pk))
    bx.annotate(f"best: {pk[k]:.0f} MPa", (f[k], pk[k]), xytext=(f[k] + 0.3, pk[k] + 14), fontsize=8, color=SERIES_1,
                arrowprops={"arrowstyle": "-", "color": SERIES_1, "lw": 0.7})
    bx.set_xlabel("crown size A / Lundberg's A (1.38 µm)")
    bx.set_ylabel("peak contact pressure (MPa)")
    bx.set_title("(b) The crown has a window: 1.1 to 2.5 x", loc="left", fontsize=10, color=TEXT)
    bx.legend(frameon=False, fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(out, dpi=150, facecolor=SURFACE)
    plt.close(fig)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "portfolio" / "img" / "roller_halfspace.png")

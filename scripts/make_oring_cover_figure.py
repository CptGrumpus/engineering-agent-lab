"""Study 25 part 2 portfolio figure, from run 20261127-162214_oring_cover_thickness_r1.

(a) The cover's lift at the seal line around the quarter (bolt at 45 deg), for each thickness.
(b) The squeeze left at the loosest corner against the cover's thickness, against the 15 % minimum and part 1's flat
    cover.

    .venv/Scripts/python.exe scripts/make_oring_cover_figure.py [out.png]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2, _style, plt  # noqa: E402

RUN = ROOT / "runs" / "20261127-162214_oring_cover_thickness_r1"
SHADES = ["#0b3d78", "#2a78d6", "#6ea8e8", "#b5d3f5"]


def main(out: Path) -> None:
    pts = sorted((json.loads(p.read_text(encoding="utf-8")) for p in (RUN / "points").glob("*/point.json")),
                 key=lambda q: float(q["parameters"]["cover_thickness_mm"]))
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(11.5, 4.2), gridspec_kw={"width_ratios": [1.2, 1]})
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    for q, col in zip(pts, SHADES):
        o = q["solver_outputs"]
        ax.plot(o["seal_line_deg"], 1e3 * np.asarray(o["seal_line_lift_mm"]), "-", color=col, lw=1.6,
                label=f"{float(q['parameters']['cover_thickness_mm']):g} mm cover")
    ax.axvline(45, color=TEXT_2, lw=0.8, ls=":")
    ax.text(45, 1, " bolt", fontsize=8, color=TEXT_2)
    ax.set_xlim(0, 90)
    ax.set_ylim(0, None)
    ax.set_xlabel("angle around the seal (deg): the quarter between two bolt gaps")
    ax.set_ylabel("lift of the cover at the seal (µm)")
    ax.set_title("(a) The cover lifts most midway between bolts", loc="left", fontsize=10, color=TEXT)
    ax.legend(frameon=False, fontsize=8, loc="upper center", ncol=2)

    _style(bx)
    t = np.array([float(q["parameters"]["cover_thickness_mm"]) for q in pts])
    sq = np.array([q["metrics"]["loosest_squeeze_with_lift_pct"] for q in pts])
    flat = pts[0]["derived"]["loosest_squeeze_flat_pct"]
    bx.plot(t, sq, "o-", color=SERIES_1, lw=1.6, ms=5, label="with the cover's lift (this part)")
    bx.axhline(flat, color=SERIES_2, lw=1.2, ls="--", label=f"flat rigid cover (part 1): {flat:.1f} %")
    bx.axhline(15.0, color=TEXT, lw=0.9, ls=":", label="minimum 15 %")
    for ti, si in zip(t, sq):
        bx.annotate(f"{si:.2f} %", (ti, si), xytext=(0, -13), textcoords="offset points", ha="center", fontsize=7.5,
                    color=SERIES_1)
    bx.set_ylim(14.5, 17.6)
    bx.set_xlabel("cover thickness (mm), 6061-T6, 4 x M6")
    bx.set_ylabel("squeeze at the loosest corner (%)")
    bx.set_title("(b) Any practical cover keeps the margin", loc="left", fontsize=10, color=TEXT)
    bx.legend(frameon=False, fontsize=8, loc="center right")
    fig.tight_layout()
    fig.savefig(out, dpi=150, facecolor=SURFACE)
    plt.close(fig)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "portfolio" / "img" / "oring_cover.png")

"""Study 23 part 2 portfolio figure, from run 20261127-120457_rotor_solid_detail.

(a) The first lateral frequency at rest, soft bearings, from the 3D solid and from ROSS's beam model, as the rotor's
    detail is added: the beam model raises it with the hub, the solid lowers it.
(b) The first forward critical speed corrected by the solid, against REQ-G1's 3450 rpm (15 % over 3000 rpm).

    .venv/Scripts/python.exe scripts/make_rotor_solid_figure.py [out.png]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harness.plotting import GRID, SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2, _style, plt  # noqa: E402

RUN = ROOT / "runs" / "20261127-120457_rotor_solid_detail"
SCEN = [("p00_uniform", "uniform\n(part 1's rotor)"), ("p02_journals", "+ journals"), ("p01_hub", "+ hub"),
        ("p03_detailed", "hub +\njournals")]


def main(out: Path) -> None:
    pts = {lab: json.loads((RUN / "points" / lab / "point.json").read_text(encoding="utf-8"))["metrics"]
           for lab, _ in SCEN + [("p04_detailed_kb1e8", "")]}
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(11.5, 4.4), gridspec_kw={"width_ratios": [1.3, 1]})
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    x = np.arange(len(SCEN))
    ross = [pts[lab]["ross_f1_hz"] for lab, _ in SCEN]
    solid = [pts[lab]["solid_f1_hz"] for lab, _ in SCEN]
    ax.bar(x - 0.19, ross, 0.36, color=SERIES_2, label="ROSS beam model (hub as a 130 mm shaft section)")
    ax.bar(x + 0.19, solid, 0.36, color=SERIES_1, label="3D solid (CalculiX)")
    for xi, r, s in zip(x, ross, solid):
        ax.text(xi - 0.19, r + 0.08, f"{r:.2f}", ha="center", fontsize=8, color=TEXT_2)
        ax.text(xi + 0.19, s + 0.08, f"{s:.2f}", ha="center", fontsize=8, color=TEXT)
    ax.set_xticks(x, [n for _, n in SCEN], fontsize=8.5)
    ax.set_ylim(60.5, 63.2)
    ax.set_ylabel("first lateral frequency at rest (Hz)")
    ax.set_title("(a) Soft bearings (1e7 N/m): the detail added", loc="left", fontsize=10, color=TEXT)
    ax.legend(loc="upper center", frameon=False, fontsize=8, bbox_to_anchor=(0.5, -0.17))

    _style(bx)
    labels = ["part 1\n(beam)", "detailed,\nsoft bearings", "detailed,\nstiff bearings"]
    vals = [pts["p00_uniform"]["ross_critical_rpm"], pts["p03_detailed"]["corrected_critical_rpm"],
            pts["p04_detailed_kb1e8"]["corrected_critical_rpm"]]
    cols = [TEXT_2, SERIES_1, SERIES_1]
    bx.bar(np.arange(3), vals, 0.55, color=cols)
    for i, v in enumerate(vals):
        bx.text(i, v + 60, f"{v:.0f} rpm\n{100 * (v / 3000 - 1):.1f} %", ha="center", fontsize=8, color=TEXT)
    bx.axhspan(0, 3450, color=GRID, alpha=0.6, lw=0, zorder=0)
    bx.axhline(3450, color=TEXT, lw=1, ls=(0, (4, 3)))
    bx.axhline(3000, color=TEXT_2, lw=0.8, ls=":")
    bx.text(-0.42, 5250, "dashed: REQ-G1, 3450 rpm (15 % over)\ndotted: top speed, 3000 rpm", ha="left",
            va="top", fontsize=8, color=TEXT_2)
    bx.set_xticks(np.arange(3), labels, fontsize=8.5)
    bx.set_ylim(0, 5300)
    bx.set_ylabel("first forward critical speed (rpm)")
    bx.set_title("(b) Corrected critical speed, 65 mm shaft", loc="left", fontsize=10, color=TEXT)
    fig.suptitle("The beam model gets the hub backwards; the 65 mm shaft still clears the range by 23 %", x=0.01,
                 ha="left", fontsize=11.5, color=TEXT)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    print(out)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "portfolio" / "img" / "rotor_solid.png")

"""Study 28 part 2 portfolio figure: what the knee's bolts do to the frame, from run 20261127-105635_steel_frame_knee.

(a) The beam's moment under gravity + lateral load with rigid knees, slip-critical knees (the measured spring) and
    bearing-type knees that slip 1/16 in. per flange: the slip moves moment from the knees to the unbraced midspan.
    Each curve is the quadratic through the run's nine eighth-point moments (a uniform load: exact).
(b) Each scenario's largest member ratio (H1-1) and connection ratio against the limit 1.0.

    .venv/Scripts/python.exe scripts/make_steel_knee_figure.py [out.png]
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

RUN = ROOT / "runs" / "20261127-105635_steel_frame_knee"
SCEN = [("p00_rigid_sc6", "rigid knees (part 1's analysis)", TEXT_2, (0, (4, 3))),
        ("p01_sc6", "slip-critical bolts: measured knee spring", SERIES_1, "-"),
        ("p03_bearing4_half_slip", "bearing bolts, half the slip", "#c9a227", "-"),
        ("p02_bearing4_slip", "bearing bolts, 1/16 in. slip per flange", SERIES_2, "-")]


def beam_moments(label: str) -> tuple[np.ndarray, np.ndarray]:
    with open(RUN / "points" / label / "moment_diagrams.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    s = np.array([float(r["position_along_member"]) for r in rows])
    m = np.array([float(r["M_kNm_gravity_lateral_beam"]) for r in rows])
    return s, m


def main(out: Path) -> None:
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1.45, 1]})
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    xs = np.linspace(0, 1, 121)
    for label, name, color, ls in SCEN:
        s, m = beam_moments(label)
        coef = np.polyfit(s, m, 2)
        assert np.max(np.abs(np.polyval(coef, s) - m)) < 0.05, label      # the quadratic passes through the run's
        ax.plot(6 * xs, np.polyval(coef, xs), color=color, ls=ls, lw=2, label=name)
        ax.plot(6 * s, m, "o", color=color, ms=4, mec=SURFACE, mew=0.8)
    pts = {lab: json.loads((RUN / "points" / lab / "point.json").read_text(encoding="utf-8")) for lab, *_ in SCEN}
    for lab, txt, dy, va in (("p00_rigid_sc6", "rigid knees", -2, "top"), ("p02_bearing4_slip", "slipping knees", 2,
                                                                                    "bottom")):
        b = pts[lab]["solver_outputs"]["member_checks"]["gravity_lateral"]["beam"]
        ax.axhline(-b["phiMn_kNm"], color=TEXT_2, lw=0.9, ls=":")
        ax.text(0.05, -b["phiMn_kNm"] + dy, f"φMn {b['phiMn_kNm']:.0f} kN m, {txt} (Cb {b['Cb']:.2f})", ha="left",
                va=va, fontsize=8, color=TEXT_2)
    ax.axhline(0, color=GRID, lw=1)
    ax.set_xlabel("along the beam (m), windward knee at 0")
    ax.set_ylabel("beam moment (kN m), hogging +")
    ax.set_ylim(-150, 100)
    ax.set_title("(a) Beam moment, gravity + lateral (factored)", loc="left", fontsize=10, color=TEXT)
    ax.legend(loc="upper center", frameon=False, fontsize=8, ncol=2, bbox_to_anchor=(0.5, -0.17))

    _style(bx)
    names = ["rigid", "slip-critical", "bearing,\nhalf slip", "bearing,\nfull slip"]
    h1 = [pts[lab]["metrics"]["max_interaction_ratio"] for lab, *_ in SCEN]
    cn = [pts[lab]["metrics"]["max_connection_ratio"] for lab, *_ in SCEN]
    x = np.arange(len(names))
    bx.bar(x - 0.19, h1, 0.36, color=[c for _, _, c, _ in SCEN], label="frame: largest member ratio (H1-1)")
    bx.bar(x + 0.19, cn, 0.36, color=[c for _, _, c, _ in SCEN], alpha=0.45, hatch="//", edgecolor=SURFACE,
           label="knee connection: largest Chapter J ratio")
    for xi, v in zip(x, h1):
        bx.text(xi - 0.19, v + 0.02, f"{v:.2f}", ha="center", fontsize=8, color=TEXT)
    for xi, v in zip(x, cn):
        bx.text(xi + 0.19, v + 0.02, f"{v:.2f}", ha="center", fontsize=8, color=TEXT_2)
    bx.axhline(1.0, color=TEXT, lw=1, ls=(0, (4, 3)))
    bx.axhspan(1.0, 1.35, color=GRID, alpha=0.6, lw=0, zorder=0)
    bx.text(-0.45, 1.3, "fails above 1.0", va="top", fontsize=8, color=TEXT_2)
    bx.set_xticks(x, names, fontsize=8.5)
    bx.set_ylim(0, 1.35)
    bx.set_title("(b) Ratios against the limit", loc="left", fontsize=10, color=TEXT)
    bx.legend(loc="upper center", frameon=False, fontsize=8, bbox_to_anchor=(0.5, -0.17))
    fig.suptitle("The knee's bolts decide the frame: slip-critical keeps the verdict, slipping bolts fail the beam",
                 x=0.01, ha="left", fontsize=11.5, color=TEXT)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    print(out)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "portfolio" / "img" / "steel_knee_frame.png")

"""Study 2 part 2 portfolio figure, from runs 20261127-151911_strap_3d_mesh, 20261127-152203_strap_3d_size and study
2's 20261119-235211_strap_hole_size.

(a) The hole-edge stress through the thickness at the 16 mm hole (finest mesh), against plane stress and the 120 MPa
    allowable.
(b) The peak against hole size: plane stress (study 2) and 3D mid-thickness, with the largest hole each allows.

    .venv/Scripts/python.exe scripts/make_strap_3d_figure.py [out.png]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2, _style, plt  # noqa: E402

MESH = ROOT / "runs" / "20261127-151911_strap_3d_mesh"
SIZE = ROOT / "runs" / "20261127-152203_strap_3d_size"
PLANE = ROOT / "runs" / "20261119-235211_strap_hole_size"
ALLOW = 120.0


def _points(run: Path) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((run / "points").glob("*/point.json"))]


def _limit(d, s):
    i = int(np.searchsorted(s, ALLOW))
    return d[i - 1] + (d[i] - d[i - 1]) * (ALLOW - s[i - 1]) / (s[i] - s[i - 1])


def main(out: Path) -> None:
    fine = next(p for p in _points(MESH) if p["label"].startswith("p02"))
    o = fine["solver_outputs"]
    z, s = np.asarray(o["profile_z_mm"]), np.asarray(o["profile_sxx_MPa"])
    ps = float(fine["parameters"]["plane_stress_peak_MPa"])
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(11.5, 4.3), gridspec_kw={"width_ratios": [1, 1.25]})
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    zz = np.concatenate([-z[::-1], z[1:]])       # both halves of the thickness (the model is the upper half)
    sz = np.concatenate([s[::-1], s[1:]])
    ax.plot(sz, zz, "o-", color=SERIES_1, ms=3, lw=1.6, label="3D: hole edge through the 4 mm")
    ax.axvline(ps, color=SERIES_2, lw=1.3, ls="--", label=f"plane stress (study 2): {ps:.1f}")
    ax.axvline(ALLOW, color=TEXT, lw=0.9, ls=":", label=f"allowable {ALLOW:.0f}")
    ax.annotate(f"mid-thickness {s[0]:.1f} MPa\n(+{100 * (s[0] / ps - 1):.1f} %)", (s[0], 0), xytext=(s[0] - 4.2, 0.6),
                fontsize=8, color=SERIES_1, arrowprops={"arrowstyle": "-", "color": SERIES_1, "lw": 0.7})
    ax.annotate(f"faces {s[-1]:.1f}", (s[-1], z[-1]), xytext=(113.1, z[-1] - 0.25), fontsize=8,
                color=SERIES_1, ha="left", va="center")
    ax.set_xlim(113, 121)
    ax.set_ylim(-2.15, 2.15)
    ax.set_xlabel("stress at the hole edge (MPa)")
    ax.set_ylabel("through the thickness (mm)")
    ax.set_title("(a) 16 mm hole: the stress is not uniform through t", loc="left", fontsize=10, color=TEXT)
    ax.legend(frameon=False, fontsize=7.5, loc="center left")

    _style(bx)
    p2 = sorted(_points(PLANE), key=lambda p: float(p["parameters"]["hole_diameter_mm"]))
    d2 = np.array([float(p["parameters"]["hole_diameter_mm"]) for p in p2])
    s2 = np.array([p["metrics"]["peak_hole_stress_MPa"] for p in p2])
    p3 = sorted(_points(SIZE), key=lambda p: float(p["parameters"]["hole_diameter_mm"]))
    d3 = np.array([float(p["parameters"]["hole_diameter_mm"]) for p in p3])
    s3 = np.array([p["metrics"]["peak_hole_stress_MPa"] for p in p3])
    bx.plot(d2, s2, "s--", color=SERIES_2, ms=4, lw=1.2, label="plane stress (study 2)")
    bx.plot(d3, s3, "o-", color=SERIES_1, ms=5, lw=1.6, label="3D, mid-thickness (this part)")
    bx.axhline(ALLOW, color=TEXT, lw=0.9, ls=":")
    for d_, s_, col, lab, xy in ((d2, s2, SERIES_2, "plane stress", (16.95, 108.5)), (d3, s3, SERIES_1, "3D",
                                                                                      (10.2, 123.0))):
        dl = _limit(d_, s_)
        bx.plot([dl], [ALLOW], "o", color=col, mfc=SURFACE, ms=7)
        bx.annotate(f"{lab}: largest hole {dl:.1f} mm", (dl, ALLOW), xytext=xy, fontsize=8, color=col,
                    ha="right" if xy[0] > dl else "left",
                    arrowprops={"arrowstyle": "-", "color": col, "lw": 0.7})
    bx.set_xlabel("cable hole diameter (mm)")
    bx.set_ylabel("peak stress at the hole edge (MPa)")
    bx.set_title("(b) The largest hole moves from 16.7 to 16.3 mm", loc="left", fontsize=10, color=TEXT)
    bx.legend(frameon=False, fontsize=8, loc="upper left")
    bx.text(0.99, 0.02, "16 mm passes either way: 117.0 / 118.8 MPa", transform=bx.transAxes, fontsize=8,
            color=TEXT_2, ha="right")
    fig.tight_layout()
    fig.savefig(out, dpi=150, facecolor=SURFACE)
    plt.close(fig)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "portfolio" / "img" / "strap_3d.png")

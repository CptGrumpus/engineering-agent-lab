"""Study 18 page figure, from the committed runs: the governing classification line and the thickness sweep.

  (a) von Mises stress through the shell wall on the governing line (shell side of the junction, plane along the
      vessel), finest mesh: the FE profile, its linearised (membrane plus bending) distribution and the membrane PL,
      against the PL limit 1.5 S.
  (b) PL against nozzle wall thickness, with the limit, where it is reached, and the simplified rule's thickness.

    .venv/Scripts/python.exe scripts/make_pv_figure.py [out.png]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harness.linearize import von_mises  # noqa: E402
from harness.plotting import GRID, SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2, _style, plt  # noqa: E402

MESH = ROOT / "runs/20261122-102842_pv_nozzle_mesh/points/p02_element_size_local_mm-2.6667/point.json"
SWEEP = ROOT / "runs/20261122-103521_pv_nozzle_thickness"
LIMIT = 207.0
BOX = dict(facecolor=SURFACE, edgecolor="none", pad=1.5)


def main(out: Path) -> None:
    pt = json.loads(MESH.read_text(encoding="utf-8"))
    line = pt["solver_outputs"]["lines"]["shell_long"]
    prof = pt["solver_outputs"]["profiles"]["shell_long"]
    s, vm = np.asarray(prof["s_mm"]), np.asarray(prof["vm_MPa"])
    t = line["thickness"]
    m, b = np.asarray(line["membrane"]), np.asarray(line["bending"])
    lin = von_mises(m[None, :] + b[None, :] * (1 - 2 * s[:, None] / t))
    assert abs(lin[0] - von_mises(np.asarray(line["at_start"]))) < 1e-9 * lin[0]
    pl = line["membrane_vm"]
    assert abs(pl / pt["metrics"]["pl_shell_long_MPa"] - 1) < 1e-12

    sweep = []
    for pj in sorted((SWEEP / "points").glob("*/point.json")):
        q = json.loads(pj.read_text(encoding="utf-8"))
        sweep.append((q["parameters"]["nozzle_thickness_mm"], q["metrics"]["pl_max_MPa"]))
    tn, plt_ = np.array(sweep).T
    order = np.argsort(tn)
    tn, plt_ = tn[order], plt_[order]
    k = np.searchsorted(-plt_, -LIMIT)                 # first thickness at or under the limit
    t_req = tn[k - 1] + (LIMIT - plt_[k - 1]) * (tn[k] - tn[k - 1]) / (plt_[k] - plt_[k - 1])

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2), gridspec_kw={"width_ratios": [1.1, 1]})
    fig.patch.set_facecolor(SURFACE)

    ax = axes[0]
    _style(ax)
    ax.plot(s, vm, color=SERIES_1, lw=2, label="FE stress through the wall")
    ax.plot(s, lin, color=SERIES_2, lw=2, ls=(0, (5, 3)), label="linearised: membrane plus bending")
    ax.axhline(pl, color=SERIES_2, lw=2)
    ax.text(0.3, pl - 2, f"PL, the membrane: {pl:.1f} MPa", color=TEXT, fontsize=9, va="top")
    ax.axhline(LIMIT, color=TEXT_2, lw=1, ls=(0, (4, 3)))
    ax.text(11, LIMIT + 1.2, "PL limit 207 MPa", color=TEXT_2, fontsize=8, ha="center", va="bottom", bbox=BOX)
    ax.set_xlim(-0.3, 16.3)
    ax.set_ylim(180, 255)
    ax.set_xlabel("through the shell wall, inside to outside (mm)")
    ax.set_ylabel("von Mises stress (MPa)")
    ax.set_title("(a) The governing line, 12 mm nozzle", loc="left", fontsize=10, color=TEXT)
    ax.legend(frameon=False, fontsize=8, loc="upper center")

    ax = axes[1]
    _style(ax)
    ax.axhline(LIMIT, color=TEXT_2, lw=1, ls=(0, (4, 3)))
    ax.text(7.4, LIMIT + 1.2, "limit 207 MPa", color=TEXT_2, fontsize=8, ha="left", va="bottom", bbox=BOX)
    ax.plot(tn, plt_, color=SERIES_1, lw=2, zorder=2)
    ok = plt_ <= LIMIT
    ax.scatter(tn[ok], plt_[ok], s=60, color=SERIES_1, edgecolor=SERIES_1, linewidth=2, zorder=3, label="passes")
    ax.scatter(tn[~ok], plt_[~ok], s=60, color=SURFACE, edgecolor=SERIES_1, linewidth=2, zorder=3, label="fails")
    for x, y in zip(tn, plt_):
        ax.annotate(f"{y:.1f}", (x, y), textcoords="offset points", xytext=(8, 4 if y > LIMIT else -12), fontsize=8,
                    color=TEXT_2)
    ax.axvline(t_req, color=GRID, lw=1.2)
    ax.text(t_req - 0.15, 211, f"analysis: {t_req:.1f} mm", rotation=90, fontsize=8, color=TEXT_2, ha="right", va="bottom", bbox=BOX)
    ax.axvline(16, color=GRID, lw=1.2)
    ax.text(15.85, 186, "simplified rule: about 16 mm", rotation=90, fontsize=8, color=TEXT_2, ha="right", va="bottom", bbox=BOX)
    ax.set_xlim(7.2, 16.8)
    ax.set_ylim(178, 245)
    ax.set_xlabel("nozzle wall thickness (mm)")
    ax.set_ylabel("PL, local membrane stress (MPa)")
    ax.set_title("(b) PL against the nozzle wall", loc="left", fontsize=10, color=TEXT)
    ax.legend(frameon=False, fontsize=8, loc="upper right")

    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, facecolor=SURFACE)
    print(out, f"PL {pl:.2f} MPa; limit reached at {t_req:.2f} mm")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "site/v2/pv_nozzle_response.png")

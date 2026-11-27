"""Study 26 part 2 portfolio figure: fatigue and overload yield safety against the gear seat's diameter, from the runs.

Three series on each panel, with the requirement's limit and its failing side shaded:
  - no keyway (part 1: the shoulder fillet alone, run 20261124-155125_shaft_fillet_size);
  - DIN 6885 keyway, bottom corner 0.40 mm (36 mm: run 20261127-010741 base mesh; 38, 40 mm: design_r1);
  - the same keyway at the bottom of its corner tolerance, 0.25 mm (36, 40, 42 mm: design_r1).
Every keyed point is at mesh scale 0.8 and its governing location is the keyway.

    .venv/Scripts/python.exe scripts/make_keyed_shaft_figure.py [out.png]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from harness.plotting import GRID, SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2, _style, plt  # noqa: E402

PART1 = "20261124-155125_shaft_fillet_size"
NOISE_BASE = ("20261127-010741_keyed_shaft_noise", "p02_far4.0")
DESIGN = "20261127-021152_keyed_shaft_design_r1"
LIMITS = {"fatigue_safety": 1.5, "static_safety": 2.0}


def point(run: str, label: str) -> dict:
    return json.loads((ROOT / "runs" / run / "points" / label / "point.json").read_text(encoding="utf-8"))


def series() -> dict[str, list[dict]]:
    p1 = [json.loads(f.read_text(encoding="utf-8"))
          for f in sorted((ROOT / "runs" / PART1 / "points").glob("*/point.json"))]
    r040 = [point(*NOISE_BASE), point(DESIGN, "p01_d38"), point(DESIGN, "p02_d40")]
    r025 = [point(DESIGN, "p00_rk025"), point(DESIGN, "p03_d40_rk025"), point(DESIGN, "p04_d42_rk025")]
    for p in r040 + r025:
        assert p["metrics"]["fatigue_safety"] == p["metrics"]["fatigue_safety_key"], p["label"]  # keyway governs
    return {"no keyway (part 1: shoulder fillet)": p1, "keyway, corner r 0.40 mm": r040,
            "keyway, corner r 0.25 mm (DIN lower tolerance)": r025}


def main(out: Path) -> None:
    S = series()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
    fig.patch.set_facecolor(SURFACE)
    looks = [(TEXT_2, "o", (0, (4, 3))), (SERIES_1, "o", "-"), (SERIES_2, "D", "-")]
    for ax, (metric, title) in zip(axes, [("fatigue_safety", "Fatigue safety (REQ-S1, modified Goodman)"),
                                          ("static_safety", "Yield safety at 1.5 x overload (REQ-S2)")]):
        _style(ax)
        lim = LIMITS[metric]
        for (name, pts), (c, mk, ls) in zip(S.items(), looks):
            pts = sorted(pts, key=lambda p: p["parameters"]["d_mm"])
            x = [p["parameters"]["d_mm"] for p in pts]
            y = [p["metrics"][metric] for p in pts]
            ax.plot(x, y, color=c, ls=ls, lw=2, marker=mk, ms=7, mfc=c, mec=SURFACE, mew=1.2, label=name, zorder=3)
            if metric == "fatigue_safety" and ls == "-":
                for xi, yi in zip(x, y):
                    ax.annotate(f"{yi:.3f}", (xi, yi), textcoords="offset points", xytext=(7, -4), fontsize=8,
                                color=TEXT_2)
        ax.set_xlim(31.5, 42.8)
        y0, y1 = ax.get_ylim()
        ax.axhspan(min(y0, lim - 0.1), lim, color=GRID, alpha=0.6, zorder=0, lw=0)
        ax.axhline(lim, color=TEXT, lw=1, ls=(0, (4, 3)))
        ax.text(31.7, lim, f" limit {lim:g}: fails below", va="bottom", fontsize=8, color=TEXT_2)
        ax.set_ylim(min(y0, lim - 0.1), y1)
        ax.set_xlabel("gear seat diameter d (mm); shoulder D = 1.25 d")
        ax.set_title(title, loc="left", fontsize=10, color=TEXT)
    axes[0].legend(loc="upper left", frameon=False, fontsize=8)
    fig.suptitle("The keyway, not the fillet, sizes the seat: 36 mm fails; 40 mm passes at r 0.40, 42 mm at r 0.25",
                 x=0.01, ha="left", fontsize=11.5, color=TEXT)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    print(out)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "portfolio" / "img" / "keyed_shaft_seat.png")

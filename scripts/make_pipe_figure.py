"""Study 19 portfolio figure: friction factor against Prandtl's smooth-pipe law, from the committed runs.

Three panels on one percent scale (deviation from Prandtl), with REQ-T1's +-5 % band:
  (a) the low-Reynolds mesh study (f against 1/n_radial, with the Richardson-extrapolated value),
  (b) both wall treatments across Reynolds numbers,
  (c) wall functions against the first-cell y+ at Re 2e6.

    .venv/Scripts/python.exe scripts/make_pipe_figure.py [out.png]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from matplotlib.ticker import NullFormatter, ScalarFormatter  # noqa: E402

from harness.plotting import GRID, SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2, _style, plt  # noqa: E402

RUNS = {
    "mesh": "20261122-104218_pipe_rans_mesh",
    "reynolds": "20261122-104744_pipe_rans_reynolds",
    "wf_yplus": "20261122-140211_pipe_rans_wf_yplus",
}


def points(run: str) -> list[dict]:
    out = []
    for pj in sorted((ROOT / "runs" / run / "points").glob("*/point.json")):
        pt = json.loads(pj.read_text(encoding="utf-8"))
        if pt.get("status") == "completed":
            out.append(pt)
    return out


def latest(case: str) -> str | None:
    runs = sorted(p.name for p in (ROOT / "runs").glob(f"*_{case}") if (p / "report.md").exists())
    return runs[-1] if runs else None


def band(ax):
    for y in (-5, 5):
        ax.axhline(y, color=TEXT_2, lw=1, ls=(0, (4, 3)))
    ax.axhline(0, color=GRID, lw=1.2)
    ax.text(ax.get_xlim()[1], 5, "REQ-T1 limit  ", ha="right", va="bottom", fontsize=8, color=TEXT_2)


def main(out: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), sharey=True)
    fig.patch.set_facecolor(SURFACE)

    # (a) low-Re mesh study: first run and revision, f against 1/n
    ax = axes[0]
    # r1 is left out: its finest mesh never converged (the axial-length rule stalled SIMPLE); r2 is the revision of record
    r2 = latest("pipe_rans_mesh_r2")
    series = [(RUNS["mesh"], "first study (40 / 80 / 160)", "o")]
    if r2:
        series.append((r2, "revision 2 (80 / 160 / 320)", "s"))
    for run, label, marker in series:
        pts = sorted(points(run), key=lambda p: p["parameters"]["n_radial"])
        x = [1 / p["parameters"]["n_radial"] for p in pts]
        y = [p["metrics"]["friction_dev_prandtl_pct"] for p in pts]
        ax.plot(x, y, color=SERIES_1, lw=2, marker=marker, ms=8, mfc=SERIES_1 if marker == "o" else SURFACE,
                mec=SERIES_1, mew=2, label=label)
        for xi, yi, p in zip(x, y, pts):
            ax.annotate(f"{p['parameters']['n_radial']}", (xi, yi), textcoords="offset points", xytext=(6, -12),
                        fontsize=8, color=TEXT_2)
    # the latest study's Richardson extrapolation, at 1/n = 0, with its GCI as an error bar
    v = json.loads((ROOT / "runs" / series[-1][0] / "verification.json").read_text(encoding="utf-8"))
    u = v.get("run_check_detail", {}).get("friction_factor", {})
    if u.get("extrapolated"):
        m = points(series[-1][0])[0]["metrics"]  # Prandtl at the wedge's hydraulic Reynolds number, as the metrics use
        pr = m["friction_factor"] / (1 + m["friction_dev_prandtl_pct"] / 100)
        ye = 100 * (u["extrapolated"] / pr - 1)
        ax.errorbar([0.0004], [ye], yerr=[100 * u["uncertainty"] * u["extrapolated"] / pr], color=TEXT, marker="*",
                    ms=11, capsize=4, lw=1.2, ls="none", label=f"extrapolated ({ye:+.1f} %, GCI {100 * u['uncertainty']:.1f} %)")
    ax.set_xlim(0, 0.028)
    ax.set_xlabel("1 / radial cells")
    ax.set_ylabel("friction factor vs Prandtl (%)")
    ax.set_title("(a) Low-Re SST, Re 1e5: mesh study", fontsize=10, color=TEXT, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="lower left")

    # (b) across Reynolds numbers
    ax = axes[1]
    pts = points(RUNS["reynolds"])
    for treat, color, label in (("low_re", SERIES_1, "resolved sublayer (y+ < 1)"),
                                ("wall_function", SERIES_2, "wall functions (y+ 46-79)")):
        sel = sorted((p for p in pts if p["parameters"]["wall_treatment"] == treat),
                     key=lambda p: p["parameters"]["reynolds_number"])
        ax.plot([p["parameters"]["reynolds_number"] for p in sel], [p["metrics"]["friction_dev_prandtl_pct"] for p in sel],
                color=color, lw=2, marker="o" if treat == "low_re" else "D", ms=8, label=label)
    ax.set_xscale("log")
    ax.set_xlim(1e4, 4e6)
    ax.set_xlabel("Reynolds number")
    ax.set_title("(b) Across Reynolds numbers (coarse meshes)", fontsize=10, color=TEXT, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="upper right", bbox_to_anchor=(1, 0.74))

    # (c) wall functions: first-cell placement at Re 2e6
    ax = axes[2]
    pts = sorted(points(RUNS["wf_yplus"]), key=lambda p: p["metrics"]["yplus_first_cell"])
    ax.plot([p["metrics"]["yplus_first_cell"] for p in pts], [p["metrics"]["friction_dev_prandtl_pct"] for p in pts],
            color=SERIES_2, lw=2, marker="D", ms=8, label="wall functions, 80 cells")
    ax.set_xscale("log")
    ax.set_xlim(20, 300)
    ax.set_xticks([30, 50, 100, 200])
    ax.xaxis.set_major_formatter(ScalarFormatter())
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel("first-cell y+ (cell centre)")
    ax.set_title("(c) Wall functions, Re 2e6: where the wall cell sits", fontsize=10, color=TEXT, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="upper right", bbox_to_anchor=(1, 0.74))

    for ax in axes:
        _style(ax)
        ax.set_ylim(-7, 7)
        band(ax)
    fig.suptitle("Turbulent pipe friction (k-omega SST) against Prandtl's smooth-pipe law", fontsize=11, color=TEXT)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=130, facecolor=SURFACE)
    plt.close(fig)
    print(out)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "portfolio" / "img" / "pipe_friction.png")

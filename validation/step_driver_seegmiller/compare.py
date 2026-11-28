"""Study 19 part 2: score the step model against Driver and Seegmiller's measurements (ERCOFTAC classic case 030,
alpha 0), once, with the limits agreed before the data was opened (PROTOCOL.md):
  REQ-S1  reattachment length Xr/H within 10 % of measured (Table 1, laser oil-flow interferometry)
  REQ-S2  Cf on the step-side wall over 10 <= x/H <= 30 within 15 % rms of measured (Table 3, at its stations)
  REQ-S3  pressure recovery Cp(30 H) - Cp(-4 H) within 0.02 of measured (Table 2, step-side wall, alpha 0)

usage: .venv/Scripts/python.exe validation/step_driver_seegmiller/compare.py RUN_ID POINT_LABEL [--data DIR]
       [--out DIR] [--title TEXT]
Writes comparison.json, comparison.png and RESULTS.md beside this file (or in --out: part 3's 3D model, whose point
files carry the same keys at mid-span). The data stays outside the repo (DIR, default ~/data/ercoftac_case030/files);
only the values compared are copied into the results.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
LIMITS = {"REQ-S1": 0.10, "REQ-S2": 0.15, "REQ-S3": 0.02}


def _rows(path: Path):
    for ln in path.read_text(encoding="latin-1").splitlines():
        if ln.strip() and not ln.lstrip().startswith("#"):
            yield ln.split()


def measured_xr(d: Path) -> tuple[float, float]:
    for r in _rows(d / "bkst-reattach.dat"):
        if len(r) >= 3 and float(r[0]) == 0.0:
            return float(r[1]), float(r[2].replace("+-", "").strip() or "nan") if r[2] != "+-" else float(r[3])
    raise ValueError("alpha 0 not in bkst-reattach.dat")


def measured_cf(d: Path) -> np.ndarray:
    """Table 3, alpha 0: rows (x/H, Cf, relative uncertainty) up to the next alpha block."""
    out, on = [], False
    for ln in (d / "bkst-tauw.dat").read_text(encoding="latin-1").splitlines():
        s = ln.strip()
        if s.startswith("#") and "Alpha" in s:
            on = "= 0 " in s + " " or s.rstrip().endswith("= 0 degrees")
            continue
        if on and s and not s.startswith("#"):
            out.append([float(v) for v in s.split()[:3]])
    return np.array(out)


def measured_cp(d: Path) -> np.ndarray:
    """Table 2, the step-side wall, the alpha 0 column (x/H, Cp); '--' entries dropped. Stops at the next table."""
    out, started = [], False
    for ln in (d / "bkst-cp.dat").read_text(encoding="latin-1").splitlines():
        s = ln.strip()
        if s.startswith("#"):
            if started:
                break
            continue
        if not s:
            continue
        r = s.split()
        started = True
        if len(r) >= 3 and r[2] != "--":
            out.append([float(r[0]), float(r[2])])
    return np.array(out)


def ours(run_id: str, label: str) -> dict:
    pdir = REPO / "runs" / run_id / "points" / label
    pt = json.loads((pdir / "point.json").read_text(encoding="utf-8"))
    o = pt["solver_outputs"]
    with open(pdir / "wall.csv", newline="", encoding="utf-8") as f:
        rows = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(f)]
    return {"xr_over_h": o["xr_over_h"], "x_cf": np.array([r["x_over_h"] for r in rows]),
            "cf": np.array([r["cf"] for r in rows]), "x_cp": np.array(o["profiles"]["x_p_over_h"]),
            "cp": np.array(o["profiles"]["cp"]), "x_up": np.array(o["profiles"]["x_up_over_h"]),
            "cf_up": np.array(o["profiles"]["cf_up"]), "inflow": o["inflow"], "label": label, "run": run_id}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_id")
    ap.add_argument("label")
    ap.add_argument("--data", default=str(Path.home() / "data" / "ercoftac_case030" / "files"))
    ap.add_argument("--out", default=str(HERE))
    ap.add_argument("--title", default="Study 19 part 2: the step against Driver and Seegmiller (alpha 0)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    d = Path(a.data)
    m = ours(a.run_id, a.label)
    xr_meas, xr_unc = measured_xr(d)
    cf = measured_cf(d)
    cp = measured_cp(d)
    # REQ-S1
    s1 = m["xr_over_h"] / xr_meas - 1
    # REQ-S2 at the measured stations in 10..30
    sel = (cf[:, 0] >= 10) & (cf[:, 0] <= 30)
    cf_ours = np.interp(cf[sel, 0], m["x_cf"], m["cf"])
    rel = cf_ours / cf[sel, 1] - 1
    s2 = float(math.sqrt(np.mean(rel ** 2)))
    # REQ-S3: recovery from -4 H to 30 H (the measured table interpolated at both ends; ours referred to -4 H already)
    cp_meas = float(np.interp(30.0, cp[:, 0], cp[:, 1]) - np.interp(-4.0, cp[:, 0], cp[:, 1]))
    cp_ours = float(np.interp(30.0, m["x_cp"], m["cp"]) - np.interp(-4.0, m["x_cp"], m["cp"]))
    s3 = cp_ours - cp_meas
    res = {"run": a.run_id, "point": a.label,
           "REQ-S1": {"ours": m["xr_over_h"], "measured": xr_meas, "measured_uncertainty": xr_unc, "rel_error": s1,
                      "limit": LIMITS["REQ-S1"], "pass": abs(s1) <= LIMITS["REQ-S1"]},
           "REQ-S2": {"stations_x_over_h": cf[sel, 0].tolist(), "measured": cf[sel, 1].tolist(),
                      "measured_rel_uncertainty": cf[sel, 2].tolist(), "ours": cf_ours.tolist(),
                      "rel_error": rel.tolist(), "rms_rel_error": s2, "limit": LIMITS["REQ-S2"],
                      "pass": s2 <= LIMITS["REQ-S2"]},
           "REQ-S3": {"ours": cp_ours, "measured": cp_meas, "difference": s3, "limit": LIMITS["REQ-S3"],
                      "pass": abs(s3) <= LIMITS["REQ-S3"]},
           "upstream_cf_at_minus4h": {"ours": float(np.interp(-3.956, m["x_up"], m["cf_up"])),
                                      "measured": float(cf[np.argmin(np.abs(cf[:, 0] + 3.956)), 1])}}
    (out / "comparison.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    figure(m, cf, cp, res, out)
    v = lambda ok: "PASS" if ok else "FAIL"  # noqa: E731
    md = [f"# {a.title}\n",
          f"Model: run `{a.run_id}`, point `{a.label}`. Limits agreed before the data was opened (PROTOCOL.md).\n",
          "| Requirement | Ours | Measured | Error | Limit | Verdict |", "|---|---|---|---|---|---|",
          f"| REQ-S1 reattachment Xr/H | {m['xr_over_h']:.3f} | {xr_meas:.2f} +- {xr_unc:.2f} | {100 * s1:+.1f} % | 10 % | **{v(res['REQ-S1']['pass'])}** |",
          f"| REQ-S2 Cf, 10 <= x/H <= 30 ({int(sel.sum())} stations) | | | rms {100 * s2:.1f} % | 15 % | **{v(res['REQ-S2']['pass'])}** |",
          f"| REQ-S3 Cp(30 H) - Cp(-4 H) | {cp_ours:.4f} | {cp_meas:.4f} | {s3:+.4f} | 0.02 | **{v(res['REQ-S3']['pass'])}** |",
          "", "Cf at the stations (ours / measured, relative error):", ""]
    md += [f"- x/H {x:.2f}: {o_:.5f} / {c:.5f} ({100 * e:+.1f} %)" for x, o_, c, e in
           zip(cf[sel, 0], cf_ours, cf[sel, 1], rel)]
    md += ["", "![comparison](comparison.png)", ""]
    (out / "RESULTS.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md[:8]))


def figure(m, cf, cp, res, out=HERE):
    import sys

    sys.path.insert(0, str(REPO))
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, _style, plt

    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    fig.patch.set_facecolor(SURFACE)
    a = ax[0]
    a.plot(np.concatenate([m["x_up"], m["x_cf"]]), np.concatenate([m["cf_up"], m["cf"]]) * 1e3, "-", color=SERIES_1,
           lw=1.5, label="k-omega SST (ours)")
    a.errorbar(cf[:, 0], cf[:, 1] * 1e3, yerr=np.abs(cf[:, 1] * cf[:, 2]) * 1e3, fmt="o", ms=4, color=SERIES_2,
               label="Driver & Seegmiller")
    a.axhline(0, color=TEXT, lw=0.6)
    a.axvspan(10, 30, color=TEXT, alpha=0.06)
    a.set_xlim(-5, 36)
    a.set_xlabel("x / H")
    a.set_ylabel("C_f x 1000")
    a.legend(frameon=False, fontsize=8)
    _style(a)
    a = ax[1]
    a.plot(m["x_cp"], m["cp"], "-", color=SERIES_1, lw=1.5, label="ours (from x = -4 H)")
    a.plot(cp[:, 0], cp[:, 1] - np.interp(-4.0, cp[:, 0], cp[:, 1]), "o", ms=4, color=SERIES_2,
           label="measured (shifted to x = -4 H)")
    a.set_xlim(-5, 36)
    a.set_xlabel("x / H")
    a.set_ylabel("C_p - C_p(-4 H)")
    a.legend(frameon=False, fontsize=8)
    _style(a)
    fig.suptitle(f"Backward-facing step: Xr/H {res['REQ-S1']['ours']:.2f} against {res['REQ-S1']['measured']:.2f} "
                 f"measured", fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(Path(out) / "comparison.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    main()

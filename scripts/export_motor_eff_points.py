"""The motor's efficiency against ORNL point by point, for the site figure.

    .venv\\Scripts\\python.exe scripts\\export_motor_eff_points.py

The study's scoring (scripts/motor_rev5_vs_ornl.py, through motor_calibration.efficiency()) saves only the summary:
median, p10-p90 and the count within 2 points. This repeats that function's loop line for line on the same case and
tables, keeping each point, and refuses to write anything unless the summary it gets back equals the recorded one in
validation/motor_ornl/rev5_efficiency_vs_ornl.json. So the figure shows the scored comparison, not a new one.

Writes build/drawings/motor_eff_vs_ornl.json. Python only: reads the saved dq tables, runs no FEMM.
"""
from __future__ import annotations

import json
import math
import sys
import tomllib
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import motor_calibration as mc  # noqa: E402
from motor_rev5_vs_ornl import CASE, OUT as SCORED  # noqa: E402

OUT = REPO / "build" / "drawings" / "motor_eff_vs_ornl.json"


def main():
    case = tomllib.loads(CASE.read_text(encoding="utf-8"))
    tab = mc.tables(case)
    fine = {n: t["fine"] for n, t in tab.items()}
    grids = {n: t["grid"] for n, t in tab.items()}
    # mc.efficiency(case, fine, 1.0, grids), keeping the points
    p = dict(case["parameters"])
    r20 = mc.phase_resistance_20C(p) * 1.0
    vmax = float(p["bus_voltage_V"]) / math.sqrt(6)
    d = []
    for r in mc.read_csv(mc.V / "tm2006_423_table_b1.csv"):
        n, T = r["speed"], r["torque"]
        if not (float(p["speed_min_rpm"]) <= n <= float(p["speed_max_rpm"]) and T >= float(p["torque_min_Nm"])):
            continue
        rec = {"speed_rpm": n, "torque_Nm": T, "ornl_pct": 100 * r["eff_motor"]}
        for name, f in fine.items():
            wt = 20.0 if name == "cold" else 100.0
            o = mc.em.operating_points(f, speed_rpm=n, torques_Nm=[T], pole_pairs=grids[name]["pole_pairs"],
                                       r_ohm=mc.em.resistance(r20, wt, float(p["copper_alpha_per_K"])), v_max_rms=vmax,
                                       i_max_rms=float(p["current_limit_map_A"]))
            rec[name] = float(o["efficiency_pct"][0])
        d.append(rec)
    ok = [x for x in d if np.isfinite(x["cold"]) and np.isfinite(x["hot"])]
    gap = np.array([x["hot"] - x["ornl_pct"] for x in ok])
    band = []
    for x in ok:
        lo, hi = sorted((x["hot"], x["cold"]))
        e = x["ornl_pct"]
        band.append(0.0 if lo <= e <= hi else min(abs(e - lo), abs(e - hi)))
    mine = {"points": len(ok), "hot_minus_ornl_median_pts": float(np.median(gap)),
            "hot_minus_ornl_p10_p90": [float(np.percentile(gap, 10)), float(np.percentile(gap, 90))],
            "within_2pts_of_band": int(np.sum(np.array(band) <= 2.0))}
    rec_ = json.loads(SCORED.read_text(encoding="utf-8"))["ornl"]
    assert mine["points"] == rec_["points"] and mine["within_2pts_of_band"] == rec_["within_2pts_of_band"], (mine, rec_)
    assert abs(mine["hot_minus_ornl_median_pts"] - rec_["hot_minus_ornl_median_pts"]) < 1e-9, (mine, rec_)
    assert np.allclose(mine["hot_minus_ornl_p10_p90"], rec_["hot_minus_ornl_p10_p90"], atol=1e-9), (mine, rec_)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"case": str(CASE.relative_to(REPO)).replace("\\", "/"), "summary": mine,
                               "points": ok}, indent=1), encoding="utf-8")
    print(f"{len(ok)} points, median hot - ORNL {mine['hot_minus_ornl_median_pts']:.4f}, matches the scored summary")


if __name__ == "__main__":
    main()

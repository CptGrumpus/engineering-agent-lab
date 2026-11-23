"""Study 7 post-test revision (validation/motor_ornl/CALIBRATION_PLAN.md): calibrate on back-EMF, choose between the
two hypotheses with the locked-rotor torque, test the chosen one on efficiency (out of sample).

usage: .venv/Scripts/python.exe scripts/motor_calibration.py [--torque-run RUN_ID]
  --torque-run: the hypothesis-A torque-current run (FEMM at the calibrated remanence); without it, only B is scored.
Writes validation/motor_ornl/calibration.json; prints a summary.

Hypothesis B (series turns x k, same copper area per slot) is exact from the committed cold table: currents / k,
flux linkages x k, torque and iron loss at the same ampere-turns unchanged, resistance x k^2.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import tomllib
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from models.motor import efficiency_map as em  # noqa: E402
from motor_blind_comparison import EFF_CASE, LOCKED, V, back_emf, mtpa, read_csv, tables  # noqa: E402
from studies.motor_efficiency import phase_resistance_20C  # noqa: E402


def turns_scaled(fine: dict, k: float) -> dict:
    out = dict(fine)
    out["id"], out["iq"] = fine["id"] / k, fine["iq"] / k
    out["phi_d_Wb"], out["phi_q_Wb"] = k * fine["phi_d_Wb"], k * fine["phi_q_Wb"]
    return out


def torque_rows(curve) -> list[dict]:
    """curve(i_rms) -> MTPA torque; ORNL's currents under both readings."""
    rows = []
    for i, (fig, _) in LOCKED.items():
        pk, rms = curve(i / math.sqrt(2)), curve(float(i))
        rows.append({"ornl_current_A": i, "ornl_Nm": fig, "if_peak_Nm": pk, "if_rms_Nm": rms,
                     "err_if_peak": pk / fig - 1, "err_if_rms": rms / fig - 1})
    return rows


def rms_err(rows, key):
    return float(np.sqrt(np.mean([r[key] ** 2 for r in rows])))


def efficiency(case, fine_by_scen, r_scale, grids) -> dict:
    p = dict(case["parameters"])
    r20 = phase_resistance_20C(p) * r_scale
    vmax = float(p["bus_voltage_V"]) / math.sqrt(6)
    d = []
    for r in read_csv(V / "tm2006_423_table_b1.csv"):
        n, T = r["speed"], r["torque"]
        if not (float(p["speed_min_rpm"]) <= n <= float(p["speed_max_rpm"]) and T >= float(p["torque_min_Nm"])):
            continue
        rec = {"speed_rpm": n, "torque_Nm": T, "ornl_pct": 100 * r["eff_motor"]}
        for name, fine in fine_by_scen.items():
            wt = 20.0 if name == "cold" else 100.0
            o = em.operating_points(fine, speed_rpm=n, torques_Nm=[T], pole_pairs=grids[name]["pole_pairs"],
                                    r_ohm=em.resistance(r20, wt, float(p["copper_alpha_per_K"])), v_max_rms=vmax,
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
    return {"points": len(ok), "hot_minus_ornl_median_pts": float(np.median(gap)),
            "hot_minus_ornl_p10_p90": [float(np.percentile(gap, 10)), float(np.percentile(gap, 90))],
            "within_2pts_of_band": int(np.sum(np.array(band) <= 2.0))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--torque-run")
    a = ap.parse_args()
    case = tomllib.loads(EFF_CASE.read_text(encoding="utf-8"))
    tab = tables(case)
    be = back_emf()
    k = be["ornl_Vrms_per_krpm"] / be["ours"]["LL_total_rms"]
    g = tab["cold"]["grid"]
    out = {"k_flux": k, "blind": {"torque": torque_rows(lambda i: mtpa(g, i))}}
    out["B_turns"] = {"torque": torque_rows(lambda i: mtpa(g, k * i))}
    out["B_turns"]["efficiency"] = efficiency(
        case, {n: turns_scaled(t["fine"], k) for n, t in tab.items()}, k * k, {n: t["grid"] for n, t in tab.items()})
    out["blind"]["efficiency"] = efficiency(case, {n: t["fine"] for n, t in tab.items()}, 1.0,
                                            {n: t["grid"] for n, t in tab.items()})
    if a.torque_run:
        pts = []
        for pj in sorted((REPO / "runs" / a.torque_run / "points").glob("*/point.json")):
            pt = json.loads(pj.read_text(encoding="utf-8"))
            pts.append((float(pt["parameters"]["current_rms_A"]), float(pt["metrics"]["torque_mtpa_Nm"])))
        pts.sort()
        I = np.array([0.0] + [x for x, _ in pts])
        T = np.array([0.0] + [y for _, y in pts])
        out["A_remanence"] = {"torque_run": a.torque_run, "curve_points": pts,
                              "torque": torque_rows(lambda i: float(np.interp(i, I, T)))}
    for h in ("blind", "B_turns", "A_remanence"):
        if h in out:
            out[h]["rms_err_if_peak"] = rms_err(out[h]["torque"], "err_if_peak")
            out[h]["rms_err_if_rms"] = rms_err(out[h]["torque"], "err_if_rms")
    (V / "calibration.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"k = {k:.4f}")
    for h in ("blind", "B_turns", "A_remanence"):
        if h in out:
            print(h, "torque rms error: peak reading", round(out[h]["rms_err_if_peak"], 4), "rms reading",
                  round(out[h]["rms_err_if_rms"], 4))
            print("   if peak:", [f'{r["err_if_peak"]:+.3f}' for r in out[h]["torque"]])
            print("   if rms: ", [f'{r["err_if_rms"]:+.3f}' for r in out[h]["torque"]])
            if "efficiency" in out[h]:
                print("   efficiency", out[h]["efficiency"])


if __name__ == "__main__":
    main()

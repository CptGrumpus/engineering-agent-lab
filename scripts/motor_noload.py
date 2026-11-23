"""Study 7, revision 2 (validation/motor_ornl/CALIBRATION_PLAN.md): ORNL's no-load spin-loss test as calibration data,
then the efficiency score again.

usage: .venv/Scripts/python.exe scripts/motor_noload.py
Reads validation/motor_ornl/tm2006_423_table_3_7.csv (motor-rotor loss against motor-shaft speed, windings not
energised) and hypothesis A's efficiency case (cases/motor_prius_efficiency_br.toml, committed dq tables). Writes
validation/motor_ornl/noload_revision2.json and prints a summary.

Model open-circuit iron loss: the cold dq table at id = iq = 0, P = A f + B f^2 + C f^1.5 (stator + rotor), f electrical.
Residual R(n) = measured - model, signed, linear in speed between the table's rows (it spans the map's 500-6000 rpm).
Two readings (fixed before the table was opened):
  (a) additive, load-independent: R(n) added to every map point's loss (the operating point is unchanged);
  (b) multiplicative: the map's iron loss times k(n) = measured / model, operating points re-optimised.
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

from models.motor import efficiency_map as em  # noqa: E402
from motor_blind_comparison import V, read_csv, tables  # noqa: E402
from studies.motor_efficiency import phase_resistance_20C  # noqa: E402

CASE = REPO / "cases" / "motor_prius_efficiency_br.toml"


def oc_iron_W(grid: dict, n_rpm, pole_pairs: int) -> np.ndarray:
    f_int = em.interpolants(grid)
    pt = np.array([[0.0, 0.0]])
    A, B, C = (float(f_int[k](pt)[0]) for k in ("iron_A_W", "iron_B_W", "iron_C_W"))
    f = np.asarray(n_rpm, float) / 60 * pole_pairs
    return A * f + B * f ** 2 + C * f ** 1.5


def score(recs, key):
    ok = [x for x in recs if np.isfinite(x[f"cold_{key}"]) and np.isfinite(x[f"hot_{key}"])]
    gap = np.array([x[f"hot_{key}"] - x["ornl_pct"] for x in ok])
    band = []
    for x in ok:
        lo, hi = sorted((x[f"hot_{key}"], x[f"cold_{key}"]))
        e = x["ornl_pct"]
        band.append(0.0 if lo <= e <= hi else min(abs(e - lo), abs(e - hi)))
    return {"points": len(ok), "hot_minus_ornl_median_pts": float(np.median(gap)),
            "hot_minus_ornl_p10_p90": [float(np.percentile(gap, 10)), float(np.percentile(gap, 90))],
            "within_2pts_of_band": int(np.sum(np.array(band) <= 2.0))}


def main():
    case = tomllib.loads(CASE.read_text(encoding="utf-8"))
    p = dict(case["parameters"])
    tab = tables(case)
    pp = int(tab["cold"]["grid"]["pole_pairs"])
    meas = read_csv(V / "tm2006_423_table_3_7.csv")
    n_t = np.array([r["motor_shaft_speed_rpm"] for r in meas])
    P_t = np.array([r["motor_rotor_loss_W"] for r in meas])
    model_t = oc_iron_W(tab["cold"]["grid"], n_t, pp)
    R_t = P_t - model_t
    k_t = P_t / model_t
    a, b = np.linalg.lstsq(np.column_stack([n_t, n_t ** 2]), R_t, rcond=None)[0]

    r20 = phase_resistance_20C(p)
    vmax = float(p["bus_voltage_V"]) / math.sqrt(6)
    recs = []
    for r in read_csv(V / "tm2006_423_table_b1.csv"):
        n, T = r["speed"], r["torque"]
        if not (float(p["speed_min_rpm"]) <= n <= float(p["speed_max_rpm"]) and T >= float(p["torque_min_Nm"])):
            continue
        rec = {"speed_rpm": n, "torque_Nm": T, "ornl_pct": 100 * r["eff_motor"]}
        Rn, kn = float(np.interp(n, n_t, R_t)), float(np.interp(n, n_t, k_t))
        P_out = T * 2 * math.pi * n / 60
        for name, t in tab.items():
            wt = 20.0 if name == "cold" else 100.0
            kw = dict(speed_rpm=n, torques_Nm=[T], pole_pairs=pp,
                      r_ohm=em.resistance(r20, wt, float(p["copper_alpha_per_K"])), v_max_rms=vmax,
                      i_max_rms=float(p["current_limit_map_A"]))
            e0 = float(em.operating_points(t["fine"], **kw)["efficiency_pct"][0])
            loss0 = P_out * (100 / e0 - 1) if np.isfinite(e0) else math.nan
            ea = 100 * P_out / (P_out + loss0 + Rn) if np.isfinite(e0) else math.nan
            fine_b = dict(t["fine"]) | {k: t["fine"][k] * kn for k in ("iron_A_W", "iron_B_W", "iron_C_W")}
            eb = float(em.operating_points(fine_b, **kw)["efficiency_pct"][0])
            rec |= {f"{name}_rev1": e0, f"{name}_a": ea, f"{name}_b": eb}
        recs.append(rec)
    out = {"case": str(CASE.relative_to(REPO)), "table": "TM-2006/423 Table 3.7, motor-rotor losses",
           "spin_test": [{"speed_rpm": float(n), "measured_W": float(m), "model_oc_iron_W": float(mo),
                          "residual_W": float(rr), "ratio": float(kk)}
                         for n, m, mo, rr, kk in zip(n_t, P_t, model_t, R_t, k_t)],
           "residual_fit_W": {"a_per_rpm": float(a), "b_per_rpm2": float(b)},
           "rev1": score(recs, "rev1"), "rev2_additive": score(recs, "a"), "rev2_multiplicative": score(recs, "b")}
    (V / "noload_revision2.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("speed  measured  model  residual  ratio")
    for s in out["spin_test"]:
        print(f"{s['speed_rpm']:6.0f} {s['measured_W']:8.1f} {s['model_oc_iron_W']:7.1f} {s['residual_W']:+8.1f} "
              f"{s['ratio']:6.3f}")
    print("fit R = a n + b n^2:", out["residual_fit_W"])
    for k in ("rev1", "rev2_additive", "rev2_multiplicative"):
        print(k, out[k])


if __name__ == "__main__":
    main()

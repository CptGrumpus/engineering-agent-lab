"""Study 7 blind comparison: our committed predictions against ORNL's measurements (ORNL/TM-2006/423).

usage: .venv/Scripts/python.exe scripts/motor_blind_comparison.py
Writes validation/motor_ornl/comparison.json and validation/motor_ornl/comparison.png; prints a summary.

Predictions (all committed before any ORNL test data was opened; see reports/motor/blind_comparison_log.md):
- back-EMF: run motor_prius_ornl_oc_mesh_r3, finest mesh (110.88 V rms line-to-line per 1000 rpm, fundamental, 20 C);
  its full-waveform rms from the same run's flux linkage is reported too (ORNL's oscilloscope rms includes harmonics).
- torque: the cold dq table (the efficiency study's, 20 C), maximum torque over the current angle at a given current
  magnitude (it reproduces motor_prius_torque_current_r1 to 0.2 %); evaluated at ORNL's currents read as peak (I / sqrt 2
  rms) and as rms.
- efficiency: the efficiency study's model and parameters (motor_prius_efficiency_r1), cold and hot scenarios,
  evaluated at ORNL's measured speed and torque (lowest-loss current under 500 V and 300 A).
Validation limits, agreed 2026-11-21: back-EMF within 5 %; peak torque within 10 %; efficiency within 2 points.
"""

from __future__ import annotations

import csv
import json
import math
import sys
import tomllib
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from models.motor import efficiency_map as em  # noqa: E402
from studies.motor_efficiency import load_lut, phase_resistance_20C, run_list  # noqa: E402

V = REPO / "validation" / "motor_ornl"
OC_RUN = "20261122-014658_motor_prius_ornl_oc_mesh_r3"
EFF_CASE = REPO / "cases" / "motor_prius_efficiency_r1.toml"
#: TM-2006/423 Fig. 3.10 (ORNL's stated peaks, 2005 tests) and the maxima of its Table 3.2 (2 deg shaft steps)
LOCKED = {50: (74, 74.0), 75: (118, 117.7), 100: (154, 158.0), 125: (199, 199.0), 150: (221, 229.0),
          200: (286, 286.6), 250: (337, 339.0)}


def read_csv(p):
    with open(p, newline="", encoding="utf-8") as f:
        return [{k: float(v) if v not in ("", None) else math.nan for k, v in r.items()} for r in csv.DictReader(f)]


def back_emf():
    rows = read_csv(V / "tm2006_423_back_emf.csv")
    n = np.array([r["motor_shaft_speed_rpm"] for r in rows])
    vr = np.array([r["back_emf_Vrms"] for r in rows])
    vp = np.array([r["back_emf_Vpeak"] for r in rows])
    k_ornl = float(np.sum(n * vr) / np.sum(n * n) * 1000)  # least squares through the origin, V rms per 1000 rpm
    pdir = sorted((REPO / "runs" / OC_RUN / "points").glob("p*"))[-1]
    fl = read_csv(pdir / "flux_linkage.csv")
    t = np.array([r["time_s"] for r in fl])
    ph = np.array([[r["phi_a_Wb"], r["phi_b_Wb"], r["phi_c_Wb"]] for r in fl])
    k = np.fft.fftfreq(len(t), d=t[1] - t[0])
    e = np.real(np.fft.ifft(2j * np.pi * k[:, None] * np.fft.fft(ph, axis=0), axis=0))
    ll = e[:, 0] - e[:, 1]
    pred_fund = json.loads((pdir / "point.json").read_text(encoding="utf-8"))["metrics"]["back_emf_LL_rms_per_krpm_V"]
    ours = {"LL_fundamental": pred_fund, "LL_total_rms": float(np.sqrt(np.mean(ll ** 2))),
            "phase_total_rms": float(np.sqrt(np.mean(e[:, 0] ** 2))),
            "LL_peak_over_rms": float(np.max(np.abs(ll)) / np.sqrt(np.mean(ll ** 2))),
            "phase_peak_over_rms": float(np.max(np.abs(e[:, 0])) / np.sqrt(np.mean(e[:, 0] ** 2)))}
    return {"ornl_Vrms_per_krpm": k_ornl, "ornl_per_point": (vr / n * 1000).tolist(),
            "ornl_peak_over_rms_6000": float(vp[-1] / vr[-1]), "ours": ours,
            "err_LL_prediction": pred_fund / k_ornl - 1, "err_LL_total": ours["LL_total_rms"] / k_ornl - 1,
            "err_if_ornl_were_phase": ours["phase_total_rms"] / k_ornl - 1}


def tables(case):
    p = case["parameters"]
    out = {}
    for sc in case["sweep"]["scenarios"]:
        g = load_lut([REPO / "runs" / r for r in run_list(sc["lut_run"])])
        out[sc["name"]] = {"grid": g, "fine": em.fine_grid(g, step_A=1.0), "winding_C": float(sc["winding_temperature_C"])}
    return out


def mtpa(grid, i_rms):
    f = em.interpolants(grid)["torque_mean_Nm"]
    gam = np.radians(np.linspace(0, 85, 1701))
    return float(np.max(f(np.column_stack([-i_rms * np.sin(gam), i_rms * np.cos(gam)]))))


def torque(tab):
    g = tab["cold"]["grid"]
    rows = []
    for i, (fig, tbl) in LOCKED.items():
        pk, rms = mtpa(g, i / math.sqrt(2)), mtpa(g, float(i))
        rows.append({"ornl_current_A": i, "ornl_fig_Nm": fig, "ornl_table_max_Nm": tbl, "ours_if_peak_Nm": pk,
                     "ours_if_rms_Nm": rms, "err_if_peak": pk / fig - 1, "err_if_rms": rms / fig - 1})
    return rows


def efficiency(case, tab):
    p = dict(case["parameters"])
    r20 = phase_resistance_20C(p)
    vmax = float(p["bus_voltage_V"]) / math.sqrt(6)
    pts = []
    for r in read_csv(V / "tm2006_423_table_b1.csv"):
        n, T = r["speed"], r["torque"]
        if not (float(p["speed_min_rpm"]) <= n <= float(p["speed_max_rpm"]) and T >= float(p["torque_min_Nm"])):
            continue
        rec = {"speed_rpm": n, "torque_Nm": T, "ornl_motor_eff_pct": 100 * r["eff_motor"]}
        for name, t in tab.items():
            o = em.operating_points(t["fine"], speed_rpm=n, torques_Nm=[T], pole_pairs=t["grid"]["pole_pairs"],
                                    r_ohm=em.resistance(r20, t["winding_C"], float(p["copper_alpha_per_K"])),
                                    v_max_rms=vmax, i_max_rms=float(p["current_limit_map_A"]))
            rec[f"ours_{name}_pct"] = float(o["efficiency_pct"][0])
        pts.append(rec)
    ok = [x for x in pts if np.isfinite(x["ours_cold_pct"]) and np.isfinite(x["ours_hot_pct"])]
    for x in ok:
        lo, hi = sorted((x["ours_hot_pct"], x["ours_cold_pct"]))
        e = x["ornl_motor_eff_pct"]
        x["dist_to_band_pts"] = 0.0 if lo <= e <= hi else (e - hi if e > hi else e - lo)
        x["hot_minus_ornl_pts"] = x["ours_hot_pct"] - e
    d = np.array([x["dist_to_band_pts"] for x in ok])
    h = np.array([x["hot_minus_ornl_pts"] for x in ok])
    summ = {"points_in_domain": len(pts), "points_compared": len(ok),
            "within_2pts_of_band": int(np.sum(np.abs(d) <= 2.0)), "within_2pts_of_hot": int(np.sum(np.abs(h) <= 2.0)),
            "hot_minus_ornl_median_pts": float(np.median(h)), "hot_minus_ornl_p10_p90": [float(np.percentile(h, 10)),
                                                                                        float(np.percentile(h, 90))]}
    for lo_T, hi_T in ((10, 50), (50, 100), (100, 200), (200, 400)):
        sel = np.array([lo_T <= x["torque_Nm"] < hi_T for x in ok])
        if sel.any():
            summ[f"hot_minus_ornl_median_{lo_T}_{hi_T}Nm"] = float(np.median(h[sel]))
            summ[f"within_2pts_of_band_{lo_T}_{hi_T}Nm"] = f"{int(np.sum(np.abs(d[sel]) <= 2))}/{int(sel.sum())}"
    return pts, summ


def figure(be, tq, pts, path):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, _style, plt

    fig, ax = plt.subplots(1, 3, figsize=(14, 4.2))
    fig.patch.set_facecolor(SURFACE)
    rows = read_csv(V / "tm2006_423_back_emf.csv")
    n = np.array([r["motor_shaft_speed_rpm"] for r in rows])
    ax[0].plot(n, [r["back_emf_Vrms"] for r in rows], "o", color=SERIES_2, ms=4, label="ORNL, measured (Vrms)")
    ax[0].plot(n, be["ours"]["LL_total_rms"] * n / 1000, color=SERIES_1, lw=1.5, label="ours, line-to-line rms")
    ax[0].set_xlabel("speed (rpm)"); ax[0].set_ylabel("back-EMF (V rms)"); ax[0].legend(frameon=False, fontsize=8)
    I = [r["ornl_current_A"] for r in tq]
    ax[1].plot(I, [r["ornl_fig_Nm"] for r in tq], "o", color=SERIES_2, ms=4, label="ORNL, locked rotor")
    ax[1].plot(I, [r["ours_if_peak_Nm"] for r in tq], color=SERIES_1, lw=1.5, label="ours, current read as peak")
    ax[1].plot(I, [r["ours_if_rms_Nm"] for r in tq], color=SERIES_1, lw=1.0, ls="--", label="ours, read as rms")
    ax[1].set_xlabel("ORNL current (A)"); ax[1].set_ylabel("peak torque (N m)"); ax[1].legend(frameon=False, fontsize=8)
    ok = [x for x in pts if np.isfinite(x.get("ours_hot_pct", np.nan))]
    ax[2].scatter([x["ornl_motor_eff_pct"] for x in ok], [x["ours_hot_pct"] for x in ok], s=8, color=SERIES_1,
                  label="ours, hot")
    ax[2].plot([60, 100], [60, 100], color=TEXT, lw=0.8)
    ax[2].fill_between([60, 100], [58, 98], [62, 102], color=SERIES_2, alpha=0.15, label="±2 points")
    ax[2].set_xlim(60, 100); ax[2].set_ylim(60, 100)
    ax[2].set_xlabel("ORNL motor efficiency (%)"); ax[2].set_ylabel("ours (%)"); ax[2].legend(frameon=False, fontsize=8)
    for a in ax:
        _style(a)
    fig.suptitle("Study 7 blind comparison against ORNL/TM-2006/423", fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main():
    case = tomllib.loads(EFF_CASE.read_text(encoding="utf-8"))
    tab = tables(case)
    be = back_emf()
    tq = torque(tab)
    pts, summ = efficiency(case, tab)
    out = {"back_emf": be, "torque": tq, "efficiency_summary": summ, "efficiency_points": pts}
    (V / "comparison.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    figure(be, tq, pts, V / "comparison.png")
    print(json.dumps({"back_emf": {k: v for k, v in be.items() if k != "ornl_per_point"}, "torque": tq,
                      "efficiency": summ}, indent=1))


if __name__ == "__main__":
    main()

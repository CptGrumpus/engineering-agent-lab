"""Study: the dq look-up table of our 2004 Prius machine (study 7), the input of the efficiency map.

Model:     pyleecan_femm_lut (models/motor/pyleecan_em.py in its dq-grid mode, Pyleecan environment): one point per
           d-axis current, one 2D magnetostatic FEMM simulation per q-axis current, each over one electrical period,
           keeping the element fields. Each simulation returns the mean dq flux linkages, the mean torque and, per core
           (stator, rotor), the iron-loss coefficients A, B, C (W) with P = A f + B f^2 + C f^1.5 at electrical frequency
           f: a magnetostatic field waveform does not depend on speed, so one solve serves every speed.
Reference: power balance (as in motor_torque: mean sum i dphi/dt = mean torque x mechanical speed, independent of the
           stress-tensor torque); the dq torque equation T = 3 p (phi_d i_q - phi_q i_d) (rms dq quantities) against
           FEMM's torque, a check of the flux linkages the efficiency map interpolates; the imposed current amplitude;
           iron-loss coefficients non-negative. ORNL test data is NOT used here.
Run-level: none (the grid is assembled by studies/motor_efficiency.py).
"""

from __future__ import annotations

import json

import numpy as np

from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study
from studies.motor_em import PyleecanFEMM, fundamental
from studies.motor_torque import power_balance

PARAMS = ("machine", "speed_rpm", "id_A", "iq_min_A", "iq_max_A", "iq_steps", "mesh_fineness", "steps_per_period",
          "angle_points", "magnet_temperature_C", "iron_kh", "iron_alpha", "iron_kc", "iron_ke", "slot_fill",
          "slot_area_mm2", "turns_per_slot")
RUNNER_PARAMS = ("machine", "speed_rpm", "id_A", "iq_min_A", "iq_max_A", "iq_steps", "mesh_fineness",
                 "steps_per_period", "angle_points", "magnet_temperature_C")
#: torques below this are too small for a relative check (the open-circuit corner of the grid)
TORQUE_FLOOR_NM = 5.0


def dq_torque(op, pole_pairs, flux_sign):
    """Mean torque from the dq flux linkages and currents (rms dq quantities: T = 3 p (phi_d i_q - phi_q i_d))."""
    return flux_sign * 3 * pole_pairs * (op["phi_d_Wb"] * op["iq_rms_A"] - op["phi_q_Wb"] * op["id_rms_A"])


#: Sign of the dq torque equation with Pyleecan's dq flux linkages (n2dqh_DataTime, rms). Smoke test 2026-11-22 at
#: id -100, iq 150 A rms: 3 p (phi_d iq - phi_q id) = 403.4 N m against FEMM's 403.45, so +1 (Pyleecan's transform
#: already undoes the phase flux sign that motor_torque.PYLEECAN_FLUX_SIGN handles). A constant, so a change fails.
DQ_FLUX_SIGN = 1.0


class PyleecanFEMMLUT(PyleecanFEMM):
    runner_params = RUNNER_PARAMS + ("iron_loss",)

    def solve(self, params, numerics, tolerance_scale=1.0):
        params = dict(params) | {"iron_loss": {"kh": float(params["iron_kh"]), "alpha": float(params["iron_alpha"]),
                                               "kc": float(params["iron_kc"]), "ke": float(params["iron_ke"])}}
        res = super().solve(params, numerics, tolerance_scale)
        if not res.get("success"):
            return res
        d = json.loads((res["cleanup"] / "out.json").read_text(encoding="utf-8"))
        res["series"] = series_from_outputs(d["ops"])
        res["outputs"] = {k: d[k] for k in ("gap_radius_m", "stack_length_m", "pole_pairs", "series_turns_per_phase",
                                            "winding_factor_1", "slots", "wall_s")} | {"ops": d["ops"]}
        res["message"] = f"{len(d['ops'])} q-axis currents, {d['wall_s']:.0f} s"
        res["nfev"] = len(d["ops"])
        return res


def series_from_outputs(ops):
    s = {"id_rms_A": [], "iq_rms_A": [], "torque_mean_Nm": [], "torque_ripple_pp_Nm": [], "phi_d_Wb": [], "phi_q_Wb": []}
    for core in ("stator", "rotor"):
        for c in "ABC":
            s[f"{core}_iron_{c}_W"] = []
    for o in ops:
        s["id_rms_A"].append(o["id_rms_A"])
        s["iq_rms_A"].append(o["iq_rms_A"])
        s["torque_mean_Nm"].append(float(np.mean(o["torque_Nm"])))
        s["torque_ripple_pp_Nm"].append(float(np.ptp(o["torque_Nm"])))
        s["phi_d_Wb"].append(o["phi_d_Wb"])
        s["phi_q_Wb"].append(o["phi_q_Wb"])
        for core in ("stator", "rotor"):
            for c, v in zip("ABC", o["iron"][core]["coeff_W"]):
                s[f"{core}_iron_{c}_W"].append(v)
    return {k: np.array(v) for k, v in s.items()}


def iron_loss_W(series_or_op, f_hz, core=("stator", "rotor")):
    """P = A f + B f^2 + C f^1.5 summed over the cores, from a series row dict or arrays."""
    tot = 0.0
    for c in core:
        A, B, C = (np.asarray(series_or_op[f"{c}_iron_{k}_W"]) for k in "ABC")
        tot = tot + A * f_hz + B * f_hz ** 2 + C * f_hz ** 1.5
    return tot


class MotorLUTStudy(Study):
    name = "motor_lut"
    models = {"pyleecan_femm_lut": PyleecanFEMMLUT}
    metrics = frozenset({"torque_at_iq_max_Nm", "current_density_max_A_per_mm2", "iron_loss_at_iq_max_1000rpm_W",
                         "iron_loss_at_iq_max_6000rpm_W"})
    param_names = PARAMS
    series_file = "lut.csv"
    compare_description = "max relative difference of the mean torque across q-axis currents"

    def derive(self, params):
        if int(params["iq_steps"]) < 2 or int(params["steps_per_period"]) < 8:
            raise ValueError("at least 2 q-axis currents and 8 steps per electrical period")
        I = float(np.hypot(float(params["id_A"]), max(abs(float(params["iq_min_A"])), abs(float(params["iq_max_A"])))))
        return {"current_rms_max_A": I}

    def compute_metrics(self, series, params, case, outputs=None):
        j = int(np.argmax(np.abs(series["iq_rms_A"])))
        I = float(np.hypot(series["id_rms_A"][j], series["iq_rms_A"][j]))
        pp = int(outputs["pole_pairs"])
        row = {k: v[j] for k, v in series.items()}
        return {"torque_at_iq_max_Nm": float(series["torque_mean_Nm"][j]),
                "current_density_max_A_per_mm2": float(params["turns_per_slot"]) * I / (
                    float(params["slot_fill"]) * float(params["slot_area_mm2"])),
                "iron_loss_at_iq_max_1000rpm_W": float(iron_loss_W(row, 1000 / 60 * pp)),
                "iron_loss_at_iq_max_6000rpm_W": float(iron_loss_W(row, 6000 / 60 * pp))}

    def verify_point(self, case, point, pdir, series, backend):
        tol = case["verification"]
        p, out = point["parameters"], point["solver_outputs"]
        ops, pp = out["ops"], int(out["pole_pairs"])
        pb, cur, dq, neg = [], [], [], []
        for op in ops:
            T = float(np.mean(op["torque_Nm"]))
            I = float(np.hypot(op["id_rms_A"], op["iq_rms_A"]))
            if abs(T) >= TORQUE_FLOOR_NM:
                p_el, p_mech = power_balance(op, float(p["speed_rpm"]))
                pb.append(abs(p_el - p_mech) / abs(p_mech))
                dq.append(abs(dq_torque(op, pp, DQ_FLUX_SIGN) - T) / abs(T))
            if I > 0:
                t = np.asarray(op["current_time_s"])
                Iamp = np.abs(fundamental(t, np.asarray(op["current_A"])))
                cur.append(float(np.max(np.abs(Iamp - np.sqrt(2) * I)) / (np.sqrt(2) * I)))
            neg.append(min(min(op["iron"][c]["coeff_W"]) for c in ("stator", "rotor")))
        checks = [
            check("power_balance", f"max over q-axis currents (|T| >= {TORQUE_FLOOR_NM:g} N m) of |mean(sum i dphi/dt) - "
                  "mean torque x omega_m| / (mean torque x omega_m)", max(pb) if pb else 0.0, tol["power_balance_rel_tol"]),
            check("dq_torque", f"max over q-axis currents (|T| >= {TORQUE_FLOOR_NM:g} N m) of |3 p (phi_d i_q - phi_q i_d) - "
                  "FEMM torque| / FEMM torque: the mean dq flux linkages the efficiency map interpolates reproduce the "
                  "torque (model form: harmonics are left out of the dq means)", max(dq) if dq else 0.0,
                  tol["dq_torque_rel_tol"]),
            check("current_amplitude", "max |imposed phase current fundamental - sqrt(2) x requested rms| / peak",
                  max(cur) if cur else 0.0, tol["current_rel_tol"]),
            check("iron_coefficients_non_negative", "min iron-loss coefficient over cores and currents (W), below 0 "
                  "would be unphysical", -min(neg), 0.0),
            check("time_resolution", "48 / steps per electrical period (below 1: at least 48)",
                  48 / int(p["steps_per_period"]), 1.0, kind="validity"),
        ]
        lut_figure(pdir / "response.png", series, point, pp)
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "mesh_fineness":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: -float(pt["parameters"]["mesh_fineness"]))
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(1.0 / float(pt["parameters"]["mesh_fineness"]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
        for metric in ("torque_at_iq_max_Nm", "iron_loss_at_iq_max_1000rpm_W", "iron_loss_at_iq_max_6000rpm_W"):
            vals = tuple(pt["metrics"][metric] for pt in fine)
            u = discretization_uncertainty(hs, vals, design_order=2, noise_floor=tol.get("mesh_noise_rel", 1e-5))
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


def lut_figure(path, series, point, pole_pairs):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, _style, plt

    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(13, 3.8))
    fig.patch.set_facecolor(SURFACE)
    iq = series["iq_rms_A"]
    a1.plot(iq, series["torque_mean_Nm"], "o-", color=SERIES_1, lw=1.5, ms=4, label="FEMM (stress tensor)")
    ops = [{"phi_d_Wb": d, "phi_q_Wb": q, "id_rms_A": i, "iq_rms_A": j}
           for d, q, i, j in zip(series["phi_d_Wb"], series["phi_q_Wb"], series["id_rms_A"], iq)]
    a1.plot(iq, [dq_torque(o, pole_pairs, DQ_FLUX_SIGN) for o in ops], "s--", color=SERIES_2, lw=1, ms=3,
            label="3 p (phi_d iq - phi_q id)")
    a1.set_xlabel("q-axis current (A rms)")
    a1.set_ylabel("mean torque (N m)")
    a1.legend(frameon=False, fontsize=8)
    a2.plot(iq, series["phi_d_Wb"], "o-", color=SERIES_1, lw=1.5, ms=4, label="phi_d")
    a2.plot(iq, series["phi_q_Wb"], "o-", color=SERIES_2, lw=1.5, ms=4, label="phi_q")
    a2.set_xlabel("q-axis current (A rms)")
    a2.set_ylabel("mean flux linkage (Wb, rms dq)")
    a2.legend(frameon=False, fontsize=8)
    f = 1000 / 60 * pole_pairs * 4  # electrical frequency at 4000 rpm
    a3.plot(iq, iron_loss_W(series, f, ("stator",)), "o-", color=SERIES_1, lw=1.5, ms=4, label="stator core")
    a3.plot(iq, iron_loss_W(series, f, ("rotor",)), "o-", color=SERIES_2, lw=1.5, ms=4, label="rotor core")
    a3.set_xlabel("q-axis current (A rms)")
    a3.set_ylabel("iron loss at 4000 rpm (W)")
    a3.legend(frameon=False, fontsize=8)
    for ax in (a1, a2, a3):
        _style(ax)
    fig.suptitle(f"{point['label']}: d-axis current {float(point['parameters']['id_A']):g} A rms", fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = MotorLUTStudy()

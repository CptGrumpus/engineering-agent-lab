"""Study: electric-machine torque against current (study 7), Pyleecan + FEMM, on our 2004 Prius machine.

Model:     pyleecan_femm_load (models/motor/pyleecan_em.py in its current-angle mode, Pyleecan environment): at a
           given rms phase current, one 2D magnetostatic FEMM simulation per current angle gamma (from the q axis
           towards negative d), each over one electrical period
Reference: power balance, exact for a lossless magnetostatic model over a whole period: the mean electrical power
           converted, mean(sum_k i_k d(phi_k)/dt), equals mean torque x mechanical speed (an independent route to the
           torque FEMM computes with its weighted stress tensor); the imposed phase currents against the requested
           amplitude (guards Pyleecan's rms convention); three-phase symmetry of the flux linkages under load; the
           maximum torque per amp (MTPA) bracketed inside the angle sweep. ORNL test data is NOT used here.
Run-level: GCI on the MTPA torque when the sweep is mesh_fineness
"""

from __future__ import annotations

import numpy as np

from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study
from studies.motor_em import MACHINES, PyleecanFEMM, fundamental

PARAMS = ("machine", "speed_rpm", "current_rms_A", "angle_min_deg", "angle_max_deg", "angle_steps", "mesh_fineness",
          "steps_per_period", "angle_points", "rated_torque_Nm", "slot_fill", "slot_area_mm2", "turns_per_slot")
RUNNER_PARAMS = ("machine", "speed_rpm", "current_rms_A", "angle_min_deg", "angle_max_deg", "angle_steps",
                 "mesh_fineness", "steps_per_period", "angle_points")


def spectral_derivative(t, x):
    """d/dt of each column of x (rows = time over exactly one period, endpoint excluded)."""
    x = np.asarray(x, float)
    n, T = x.shape[0], (t[1] - t[0]) * len(t)
    k = np.fft.rfftfreq(n, d=1.0 / n)
    return np.fft.irfft(1j * 2 * np.pi * k[:, None] / T * np.fft.rfft(x, axis=0), n, axis=0)


#: Pyleecan's phase flux linkage has the opposite sign to the motor convention v = R i + d(psi)/dt: with its
#: currents and torque, sum(i d(phi)/dt) comes out as minus the mechanical power (smoke test 2026-11-21: magnitudes
#: agreed to 0.05 % at 250 A rms, signs opposite at every angle). The check keeps the sign, so a change of
#: convention fails it instead of passing unnoticed.
PYLEECAN_FLUX_SIGN = -1.0


def power_balance(op, speed_rpm, flux_sign=PYLEECAN_FLUX_SIGN):
    """(mean electrical power converted, mean torque x mechanical speed) for one operating point."""
    t = np.asarray(op["time_s"])
    phi = np.asarray(op["phi_Wb"])
    i = np.asarray(op["current_A"])
    if i.shape != phi.shape:
        i = i.T
    p_el = flux_sign * float(np.mean(np.sum(i * spectral_derivative(t, phi), axis=1)))
    p_mech = float(np.mean(op["torque_Nm"])) * 2 * np.pi * speed_rpm / 60
    return p_el, p_mech


def mtpa(gammas, torques):
    """Maximum of a parabola through the best sample and its two neighbours; (angle, torque, interior?)."""
    g, T = np.asarray(gammas, float), np.asarray(torques, float)
    j = int(np.argmax(T))
    if j == 0 or j == len(T) - 1:
        return float(g[j]), float(T[j]), False
    a, b, c = np.polyfit(g[j - 1:j + 2], T[j - 1:j + 2], 2)
    gm = -b / (2 * a)
    return float(gm), float(np.polyval([a, b, c], gm)), True


class PyleecanFEMMLoad(PyleecanFEMM):
    runner_params = RUNNER_PARAMS

    def solve(self, params, numerics, tolerance_scale=1.0):
        import json

        res = super().solve(params, numerics, tolerance_scale)
        if not res.get("success"):
            return res
        d = json.loads((res["cleanup"] / "out.json").read_text(encoding="utf-8"))
        res["series"] = series_from_outputs(d["ops"])
        res["outputs"] = {k: d[k] for k in ("gap_radius_m", "stack_length_m", "pole_pairs", "series_turns_per_phase",
                                            "winding_factor_1", "slots", "wall_s")} | {"ops": d["ops"]}
        res["message"] = f"{len(d['ops'])} current angles, {d['wall_s']:.0f} s"
        res["nfev"] = len(d["ops"])
        return res


class MotorTorqueStudy(Study):
    name = "motor_torque"
    models = {"pyleecan_femm_load": PyleecanFEMMLoad}
    metrics = frozenset({"torque_mtpa_Nm", "mtpa_angle_deg", "torque_ripple_pp_at_mtpa_Nm", "torque_per_amp_Nm_per_A",
                         "current_density_rms_A_per_mm2"})
    param_names = PARAMS
    series_file = "angle_sweep.csv"
    compare_description = "max relative difference of the mean torque across current angles"

    def derive(self, params):
        if float(params["current_rms_A"]) <= 0 or int(params["angle_steps"]) < 3:
            raise ValueError("positive current and at least 3 current angles")
        if int(params["steps_per_period"]) < 8:
            raise ValueError("at least 8 steps per electrical period")
        J = float(params["turns_per_slot"]) * float(params["current_rms_A"]) / (
            float(params["slot_fill"]) * float(params["slot_area_mm2"]))
        return {"current_density_rms_A_per_mm2": J}

    def compute_metrics(self, series, params, case, outputs=None):
        gm, Tm, _ = mtpa(series["gamma_deg"], series["torque_mean_Nm"])
        j = int(np.argmax(series["torque_mean_Nm"]))
        I = float(params["current_rms_A"])
        return {"torque_mtpa_Nm": Tm, "mtpa_angle_deg": gm,
                "torque_ripple_pp_at_mtpa_Nm": float(series["torque_ripple_pp_Nm"][j]),
                "torque_per_amp_Nm_per_A": Tm / I,
                "current_density_rms_A_per_mm2": float(params["turns_per_slot"]) * I / (
                    float(params["slot_fill"]) * float(params["slot_area_mm2"]))}

    def verify_point(self, case, point, pdir, series, backend):
        tol = case["verification"]
        p, out = point["parameters"], point["solver_outputs"]
        ops = out["ops"]
        I = float(p["current_rms_A"])
        pb, cur, sym = [], [], []
        for op in ops:
            p_el, p_mech = power_balance(op, float(p["speed_rpm"]))
            pb.append(abs(p_el - p_mech) / max(abs(p_mech), 1e-9))
            t = np.asarray(op["current_time_s"])
            Iamp = np.abs(fundamental(t, np.asarray(op["current_A"])))
            cur.append(float(np.max(np.abs(Iamp - np.sqrt(2) * I)) / (np.sqrt(2) * I)))
            F = np.abs(fundamental(np.asarray(op["time_s"]), np.asarray(op["phi_Wb"])))
            sym.append(float(np.ptp(F) / np.mean(F)))
        _, _, interior = mtpa(series["gamma_deg"], series["torque_mean_Nm"])
        checks = [
            check("power_balance", "max over current angles of |mean(sum i dphi/dt) - mean torque x omega_m| / "
                  "(mean torque x omega_m): energy conservation, an independent route to FEMM's stress-tensor torque",
                  max(pb), tol["power_balance_rel_tol"]),
            check("current_amplitude", "max |imposed phase current fundamental - sqrt(2) x requested rms| / peak "
                  "(Pyleecan's dq currents are rms)", max(cur), tol["current_rel_tol"]),
            check("phase_symmetry_load", "max over angles of the spread of the three phases' fundamental flux "
                  "linkage / mean, under load", max(sym), tol["phase_symmetry_rel_tol"]),
            check("mtpa_bracketed", "maximum torque inside the angle sweep (0 = yes)", 0.0 if interior else 1.0, 0.0,
                  kind="validity"),
            check("time_resolution", "48 / steps per electrical period (below 1: at least 48)",
                  48 / int(p["steps_per_period"]), 1.0, kind="validity"),
        ]
        torque_figure(pdir / "response.png", series, ops, point, title=f"{point['label']}  ({p['machine']}, "
                      f"{I:g} A rms, fineness {float(p['mesh_fineness']):g})")
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
        for metric in sorted({r["metric"] for r in case["requirements"]} | {"torque_mtpa_Nm"}):
            vals = tuple(pt["metrics"][metric] for pt in fine)
            if len(set(vals)) == 1:
                continue
            u = discretization_uncertainty(hs, vals, design_order=2, noise_floor=tol.get("mesh_noise_rel", 1e-5))
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


def series_from_outputs(ops):
    return {"gamma_deg": np.array([o["gamma_deg"] for o in ops]),
            "id_rms_A": np.array([o["id_rms_A"] for o in ops]),
            "iq_rms_A": np.array([o["iq_rms_A"] for o in ops]),
            "torque_mean_Nm": np.array([np.mean(o["torque_Nm"]) for o in ops]),
            "torque_ripple_pp_Nm": np.array([np.ptp(o["torque_Nm"]) for o in ops])}


def torque_figure(path, series, ops, point, *, title):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2, _style, plt

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
    fig.patch.set_facecolor(SURFACE)
    g, T = series["gamma_deg"], series["torque_mean_Nm"]
    a1.plot(g, T, "o-", color=SERIES_1, lw=1.6, ms=5, label="mean torque (FEMM stress tensor)")
    gm, Tm = point["metrics"]["mtpa_angle_deg"], point["metrics"]["torque_mtpa_Nm"]
    a1.plot([gm], [Tm], "o", color=SERIES_2, ms=8, label=f"MTPA {Tm:.1f} N m at {gm:.1f} deg")
    a1.set_xlabel("current angle from the q axis (deg)")
    a1.set_ylabel("torque (N m)")
    a1.legend(frameon=False, fontsize=8)
    j = int(np.argmax(T))
    t = np.asarray(ops[j]["torque_time_s"]) * 1e3
    a2.plot(t, ops[j]["torque_Nm"], color=SERIES_1, lw=1.4)
    a2.axhline(np.mean(ops[j]["torque_Nm"]), color=TEXT_2, lw=0.8, ls="--")
    a2.set_xlabel("time (ms), one period of the torque (shorter than the electrical period)")
    a2.set_ylabel(f"torque at {g[j]:g} deg (N m)")
    for ax in (a1, a2):
        _style(ax)
    fig.suptitle(title, fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = MotorTorqueStudy()
_ = MACHINES  # the backend copies our machine files into the run inputs (inherited sources)

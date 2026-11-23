"""Study: electric-machine electromagnetics (study 7), Pyleecan + FEMM, starting with the 2004 Toyota Prius motor.

Model:     pyleecan_femm (models/motor/pyleecan_em.py, run in its own Python environment, which needs Pyleecan
           master and SciDataTool master; see tool-notes): 2D magnetostatic FEMM solves over one electrical period
Reference: winding theory (flux linkage = 2 N k_w1 B_1 R L / p from the FEMM air-gap field's fundamental) as an
           independent route to the flux linkage FEMM integrates over the coils; three-phase symmetry; zero mean
           open-circuit torque. The ORNL test data is NOT used here: it is the blind validation at the end of the
           study (BACKLOG, study 7 plan)
Run-level: GCI on the flux linkage and back-EMF when the sweep is mesh_fineness
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness.backend_base import Backend, failed
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study

RUNNER = "models/motor/pyleecan_em.py"
#: our own machine definitions (built by models/motor/build_prius_ornl.py); a case names one by file name
MACHINES = ("models/motor/Toyota_Prius_ORNL.json", "models/motor/Toyota_Prius_ORNL_M250-35A.json",
            "models/motor/Toyota_Prius_ORNL_190Y390.json", "models/motor/Toyota_Prius_ORNL_M330-35A-Js205.json",
            # post-test calibration, hypothesis A (validation/motor_ornl/CALIBRATION_PLAN.md): remanence variants
            "models/motor/Toyota_Prius_ORNL_Br1p0000.json", "models/motor/Toyota_Prius_ORNL_Br1p0300.json",
            "models/motor/Toyota_Prius_ORNL_Br1p0600.json",
            # the calibrated remanence (motor_prius_cal_oc_br: ORNL back-EMF matched at 1.036 T)
            "models/motor/Toyota_Prius_ORNL_Br1p0360.json")
PARAMS = ("machine", "speed_rpm", "id_A", "iq_A", "mesh_fineness", "steps_per_period", "angle_points",
          "max_speed_rpm", "bus_voltage_V", "rated_torque_Nm")
NUMERIC = PARAMS[1:]


def pyleecan_python() -> Path:
    """The Pyleecan environment's interpreter: PYLEECAN_PYTHON, else ~/.venvs/pyleecan."""
    env = os.environ.get("PYLEECAN_PYTHON")
    return Path(env) if env else Path.home() / ".venvs" / "pyleecan" / "Scripts" / "python.exe"


def _p(params, k):
    return float(params[k])


def fundamental(t, x):
    """Complex fundamental amplitude of each column of x over one period sampled uniformly (endpoint excluded)."""
    x = np.atleast_2d(np.asarray(x, dtype=float))
    if x.shape[0] != len(t):
        x = x.T
    return 2 * np.fft.rfft(x, axis=0)[1] / len(t)


def line_emf_peak(t, phi_a, phi_b, scale):
    """Peak of e_ab = d(phi_a - phi_b)/dt from a spectral derivative over one period, scaled to another speed."""
    n, T = len(t), (t[1] - t[0]) * len(t)
    F = np.fft.rfft(np.asarray(phi_a) - np.asarray(phi_b))
    k = np.arange(len(F))
    e = np.fft.irfft(1j * 2 * np.pi * k / T * F, n)
    return float(np.max(np.abs(e)) * scale)


class PyleecanFEMM(Backend):
    sources = (RUNNER, *MACHINES)
    #: parameters passed to the runner
    runner_params = PARAMS

    def __init__(self):
        self.python = pyleecan_python()
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        self.runner = self.source_path(RUNNER, source_dir)
        self.machines = {Path(m).name: self.source_path(m, source_dir) for m in MACHINES}
        r = subprocess.run([str(self.python), "-c", "import pyleecan, SciDataTool, numpy; "
                            "print(getattr(pyleecan, '__version__', '?'), SciDataTool.__version__, numpy.__version__)"],
                           capture_output=True, text=True, timeout=120, env=os.environ | {"PYTHONUTF8": "1"})
        v = (r.stdout.strip().split() + ["?"] * 3)[:3]
        self._versions = {"pyleecan": v[0], "SciDataTool": v[1], "numpy_pyleecan_env": v[2]}

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="motor_"))
        run_params = {k: params[k] for k in self.runner_params}
        if run_params["machine"] in self.machines:  # ours, from the run's inputs (hashed), not Pyleecan's data folder
            run_params["machine"] = str(self.machines[run_params["machine"]])
        (work / "params.json").write_text(json.dumps(run_params), encoding="utf-8")
        r = subprocess.run([str(self.python), str(self.runner), "params.json", "out.json"], cwd=work,
                           capture_output=True, text=True, timeout=float(numerics.get("solver_timeout_s", 3600)),
                           env=os.environ | {"PYTHONUTF8": "1"})
        (work / "runner.log").write_text(r.stdout + r.stderr, encoding="utf-8")
        files = {f.name: f for f in (work / "params.json", work / "runner.log") if f.exists()}
        if r.returncode != 0 or not (work / "out.json").exists():
            return failed(f"Pyleecan/FEMM runner failed (exit {r.returncode}): {r.stderr.strip()[-300:]}") | {
                "files": files, "cleanup": work}
        d = json.loads((work / "out.json").read_text(encoding="utf-8"))
        t, P = np.array(d["time_s"]), np.array(d["phi_Wb"])
        series = {"time_s": t, "phi_a_Wb": P[:, 0], "phi_b_Wb": P[:, 1], "phi_c_Wb": P[:, 2]}
        outputs = {k: d[k] for k in ("gap_radius_m", "stack_length_m", "pole_pairs", "series_turns_per_phase",
                                     "winding_factor_1", "slots", "wall_s")}
        outputs |= {"torque_Nm": d["torque_Nm"], "gap_angle_rad": d["gap_angle_rad"], "gap_Br_T": d["gap_Br_T"]}
        return {"success": True, "message": f"{len(t)} steps per electrical period, {d['wall_s']:.1f} s",
                "nfev": len(t), "series": series, "outputs": outputs, "files": files, "cleanup": work}

    def tool_versions(self):
        return self._versions


class MotorEMStudy(Study):
    name = "motor_em"
    models = {"pyleecan_femm": PyleecanFEMM}
    metrics = frozenset({"lambda1_Wb", "back_emf_LL_rms_per_krpm_V", "back_emf_LL_peak_at_max_speed_V",
                         "mean_torque_Nm", "torque_ripple_pp_Nm"})
    param_names = PARAMS
    series_file = "flux_linkage.csv"
    compare_description = "max relative difference of the phase-a flux linkage"

    def derive(self, params):
        n = _p(params, "speed_rpm")
        if n <= 0 or int(params["steps_per_period"]) < 8:
            raise ValueError("positive speed and at least 8 steps per electrical period")
        return {"speed_ratio_to_max": _p(params, "max_speed_rpm") / n}

    def compute_metrics(self, series, params, case, outputs=None):
        t = np.asarray(series["time_s"])
        P = np.column_stack([series[f"phi_{c}_Wb"] for c in "abc"])
        lam1 = float(np.mean(np.abs(fundamental(t, P))))
        p = int(outputs["pole_pairs"])
        we_krpm = 2 * np.pi * 1000 / 60 * p
        T = np.asarray(outputs["torque_Nm"])
        return {"lambda1_Wb": lam1, "back_emf_LL_rms_per_krpm_V": np.sqrt(3) * we_krpm * lam1 / np.sqrt(2),
                "back_emf_LL_peak_at_max_speed_V": line_emf_peak(t, P[:, 0], P[:, 1],
                                                                 _p(params, "max_speed_rpm") / _p(params, "speed_rpm")),
                "mean_torque_Nm": float(np.mean(T)), "torque_ripple_pp_Nm": float(np.ptp(T))}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        p, m, out = point["parameters"], point["metrics"], point["solver_outputs"]
        t = np.asarray(series["time_s"])
        F = fundamental(t, np.column_stack([series[f"phi_{c}_Wb"] for c in "abc"]))
        amp = np.abs(F)
        sym = float(np.ptp(amp) / np.mean(amp))
        ang = np.degrees(np.angle(F))
        shifts = [((ang[i] - ang[(i + 1) % 3]) % 360) for i in range(3)]
        shift_err = float(max(min(abs(s - 120), abs(s - 240)) for s in shifts))
        th = np.asarray(out["gap_angle_rad"])
        br = np.asarray(out["gap_Br_T"])
        pp = int(out["pole_pairs"])
        dth = th[1] - th[0]
        B1 = float(np.hypot(*(pp / np.pi * 2 * np.sum(br * f(pp * th)) * dth for f in (np.cos, np.sin))))
        lam_theory = 2 * out["series_turns_per_phase"] * out["winding_factor_1"] * B1 * out["gap_radius_m"] \
            * out["stack_length_m"] / pp
        checks = [
            check("phase_symmetry", "spread of the three phases' fundamental flux linkage / mean", sym,
                  tol["phase_symmetry_rel_tol"]),
            check("phase_shift", "max |phase shift between phases - 120 deg| (deg)", shift_err, tol["phase_shift_deg_tol"]),
            check("winding_theory", "|2 N k_w1 B_1 R L / p from the air-gap field - FEMM coil flux linkage| / FEMM "
                  "(model form: mid-gap sampling, slot openings, leakage)", abs(lam_theory - m["lambda1_Wb"])
                  / m["lambda1_Wb"], tol["winding_theory_rel_tol"]),
        ]
        if _p(p, "id_A") == 0 and _p(p, "iq_A") == 0:
            checks.append(check("open_circuit_torque", "|mean torque at zero current| / rated torque (no net "
                                "torque without current)", abs(m["mean_torque_Nm"]) / _p(p, "rated_torque_Nm"),
                                tol["open_circuit_torque_rel_tol"]))
        checks.append(check("time_resolution", "48 / steps per electrical period (below 1: at least 48)",
                            48 / int(p["steps_per_period"]), 1.0, kind="validity"))
        motor_figure(pdir / "response.png", series, out, lam_theory, m, title=f"{point['label']}  ({p['machine']}, "
                     f"{_p(p, 'speed_rpm'):g} rpm, id {_p(p, 'id_A'):g} A, iq {_p(p, 'iq_A'):g} A)")
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
        for metric in sorted({r["metric"] for r in case["requirements"]} | {"lambda1_Wb"}):
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine), design_order=2,
                                           noise_floor=tol.get("mesh_noise_rel", 1e-5))
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


def motor_figure(path, series, out, lam_theory, m, *, title):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2, _style, plt

    t = np.asarray(series["time_s"]) * 1e3
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
    fig.patch.set_facecolor(SURFACE)
    for c, col in zip("abc", (SERIES_1, TEXT_2, SERIES_2)):
        a1.plot(t, series[f"phi_{c}_Wb"], color=col, lw=1.4, label=f"phase {c}")
    a1.axhline(lam_theory, color=TEXT, lw=0.8, ls="--", label="winding theory, fundamental")
    a1.set_xlabel("time (ms)")
    a1.set_ylabel("flux linkage (Wb)")
    a1.legend(frameon=False, fontsize=8)
    th = np.degrees(np.asarray(out["gap_angle_rad"]))
    a2.plot(th, out["gap_Br_T"], color=SERIES_1, lw=1.2)
    a2.set_xlabel("mechanical angle (deg)")
    a2.set_ylabel("radial air-gap flux density at t = 0 (T)")
    for ax in (a1, a2):
        _style(ax)
    fig.suptitle(f"{title}: back-EMF {m['back_emf_LL_rms_per_krpm_V']:.2f} V rms LL per 1000 rpm", fontsize=10,
                 color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = MotorEMStudy()

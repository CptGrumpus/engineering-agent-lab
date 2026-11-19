"""Study: 1-DOF mass-spring-damper step response.

Models:   msd (SciPy, models/msd.py), msd_modelica (OpenModelica, models/modelica/EngLab.mo)
Reference: closed-form step response, validation/msd_analytical.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.integrate import trapezoid

from harness.backend_base import Backend, ModelicaBackend
from harness.checks import check
from harness.metrics import step_metrics
from harness.plotting import plot_response
from harness.study import Study
from models.msd import MSDParameters, simulate
from validation import msd_analytical as ref

PARAMS = ("mass_kg", "stiffness_N_per_m", "damping_ratio", "step_force_N")


class ScipyMSD(Backend):
    sources = ("models/msd.py",)

    def solve(self, params, numerics, tolerance_scale=1.0):
        res = simulate(
            MSDParameters.from_dict(params),
            t_end_s=float(numerics["t_end_s"]),
            n_points=int(numerics["n_points"]),
            method=str(numerics["method"]),
            rtol=float(numerics["rtol"]) * tolerance_scale,
            atol=float(numerics["atol"]) * tolerance_scale,
        )
        series = None
        if res["success"]:
            series = {"t_s": res["t"], "x_m": res["x"], "v_m_per_s": res["v"]}
        return {"success": res["success"], "message": res["message"], "nfev": res["nfev"],
                "series": series}

    def tool_versions(self):
        import scipy
        return {"scipy": scipy.__version__}


class ModelicaMSD(ModelicaBackend):
    source = "models/modelica/EngLab.mo"
    class_name = "EngLab.MSDStep"
    param_names = PARAMS
    outputs = {"x_m": "x_m", "v_m_per_s": "v_m_per_s"}


class MSDStudy(Study):
    name = "msd"
    models = {"msd": ScipyMSD, "msd_modelica": ModelicaMSD}
    metrics = frozenset({"overshoot_pct", "settling_time_s", "static_deflection_mm",
                         "peak_displacement_mm"})
    param_names = PARAMS
    compare_description = "max |x - x_other| / (F/k)"

    def derive(self, params):
        return MSDParameters.from_dict(params).derived()

    def compute_metrics(self, series, params, case):
        return step_metrics(series["t_s"], series["x_m"],
                            float(case["metrics"]["settling_band_fraction"]))

    def compare_point(self, case, params, a, b):
        xs = params["step_force_N"] / params["stiffness_N_per_m"]
        return float(np.max(np.abs(a["x_m"] - b["x_m"])) / abs(xs))

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        band = float(case["metrics"]["settling_band_fraction"])
        t, x, v = series["t_s"], series["x_m"], series["v_m_per_s"]

        params = point["parameters"]
        m = float(params["mass_kg"])
        k = float(params["stiffness_N_per_m"])
        f = float(params["step_force_N"])
        c = float(point["derived"]["damping_N_s_per_m"])
        xs = ref.static_deflection(k, f)

        x_ref = ref.step_response(t, m, c, k, f)
        np.savetxt(pdir / "reference.csv", np.column_stack([t, x_ref]), delimiter=",",
                   header="t_s,x_ref_m", comments="", fmt="%.15e")
        metrics = point["metrics"]
        ref_metrics = step_metrics(t, x_ref, band)

        checks = [
            check("reference_agreement",
                  "max |x_num - x_ref| / (F/k) over the full time history",
                  np.max(np.abs(x - x_ref)) / abs(xs), tol["reference_max_rel_error"]),
            check("overshoot_reference",
                  "|overshoot_num - overshoot_closed_form| in percentage points",
                  abs(metrics["overshoot_pct"] - ref.overshoot_pct(m, c, k)),
                  tol["overshoot_abs_tol_pct"]),
            check("settling_reference",
                  "|settling_num - settling of analytical curve| in s",
                  abs(metrics["settling_time_s"] - ref_metrics["settling_time_s"]),
                  tol["settling_time_abs_tol_s"]),
            check("steady_state",
                  "|x(t_end) - F/k| / (F/k)",
                  abs(x[-1] - xs) / abs(xs), tol["steady_state_rel_tol"]),
        ]

        # Energy: F*x_end = 1/2 m v_end^2 + 1/2 k x_end^2 + integral(c v^2 dt)
        work_in = f * x[-1]
        stored = 0.5 * m * v[-1] ** 2 + 0.5 * k * x[-1] ** 2
        dissipated = trapezoid(c * v**2, t)
        checks.append(check("energy_balance",
                            "|W_in - (KE + PE + E_dissipated)| / W_in",
                            abs(work_in - stored - dissipated) / abs(work_in),
                            tol["energy_residual_rel_tol"]))

        tight = backend.solve(params, case["numerics"], tolerance_scale=1e-2)
        change = (np.max(np.abs(tight["series"]["x_m"] - x)) / abs(xs)
                  if tight["success"] else float("inf"))
        checks.append(check("solver_convergence",
                            "max |x(rtol, atol) - x(rtol/100, atol/100)| / (F/k)",
                            change, tol["convergence_max_rel_change"]))

        req_by_metric = {r["metric"]: r for r in case["requirements"]}
        plot_response(
            pdir / "response.png", t, x, x_ref,
            static_deflection_m=xs,
            settling_band_fraction=band,
            overshoot_limit_pct=req_by_metric.get("overshoot_pct", {}).get("limit"),
            settling_limit_s=req_by_metric.get("settling_time_s", {}).get("limit"),
            error_tolerance=tol["reference_max_rel_error"],
            title=f"{point['label']}  (ζ = {params['damping_ratio']:g})",
        )
        return checks


STUDY = MSDStudy()

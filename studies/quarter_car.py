"""Study: 2-DOF quarter-car ride and road-holding (linear tire, or a tire that can lift off).

Models:
  quarter_car           SciPy solve_ivp (models/quarter_car.py), road 'bump' or 'iso8608'
  quarter_car_modelica  OpenModelica, MSL Translational components, road 'bump' only
                        (models/modelica/EngLab.mo, EngLab.QuarterCarBump)

References (validation/quarter_car_reference.py, independent of the model code):
  bump     state-space matrix-exponential solution on a 10x finer grid
  bump, tire_model = "liftoff"
           piecewise-exact solution: matrix exponential within each contact or
           airborne phase, switch times by root-finding on the exact solution
  iso8608  closed-form window RMS from hand-derived transfer functions
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.integrate import simpson

from excitation.road import Road
from harness.backend_base import Backend, ModelicaBackend
from harness.checks import check
from harness.plotting import quarter_car_bump_figure, quarter_car_road_figure
from harness.study import Study
from models import quarter_car as qc
from validation import quarter_car_reference as ref

BUMP_METRICS = {"peak_body_accel_m_per_s2", "max_suspension_travel_mm", "max_tire_load_ratio"}
ROAD_METRICS = {"body_accel_rms_m_per_s2", "suspension_travel_rms_mm", "tire_load_rms_ratio"}


def body_accel(series: dict, params: dict) -> np.ndarray:
    ms, _, ks, cs, _ = qc.unpack(params)
    return -(ks * (series["zs_m"] - series["zu_m"])
             + cs * (series["vs_m_per_s"] - series["vu_m_per_s"])) / ms


def liftoff(params: dict) -> bool:
    return params.get("tire_model", "linear") == "liftoff"


def tire_load_ratio(series: dict, params: dict) -> np.ndarray:
    """Loss of tire load / static tire load; +1 means the wheel is unloaded (lifting off).
    With the lift-off tire the load cannot go below zero, so the ratio is capped at 1."""
    ms, mu, _, _, kt = qc.unpack(params)
    r = kt * (series["zu_m"] - series["zr_m"]) / ((ms + mu) * qc.G)
    return np.minimum(r, 1.0) if liftoff(params) else r


def airborne_time(series: dict, params: dict) -> float:
    """Time with zero tire load [s], from the output grid (half-open samples)."""
    ms, mu, _, _, kt = qc.unpack(params)
    t = series["t_s"]
    compression = (ms + mu) * qc.G / kt + series["zr_m"] - series["zu_m"]
    return float(np.sum(compression[:-1] < 0) * (t[1] - t[0]))


def window_slice(t: np.ndarray, params: dict) -> slice:
    """Samples of the analysis window [t_end - window_s, t_end), endpoint excluded."""
    dt = t[1] - t[0]
    n_win = float(params["window_s"]) / dt
    if abs(n_win - round(n_win)) > 1e-6:
        raise ValueError("window_s must be an integer number of output steps")
    n_win = int(round(n_win))
    if n_win >= len(t):
        raise ValueError("window_s must be shorter than t_end_s")
    return slice(len(t) - 1 - n_win, len(t) - 1)


class ScipyQuarterCar(Backend):
    sources = ("models/quarter_car.py",)

    def solve(self, params, numerics, tolerance_scale=1.0):
        return qc.simulate(
            params, t_end_s=float(numerics["t_end_s"]), n_points=int(numerics["n_points"]),
            method=str(numerics["method"]), rtol=float(numerics["rtol"]) * tolerance_scale,
            atol=float(numerics["atol"]) * tolerance_scale)

    def tool_versions(self):
        import scipy
        return {"scipy": scipy.__version__}


class ModelicaQuarterCarBump(ModelicaBackend):
    source = "models/modelica/EngLab.mo"
    class_name = "EngLab.QuarterCarBump"
    param_names = ("sprung_mass_kg", "unsprung_mass_kg", "suspension_stiffness_N_per_m",
                   "damping_N_s_per_m", "tire_stiffness_N_per_m", "speed_m_per_s",
                   "bump_height_m", "bump_length_m")
    outputs = {"zs_m": "zs_m", "vs_m_per_s": "vs_m_per_s", "zu_m": "zu_m",
               "vu_m_per_s": "vu_m_per_s", "zr_m": "zr_m"}

    def solve(self, params, numerics, tolerance_scale=1.0):
        if params.get("road") != "bump":
            raise ValueError("quarter_car_modelica supports road = 'bump' only")
        return super().solve(params, numerics, tolerance_scale)


class QuarterCarStudy(Study):
    name = "quarter_car"
    models = {"quarter_car": ScipyQuarterCar, "quarter_car_modelica": ModelicaQuarterCarBump}
    metrics = frozenset(BUMP_METRICS | ROAD_METRICS | {"max_tire_lift_ratio", "airborne_time_ms"})
    param_names = qc.PARAMS
    compare_description = "max |z - z_other| / max |z| over body and wheel displacement"

    def derive(self, params):
        d = qc.derived(params)
        Road(params)  # validates road parameters
        d["slowest_decay_rate_per_s"] = ref.slowest_decay_rate(params)
        return d

    def compute_metrics(self, series, params, case, outputs=None):
        acc = body_accel(series, params)
        travel = series["zs_m"] - series["zu_m"]
        load = tire_load_ratio(series, params)
        m = {"max_tire_lift_ratio": float(np.max(load))}
        if liftoff(params):
            m["airborne_time_ms"] = 1e3 * airborne_time(series, params)
        if params["road"] == "bump":
            m.update(peak_body_accel_m_per_s2=float(np.max(np.abs(acc))),
                     max_suspension_travel_mm=1e3 * float(np.max(np.abs(travel))),
                     max_tire_load_ratio=float(np.max(np.abs(load))))
        else:
            w = window_slice(series["t_s"], params)
            rms = lambda a: float(np.sqrt(np.mean(a[w] ** 2)))  # noqa: E731
            m.update(body_accel_rms_m_per_s2=rms(acc),
                     suspension_travel_rms_mm=1e3 * rms(travel),
                     tire_load_rms_ratio=rms(load))
        return m

    def compare_point(self, case, params, a, b):
        scale = max(np.max(np.abs(a["zs_m"])), np.max(np.abs(a["zu_m"])), 1e-300)
        return float(max(np.max(np.abs(a["zs_m"] - b["zs_m"])),
                         np.max(np.abs(a["zu_m"] - b["zu_m"]))) / scale)

    # ------------------------------------------------------------------ checks
    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        params = point["parameters"]
        t = series["t_s"]
        ms, mu, ks, cs, kt = qc.unpack(params)
        road = Road(params)
        checks = []

        # Energy: E(T) - E(0) + dissipated = road work, with E(0) = 0 (start from rest)
        zs, vs, zu, vu, zr = (series[k] for k in ("zs_m", "vs_m_per_s", "zu_m", "vu_m_per_s",
                                                   "zr_m"))
        if liftoff(params):
            # absolute energies (gravity, preloaded springs), valid in contact and in the air:
            # the tire stores energy and transmits road work only while compressed
            W, s0 = (ms + mu) * qc.G, ms * qc.G / ks
            delta = np.maximum(W / kt + zr - zu, 0.0)

            def energy(i):
                return (0.5 * ms * vs[i] ** 2 + 0.5 * mu * vu[i] ** 2
                        + 0.5 * ks * (s0 - (zs[i] - zu[i])) ** 2 + 0.5 * kt * delta[i] ** 2
                        + qc.G * (ms * zs[i] + mu * zu[i]))
            energy_end, energy_0 = energy(-1), energy(0)
            p_road = kt * delta * np.asarray(road.vr(t), float)
        else:
            energy_end = (0.5 * ms * vs[-1] ** 2 + 0.5 * mu * vu[-1] ** 2
                          + 0.5 * ks * (zs[-1] - zu[-1]) ** 2 + 0.5 * kt * (zu[-1] - zr[-1]) ** 2)
            energy_0 = 0.5 * kt * (zu[0] - zr[0]) ** 2
            p_road = kt * (zr - zu) * np.asarray(road.vr(t), float)
        dissipated = simpson(cs * (vs - vu) ** 2, x=t)
        work = simpson(p_road, x=t)
        scale = simpson(np.abs(p_road), x=t)
        checks.append(check("energy_balance",
                            "|W_road - (dE + E_dissipated)| / integral |P_road| dt",
                            abs(work - (energy_end - energy_0) - dissipated) / scale,
                            tol["energy_residual_rel_tol"]))

        tight = backend.solve(params, case["numerics"], tolerance_scale=1e-2)
        if tight["success"]:
            change = self.compare_point(case, params, series, tight["series"])
        else:
            change = float("inf")
        checks.append(check("solver_convergence",
                            "max |z(tol) - z(tol/100)| / max |z| (body and wheel)",
                            change, tol["convergence_max_rel_change"]))

        if not liftoff(params):
            checks.append(check("no_wheel_lift",
                                "max dynamic tire load / static load (linear tire valid only < 1)",
                                point["metrics"]["max_tire_lift_ratio"], 1.0, kind="validity"))

        if params["road"] == "bump":
            checks += self._verify_bump(case, point, pdir, series, params)
        else:
            checks += self._verify_road(case, point, pdir, series, params)
        return checks

    def _verify_bump(self, case, point, pdir, series, params):
        tol = case["verification"]
        t = series["t_s"]
        h = float(params["bump_height_m"])
        r = ref.time_response_liftoff(params, t) if liftoff(params) else ref.time_response(params, t)
        err = max(np.max(np.abs(series["zs_m"] - r["zs_m"])),
                  np.max(np.abs(series["zu_m"] - r["zu_m"]))) / h
        np.savetxt(pdir / "reference.csv",
                   np.column_stack([t, r["zs_m"], r["vs_m_per_s"], r["zu_m"], r["vu_m_per_s"]]),
                   delimiter=",", header="t_s,zs_ref_m,vs_ref_m_per_s,zu_ref_m,vu_ref_m_per_s",
                   comments="", fmt="%.15e")
        ref_series = dict(r, zr_m=series["zr_m"], t_s=t)
        acc_ref = body_accel(ref_series, params)
        peak_ref = float(np.max(np.abs(acc_ref)))
        rest = max(abs(series["zs_m"][-1]), abs(series["zu_m"][-1])) / h

        reqs = {rq["metric"]: rq["limit"] for rq in case["requirements"]}
        quarter_car_bump_figure(
            pdir / "response.png", t, body_accel(series, params), acc_ref,
            1e3 * (series["zs_m"] - series["zu_m"]), tire_load_ratio(series, params),
            1e3 * series["zr_m"],
            accel_limit=reqs.get("peak_body_accel_m_per_s2"),
            travel_limit_mm=reqs.get("max_suspension_travel_mm"),
            load_limit=reqs.get("max_tire_load_ratio"),
            title=f"{point['label']}  (c = {params['damping_N_s_per_m']:g} N·s/m)")
        extra = []
        if liftoff(params):
            got = (point.get("solver_outputs") or {}).get("tire_events", [])
            want = r["events"]
            same = len(got) == len(want) and all(a[1] == b[1] for a, b in zip(got, want))
            dt_ev = max((abs(a[0] - b[0]) for a, b in zip(got, want)), default=0.0) if same else float("inf")
            extra.append(check("contact_event_times",
                               "max |t_event model - t_event exact| [s] over lift-offs and touchdowns "
                               f"({len(want)} events; sequence must match)",
                               dt_ev, tol["event_time_tol_s"]))
        return extra + [
            check("reference_agreement",
                  "max |z_num - z_ref| / bump height (body and wheel; matrix-exponential ref)",
                  err, tol["reference_max_rel_error"]),
            check("peak_accel_reference",
                  "|peak accel num - peak accel ref| / peak accel ref",
                  abs(point["metrics"]["peak_body_accel_m_per_s2"] - peak_ref) / peak_ref,
                  tol["peak_metric_rel_tol"]),
            check("return_to_rest",
                  "max(|zs(t_end)|, |zu(t_end)|) / bump height",
                  rest, tol["rest_rel_tol"]),
        ]

    def _verify_road(self, case, point, pdir, series, params):
        tol = case["verification"]
        t = series["t_s"]
        expected = ref.steady_state_rms(params)
        m = point["metrics"]
        settle = t[-1] - float(params["window_s"])
        decay = float(np.exp(-ref.slowest_decay_rate(params) * settle))

        acc = body_accel(series, params)
        w = window_slice(t, params)
        road = Road(params)
        h = ref.frequency_response(params, road.sines.freq_hz)
        quarter_car_road_figure(
            pdir / "response.png", t[w], acc[w], road.sines.freq_hz,
            np.abs(h["body_accel"]) * road.sines.amp_m,
            title=f"{point['label']}  (c = {params['damping_N_s_per_m']:g} N·s/m)")

        checks = [check(f"{k}_reference",
                        f"|{k} num - closed-form| / closed-form",
                        abs(m[k] - expected[k]) / expected[k], tol["rms_rel_tol"])
                  for k in ("body_accel_rms_m_per_s2", "suspension_travel_rms_mm",
                            "tire_load_rms_ratio")]
        checks.append(check("transient_decayed",
                            "exp(-sigma_min * settle time): start-up transient left in window",
                            decay, tol["transient_max_fraction"]))
        return checks


STUDY = QuarterCarStudy()

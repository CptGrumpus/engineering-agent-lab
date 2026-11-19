"""Independent checks on a completed run.

Checks per point:
  1. reference_agreement - numerical x(t) vs closed-form solution
  2. overshoot_reference - numerical overshoot vs closed-form overshoot formula
  3. settling_reference  - numerical settling time vs settling time of the analytical curve
  4. steady_state        - x(t_end) vs F/k (proves the simulation ran long enough)
  5. energy_balance      - work in = kinetic + potential + dissipated energy
  6. solver_convergence  - rerun with tolerances tightened 100x; solution must not move

Tolerances come from the case file's [verification] section, written before
the first run. A FAIL is reported, never suppressed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.integrate import trapezoid

from harness.case import load_case
from harness.metrics import step_metrics
from harness.plotting import plot_response
from harness.backends import get_backend, sha256_file
from harness.runio import close_logger, get_logger, read_json, read_timeseries, write_json
from validation import msd_analytical as ref


def _check(cid: str, description: str, value: float, tolerance: float) -> dict:
    ok = bool(np.isfinite(value) and value <= tolerance)
    return {
        "id": cid,
        "description": description,
        "value": float(value),
        "tolerance": float(tolerance),
        "comparison": "<=",
        "status": "PASS" if ok else "FAIL",
    }


def verify_point(case: dict, point: dict, pdir: Path, backend) -> list[dict]:
    tol = case["verification"]
    band = float(case["metrics"]["settling_band_fraction"])
    t, x, v = read_timeseries(pdir / "timeseries.csv")

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
        _check("reference_agreement",
               "max |x_num - x_ref| / (F/k) over the full time history",
               np.max(np.abs(x - x_ref)) / abs(xs), tol["reference_max_rel_error"]),
        _check("overshoot_reference",
               "|overshoot_num - overshoot_closed_form| in percentage points",
               abs(metrics["overshoot_pct"] - ref.overshoot_pct(m, c, k)),
               tol["overshoot_abs_tol_pct"]),
        _check("settling_reference",
               "|settling_num - settling of analytical curve| in s",
               abs(metrics["settling_time_s"] - ref_metrics["settling_time_s"]),
               tol["settling_time_abs_tol_s"]),
        _check("steady_state",
               "|x(t_end) - F/k| / (F/k)",
               abs(x[-1] - xs) / abs(xs), tol["steady_state_rel_tol"]),
    ]

    # Energy: F*x_end = 1/2 m v_end^2 + 1/2 k x_end^2 + integral(c v^2 dt)
    work_in = f * x[-1]
    stored = 0.5 * m * v[-1] ** 2 + 0.5 * k * x[-1] ** 2
    dissipated = trapezoid(c * v**2, t)
    checks.append(_check("energy_balance",
                         "|W_in - (KE + PE + E_dissipated)| / W_in",
                         abs(work_in - stored - dissipated) / abs(work_in),
                         tol["energy_residual_rel_tol"]))

    _, tight = backend.solve(params, case["numerics"], tolerance_scale=1e-2)
    if tight["success"]:
        change = np.max(np.abs(tight["x"] - x)) / abs(xs)
    else:
        change = float("inf")
    checks.append(_check("solver_convergence",
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


def verify_run(run_dir: str | Path) -> dict:
    run_dir = Path(run_dir)
    case, _, digest = load_case(run_dir / "inputs" / "case.toml")
    manifest = read_json(run_dir / "manifest.json")
    if digest != manifest["case_sha256"]:
        raise RuntimeError("inputs/case.toml no longer matches the hash recorded in manifest.json")
    for rel, digest_src in manifest.get("model_sources_sha256", {}).items():
        if sha256_file(run_dir / "inputs" / Path(rel).name) != digest_src:
            raise RuntimeError(f"inputs/{Path(rel).name} no longer matches manifest.json")

    log = get_logger(run_dir, "verify")
    summary = {
        "run_id": manifest["run_id"],
        "verified_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tolerances": case["verification"],
        "points": [],
    }
    backend = get_backend(case["case"]["model"])
    prepare_error = None
    if any(p["status"] == "completed" for p in manifest["points"]):
        try:
            backend.prepare(source_dir=run_dir / "inputs" if backend.sources else None)
        except Exception as e:
            prepare_error = f"backend prepare failed: {type(e).__name__}: {e}"
            log.error("%s", prepare_error)
    for point in manifest["points"]:
        pdir = run_dir / "points" / point["label"]
        if point["status"] != "completed":
            entry = {"label": point["label"], "status": "NOT_RUN",
                     "reason": f"simulation status '{point['status']}'", "checks": []}
            log.warning("%s: not verified (%s)", point["label"], entry["reason"])
        elif prepare_error:
            entry = {"label": point["label"], "status": "ERROR", "reason": prepare_error,
                     "checks": []}
        else:
            try:
                checks = verify_point(case, point, pdir, backend)
                status = "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL"
                entry = {"label": point["label"], "status": status, "checks": checks}
                for c in checks:
                    log.info("%s: %-20s %s  value %.3e  tol %.1e", point["label"], c["id"],
                             c["status"], c["value"], c["tolerance"])
            except Exception as e:
                entry = {"label": point["label"], "status": "ERROR",
                         "reason": f"{type(e).__name__}: {e}", "checks": []}
                log.exception("%s: verification error", point["label"])
        write_json(pdir / "checks.json", entry)
        summary["points"].append(entry)

    backend.close()
    statuses = {p["status"] for p in summary["points"]}
    summary["status"] = "PASS" if statuses == {"PASS"} else "FAIL"
    write_json(run_dir / "verification.json", summary)
    log.info("verification %s: %s", run_dir.name, summary["status"])
    close_logger(log)
    return summary

"""Cross-tool check: compare two runs of the same physical case, point by point.

Two independent implementations (e.g. SciPy equations vs an OpenModelica
component model) agreeing within tolerance is evidence that neither contains
a modelling or set-up error the other lacks. It does not replace the analytical
reference check; it adds a second, tool-level line of evidence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from harness.case import load_case
from harness.runio import read_json, read_timeseries, write_json

METRIC_KEYS = ("overshoot_pct", "settling_time_s", "static_deflection_mm")


def compare_runs(run_dir: str | Path, against_dir: str | Path) -> dict:
    """Compare run_dir against against_dir. Tolerance from run_dir's [cross_check]."""
    run_dir, against_dir = Path(run_dir), Path(against_dir)
    case, _, _ = load_case(run_dir / "inputs" / "case.toml")
    xc = case.get("cross_check")
    if not xc:
        raise ValueError(f"{run_dir}/inputs/case.toml has no [cross_check] section")
    tol = float(xc["max_rel_diff"])

    ma, mb = read_json(run_dir / "manifest.json"), read_json(against_dir / "manifest.json")
    if mb["case_name"] != xc["against_case"]:
        raise ValueError(f"[cross_check] expects case '{xc['against_case']}', "
                         f"but {against_dir.name} is case '{mb['case_name']}'")
    b_points = {p["label"]: p for p in mb["points"]}

    points = []
    for pa in ma["points"]:
        pb = b_points.get(pa["label"])
        entry = {"label": pa["label"]}
        if pb is None:
            entry.update(status="FAIL", reason="point missing in comparison run")
        elif pa["parameters"] != pb["parameters"]:
            entry.update(status="FAIL", reason="parameters differ between runs")
        elif pa["status"] != "completed" or pb["status"] != "completed":
            entry.update(status="NOT_RUN", reason="a simulation did not complete")
        else:
            ta, xa, _ = read_timeseries(run_dir / "points" / pa["label"] / "timeseries.csv")
            tb, xb, _ = read_timeseries(against_dir / "points" / pb["label"] / "timeseries.csv")
            xs = pa["parameters"]["step_force_N"] / pa["parameters"]["stiffness_N_per_m"]
            if ta.shape != tb.shape or not np.allclose(ta, tb, rtol=0, atol=1e-12):
                xb = np.interp(ta, tb, xb)
                entry["note"] = "time grids differ; comparison run interpolated"
            diff = float(np.max(np.abs(xa - xb)) / abs(xs))
            entry.update(
                max_rel_diff=diff, tolerance=tol, status="PASS" if diff <= tol else "FAIL",
                metrics={k: {"run": pa["metrics"][k], "against": pb["metrics"][k],
                             "diff": pa["metrics"][k] - pb["metrics"][k]} for k in METRIC_KEYS},
            )
        points.append(entry)

    def model_of(manifest, rdir):  # older manifests did not record the model
        return manifest.get("model") or load_case(rdir / "inputs" / "case.toml")[0]["case"]["model"]

    result = {
        "run": ma["run_id"], "model": model_of(ma, run_dir),
        "against": mb["run_id"], "against_model": model_of(mb, against_dir),
        "compared_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tolerance": tol, "points": points,
        "status": "PASS" if all(p["status"] == "PASS" for p in points) else "FAIL",
    }
    write_json(run_dir / f"cross_check_{mb['run_id']}.json", result)
    return result

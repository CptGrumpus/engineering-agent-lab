"""Execute a case: one simulation per sweep point, saving all evidence to runs/."""

from __future__ import annotations

import traceback
from datetime import datetime, timezone
from pathlib import Path

from harness.case import expand_points, load_case
from harness.metrics import step_metrics
from harness.runio import close_logger, environment, get_logger, write_json, write_timeseries
from models.msd import MSDParameters, simulate


def solve_point(params: dict, numerics: dict, tolerance_scale: float = 1.0) -> tuple[MSDParameters, dict]:
    p = MSDParameters.from_dict(params)
    result = simulate(
        p,
        t_end_s=float(numerics["t_end_s"]),
        n_points=int(numerics["n_points"]),
        method=str(numerics["method"]),
        rtol=float(numerics["rtol"]) * tolerance_scale,
        atol=float(numerics["atol"]) * tolerance_scale,
    )
    return p, result


def _new_run_dir(runs_root: Path, case_name: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = runs_root / f"{stamp}_{case_name}"
    n = 1
    while run_dir.exists():
        run_dir = runs_root / f"{stamp}-{n}_{case_name}"
        n += 1
    return run_dir


def run_case(case_path: str | Path, runs_root: str | Path = "runs", rerun_of: str | None = None) -> Path:
    """Run every point of a case. Returns the new run directory.

    Failed points are kept (status 'failed' with the error recorded) rather than
    aborting the run, so failures remain available as diagnostic evidence.
    """
    case, raw, digest = load_case(case_path)
    run_dir = _new_run_dir(Path(runs_root), case["case"]["name"])
    (run_dir / "inputs").mkdir(parents=True)
    (run_dir / "inputs" / "case.toml").write_bytes(raw)

    log = get_logger(run_dir, "run")
    started = datetime.now(timezone.utc)
    log.info("run %s: case %s (sha256 %s)", run_dir.name, case_path, digest[:12])

    manifest = {
        "run_id": run_dir.name,
        "case_name": case["case"]["name"],
        "case_source": Path(case_path).as_posix(),
        "case_sha256": digest,
        "rerun_of": rerun_of,
        "started_utc": started.isoformat(timespec="seconds"),
        "environment": environment(),
        "numerics": case["numerics"],
        "points": [],
    }

    for label, params in expand_points(case):
        pdir = run_dir / "points" / label
        pdir.mkdir(parents=True)
        entry = {"label": label, "parameters": params, "status": "failed"}
        try:
            p, res = solve_point(params, case["numerics"])
            entry["derived"] = p.derived()
            entry["solver"] = {k: res[k] for k in ("success", "message", "nfev")}
            if not res["success"]:
                log.error("%s: solver failed: %s", label, res["message"])
            else:
                write_timeseries(pdir / "timeseries.csv", res["t"], res["x"], res["v"])
                entry["metrics"] = step_metrics(
                    res["t"], res["x"], float(case["metrics"]["settling_band_fraction"])
                )
                entry["status"] = "completed"
                m = entry["metrics"]
                log.info("%s: overshoot %.3f %%, settling %.4f s, deflection %.4f mm (nfev %d)",
                         label, m["overshoot_pct"], m["settling_time_s"], m["static_deflection_mm"],
                         res["nfev"])
        except Exception as e:  # keep going; the failure is evidence
            entry["error"] = f"{type(e).__name__}: {e}"
            log.error("%s: exception\n%s", label, traceback.format_exc())
        write_json(pdir / "point.json", entry)
        manifest["points"].append(entry)

    n_ok = sum(pt["status"] == "completed" for pt in manifest["points"])
    manifest["status"] = "completed" if n_ok == len(manifest["points"]) else (
        "partial" if n_ok else "failed")
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    write_json(run_dir / "manifest.json", manifest)
    log.info("run %s: %s (%d/%d points completed)", run_dir.name, manifest["status"], n_ok,
             len(manifest["points"]))
    close_logger(log)
    return run_dir

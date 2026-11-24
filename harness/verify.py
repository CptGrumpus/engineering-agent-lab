"""Independent checks on a completed run.

The checks themselves belong to each study (studies/<name>.py, verify_point).
This module handles integrity of the saved inputs, backend setup, failure
recording, and the run-level summary.

Tolerances come from the case file's [verification] section, written before
the first run. A FAIL is reported, never suppressed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from harness.backend_base import sha256_file
from harness.case import load_case
from harness.registry import resolve
from harness.runio import close_logger, get_logger, read_json, read_series, write_json


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
    study, backend = resolve(case["case"]["model"])
    prepare_error = None
    if any(p["status"] == "completed" for p in manifest["points"]):
        try:
            backend.prepare(source_dir=run_dir / "inputs")
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
                series = read_series(pdir / study.series_file)
                checks = study.verify_point(case, point, pdir, series, backend)
                status = "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL"
                entry = {"label": point["label"], "status": status, "checks": checks}
                for c in checks:
                    log.info("%s: %-24s %s  value %.3e  tol %.1e", point["label"], c["id"],
                             c["status"], c["value"], c["tolerance"])
            except Exception as e:
                entry = {"label": point["label"], "status": "ERROR",
                         "reason": f"{type(e).__name__}: {e}", "checks": []}
                log.exception("%s: verification error", point["label"])
        write_json(pdir / "checks.json", entry)
        summary["points"].append(entry)

    backend.close()
    try:
        run_checks, detail = study.verify_run_level(case, manifest, summary["points"])
    except Exception as e:
        log.exception("run-level verification error")
        run_checks, detail = [{"id": "run_level_error", "description": f"{type(e).__name__}: {e}",
                               "kind": "numerical", "value": float("inf"), "tolerance": 0.0,
                               "comparison": "<=", "status": "FAIL"}], {}
    if run_checks or detail:   # detail without checks (e.g. a sweep's interpolated limits) is kept too
        summary["run_checks"] = run_checks
        summary["run_check_detail"] = detail
        for c in run_checks:
            log.info("run-level: %-28s %s  value %.3e  tol %.1e", c["id"], c["status"],
                     c["value"], c["tolerance"])
    opt = manifest.get("optimization")
    if opt:
        # an optimisation run: rejected candidates are the checks doing their job (they were
        # infeasible to the optimiser); the run stands on the optimum and the run-level checks
        best = next((p for p in summary["points"] if p["label"] == opt.get("best_label")), None)
        summary["optimum"] = opt.get("best_label")
        summary["rejected_candidates"] = [p["label"] for p in summary["points"] if p["status"] != "PASS"]
        statuses = {best["status"] if best else "FAIL"}
    else:
        statuses = {p["status"] for p in summary["points"]}
    statuses |= {c["status"] for c in run_checks}
    summary["status"] = "PASS" if statuses == {"PASS"} else "FAIL"
    write_json(run_dir / "verification.json", summary)
    log.info("verification %s: %s", run_dir.name, summary["status"])
    close_logger(log)
    return summary

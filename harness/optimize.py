"""Design optimisation loop: an optimiser proposes designs, and each candidate is built, meshed,
solved and checked exactly like a point of an ordinary case.

    python -m harness optimize cases/<name>.toml

The case file has the usual sections plus [optimization]:

    [optimization]
    method = "COBYLA"                 # scipy.optimize, derivative-free, handles constraints
    objective = "mass_g"              # study metric to minimise
    design_margin = 0.005             # constraints use limit x (1 - margin), reserving room for
                                      # discretisation error (the optimum sits on a constraint)
    rhobeg = 2.0                      # initial step (units of the variables)
    tol = 0.01                        # final trust-region radius
    max_evaluations = 80
    [[optimization.variables]]
    name = "root_height_mm"           # a [parameters] entry; its value there is the start
    lower = 10.0
    upper = 40.0

The constraints are the case's requirements. Every candidate is a point under
runs/<run>/points/c###, with its own evidence, metrics and checks (checks.json). A candidate
that fails any check is unverified and counts as infeasible, whatever its metrics say, so the
optimiser cannot be steered by a result the checks have rejected. The optimum reported is
the best verified, feasible candidate, never an unverified one. Mesh convergence at the
optimum and the comparison with an independent optimum are a separate confirmation case.
"""

from __future__ import annotations

import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from harness.backend_base import sha256_file
from harness.case import OPERATORS, CaseError, load_case
from harness.registry import resolve
from harness.run import _new_run_dir, execute_point
from harness.runio import close_logger, environment, get_logger, read_series, write_json


def _constraint_values(metrics: dict, requirements: list, margin: float) -> list[float]:
    """g >= 0 when satisfied with the design margin; normalised by the limit."""
    g = []
    for r in requirements:
        lim, v = float(r["limit"]), float(metrics[r["metric"]])
        if r["operator"] in ("<=", "<"):
            g.append((lim * (1 - margin) - v) / abs(lim))
        else:
            g.append((v - lim * (1 + margin)) / abs(lim))
    return g


def optimize_case(case_path: str | Path, runs_root: str | Path = "runs") -> Path:
    from scipy.optimize import minimize

    case, raw, digest = load_case(case_path)
    opt = case.get("optimization")
    if not opt:
        raise CaseError(f"{case_path}: no [optimization] section")
    variables = opt["variables"]
    names = [v["name"] for v in variables]
    unknown = [n for n in names if n not in case["parameters"]]
    if unknown:
        raise CaseError(f"{case_path}: optimisation variables not in [parameters]: {unknown}")
    if opt.get("method", "COBYLA") != "COBYLA":
        raise CaseError("only method = 'COBYLA' is supported")
    margin = float(opt.get("design_margin", 0.0))
    reqs = case["requirements"]
    for r in reqs:
        if r["operator"] not in OPERATORS:
            raise CaseError(f"bad operator in {r['id']}")

    run_dir = _new_run_dir(Path(runs_root), case["case"]["name"])
    inputs = run_dir / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "case.toml").write_bytes(raw)
    log = get_logger(run_dir, "run")
    started = datetime.now(timezone.utc)
    log.info("optimisation %s: case %s (sha256 %s)", run_dir.name, case_path, digest[:12])
    manifest = {"run_id": run_dir.name, "case_name": case["case"]["name"], "model": case["case"]["model"],
                "case_source": Path(case_path).as_posix(), "case_sha256": digest,
                "model_sources_sha256": {}, "rerun_of": None,
                "started_utc": started.isoformat(timespec="seconds"), "environment": environment(),
                "numerics": case["numerics"], "points": []}
    study, backend = resolve(case["case"]["model"])
    manifest["study"] = study.name
    try:
        if not opt.get("objective") in study.metrics:
            raise CaseError(f"objective {opt.get('objective')!r} is not a metric of {study.name}")
        for rel in backend.sources:
            dst = inputs / Path(rel).name
            shutil.copyfile(backend.source_path(rel, None), dst)
            manifest["model_sources_sha256"][rel] = sha256_file(dst)
        backend.prepare(source_dir=inputs, log_dir=run_dir / "build")
        manifest["environment"]["tools"] = backend.tool_versions()
    except Exception as e:
        log.error("backend prepare failed\n%s", traceback.format_exc())
        manifest["prepare_error"] = f"{type(e).__name__}: {e}"
        manifest["status"] = "failed"
        write_json(run_dir / "manifest.json", manifest)
        close_logger(log)
        return run_dir

    history: list[dict] = []
    cache: dict = {}
    n_ineq = len(reqs)

    def evaluate(x):
        x = np.clip(np.asarray(x, float), [v["lower"] for v in variables], [v["upper"] for v in variables])
        key = tuple(round(float(v), 9) for v in x)
        if key in cache:
            return cache[key]
        params = dict(case["parameters"])
        params.update({n: float(v) for n, v in zip(names, x)})
        label = f"c{len(manifest['points']):03d}"
        entry = execute_point(study, backend, case, label, params, run_dir, log)
        verified, failed_checks = False, []
        if entry["status"] == "completed":
            pdir = run_dir / "points" / label
            try:
                checks = study.verify_point(case, entry, pdir, read_series(pdir / study.series_file), backend)
                failed_checks = [c["id"] for c in checks if c["status"] != "PASS"]
                verified = not failed_checks
                write_json(pdir / "checks.json", {"label": label, "status": "PASS" if verified else "FAIL",
                                                  "checks": checks})
            except Exception as e:
                failed_checks = [f"verification error: {type(e).__name__}: {e}"]
                log.exception("%s: verification error", label)
        if verified:
            obj = float(entry["metrics"][opt["objective"]])
            g = _constraint_values(entry["metrics"], reqs, margin)
        else:                                     # an unverified candidate is infeasible
            obj = float(entry.get("metrics", {}).get(opt["objective"], np.inf))
            g = [-1.0] * n_ineq
        entry["candidate"] = {"variables": dict(zip(names, map(float, x))), "verified": verified,
                              "failed_checks": failed_checks, "objective": obj, "constraints": g,
                              "feasible": verified and min(g) >= 0}
        manifest["points"].append(entry)
        history.append({"label": label, **entry["candidate"]})
        log.info("%s: %s = %.4f, constraints %s, %s", label, opt["objective"], obj,
                 ", ".join(f"{v:+.4f}" for v in g), "verified" if verified else f"UNVERIFIED {failed_checks}")
        cache[key] = (obj, g)
        return cache[key]

    x0 = np.array([float(case["parameters"][n]) for n in names])
    obj0 = evaluate(x0)[0]
    scale = obj0 if np.isfinite(obj0) and obj0 != 0 else 1.0
    cons = [{"type": "ineq", "fun": (lambda x, i=i: evaluate(x)[1][i])} for i in range(n_ineq)]
    try:
        res = minimize(lambda x: evaluate(x)[0] / scale, x0, method="COBYLA", constraints=cons,
                       bounds=[(v["lower"], v["upper"]) for v in variables],
                       options={"rhobeg": float(opt.get("rhobeg", 1.0)), "tol": float(opt.get("tol", 1e-3)),
                                "maxiter": int(opt.get("max_evaluations", 100)), "catol": 0.0})
        result = {"message": str(res.message), "success": bool(res.success), "x": list(map(float, res.x))}
    except Exception as e:
        log.error("optimiser failed\n%s", traceback.format_exc())
        result = {"message": f"{type(e).__name__}: {e}", "success": False}
    backend.close()

    feasible = [h for h in history if h["feasible"]]
    best = min(feasible, key=lambda h: h["objective"]) if feasible else None
    manifest["optimization"] = {
        "objective": opt["objective"], "variables": variables, "design_margin": margin,
        "optimizer": result, "evaluations": len(history),
        "unverified_candidates": [h["label"] for h in history if not h["verified"]],
        "history": history,
        "best_label": best["label"] if best else None,
        "best_variables": best["variables"] if best else None,
        "best_objective": best["objective"] if best else None,
    }
    if best:
        log.info("optimum %s: %s, %s = %.4f", best["label"],
                 ", ".join(f"{k} {v:.4f}" for k, v in best["variables"].items()), opt["objective"], best["objective"])
    n_ok = sum(pt["status"] == "completed" for pt in manifest["points"])
    manifest["status"] = "completed" if best and n_ok == len(manifest["points"]) else ("partial" if best else "failed")
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    write_json(run_dir / "manifest.json", manifest)
    fig = getattr(study, "optimization_figure", None)
    if fig:
        try:
            fig(run_dir / "optimization.png", case, manifest)
        except Exception:
            log.exception("optimisation figure failed")
    log.info("optimisation %s: %s (%d candidates, %d unverified)", run_dir.name, manifest["status"],
             len(history), len(manifest["optimization"]["unverified_candidates"]))
    close_logger(log)
    return run_dir

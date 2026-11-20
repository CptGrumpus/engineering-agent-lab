"""Execute a case: one simulation per sweep point, saving all evidence to runs/."""

from __future__ import annotations

import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path

from harness.backend_base import REPO, sha256_file
from harness.case import expand_points, load_case
from harness.registry import resolve
from harness.runio import close_logger, environment, get_logger, write_json, write_series


def _new_run_dir(runs_root: Path, case_name: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = runs_root / f"{stamp}_{case_name}"
    n = 1
    while run_dir.exists():
        run_dir = runs_root / f"{stamp}-{n}_{case_name}"
        n += 1
    return run_dir


def _fmt_metrics(m: dict) -> str:
    return ", ".join(f"{k} {v:.4g}" for k, v in m.items())


def run_case(case_path: str | Path, runs_root: str | Path = "runs", rerun_of: str | None = None,
             model_source_dir: Path | None = None) -> Path:
    """Run every point of a case. Returns the new run directory.

    model_source_dir: read model sources from here instead of the repo (used by
    rerun so a reproduction uses the exact saved model files).

    Failed points are kept (status 'failed' with the error recorded) rather than
    aborting the run, so failures remain available as diagnostic evidence.
    """
    case, raw, digest = load_case(case_path)
    run_dir = _new_run_dir(Path(runs_root), case["case"]["name"])
    inputs = run_dir / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "case.toml").write_bytes(raw)

    log = get_logger(run_dir, "run")
    started = datetime.now(timezone.utc)
    log.info("run %s: case %s (sha256 %s)", run_dir.name, case_path, digest[:12])

    manifest = {
        "run_id": run_dir.name,
        "case_name": case["case"]["name"],
        "model": case["case"]["model"],
        "case_source": Path(case_path).as_posix(),
        "case_sha256": digest,
        "model_sources_sha256": {},
        "rerun_of": rerun_of,
        "started_utc": started.isoformat(timespec="seconds"),
        "environment": environment(),
        "numerics": case["numerics"],
        "points": [],
    }

    prepared = False
    backend = None
    try:
        study, backend = resolve(case["case"]["model"])
        manifest["study"] = study.name
        for rel in backend.sources:
            src = backend.source_path(rel, model_source_dir)
            if model_source_dir and src.parent != Path(model_source_dir).resolve():
                log.warning("no saved copy of %s in %s; using repository version", rel,
                            model_source_dir)
            dst = inputs / Path(rel).name
            shutil.copyfile(src, dst)
            manifest["model_sources_sha256"][rel] = sha256_file(dst)
        backend.prepare(source_dir=inputs, log_dir=run_dir / "build")
        manifest["environment"]["tools"] = backend.tool_versions()
        prepared = True
    except Exception as e:
        log.error("backend prepare failed\n%s", traceback.format_exc())
        manifest["prepare_error"] = f"{type(e).__name__}: {e}"

    for label, params in expand_points(case):
        pdir = run_dir / "points" / label
        pdir.mkdir(parents=True)
        entry = {"label": label, "parameters": params, "status": "failed"}
        try:
            if not prepared:
                raise RuntimeError("backend preparation failed; see prepare_error")
            entry["derived"] = study.derive(params)
            res = backend.solve(params, case["numerics"])
            entry["solver"] = {k: res[k] for k in ("success", "message", "nfev")}
            if res.get("outputs"):
                entry["solver_outputs"] = res["outputs"]
            if res.get("files"):  # solver decks, logs, native model files
                (pdir / "solver").mkdir()
                for name, src in res["files"].items():  # name may contain subfolders
                    (pdir / "solver" / name).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, pdir / "solver" / name)
            if res.get("cleanup"):
                shutil.rmtree(res["cleanup"], ignore_errors=True)
            if not res["success"]:
                log.error("%s: solver failed: %s", label, res["message"])
            else:
                write_series(pdir / study.series_file, res["series"])
                entry["metrics"] = study.compute_metrics(res["series"], params, case,
                                                         res.get("outputs") or {})
                entry["status"] = "completed"
                log.info("%s: %s", label, _fmt_metrics(entry["metrics"]))
        except Exception as e:  # keep going; the failure is evidence
            entry["error"] = f"{type(e).__name__}: {e}"
            log.error("%s: exception\n%s", label, traceback.format_exc())
        write_json(pdir / "point.json", entry)
        manifest["points"].append(entry)
    if backend is not None:
        backend.close()

    n_ok = sum(pt["status"] == "completed" for pt in manifest["points"])
    manifest["status"] = "completed" if n_ok == len(manifest["points"]) else (
        "partial" if n_ok else "failed")
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    write_json(run_dir / "manifest.json", manifest)
    log.info("run %s: %s (%d/%d points completed)", run_dir.name, manifest["status"], n_ok,
             len(manifest["points"]))
    close_logger(log)
    return run_dir

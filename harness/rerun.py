"""Reproduce a run from its saved inputs and compare the results."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from harness.run import run_case
from harness.runio import read_json, read_timeseries, write_json


def rerun(run_dir: str | Path, rel_tol: float = 1e-12) -> tuple[Path, dict]:
    """Rerun from <run_dir>/inputs/case.toml into a new run dir; compare per point.

    The tolerance covers floating-point noise only; on the same machine and
    package versions the results are expected to be bit-identical.
    """
    old = Path(run_dir)
    old_manifest = read_json(old / "manifest.json")
    new = run_case(old / "inputs" / "case.toml", runs_root=old.parent, rerun_of=old.name)
    new_manifest = read_json(new / "manifest.json")

    env_diff = {
        k: (old_manifest["environment"].get(k), new_manifest["environment"].get(k))
        for k in ("python", "packages", "platform")
        if old_manifest["environment"].get(k) != new_manifest["environment"].get(k)
    }

    points = []
    for p_old, p_new in zip(old_manifest["points"], new_manifest["points"], strict=True):
        entry = {"label": p_old["label"]}
        f_old = old / "points" / p_old["label"] / "timeseries.csv"
        f_new = new / "points" / p_new["label"] / "timeseries.csv"
        if not (f_old.exists() and f_new.exists()):
            entry.update(status="FAIL", reason="time series missing in one of the runs")
        else:
            _, x_old, _ = read_timeseries(f_old)
            _, x_new, _ = read_timeseries(f_new)
            scale = max(np.max(np.abs(x_old)), 1e-300)
            diff = float(np.max(np.abs(x_old - x_new)) / scale) if x_old.shape == x_new.shape else float("inf")
            entry.update(max_rel_diff=diff, tolerance=rel_tol,
                         bit_identical=f_old.read_bytes() == f_new.read_bytes(),
                         status="PASS" if diff <= rel_tol else "FAIL")
        points.append(entry)

    result = {
        "original_run": old.name,
        "rerun": new.name,
        "environment_differences": env_diff,
        "points": points,
        "status": "PASS" if all(p["status"] == "PASS" for p in points) else "FAIL",
    }
    write_json(new / "reproducibility.json", result)
    return new, result

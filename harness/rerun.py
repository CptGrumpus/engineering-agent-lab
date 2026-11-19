"""Reproduce a run from its saved inputs and compare the results."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from harness.registry import study_for
from harness.run import run_case
from harness.runio import read_json, read_series, write_json


def rerun(run_dir: str | Path, rel_tol: float = 1e-12) -> tuple[Path, dict]:
    """Rerun from <run_dir>/inputs into a new run dir; compare every series column.

    The tolerance covers floating-point noise only; on the same machine and
    package versions the results are expected to be bit-identical.
    """
    old = Path(run_dir)
    old_manifest = read_json(old / "manifest.json")
    new = run_case(old / "inputs" / "case.toml", runs_root=old.parent, rerun_of=old.name,
                   model_source_dir=old / "inputs")
    new_manifest = read_json(new / "manifest.json")
    series_file = study_for(new_manifest["model"]).series_file

    env_diff = {
        k: (old_manifest["environment"].get(k), new_manifest["environment"].get(k))
        for k in ("python", "packages", "platform", "tools")
        if old_manifest["environment"].get(k) != new_manifest["environment"].get(k)
    }

    points = []
    for p_old, p_new in zip(old_manifest["points"], new_manifest["points"], strict=True):
        entry = {"label": p_old["label"]}
        f_old = old / "points" / p_old["label"] / series_file
        f_new = new / "points" / p_new["label"] / series_file
        if not (f_old.exists() and f_new.exists()):
            entry.update(status="FAIL", reason="result series missing in one of the runs")
        else:
            a, b = read_series(f_old), read_series(f_new)
            diffs = []
            for col in a:
                if col not in b or a[col].shape != b[col].shape:
                    diffs.append(float("inf"))
                    continue
                scale = max(np.max(np.abs(a[col])), 1e-300)
                diffs.append(float(np.max(np.abs(a[col] - b[col])) / scale))
            diff = max(diffs) if diffs else float("inf")
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

"""Run-directory I/O: environment capture, logging, JSON and time-series files."""

from __future__ import annotations

import importlib.metadata
import json
import logging
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np

TIMESERIES_HEADER = "t_s,x_m,v_m_per_s"


def environment() -> dict:
    pkgs = {}
    for name in ("numpy", "scipy", "matplotlib"):
        try:
            pkgs[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pkgs[name] = None
    return {
        "python": sys.version.split()[0],
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "packages": pkgs,
        "git": _git_state(),
    }


def _git_state() -> dict:
    def git(*args):
        r = subprocess.run(["git", *args], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else None

    try:
        commit = git("rev-parse", "HEAD")
        status = git("status", "--porcelain")
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "dirty": None}
    return {"commit": commit, "dirty": bool(status) if status is not None else None}


def get_logger(run_dir: Path, name: str) -> logging.Logger:
    """Logger writing to <run_dir>/run.log (appending) and to stdout."""
    logger = logging.getLogger(f"harness.{run_dir.name}.{name}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    fh = logging.FileHandler(run_dir / "run.log", encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def close_logger(logger: logging.Logger) -> None:
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, default=_json_default) + "\n", encoding="utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _json_default(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, Path):
        return o.as_posix()
    raise TypeError(f"not JSON serializable: {type(o)}")


def write_timeseries(path: Path, t, x, v) -> None:
    np.savetxt(path, np.column_stack([t, x, v]), delimiter=",", header=TIMESERIES_HEADER,
               comments="", fmt="%.15e")


def read_timeseries(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    data = np.loadtxt(path, delimiter=",", skiprows=1)
    return data[:, 0], data[:, 1], data[:, 2]

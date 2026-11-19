"""Backend base classes shared by all studies.

A backend turns (parameters, numerics) into a result dict:

    {"success": bool, "message": str, "nfev": int | None,
     "series": {column_name: np.ndarray, ...} | None}

Time-domain backends return series on np.linspace(0, t_end_s, n_points).
"""

from __future__ import annotations

import glob
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def failed(message: str) -> dict:
    return {"success": False, "message": message, "nfev": None, "series": None}


class Backend:
    #: model source files (repo-relative) copied into run inputs and hashed
    sources: tuple[str, ...] = ()

    def prepare(self, source_dir: Path | None = None, log_dir: Path | None = None) -> None:
        """One-time setup (e.g. compile). source_dir: where to read saved sources."""

    def solve(self, params: dict, numerics: dict, tolerance_scale: float = 1.0) -> dict:
        raise NotImplementedError

    def tool_versions(self) -> dict:
        return {}

    def close(self) -> None:
        pass

    def source_path(self, rel: str, source_dir: Path | None) -> Path:
        if source_dir and (Path(source_dir) / Path(rel).name).exists():
            return (Path(source_dir) / Path(rel).name).resolve()
        return (REPO / rel).resolve()


# --------------------------------------------------------------------------- Modelica

class ModelicaError(RuntimeError):
    pass


def find_omc() -> Path:
    home = os.environ.get("OPENMODELICAHOME")
    candidates = [Path(home) / "bin" / "omc.exe"] if home else []
    candidates += [Path(p) for p in sorted(glob.glob("C:/Program Files/OpenModelica*/bin/omc.exe"),
                                           reverse=True)]
    which = shutil.which("omc")
    if which:
        candidates.append(Path(which))
    for c in candidates:
        if c.exists():
            return c
    raise ModelicaError("omc not found: install OpenModelica or set OPENMODELICAHOME")


class ModelicaBackend(Backend):
    """Compile a Modelica class once with omc; run the executable once per point.

    Parameters are passed with -overrideFile. Experiment settings use dedicated
    flags (-stopTime, -stepSize, -tolerance, -s): OpenModelica 1.26 silently
    ignores them inside an override.
    """

    source = ""                      # repo-relative .mo file
    class_name = ""
    param_names: tuple[str, ...] = ()
    outputs: dict[str, str] = {}     # Modelica variable -> series column
    time_column = "t_s"
    msl_version = "4.1.0"

    def __init__(self):
        self.omc = find_omc()
        self.build_dir: Path | None = None
        self.exe: Path | None = None
        self._versions: dict = {}
        self._count = 0

    @property
    def sources(self):  # type: ignore[override]
        return (self.source,)

    def extra_overrides(self, params: dict, numerics: dict) -> dict:
        """Hook for studies that pass more than scalar parameters (e.g. arrays)."""
        return {}

    def prepare(self, source_dir=None, log_dir=None):
        src = self.source_path(self.source, source_dir)
        if not src.exists():
            raise ModelicaError(f"model source not found: {src}")
        self.build_dir = Path(tempfile.mkdtemp(prefix="omc_build_"))
        vfilter = "|".join(re.escape(v) for v in self.outputs)
        script = (
            f'loadModel(Modelica, {{"{self.msl_version}"}}); getErrorString();\n'
            f'getVersion(Modelica);\n'
            f'loadFile("{src.as_posix()}"); getErrorString();\n'
            f'buildModel({self.class_name}, method="dassl", outputFormat="csv", '
            f'variableFilter="{vfilter}"); getErrorString();\n'
        )
        (self.build_dir / "build.mos").write_text(script, encoding="utf-8")
        r = subprocess.run([str(self.omc), "build.mos"], cwd=self.build_dir,
                           capture_output=True, text=True, timeout=900)
        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
            (log_dir / "build.mos").write_text(script, encoding="utf-8")
            (log_dir / "omc_build.log").write_text(r.stdout + r.stderr, encoding="utf-8")
        exe = self.build_dir / f"{self.class_name}.exe"
        if r.returncode != 0 or not exe.exists():
            raise ModelicaError(f"omc build failed (exit {r.returncode}):\n{r.stdout[-2000:]}")
        self.exe = exe
        lines = [ln.strip().strip('"') for ln in r.stdout.splitlines()]
        msl = next((ln for ln in lines if ln and ln[0].isdigit()), None)
        ver = subprocess.run([str(self.omc), "--version"], capture_output=True, text=True)
        self._versions = {"omc": ver.stdout.strip(), "Modelica Standard Library": msl}

    def solve(self, params, numerics, tolerance_scale=1.0):
        if self.exe is None:
            raise ModelicaError("prepare() must be called before solve()")
        t_end = float(numerics["t_end_s"])
        n = int(numerics["n_points"])
        self._count += 1
        overrides = {name: float(params[name]) for name in self.param_names}
        overrides.update(self.extra_overrides(params, numerics))
        ofile = self.build_dir / f"override_{self._count}.txt"
        ofile.write_text("\n".join(f"{k}={v!r}" for k, v in overrides.items()) + "\n",
                         encoding="utf-8")
        result_file = self.build_dir / f"res_{self._count}.csv"
        env = dict(os.environ)
        env["PATH"] = str(self.omc.parent) + os.pathsep + env.get("PATH", "")
        r = subprocess.run(
            [str(self.exe), f"-overrideFile={ofile}", "-startTime=0",
             f"-stopTime={t_end!r}", f"-stepSize={t_end / (n - 1)!r}",
             f"-tolerance={float(numerics['rtol']) * tolerance_scale!r}",
             f"-s={numerics['method']}", "-noEventEmit", f"-r={result_file}"],
            cwd=self.build_dir, capture_output=True, text=True, env=env, timeout=1800)
        message = (r.stdout + r.stderr).strip()
        if r.returncode != 0 or not result_file.exists():
            return failed(message or f"exit code {r.returncode}")

        data = np.genfromtxt(result_file, delimiter=",", names=True)
        t = np.asarray(data["time"], dtype=float)
        dt = t_end / (n - 1)
        idx = np.rint(t / dt).astype(int)
        on_grid = np.abs(t - idx * dt) <= 1e-9 * max(t_end, 1.0)
        # keep the last row for each grid index (handles repeated rows at events/end)
        series = {self.time_column: np.linspace(0.0, t_end, n)}
        keep = {}
        for row, (ok, i) in enumerate(zip(on_grid, idx)):
            if ok and 0 <= i < n:
                keep[i] = row
        if len(keep) != n:
            return failed(f"output grid mismatch: got {len(keep)} grid points, expected {n} "
                          f"on linspace(0, {t_end}, {n})")
        rows = np.array([keep[i] for i in range(n)])
        for var, col in self.outputs.items():
            series[col] = np.asarray(data[_genfromtxt_name(var)], dtype=float)[rows]
        return {"success": True, "message": message.splitlines()[-1] if message else "",
                "nfev": None, "series": series}

    def tool_versions(self):
        return self._versions

    def close(self):
        if self.build_dir and self.build_dir.exists():
            shutil.rmtree(self.build_dir, ignore_errors=True)
        self.build_dir = self.exe = None


def _genfromtxt_name(var: str) -> str:
    """np.genfromtxt(names=True) replaces characters such as '.' or '[' in headers."""
    return re.sub(r"[^A-Za-z0-9_]", "", var.replace(".", "_"))

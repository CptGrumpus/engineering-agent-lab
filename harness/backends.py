"""Model backends: one interface, several tools.

A backend turns (parameters, numerics) into a time series t, x, v on the grid
np.linspace(0, t_end_s, n_points). Every backend uses the same parameter
names, so verification and reporting do not depend on which tool ran.

    msd            SciPy solve_ivp           models/msd.py
    msd_modelica   OpenModelica (omc, MSL)   models/modelica/EngLab.mo
"""

from __future__ import annotations

import glob
import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from models.msd import MSDParameters, simulate

REPO = Path(__file__).resolve().parent.parent
PARAM_NAMES = ("mass_kg", "stiffness_N_per_m", "damping_ratio", "step_force_N")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Backend:
    name = ""
    #: model source files, relative to the repo root; copied into run inputs
    sources: tuple[str, ...] = ()

    def prepare(self, source_dir: Path | None = None, log_dir: Path | None = None) -> None:
        """One-time setup (e.g. compile). source_dir overrides where sources are read."""

    def solve(self, params: dict, numerics: dict, tolerance_scale: float = 1.0
              ) -> tuple[MSDParameters, dict]:
        raise NotImplementedError

    def tool_versions(self) -> dict:
        return {}

    def close(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class ScipyMSD(Backend):
    name = "msd"
    sources = ("models/msd.py",)

    def solve(self, params, numerics, tolerance_scale=1.0):
        p = MSDParameters.from_dict(params)
        res = simulate(
            p,
            t_end_s=float(numerics["t_end_s"]),
            n_points=int(numerics["n_points"]),
            method=str(numerics["method"]),
            rtol=float(numerics["rtol"]) * tolerance_scale,
            atol=float(numerics["atol"]) * tolerance_scale,
        )
        return p, res

    def tool_versions(self):
        import scipy
        return {"scipy": scipy.__version__}


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


class ModelicaMSD(Backend):
    """Compile EngLab.MSDStep once with omc, then run the executable per point
    with -override (parameters, stopTime, stepSize, tolerance, solver)."""

    name = "msd_modelica"
    sources = ("models/modelica/EngLab.mo",)
    class_name = "EngLab.MSDStep"
    msl_version = "4.1.0"

    def __init__(self):
        self.omc = find_omc()
        self.build_dir: Path | None = None
        self.exe: Path | None = None
        self._versions: dict = {}
        self._count = 0

    def prepare(self, source_dir=None, log_dir=None):
        src = Path(source_dir or REPO) / (
            Path(self.sources[0]).name if source_dir else self.sources[0])
        src = src.resolve()  # omc runs in the build dir, so the path must be absolute
        if not src.exists():
            raise ModelicaError(f"model source not found: {src}")
        self.build_dir = Path(tempfile.mkdtemp(prefix="omc_build_"))
        script = (
            f'loadModel(Modelica, {{"{self.msl_version}"}}); getErrorString();\n'
            f'getVersion(Modelica);\n'
            f'loadFile("{src.as_posix()}"); getErrorString();\n'
            f'buildModel({self.class_name}, method="dassl", outputFormat="csv", '
            f'variableFilter="x_m|v_m_per_s"); getErrorString();\n'
        )
        (self.build_dir / "build.mos").write_text(script, encoding="utf-8")
        r = subprocess.run([str(self.omc), "build.mos"], cwd=self.build_dir,
                           capture_output=True, text=True, timeout=600)
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
        p = MSDParameters.from_dict(params)  # validates inputs, gives derived values
        t_end = float(numerics["t_end_s"])
        n = int(numerics["n_points"])
        # Model parameters go through -override. Experiment settings must use their
        # dedicated flags: OpenModelica 1.26 silently ignores them inside -override.
        overrides = ",".join(f"{name}={float(params[name])!r}" for name in PARAM_NAMES)
        self._count += 1
        result_file = self.build_dir / f"res_{self._count}.csv"
        env = dict(os.environ)
        env["PATH"] = str(self.omc.parent) + os.pathsep + env.get("PATH", "")
        r = subprocess.run(
            [str(self.exe), f"-override={overrides}",
             "-startTime=0", f"-stopTime={t_end!r}", f"-stepSize={t_end / (n - 1)!r}",
             f"-tolerance={float(numerics['rtol']) * tolerance_scale!r}",
             f"-s={numerics['method']}", f"-r={result_file}"],
            cwd=self.build_dir, capture_output=True, text=True, env=env, timeout=600)
        message = (r.stdout + r.stderr).strip()
        fail = {"t": None, "x": None, "v": None, "success": False, "message": message,
                "nfev": None}
        if r.returncode != 0 or not result_file.exists():
            return p, fail

        data = np.genfromtxt(result_file, delimiter=",", names=True)
        t = np.asarray(data["time"], dtype=float)
        keep = np.concatenate([[True], np.diff(t) > 0])  # OM repeats the final time row
        t, x, v = t[keep], data["x_m"][keep], data["v_m_per_s"][keep]
        grid = np.linspace(0.0, t_end, n)
        if t.shape != grid.shape or not np.allclose(t, grid, rtol=0, atol=1e-9 * t_end):
            fail["message"] = (f"output grid mismatch: got {t.size} points, expected {n} "
                               f"on linspace(0, {t_end}, {n})")
            return p, fail
        return p, {"t": grid, "x": np.asarray(x, float), "v": np.asarray(v, float),
                   "success": True, "message": message.splitlines()[-1] if message else "",
                   "nfev": None}

    def tool_versions(self):
        return self._versions

    def close(self):
        if self.build_dir and self.build_dir.exists():
            shutil.rmtree(self.build_dir, ignore_errors=True)
        self.build_dir = self.exe = None


BACKENDS = {"msd": ScipyMSD, "msd_modelica": ModelicaMSD}


def get_backend(model: str) -> Backend:
    try:
        return BACKENDS[model]()
    except KeyError:
        raise ValueError(f"unsupported model {model!r}; supported: {sorted(BACKENDS)}") from None

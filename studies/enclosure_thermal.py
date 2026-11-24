"""Study 11, stage 3: a sealed electronics enclosure (2D section), conjugate heat transfer with internal radiation.

Model:     openfoam_enclosure_cht (models/cfd/enclosure_openfoam.py, models/cfd/run_enclosure.sh): OpenFOAM 14
           foamMultiRun, regions fluid (air, laminar natural convection, fvDOM radiation), board and component
           (solid, heat sources), run transient to a settled state.
Metrics:   the hottest component temperature (C), the mean air temperature (C), the walls' mean temperature, the share
           of the walls' inside heat that arrives by radiation.
Reference: the heat balance at the end (heat leaving the walls to the ambient, from the walls' own temperatures and
           the boundary condition's law, against the input power); settling (the component's maximum over the last
           tenth of the run); the verified stage-1 and stage-2 models (cavity convection, grey-surface radiation).
Run-level: none (the corners are a bracket, not a refinement); a mesh check is a separate two-level case.
"""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness import openfoam as of
from harness.backend_base import Backend, failed
from harness.checks import check
from harness.study import Study

WRITER = "models/cfd/enclosure_openfoam.py"
RUNNER = "models/cfd/run_enclosure.sh"
SIGMA = 5.670374419e-8


def _load_writer(path: Path):
    spec = importlib.util.spec_from_file_location("enclosure_openfoam_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_W = _load_writer(Path(__file__).resolve().parent.parent / WRITER)


class OpenFOAMEnclosure(Backend):
    sources = (WRITER, RUNNER)

    def __init__(self):
        self.bashrc = of.find_openfoam_bashrc()
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        self.writer = _load_writer(self.source_path(WRITER, source_dir))
        self.runner = self.source_path(RUNNER, source_dir)

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="enclosure_"))
        case = work / "case"

        def files():
            keep = [case / n for n in ("log.blockMesh", "log.splitMeshRegions", "log.checkMesh", "versions.txt")]
            keep += sorted((case / "system").rglob("*")) + sorted((case / "constant").glob("*/*"))
            return {str(f.relative_to(case)).replace("\\", "/"): f for f in keep
                    if f.is_file() and f.stat().st_size < 20e6 and "polyMesh" not in f.parts}

        try:
            info = self.writer.write_case(params, numerics, case)
            r = subprocess.run(of.wsl_command("bash", of.to_wsl_path(self.runner), of.to_wsl_path(case), self.bashrc),
                               capture_output=True, text=True, timeout=float(numerics.get("solver_timeout_s", 21600)))
            if r.returncode != 0:
                res = failed(f"enclosure run failed (exit {r.returncode}) {r.stderr.strip()[-300:]}")
                res.update(files=files(), cleanup=work)
                return res
            times = sorted((d for d in case.iterdir() if d.is_dir() and d.name not in ("0", "constant", "system")
                            and d.name.replace(".", "").isdigit()), key=lambda d: float(d.name))
            Ta = float(params["ambient_C"]) + 273.15
            h, ee = float(params["h_ext_W_m2K"]), float(params["eps_ext"])
            hist = []
            for t in times:
                Tc = of.read_internal_field(t / "component" / "T")
                Tb = of.read_internal_field(t / "board" / "T")
                Tf = of.read_internal_field(t / "fluid" / "T")
                Tw = of.read_patch_value(t / "fluid" / "T", "walls")
                qout = h * (Tw - Ta) + ee * SIGMA * (Tw ** 4 - Ta ** 4)          # equal wall faces (uniform mesh)
                qr = of.read_patch_value(t / "fluid" / "qr", "walls")
                hist.append({"t": float(t.name), "component_max_C": float(Tc.max()) - 273.15,
                             "board_max_C": float(Tb.max()) - 273.15, "air_mean_C": float(Tf.mean()) - 273.15,
                             "walls_mean_C": float(Tw.mean()) - 273.15, "q_out_W_m2": float(qout.mean()),
                             "qr_walls_W_m2": float(qr.mean())})
            for line in (case / "versions.txt").read_text(encoding="utf-8").splitlines():
                k, _, v = line.partition("=")
                self._versions[k] = v
        except Exception as e:  # noqa: BLE001
            res = failed(f"{type(e).__name__}: {e}")
            res.update(files=files(), cleanup=work)
            return res
        lay = self.writer.layout(params)
        q_in = (float(params["power_component_W"]) + float(params["power_board_W"])) / (
            2 * (lay["W"] + lay["H"]) * float(params["box_depth_mm"]) / 1e3)
        series = {k: np.array([hh[k] for hh in hist]) for k in hist[0]}
        outputs = {**info, "q_in_W_m2": q_in, "history": hist, "final": hist[-1]}
        return {"success": True, "message": f"enclosure: component {hist[-1]['component_max_C']:.2f} C", "nfev": None,
                "series": series, "outputs": outputs, "files": files(), "cleanup": work}

    def tool_versions(self):
        return dict(self._versions)


class EnclosureThermalStudy(Study):
    name = "enclosure_thermal"
    models = {"openfoam_enclosure_cht": OpenFOAMEnclosure}
    metrics = frozenset({"component_max_C", "air_mean_C", "walls_mean_C", "radiation_share_pct"})
    param_names = _W.PARAMS
    series_file = "history.csv"
    compare_description = "max relative difference in the temperature histories"

    def compute_metrics(self, series, params, case, outputs=None):
        f = outputs["final"]
        q_in = outputs["q_in_W_m2"]
        return {"component_max_C": f["component_max_C"], "air_mean_C": f["air_mean_C"],
                "walls_mean_C": f["walls_mean_C"], "radiation_share_pct": 100 * f["qr_walls_W_m2"] / q_in}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        out = point["solver_outputs"]
        hist = out["history"]
        n = max(2, len(hist) // 10)
        drift = abs(hist[-1]["component_max_C"] - hist[-1 - max(1, n - 1)]["component_max_C"])
        return [
            check("heat_balance", "|heat leaving the walls to the ambient - input power| / input, at the end",
                  abs(out["final"]["q_out_W_m2"] - out["q_in_W_m2"]) / out["q_in_W_m2"], tol["heat_balance_rel_tol"]),
            check("settled", "change of the component's maximum over the last tenth of the run (K)", drift,
                  tol["settled_K"]),
        ]


STUDY = EnclosureThermalStudy()

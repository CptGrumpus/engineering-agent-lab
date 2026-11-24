"""Study 11, stage 2: grey-surface radiation between long concentric cylinders, OpenFOAM fvDOM, against the exact
two-surface exchange; the conduction through the (transparent, still) gas against the exact log-mean solution.

Model:     openfoam_annulus_radiation (models/cfd/annulus_radiation_openfoam.py, models/cfd/run_annulus.sh).
Metrics:   radiated and conducted heat per metre from the inner cylinder, and their deviations from the exact values.
           Radiation from fvDOM's wall flux qr; conduction from the temperature field, the conserved flux across the
           face between the two mid-gap rings of cells (the wall gradient is first order in the solver).
Reference: validation/natural_convection.py (two-surface exchange; conduction 2 pi k dT / ln(r2 / r1));
           radiation balance inner against outer wall.
Run-level: convergence in the number of directions (n_phi) when it is the sweep: the uncertainty of the radiated heat.
"""

from __future__ import annotations

import importlib.util
import math
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness import openfoam as of
from harness.backend_base import Backend, failed
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study
from validation import natural_convection as ref

WRITER = "models/cfd/annulus_radiation_openfoam.py"
RUNNER = "models/cfd/run_annulus.sh"


def _load_writer(path: Path):
    spec = importlib.util.spec_from_file_location("annulus_radiation_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_W = _load_writer(Path(__file__).resolve().parent.parent / WRITER)


def exact(params: dict) -> dict:
    r1, r2, T1, T2 = (float(params[k]) for k in ("r_inner_m", "r_outer_m", "T_inner_K", "T_outer_K"))
    return {"radiation": ref.concentric_cylinders_per_length(T1, T2, float(params["eps_inner"]),
                                                             float(params["eps_outer"]), r1, r2),
            "conduction": 2 * math.pi * _W.conductivity() * (T1 - T2) / math.log(r2 / r1)}


class OpenFOAMAnnulus(Backend):
    sources = (WRITER, RUNNER)

    def __init__(self):
        self.bashrc = of.find_openfoam_bashrc()
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        self.writer = _load_writer(self.source_path(WRITER, source_dir))
        self.runner = self.source_path(RUNNER, source_dir)

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="annulus_"))
        case = work / "case"

        def files():
            keep = [case / n for n in ("log.blockMesh", "log.checkMesh", "log.foamRun", "versions.txt")]
            keep += sorted((case / "system").glob("*")) + sorted((case / "constant").glob("*"))
            return {str(f.relative_to(case)).replace("\\", "/"): f for f in keep if f.is_file() and f.stat().st_size < 20e6}

        try:
            info = self.writer.write_case(params, numerics, case)
            r = subprocess.run(of.wsl_command("bash", of.to_wsl_path(self.runner), of.to_wsl_path(case), self.bashrc),
                               capture_output=True, text=True, timeout=float(numerics.get("solver_timeout_s", 7200)))
            if r.returncode != 0:
                res = failed(f"annulus run failed (exit {r.returncode}) {r.stderr.strip()[-300:]}")
                res.update(files=files(), cleanup=work)
                return res
            t = of.latest_time_dir(case)
            r1, r2 = float(params["r_inner_m"]), float(params["r_outer_m"])
            qi, qo = of.read_patch_value(t / "qr", "inner"), of.read_patch_value(t / "qr", "outer")
            Q_in, Q_out = -float(qi.mean()) * 2 * math.pi * r1, float(qo.mean()) * 2 * math.pi * r2
            C, T = of.read_internal_field(t / "C"), of.read_internal_field(t / "T")
            # one ring of cells sits at one radius only to about 1e-8 m (faceted arcs): bin at 0.1 um
            rr = np.round(np.hypot(C[:, 0], C[:, 1]), 7)
            rs = np.unique(rr)
            # conduction: the solver's own conserved flux across the face between the two mid-gap rings (no source, so
            # the same through every ring; a central difference there is second order, while the wall gradient is not)
            m = len(rs) // 2
            ra, rb = rs[m - 1], rs[m]
            Ta, Tb = float(np.mean(T[rr == ra])), float(np.mean(T[rr == rb]))
            Q_cond = _W.conductivity() * (Ta - Tb) / (rb - ra) * 2 * math.pi * (ra + rb) / 2
            log = (case / "log.foamRun").read_text(encoding="utf-8", errors="replace")
            h_res = re.findall(r"Solving for h, Initial residual = ([-+0-9.eE]+)", log)
            for line in (case / "versions.txt").read_text(encoding="utf-8").splitlines():
                k, _, v = line.partition("=")
                self._versions[k] = v
        except Exception as e:  # noqa: BLE001
            res = failed(f"{type(e).__name__}: {e}")
            res.update(files=files(), cleanup=work)
            return res
        series = {"r_m": rs, "T_K": np.array([float(np.mean(T[rr == v])) for v in rs])}
        outputs = {**info, "radiation_inner_W_per_m": Q_in, "radiation_outer_W_per_m": Q_out,
                   "conduction_W_per_m": Q_cond, "qr_inner_spread": float((qi.max() - qi.min()) / abs(qi.mean())),
                   "h_final_residual": float(h_res[-1]) if h_res else 1.0}
        return {"success": True, "message": f"annulus: radiation {Q_in:.3f} W/m", "nfev": None,
                "series": series, "outputs": outputs, "files": files(), "cleanup": work}

    def tool_versions(self):
        return dict(self._versions)


class AnnulusRadiationStudy(Study):
    name = "annulus_radiation"
    models = {"openfoam_annulus_radiation": OpenFOAMAnnulus}
    metrics = frozenset({"radiation_W_per_m", "conduction_W_per_m", "radiation_deviation_pct",
                         "conduction_deviation_pct"})
    param_names = _W.PARAMS
    series_file = "temperature_profile.csv"
    compare_description = "max relative difference in the radial temperature profile"

    def derive(self, params):
        if not 0 < float(params["r_inner_m"]) < float(params["r_outer_m"]):
            raise ValueError("0 < r_inner < r_outer")
        return exact(params)

    def compute_metrics(self, series, params, case, outputs=None):
        e = exact(params)
        Qr, Qc = outputs["radiation_inner_W_per_m"], outputs["conduction_W_per_m"]
        return {"radiation_W_per_m": Qr, "conduction_W_per_m": Qc,
                "radiation_deviation_pct": 100 * abs(Qr - e["radiation"]) / e["radiation"],
                "conduction_deviation_pct": 100 * abs(Qc - e["conduction"]) / e["conduction"]}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        out = point["solver_outputs"]
        Qi, Qo = out["radiation_inner_W_per_m"], out["radiation_outer_W_per_m"]
        return [
            check("radiation_balance", "|radiation leaving the inner wall - reaching the outer| / leaving",
                  abs(Qi - Qo) / abs(Qi), tol["balance_rel_tol"]),
            check("conduction_exact", "|conducted heat - 2 pi k dT / ln(r2 / r1)| / exact (no flow, transparent gas)",
                  point["metrics"]["conduction_deviation_pct"] / 100, tol["conduction_rel_tol"]),
            check("converged", "final initial residual of h", out["h_final_residual"], tol["residual_max"]),
        ]

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "n_phi":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: -float(pt["parameters"]["n_phi"]))
        if len(done) < 3:
            return [check("angular_convergence", "needs >= 3 completed angular levels", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(1.0 / float(pt["parameters"]["n_phi"]) for pt in fine)
        u = discretization_uncertainty(hs, tuple(pt["metrics"]["radiation_W_per_m"] for pt in fine))
        return ([check("discretization_radiation", f"angular discretization uncertainty of the radiated heat, "
                       f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": "radiation_deviation_pct"}],
                {"meshes_used": [pt["label"] for pt in fine], "radiation_W_per_m": u})


STUDY = AnnulusRadiationStudy()

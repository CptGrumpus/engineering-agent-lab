"""Study: side-wall effect on laminar channel flow (OpenFOAM 3D, run in WSL).

Model:     openfoam_duct  (models/cfd/duct_openfoam.py writes a periodic quarter
           cross-section; models/cfd/run_channel.sh runs it)
Reference: exact series solution for fully developed laminar flow in a
           rectangular duct (validation/channel_flow.py)
Run-level: Grid Convergence Index over the three finest meshes, when the sweep
           parameter is cells_across_gap

Purpose: quantify the error of the 2D (infinitely wide) assumption used by the
channel_flow study. The requirement is on that error, not on the design.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness import openfoam as of
from harness.backend_base import Backend, failed
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.plotting import duct_figure
from harness.study import Study
from validation import channel_flow as ref

WRITER = "models/cfd/duct_openfoam.py"
RUNNER = "models/cfd/run_channel.sh"
_GRAD = re.compile(r"Pressure gradient source: uncorrected Ubar = ([-+0-9.eE]+), "
                   r"pressure gradient = ([-+0-9.eE]+)")


def _load_writer(path: Path):
    spec = importlib.util.spec_from_file_location("duct_openfoam_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _p(params, k):
    return float(params[k])


PARAMS = _load_writer(Path(__file__).resolve().parent.parent / WRITER).PARAMS


class OpenFOAMDuct(Backend):
    sources = (WRITER, RUNNER)

    def __init__(self):
        self.bashrc = of.find_openfoam_bashrc()
        self._versions: dict = {"openfoam_bashrc": self.bashrc}

    def prepare(self, source_dir=None, log_dir=None):
        self.writer = _load_writer(self.source_path(WRITER, source_dir))
        self.runner = self.source_path(RUNNER, source_dir)

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="of_duct_"))
        case = work / "case"
        info = self.writer.write_case(params, numerics, case)
        r = subprocess.run(of.wsl_command("bash", of.to_wsl_path(self.runner),
                                          of.to_wsl_path(case), self.bashrc),
                           capture_output=True, text=True, timeout=7200)
        files = {str(f.relative_to(case)).replace("\\", "/"): f
                 for f in sorted(case.glob("system/*")) + sorted(case.glob("constant/*"))
                 + sorted(case.glob("0/*")) + sorted(case.glob("log.*"))
                 + sorted(case.glob("versions.txt")) if f.is_file()}
        if r.returncode != 0:
            res = failed(f"OpenFOAM stage failed (exit {r.returncode}) {r.stderr.strip()[:300]}")
            res.update(files=files, cleanup=work)
            return res
        for line in (case / "versions.txt").read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition("=")
            self._versions[k] = v
        log_text = (case / "log.foamRun").read_text(encoding="utf-8", errors="replace")
        grads = _GRAD.findall(log_text)
        if not grads:
            return failed("meanVelocityForce reported no pressure gradient")
        ubar, grad = (float(v) for v in grads[-1])
        # iterative convergence of the quantity of interest: change of the gradient
        # over the last 10 % of iterations (the constraint prints twice per iteration)
        hist = np.array([float(g) for _, g in grads])
        tail = hist[-max(2, len(hist) // 10):]
        grad_change = float(np.max(np.abs(tail - hist[-1])) / abs(hist[-1]))
        log = of.read_solver_log(case / "log.foamRun")
        tdir = of.latest_time_dir(case)
        n = info["cells"]
        C = of.read_internal_field(tdir / "C", n)
        Uf = of.read_internal_field(tdir / "U", n)
        series = {"x_mm": C[:, 0] * 1e3, "y_mm": C[:, 1] * 1e3, "z_mm": C[:, 2] * 1e3,
                  "ux_m_per_s": Uf[:, 0], "uy_m_per_s": Uf[:, 1], "uz_m_per_s": Uf[:, 2]}
        rho = _p(params, "density_kg_per_m3")
        outputs = {"cells": n, "nx": info["nx"], "ny": info["ny"], "nz": info["nz"],
                   "mesh_ok": "Mesh OK." in (case / "log.checkMesh").read_text(encoding="utf-8"),
                   "iterations": log["iterations"], "ended": log["ended"],
                   "final_initial_residuals": log["final_initial_residuals"],
                   "pressure_gradient_change_last_10pct": grad_change,
                   "pressure_gradient_Pa_per_m": grad * rho, "mean_velocity_reported": ubar,
                   "result_time": tdir.name}
        msg = (f"foamRun: {log['iterations']} iterations, {n} cells, gradient change over "
               f"last 10 %: {grad_change:.2e}")
        return {"success": True, "message": msg, "nfev": log["iterations"], "series": series,
                "outputs": outputs, "files": files, "cleanup": work}

    def tool_versions(self):
        return self._versions


def exact_field(series, params, G):
    """Exact u at the cell centres (G = -dp/dx in Pa/m)."""
    H, W = _p(params, "gap_mm") * 1e-3, _p(params, "width_mm") * 1e-3
    Y = series["y_mm"] * 1e-3 - H / 2      # plate at y = 0 -> Y = -a
    Z = series["z_mm"] * 1e-3 - W / 2      # side wall at z = 0 -> Z = -b
    return ref.duct_velocity(Y, Z, G, H, W, _p(params, "dynamic_viscosity_Pa_s"))


class DuctFlowStudy(Study):
    name = "duct_flow"
    models = {"openfoam_duct": OpenFOAMDuct}
    metrics = frozenset({"pressure_gradient_Pa_per_m", "side_wall_effect"})
    param_names = PARAMS
    series_file = "cells.csv"
    compare_description = "max relative difference over cell columns"

    def derive(self, params):
        H, W = _p(params, "gap_mm") * 1e-3, _p(params, "width_mm") * 1e-3
        U, rho, mu = (_p(params, k) for k in ("mean_velocity_m_per_s", "density_kg_per_m3",
                                              "dynamic_viscosity_Pa_s"))
        if min(H, U, rho, mu) <= 0 or W < H:
            raise ValueError("positive dimensions and properties; width >= gap")
        g2 = ref.pressure_gradient(U, H, mu)
        g3 = ref.duct_pressure_gradient(U, H, W, mu)
        return {"aspect_ratio_W_over_H": W / H,
                "reynolds_Dh_parallel_plates": ref.reynolds(U, H, rho, mu),
                "pressure_gradient_2D_Pa_per_m": g2,
                "pressure_gradient_exact_Pa_per_m": g3,
                "side_wall_effect_exact": g3 / g2 - 1.0}

    def compute_metrics(self, series, params, case, outputs=None):
        g2 = ref.pressure_gradient(_p(params, "mean_velocity_m_per_s"), _p(params, "gap_mm") * 1e-3,
                                   _p(params, "dynamic_viscosity_Pa_s"))
        g = outputs["pressure_gradient_Pa_per_m"]
        return {"pressure_gradient_Pa_per_m": g, "side_wall_effect": g / g2 - 1.0}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        p, d, m, out = (point["parameters"], point["derived"], point["metrics"],
                        point["solver_outputs"])
        U = _p(p, "mean_velocity_m_per_s")
        # Uy, Uz and p are exactly zero / uniform in fully developed flow, so their
        # normalised residuals are round-off noise; convergence is judged on Ux, the
        # pressure gradient history, and the cross-flow magnitude instead
        ux_res = out["final_initial_residuals"].get("Ux", np.inf)
        cross = float(max(np.max(np.abs(series["uy_m_per_s"])),
                          np.max(np.abs(series["uz_m_per_s"]))) / U)
        u_ex = exact_field(series, p, d["pressure_gradient_exact_Pa_per_m"])
        field_err = float(np.max(np.abs(series["ux_m_per_s"] - u_ex)) / np.max(u_ex))
        # cells are periodic in x: their volume-weighted mean must equal the target
        H, W = _p(p, "gap_mm"), _p(p, "width_mm")
        checks = [
            check("mesh_quality", "checkMesh result (0 = Mesh OK)", 0.0 if out["mesh_ok"] else 1.0,
                  0.0),
            check("ux_residual", "final initial residual of Ux (inf if the run did not end)",
                  ux_res if out["ended"] else np.inf, tol["ux_residual_max"]),
            check("pressure_gradient_converged",
                  "max relative change of -dp/dx over the last 10 % of iterations",
                  out["pressure_gradient_change_last_10pct"], tol["gradient_change_max"]),
            check("no_cross_flow", "max(|u_y|, |u_z|) / U_mean (exactly 0 for fully developed flow)",
                  cross, tol["cross_flow_max"]),
            check("mean_velocity", "|U_mean reported by meanVelocityForce - target| / target",
                  abs(out["mean_velocity_reported"] - U) / U, tol["mean_velocity_rel_tol"]),
            check("pressure_gradient_reference",
                  "|(-dp/dx)_CFD - exact rectangular-duct series| / exact",
                  abs(m["pressure_gradient_Pa_per_m"] - d["pressure_gradient_exact_Pa_per_m"])
                  / d["pressure_gradient_exact_Pa_per_m"], tol["pressure_gradient_rel_tol"]),
            check("velocity_field_reference", "max |u_CFD - u_exact| / u_max over all cells",
                  field_err, tol["velocity_rel_tol"]),
            check("laminar", "Re_Dh (parallel plates, conservative) / laminar limit",
                  d["reynolds_Dh_parallel_plates"] / tol["laminar_reynolds_max"], 1.0,
                  kind="validity"),
        ]
        duct_figure(pdir / "response.png", series, p, d, m, u_ex,
                    title=f"{point['label']}  ({out['cells']} cells, quarter section, "
                          f"W/H = {W / H:g})")
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "cells_across_gap":
            return [], {}
        tol = case["verification"]
        done = [pt for pt in manifest["points"] if pt["status"] == "completed"]
        done.sort(key=lambda pt: -int(pt["parameters"]["cells_across_gap"]))
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels",
                          float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(1.0 / int(pt["parameters"]["cells_across_gap"]) for pt in fine)
        metric = "pressure_gradient_Pa_per_m"
        u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine),
                                           design_order=2)  # second-order scheme / elements
        detail = {"meshes_used": [pt["label"] for pt in fine], metric: u}
        return [check(f"discretization_{metric}",
                      f"relative discretization uncertainty of {metric}, {describe(u)}",
                      u["uncertainty"], tol["gci_max"]) | {"metric": metric}], detail


STUDY = DuctFlowStudy()

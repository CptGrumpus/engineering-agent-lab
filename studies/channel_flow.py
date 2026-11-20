"""Study: laminar flow between parallel plates (OpenFOAM, run in WSL).

Model:     openfoam_channel  (models/cfd/channel_openfoam.py writes the case,
           models/cfd/run_channel.sh runs blockMesh, checkMesh, foamRun)
Reference: exact plane Poiseuille solution in the fully developed region;
           Shah & London apparent-friction correlation for the total pressure
           drop including the entrance region (validation/channel_flow.py)
Run-level: Grid Convergence Index over the three finest meshes, when the sweep
           parameter is cells_across_gap

Results are read from OpenFOAM's own ASCII field files (cell centres, U, p,
face fluxes) by harness/openfoam.py. OpenFOAM's kinematic pressure (p/rho) is
converted to Pa.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness import openfoam as of
from harness.backend_base import Backend, failed
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.plotting import channel_field_figure, channel_figure
from harness.study import Study
from validation import channel_flow as ref

WRITER = "models/cfd/channel_openfoam.py"
RUNNER = "models/cfd/run_channel.sh"


def _load_writer(path: Path):
    spec = importlib.util.spec_from_file_location("channel_openfoam_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _p(params, k):
    return float(params[k])


PARAMS = _load_writer(Path(__file__).resolve().parent.parent / WRITER).PARAMS


class OpenFOAMChannel(Backend):
    sources = (WRITER, RUNNER)

    def __init__(self):
        self.bashrc = of.find_openfoam_bashrc()
        self._versions: dict = {"openfoam_bashrc": self.bashrc}

    def prepare(self, source_dir=None, log_dir=None):
        self.writer = _load_writer(self.source_path(WRITER, source_dir))
        self.runner = self.source_path(RUNNER, source_dir)

    def solve(self, params, numerics, tolerance_scale=1.0):
        # tolerance_scale is ignored: convergence is controlled by the case's residual targets
        work = Path(tempfile.mkdtemp(prefix="of_channel_"))
        case = work / "case"
        info = self.writer.write_case(params, numerics, case)
        r = subprocess.run(of.wsl_command("bash", of.to_wsl_path(self.runner),
                                          of.to_wsl_path(case), self.bashrc),
                           capture_output=True, text=True, timeout=7200)
        files = {str(f.relative_to(case)).replace("\\", "/"): f
                 for f in sorted(case.glob("system/*")) + sorted(case.glob("constant/*"))
                 + sorted(case.glob("0/*")) + sorted(case.glob("log.*"))
                 + sorted(case.glob("versions.txt")) if f.is_file()}
        stages = {10: "case directory", 11: "OpenFOAM environment", 20: "blockMesh",
                  21: "checkMesh", 22: "foamRun", 23: "writeCellCentres"}
        if r.returncode != 0:
            res = failed(f"OpenFOAM stage failed: {stages.get(r.returncode, 'wsl')} "
                         f"(exit {r.returncode}) {r.stderr.strip()[:300]}")
            res.update(files=files, cleanup=work)
            return res
        for line in (case / "versions.txt").read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition("=")
            self._versions[k] = v

        log = of.read_solver_log(case / "log.foamRun")
        mesh_ok = "Mesh OK." in (case / "log.checkMesh").read_text(encoding="utf-8")
        tdir = of.latest_time_dir(case)
        n = info["cells"]
        C = of.read_internal_field(tdir / "C", n)
        Uf = of.read_internal_field(tdir / "U", n)
        p = of.read_internal_field(tdir / "p", n)
        phi_in = of.read_patch_value(tdir / "phi", "inlet")
        phi_out = of.read_patch_value(tdir / "phi", "outlet")
        rho = _p(params, "density_kg_per_m3")
        series = {"x_mm": C[:, 0] * 1e3, "y_mm": C[:, 1] * 1e3,
                  "ux_m_per_s": Uf[:, 0], "uy_m_per_s": Uf[:, 1], "p_Pa": p * rho}
        depth = info["depth_mm"] * 1e-3
        outputs = {"cells": n, "nx": info["nx"], "ny": info["ny"], "mesh_ok": mesh_ok,
                   "iterations": log["iterations"], "converged": log["converged"],
                   "final_initial_residuals": log["final_initial_residuals"],
                   "inlet_flow_m2_per_s": float(-np.sum(phi_in)) / depth,
                   "outlet_flow_m2_per_s": float(np.sum(phi_out)) / depth,
                   "result_time": tdir.name}
        msg = (f"foamRun: {'converged' if log['converged'] else 'NOT converged'} after "
               f"{log['iterations']} iterations, {n} cells")
        return {"success": True, "message": msg, "nfev": log["iterations"], "series": series,
                "outputs": outputs, "files": files, "cleanup": work}

    def tool_versions(self):
        return self._versions


def _window(series, params):
    x = series["x_mm"]
    return (x >= _p(params, "window_start_mm")) & (x <= _p(params, "window_end_mm"))


def _near_wall(series, params):
    """Masks of the first cell row at each wall, and wall distance (m)."""
    y, H = series["y_mm"], _p(params, "gap_mm")
    dy = H / int(params["cells_across_gap"])
    low = y < dy
    high = y > H - dy
    dist = np.where(low, y, H - y) * 1e-3
    return low, high, dist


def _centreline(series, params):
    """Cells closest to y = H/2 (one or two rows), as a mask."""
    d = np.abs(series["y_mm"] - _p(params, "gap_mm") / 2)
    return d <= d.min() + 1e-9 * _p(params, "gap_mm")


def profile_station(series, params):
    """Column of cells nearest the middle of the measurement window."""
    xs = 0.5 * (_p(params, "window_start_mm") + _p(params, "window_end_mm"))
    x = series["x_mm"]
    xc = x[np.argmin(np.abs(x - xs))]
    return np.isclose(x, xc, rtol=0, atol=1e-9)


class ChannelFlowStudy(Study):
    name = "channel_flow"
    models = {"openfoam_channel": OpenFOAMChannel}
    metrics = frozenset({"pressure_drop_Pa", "pressure_gradient_Pa_per_m", "wall_shear_stress_Pa"})
    param_names = PARAMS
    series_file = "cells.csv"
    compare_description = "max relative difference over cell columns"

    def derive(self, params):
        H, L = _p(params, "gap_mm") * 1e-3, _p(params, "length_mm") * 1e-3
        U, rho, mu = (_p(params, k) for k in ("mean_velocity_m_per_s", "density_kg_per_m3",
                                              "dynamic_viscosity_Pa_s"))
        x0, x1 = _p(params, "window_start_mm"), _p(params, "window_end_mm")
        if min(H, L, U, rho, mu) <= 0 or int(params["cells_across_gap"]) < 2:
            raise ValueError("dimensions, velocity, properties must be positive; >= 2 cells")
        if not 0 < x0 < x1 < _p(params, "length_mm"):
            raise ValueError("need 0 < window_start_mm < window_end_mm < length_mm")
        return {
            "reynolds_Dh": ref.reynolds(U, H, rho, mu),
            "entrance_length_mm": ref.entrance_length(U, H, rho, mu) * 1e3,
            "pressure_gradient_exact_Pa_per_m": ref.pressure_gradient(U, H, mu),
            "wall_shear_stress_exact_Pa": ref.wall_shear_stress(U, H, mu),
            "pressure_drop_shah_london_Pa": ref.pressure_drop_developing(L, U, H, rho, mu),
            "pressure_drop_fully_developed_only_Pa": ref.pressure_gradient(U, H, mu) * L,
        }

    def compute_metrics(self, series, params, case, outputs=None):
        mu = _p(params, "dynamic_viscosity_Pa_s")
        win = _window(series, params)
        # fully developed pressure gradient: least-squares slope of p over the window
        slope = np.polyfit(series["x_mm"][win] * 1e-3, series["p_Pa"][win], 1)[0]
        # wall shear: mu * du/dn from the first cell to the wall (OpenFOAM's own
        # wall-gradient discretization on this orthogonal mesh), both walls
        low, high, dist = _near_wall(series, params)
        wall = win & (low | high)
        tau = mu * series["ux_m_per_s"][wall] / dist[wall]
        # inlet pressure: inlet patch is zeroGradient, so its face value is the
        # first-column cell value; outlet is fixed at p = 0
        x = series["x_mm"]
        first = np.isclose(x, x.min(), rtol=0, atol=1e-9)
        return {"pressure_drop_Pa": float(np.mean(series["p_Pa"][first])),
                "pressure_gradient_Pa_per_m": float(-slope),
                "wall_shear_stress_Pa": float(np.mean(tau))}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        p, d, m = point["parameters"], point["derived"], point["metrics"]
        out = point["solver_outputs"]
        H, U = _p(p, "gap_mm") * 1e-3, _p(p, "mean_velocity_m_per_s")

        targets = {"p": float(case["numerics"]["residual_p"]),
                   "Ux": float(case["numerics"]["residual_U"]),
                   "Uy": float(case["numerics"]["residual_U"])}
        res = out["final_initial_residuals"]
        resid_ratio = max(res.get(k, np.inf) / v for k, v in targets.items())
        if not out["converged"]:
            resid_ratio = max(resid_ratio, np.inf)

        q_in, q_out = out["inlet_flow_m2_per_s"], out["outlet_flow_m2_per_s"]
        st = profile_station(series, p)
        y = series["y_mm"][st] * 1e-3
        u_exact = ref.velocity_profile(y, U, H)
        prof_err = float(np.max(np.abs(series["ux_m_per_s"][st] - u_exact)) / (1.5 * U))

        win, cl = _window(series, p), _centreline(series, p)
        uc = series["ux_m_per_s"][win & cl]
        fd_change = float((uc.max() - uc.min()) / np.mean(uc))
        balance = m["pressure_gradient_Pa_per_m"] * H / 2

        checks = [
            check("mesh_quality", "checkMesh result (0 = Mesh OK)", 0.0 if out["mesh_ok"] else 1.0,
                  0.0),
            check("iterative_convergence",
                  "max final initial residual / target (inf if SIMPLE did not converge)",
                  resid_ratio, 1.0),
            check("mass_conservation", "|Q_out - Q_in| / Q_in (face fluxes at inlet and outlet)",
                  abs(q_out - q_in) / q_in, tol["mass_rel_tol"]),
            check("inlet_flow", "|Q_in - U H| / (U H): imposed flow rate",
                  abs(q_in - U * H) / (U * H), tol["mass_rel_tol"]),
            check("momentum_balance",
                  "|tau_w - (-dp/dx) H/2| / tau_w in the fully developed window",
                  abs(m["wall_shear_stress_Pa"] - balance) / m["wall_shear_stress_Pa"],
                  tol["momentum_balance_rel_tol"]),
            check("velocity_profile_reference",
                  "max |u_CFD - u_Poiseuille| / u_max at mid-window station",
                  prof_err, tol["profile_rel_tol"]),
            check("pressure_gradient_reference", "|(-dp/dx)_CFD - 12 mu U/H^2| / exact",
                  abs(m["pressure_gradient_Pa_per_m"] - d["pressure_gradient_exact_Pa_per_m"])
                  / d["pressure_gradient_exact_Pa_per_m"], tol["fully_developed_rel_tol"]),
            check("wall_shear_reference", "|tau_w,CFD - 6 mu U/H| / exact",
                  abs(m["wall_shear_stress_Pa"] - d["wall_shear_stress_exact_Pa"])
                  / d["wall_shear_stress_exact_Pa"], tol["fully_developed_rel_tol"]),
            check("pressure_drop_correlation",
                  "|dp_CFD - dp_Shah&London| / dp_Shah&London (entrance included; correlation)",
                  abs(m["pressure_drop_Pa"] - d["pressure_drop_shah_london_Pa"])
                  / d["pressure_drop_shah_london_Pa"], tol["correlation_rel_tol"]),
            check("laminar", "Re_Dh / laminar limit", d["reynolds_Dh"] / tol["laminar_reynolds_max"],
                  1.0, kind="validity"),
            check("entrance_before_window",
                  "Shah & London entrance length / window start (window must be fully developed)",
                  d["entrance_length_mm"] / _p(p, "window_start_mm"), 1.0, kind="validity"),
            check("fully_developed",
                  "(max - min) / mean centreline velocity across the window",
                  fd_change, tol["fully_developed_change_max"], kind="validity"),
        ]
        title = (f"{point['label']}  ({out['nx']} x {out['ny']} cells, Re_Dh = "
                 f"{d['reynolds_Dh']:.0f})")
        channel_figure(pdir / "response.png", series, p, d, m, st=st, title=title)
        channel_field_figure(pdir / "field.png", series, p, out["nx"], out["ny"],
                             title=f"{point['label']}: axial velocity")
        return checks

    def verify_run_level(self, case, manifest, points):
        """GCI over the three finest meshes, only for a cells_across_gap sweep."""
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
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
        for metric, key in (("pressure_gradient_Pa_per_m", "gci_fully_developed_max"),
                            ("wall_shear_stress_Pa", "gci_fully_developed_max"),
                            ("pressure_drop_Pa", "gci_pressure_drop_max")):
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine))
            detail[metric] = u
            how = describe(u)
            checks.append(check(f"discretization_{metric}",
                                f"relative discretization uncertainty of {metric}, {how}",
                                u["uncertainty"], tol[key]) | {"metric": metric})
        return checks, detail


STUDY = ChannelFlowStudy()

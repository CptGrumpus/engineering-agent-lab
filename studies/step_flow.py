"""Study 19, part 2: turbulent flow over a backward-facing step (Driver and Seegmiller, ERCOFTAC classic case 030,
parallel walls), 2D steady RANS with k-omega SST and the viscous sublayer resolved (the setup part 1 verified).

Model:     openfoam_step_rans (models/cfd/step_openfoam.py, run_step.sh)
Reference: the measurements (reattachment length, skin friction and pressure along the step-side wall, profiles),
           compared ONCE, after the predictions are committed, by validation/step_driver_seegmiller/compare.py with the
           limits agreed beforehand (REQ-S1-3, BACKLOG). The case's own checks are internal: the inflow matches the
           stated boundary layer at x = -4 H (momentum thickness, thickness), continuity, iterative convergence,
           y+ under 1 on the walls, and the mesh study.
Run-level: GCI on the requirement metrics when the sweep is mesh_level.
"""

from __future__ import annotations

import importlib.util
import math
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness import openfoam as of
from harness.backend_base import Backend, failed
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study

WRITER = "models/cfd/step_openfoam.py"
RUNNER = "models/cfd/run_step.sh"
WALLS = ("upperWall", "upstreamFloor", "stepFace", "lowerWall")


def _load(path: Path):
    spec = importlib.util.spec_from_file_location("step_openfoam_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_W = _load(Path(__file__).resolve().parent.parent / WRITER)
PARAMS = _W.PARAMS


def crossings_up(x, y):
    """x positions where y changes from negative to positive (linear interpolation), in order."""
    out = []
    for i in range(len(x) - 1):
        if y[i] < 0 <= y[i + 1]:
            out.append(float(x[i] - y[i] * (x[i + 1] - x[i]) / (y[i + 1] - y[i])))
    return out


def boundary_layer(y, u, y_wall):
    """Edge velocity, 99 % thickness, displacement and momentum thickness of a profile (y increasing from the wall,
    u at cell centres; the wall value u = 0 is added). The edge is the velocity maximum of the profile given."""
    yy = np.concatenate([[y_wall], np.asarray(y, float)]) - y_wall
    uu = np.concatenate([[0.0], np.asarray(u, float)])
    ke = int(np.argmax(uu))
    ue = float(uu[ke])
    yy, uu = yy[:ke + 1], uu[:ke + 1]
    r = uu / ue
    k99 = int(np.argmax(r >= 0.99))
    d99 = float(yy[k99 - 1] + (0.99 - r[k99 - 1]) * (yy[k99] - yy[k99 - 1]) / (r[k99] - r[k99 - 1]))
    return {"u_e": ue, "delta99": d99, "delta_star": float(np.trapezoid(1 - r, yy)),
            "theta": float(np.trapezoid(r * (1 - r), yy))}


class OpenFOAMStep(Backend):
    sources = (WRITER, RUNNER)

    def __init__(self):
        self.bashrc = of.find_openfoam_bashrc()
        self._versions: dict = {"openfoam_bashrc": self.bashrc}

    def prepare(self, source_dir=None, log_dir=None):
        self.writer = _load(self.source_path(WRITER, source_dir))
        self.runner = self.source_path(RUNNER, source_dir)

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="of_step_"))
        case = work / "case"
        g = self.writer.write_case(params, numerics, case)
        r = subprocess.run(of.wsl_command("bash", of.to_wsl_path(self.runner), of.to_wsl_path(case), self.bashrc),
                           capture_output=True, text=True, timeout=float(numerics.get("solver_timeout_s", 14400)))
        files = {str(f.relative_to(case)).replace("\\", "/"): f
                 for f in sorted(case.glob("system/*")) + sorted(case.glob("constant/*")) + sorted(case.glob("0/*"))
                 + sorted(case.glob("log.*")) + sorted(case.glob("versions.txt"))
                 + sorted(case.glob("postProcessing/*/0/*.dat")) if f.is_file() and f.stat().st_size < 5e6}
        if r.returncode != 0:
            return failed(f"OpenFOAM stage failed (exit {r.returncode}) {r.stderr.strip()[:300]}") | {
                "files": files, "cleanup": work}
        try:
            out, series = self._post(params, g, case)
        except Exception as e:  # noqa: BLE001
            return failed(f"post-processing: {type(e).__name__}: {e}") | {"files": files, "cleanup": work}
        for line in (case / "versions.txt").read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition("=")
            self._versions[k] = v
        return {"success": True, "message": f"foamRun: {out['iterations']} iterations, Xr/H {out['xr_over_h']:.3f}",
                "nfev": out["iterations"], "series": series, "outputs": out, "files": files, "cleanup": work}

    def _post(self, params, g, case):
        H, nu = g["H_m"], g["nu_m2_per_s"]
        log = of.read_solver_log(case / "log.foamRun")
        tdir = of.latest_time_dir(case)
        C = of.read_internal_field(tdir / "C", g["cells"])
        U = of.read_internal_field(tdir / "U", g["cells"])
        P = of.read_internal_field(tdir / "p", g["cells"]).ravel()
        x, y = C[:, 0], C[:, 1]
        # inflow profile at x = -4 H: the column of block A nearest it, from the step-side wall to mid-duct
        xa = np.unique(np.round(x[(x < 0)], 12))
        x4 = float(xa[np.argmin(np.abs(xa + 4 * H))])
        col = np.flatnonzero((np.abs(x - x4) < 1e-9) & (y < H + g["duct_height_m"] / 2))
        col = col[np.argsort(y[col])]
        bl = boundary_layer(y[col], U[col, 0], H)
        u_ref = bl["u_e"]
        q = 0.5 * u_ref ** 2
        # wall shear on the floors (x component); sign set so that the attached upstream floor is positive
        tau = {}
        for patch in ("upstreamFloor", "lowerWall"):
            xc = of.read_patch_value(tdir / "C", patch)[:, 0]
            tw = of.read_patch_value(tdir / "wallShearStress", patch)[:, 0]
            o = np.argsort(xc)
            tau[patch] = (xc[o], tw[o])
        sgn = -1.0 if np.median(tau["upstreamFloor"][1]) < 0 else 1.0
        xw, cf = tau["lowerWall"][0], sgn * tau["lowerWall"][1] / q
        xu, cfu = tau["upstreamFloor"][0], sgn * tau["upstreamFloor"][1] / q
        ups = crossings_up(xw, cf)
        xr = ups[-1] if ups else float("nan")
        # pressure on the floors: the wall-adjacent cells (centres within the first cell)
        first = np.flatnonzero(((y < g["y1_m"]) & (x > 0)) | ((np.abs(y - H) < g["y1_m"]) & (x < 0) & (y > H)))
        first = first[np.argsort(x[first])]
        xp, pp = x[first], P[first]
        p_ref = float(np.interp(-4 * H, xp, pp))
        cp = (pp - p_ref) / q
        cp30 = float(np.interp(30 * H, xp, cp))
        cf20 = float(np.interp(20 * H, xw, cf))
        yp = {}
        for ln in (case / "postProcessing/yPlus/0/yPlus.dat").read_text(encoding="utf-8").splitlines():
            parts = ln.split()
            if ln.strip() and not ln.startswith("#") and len(parts) >= 5:
                yp[parts[1]] = (float(parts[2]), float(parts[3]), float(parts[4]))
        cont = [ln for ln in (case / "log.foamRun").read_text(encoding="utf-8", errors="replace").splitlines()
                if "continuity errors" in ln]
        sum_local = float(cont[-1].split("sum local =")[1].split(",")[0]) if cont else float("nan")
        cm = (case / "log.checkMesh").read_text(encoding="utf-8", errors="replace")
        out = {**g, "iterations": log["iterations"], "converged": log["converged"],
               "final_initial_residuals": log["final_initial_residuals"], "continuity_sum_local": sum_local,
               "x_inflow_station_m": x4, "inflow": bl, "u_ref_m_per_s": u_ref,
               "re_theta_inflow": u_ref * bl["theta"] / nu, "xr_over_h": xr / H,
               "reattachment_crossings_over_h": [c / H for c in ups], "cf_x20h": cf20, "cp_recovery_30h": cp30,
               "yplus": {k: v for k, v in yp.items() if k in WALLS},
               "checkmesh_failed_checks": cm.count("***"), "checkmesh_only_aspect": all(
                   "aspect ratio" in ln.lower() for ln in cm.splitlines() if "***" in ln)}
        # the harness's series file takes equal-length columns: the floor behind the step; the rest in outputs
        series = {"x_over_h": xw / H, "cf": cf}
        out["profiles"] = {"x_up_over_h": (xu / H).tolist(), "cf_up": cfu.tolist(), "x_p_over_h": (xp / H).tolist(),
                           "cp": cp.tolist(), "inflow_y_mm": ((y[col] - H) * 1e3).tolist(),
                           "inflow_u_over_uref": (U[col, 0] / u_ref).tolist()}
        return out, series

    def tool_versions(self):
        return self._versions


class StepFlowStudy(Study):
    name = "step_flow"
    models = {"openfoam_step_rans": OpenFOAMStep}
    metrics = frozenset({"xr_over_h", "cf_x20h", "cp_recovery_30h", "theta_inflow_mm", "delta99_inflow_mm",
                         "re_theta_inflow", "u_ref_m_per_s"})
    param_names = PARAMS
    series_file = "wall.csv"
    compare_description = "skin friction along the step-side wall"

    def derive(self, params):
        g = _W.geometry(params)
        return {k: g[k] for k in ("nu_m2_per_s", "cells", "y1_m", "dx_lip_m", "dx_up_max_m", "dx_far_max_m")}

    def compute_metrics(self, series, params, case, outputs=None):
        o = outputs
        return {"xr_over_h": o["xr_over_h"], "cf_x20h": o["cf_x20h"], "cp_recovery_30h": o["cp_recovery_30h"],
                "theta_inflow_mm": o["inflow"]["theta"] * 1e3, "delta99_inflow_mm": o["inflow"]["delta99"] * 1e3,
                "re_theta_inflow": o["re_theta_inflow"], "u_ref_m_per_s": o["u_ref_m_per_s"]}

    def verify_point(self, case, point, pdir, series, backend):
        tol = case["verification"]
        out, m = point["solver_outputs"], point["metrics"]
        target = case["verification"]
        ypmax = max(v[1] for k, v in out["yplus"].items() if k != "stepFace")
        checks = [
            check("converged", "SIMPLE residual control reached (0 = yes)", 0.0 if out["converged"] else 1.0, 0.0),
            check("continuity", "time-step continuity error, sum local (last iteration)", out["continuity_sum_local"],
                  tol["continuity_tol"]),
            check("inflow_theta", "|momentum thickness at x = -4 H - stated| / stated (the inflow condition)",
                  abs(m["theta_inflow_mm"] - target["inflow_theta_mm"]) / target["inflow_theta_mm"],
                  tol["inflow_theta_rel_tol"], kind="validity"),
            check("inflow_velocity", "|edge velocity at x = -4 H - stated reference| / reference",
                  abs(m["u_ref_m_per_s"] - target["inflow_u_ref_m_per_s"]) / target["inflow_u_ref_m_per_s"],
                  tol["inflow_u_rel_tol"], kind="validity"),
        ] + ([check("inflow_delta", "|99 % thickness at x = -4 H - stated| / stated",
                     abs(m["delta99_inflow_mm"] - target["inflow_delta99_mm"]) / target["inflow_delta99_mm"],
                     tol["inflow_delta_rel_tol"], kind="validity")] if "inflow_delta_rel_tol" in tol else []) + [
            check("yplus_floors", "max y+ on the walls but the step face (viscous sublayer resolved)", ypmax,
                  tol["yplus_max"], kind="validity"),
            check("mesh", "checkMesh failures other than the aspect-ratio test (0 = none)",
                  0.0 if out["checkmesh_only_aspect"] else float(out["checkmesh_failed_checks"]), 0.0),
            # Description corrected 2026-11-23: it read '1 or more = found; 0 = none', the inverse of the value.
            check("reattachment_found", "reattachment point on the floor missing (0 = found, 1 = none)",
                  0.0 if out["reattachment_crossings_over_h"] else 1.0, 0.0),
        ]
        step_figure(pdir / "response.png", series, out, point)
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "mesh_level":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: -float(pt["parameters"]["mesh_level"]))
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(1.0 / float(pt["parameters"]["mesh_level"]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
        for metric in tol.get("gci_metrics", ["xr_over_h"]):
            vals = tuple(pt["metrics"][metric] for pt in fine)
            u = discretization_uncertainty(hs, vals, design_order=2, noise_floor=tol.get("mesh_noise_rel", 1e-5))
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


def step_figure(path, series, out, point):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, _style, plt

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    fig.patch.set_facecolor(SURFACE)
    ax = axes[0]
    pr = out["profiles"]
    ax.plot(pr["inflow_u_over_uref"], pr["inflow_y_mm"], "-", color=SERIES_1, lw=1.5)
    ax.set_xlabel("u / U_ref at x = -4 H")
    ax.set_ylabel("distance from the step-side wall (mm)")
    ax.set_ylim(0, 40)
    _style(ax)
    ax = axes[1]
    ax.plot(pr["x_up_over_h"], np.asarray(pr["cf_up"]) * 1e3, "-", color=SERIES_2, lw=1.2, label="upstream floor")
    ax.plot(series["x_over_h"], series["cf"] * 1e3, "-", color=SERIES_1, lw=1.5, label="floor behind the step")
    ax.axhline(0, color=TEXT, lw=0.6)
    ax.axvline(out["xr_over_h"], color=TEXT, lw=0.6, ls="--")
    ax.annotate(f"Xr/H {out['xr_over_h']:.2f}", (out["xr_over_h"], 0), xytext=(4, 6), textcoords="offset points",
                fontsize=8, color=TEXT)
    ax.set_xlim(-8, 35)
    ax.set_xlabel("x / H")
    ax.set_ylabel("C_f x 1000")
    ax.legend(frameon=False, fontsize=8)
    _style(ax)
    ax = axes[2]
    ax.plot(pr["x_p_over_h"], pr["cp"], "-", color=SERIES_1, lw=1.5)
    ax.set_xlim(-8, 35)
    ax.set_xlabel("x / H")
    ax.set_ylabel("C_p (from x = -4 H)")
    _style(ax)
    fig.suptitle(f"{point['label']}: backward-facing step, k-omega SST (no measurements shown)", fontsize=10,
                 color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = StepFlowStudy()

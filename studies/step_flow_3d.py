"""Study 19, part 3: the backward-facing step of Driver and Seegmiller in 3D, with the wind tunnel's side walls
(half the span by symmetry), to test part 2's explanation of its one failed requirement (the pressure recovery to
30 H, 0.0227 above the measured 0.1307 against a 0.02 limit: "the tunnel's side-wall boundary layers").

Model:     openfoam_step3d_rans (models/cfd/step3d_openfoam.py on top of part 2's step_openfoam.py; run_step.sh for the
           2D solution, run_step3d.sh for the 3D one). Each point first solves the 2D model at the same mesh_level (part
           2's model, unchanged), then the 3D model started from it.
Reference: (1) side_wall = 0 (the side wall a symmetry plane) is the 2D flow exactly: the 3D result must equal the 2D
           solution on the same x-y mesh (the exact limit of this pipeline); (2) mass balance, continuity, iterative
           convergence (residuals and the recovery's own history), y+ under 1 on every wall but the step face, the 3D
           mesh's x-y plane identical to the 2D mesh (cell centres), the inflow at x = -4 H at mid-span against the
           case description; (3) spanwise refinement. The measurements are compared by
           validation/step_driver_seegmiller/compare.py (part 2's script, --out for part 3), not here: NOT blind, part 2
           opened and scored them on 2026-11-23.
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
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study
from studies.step_flow import OpenFOAMStep, boundary_layer, crossings_up

WRITER2 = "models/cfd/step_openfoam.py"
RUNNER2 = "models/cfd/run_step.sh"
WRITER3 = "models/cfd/step3d_openfoam.py"
RUNNER3 = "models/cfd/run_step3d.sh"
WALLS = ("upperWall", "upstreamFloor", "stepFace", "lowerWall", "sideWall")
FIELDS = ("U", "p", "k", "omega", "nut")
SIDE_STATIONS_OVER_H = (-4.0, 10.0, 20.0, 30.0)
SECTIONS_OVER_H = (-4.0, 30.0)
NUMERICS_3D_ONLY = ("consistent", "relax_p", "relax_U", "relax_turb")


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_W3 = _load(Path(__file__).resolve().parent.parent / WRITER3, "step3d_openfoam_repo")
#: inlet_velocity_2d_m_per_s: the 2D solution's inlet velocity (part 2's inflow match, 41.95 m/s), so every point's 2D
#: solution is part 2's model exactly; the 3D model's own inlet velocity is re-matched to the same edge velocity at
#: x = -4 H (the side walls' displacement speeds up the core)
PARAMS = _W3.PARAMS + ("inlet_velocity_2d_m_per_s",)


def _num_dirs(path: Path) -> list[Path]:
    out = []
    for d in Path(path).iterdir() if Path(path).is_dir() else []:
        try:
            out.append((float(d.name), d))
        except ValueError:
            continue
    return [d for _, d in sorted(out)]


def _dat_rows(path: Path) -> np.ndarray:
    rows = []
    for ln in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if ln.strip() and not ln.startswith("#"):
            rows.append([float(v) for v in ln.replace("(", " ").replace(")", " ").split()])
    return np.array(rows)


def latest_yplus(case: Path) -> dict:
    """y+ (min, max, mean) per patch from the LAST run's yPlus.dat: each foamRun stage writes its own
    postProcessing/yPlus/<start time>/ directory (part 2's backend read the start-up stage's, at iteration 500)."""
    dirs = _num_dirs(case / "postProcessing/yPlus")
    yp = {}
    for ln in (dirs[-1] / "yPlus.dat").read_text(encoding="utf-8").splitlines():
        parts = ln.split()
        if ln.strip() and not ln.startswith("#") and len(parts) >= 5:
            yp[parts[1]] = (float(parts[2]), float(parts[3]), float(parts[4]))
    return {"start_time_dir": dirs[-1].name, "patches": yp}


def _keep(case: Path, prefix: str) -> dict:
    return {prefix + str(f.relative_to(case)).replace("\\", "/"): f
            for f in sorted(case.glob("system/*")) + sorted(case.glob("constant/*")) + sorted(case.glob("0/*"))
            + sorted(case.glob("log.*")) + sorted(case.glob("versions.txt"))
            + sorted(case.glob("postProcessing/*/*/*")) if f.is_file() and f.stat().st_size < 5e6}


class OpenFOAMStep3D(Backend):
    sources = (WRITER2, RUNNER2, WRITER3, RUNNER3)

    def __init__(self):
        self.bashrc = of.find_openfoam_bashrc()
        self._versions: dict = {"openfoam_bashrc": self.bashrc}

    def prepare(self, source_dir=None, log_dir=None):
        # the 3D writer loads step_openfoam.py from its own folder: both are in the run's flat inputs/
        self.w3 = _load(self.source_path(WRITER3, source_dir), "step3d_openfoam_saved")
        self.w2 = self.w3.S2
        self.r2 = self.source_path(RUNNER2, source_dir)
        self.r3 = self.source_path(RUNNER3, source_dir)

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="of_step3d_"))
        c2, c3 = work / "case2d", work / "case3d"
        p2 = {k: params[k] for k in self.w2.PARAMS} | {"inlet_velocity_m_per_s": params["inlet_velocity_2d_m_per_s"]}
        # the 2D stage runs with part 2's numerics (SIMPLE and its relaxation), whatever the 3D stage uses
        n2 = {k: v for k, v in numerics.items() if k not in NUMERICS_3D_ONLY} | {
            "max_iterations": numerics.get("max_iterations_2d", 80000),
            "stage1_iterations": numerics.get("stage1_iterations_2d", 500)}
        g2 = self.w2.write_case(p2, n2, c2)
        tmo = float(numerics.get("solver_timeout_s", 43200))
        r = subprocess.run(of.wsl_command("bash", of.to_wsl_path(self.r2), of.to_wsl_path(c2), self.bashrc),
                           capture_output=True, text=True, timeout=tmo)
        files = _keep(c2, "case2d/")
        if r.returncode != 0:
            return failed(f"2D stage failed (exit {r.returncode}) {r.stderr.strip()[:300]}") | {"files": files, "cleanup": work}
        try:
            out2, series2 = OpenFOAMStep._post(None, p2, g2, c2)
            out2["yplus"] = {k: v for k, v in latest_yplus(c2)["patches"].items() if k in WALLS}
            t2 = of.latest_time_dir(c2)
            init = {n: of.read_internal_field(t2 / n, g2["cells"]) for n in FIELDS}
            C2 = of.read_internal_field(t2 / "C", g2["cells"])
        except Exception as e:  # noqa: BLE001
            return failed(f"2D post-processing: {type(e).__name__}: {e}") | {"files": files, "cleanup": work}
        g3 = self.w3.write_case(params, numerics, c3, initial=init)
        r = subprocess.run(of.wsl_command("bash", of.to_wsl_path(self.r3), of.to_wsl_path(c3), self.bashrc,
                                          str(int(numerics.get("n_procs", 1)))),
                           capture_output=True, text=True, timeout=tmo)
        files |= _keep(c3, "case3d/")
        if r.returncode != 0:
            return failed(f"3D stage failed (exit {r.returncode}) {r.stderr.strip()[:300]}") | {"files": files, "cleanup": work}
        try:
            out, series = self._post(params, g3, c3, C2)
        except Exception as e:  # noqa: BLE001
            return failed(f"3D post-processing: {type(e).__name__}: {e}") | {"files": files, "cleanup": work}
        out["precursor_2d"] = {k: out2[k] for k in ("iterations", "converged", "final_initial_residuals", "xr_over_h",
                                                     "cf_x20h", "cp_recovery_30h", "u_ref_m_per_s", "re_theta_inflow",
                                                     "continuity_sum_local", "yplus", "inflow")}
        out["precursor_2d"]["profiles"] = {"x_cf_over_h": series2["x_over_h"].tolist(), "cf": series2["cf"].tolist(),
                                           "x_p_over_h": out2["profiles"]["x_p_over_h"], "cp": out2["profiles"]["cp"]}
        for line in (c3 / "versions.txt").read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition("=")
            self._versions[k] = v
        return {"success": True, "message": f"2D {out2['iterations']} + 3D {out['iterations']} iterations, Xr/H "
                f"{out2['xr_over_h']:.3f} (2D) / {out['xr_over_h']:.3f} (3D mid-span)",
                "nfev": out["iterations"], "series": series, "outputs": out, "files": files, "cleanup": work}

    def _post(self, params, g, case, C2):
        H, nu, W = g["H_m"], g["nu_m2_per_s"], g["half_span_m"]
        n = g["cells"]
        log = of.read_solver_log(case / "log.foamRun")
        tdir = of.latest_time_dir(case)
        C = of.read_internal_field(tdir / "C", n)
        U = of.read_internal_field(tdir / "U", n)
        P = of.read_internal_field(tdir / "p", n).ravel()
        idx = self.w3.extrude_index(g)
        xy_match = float(np.max(np.abs(C[:, :2] - C2[idx, :2])))
        x, y, z = C[:, 0], C[:, 1], C[:, 2]
        zmin = float(z.min())
        lay = z < 1.5 * zmin  # the mid-span layer (cell centres at dz_mid / 2; the next layer's are at 2.8 x that)
        if int(lay.sum()) != g["cells_2d"]:
            raise ValueError(f"mid-span layer has {int(lay.sum())} cells, expected {g['cells_2d']}")
        # inflow at x = -4 H, mid-span: block A's column nearest it, from the step-side wall to mid-duct
        xa = np.unique(np.round(x[(x < 0) & lay], 12))
        x4 = float(xa[np.argmin(np.abs(xa + 4 * H))])
        col = np.flatnonzero(lay & (np.abs(x - x4) < 1e-9) & (y < H + g["duct_height_m"] / 2))
        col = col[np.argsort(y[col])]
        bl = boundary_layer(y[col], U[col, 0], H)
        u_ref = bl["u_e"]
        q = 0.5 * u_ref ** 2
        # wall shear on the floors at mid-span, and on the floor behind the step at every spanwise layer
        tau, lw = {}, None
        for patch in ("upstreamFloor", "lowerWall"):
            fc = of.read_patch_value(tdir / "C", patch)
            tw = of.read_patch_value(tdir / "wallShearStress", patch)[:, 0]
            m = fc[:, 2] < 1.5 * zmin
            o = np.argsort(fc[m, 0])
            tau[patch] = (fc[m, 0][o], tw[m][o])
            if patch == "lowerWall":
                lw = (fc, tw)
        sgn = -1.0 if np.median(tau["upstreamFloor"][1]) < 0 else 1.0
        xw, cf = tau["lowerWall"][0], sgn * tau["lowerWall"][1] / q
        xu, cfu = tau["upstreamFloor"][0], sgn * tau["upstreamFloor"][1] / q
        ups = crossings_up(xw, cf)
        xr = ups[-1] if ups else float("nan")
        zs = np.unique(np.round(lw[0][:, 2], 12))
        xr_z = []
        for zz in zs:
            m = np.abs(lw[0][:, 2] - zz) < 1e-9
            o = np.argsort(lw[0][m, 0])
            c = crossings_up(lw[0][m, 0][o], sgn * lw[1][m][o] / q)
            xr_z.append(c[-1] / H if c else float("nan"))
        # pressure on the floors: wall-adjacent cells; mid-span, and the recovery at every spanwise layer
        first = ((y < g["y1_m"]) & (x > 0)) | ((np.abs(y - H) < g["y1_m"]) & (x < 0) & (y > H))
        fm = np.flatnonzero(first & lay)
        fm = fm[np.argsort(x[fm])]
        xp, pp = x[fm], P[fm]
        p_ref = float(np.interp(-4 * H, xp, pp))
        cp = (pp - p_ref) / q
        cp30 = float(np.interp(30 * H, xp, cp))
        cf20 = float(np.interp(20 * H, xw, cf))
        zc = np.unique(np.round(z, 12))
        rec_z = []
        for zz in zc:
            f = np.flatnonzero(first & (np.abs(z - zz) < 1e-9))
            f = f[np.argsort(x[f])]
            rec_z.append(float(np.interp(30 * H, x[f], P[f]) - np.interp(-4 * H, x[f], P[f])) / q)
        # the side wall's boundary layer at mid-height of the channel, at a few stations (u along z, at y and x fixed)
        side = []
        for xs in SIDE_STATIONS_OVER_H:
            xc = np.unique(np.round(x[lay], 12))
            xn = float(xc[np.argmin(np.abs(xc - xs * H))])
            ymid = H + 0.5 * g["duct_height_m"] if xs < 0 else 0.5 * (H + g["duct_height_m"])
            yc = np.unique(np.round(y[lay & (np.abs(x - xn) < 1e-9)], 12))
            yn = float(yc[np.argmin(np.abs(yc - ymid))])
            cz = np.flatnonzero((np.abs(x - xn) < 1e-9) & (np.abs(y - yn) < 1e-9))
            d = W - z[cz]
            o = np.argsort(d)
            entry = {"x_over_h": xn / H, "y_mm": yn * 1e3, "dist_mm": (d[o] * 1e3).tolist(),
                     "u_over_uref": (U[cz, 0][o] / u_ref).tolist()}
            if g.get("side_wall"):
                sb = boundary_layer(d[o], U[cz, 0][o], 0.0)
                entry.update({k + "_mm": v * 1e3 for k, v in sb.items() if k != "u_e"}, u_e_over_uref=sb["u_e"] / u_ref)
            side.append(entry)
        yp = latest_yplus(case)
        cont = [ln for ln in (case / "log.foamRun").read_text(encoding="utf-8", errors="replace").splitlines()
                if "continuity errors" in ln]
        sum_local = float(cont[-1].split("sum local =")[1].split(",")[0]) if cont else float("nan")
        cm = (case / "log.checkMesh").read_text(encoding="utf-8", errors="replace")
        flows = {}
        for nm in ("inletFlow", "outletFlow"):
            d = _num_dirs(case / "postProcessing" / nm)
            flows[nm] = float(_dat_rows(d[-1] / "surfaceFieldValue.dat")[-1, 1])
        # the recovery's history from the probes (stage 2): wall cells at x = -4 H and 30 H, mid-span
        pd = _num_dirs(case / "postProcessing/probes")[-1]
        ph = _dat_rows(pd / "p")
        it, rec_hist = ph[:, 0], (ph[:, 2] - ph[:, 1]) / q
        last = it >= it[-1] - 0.1 * (it[-1] - float(pd.name))
        out = {**{k: v for k, v in g.items() if k != "split"}, "split": g["split"], "iterations": log["iterations"],
               "converged": log["converged"], "final_initial_residuals": log["final_initial_residuals"],
               "continuity_sum_local": sum_local, "x_inflow_station_m": x4, "inflow": bl, "u_ref_m_per_s": u_ref,
               "re_theta_inflow": u_ref * bl["theta"] / nu, "xr_over_h": xr / H,
               "reattachment_crossings_over_h": [c / H for c in ups], "cf_x20h": cf20, "cp_recovery_30h": cp30,
               "yplus": {k: v for k, v in yp["patches"].items() if k in WALLS}, "yplus_start_dir": yp["start_time_dir"],
               "checkmesh_failed_checks": cm.count("***"), "checkmesh_only_aspect": all(
                   "aspect ratio" in ln.lower() for ln in cm.splitlines() if "***" in ln),
               "mesh_xy_match_m": xy_match, "flow_in_m3_per_s": flows["inletFlow"], "flow_out_m3_per_s": flows["outletFlow"],
               "mass_balance_rel": abs(flows["inletFlow"] + flows["outletFlow"]) / abs(flows["inletFlow"]),
               "recovery_probe_last10pct_range": float(np.ptp(rec_hist[last])),
               "recovery_probe_history": {"iteration": it.tolist(), "recovery": rec_hist.tolist()},
               "xr_by_z": {"z_mm": (zs * 1e3).tolist(), "xr_over_h": xr_z},
               "cp_recovery_30h_by_z": {"z_mm": (zc * 1e3).tolist(), "recovery": rec_z}, "side_wall_layer": side}
        # maps for the figures: Cf over the floor behind the step (x, z), and u over cross-sections of the tunnel
        out["floor_cf_map"] = {"x_over_h": (lw[0][:, 0] / H).tolist(), "z_mm": (lw[0][:, 2] * 1e3).tolist(),
                               "cf": (sgn * lw[1] / q).tolist()}
        sections = []
        for xs in SECTIONS_OVER_H:
            xc = np.unique(np.round(x[lay], 12))
            xn = float(xc[np.argmin(np.abs(xc - xs * H))])
            sec = np.flatnonzero(np.abs(x - xn) < 1e-9)
            sections.append({"x_over_h": xn / H, "y_mm": (y[sec] * 1e3).tolist(), "z_mm": (z[sec] * 1e3).tolist(),
                             "u_over_uref": (U[sec, 0] / u_ref).tolist()})
        out["sections"] = sections
        series = {"x_over_h": xw / H, "cf": cf}
        out["profiles"] = {"x_up_over_h": (xu / H).tolist(), "cf_up": cfu.tolist(), "x_p_over_h": (xp / H).tolist(),
                           "cp": cp.tolist(), "inflow_y_mm": ((y[col] - H) * 1e3).tolist(),
                           "inflow_u_over_uref": (U[col, 0] / u_ref).tolist()}
        return out, series

    def tool_versions(self):
        return self._versions


class StepFlow3DStudy(Study):
    name = "step_flow_3d"
    models = {"openfoam_step3d_rans": OpenFOAMStep3D}
    metrics = frozenset({"xr_over_h", "cf_x20h", "cp_recovery_30h", "theta_inflow_mm", "delta99_inflow_mm",
                         "re_theta_inflow", "u_ref_m_per_s", "xr_over_h_2d", "cf_x20h_2d", "cp_recovery_30h_2d",
                         "cp_recovery_change", "cp_recovery_change_abs", "xr_change_rel", "sidewall_theta_inflow_mm", "sidewall_dstar_30h_mm"})
    param_names = PARAMS
    series_file = "wall.csv"
    compare_description = "skin friction along the step-side wall at mid-span"

    def derive(self, params):
        g = _W3.geometry(params)
        return {k: g[k] for k in ("nu_m2_per_s", "cells", "cells_2d", "nz", "y1_m", "y1z_m", "growth_z", "dz_mid_m",
                                  "dx_lip_m")} | {"side_wall_split": g["split"]}

    def compute_metrics(self, series, params, case, outputs=None):
        o, o2 = outputs, outputs["precursor_2d"]
        sw = {s["x_over_h"]: s for s in o["side_wall_layer"]}
        sw4 = min(sw, key=lambda v: abs(v + 4))
        sw30 = min(sw, key=lambda v: abs(v - 30))
        return {"xr_over_h": o["xr_over_h"], "cf_x20h": o["cf_x20h"], "cp_recovery_30h": o["cp_recovery_30h"],
                "theta_inflow_mm": o["inflow"]["theta"] * 1e3, "delta99_inflow_mm": o["inflow"]["delta99"] * 1e3,
                "re_theta_inflow": o["re_theta_inflow"], "u_ref_m_per_s": o["u_ref_m_per_s"],
                "xr_over_h_2d": o2["xr_over_h"], "cf_x20h_2d": o2["cf_x20h"], "cp_recovery_30h_2d": o2["cp_recovery_30h"],
                "cp_recovery_change": o["cp_recovery_30h"] - o2["cp_recovery_30h"],
                "cp_recovery_change_abs": abs(o["cp_recovery_30h"] - o2["cp_recovery_30h"]),
                "xr_change_rel": o["xr_over_h"] / o2["xr_over_h"] - 1,
                "sidewall_theta_inflow_mm": sw[sw4].get("theta_mm", 0.0),
                "sidewall_dstar_30h_mm": sw[sw30].get("delta_star_mm", 0.0)}

    def verify_point(self, case, point, pdir, series, backend):
        tol = case["verification"]
        out, m, p = point["solver_outputs"], point["metrics"], point["parameters"]
        o2 = out["precursor_2d"]
        ypmax = max(v[1] for k, v in out["yplus"].items() if k != "stepFace")
        checks = [
            check("converged", "3D: SIMPLE residual control reached (0 = yes)", 0.0 if out["converged"] else 1.0, 0.0),
            check("converged_2d", "2D solution (initial field and same-mesh comparison): residual control reached "
                  "(0 = yes)", 0.0 if o2["converged"] else 1.0, 0.0),
            check("continuity", "3D: time-step continuity error, sum local (last iteration)", out["continuity_sum_local"],
                  tol["continuity_tol"]),
            check("mass_balance", "3D: |inlet + outlet volume flow| / inlet flow", out["mass_balance_rel"],
                  tol["mass_balance_tol"]),
            check("recovery_settled", "3D: range of the probe recovery Cp(30 H) - Cp(-4 H) at mid-span over the last "
                  "10 % of the iterations", out["recovery_probe_last10pct_range"], tol["recovery_settled_tol"]),
            check("mesh_matches_2d", "max |x-y cell centre of the 3D mesh - its 2D cell's| (m): the 3D x-y plane is the "
                  "2D mesh, and the cell map is right", out["mesh_xy_match_m"], tol["mesh_match_tol_m"]),
            check("inflow_theta", "|momentum thickness at x = -4 H, mid-span - stated| / stated",
                  abs(m["theta_inflow_mm"] - tol["inflow_theta_mm"]) / tol["inflow_theta_mm"],
                  tol["inflow_theta_rel_tol"], kind="validity"),
            check("inflow_velocity", "|edge velocity at x = -4 H, mid-span - stated reference| / reference",
                  abs(m["u_ref_m_per_s"] - tol["inflow_u_ref_m_per_s"]) / tol["inflow_u_ref_m_per_s"],
                  tol["inflow_u_rel_tol"], kind="validity"),
            check("yplus_walls", "max y+ on every wall but the step face, side wall included (viscous sublayer resolved)",
                  ypmax, tol["yplus_max"], kind="validity"),
            check("mesh", "checkMesh failures other than the aspect-ratio test (0 = none)",
                  0.0 if out["checkmesh_only_aspect"] else float(out["checkmesh_failed_checks"]), 0.0),
            check("reattachment_found", "reattachment point on the floor at mid-span missing (0 = found, 1 = none)",
                  0.0 if out["reattachment_crossings_over_h"] else 1.0, 0.0),
        ]
        if int(round(float(p["side_wall"]))) == 0:
            xr_z = np.asarray(out["xr_by_z"]["xr_over_h"], float)
            checks += [
                check("limit_xr", "side wall as symmetry = 2D: |Xr/H 3D - 2D| / 2D", abs(m["xr_change_rel"]),
                      tol["limit_xr_rel_tol"]),
                check("limit_cp_recovery", "side wall as symmetry = 2D: |recovery 3D - 2D|", abs(m["cp_recovery_change"]),
                      tol["limit_cp_abs_tol"]),
                check("limit_cf20", "side wall as symmetry = 2D: |Cf(20 H) 3D - 2D| / 2D",
                      abs(m["cf_x20h"] / m["cf_x20h_2d"] - 1), tol["limit_cf_rel_tol"]),
                check("limit_spanwise_uniform", "side wall as symmetry = 2D: max |Xr/H(z) - Xr/H(mid-span)| / Xr/H",
                      float(np.max(np.abs(xr_z - m["xr_over_h"])) / m["xr_over_h"]), tol["limit_xr_rel_tol"]),
            ]
        ref = case.get("reference_2d", {})
        key = f"{float(p['mesh_level']):g}"
        if key in ref:
            r = ref[key]
            checks += [check("precursor_matches_part2", f"2D solution against part 2's committed run at mesh_level {key} "
                             "(the same model): max of |Xr/H| relative and |recovery| absolute differences",
                             max(abs(o2["xr_over_h"] / r["xr_over_h"] - 1), abs(o2["cp_recovery_30h"] - r["cp_recovery_30h"])),
                             tol["precursor_tol"])]
        step3d_figure(pdir / "response.png", series, out, point)
        return checks

    def verify_run_level(self, case, manifest, points):
        sweep = case.get("sweep", {}).get("parameter")
        if sweep not in ("mesh_level", "spanwise_level"):
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: -float(pt["parameters"][sweep]))
        checks, detail = [], {"sweep": sweep, "levels": [pt["label"] for pt in done]}
        if len(done) >= 3:
            fine = done[:3]
            hs = tuple(1.0 / float(pt["parameters"][sweep]) for pt in fine)
            for metric in tol.get("gci_metrics", ["cp_recovery_30h"]):
                vals = tuple(pt["metrics"][metric] for pt in fine)
                u = discretization_uncertainty(hs, vals, design_order=2, noise_floor=tol.get("mesh_noise_rel", 1e-5))
                detail[metric] = u
                checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric} "
                                    f"({sweep}), {describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        elif len(done) == 2:
            for metric, lim in tol.get("refinement_change_abs", {}).items():
                d = abs(done[0]["metrics"][metric] - done[1]["metrics"][metric])
                detail[metric] = {"fine": done[0]["metrics"][metric], "coarse": done[1]["metrics"][metric], "change": d}
                checks.append(check(f"refinement_{metric}", f"|{metric} finer - coarser| ({sweep}, two levels: a "
                                    "change, not an uncertainty)", d, lim) | {"metric": metric})
        else:
            checks.append(check("refinement", f"needs >= 2 completed {sweep} levels", float("inf"), 0.0))
        return checks, detail


def step3d_figure(path, series, out, point):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, _style, plt

    o2 = out["precursor_2d"]["profiles"]
    fig, axes = plt.subplots(1, 4, figsize=(19, 4))
    fig.patch.set_facecolor(SURFACE)
    ax = axes[0]
    ax.plot(o2["x_cf_over_h"], np.asarray(o2["cf"]) * 1e3, "-", color=SERIES_2, lw=1.2, label="2D, same x-y mesh")
    ax.plot(series["x_over_h"], series["cf"] * 1e3, "-", color=SERIES_1, lw=1.5, label="3D, mid-span")
    ax.axhline(0, color=TEXT, lw=0.6)
    ax.set_xlim(-2, 35)
    ax.set_xlabel("x / H")
    ax.set_ylabel("C_f x 1000 (step-side wall)")
    ax.legend(frameon=False, fontsize=8)
    _style(ax)
    ax = axes[1]
    ax.plot(o2["x_p_over_h"], o2["cp"], "-", color=SERIES_2, lw=1.2, label="2D")
    ax.plot(out["profiles"]["x_p_over_h"], out["profiles"]["cp"], "-", color=SERIES_1, lw=1.5, label="3D, mid-span")
    ax.set_xlim(-8, 35)
    ax.set_xlabel("x / H")
    ax.set_ylabel("C_p (from x = -4 H)")
    ax.legend(frameon=False, fontsize=8)
    _style(ax)
    ax = axes[2]
    xz = out["xr_by_z"]
    ax.plot(xz["xr_over_h"], xz["z_mm"], "o-", color=SERIES_1, ms=3, lw=1.2)
    ax.set_xlabel("reattachment Xr / H")
    ax.set_ylabel("z from mid-span (mm)")
    ax.axhline(out["half_span_m"] * 1e3, color=TEXT, lw=0.6, ls="--")
    _style(ax)
    ax = axes[3]
    for s, ls in zip(out["side_wall_layer"], ("-", "--", "-.", ":")):
        ax.plot(s["u_over_uref"], s["dist_mm"], ls, color=SERIES_1, lw=1.2, label=f"x/H {s['x_over_h']:.0f}")
    ax.set_xlabel("u / U_ref at channel mid-height")
    ax.set_ylabel("distance from the side wall (mm)")
    ax.set_ylim(0, 75.5)
    ax.legend(frameon=False, fontsize=8)
    _style(ax)
    fig.suptitle(f"{point['label']}: backward-facing step in 3D, k-omega SST (no measurements shown)", fontsize=10,
                 color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = StepFlow3DStudy()

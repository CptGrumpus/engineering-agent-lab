"""Study: the Turek-Hron fluid stage (CFD1, CFD2) and Schaefer-Turek 2D-1, OpenFOAM against the benchmarks.

Model:     openfoam_turek_hron (models/cfd/turek_hron_openfoam.py, run_turek_hron.sh): Gmsh quad-dominant
           mesh round the cylinder and its rigid flag, gmshToFoam, steady laminar incompressibleFluid,
           forces on the body
Reference: the published benchmark drag and lift (the requirement); Schaefer-Turek 2D-1 (cylinder alone,
           Re 20) through the same pipeline as an independent check of the pipeline itself; mass
           conservation, the imposed flow rate and the parabolic inflow
Nested:    numerics nested_base_cell_size_m: every level split uniformly from one base mesh (the writer's
           extrude_msh22), cell_size_m = base / 2^n exactly (2026-11-25: turek_hron_cfd*_nested)
Run-level: GCI on drag and lift when the sweep is cell_size_m; verification.mesh_noise_rel (one number or a
           table by metric) declares the measured regenerated-mesh scatter at one nominal size, as in
           studies/turek_hron_fsi.py (2026-11-25: turek_hron_cfd1_noise_*, turek_hron_cfd2_noise_*)
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
from harness.study import Study

WRITER = "models/cfd/turek_hron_openfoam.py"
RUNNER = "models/cfd/run_turek_hron.sh"
BENCH = ("benchmark_drag_N_per_m", "benchmark_lift_N_per_m")


def _load_writer(path: Path):
    spec = importlib.util.spec_from_file_location("turek_hron_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_W = _load_writer(Path(__file__).resolve().parent.parent / WRITER)


def _p(params, k):
    return float(params[k])


def read_forces(path: Path) -> np.ndarray:
    """forces.dat rows: (iteration, Fx_pressure, Fy_pressure, Fx_viscous, Fy_viscous)."""
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        v = [float(x) for x in re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", line)]
        rows.append([v[0], v[1], v[2], v[4], v[5]])
    return np.array(rows)


class OpenFOAMTurekHron(Backend):
    sources = (WRITER, RUNNER)

    def __init__(self):
        from studies.cantilever import find_freecadcmd

        self.gmsh = find_freecadcmd().parent / "gmsh.exe"
        self.bashrc = of.find_openfoam_bashrc()
        self._versions: dict = {"openfoam_bashrc": self.bashrc}

    def prepare(self, source_dir=None, log_dir=None):
        self.writer = _load_writer(self.source_path(WRITER, source_dir))
        self.runner = self.source_path(RUNNER, source_dir)
        r = subprocess.run([str(self.gmsh), "--version"], capture_output=True, text=True, timeout=60)
        self._versions["gmsh"] = (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "?"

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="of_turek_"))
        case = work / "case"
        info = self.writer.write_case(params, numerics, case)
        base = numerics.get("nested_base_cell_size_m")
        levels = 0
        if base:
            ratio = float(base) / _p(params, "cell_size_m")
            levels = int(round(np.log2(ratio)))
            if levels < 0 or abs(ratio / 2 ** levels - 1) > 1e-9:
                return failed(f"cell_size_m must be nested_base_cell_size_m / 2^n (ratio {ratio})")
        self.writer.write_geo(params, case / "mesh.geo", base_cell_size_m=base, refine_levels=levels)

        def files():
            return {str(f.relative_to(case)).replace("\\", "/"): f
                    for f in sorted(case.glob("system/*")) + sorted(case.glob("constant/*"))
                    + sorted(case.glob("0/*")) + sorted(case.glob("log.*")) + [case / "mesh.geo"]
                    + sorted(case.glob("versions.txt")) + sorted(case.glob("postProcessing/forces/0/*.dat"))
                    if f.is_file()}

        if base:
            g = subprocess.run([str(self.gmsh), "mesh.geo", "-parse_and_exit"], cwd=case,
                               capture_output=True, text=True, timeout=3600)
            if g.returncode == 0 and (case / "mesh2d.msh").exists():
                self.writer.extrude_msh22(case / "mesh2d.msh", case / "mesh.msh")
                (case / "mesh2d.msh").unlink()
        else:
            g = subprocess.run([str(self.gmsh), "mesh.geo", "-3", "-format", "msh22", "-o", "mesh.msh"], cwd=case,
                               capture_output=True, text=True, timeout=3600)
        (case / "log.gmsh").write_text(g.stdout + g.stderr, encoding="utf-8")
        if g.returncode != 0 or not (case / "mesh.msh").exists():
            return failed("Gmsh failed") | {"files": files(), "cleanup": work}
        quality = {"nested_refine_levels": levels} if base else {}
        flag = _p(params, "flag_length_m")
        if flag > 0:   # the fluid-cell check at the flag that caught turek_hron_fsi1_noise_a (2026-11-25 here)
            from studies.turek_hron_fsi import flag_cell_quality, read_msh22_base
            W = self.writer
            quality |= flag_cell_quality(*read_msh22_base(case / "mesh.msh"),
                                        W.XC + (W.R ** 2 - (W.FLAG_H / 2) ** 2) ** 0.5, W.XC + W.R + flag,
                                        W.YC - W.FLAG_H / 2, W.YC + W.FLAG_H / 2)
        r = subprocess.run(of.wsl_command("bash", of.to_wsl_path(self.runner), of.to_wsl_path(case), self.bashrc),
                           capture_output=True, text=True,
                           timeout=float(numerics.get("solver_timeout_s", 7200)))
        (case / "mesh.msh").unlink(missing_ok=True)
        if r.returncode != 0:
            return failed(f"OpenFOAM stage failed (exit {r.returncode}) {r.stderr.strip()[:300]}") | {
                "files": files(), "cleanup": work}
        for line in (case / "versions.txt").read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition("=")
            self._versions[k] = v
        log = of.read_solver_log(case / "log.foamRun")
        chk = (case / "log.checkMesh").read_text(encoding="utf-8")
        cells = int(re.search(r"cells:\s+(\d+)", chk).group(1))
        tdir = of.latest_time_dir(case)
        phi_in = of.read_patch_value(tdir / "phi", "inlet")
        phi_out = of.read_patch_value(tdir / "phi", "outlet")
        u_in = np.asarray(of.read_patch_value(tdir / "U", "inlet"))
        y_in = np.asarray(of.read_patch_value(tdir / "C", "inlet"))[:, 1]
        U, H = _p(params, "mean_velocity_m_per_s"), self.writer.CHANNEL_H
        parabola = 1.5 * U * 4 * y_in * (H - y_in) / H**2
        F = read_forces(case / "postProcessing/forces/0/forces.dat")
        d = info["depth_m"]
        drag, lift = (F[:, 1] + F[:, 3]) / d, (F[:, 2] + F[:, 4]) / d
        series = {"iteration": F[:, 0], "drag_N_per_m": drag, "lift_N_per_m": lift}
        outputs = {"cells": cells, "mesh_ok": "Mesh OK." in chk, "simple_converged": log["converged"],
                   "iterations": log["iterations"], "final_initial_residuals": log["final_initial_residuals"],
                   "inlet_flow_m3_per_s": float(-np.sum(phi_in)), "outlet_flow_m3_per_s": float(np.sum(phi_out)),
                   "imposed_flow_m3_per_s": info["flow_m3_per_s"],
                   "inlet_profile_error_max": float(np.max(np.abs(u_in[:, 0] - parabola)) / (1.5 * U)),
                   "inlet_faces": int(len(y_in)),
                   "pressure_drag_N_per_m": float(F[-1, 1] / d), "viscous_drag_N_per_m": float(F[-1, 3] / d),
                   "domain_area_m2": _domain_area(params), **quality}
        return {"success": True, "message": f"drag {drag[-1]:.5f}, lift {lift[-1]:.5f} N/m ({cells} cells, "
                f"{log['iterations']} iterations)", "nfev": log["iterations"], "series": series,
                "outputs": outputs, "files": files(), "cleanup": work}

    def tool_versions(self):
        return self._versions


def _domain_area(params) -> float:
    W = _W
    a = W.CHANNEL_L * W.CHANNEL_H - np.pi * W.R**2
    flag = _p(params, "flag_length_m")
    if flag > 0:   # flag rectangle from x = XC to the end, minus its overlap with the disk
        y = W.FLAG_H / 2
        seg = W.R**2 * np.arcsin(y / W.R) + y * np.sqrt(W.R**2 - y**2)    # disk area for |y'| < y, x' > 0
        a -= (W.R + flag) * W.FLAG_H - seg
    return float(a)


class TurekHronCFDStudy(Study):
    name = "turek_hron_cfd"
    models = {"openfoam_turek_hron": OpenFOAMTurekHron}
    metrics = frozenset({"drag_N_per_m", "lift_N_per_m", "drag_deviation_pct", "lift_deviation_pct"})
    param_names = _W.PARAMS + BENCH
    series_file = "forces.csv"
    compare_description = "max relative difference of the force history"

    def derive(self, params):
        U, nu = _p(params, "mean_velocity_m_per_s"), _p(params, "kinematic_viscosity_m2_per_s")
        D = 2 * _W.R
        q = 0.5 * _p(params, "density_kg_per_m3") * U**2 * D
        return {"reynolds_D": U * D / nu, "dynamic_pressure_times_D_N_per_m": q}

    def compute_metrics(self, series, params, case, outputs=None):
        drag, lift = float(series["drag_N_per_m"][-1]), float(series["lift_N_per_m"][-1])
        bd, bl = _p(params, BENCH[0]), _p(params, BENCH[1])
        return {"drag_N_per_m": drag, "lift_N_per_m": lift,
                "drag_deviation_pct": 100 * abs(drag - bd) / abs(bd), "lift_deviation_pct": 100 * abs(lift - bl) / abs(bl)}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        p, d, out = point["parameters"], point["derived"], point["solver_outputs"]
        q = out["imposed_flow_m3_per_s"]
        drag, lift = np.asarray(series["drag_N_per_m"]), np.asarray(series["lift_N_per_m"])
        k = int(0.9 * len(drag))
        settle = max(np.ptp(drag[k:]) / abs(drag[-1]), np.ptp(lift[k:]) / max(abs(lift[-1]), 1e-30))
        checks = [
            check("mesh", "checkMesh reports Mesh OK (1 = failed)", 0.0 if out["mesh_ok"] else 1.0, 0.5),
            *([check("flag_cells", "largest interior angle (deg) of the fluid cells touching the flag, at "
                     f"({out['flag_cell_max_angle_at_m'][0]:.4f}, {out['flag_cell_max_angle_at_m'][1]:.4f}) m (a "
                     "cell wrapped around a tip corner reads near 180)", out["flag_cell_max_angle_deg"],
                     tol.get("flag_cell_max_angle_deg", 140.0))] if "flag_cell_max_angle_deg" in out else []),
            check("converged", "SIMPLE met its residual targets (1 = stopped at the iteration limit)",
                  0.0 if out["simple_converged"] else 1.0, 0.5),
            check("forces_settled", "max over drag and lift of the spread over the last 10 % of iterations / "
                  "final value", float(settle), tol["forces_settled_max"]),
            check("inflow_profile", "max over inlet faces |U - benchmark parabola at the face centre| / (1.5 U_mean)",
                  out["inlet_profile_error_max"], tol["profile_rel_tol"]),
            check("flow_rate", "|inlet flow - U_mean H depth| / (U_mean H depth) (midpoint sampling of the parabola "
                  "on the inlet faces; shrinks with the mesh)", abs(out["inlet_flow_m3_per_s"] - q) / q,
                  tol["flow_rel_tol"]),
            check("mass_conservation", "|outlet flow - inlet flow| / inlet flow",
                  abs(out["outlet_flow_m3_per_s"] - out["inlet_flow_m3_per_s"]) / out["inlet_flow_m3_per_s"],
                  tol["mass_rel_tol"]),
            check("laminar", "Reynolds number (D) / 200 (the benchmark's steady laminar range)",
                  d["reynolds_D"] / 200, 1.0, kind="validity"),
        ]
        cfd_figure(pdir / "response.png", series, p, title=f"{point['label']}  ({out['cells']} cells, Re "
                   f"{d['reynolds_D']:.0f})")
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "cell_size_m":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: float(pt["parameters"]["cell_size_m"]))
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(np.sqrt(pt["solver_outputs"]["domain_area_m2"] / pt["solver_outputs"]["cells"]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine], "representative_sizes_m": hs}
        noise = tol.get("mesh_noise_rel", 1e-5)
        for metric, req in (("drag_N_per_m", "drag_deviation_pct"), ("lift_N_per_m", "lift_deviation_pct")):
            floor = float(noise.get(metric, 1e-5) if isinstance(noise, dict) else noise)
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine), design_order=2,
                                           noise_floor=floor)
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": req})
        return checks, detail


def cfd_figure(path, series, p, *, title):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, _style, plt

    it = np.asarray(series["iteration"])
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    fig.patch.set_facecolor(SURFACE)
    for ax, key, bkey, lab in ((axes[0], "drag_N_per_m", BENCH[0], "drag (N/m)"),
                               (axes[1], "lift_N_per_m", BENCH[1], "lift (N/m)")):
        ax.plot(it, series[key], color=SERIES_1, lw=1.2, label="OpenFOAM")
        ax.axhline(_p(p, bkey), color=SERIES_2, lw=2, ls="--", label="benchmark")
        ax.set_xlabel("SIMPLE iteration")
        ax.set_ylabel(lab)
        v = _p(p, bkey)
        ax.set_ylim(v - 0.2 * abs(v), v + 0.2 * abs(v))
        _style(ax)
        ax.legend(frameon=False, fontsize=8)
    fig.suptitle(title, fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = TurekHronCFDStudy()

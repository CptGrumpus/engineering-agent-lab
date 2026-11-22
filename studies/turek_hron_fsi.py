"""Study: Turek-Hron fluid-structure interaction (FSI1), OpenFOAM v2512 + CalculiX through preCICE.

Model:     openfoam_ccx_precice_fsi (models/fsi/turek_hron_fsi.py, run_turek_hron_fsi.sh): the verified flag of
           studies/flag_csm.py and the fluid of studies/turek_hron_cfd.py, coupled (parallel implicit, IQN-ILS)
Reference: the published FSI1 values (the requirement); internal checks: every coupling window converged, the
           steady state reached, the force the fluid puts on the flag equal to the clamp reaction in the solid
           (the coupling conserves force), the inflow equal to the benchmark parabola at every inlet face
Run-level: GCI on the requirement metrics when the sweep is fluid_cell_size_m (single-mesh runs: none)

Opt-in (FSI1 revision 1): numerics.metric_average_s takes the metrics and the force-transfer check as means over the
last that many seconds instead of the final values, and verification.steady_measure = "drift" judges steadiness by
the change of the mean between the two halves of the steady window instead of the peak-to-peak spread. The first FSI1
run showed why: at Re 20 the lift jitters at every time step (coupling noise, about +-2 % of the lift) with no drift, so
a final value and a spread both report the noise. Cases without these keys behave as before.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness import openfoam as of
from harness.backend_base import Backend, failed
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study
from studies.strut_buckling import read_dat_blocks

WRITER = "models/fsi/turek_hron_fsi.py"
RUNNER = "models/fsi/run_turek_hron_fsi.sh"
FLAG_WRITER = "models/fea/flag_ccx.py"
BENCH = ("benchmark_ux_A_m", "benchmark_uy_A_m", "benchmark_drag_N_per_m", "benchmark_lift_N_per_m")
METRICS = ("ux_A_m", "uy_A_m", "drag_N_per_m", "lift_N_per_m")
V2512_BASHRC = "/usr/lib/openfoam/openfoam2512/etc/bashrc"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_W = _load(Path(__file__).resolve().parent.parent / WRITER, "turek_hron_fsi_saved")


def _p(params, k):
    return float(params[k])


def read_forces(path: Path) -> np.ndarray:
    """OpenFOAM v2512 force.dat rows: (time, Fx_pressure, Fy_pressure, Fx_viscous, Fy_viscous).

    v2512 writes `time total_xyz pressure_xyz viscous_xyz` as plain columns. The openfoam.org v14 parser in
    studies/turek_hron_cfd.py reads `((pressure) (viscous))` instead: applied to a v2512 file it summed total +
    pressure and reported 21.6 N/m for a 14.3 N/m drag (FSI1, first evidence run)."""
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        v = [float(x) for x in line.split()]
        if len(v) != 10:
            raise ValueError(f"{path}: expected 10 columns (time, total, pressure, viscous), got {len(v)}")
        rows.append([v[0], v[4], v[5], v[7], v[8]])
    return np.array(rows)


def read_watchpoint(path: Path) -> np.ndarray:
    """preCICE watch-point log: (time, x, y, ux, uy, Fx, Fy)."""
    return np.loadtxt(path, skiprows=1, ndmin=2)


def _window_means(numerics, Ff, rf_blocks) -> dict:
    """Means of the flag's fluid force and the clamp reaction over the last numerics.metric_average_s (opt-in)."""
    w = numerics.get("metric_average_s")
    if not w or not rf_blocks:
        return {}
    t_end = float(Ff[-1, 0])
    f = Ff[Ff[:, 0] >= t_end - float(w)]
    r = np.array([b["rows"][0][:2] for b in rf_blocks if b["time"] >= t_end - float(w)])
    return {"flag_fluid_force_mean_N": [float(np.mean(f[:, 1] + f[:, 3])), float(np.mean(f[:, 2] + f[:, 4]))],
            "clamp_reaction_mean_N": [float(np.mean(r[:, 0])), float(np.mean(r[:, 1]))],
            "metric_average_s": float(w)}


def read_iterations(path: Path) -> np.ndarray:
    """preCICE iterations log: (window, total iterations, iterations, converged, ...)."""
    return np.loadtxt(path, skiprows=1, ndmin=2)


class PreciceFSI(Backend):
    sources = (WRITER, RUNNER, FLAG_WRITER)

    def __init__(self):
        from studies.cantilever import find_freecadcmd

        self.gmsh = find_freecadcmd().parent / "gmsh.exe"
        self.bashrc = os.environ.get("OPENFOAM_V2512_BASHRC", V2512_BASHRC)
        self._versions: dict = {"openfoam_bashrc": self.bashrc}

    def prepare(self, source_dir=None, log_dir=None):
        self.writer = _load(self.source_path(WRITER, source_dir), "turek_hron_fsi_run")
        self.runner = self.source_path(RUNNER, source_dir)
        r = subprocess.run([str(self.gmsh), "--version"], capture_output=True, text=True, timeout=60)
        self._versions["gmsh"] = ((r.stdout + r.stderr).strip().splitlines() or ["?"])[-1]

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="fsi_"))
        case = work / "case"
        info = self.writer.write_case(params, numerics, case)
        fl, so = case / "fluid", case / "solid"

        def files():
            keep = (sorted(fl.glob("system/*")) + sorted(fl.glob("constant/*")) + sorted(fl.glob("0/*"))
                    + sorted(fl.glob("log.*")) + sorted(fl.glob("*.log")) + [fl / "mesh.geo"]
                    + sorted(fl.glob("postProcessing/*/0/*.dat"))
                    + [so / "flag.inp", so / "config.yml", so / "flag.sta"] + sorted(so.glob("*.log"))
                    + [case / "precice-config.xml", case / "versions.txt"])
            return {str(f.relative_to(case)).replace("\\", "/"): f for f in keep
                    if f.is_file() and f.stat().st_size < 20e6}

        g = subprocess.run([str(self.gmsh), "mesh.geo", "-3", "-format", "msh22", "-o", "mesh.msh"], cwd=fl,
                           capture_output=True, text=True, timeout=3600)
        (fl / "log.gmsh").write_text(g.stdout + g.stderr, encoding="utf-8")
        if g.returncode != 0 or not (fl / "mesh.msh").exists():
            return failed("Gmsh failed") | {"files": files(), "cleanup": work}
        r = subprocess.run(of.wsl_command("bash", of.to_wsl_path(self.runner), of.to_wsl_path(case), self.bashrc),
                           capture_output=True, text=True, timeout=float(numerics.get("solver_timeout_s", 21600)))
        (fl / "mesh.msh").unlink(missing_ok=True)
        if r.returncode != 0:
            return failed(f"FSI run failed (exit {r.returncode}) {r.stderr.strip()[:300]}") | {
                "files": files(), "cleanup": work}
        for line in (case / "versions.txt").read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition("=")
            self._versions[k] = v
        d = info["depth_m"]
        wp = read_watchpoint(so / "precice-Solid-watchpoint-A.log")
        F = read_forces(fl / "postProcessing/forces/0/force.dat")
        Ff = read_forces(fl / "postProcessing/forcesFlag/0/force.dat")
        it = read_iterations(fl / "precice-Fluid-iterations.log")
        rfb = [b for b in read_dat_blocks(so / "flag.dat") if b["kind"] == "total" and b["set"] == "NFIX"]
        rf = [b["rows"][0] for b in rfb]
        chk = (fl / "log.checkMesh").read_text(encoding="utf-8")
        tdir = of.latest_time_dir(fl)
        u_in = np.asarray(of.read_patch_value(tdir / "U", "inlet"))
        y_in = np.asarray(of.read_patch_value(tdir / "C", "inlet"))[:, 1]
        U, H = _p(params, "mean_velocity_m_per_s"), self.writer.CH_H
        parabola = 1.5 * U * 4 * y_in * (H - y_in) / H**2
        series = {"t_s": wp[:, 0], "ux_A_m": wp[:, 3], "uy_A_m": wp[:, 4],
                  "drag_N_per_m": np.interp(wp[:, 0], F[:, 0], (F[:, 1] + F[:, 3]) / d),
                  "lift_N_per_m": np.interp(wp[:, 0], F[:, 0], (F[:, 2] + F[:, 4]) / d)}
        outputs = info | {"cells": int(chk.split("cells:")[1].split()[0]), "mesh_ok": "Mesh OK." in chk,
                          "windows": int(len(it)), "windows_not_converged": int(np.sum(it[:, 3] < 0.5)),
                          "coupling_iterations_mean": float(np.mean(it[:, 2])),
                          "coupling_iterations_max": int(np.max(it[:, 2])),
                          "flag_fluid_force_N": [float(Ff[-1, 1] + Ff[-1, 3]), float(Ff[-1, 2] + Ff[-1, 4])],
                          "clamp_reaction_N": [float(rf[-1][0]), float(rf[-1][1])] if rf else [float("nan")] * 2,
                          **_window_means(numerics, Ff, rfb),
                          "inlet_profile_error_max": float(np.max(np.abs(u_in[:, 0] - parabola)) / (1.5 * U))}
        return {"success": True, "message": f"uy(A) {wp[-1, 4] * 1e3:.4f} mm, drag {series['drag_N_per_m'][-1]:.3f} "
                f"N/m ({len(it)} windows, {outputs['coupling_iterations_mean']:.1f} iterations each)",
                "nfev": int(np.sum(it[:, 2])), "series": series, "outputs": outputs, "files": files(),
                "cleanup": work}

    def tool_versions(self):
        return self._versions


class TurekHronFSIStudy(Study):
    name = "turek_hron_fsi"
    models = {"openfoam_ccx_precice_fsi": PreciceFSI}
    metrics = frozenset(set(METRICS) | {m.replace("_m", "").replace("_N_per", "") + "_deviation_pct" for m in METRICS})
    param_names = _W.PARAMS + BENCH
    series_file = "history.csv"
    compare_description = "max relative difference of uy(A) over time"

    @staticmethod
    def _dev_name(metric):
        return metric.replace("_m", "").replace("_N_per", "") + "_deviation_pct"

    def derive(self, params):
        U, nu = _p(params, "mean_velocity_m_per_s"), _p(params, "kinematic_viscosity_m2_per_s")
        return {"reynolds_D": U * 2 * _W.R / nu,
                "mass_ratio": _p(params, "solid_density_kg_per_m3") / _p(params, "fluid_density_kg_per_m3")}

    def compute_metrics(self, series, params, case, outputs=None):
        w = case.get("numerics", {}).get("metric_average_s")
        if w:
            t = np.asarray(series["t_s"])
            tail = t >= t[-1] - float(w)
            out = {m: float(np.mean(np.asarray(series[m])[tail])) for m in METRICS}
        else:
            out = {m: float(np.asarray(series[m])[-1]) for m in METRICS}
        for m, b in zip(METRICS, BENCH):
            out[self._dev_name(m)] = 100 * abs(out[m] - _p(params, b)) / abs(_p(params, b))
        return out

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        p, d, out = point["parameters"], point["derived"], point["solver_outputs"]
        t = np.asarray(series["t_s"])
        tail = t >= t[-1] - tol["steady_window_s"]
        drift = tol.get("steady_measure") == "drift"
        if drift:
            def change(x):
                h = len(x) // 2
                return abs(np.mean(x[h:]) - np.mean(x[:h])) / max(abs(np.mean(x)), 1e-30)
            steady = max(float(change(np.asarray(series[m])[tail])) for m in ("uy_A_m", "drag_N_per_m", "lift_N_per_m"))
            steady_text = (f"max over uy(A), drag, lift of the change of the mean between the two halves of the last "
                           f"{tol['steady_window_s']:g} s / mean (drift, not jitter)")
        else:
            steady = max(float(np.ptp(np.asarray(series[m])[tail]) / max(abs(np.asarray(series[m])[-1]), 1e-30))
                         for m in ("uy_A_m", "drag_N_per_m", "lift_N_per_m"))
            steady_text = f"max over uy(A), drag, lift of the spread over the last {tol['steady_window_s']:g} s / final value"
        means = "flag_fluid_force_mean_N" in out
        ff = np.array(out["flag_fluid_force_mean_N" if means else "flag_fluid_force_N"])
        rf = np.array(out["clamp_reaction_mean_N" if means else "clamp_reaction_N"])
        transfer = float(np.linalg.norm(ff + rf) / np.linalg.norm(ff))
        when = f"averaged over the last {out['metric_average_s']:g} s" if means else "at the end"
        checks = [
            check("mesh", "checkMesh reports Mesh OK (1 = failed)", 0.0 if out["mesh_ok"] else 1.0, 0.5),
            check("coupling_converged", "coupling windows that hit the iteration limit without converging",
                  float(out["windows_not_converged"]), 0.5),
            check("steady", steady_text, steady, tol["steady_rel_tol"]),
            check("force_transfer", "|fluid force on the flag + clamp reaction in the solid| / |fluid force on the "
                  f"flag| {when} (the coupling conserves force)", transfer, tol["force_transfer_rel_tol"]),
            check("inflow_profile", "max over inlet faces |U - benchmark parabola| / (1.5 U_mean), after the ramp",
                  out["inlet_profile_error_max"], tol["profile_rel_tol"]),
            check("laminar", "Reynolds number (D) / 200", d["reynolds_D"] / 200, 1.0, kind="validity"),
        ]
        fsi_figure(pdir / "response.png", series, p, title=f"{point['label']}  ({out['cells']} fluid cells, "
                   f"{out['windows']} windows, {out['coupling_iterations_mean']:.1f} coupling iterations each)")
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "fluid_cell_size_m":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: float(pt["parameters"]["fluid_cell_size_m"]))
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(float(pt["parameters"]["fluid_cell_size_m"]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
        for m in METRICS:
            u = discretization_uncertainty(hs, tuple(pt["metrics"][m] for pt in fine), design_order=2)
            detail[m] = u
            checks.append(check(f"discretization_{m}", f"relative discretization uncertainty of {m}, {describe(u)}",
                                u["uncertainty"], tol["gci_max"]) | {"metric": self._dev_name(m)})
        return checks, detail


def fsi_figure(path, series, p, *, title):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, _style, plt

    t = np.asarray(series["t_s"])
    fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=True)
    fig.patch.set_facecolor(SURFACE)
    rows = ((axes[0], "uy_A_m", "benchmark_uy_A_m", "uy(A) (mm)", 1e3), (axes[1], "drag_N_per_m",
            "benchmark_drag_N_per_m", "drag (N/m)", 1.0), (axes[2], "lift_N_per_m", "benchmark_lift_N_per_m",
            "lift (N/m)", 1.0))
    for ax, key, bkey, lab, s in rows:
        ax.plot(t, np.asarray(series[key]) * s, color=SERIES_1, lw=1.2, label="OpenFOAM + CalculiX (preCICE)")
        ax.axhline(_p(p, bkey) * s, color=SERIES_2, lw=2, ls="--", label="Turek-Hron FSI1")
        ax.set_ylabel(lab)
        _style(ax)
    axes[0].legend(frameon=False, fontsize=8)
    axes[2].set_xlabel("time (s)")
    fig.suptitle(title, fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = TurekHronFSIStudy()

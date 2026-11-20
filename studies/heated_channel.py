"""Study: heated laminar coolant channel (thermal entry), OpenFOAM vs the Graetz reference.

Model:     openfoam_heated_channel (models/cfd/heated_channel_openfoam.py): 2D parallel
           plates, developed parabolic inflow, both walls at uniform heat flux over the
           heated length; temperature by the scalarTransport function object
Reference: validation/graetz.py: thermal entry solution without axial conduction
           (exact along x, 400 cells across), plus the exact energy balance
Run-level: GCI on the requirement metrics when the sweep is cells_across_gap

Wall temperature is not written by OpenFOAM for a fixedGradient patch; it is
evaluated exactly as the boundary condition does: wall-cell temperature plus
gradient (q/k) times the centre-to-wall distance.
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
from validation import graetz

WRITER = "models/cfd/heated_channel_openfoam.py"
RUNNER = "models/cfd/run_heated.sh"
STATIONS = (0.2, 0.5, 0.9)          # fractions of the heated length for the reference comparison


def _load_writer(path: Path):
    spec = importlib.util.spec_from_file_location("heated_channel_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_W = _load_writer(Path(__file__).resolve().parent.parent / WRITER)


def _p(params, k):
    return float(params[k])


def props(params):
    return dict(H=_p(params, "gap_mm") * 1e-3, U=_p(params, "mean_velocity_m_per_s"),
                rho=_p(params, "density_kg_per_m3"), cp=_p(params, "specific_heat_J_per_kgK"),
                k=_p(params, "conductivity_W_per_mK"), q=_p(params, "wall_heat_flux_W_per_m2"),
                T_in=_p(params, "inlet_temperature_C"))


class OpenFOAMHeatedChannel(Backend):
    sources = (WRITER, RUNNER)

    def __init__(self):
        self.bashrc = of.find_openfoam_bashrc()
        self._versions: dict = {"openfoam_bashrc": self.bashrc}

    def prepare(self, source_dir=None, log_dir=None):
        self.writer = _load_writer(self.source_path(WRITER, source_dir))
        self.runner = self.source_path(RUNNER, source_dir)

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="of_heated_"))
        case = work / "case"
        info = self.writer.write_case(params, numerics, case)
        r = subprocess.run(of.wsl_command("bash", of.to_wsl_path(self.runner), of.to_wsl_path(case), self.bashrc),
                           capture_output=True, text=True, timeout=7200)
        files = {str(f.relative_to(case)).replace("\\", "/"): f
                 for f in sorted(case.glob("system/*")) + sorted(case.glob("constant/*"))
                 + sorted(case.glob("0/*")) + sorted(case.glob("log.*")) + sorted(case.glob("versions.txt"))
                 if f.is_file()}
        if r.returncode != 0:
            res = failed(f"OpenFOAM stage failed (exit {r.returncode}) {r.stderr.strip()[:300]}")
            res.update(files=files, cleanup=work)
            return res
        for line in (case / "versions.txt").read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition("=")
            self._versions[k] = v
        tdir = of.latest_time_dir(case)
        n = info["cells"]
        C = of.read_internal_field(tdir / "C", n)
        flow_dir = max((d for d in case.iterdir() if (d / "U").exists() and d.name != "0"), key=lambda d: float(d.name))
        Uf = of.read_internal_field(flow_dir / "U", n)
        T = of.read_internal_field(tdir / "T", n)
        times = sorted((d for d in case.iterdir() if d.is_dir() and d.name.replace(".", "").isdigit()
                        and d.name != "0"), key=lambda d: float(d.name))
        T_prev = of.read_internal_field(times[-2] / "T", n) if len(times) >= 2 else T * np.nan
        phi_in = of.read_patch_value(flow_dir / "phi", "inlet")
        log_text = (case / "log.foamRun.temperature").read_text(encoding="utf-8")
        t_res = [float(s.split("Initial residual = ")[1].split(",")[0])
                 for s in log_text.splitlines() if "Solving for T," in s]
        series = {"x_mm": C[:, 0] * 1e3, "y_mm": C[:, 1] * 1e3, "ux_m_per_s": Uf[:, 0], "T_C": T}
        depth = info["depth_mm"] * 1e-3
        outputs = {"cells": n, "blocks": [list(b) for b in info["blocks"]], "prandtl": info["prandtl"],
                   "mesh_ok": "Mesh OK." in (case / "log.checkMesh").read_text(encoding="utf-8"),
                   "inlet_flow_m2_per_s": float(-np.sum(phi_in)) / depth,
                   "final_T_initial_residual": t_res[-1] if t_res else float("nan"),
                   "T_change_last_write_K": float(np.max(np.abs(T - T_prev))),
                   "previous_write": times[-2].name if len(times) >= 2 else None,
                   "result_time": tdir.name}
        return {"success": True, "message": f"foamRun + scalarTransport: {n} cells, {tdir.name} iterations",
                "nfev": int(float(tdir.name)), "series": series, "outputs": outputs, "files": files,
                "cleanup": work}

    def tool_versions(self):
        return self._versions


def wall_profile(series, params):
    """(x_mm, wall temperature) over the heated length, both walls averaged per column."""
    H, ny = _p(params, "gap_mm"), int(params["cells_across_gap"])
    dy = H / ny
    x, y, T = series["x_mm"], series["y_mm"], series["T_C"]
    Lh = _p(params, "heated_length_mm")
    wall = (np.abs(y - dy / 2) < 1e-6 * H) | (np.abs(y - (H - dy / 2)) < 1e-6 * H)
    heated = wall & (x > 0) & (x < Lh)
    tw = T + _p(params, "wall_heat_flux_W_per_m2") / _p(params, "conductivity_W_per_mK") * (dy / 2) * 1e-3
    xs = np.unique(np.round(x[heated], 9))
    return xs, np.array([tw[heated & (np.abs(x - xx) < 1e-6)].mean() for xx in xs])


def bulk_at(series, x_target_mm):
    x = series["x_mm"]
    xs = np.unique(np.round(x, 9))
    xc = xs[np.argmin(np.abs(xs - x_target_mm))]
    col = np.abs(x - xc) < 1e-6
    u = series["ux_m_per_s"][col]
    return float(xc), float(np.sum(u * series["T_C"][col]) / np.sum(u))


class HeatedChannelStudy(Study):
    name = "heated_channel"
    models = {"openfoam_heated_channel": OpenFOAMHeatedChannel}
    metrics = frozenset({"max_wall_temperature_C", "outlet_bulk_rise_K", "wall_temperature_end_C"})
    param_names = _W.PARAMS
    series_file = "cells.csv"
    compare_description = "max relative difference over cells"

    def derive(self, params):
        pr = props(params)
        mu = _p(params, "dynamic_viscosity_Pa_s")
        Dh = 2 * pr["H"]
        Re = pr["rho"] * pr["U"] * Dh / mu
        Pr = mu * pr["cp"] / pr["k"]
        Lh = _p(params, "heated_length_mm") * 1e-3
        return {"reynolds_Dh": Re, "prandtl": Pr, "peclet_Dh": Re * Pr,
                "graetz_x_star_end": Lh / (Dh * Re * Pr),
                "bulk_rise_exact_K": 2 * pr["q"] * Lh / (pr["rho"] * pr["cp"] * pr["U"] * pr["H"]),
                "wall_minus_bulk_fully_developed_K": graetz.wall_minus_bulk_developed(pr["q"], pr["H"], pr["k"])}

    def compute_metrics(self, series, params, case, outputs=None):
        xs, tw = wall_profile(series, params)
        x_end = _p(params, "heated_length_mm") + _p(params, "exit_length_mm")
        _, tb = bulk_at(series, x_end)
        return {"max_wall_temperature_C": float(tw.max()), "wall_temperature_end_C": float(tw[-1]),
                "outlet_bulk_rise_K": tb - _p(params, "inlet_temperature_C")}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        prm, d, m, out = point["parameters"], point["derived"], point["metrics"], point["solver_outputs"]
        pr = props(prm)
        Lh = _p(prm, "heated_length_mm")
        xs, tw = wall_profile(series, prm)
        st = np.array([xs[np.argmin(np.abs(xs - f * Lh))] for f in STATIONS])
        ref = graetz.thermal_entry(np.append(st, xs[-1]) * 1e-3, n_cells=400, **pr)
        rise = ref["T_wall"] - pr["T_in"]
        cfd = np.array([tw[np.argmin(np.abs(xs - s))] for s in st])
        err_st = float(np.max(np.abs(cfd - ref["T_wall"][:-1]) / rise[:-1]))
        err_peak = abs(m["max_wall_temperature_C"] - ref["T_wall"][-1]) / rise[-1]
        flow = pr["U"] * pr["H"]
        xc, _ = bulk_at(series, 0.0)
        col = np.abs(series["x_mm"] - xc) < 1e-6
        umax = float(np.max(series["ux_m_per_s"][col]))
        checks = [
            check("mesh", "checkMesh reports Mesh OK (1 = failed)", 0.0 if out["mesh_ok"] else 1.0, 0.5),
            check("temperature_converged", "max |T change| anywhere over the last write interval "
                  f"(iterations {out.get('previous_write')} to {out['result_time']}) / outlet bulk rise",
                  out["T_change_last_write_K"] / m["outlet_bulk_rise_K"], tol["temperature_change_rel_max"]),
            check("flow_rate", "|inlet flow - U H| / (U H)", abs(out["inlet_flow_m2_per_s"] - flow) / flow,
                  tol["flow_rel_tol"]),
            check("developed_inflow", "|peak velocity at the start of heating - 1.5 U| / 1.5 U (parabolic)",
                  abs(umax - 1.5 * pr["U"]) / (1.5 * pr["U"]), tol["profile_rel_tol"]),
            check("energy_balance", "|outlet bulk rise - 2 q L / (rho cp U H)| / exact rise",
                  abs(m["outlet_bulk_rise_K"] - d["bulk_rise_exact_K"]) / d["bulk_rise_exact_K"],
                  tol["energy_rel_tol"]),
            check("wall_temperature_reference", "max |T_wall CFD - Graetz| / (T_wall - T_in) at "
                  + ", ".join(f"{f:g}" for f in STATIONS) + " of the heated length", err_st, tol["wall_rel_tol"]),
            check("peak_vs_reference", "|peak wall temperature - Graetz at the end of heating| / rise "
                  "(model form: the reference has no axial conduction)", err_peak, tol["peak_rel_tol"]),
            check("laminar", "Reynolds number (Dh) / 2000", d["reynolds_Dh"] / 2000, 1.0, kind="validity"),
            check("reference_assumption", "100 / Peclet (the reference neglects axial conduction)",
                  100 / d["peclet_Dh"], 1.0, kind="validity"),
        ]
        heated_figure(pdir / "response.png", series, prm, xs, tw, d,
                      title=f"{point['label']}  ({out['cells']} cells, q = {pr['q'] / 1e3:g} kW/m²)")
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "cells_across_gap":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: -int(pt["parameters"]["cells_across_gap"]))
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(1.0 / int(pt["parameters"]["cells_across_gap"]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
        for metric in sorted({r["metric"] for r in case["requirements"]}):
            vals = tuple(pt["metrics"][metric] - (pt["parameters"]["inlet_temperature_C"]
                                                  if metric.endswith("_C") else 0.0) for pt in fine)
            u = discretization_uncertainty(hs, vals)
            detail[metric] = u
            checks.append(check(f"discretization_{metric}",
                                f"relative discretization uncertainty of {metric} (rise above inlet), {describe(u)}",
                                u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


def heated_figure(path, series, params, xs, tw, d, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from harness.plotting import GRID, SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2

    pr = props(params)
    xr = np.linspace(xs[0], xs[-1], 120)
    ref = graetz.thermal_entry(xr * 1e-3, n_cells=400, **pr)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2), facecolor=SURFACE)
    a1.plot(xr, ref["T_wall"], color=SERIES_2, lw=2, label="wall, Graetz reference")
    a1.plot(xs, tw, ".", ms=3, color=SERIES_1, label="wall, OpenFOAM")
    a1.plot(xr, graetz.bulk_temperature(xr * 1e-3, pr["T_in"], pr["q"], pr["H"], pr["U"], pr["rho"], pr["cp"]),
            color=TEXT_2, lw=1.2, ls="--", label="bulk, energy balance")
    a1.set_xlabel("distance from the start of heating (mm)")
    a1.set_ylabel("temperature (°C)")
    a1.set_title("Wall and bulk temperature", color=TEXT, loc="left", fontsize=10)
    nu_cfd = pr["q"] * 2 * pr["H"] / (pr["k"] * (tw - graetz.bulk_temperature(xs * 1e-3, pr["T_in"], pr["q"], pr["H"],
                                                                                 pr["U"], pr["rho"], pr["cp"])))
    a2.plot(xr, ref["Nu"], color=SERIES_2, lw=2, label="Graetz reference")
    a2.plot(xs, nu_cfd, ".", ms=3, color=SERIES_1, label="OpenFOAM")
    a2.axhline(graetz.NU_FULLY_DEVELOPED, color=TEXT_2, lw=1, ls="--", label="fully developed 140/17")
    a2.set_ylim(7, 20)
    a2.set_xlabel("distance from the start of heating (mm)")
    a2.set_ylabel("local Nusselt number (Dh)")
    a2.set_title("Heat transfer coefficient, as Nusselt number", color=TEXT, loc="left", fontsize=10)
    for ax in (a1, a2):
        ax.grid(color=GRID, lw=0.6)
        ax.legend(frameon=False, fontsize=8.5, labelcolor=TEXT_2)
        ax.tick_params(colors=TEXT_2)
        for s in ax.spines.values():
            s.set_color(GRID)
    fig.suptitle(title, color=TEXT, fontsize=10, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=130, facecolor=SURFACE)
    plt.close(fig)


STUDY = HeatedChannelStudy()

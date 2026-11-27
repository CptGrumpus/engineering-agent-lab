"""Study 11 part 2: the cold-plate passage with its side walls (fully developed cross-section), against study 11's
parallel-plate answer.

Model:     python_duct_section (models/thermal/duct_section.py): finite volumes on the quarter section, the broad wall
           as a conducting sheet (the plate: conductance k_s t_p) or one of the two bounds (H2: no spreading, H1: perfect
           spreading).
Metrics:   the broad wall's peak excess over the bulk (K) and its ratio to the parallel-plate value; the peak wall
           temperature corrected from study 11's verified 2D value: T_2D + (excess_3D - excess_2D, both fully
           developed); the share of study 11's margin it uses.
Reference: in every point, on the same grid settings: the parallel-plate limit (side wall replaced by symmetry: exact
           17/70 q H / k), Fanning fRe against the exact rectangular-duct series, and Incropera's rectangular-duct
           Nusselt numbers for four walls at one temperature (Table 8.1: 5.33 at b/a = 4, 6.49 at 8).
Run-level: GCI over cells_across_half_gap.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

from harness.backend_base import Backend, failed
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study

WRITER = "models/thermal/duct_section.py"
PARAMS = ("gap_mm", "width_mm", "cells_across_half_gap", "side_growth", "dz_max_over_dy", "bc",
          "plate_conductivity_W_per_mK", "plate_thickness_mm", "fluid_conductivity_W_per_mK", "wall_heat_flux_W_per_m2",
          "wall_temperature_2D_C", "wall_limit_C")
INCROPERA = {4.0: 5.33, 8.0: 6.49}


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def frect_exact(H: float, W: float, n: int = 400) -> float:
    """Fanning fRe of a rectangular duct, the exact series (Shah and London's form)."""
    a = min(H, W) / max(H, W)
    m = np.arange(1, 2 * n, 2)
    return float(24 / ((1 + a) ** 2 * (1 - 192 * a / np.pi ** 5 * np.sum(np.tanh(m * np.pi / (2 * a)) / m ** 5))))


class PythonDuctSection(Backend):
    sources = (WRITER,)

    def prepare(self, source_dir=None, log_dir=None):
        self.W = _load(self.source_path(WRITER, source_dir), "duct_section_saved")

    def solve(self, params, numerics, tolerance_scale=1.0):
        try:
            H, Wd = float(params["gap_mm"]), float(params["width_mm"])
            kw = dict(ny=int(params["cells_across_half_gap"]), growth=float(params["side_growth"]),
                      dz_max_over_dy=float(params["dz_max_over_dy"]))
            kp, tp, kf = (float(params[k]) for k in ("plate_conductivity_W_per_mK", "plate_thickness_mm",
                                                     "fluid_conductivity_W_per_mK"))
            bc = str(params["bc"])
            r = self.W.solve(H, Wd, bc=bc, plate_conductance_rel=kp * tp / kf if bc == "plate" else 0.0, **kw)
            pp = self.W.solve(H, Wd, bc="H2", side="symmetry", **kw)
            inc = {ar: self.W.solve(1.0, ar, bc="H1_4", **kw)["Nu"] for ar in INCROPERA}
        except Exception as e:  # noqa: BLE001
            return failed(f"{type(e).__name__}: {e}")
        scale = float(params["wall_heat_flux_W_per_m2"]) * H * 1e-3 / kf          # q H / k (K)
        outputs = {"fRe": r["fRe"], "fRe_exact": frect_exact(H, Wd), "cells": r["cells"],
                   "wall_peak_excess_rel": r["wall_peak_excess"], "wall_mean_excess_rel": r["wall_mean_excess"],
                   "peak_at_z_mm": r["peak_at_z"], "parallel_plate_excess_rel": pp["wall_peak_excess"],
                   "incropera_Nu": {str(k): v for k, v in inc.items()}, "qH_over_k_K": scale,
                   "tw_z_rel": r["tw_z"].tolist(), "zc_mm": r["zc"].tolist()}
        series = {"z_mm": r["zc"], "wall_excess_K": scale * (r["tw_z"] - (r["tw_z"].mean() - r["wall_mean_excess"]))}
        return {"success": True, "message": f"{r['cells']} cells, peak excess {scale * r['wall_peak_excess']:.3f} K",
                "nfev": None, "series": series, "outputs": outputs}

    def tool_versions(self):
        import scipy

        return {"scipy": scipy.__version__, "numpy": np.__version__}


class DuctSectionStudy(Study):
    name = "duct_section"
    models = {"python_duct_section": PythonDuctSection}
    metrics = frozenset({"wall_peak_excess_K", "peak_over_parallel_plate", "wall_peak_temperature_C",
                         "margin_used_pct"})
    param_names = PARAMS
    series_file = "broad_wall_excess.csv"
    compare_description = "max relative difference of the broad wall's excess across the width"

    def derive(self, params):
        q, H, kf = (float(params[k]) for k in ("wall_heat_flux_W_per_m2", "gap_mm", "fluid_conductivity_W_per_mK"))
        return {"parallel_plate_excess_K": 17 / 70 * q * H * 1e-3 / kf,
                "plate_conductance_rel_mm": float(params["plate_conductivity_W_per_mK"])
                * float(params["plate_thickness_mm"]) / kf,
                "study11_margin_K": float(params["wall_limit_C"]) - float(params["wall_temperature_2D_C"])}

    def compute_metrics(self, series, params, case, outputs=None):
        s = outputs["qH_over_k_K"]
        ex3, ex2 = s * outputs["wall_peak_excess_rel"], s * 17 / 70
        T = float(params["wall_temperature_2D_C"]) + ex3 - ex2
        margin = float(params["wall_limit_C"]) - float(params["wall_temperature_2D_C"])
        return {"wall_peak_excess_K": ex3, "peak_over_parallel_plate": outputs["wall_peak_excess_rel"] / (17 / 70),
                "wall_peak_temperature_C": T, "margin_used_pct": 100 * (ex3 - ex2) / margin}

    def verify_point(self, case, point, pdir, series, backend):
        tol = case["verification"]
        out = point["solver_outputs"]
        checks = [
            check("parallel_plate_limit", "|wall excess with the side wall replaced by symmetry - 17/70 q H / k| / "
                  "(17/70 q H / k) (exact)", abs(out["parallel_plate_excess_rel"] / (17 / 70) - 1), tol["exact_rel_tol"]),
            check("fRe_exact", "|Fanning fRe - the exact rectangular-duct series| / exact",
                  abs(out["fRe"] / out["fRe_exact"] - 1), tol["exact_rel_tol"]),
        ]
        for ar, ref in INCROPERA.items():
            checks.append(check(f"incropera_Nu_ar{int(ar)}", f"|Nu, four walls at one temperature, b/a = {ar:g} - "
                                f"Incropera Table 8.1 ({ref})| / {ref} (printed to 3 figures)",
                                abs(out["incropera_Nu"][str(ar)] / ref - 1), tol["table_rel_tol"]))
        section_figure(pdir / "response.png", out, point)
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "cells_across_half_gap":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: -int(pt["parameters"]["cells_across_half_gap"]))
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(1.0 / int(pt["parameters"]["cells_across_half_gap"]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
        for metric in sorted({r["metric"] for r in case["requirements"]} | {"wall_peak_excess_K"}):
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine), design_order=2,
                                           noise_floor=tol["mesh_noise_rel"])
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


def section_figure(path, out, point):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, _style, plt

    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    s = out["qH_over_k_K"]
    z = np.asarray(out["zc_mm"])
    tw = np.asarray(out["tw_z_rel"])
    tb = tw.mean() - out["wall_mean_excess_rel"]
    ax.plot(z, s * (tw - tb), color=SERIES_1, lw=1.6, label="broad wall, excess over the bulk")
    ax.axhline(s * 17 / 70, color=SERIES_2, ls="--", lw=1.1, label="parallel plates (study 11)")
    ax.set_xlabel("across the width from mid-width (mm); the side wall at the right")
    ax.set_ylabel("wall minus bulk temperature (K)")
    ax.legend(frameon=False, fontsize=8)
    fig.suptitle(f"{point['label']}: peak {s * out['wall_peak_excess_rel']:.2f} K", fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = DuctSectionStudy()

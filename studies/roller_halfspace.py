"""Study 10 part 2: the track roller's contact along its length, with its ends and its profile, by the half-space
influence-coefficient method, against study 10's long-roller (plane strain) answer.

Model:     python_roller_halfspace (models/contact/roller_halfspace.py): Boussinesq / Love on a quarter grid of the
           contact plane, the gap closed by an active set, the approach set by the load.
Metrics:   the peak contact pressure anywhere and its distance from the roller's end, the mid-length peak, and the
           peak over Hertz's long-roller value at the nominal line load.
Reference: inside every point, on the point's own grid: a long straight roller's mid-length pressure against Hertz
           line contact for the line load that section carries, and a circularly crowned roller against Hertz's
           elliptical contact (both exact for half-spaces).
Run-level: GCI over grid_scale (cells across the contact and along the roller refined together).
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
from validation import hertz

WRITER = "models/contact/roller_halfspace.py"
PROFILES = "models/fea/roller_3d.py"
PARAMS = ("roller_radius_mm", "roller_length_mm", "youngs_modulus_MPa", "poisson_ratio", "line_load_N_per_mm",
          "profile_code", "edge_radius_mm", "z_fine_mm", "crown_A_factor", "crown_zm_um", "cap_um", "grid_scale",
          "pressure_limit_MPa")
PROFILE_NAMES = {0: "none", 1: "edge", 2: "log"}


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def grid(params) -> dict:
    s = float(params["grid_scale"])
    return {"nx": int(round(24 * s)), "y_fine": 0.1 / s, "y_max_cell": 1.0 / s}


def model_params(params, R3) -> dict:
    p = {k: params[k] for k in ("roller_radius_mm", "roller_length_mm", "youngs_modulus_MPa", "poisson_ratio",
                                "line_load_N_per_mm", "edge_radius_mm", "crown_zm_um", "cap_um")}
    p["profile"] = PROFILE_NAMES[int(params["profile_code"])]
    p["z_fine_mm"] = float(params["z_fine_mm"])
    p["crown_A_um"] = float(params["crown_A_factor"]) * R3.lundberg_A_um(p)
    return p


class PythonRollerHalfspace(Backend):
    sources = (WRITER, PROFILES)

    def prepare(self, source_dir=None, log_dir=None):
        self.R3 = _load(self.source_path(PROFILES, source_dir), "roller_3d_profiles_saved")
        self.H = _load(self.source_path(WRITER, source_dir), "roller_halfspace_saved")

    def solve(self, params, numerics, tolerance_scale=1.0):
        H, R3 = self.H, self.R3
        g = grid(params)
        try:
            p = model_params(params, R3)
            r = H.solve(p, drop_um=R3.drop_um, **g)
            # references on the same grid settings
            straight = dict(p, profile="none", roller_length_mm=200.0, z_fine_mm=0.0)
            rs = H.solve(straight, drop_um=R3.drop_um, nx=g["nx"], y_fine=g["y_fine"], y_max_cell=4.0 / float(params["grid_scale"]))
            Rc = 3000.0
            E_star = 1.0 / (2 * (1 - float(p["poisson_ratio"]) ** 2) / float(p["youngs_modulus_MPa"]))
            Wc = float(p["line_load_N_per_mm"]) * 40.0
            ell = H.hertz_elliptic(Wc, float(p["roller_radius_mm"]), Rc, E_star)
            rc = H.solve(dict(p, roller_length_mm=40.0, z_fine_mm=0.0), nx=g["nx"], x_max=1.6 * ell["a_mm"],
                         y_fine=2.5 * g["y_fine"], y_max_cell=0.5 * g["y_max_cell"],
                         drop_um=lambda _p, y: 1e3 * np.asarray(y) ** 2 / (2 * Rc))
        except Exception as e:  # noqa: BLE001
            return failed(f"{type(e).__name__}: {e}")
        Pm = r["pressure_MPa"]
        yc = 0.5 * (r["yf"][1:] + r["yf"][:-1])
        along = Pm.max(axis=0)
        ref_line = hertz.line_contact(rs["mid_line_load_N_per_mm"], float(p["roller_radius_mm"]),
                                      float(p["youngs_modulus_MPa"]), float(p["poisson_ratio"]))
        outputs = {"peak_MPa": r["peak_MPa"], "peak_y_mm": r["peak_y_mm"], "mid_peak_MPa": r["mid_peak_MPa"],
                   "mid_line_load_N_per_mm": r["mid_line_load_N_per_mm"], "approach_mm": r["approach_mm"],
                   "load_error": r["load_error"], "cells": r["cells"], "crown_A_um": p["crown_A_um"], "grid": g,
                   "ref_straight_mid_MPa": rs["mid_peak_MPa"], "ref_straight_hertz_MPa": ref_line["peak_pressure_MPa"],
                   "ref_ellipse_peak_MPa": rc["peak_MPa"], "ref_ellipse_hertz_MPa": ell["p0_MPa"],
                   "ref_load_errors": [rs["load_error"], rc["load_error"]],
                   "y_mm": yc.tolist(), "peak_along_MPa": along.tolist()}
        return {"success": True, "message": f"{r['cells']} cells, peak {r['peak_MPa']:.1f} MPa", "nfev": None,
                "series": {"y_mm": yc, "peak_pressure_MPa": along}, "outputs": outputs}

    def tool_versions(self):
        import scipy

        return {"scipy": scipy.__version__, "numpy": np.__version__}


class RollerHalfspaceStudy(Study):
    name = "roller_halfspace"
    models = {"python_roller_halfspace": PythonRollerHalfspace}
    metrics = frozenset({"peak_contact_pressure_MPa", "mid_contact_pressure_MPa", "peak_from_end_mm",
                         "peak_over_long_roller"})
    param_names = PARAMS
    series_file = "pressure_along_roller.csv"
    compare_description = "max relative difference of the peak pressure along the roller"

    def derive(self, params):
        ref = hertz.line_contact(float(params["line_load_N_per_mm"]), float(params["roller_radius_mm"]),
                                 float(params["youngs_modulus_MPa"]), float(params["poisson_ratio"]))
        return {"long_roller_hertz_MPa": ref["peak_pressure_MPa"], "long_roller_half_width_mm": ref["half_width_mm"],
                "profile": PROFILE_NAMES[int(params["profile_code"])], "grid": grid(params)}

    def compute_metrics(self, series, params, case, outputs=None):
        ref = hertz.line_contact(float(params["line_load_N_per_mm"]), float(params["roller_radius_mm"]),
                                 float(params["youngs_modulus_MPa"]), float(params["poisson_ratio"]))["peak_pressure_MPa"]
        return {"peak_contact_pressure_MPa": outputs["peak_MPa"], "mid_contact_pressure_MPa": outputs["mid_peak_MPa"],
                "peak_from_end_mm": float(params["roller_length_mm"]) / 2 - outputs["peak_y_mm"],
                "peak_over_long_roller": outputs["peak_MPa"] / ref}

    def verify_point(self, case, point, pdir, series, backend):
        tol = case["verification"]
        out = point["solver_outputs"]
        checks = [
            check("hertz_line_mid", "|long straight roller's mid-length pressure - Hertz line contact for the line "
                  "load that section carries| / Hertz", abs(out["ref_straight_mid_MPa"] / out["ref_straight_hertz_MPa"] - 1),
                  tol["hertz_rel_tol"]),
            check("hertz_ellipse", "|circularly crowned roller's peak - Hertz elliptical contact| / Hertz",
                  abs(out["ref_ellipse_peak_MPa"] / out["ref_ellipse_hertz_MPa"] - 1), tol["hertz_rel_tol"]),
            check("load", "max |total contact force / target - 1| over the design and reference solves",
                  max([out["load_error"]] + out["ref_load_errors"]), tol["load_rel_tol"]),
        ]
        roller_hs_figure(pdir / "response.png", out, point)
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "grid_scale":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: -float(pt["parameters"]["grid_scale"]))
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed grid levels", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(1.0 / float(pt["parameters"]["grid_scale"]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
        for metric in sorted({r["metric"] for r in case["requirements"]}):
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine), design_order=2,
                                           noise_floor=tol["mesh_noise_rel"])
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


def roller_hs_figure(path, out, point):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, _style, plt

    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    ax.plot(out["y_mm"], out["peak_along_MPa"], "-", color=SERIES_1, lw=1.5, label="peak across the contact")
    ax.axhline(650.0, color=TEXT, ls=":", lw=0.9, label="limit 650 MPa")
    ax.axhline(point["derived"]["long_roller_hertz_MPa"], color=SERIES_2, ls="--", lw=1.0, label="long roller (Hertz)")
    ax.set_xlabel("along the roller from mid-length (mm); the end at 15")
    ax.set_ylabel("contact pressure (MPa)")
    ax.legend(frameon=False, fontsize=8)
    fig.suptitle(f"{point['label']}: peak {out['peak_MPa']:.0f} MPa", fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = RollerHalfspaceStudy()

"""Study: fatigue life of the strap with a cable hole (chained analysis).

Model:     strap_fatigue. Runs the verified strap CAD-to-FEA pipeline
           (models/fea/strap_hole.py) for the elastic hole-edge stress, then the
           fatigue model (models/fatigue/sn_6061.py): Peterson notch
           sensitivity -> K_f, Smith-Watson-Topper mean stress, Basquin S-N
           curve fitted to published 6061-T6 data.
Reference: Peterson K_t for the FE step; for the fatigue step, an independent
           high-cycle value (ASM datasheet: 96.5 MPa at 5e8 cycles, fully
           reversed) for the extrapolated S-N curve, and an exact round trip of
           the life calculation.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

from harness.checks import check
from harness.plotting import fatigue_figure
from harness.study import Study
from studies.strap_hole import CadQueryCalculiXStrap, hole_edge, ligament
from validation import stress_concentration as sc

FATIGUE_MODEL = "models/fatigue/sn_6061.py"
ASM_HCF_MPA, ASM_HCF_REVERSALS = 96.5, 1.0e9   # 5e8 cycles, R = -1 (R.R. Moore), ASM datasheet


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_SN = _load(Path(__file__).resolve().parent.parent / FATIGUE_MODEL, "sn_6061_repo")


def _p(params, k):
    return float(params[k])


class StrapFatigue(CadQueryCalculiXStrap):
    sources = CadQueryCalculiXStrap.sources + (FATIGUE_MODEL,)

    def prepare(self, source_dir=None, log_dir=None):
        super().prepare(source_dir, log_dir)
        self.sn = _load(self.source_path(FATIGUE_MODEL, source_dir), "sn_6061_saved")

    def solve(self, params, numerics, tolerance_scale=1.0):
        res = super().solve(params, numerics, tolerance_scale)
        if not res["success"]:
            return res
        s = res["series"]
        W, d, t = _p(params, "width_mm"), _p(params, "hole_diameter_mm"), _p(params, "thickness_mm")
        F_max, F_min = _p(params, "axial_load_N"), _p(params, "min_load_N")
        sn_max = sc.net_stress(F_max, W, d, t)
        peak = float(np.max(s["sxx_MPa"][hole_edge(s, params)]))
        kt = peak / sn_max                                    # elastic, from the FE
        kf = self.sn.fatigue_notch_factor(kt, d / 2)
        smax, smin = kf * sn_max, kf * sc.net_stress(F_min, W, d, t)
        sar = self.sn.swt_amplitude(smax, smin)
        fit = self.sn.fit_basquin(str(params["sn_data_set"]))
        life = self.sn.life_cycles(sar, fit)
        others = {ds: self.sn.life_cycles(sar, self.sn.fit_basquin(ds))
                  for ds in self.sn.DATA_SETS}
        res["outputs"].update({
            "kt_net_fe": kt, "notch_sensitivity_q": self.sn.notch_sensitivity(d / 2), "kf": kf,
            "notch_max_stress_MPa": smax, "notch_min_stress_MPa": smin, "swt_amplitude_MPa": sar,
            "sn_fit": fit, "fatigue_life_cycles": life,
            "life_by_data_set": others,
            "sn_fit_at_hcf_anchor_MPa": self.sn.amplitude_at(ASM_HCF_REVERSALS, fit),
            "round_trip_amplitude_MPa": self.sn.amplitude_at(2 * life, fit)})
        res["message"] += f"; fatigue life {life:.3g} cycles"
        return res


class StrapFatigueStudy(Study):
    name = "strap_fatigue"
    models = {"strap_fatigue": StrapFatigue}
    metrics = frozenset({"fatigue_life_cycles", "notch_max_stress_MPa", "kt_net_fe"})
    param_names = tuple(_load(Path(__file__).resolve().parent.parent / "models/fea/strap_hole.py",
                              "strap_hole_params").PARAMS) + ("min_load_N", "sn_data_set")
    series_file = "nodal_results.csv"
    compare_description = "max relative difference over nodal columns"

    def derive(self, params):
        W, d, t = _p(params, "width_mm"), _p(params, "hole_diameter_mm"), _p(params, "thickness_mm")
        F = _p(params, "axial_load_N")
        if str(params["sn_data_set"]) not in _SN.DATA_SETS:
            raise ValueError(f"sn_data_set must be one of {sorted(_SN.DATA_SETS)}")
        if _p(params, "min_load_N") < 0 or _p(params, "min_load_N") >= F:
            raise ValueError("need 0 <= min_load_N < axial_load_N")
        return {"gross_stress_MPa": sc.gross_stress(F, W, t),
                "net_stress_MPa": sc.net_stress(F, W, d, t),
                "kt_net_peterson": sc.kt_net(d, W)}

    def compute_metrics(self, series, params, case, outputs=None):
        return {"fatigue_life_cycles": outputs["fatigue_life_cycles"],
                "notch_max_stress_MPa": outputs["notch_max_stress_MPa"],
                "kt_net_fe": outputs["kt_net_fe"]}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        p, d, m, out = (point["parameters"], point["derived"], point["metrics"],
                        point["solver_outputs"])
        F, t = _p(p, "axial_load_N"), _p(p, "thickness_mm")
        half = F / 2
        rf = out.get("reaction_totals_N", {}).get("XSYM")
        eq = abs(rf[0] / out["force_scale"] + half) / half if rf else float("inf")
        y, sxx = ligament(series)
        from scipy.integrate import simpson
        lig = abs(float(simpson(sxx, x=y)) * t - half) / half
        fit = out["sn_fit"]
        checks = [
            check("equilibrium", "|reaction on the x = 0 symmetry edge + F/2| / (F/2)",
                  eq, tol["equilibrium_rel_tol"]),
            check("ligament_force", "|t * integral of sigma_xx across the ligament - F/2| / (F/2)",
                  lig, tol["ligament_force_rel_tol"]),
            check("kt_reference", "|Kt_net FE - Peterson| / Peterson (model form)",
                  abs(m["kt_net_fe"] - d["kt_net_peterson"]) / d["kt_net_peterson"], tol["kt_rel_tol"]),
            check("sn_hcf_crosscheck",
                  "|fitted S-N amplitude at 1e9 reversals - ASM 96.5 MPa| / 96.5 (independent high-cycle value)",
                  abs(out["sn_fit_at_hcf_anchor_MPa"] - ASM_HCF_MPA) / ASM_HCF_MPA,
                  tol["hcf_crosscheck_rel_tol"]),
            check("sn_fit_scatter", "standard deviation of log(stress) residuals of the S-N fit",
                  fit["log_scatter_sd"], tol["sn_scatter_max"]),
            check("life_round_trip", "|S-N amplitude at the computed life - SWT amplitude| / SWT amplitude",
                  abs(out["round_trip_amplitude_MPa"] - out["swt_amplitude_MPa"]) / out["swt_amplitude_MPa"],
                  tol["round_trip_rel_tol"]),
            check("elastic_notch", "notch peak stress / yield (elastic notch analysis valid below 1)",
                  out["notch_max_stress_MPa"] / _p(p, "yield_strength_MPa"), 1.0, kind="validity"),
        ]
        req = next((r["limit"] for r in case["requirements"] if r["metric"] == "fatigue_life_cycles"), None)
        fatigue_figure(pdir / "response.png", _SN, out, req,
                       title=f"{point['label']}  (0 -> {F / 1000:g} kN, K_f {out['kf']:.3f})")
        return checks


STUDY = StrapFatigueStudy()

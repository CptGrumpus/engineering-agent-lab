"""Study: cantilever beam, 3D solid FEA (FreeCAD + Gmsh + CalculiX).

Model:     cantilever_freecad  (models/fea/cantilever_freecad.py, run by freecadcmd)
Reference: Timoshenko beam theory with Cowper shear coefficient (validation/beam_theory.py)
Run-level: Grid Convergence Index over the three finest meshes (harness/convergence.py)

The sweep parameter is normally mesh_size_mm, which makes each run a
mesh-refinement study.
"""

from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness.backend_base import Backend, failed
from harness.calculix import read_dat_total_forces, read_frd
from harness.checks import check
from harness.convergence import discretization_uncertainty
from harness.plotting import cantilever_figure
from harness.study import Study
from validation import beam_theory as beam

PARAMS = ("length_mm", "width_mm", "height_mm", "youngs_modulus_MPa", "poisson_ratio",
          "yield_strength_MPa", "tip_load_N", "mesh_size_mm", "element_order")


def find_freecadcmd() -> Path:
    cands = []
    if os.environ.get("FREECADCMD"):
        cands.append(Path(os.environ["FREECADCMD"]))
    for base in (os.environ.get("LOCALAPPDATA", ""), "C:/Program Files"):
        cands += [Path(p) for p in sorted(glob.glob(f"{base}/Programs/FreeCAD*/bin/freecadcmd.exe")
                                          + glob.glob(f"{base}/FreeCAD*/bin/freecadcmd.exe"),
                                          reverse=True)]
    for c in cands:
        if c.exists():
            return c
    raise RuntimeError("freecadcmd not found: install FreeCAD or set FREECADCMD")


class FreeCADCantilever(Backend):
    sources = ("models/fea/cantilever_freecad.py",)

    def __init__(self):
        self.exe = find_freecadcmd()
        self.script: Path | None = None
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        self.script = self.source_path(self.sources[0], source_dir)
        ccx = self.exe.parent / "ccx.exe"
        ver = subprocess.run([str(ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"freecadcmd": str(self.exe),
                          "CalculiX": (ver.stdout.strip().splitlines() or ["?"])[-1]}

    def solve(self, params, numerics, tolerance_scale=1.0):
        # tolerance_scale is ignored: CalculiX's linear static solve is direct (SPOOLES)
        work = Path(tempfile.mkdtemp(prefix="ccx_cantilever_"))
        inp = {k: params[k] for k in PARAMS if k != "yield_strength_MPa"}
        inp["workdir"] = str(work)
        (work / "input.json").write_text(json.dumps(inp), encoding="utf-8")
        env = dict(os.environ, CANTILEVER_INPUT=str(work / "input.json"))
        r = subprocess.run([str(self.exe), str(self.script)], cwd=work, env=env,
                           capture_output=True, text=True, timeout=3600)
        (work / "freecad_stdout.log").write_text(r.stdout + r.stderr, encoding="utf-8")
        summary_file = work / "freecad_summary.json"
        if not summary_file.exists():
            return failed(f"freecadcmd produced no summary (exit {r.returncode})")
        summary = json.loads(summary_file.read_text(encoding="utf-8"))
        if not summary.get("ok"):
            return failed(summary.get("error", "FreeCAD script failed"))
        self._versions["FreeCAD"] = summary.get("freecad_version")
        stem = Path(summary["inp_file"]).stem
        frd, dat = work / f"{stem}.frd", work / f"{stem}.dat"
        if not frd.exists():
            return failed("CalculiX produced no .frd results")

        res = read_frd(frd)
        order = np.argsort(res["nodes"])
        ids = res["nodes"][order]
        disp, stress = res["DISP"], res["STRESS"]
        assert np.array_equal(np.sort(disp["ids"]), ids) and np.array_equal(np.sort(stress["ids"]), ids)
        di, si = np.argsort(disp["ids"]), np.argsort(stress["ids"])
        series = {"node_id": ids.astype(float),
                  "x_mm": res["coords"][order, 0], "y_mm": res["coords"][order, 1],
                  "z_mm": res["coords"][order, 2],
                  "ux_mm": disp["D1"][di], "uy_mm": disp["D2"][di], "uz_mm": disp["D3"][di]}
        for c in ("SXX", "SYY", "SZZ", "SXY", "SYZ", "SZX"):
            series[f"{c.lower()}_MPa"] = stress[c][si]
        totals = read_dat_total_forces(dat) if dat.exists() else {}
        outputs = {"nodes": summary["nodes"], "volume_elements": summary["volumes"],
                   "dof": 3 * summary["nodes"], "load_direction": summary["load_direction"],
                   "reaction_totals_N": totals}
        files = {name: work / name for name in
                 (f"{stem}.inp", f"{stem}.dat", f"{stem}.sta", "cantilever.FCStd",
                  "freecad_summary.json", "freecad_stdout.log") if (work / name).exists()}
        return {"success": True, "message": f"CalculiX: {summary['volumes']} elements",
                "nfev": None, "series": series, "outputs": outputs, "files": files,
                "cleanup": work}

    def tool_versions(self):
        return self._versions


def von_mises(s: dict) -> np.ndarray:
    sxx, syy, szz = s["sxx_MPa"], s["syy_MPa"], s["szz_MPa"]
    sxy, syz, szx = s["sxy_MPa"], s["syz_MPa"], s["szx_MPa"]
    return np.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
                   + 3 * (sxy**2 + syz**2 + szx**2))


def _f(params, k):
    return float(params[k])


class CantileverStudy(Study):
    name = "cantilever"
    models = {"cantilever_freecad": FreeCADCantilever}
    metrics = frozenset({"tip_deflection_mm", "root_bending_stress_MPa", "max_von_mises_MPa"})
    param_names = PARAMS
    series_file = "nodal_results.csv"
    compare_description = "max relative difference over nodal columns"

    def derive(self, params):
        L, b, h = _f(params, "length_mm"), _f(params, "width_mm"), _f(params, "height_mm")
        E, nu, F = _f(params, "youngs_modulus_MPa"), _f(params, "poisson_ratio"), _f(params, "tip_load_N")
        if min(L, b, h, E, F) <= 0 or not 0 <= nu < 0.5:
            raise ValueError("dimensions, modulus, and load must be positive; 0 <= nu < 0.5")
        if params["element_order"] not in ("1st", "2nd"):
            raise ValueError("element_order must be '1st' or '2nd'")
        return {
            "slenderness_L_over_h": L / h,
            "tip_deflection_euler_bernoulli_mm": beam.euler_bernoulli_tip(F, L, E, b, h),
            "tip_deflection_timoshenko_mm": beam.timoshenko_tip(F, L, E, nu, b, h),
            "root_bending_stress_beam_theory_MPa": beam.bending_stress(F, L, b, h),
        }

    def compute_metrics(self, series, params, case, outputs=None):
        L, h = _f(params, "length_mm"), _f(params, "height_mm")
        x, z = series["x_mm"], series["z_mm"]
        tip = np.isclose(x, L, atol=1e-6)
        # root stress: fit sigma_xx along the top fibre away from the clamp and the
        # load (St-Venant), then extrapolate the linear moment distribution to x = 0
        top = np.isclose(z, h, atol=1e-6) & (x >= 0.25 * L) & (x <= 0.75 * L)
        slope, intercept = np.polyfit(x[top], series["sxx_MPa"][top], 1)
        return {
            "tip_deflection_mm": float(-np.mean(series["uz_mm"][tip])),
            "root_bending_stress_MPa": float(intercept),
            "max_von_mises_MPa": float(np.max(von_mises(series))),
        }

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        p = point["parameters"]
        d = point["derived"]
        m = point["metrics"]
        F = _f(p, "tip_load_N")
        out = point.get("solver_outputs", {})
        totals = out.get("reaction_totals_N", {})
        rf = next(iter(totals.values()), None)

        checks = []
        if rf is None:
            checks.append(check("equilibrium", "reaction totals missing from .dat",
                                float("inf"), tol["equilibrium_rel_tol"]))
        else:
            # reaction must balance the applied -z load: R = (0, 0, +F)
            resid = np.linalg.norm(np.array(rf) - np.array([0.0, 0.0, F])) / F
            checks.append(check("equilibrium", "|R_fixed - (0, 0, F)| / F (sum of reactions)",
                                resid, tol["equilibrium_rel_tol"]))
        checks += [
            check("tip_deflection_reference",
                  "|tip deflection FE - Timoshenko| / Timoshenko",
                  abs(m["tip_deflection_mm"] - d["tip_deflection_timoshenko_mm"])
                  / d["tip_deflection_timoshenko_mm"], tol["deflection_rel_tol"]),
            check("root_stress_reference",
                  "|extrapolated root stress FE - 6FL/(bh^2)| / beam theory",
                  abs(m["root_bending_stress_MPa"] - d["root_bending_stress_beam_theory_MPa"])
                  / d["root_bending_stress_beam_theory_MPa"], tol["stress_rel_tol"]),
            check("linear_material",
                  "root bending stress / yield strength (linear elastic only below 1)",
                  m["root_bending_stress_MPa"] / _f(p, "yield_strength_MPa"), 1.0,
                  kind="validity"),
            check("small_deflection",
                  "tip deflection / length (geometrically linear analysis)",
                  m["tip_deflection_mm"] / _f(p, "length_mm"), tol["small_deflection_max"],
                  kind="validity"),
        ]
        cantilever_figure(pdir / "response.png", series, p, d, m,
                          title=f"{point['label']}  ({out.get('volume_elements', '?')} "
                                f"{p['element_order']}-order tets, {out.get('dof', '?')} DOF)")
        return checks

    def verify_run_level(self, case, manifest, points):
        """GCI on the three finest completed meshes (needs mesh_size_mm sweep)."""
        tol = case["verification"]
        done = [pt for pt in manifest["points"] if pt["status"] == "completed"]
        done.sort(key=lambda pt: pt["parameters"]["mesh_size_mm"])
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels",
                          float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(float(pt["parameters"]["mesh_size_mm"]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
        for metric, key in (("tip_deflection_mm", "gci_deflection_max"),
                            ("root_bending_stress_MPa", "gci_stress_max")):
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine))
            detail[metric] = u
            if u["regime"] == "monotone":
                how = (f"monotone (R = {u['convergence_ratio']:.3f}): GCI_fine, observed order "
                       f"{u['order']:.2f}, extrapolated {u['extrapolated']:.6g}")
            elif u["regime"] == "oscillatory":
                how = (f"oscillatory (R = {u['convergence_ratio']:.3f}): 1.25 x half-range of "
                       f"the 3 finest solutions")
            else:
                how = u["regime"]
            checks.append(check(f"discretization_{metric}",
                                f"relative discretization uncertainty of {metric}, {how}",
                                u["uncertainty"], tol[key]))
        return checks, detail


STUDY = CantileverStudy()

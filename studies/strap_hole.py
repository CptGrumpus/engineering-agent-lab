"""Study: strap with a central cable hole, CAD-to-FEA pipeline.

Model:     cadquery_ccx_strap (models/fea/strap_hole.py): CadQuery quarter face
           -> STEP -> Gmsh (6-node triangles, refined at the hole) -> CalculiX
           plane stress
Reference: Peterson's stress concentration factor (validation/stress_concentration.py)
Run-level: GCI on every requirement metric when the sweep is the hole-edge
           element size (design order 2)

The peak at a smooth hole edge converges with refinement, unlike the peak at a
sharp corner; the GCI with the design-order test is what demonstrates it.
"""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from scipy.integrate import simpson

from harness.backend_base import Backend, failed
from harness.calculix import read_dat_total_forces, read_frd
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.plotting import strap_figure
from harness.study import Study
from validation import stress_concentration as sc

WRITER = "models/fea/strap_hole.py"


def _load_writer(path: Path):
    spec = importlib.util.spec_from_file_location("strap_hole_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_W = _load_writer(Path(__file__).resolve().parent.parent / WRITER)
PARAMS = _W.PARAMS


def _p(params, k):
    return float(params[k])


class CadQueryCalculiXStrap(Backend):
    sources = (WRITER,)

    def __init__(self):
        from studies.cantilever import find_freecadcmd

        bin_dir = find_freecadcmd().parent
        self.gmsh, self.ccx = bin_dir / "gmsh.exe", bin_dir / "ccx.exe"
        for exe in (self.gmsh, self.ccx):
            if not exe.exists():
                raise RuntimeError(f"{exe.name} not found next to freecadcmd")
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        import cadquery

        self.writer = _load_writer(self.source_path(WRITER, source_dir))
        g = subprocess.run([str(self.gmsh), "--version"], capture_output=True, text=True, timeout=60)
        c = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"cadquery": cadquery.__version__,
                          "gmsh": (g.stdout + g.stderr).strip().splitlines()[-1],
                          "CalculiX": (c.stdout.strip().splitlines() or ["?"])[-1]}

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="strap_hole_"))
        keep = ("quarter.step", "mesh.geo", "mesh.inp", "job.inp", "job.dat", "job.sta",
                "gmsh.log", "ccx.log")

        def files():
            return {n: work / n for n in keep if (work / n).exists()}

        try:
            area = self.writer.build_step(params, work / "quarter.step")
            self.writer.write_geo(params, work / "mesh.geo")
            g = subprocess.run([str(self.gmsh), "mesh.geo", "-2", "-format", "inp", "-o", "mesh.inp"],
                               cwd=work, capture_output=True, text=True, timeout=600)
            (work / "gmsh.log").write_text(g.stdout + g.stderr, encoding="utf-8")
            if g.returncode != 0 or not (work / "mesh.inp").exists():
                res = failed(f"gmsh failed (exit {g.returncode})")
                res.update(files=files(), cleanup=work)
                return res
            info = self.writer.write_deck(params, work / "mesh.inp", work / "job.inp")
            c = subprocess.run([str(self.ccx), "-i", "job"], cwd=work, capture_output=True,
                               text=True, timeout=3600)
            (work / "ccx.log").write_text(c.stdout + c.stderr, encoding="utf-8")
            if c.returncode != 0 or not (work / "job.frd").exists():
                res = failed(f"CalculiX failed (exit {c.returncode}); see ccx.log")
                res.update(files=files(), cleanup=work)
                return res
        except Exception as e:  # geometry or deck errors are evidence too
            res = failed(f"{type(e).__name__}: {e}")
            res.update(files=files(), cleanup=work)
            return res

        r = read_frd(work / "job.frd")
        order = np.argsort(r["nodes"])
        ids, xyz = r["nodes"][order], r["coords"][order]
        disp, stress = r["DISP"], r["STRESS"]
        di, si = np.argsort(disp["ids"]), np.argsort(stress["ids"])
        series = {"node_id": ids.astype(float), "x_mm": xyz[:, 0], "y_mm": xyz[:, 1],
                  "ux_mm": disp["D1"][di], "uy_mm": disp["D2"][di],
                  "sxx_MPa": stress["SXX"][si], "syy_MPa": stress["SYY"][si],
                  "sxy_MPa": stress["SXY"][si]}
        mesh_text = (work / "mesh.inp").read_text(encoding="utf-8")
        n_elem = sum(1 for ln in mesh_text.split("*ELEMENT", 1)[1].split("*", 1)[0].splitlines()
                     if ln.strip() and ln.strip()[0].isdigit())
        outputs = {**info, "elements": n_elem, "face_area_mm2": area,
                   "hole_element_size_used_mm": self.writer.hole_element_size(params),
                   "reaction_totals_N": read_dat_total_forces(work / "job.dat")}
        return {"success": True, "message": f"CalculiX: {n_elem} CPS6 elements",
                "nfev": None, "series": series, "outputs": outputs, "files": files(),
                "cleanup": work}

    def tool_versions(self):
        return self._versions


def hole_edge(series, params):
    r = _p(params, "hole_diameter_mm") / 2
    return np.abs(np.hypot(series["x_mm"], series["y_mm"]) - r) < 1e-4 * r


def ligament(series):
    lig = np.isclose(series["x_mm"], 0.0, atol=1e-6)
    o = np.argsort(series["y_mm"][lig])
    return series["y_mm"][lig][o], series["sxx_MPa"][lig][o]


class StrapHoleStudy(Study):
    name = "strap_hole"
    models = {"cadquery_ccx_strap": CadQueryCalculiXStrap}
    metrics = frozenset({"peak_hole_stress_MPa", "kt_net"})
    param_names = PARAMS
    series_file = "nodal_results.csv"
    compare_description = "max relative difference over nodal columns"

    def derive(self, params):
        W, d, t = _p(params, "width_mm"), _p(params, "hole_diameter_mm"), _p(params, "thickness_mm")
        F, L = _p(params, "axial_load_N"), _p(params, "length_mm")
        if min(W, d, t, F, L) <= 0 or d >= W:
            raise ValueError("positive dimensions and load; hole smaller than the width")
        return {"d_over_W": d / W,
                "gross_stress_MPa": sc.gross_stress(F, W, t),
                "net_stress_MPa": sc.net_stress(F, W, d, t),
                "kt_net_peterson": sc.kt_net(d, W),
                "peak_stress_peterson_MPa": sc.peak_stress(F, W, d, t),
                "end_distance_over_width": (L / 2 - d / 2) / W,
                "face_area_closed_form_mm2": L / 2 * W / 2 - np.pi * d**2 / 16}

    def compute_metrics(self, series, params, case, outputs=None):
        edge = hole_edge(series, params)
        peak = float(np.max(series["sxx_MPa"][edge]))
        sn = sc.net_stress(_p(params, "axial_load_N"), _p(params, "width_mm"),
                           _p(params, "hole_diameter_mm"), _p(params, "thickness_mm"))
        return {"peak_hole_stress_MPa": peak, "kt_net": peak / sn}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        p, d, m, out = (point["parameters"], point["derived"], point["metrics"],
                        point["solver_outputs"])
        F, t, W2 = _p(p, "axial_load_N"), _p(p, "thickness_mm"), _p(p, "width_mm") / 2
        half = F / 2
        rf = out.get("reaction_totals_N", {}).get("XSYM")
        # the deck analyses a thin layer with scaled forces (true plane stress);
        # scale its reaction back to the real plate
        eq = abs(rf[0] / out["force_scale"] + half) / half if rf else float("inf")
        far = np.isclose(series["x_mm"], _p(p, "length_mm") / 2, atol=1e-6)
        far_err = float(np.max(np.abs(series["sxx_MPa"][far] - d["gross_stress_MPa"]))
                        / d["gross_stress_MPa"])
        y, sxx = ligament(series)
        lig_force = float(simpson(sxx, x=y)) * t
        checks = [
            check("cad_area", "|face area from CadQuery - closed form| / closed form",
                  abs(out["face_area_mm2"] - d["face_area_closed_form_mm2"])
                  / d["face_area_closed_form_mm2"], 1e-9),
            check("applied_load", "|load written to the deck - F/2| / (F/2)",
                  abs(out["applied_load_N"] - half) / half, tol["equilibrium_rel_tol"]),
            check("equilibrium", "|reaction on the x = 0 symmetry edge + F/2| / (F/2)",
                  eq, tol["equilibrium_rel_tol"]),
            check("ligament_force", "|t * integral of sigma_xx across the ligament - F/2| / (F/2)",
                  abs(lig_force - half) / half, tol["ligament_force_rel_tol"]),
            check("far_field_uniform", "max |sigma_xx at the loaded end - gross stress| / gross",
                  far_err, tol["far_field_rel_tol"]),
            check("kt_reference", "|Kt_net FE - Peterson| / Peterson (model form)",
                  abs(m["kt_net"] - d["kt_net_peterson"]) / d["kt_net_peterson"],
                  tol["kt_rel_tol"]),
            check("linear_material", "peak hole-edge stress / yield strength",
                  m["peak_hole_stress_MPa"] / _p(p, "yield_strength_MPa"), 1.0, kind="validity"),
        ]
        strap_figure(pdir / "response.png", series, p, d, m,
                     title=f"{point['label']}  ({out['elements']} quadratic triangles, "
                           f"hole elements {out['hole_element_size_used_mm']:.3g} mm)")
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "hole_element_size_mm":
            return [], {}
        tol = case["verification"]
        done = [pt for pt in manifest["points"] if pt["status"] == "completed"]
        done.sort(key=lambda pt: pt["parameters"]["hole_element_size_mm"])
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels",
                          float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(float(pt["parameters"]["hole_element_size_mm"]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
        for metric in sorted({r["metric"] for r in case["requirements"]} | {"kt_net"}):
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine),
                                           design_order=2)  # quadratic triangles
            detail[metric] = u
            checks.append(check(f"discretization_{metric}",
                                f"relative discretization uncertainty of {metric}, {describe(u)}",
                                u["uncertainty"], tol["gci_peak_max"]) | {"metric": metric})
        return checks, detail


STUDY = StrapHoleStudy()

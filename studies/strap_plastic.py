"""Study: strap with a central hole under a proof load beyond notch yield, then unloaded.

Model:     cadquery_ccx_strap_plastic: the strap CAD-to-FEA pipeline (models/fea/strap_hole.py:
           CadQuery quarter face -> STEP -> Gmsh 6-node triangles refined at the hole) with
           CalculiX isotropic-hardening plasticity (models/fea/strap_plastic.py): load to the
           proof load, unload to zero; plus an elastic run at the proof load on the same mesh
References (validation/, independent of the FE path):
           Peterson Kt (stress_concentration.py) for the elastic peak; Neuber's rule and Glinka's
           strain-energy method (notch_plasticity.py) bracketing the notch-root strain; the
           residual stress by elastic unloading, s_res = s_max - s_e (both from the Neuber state
           and, exactly, from the FE's own two runs)
Run-level: GCI on the requirement metrics when the sweep is hole_element_ratio

Notch root: the hole-edge node on the x = 0 symmetry line (y = r), where the peak stress and
strain sit; values are the .frd nodal (extrapolated) stress and total strain, xx components (the
stress there is uniaxial: a free surface).
"""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness.backend_base import Backend, failed
from harness.calculix import read_frd
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study
from studies.strut_buckling import read_dat_blocks
from validation import notch_plasticity as npl
from validation import stress_concentration as sc

GEOM = "models/fea/strap_hole.py"
WRITER = "models/fea/strap_plastic.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_ROOT = Path(__file__).resolve().parent.parent
_G = _load(_ROOT / GEOM, "strap_geom_saved")
_W = _load(_ROOT / WRITER, "strap_plastic_saved")
PARAMS = ("length_mm", "width_mm", "thickness_mm", "hole_diameter_mm", "axial_load_N", "youngs_modulus_MPa",
          "poisson_ratio", "far_element_size_mm", "hole_element_ratio") + _W.PARAMS_PLASTIC


def _p(params, k):
    return float(params[k])


def material(params) -> npl.Material:
    return npl.Material(_p(params, "youngs_modulus_MPa"), params["plastic_strain"], params["plastic_stress_MPa"])


def net_stress(params):
    return sc.net_stress(_p(params, "axial_load_N"), _p(params, "width_mm"), _p(params, "hole_diameter_mm"),
                         _p(params, "thickness_mm"))


class CadQueryCalculiXStrapPlastic(Backend):
    sources = (GEOM, WRITER)

    def __init__(self):
        from studies.cantilever import find_freecadcmd

        bin_dir = find_freecadcmd().parent
        self.gmsh, self.ccx = bin_dir / "gmsh.exe", bin_dir / "ccx.exe"
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        import cadquery

        self.geom = _load(self.source_path(GEOM, source_dir), "strap_geom_run")
        self.writer = _load(self.source_path(WRITER, source_dir), "strap_plastic_run")
        g = subprocess.run([str(self.gmsh), "--version"], capture_output=True, text=True, timeout=60)
        c = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"cadquery": cadquery.__version__, "gmsh": (g.stdout + g.stderr).strip().splitlines()[-1],
                          "CalculiX": (c.stdout.strip().splitlines() or ["?"])[-1]}

    def _ccx(self, work, job):
        r = subprocess.run([str(self.ccx), "-i", job], cwd=work, capture_output=True, text=True, timeout=7200)
        (work / f"{job}.log").write_text(r.stdout + r.stderr, encoding="utf-8")
        return r.returncode == 0 and "Job finished" in r.stdout

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="strap_plastic_"))
        g, w = self.geom, self.writer
        keep = ("quarter.step", "mesh.geo", "mesh.inp", "elastic.inp", "elastic.dat", "plastic.inp", "plastic.dat",
                "plastic.sta", "gmsh.log", "elastic.log", "plastic.log")

        def files():
            return {n: work / n for n in keep if (work / n).exists()}

        p = dict(params)
        p.setdefault("hole_element_size_mm", 0.0)
        p.setdefault("yield_strength_MPa", float(params["plastic_stress_MPa"][0]))
        try:
            g.build_step(p, work / "quarter.step")
            g.write_geo(p, work / "mesh.geo")
            r = subprocess.run([str(self.gmsh), "mesh.geo", "-2", "-format", "inp", "-o", "mesh.inp"], cwd=work,
                               capture_output=True, text=True, timeout=1800)
            (work / "gmsh.log").write_text(r.stdout + r.stderr, encoding="utf-8")
            if r.returncode != 0:
                return failed("gmsh failed") | {"files": files(), "cleanup": work}
            g.write_deck(p, work / "mesh.inp", work / "elastic.inp")
            info = w.write_plastic_deck(p, work / "mesh.inp", work / "plastic.inp", g.read_mesh_nodes,
                                        g.ANALYSIS_THICKNESS_RATIO, g.TOL)
            for job in ("elastic", "plastic"):
                if not self._ccx(work, job):
                    return failed(f"CalculiX {job} run failed") | {"files": files(), "cleanup": work}
        except Exception as e:
            return failed(f"{type(e).__name__}: {e}") | {"files": files(), "cleanup": work}

        el = read_frd(work / "elastic.frd")
        pl = read_frd(work / "plastic.frd")
        r = float(params["hole_diameter_mm"]) / 2
        W2 = float(params["width_mm"]) / 2
        nodes, xyz = el["nodes"], el["coords"]
        lig = np.where(np.isclose(xyz[:, 0], 0.0, atol=1e-6) & (xyz[:, 1] >= r - 1e-6))[0]
        lig = lig[np.argsort(xyz[lig, 1])]
        lig_ids = nodes[lig]
        root = int(lig_ids[0])
        if abs(xyz[lig[0], 1] - r) > 1e-6:
            return failed("no node at the hole edge on the symmetry line") | {"files": files(), "cleanup": work}

        def at(block, comp, ids):
            m = dict(zip(block["ids"].tolist(), block[comp].tolist()))
            return np.array([m[int(i)] for i in ids])

        steps = {name: [b for n, b in pl["blocks"] if n == name] for name in ("STRESS", "TOSTRAIN", "PE")}
        if any(len(v) != 2 for v in steps.values()):
            return failed(f"expected two steps of output, got {[len(v) for v in steps.values()]}") | {
                "files": files(), "cleanup": work}
        rf = [b["rows"][0].tolist() for b in read_dat_blocks(work / "plastic.dat") if b["kind"] == "total"]
        series = {"y_mm": xyz[lig, 1], "sxx_elastic_MPa": at(el["STRESS"], "SXX", lig_ids),
                  "sxx_proof_MPa": at(steps["STRESS"][0], "SXX", lig_ids),
                  "exx_proof": at(steps["TOSTRAIN"][0], "EXX", lig_ids),
                  "peeq_proof": at(steps["PE"][0], "PE", lig_ids),
                  "sxx_residual_MPa": at(steps["STRESS"][1], "SXX", lig_ids)}
        outputs = {**info, "root_node": root, "ligament_nodes": int(len(lig)),
                   "reaction_x_proof_N": rf[0][0] / info["force_scale"] if rf else float("nan"),
                   "reaction_x_unloaded_N": rf[-1][0] / info["force_scale"] if len(rf) > 1 else float("nan"),
                   "ligament_width_mm": W2 - r}
        return {"success": True, "message": f"CalculiX: {info['nodes']} nodes, load and unload",
                "nfev": None, "series": series, "outputs": outputs, "files": files(), "cleanup": work}

    def tool_versions(self):
        return self._versions


class StrapPlasticStudy(Study):
    name = "strap_plastic"
    models = {"cadquery_ccx_strap_plastic": CadQueryCalculiXStrapPlastic}
    metrics = frozenset({"notch_strain_percent", "notch_stress_MPa", "residual_stress_MPa", "elastic_peak_MPa",
                         "plastic_zone_mm"})
    param_names = PARAMS
    series_file = "ligament.csv"
    compare_description = "max relative difference over the ligament profiles"

    def derive(self, params):
        mat = material(params)
        kt = sc.kt_net(_p(params, "hole_diameter_mm"), _p(params, "width_mm"))
        s_net = net_stress(params)
        s_e = kt * s_net
        sn, en = npl.neuber(mat, s_e)
        sg, eg = npl.glinka(mat, s_e)
        return {"kt_net_peterson": kt, "net_stress_MPa": s_net, "elastic_peak_peterson_MPa": s_e,
                "neuber_stress_MPa": sn, "neuber_strain": en, "glinka_stress_MPa": sg, "glinka_strain": eg,
                "residual_neuber_MPa": npl.residual_after_elastic_unloading(sn, s_e),
                "initial_yield_MPa": mat.yield_stress}

    def compute_metrics(self, series, params, case, outputs=None):
        y, pe = series["y_mm"], series["peeq_proof"]
        r = _p(params, "hole_diameter_mm") / 2
        plastic = y[pe > 1e-6]
        return {"notch_strain_percent": float(series["exx_proof"][0]) * 100,
                "notch_stress_MPa": float(series["sxx_proof_MPa"][0]),
                "residual_stress_MPa": float(series["sxx_residual_MPa"][0]),
                "elastic_peak_MPa": float(series["sxx_elastic_MPa"][0]),
                "plastic_zone_mm": float(plastic.max() - r) if len(plastic) else 0.0}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        p, d, m, out = point["parameters"], point["derived"], point["metrics"], point["solver_outputs"]
        F = _p(p, "axial_load_N")
        mat = material(p)
        eps = m["notch_strain_percent"] / 100
        kt_fe = m["elastic_peak_MPa"] / d["net_stress_MPa"]
        # bracket: below Glinka or above Neuber, as a fraction of the bound crossed
        bracket = max(0.0, (d["glinka_strain"] - eps) / d["glinka_strain"], (eps - d["neuber_strain"]) / d["neuber_strain"])
        superposed = m["notch_stress_MPa"] - m["elastic_peak_MPa"]
        flow = float(np.interp(float(series["peeq_proof"][0]), mat.ep, mat.s))   # current yield after hardening
        checks = [
            check("equilibrium_proof", "|reaction on the symmetry edge + F/2| / (F/2) at the proof load",
                  abs(out["reaction_x_proof_N"] + F / 2) / (F / 2), tol["equilibrium_rel_tol"]),
            check("equilibrium_unloaded", "|reaction on the symmetry edge| / (F/2) after unloading",
                  abs(out["reaction_x_unloaded_N"]) / (F / 2), tol["equilibrium_rel_tol"]),
            check("elastic_kt_reference", "|FE elastic peak / net stress - Peterson Kt| / Kt (handbook)",
                  abs(kt_fe - d["kt_net_peterson"]) / d["kt_net_peterson"], tol["kt_rel_tol"]),
            check("neuber_glinka_bracket", "notch-root strain outside [Glinka, Neuber], as a fraction of the "
                  "bound crossed (0 = inside)", bracket, tol["bracket_rel_tol"]),
            check("neuber_reference", "|notch-root strain FE - Neuber| / Neuber (model form; plane stress)",
                  abs(eps - d["neuber_strain"]) / d["neuber_strain"], tol["neuber_rel_tol"]),
            check("residual_superposition", "|residual stress - (proof stress - elastic peak)| / elastic peak "
                  "(exact if the unloading is elastic)", abs(m["residual_stress_MPa"] - superposed)
                  / m["elastic_peak_MPa"], tol["superposition_rel_tol"]),
            check("residual_reference", "|residual stress FE - Neuber state minus Peterson elastic peak| / elastic "
                  "peak (model form)", abs(m["residual_stress_MPa"] - d["residual_neuber_MPa"])
                  / d["elastic_peak_peterson_MPa"], tol["residual_rel_tol"]),
            check("net_section_elastic", "net-section stress / initial yield (contained yielding)",
                  d["net_stress_MPa"] / d["initial_yield_MPa"], 1.0, kind="validity"),
            check("contained_yield", "plastic zone along the ligament / ligament width",
                  m["plastic_zone_mm"] / out["ligament_width_mm"], tol["plastic_zone_fraction_max"], kind="validity"),
            check("elastic_unloading", "|residual stress| / current flow stress at the notch root (no reversed yield)",
                  abs(m["residual_stress_MPa"]) / flow, 1.0, kind="validity"),
            check("small_strain", "notch-root strain (geometrically linear analysis)", eps, tol["strain_max"],
                  kind="validity"),
        ]
        plastic_figure(pdir / "response.png", p, d, m, series, mat,
                       title=f"{point['label']}  (proof load {F / 1e3:g} kN, {out['nodes']} nodes)")
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "hole_element_ratio":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: float(pt["parameters"]["hole_element_ratio"]))
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(float(pt["parameters"]["hole_element_ratio"]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
        for metric in sorted({r["metric"] for r in case["requirements"]}):
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine), design_order=2)
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


def plastic_figure(path, p, d, m, series, mat, *, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from harness.plotting import GRID, SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.4), facecolor=SURFACE)
    s = np.linspace(0, mat.s[-1], 400)
    a1.plot(mat.strain(s) * 100, s, color=TEXT_2, lw=1.4, label="material curve")
    ee = np.linspace(1e-4, 1.6 * d["neuber_strain"], 200)
    a1.plot(ee * 100, d["elastic_peak_peterson_MPa"] ** 2 / (mat.E * ee), color=SERIES_2, lw=1, ls="--",
            label="Neuber hyperbola  s e = (Kt S)^2 / E")
    a1.plot(d["neuber_strain"] * 100, d["neuber_stress_MPa"], "D", color=SERIES_2, mfc="none", ms=8, label="Neuber")
    a1.plot(d["glinka_strain"] * 100, d["glinka_stress_MPa"], "s", color=SERIES_2, mfc="none", ms=8, label="Glinka")
    a1.plot(m["notch_strain_percent"], m["notch_stress_MPa"], "o", color=SERIES_1, ms=8, label="FE notch root")
    a1.set_xlim(0, 1.5 * d["neuber_strain"] * 100)
    a1.set_ylim(0, 1.1 * d["elastic_peak_peterson_MPa"])
    a1.set_xlabel("strain (%)")
    a1.set_ylabel("stress (MPa)")
    a1.set_title("Notch root at the proof load", color=TEXT, loc="left", fontsize=10)
    y = series["y_mm"]
    a2.plot(y, series["sxx_elastic_MPa"], color=TEXT_2, lw=1.2, ls="--", label="elastic, at the proof load")
    a2.plot(y, series["sxx_proof_MPa"], color=SERIES_1, lw=1.8, label="elastic-plastic, at the proof load")
    a2.plot(y, series["sxx_residual_MPa"], color=SERIES_2, lw=1.8, label="residual, after unloading")
    a2.axhline(0, color=GRID, lw=1)
    a2.set_xlabel("distance from the strap centre along the ligament (mm)")
    a2.set_ylabel("axial stress (MPa)")
    a2.set_title(f"Residual {m['residual_stress_MPa']:.1f} MPa at the hole edge; plastic zone "
                 f"{m['plastic_zone_mm']:.2f} mm", color=TEXT, loc="left", fontsize=10)
    for a in (a1, a2):
        a.grid(color=GRID, lw=0.6)
        a.legend(frameon=False, fontsize=8, labelcolor=TEXT_2)
        a.tick_params(colors=TEXT_2)
        for s_ in a.spines.values():
            s_.set_color(GRID)
    fig.suptitle(title, color=TEXT, fontsize=10, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=120, facecolor=SURFACE)
    plt.close(fig)


STUDY = StrapPlasticStudy()

"""Study 25 part 2: the pump cover between its bolts, against part 1's flat rigid cover.

Model:     ccx_oring_cover (models/fea/oring_cover.py): a CadQuery quarter cover, Gmsh C3D10, CalculiX static; the
           sealed pressure and the O-ring's line load from part 1 (loosest corner) push it up; the bolts hold it at the
           washer footprints on a rigid flange.
Metrics:   the largest lift of the cover's underside along the O-ring's centroid circle, and the squeeze left at the
           loosest corner with that lift: (d - h - lift) / d.
Reference: the cover simply supported along its edge under pressure over its whole underside against Mindlin's plate
           (Kirchhoff with the transverse-shear term); the reaction at the bolts against the applied load (exact).
Run-level: GCI over element_size_mm.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

from harness.backend_base import Backend, failed
from harness.calculix import read_dat_total_forces, read_frd
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study

WRITER = "models/fea/oring_cover.py"
MESHREAD = "models/fea/pressure_vessel.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_W = _load(Path(__file__).resolve().parent.parent / WRITER, "oring_cover_repo")
PARAMS = _W.PARAMS + ("loosest_cross_section_mm", "loosest_groove_depth_mm")


class CalculiXCover(Backend):
    sources = (WRITER, MESHREAD)

    def __init__(self):
        from studies.cantilever import find_freecadcmd

        bin_dir = find_freecadcmd().parent
        self.gmsh, self.ccx = bin_dir / "gmsh.exe", bin_dir / "ccx.exe"
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        import cadquery

        _load(self.source_path(MESHREAD, source_dir), "models.fea.pressure_vessel")
        self.W = _load(self.source_path(WRITER, source_dir), "oring_cover_saved")
        g = subprocess.run([str(self.gmsh), "--version"], capture_output=True, text=True, timeout=60)
        c = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"cadquery": cadquery.__version__, "gmsh": (g.stdout + g.stderr).strip().splitlines()[-1],
                          "CalculiX": (c.stdout.strip().splitlines() or ["?"])[-1]}

    def solve(self, params, numerics, tolerance_scale=1.0):
        W = self.W
        work = Path(tempfile.mkdtemp(prefix="cover_"))
        keep = ("cover.step", "mesh.geo", "job.inp", "job.dat", "job.sta", "gmsh.log", "ccx.log")

        def files():
            return {n: work / n for n in keep if (work / n).exists()}

        try:
            cad = W.build_step(params, work / "cover.step")
            W.write_geo(params, work / "mesh.geo")
            g = subprocess.run([str(self.gmsh), "mesh.geo", "-3", "-format", "inp", "-o", "mesh.inp"], cwd=work,
                               capture_output=True, text=True, timeout=1800)
            (work / "gmsh.log").write_text(g.stdout + g.stderr, encoding="utf-8")
            if g.returncode != 0 or not (work / "mesh.inp").exists():
                return failed(f"gmsh failed (exit {g.returncode})") | {"files": files(), "cleanup": work}
            info = W.write_deck(params, work / "mesh.inp", work / "job.inp")
            th = str(int(numerics.get("threads", 4)))
            env = dict(os.environ, OMP_NUM_THREADS=th, CCX_NPROC_EQUATION_SOLVER=th)
            c = subprocess.run([str(self.ccx), "-i", "job"], cwd=work, capture_output=True, text=True, env=env,
                               timeout=float(numerics.get("solver_timeout_s", 3600)))
            (work / "ccx.log").write_text(c.stdout + c.stderr, encoding="utf-8")
            if c.returncode != 0 or not (work / "job.frd").exists():
                return failed(f"CalculiX failed (exit {c.returncode})") | {"files": files(), "cleanup": work}
            fr = read_frd(work / "job.frd")
        except Exception as e:  # noqa: BLE001
            return failed(f"{type(e).__name__}: {e}") | {"files": files(), "cleanup": work}

        ids, xyz = fr["nodes"], fr["coords"]
        D = fr["DISP"]
        uz = dict(zip(D["ids"].tolist(), D["D3"].tolist()))
        outputs = {**info, **{f"cad_{k}": v for k, v in cad.items()},
                   "reaction_totals_N": read_dat_total_forces(work / "job.dat")}
        if params["support"] == "edge":
            t = float(params["cover_thickness_mm"])
            k = int(np.argmin(np.linalg.norm(xyz - np.array([0.0, 0.0, t / 2]), axis=1)))
            outputs["centre_deflection_mm"] = float(uz[int(ids[k])])
            outputs["mindlin_centre_deflection_mm"] = W.mindlin_centre_deflection(params)
            series = {"r_mm": np.array([0.0]), "uz_mm": np.array([outputs["centre_deflection_mm"]])}
        else:
            th_deg, w = W.seal_line_lift(ids, xyz, uz, params)
            outputs["seal_line_deg"], outputs["seal_line_lift_mm"] = th_deg.tolist(), w.tolist()
            series = {"angle_deg": th_deg, "lift_mm": w}
        return {"success": True, "message": f"CalculiX: {info['elements']} C3D10, {info['nodes']} nodes",
                "nfev": None, "series": series, "outputs": outputs, "files": files(), "cleanup": work}

    def tool_versions(self):
        return self._versions


class CoverStudy(Study):
    name = "oring_cover"
    models = {"ccx_oring_cover": CalculiXCover}
    metrics = frozenset({"max_seal_lift_um", "loosest_squeeze_with_lift_pct", "centre_deflection_um"})
    param_names = PARAMS
    series_file = "seal_line_lift.csv"
    compare_description = "max relative difference of the lift along the seal line"

    def derive(self, params):
        d, h = float(params["loosest_cross_section_mm"]), float(params["loosest_groove_depth_mm"])
        return {"loosest_squeeze_flat_pct": 100 * (d - h) / d,
                "allowed_lift_for_15pct_mm": d - h - 0.15 * d,
                "mindlin_centre_deflection_mm": _W.mindlin_centre_deflection(params)}

    def compute_metrics(self, series, params, case, outputs=None):
        d, h = float(params["loosest_cross_section_mm"]), float(params["loosest_groove_depth_mm"])
        if params["support"] == "edge":
            return {"centre_deflection_um": 1e3 * outputs["centre_deflection_mm"]}
        w = float(np.max(series["lift_mm"]))
        return {"max_seal_lift_um": 1e3 * w, "loosest_squeeze_with_lift_pct": 100 * (d - h - w) / d}

    def verify_point(self, case, point, pdir, series, backend):
        tol = case["verification"]
        p, out, m = point["parameters"], point["solver_outputs"], point["metrics"]
        checks = [check("cad_valid", "CadQuery B-rep valid, one solid (0 = yes)",
                        0.0 if out["cad_valid"] and out["cad_solids"] == 1 else 1.0, 0.0)]
        if p["support"] == "edge":
            checks.append(check("plate_theory", "|centre deflection (mid-plane) - Mindlin plate| / Mindlin",
                                abs(out["centre_deflection_mm"] / out["mindlin_centre_deflection_mm"] - 1),
                                tol["plate_rel_tol"]))
        else:
            rz = out["reaction_totals_N"]["SUPPORT"][2]
            checks.append(check("equilibrium", "|reaction at the washer footprints + applied load| / applied load "
                                "(the footprints carry no load, so RF is the reaction)",
                                abs(rz + out["applied_quarter_load_N"]) / out["applied_quarter_load_N"],
                                tol["equilibrium_rel_tol"]))
            lift = np.asarray(out["seal_line_lift_mm"])
            checks.append(check("lifts_everywhere", "the cover lifts (does not press down) all along the seal line "
                                "(min lift / max lift >= 0; 0 = yes)", 0.0 if lift.min() >= 0 else 1.0, 0.0,
                                kind="validity"))
        cover_figure(pdir / "response.png", series, p, m)
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "element_size_mm":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: float(pt["parameters"]["element_size_mm"]))
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(float(pt["parameters"]["element_size_mm"]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
        for metric in sorted({r["metric"] for r in case["requirements"]} | {"max_seal_lift_um"}):
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine), design_order=2,
                                           noise_floor=tol["mesh_noise_rel"])
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


def cover_figure(path, series, p, m):
    from harness.plotting import SERIES_1, SURFACE, TEXT, _style, plt

    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    if "angle_deg" in series:
        ax.plot(series["angle_deg"], 1e3 * np.asarray(series["lift_mm"]), "o-", color=SERIES_1, ms=2.5, lw=1.4)
        ax.set_xlabel("angle around the seal (deg); bolts at " + ", ".join(
            f"{a:.0f}" for a in _W.bolt_angles(int(p["bolt_count"]))))
        ax.set_ylabel("lift of the cover at the seal (um)")
        title = f"t = {float(p['cover_thickness_mm']):g} mm: max lift {m['max_seal_lift_um']:.1f} um"
    else:
        ax.text(0.5, 0.5, f"centre deflection {m['centre_deflection_um']:.2f} um", ha="center", transform=ax.transAxes)
        title = "edge-supported plate (reference)"
    fig.suptitle(title, fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = CoverStudy()

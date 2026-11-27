"""Study 2 part 2: the strap's cable hole in 3D, through the 4 mm thickness, against study 2's plane-stress answer.

Model:     cadquery_ccx_strap_3d (models/fea/strap_3d.py): study 2's CadQuery quarter face, extruded in Gmsh through the
           half thickness (20-node bricks, layers graded to the free face), CalculiX static.
Metrics:   the hole-edge stress at mid-thickness (the peak, REQ-H1's metric), at the face, its mean through the
           thickness, and the 3D factors mid / plane stress and mid / mean.
Reference: the thin-plate limit (a case at t / d = 0.0025) against study 2's plane-stress value; equilibrium (reaction
           and ligament force F / 4); loaded area exact; Peterson's Kt for the mean (model form, as study 2).
Run-level: GCI on the requirement metric when the sweep is hole_element_size_mm (layers refine with it).
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
from validation import stress_concentration as sc

WRITER = "models/fea/strap_3d.py"
FACE = "models/fea/strap_hole.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_W = _load(Path(__file__).resolve().parent.parent / WRITER, "strap_3d_repo")
PARAMS = _W.PARAMS


class CadQueryCalculiXStrap3D(Backend):
    sources = (WRITER, FACE)

    def __init__(self):
        from studies.cantilever import find_freecadcmd

        bin_dir = find_freecadcmd().parent
        self.gmsh, self.ccx = bin_dir / "gmsh.exe", bin_dir / "ccx.exe"
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        import cadquery

        self.face = _load(self.source_path(FACE, source_dir), "strap_hole_saved")
        self.W = _load(self.source_path(WRITER, source_dir), "strap_3d_saved")
        g = subprocess.run([str(self.gmsh), "--version"], capture_output=True, text=True, timeout=60)
        c = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"cadquery": cadquery.__version__, "gmsh": (g.stdout + g.stderr).strip().splitlines()[-1],
                          "CalculiX": (c.stdout.strip().splitlines() or ["?"])[-1]}

    def solve(self, params, numerics, tolerance_scale=1.0):
        W = self.W
        work = Path(tempfile.mkdtemp(prefix="strap3d_"))
        keep = ("quarter.step", "mesh.geo", "job.inp", "job.dat", "job.sta", "gmsh.log", "ccx.log")

        def files():
            return {n: work / n for n in keep if (work / n).exists()}

        try:
            area = self.face.build_step(params, work / "quarter.step")
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
                               timeout=float(numerics.get("solver_timeout_s", 7200)))
            (work / "ccx.log").write_text(c.stdout + c.stderr, encoding="utf-8")
            if c.returncode != 0 or not (work / "job.frd").exists():
                return failed(f"CalculiX failed (exit {c.returncode})") | {"files": files(), "cleanup": work}
            fr = read_frd(work / "job.frd")
        except Exception as e:  # noqa: BLE001
            return failed(f"{type(e).__name__}: {e}") | {"files": files(), "cleanup": work}

        ids, xyz = fr["nodes"], fr["coords"]
        S = fr["STRESS"]
        sxx = dict(zip(S["ids"].tolist(), S["SXX"].tolist()))
        r, t2 = float(params["hole_diameter_mm"]) / 2, float(params["thickness_mm"]) / 2
        z, s = W.hole_edge_profile(ids, xyz, sxx, r)
        mean = W.through_mean(z, s, t2)
        lig = W.ligament_force(ids, xyz, sxx, r, float(params["width_mm"]) / 2, t2, W.n_layers(params))
        far = np.abs(xyz[:, 0] - float(params["length_mm"]) / 2) < 1e-6
        far_s = np.array([sxx[int(n)] for n in ids[far]])
        outputs = {**info, "face_area_mm2": area, "layers": W.n_layers(params),
                   "profile_z_mm": z.tolist(), "profile_sxx_MPa": s.tolist(), "mean_through_MPa": mean,
                   "ligament_force_N": lig, "far_sxx_MPa": [float(far_s.min()), float(far_s.max())],
                   "reaction_totals_N": read_dat_total_forces(work / "job.dat")}
        series = {"z_mm": z, "sxx_MPa": s}
        return {"success": True, "message": f"CalculiX: {info['elements']} C3D20, {info['nodes']} nodes, "
                f"{W.n_layers(params)} layers", "nfev": None, "series": series, "outputs": outputs,
                "files": files(), "cleanup": work}

    def tool_versions(self):
        return self._versions


def plane_stress_peak(params) -> float:
    """Study 2's plane-stress peak for this hole: a number, or a table keyed by the hole diameter ("16" = 116.988)."""
    v = params["plane_stress_peak_MPa"]
    if isinstance(v, dict):
        return float(v[f"{float(params['hole_diameter_mm']):g}"])
    return float(v)


class Strap3DStudy(Study):
    name = "strap_3d"
    models = {"cadquery_ccx_strap_3d": CadQueryCalculiXStrap3D}
    metrics = frozenset({"peak_hole_stress_MPa", "surface_hole_stress_MPa", "mean_hole_stress_MPa",
                         "mid_over_plane_stress", "mid_over_mean", "kt_net_mid"})
    param_names = PARAMS + ("plane_stress_peak_MPa",)
    series_file = "hole_edge_profile.csv"
    compare_description = "max relative difference of sigma_xx along the hole edge through the thickness"

    def derive(self, params):
        F, W, d, t = (float(params[k]) for k in ("axial_load_N", "width_mm", "hole_diameter_mm", "thickness_mm"))
        return {"t_over_d": t / d, "t_over_r": 2 * t / d, "net_stress_MPa": sc.net_stress(F, W, d, t),
                "kt_net_peterson": sc.kt_net(d, W), "peak_stress_peterson_MPa": sc.peak_stress(F, W, d, t),
                "face_area_closed_form_mm2": float(params["length_mm"]) / 2 * W / 2 - np.pi * d ** 2 / 16}

    def compute_metrics(self, series, params, case, outputs=None):
        s = np.asarray(series["sxx_MPa"], float)
        F, W, d, t = (float(params[k]) for k in ("axial_load_N", "width_mm", "hole_diameter_mm", "thickness_mm"))
        ps = plane_stress_peak(params)
        return {"peak_hole_stress_MPa": float(s.max()), "surface_hole_stress_MPa": float(s[-1]),
                "mean_hole_stress_MPa": outputs["mean_through_MPa"], "mid_over_plane_stress": float(s[0]) / ps,
                "mid_over_mean": float(s[0]) / outputs["mean_through_MPa"],
                "kt_net_mid": float(s.max()) / sc.net_stress(F, W, d, t)}

    def verify_point(self, case, point, pdir, series, backend):
        tol = case["verification"]
        p, d, m, out = point["parameters"], point["derived"], point["metrics"], point["solver_outputs"]
        F, t = float(p["axial_load_N"]), float(p["thickness_mm"])
        q = F / 4
        rf = out["reaction_totals_N"].get("XSYM")
        s = np.asarray(out["profile_sxx_MPa"])
        checks = [
            check("cad_area", "|face area from CadQuery - closed form| / closed form",
                  abs(out["face_area_mm2"] - d["face_area_closed_form_mm2"]) / d["face_area_closed_form_mm2"], 1e-9),
            check("loaded_area", "|area of the loaded element faces - W t / 4| / (W t / 4)",
                  abs(out["loaded_area_mm2"] / out["end_area_exact_mm2"] - 1), 1e-9),
            check("equilibrium", "|reaction on x = 0 + F / 4| / (F / 4)",
                  abs(rf[0] + q) / q if rf else float("inf"), tol["equilibrium_rel_tol"]),
            check("ligament_force", "|integral of sigma_xx over the ligament face - F / 4| / (F / 4)",
                  abs(out["ligament_force_N"] / q - 1), tol["ligament_force_rel_tol"]),
            check("far_field_uniform", "max |sigma_xx on the loaded end - F / (W t)| / (F / (W t))",
                  max(abs(v / out["traction_MPa"] - 1) for v in out["far_sxx_MPa"]), tol["far_field_rel_tol"]),
            check("kt_mean_reference", "|Kt_net of the through-thickness mean - Peterson (plane stress)| / Peterson "
                  "(model form: the mean differs from plane stress by order (t / r)^2)",
                  abs(m["mean_hole_stress_MPa"] / d["net_stress_MPa"] / d["kt_net_peterson"] - 1), tol["kt_rel_tol"]),
            check("mid_is_peak", "the hole-edge peak is at mid-thickness (0 = yes)",
                  0.0 if int(np.argmax(s)) == 0 or s.max() - s[0] < 1e-6 * s.max() else 1.0, 0.0, kind="validity"),
            check("linear_material", "peak hole-edge stress / yield strength",
                  m["peak_hole_stress_MPa"] / float(p["yield_strength_MPa"]), 1.0, kind="validity"),
        ]
        if "thin_plate_rel_tol" in tol:
            checks += [
                check("thin_plate_limit", "|mid-thickness hole stress - study 2's plane-stress value| / plane stress "
                      "(thin plate: the 3D solution tends to plane stress)", abs(m["mid_over_plane_stress"] - 1),
                      tol["thin_plate_rel_tol"]),
                check("thin_plate_uniform", "|face / mid-thickness hole stress - 1| (thin plate: uniform through t)",
                      abs(m["surface_hole_stress_MPa"] / s[0] - 1), tol["thin_plate_rel_tol"]),
            ]
        profile_figure(pdir / "response.png", out, p, m)
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "hole_element_size_mm":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: float(pt["parameters"]["hole_element_size_mm"]))
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(float(pt["parameters"]["hole_element_size_mm"]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
        for metric in sorted({r["metric"] for r in case["requirements"]} | {"mean_hole_stress_MPa"}):
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine), design_order=2,
                                           noise_floor=tol["mesh_noise_rel"])
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


def profile_figure(path, out, p, m):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2, _style, plt

    z, s = np.asarray(out["profile_z_mm"]), np.asarray(out["profile_sxx_MPa"])
    fig, ax = plt.subplots(figsize=(6.5, 4))
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    ax.plot(s, z, "o-", color=SERIES_1, ms=3, lw=1.5, label="3D: hole edge through the thickness")
    ax.axvline(plane_stress_peak(p), color=SERIES_2, lw=1.2, ls="--", label="plane stress (study 2)")
    ax.axvline(m["mean_hole_stress_MPa"], color=TEXT_2, lw=0.9, ls=":", label="3D mean through the thickness")
    ax.set_xlabel("sigma_xx at the hole edge (MPa)")
    ax.set_ylabel("z from mid-thickness (mm)")
    ax.legend(frameon=False, fontsize=8)
    fig.suptitle(f"d = {float(p['hole_diameter_mm']):g} mm, t = {float(p['thickness_mm']):g} mm: mid "
                 f"{m['peak_hole_stress_MPa']:.2f}, face {m['surface_hole_stress_MPa']:.2f} MPa", fontsize=10,
                 color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = Strap3DStudy()

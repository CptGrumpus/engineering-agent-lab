"""Study 18, the head-to-shell junction: a cylindrical shell closed by a hemispherical head under internal pressure,
elastic stress analysis by linearisation at the junction (as studies/pressure_vessel.py at the nozzle).

Model:     ccx_vessel_head_axi (models/fea/vessel_head_axi.py): structured CAX8 mesh generated in Python ->
           CalculiX static; stresses linearised along lines through the wall (harness/linearize.py) on element
           boundaries, in the shell (distance x from the junction) and the head (arc distance s).
Reference: the far shell against the Lame closed-end cylinder and the far head against the Lame thick sphere (exact);
           the axial reaction on the mid-length plane against p pi Ri^2 (exact); with equal thicknesses, the
           junction against thin-shell discontinuity theory (models/fea/vessel_head_axi.py discontinuity_theory:
           the largest axial bending in the shell, where it occurs, and the hoop membrane at the junction; model form,
           the shell theory's own error is of order t / R, about 3 %).
Run-level: GCI on the requirement metrics when the sweep is element_size_mm.

Classification (as study 18's nozzle): far from the junction the membrane is general primary (Pm <= S); within the
junction region (the lines within junction_region_mm of it) the membrane is local primary (PL <= 1.5 S) and membrane
plus bending primary plus secondary (P + Q <= 3 S).
"""

from __future__ import annotations

import importlib.util
import math
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness.backend_base import Backend, failed
from harness.calculix import read_frd
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.linearize import linearize
from harness.study import Study
from studies.strut_buckling import read_dat_blocks

WRITER = "models/fea/vessel_head_axi.py"
#: CalculiX expands CAX elements into a 2-degree wedge; reactions are printed for that segment (checked in the smoke
#: test against p pi Ri^2)
SEGMENT = 2.0 / 360.0


def _load(path: Path):
    spec = importlib.util.spec_from_file_location("vessel_head_axi_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_W = _load(Path(__file__).resolve().parent.parent / WRITER)
PARAMS = _W.PARAMS + ("allowable_stress_MPa",)
AXES_SHELL = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], float)  # n radial, m axial, h hoop (global r, z, theta)


def _axes_head(phi):
    c, s = math.cos(phi), math.sin(phi)
    return np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]], float)  # n along the radius, m meridional, h hoop


class CalculiXVesselHead(Backend):
    sources = (WRITER,)

    def __init__(self):
        from studies.cantilever import find_freecadcmd

        self.ccx = find_freecadcmd().parent / "ccx.exe"
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        self.writer = _load(self.source_path(WRITER, source_dir))
        c = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"CalculiX": (c.stdout.strip().splitlines() or ["?"])[-1]}

    def solve(self, params, numerics, tolerance_scale=1.0):
        W = self.writer
        work = Path(tempfile.mkdtemp(prefix="vhead_"))
        keep = ("job.inp", "job.dat", "job.sta", "ccx.log")

        def files():
            return {n: work / n for n in keep if (work / n).exists()}

        try:
            info = W.write_deck(params, work / "job.inp")
            c = subprocess.run([str(self.ccx), "-i", "job"], cwd=work, capture_output=True, text=True,
                               timeout=float(numerics.get("solver_timeout_s", 3600)))
            (work / "ccx.log").write_text(c.stdout + c.stderr, encoding="utf-8")
            if c.returncode != 0 or not (work / "job.frd").exists():
                return failed(f"CalculiX failed (exit {c.returncode})") | {"files": files(), "cleanup": work}
            frd = read_frd(work / "job.frd")
            nodes, elems, cyl, head = W.build_mesh(params)
        except Exception as e:  # noqa: BLE001
            return failed(f"{type(e).__name__}: {e}") | {"files": files(), "cleanup": work}

        S = frd["STRESS"]
        smap = {k: dict(zip(S["ids"].tolist(), S[k].tolist())) for k in ("SXX", "SYY", "SZZ", "SXY", "SYZ", "SZX")}
        missing = [n for n in nodes if n not in smap["SXX"]]
        if missing:
            return failed(f"{len(missing)} mesh nodes without stress in the .frd (first {missing[:3]})") | {
                "files": files(), "cleanup": work}

        def stress(ids):
            return np.array([[smap[k][n] for k in smap] for n in ids])

        def line(ids, axes):
            xyz = np.array([[nodes[n][0], nodes[n][1], 0.0] for n in ids])
            s = np.linalg.norm(xyz - xyz[0], axis=1)
            res = linearize(s, stress(ids), axes)
            return {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in res.items()}

        d = W.dims(params)
        region = float(numerics.get("junction_region_mm", 3 * math.sqrt(d["Rm"] * d["t"])))
        shell = [{"x_mm": x} | line(ids, AXES_SHELL) for x, ids in W.scl_shell(params, cyl, region)]
        hd = [{"s_mm": s, "phi_rad": ph} | line(ids, _axes_head(ph)) for s, ph, ids in W.scl_head(params, head, region)]
        far_shell = W.scl_shell(params, cyl, d["L"] / 2)[-1]
        phi_far, far_head_ids = W.head_line_at(params, head, math.radians(float(numerics.get("far_head_deg", 60.0))))
        D = frd["DISP"]
        umax = float(np.max(np.hypot(D["D1"], D["D2"])))
        blocks = read_dat_blocks(work / "job.dat")
        rz = next(b["rows"][0] for b in blocks if b["kind"] == "total" and b["set"] == "NBOTTOM")
        outputs = {**info, "shell_lines": shell, "head_lines": hd, "junction_region_mm": region,
                   "far_shell": {"x_mm": far_shell[0]} | line(far_shell[1], AXES_SHELL),
                   "far_head": {"phi_rad": phi_far} | line(far_head_ids, _axes_head(phi_far)),
                   "reaction_z_N_segment": float(rz[1]), "max_displacement_mm": umax,
                   "theory": W.discontinuity_theory(params)}
        series = {"x_mm": np.array([ln["x_mm"] for ln in shell]),
                  "bending_axial_MPa": np.array([ln["bending"][1] for ln in shell])}
        return {"success": True, "message": f"CalculiX: {info['elements']} CAX8, {info['nodes']} nodes",
                "nfev": None, "series": series, "outputs": outputs, "files": files(), "cleanup": work}

    def tool_versions(self):
        return self._versions


def _lame_cyl_pm(p):
    d = _W.dims(p)
    r = np.linspace(d["Ri"], d["Ri"] + d["t"], 41)
    sr, sh, sa, _ = _W.lame_cylinder(p, r)
    st = np.zeros((41, 6))
    st[:, 0], st[:, 1], st[:, 2] = sr, sa, sh
    return linearize(r - d["Ri"], st, np.eye(3))["membrane_vm"]


def _lame_sph_pm(p):
    d = _W.dims(p)
    r = np.linspace(d["Ri"], d["Ri"] + d["th"], 41)
    sr, st_, _ = _W.lame_sphere(p, r)
    st = np.zeros((41, 6))
    st[:, 0], st[:, 1], st[:, 2] = sr, st_, st_
    return linearize(r - d["Ri"], st, np.eye(3))["membrane_vm"]


class VesselHeadStudy(Study):
    name = "vessel_head"
    models = {"ccx_vessel_head_axi": CalculiXVesselHead}
    metrics = frozenset({"pm_shell_MPa", "pm_head_MPa", "pl_junction_MPa", "pq_junction_MPa", "pl_shell_junction_MPa",
                         "pl_head_junction_MPa", "pq_shell_junction_MPa", "pq_head_junction_MPa",
                         "bending_shell_max_MPa", "x_bending_shell_max_mm", "hoop_membrane_junction_MPa"})
    param_names = PARAMS
    series_file = "shell_bending.csv"
    compare_description = "max relative difference of the axial bending stress along the shell"

    def derive(self, params):
        d = _W.dims(params)
        p, S = float(params["pressure_MPa"]), float(params["allowable_stress_MPa"])
        th = _W.discontinuity_theory(params)
        return {"hoop_membrane_p_Ri_over_t_MPa": p * d["Ri"] / d["t"], "allowable_PL_MPa": 1.5 * S,
                "allowable_PS_MPa": 3.0 * S, "sqrt_Rt_mm": math.sqrt(d["Rm"] * d["t"]),
                "head_rule_thickness_mm": p * d["Ri"] / (2 * S), "lame_pm_shell_MPa": _lame_cyl_pm(params),
                "lame_pm_head_MPa": _lame_sph_pm(params)} | {f"theory_{k}": v for k, v in th.items()}

    def compute_metrics(self, series, params, case, outputs=None):
        sh, hd = outputs["shell_lines"], outputs["head_lines"]
        xs, ss = [ln["x_mm"] for ln in sh], [ln["s_mm"] for ln in hd]
        b_max, x_b = peak(xs, [abs(ln["bending"][1]) for ln in sh])
        out = {"pm_shell_MPa": outputs["far_shell"]["membrane_vm"], "pm_head_MPa": outputs["far_head"]["membrane_vm"],
               "pl_shell_junction_MPa": peak(xs, [ln["membrane_vm"] for ln in sh])[0],
               "pl_head_junction_MPa": peak(ss, [ln["membrane_vm"] for ln in hd])[0],
               "pq_shell_junction_MPa": peak(xs, [ln["membrane_plus_bending_vm"] for ln in sh])[0],
               "pq_head_junction_MPa": peak(ss, [ln["membrane_plus_bending_vm"] for ln in hd])[0],
               "bending_shell_max_MPa": b_max, "x_bending_shell_max_mm": x_b,
               "hoop_membrane_junction_MPa": sh[0]["membrane"][2]}
        out["pl_junction_MPa"] = max(out["pl_shell_junction_MPa"], out["pl_head_junction_MPa"])
        out["pq_junction_MPa"] = max(out["pq_shell_junction_MPa"], out["pq_head_junction_MPa"])
        return out

    def verify_point(self, case, point, pdir, series, backend):
        tol = case["verification"]
        p, out, m = point["parameters"], point["solver_outputs"], point["metrics"]
        d = _W.dims(p)
        pr = float(p["pressure_MPa"])
        exact_rz = pr * math.pi * d["Ri"] ** 2
        r = np.linspace(d["Ri"], d["Ri"] + d["t"], 2 * d["nc"] + 1)
        hoop_bore = float(_W.lame_cylinder(p, d["Ri"])[1])
        fs = out["far_shell"]
        checks = [
            check("equilibrium_z", "|axial reaction on the mid-length plane / 2-degree segment - p pi Ri^2| / p pi Ri^2 "
                  "(exact: the pressure on the head's projected area)",
                  abs(out["reaction_z_N_segment"] / SEGMENT + exact_rz) / exact_rz, tol["equilibrium_rel_tol"]),
            check("lame_shell_membrane", "|far-shell linearised membrane (von Mises) - the same linearisation of Lame| "
                  "/ Lame (exact)", abs(m["pm_shell_MPa"] - _lame_cyl_pm(p)) / _lame_cyl_pm(p), tol["lame_rel_tol"]),
            check("lame_head_membrane", "|far-head linearised membrane (von Mises) - the thick sphere's| / exact",
                  abs(m["pm_head_MPa"] - _lame_sph_pm(p)) / _lame_sph_pm(p), tol["lame_rel_tol"]),
            check("lame_shell_hoop_range", "|far-shell hoop stress, bore minus outside, FE - Lame| / Lame (the through-"
                  "wall gradient, not only the mean)", abs((fs["at_start"][2] - fs["at_end"][2])
                                                           - (hoop_bore - float(_W.lame_cylinder(p, r[-1])[1])))
                  / hoop_bore, tol["lame_rel_tol"]),
            check("small_displacement", "max displacement / shell thickness (linear geometry)",
                  out["max_displacement_mm"] / d["t"], 0.1, kind="validity"),
            check("far_lines_far", "junction region / distance of the far lines (the far shell line at L / 2; the head "
                  "line at the stated angle): far lines outside the bending zone", out["junction_region_mm"]
                  / min(fs["x_mm"], d["Rmh"] * out["far_head"]["phi_rad"]), 1.0, kind="validity"),
        ]
        th = out["theory"]
        if th:  # equal thicknesses: thin-shell discontinuity theory applies
            checks += [
                check("theory_bending_max", "|largest axial bending in the shell - thin-shell theory 6 M_max / t^2| / "
                      "theory (model form: shell theory error of order t / R)",
                      abs(m["bending_shell_max_MPa"] - th["bending_max_MPa"]) / th["bending_max_MPa"],
                      tol["theory_rel_tol"]),
                check("theory_bending_location", "|x of the largest bending - pi / (4 beta)| / (pi / (4 beta)) (the "
                      "lines are one element length apart)",
                      abs(m["x_bending_shell_max_mm"] - th["x_bending_max_mm"]) / th["x_bending_max_mm"],
                      tol["theory_location_rel_tol"]),
                check("theory_hoop_junction", "|hoop membrane at the junction - (p Ri / t - E delta / (2 Rm))| / theory",
                      abs(m["hoop_membrane_junction_MPa"] - th["hoop_membrane_junction_MPa"])
                      / th["hoop_membrane_junction_MPa"], tol["theory_rel_tol"]),
            ]
        head_figure(pdir / "response.png", out, point)
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
        for metric in sorted({r["metric"] for r in case["requirements"]}):
            vals = tuple(pt["metrics"][metric] for pt in fine)
            u = discretization_uncertainty(hs, vals, design_order=2, noise_floor=tol.get("mesh_noise_rel", 1e-5))
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


def peak(s, v):
    """Largest value of v over the lines at positions s, located between lines by a parabola through the largest
    sample and its two neighbours (a sampled maximum is not smooth in the mesh size: the line spacing halves with
    each refinement, so each mesh samples the peak at different points). At either end, the end sample itself.
    Returns (value, position)."""
    s, v = np.asarray(s, float), np.asarray(v, float)
    k = int(np.argmax(v))
    if k == 0 or k == len(v) - 1:
        return float(v[k]), float(s[k])
    a, b, c = np.polyfit(s[k - 1:k + 2], v[k - 1:k + 2], 2)
    if a >= 0:
        return float(v[k]), float(s[k])
    x = -b / (2 * a)
    return float(np.polyval([a, b, c], x)), float(x)


def head_figure(path, out, point):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, _style, plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    fig.patch.set_facecolor(SURFACE)
    sh, hd = out["shell_lines"], out["head_lines"]
    x = [ln["x_mm"] for ln in sh]
    s = [ln["s_mm"] for ln in hd]
    ax = axes[0]
    ax.plot(x, [ln["bending"][1] for ln in sh], "-", color=SERIES_1, lw=1.5, label="shell: axial bending (FE)")
    ax.plot(s, [ln["bending"][1] for ln in hd], "-", color=SERIES_2, lw=1.5, label="head: meridional bending (FE)")
    th = out["theory"]
    if th:
        xx = np.linspace(0, max(x), 200)
        m = th["Q0_N_per_mm"] / th["beta_per_mm"] * np.exp(-th["beta_per_mm"] * xx) * np.sin(th["beta_per_mm"] * xx)
        sgn = np.sign(sh[int(np.argmax([abs(ln["bending"][1]) for ln in sh]))]["bending"][1])
        ax.plot(xx, sgn * 6 * m / (point["parameters"]["shell_thickness_mm"]) ** 2, "--", color=TEXT, lw=0.8,
                label="thin-shell theory (equal thickness)")
    ax.set_xlabel("distance from the junction along the wall (mm)")
    ax.set_ylabel("linearised bending stress (MPa)")
    ax.legend(frameon=False, fontsize=8)
    _style(ax)
    ax = axes[1]
    ax.plot(x, [ln["membrane_vm"] for ln in sh], "-", color=SERIES_1, lw=1.5, label="shell: membrane (PL)")
    ax.plot(x, [ln["membrane_plus_bending_vm"] for ln in sh], ":", color=SERIES_1, lw=1.5, label="shell: P + Q")
    ax.plot(s, [ln["membrane_vm"] for ln in hd], "-", color=SERIES_2, lw=1.5, label="head: membrane (PL)")
    ax.plot(s, [ln["membrane_plus_bending_vm"] for ln in hd], ":", color=SERIES_2, lw=1.5, label="head: P + Q")
    ax.set_xlabel("distance from the junction along the wall (mm)")
    ax.set_ylabel("von Mises of the linearised stress (MPa)")
    ax.legend(frameon=False, fontsize=8)
    _style(ax)
    fig.suptitle(f"{point['label']}: head-to-shell junction", fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = VesselHeadStudy()

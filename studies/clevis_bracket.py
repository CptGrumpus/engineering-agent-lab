"""Study: machined clevis bracket (base, lug, two gussets, fillets), CAD-to-FEA static pipeline;
the model inside the bracket optimisation loop.

Model:     cadquery_ccx_clevis (models/fea/clevis_bracket.py): CadQuery solid -> STEP -> Gmsh
           10-node tetrahedra (curvature-refined at the fillets and hole) -> CalculiX static, pin load
           through a rigid pin, base fixed
Checks:    no closed form covers this shape, so each candidate is checked by what must hold exactly
           (valid B-rep, meshed volume = CAD volume, force and moment equilibrium of the base reactions
           with the pin load about the origin) and, where the lug has a clear section between the
           gussets and the hole, beam theory on that section (model form); validity: below yield,
           small deflection. Mesh convergence of the peak stress at the optimum is a separate
           confirmation case (the peak sits in a fillet, so it converges; at a sharp corner it would not).
Run-level: optimisation runs: optimum found, optimiser converged; element-size or fillet-element-size
           sweeps: GCI on the requirement metrics, with the requirement checked including the uncertainty

Stress metric: the peak von Mises stress over the part, excluding the bottom half of the base plate
(fixed to the structure: the edge of a fixed face is singular, and the real joint is not modelled)
and a ring of one pin diameter around the hole (the rigid pin idealises the bearing contact; pin
bearing and lug net section are sized separately by the standard lug method).
"""

from __future__ import annotations

import importlib.util
import re
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

WRITER = "models/fea/clevis_bracket.py"
# mesh studies: the global element size, or the fillet element size (local refinement where the peak sits)
MESH_SIZE_PARAMETERS = ("element_size_mm", "fillet_element_size_mm")
INVERTED = re.compile(r"[1-9]\d* elements with jac\. < 0")


def _load_writer(path: Path):
    spec = importlib.util.spec_from_file_location("clevis_bracket_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_W = _load_writer(Path(__file__).resolve().parent.parent / WRITER)
PARAMS = _W.PARAMS + ("yield_strength_MPa",)


def _p(params, k):
    return float(params[k])


def load_vector(p):
    return np.array([_p(p, "load_x_N"), _p(p, "load_y_N"), _p(p, "load_z_N")])


class CadQueryCalculiXClevis(Backend):
    sources = (WRITER,)

    def __init__(self):
        from studies.cantilever import find_freecadcmd

        bin_dir = find_freecadcmd().parent
        self.gmsh, self.ccx = bin_dir / "gmsh.exe", bin_dir / "ccx.exe"
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        import cadquery

        self.writer = _load_writer(self.source_path(WRITER, source_dir))
        g = subprocess.run([str(self.gmsh), "--version"], capture_output=True, text=True, timeout=60)
        c = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"cadquery": cadquery.__version__, "gmsh": (g.stdout + g.stderr).strip().splitlines()[-1],
                          "CalculiX": (c.stdout.strip().splitlines() or ["?"])[-1]}

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="clevis_"))
        keep = ("bracket.step", "mesh.geo", "job.inp", "job.dat", "job.sta", "gmsh.log", "gmsh_first.log",
                "ccx.log")

        def files():
            return {n: work / n for n in keep if (work / n).exists()}

        try:
            cad = self.writer.build_step(params, work / "bracket.step")
            retried = False
            for high_order in (False, True):
                self.writer.write_geo(params, work / "mesh.geo", high_order_optimize=high_order)
                g = subprocess.run([str(self.gmsh), "mesh.geo", "-3", "-format", "inp", "-o", "mesh.inp"], cwd=work,
                                   capture_output=True, text=True, timeout=1800)
                (work / "gmsh.log").write_text(g.stdout + g.stderr, encoding="utf-8")
                if g.returncode != 0 or not (work / "mesh.inp").exists():
                    return failed(f"gmsh failed (exit {g.returncode})") | {"files": files(), "cleanup": work}
                # curving the quadratic tets can invert one; then remesh once with the high-order optimiser
                if high_order or not INVERTED.search(g.stdout + g.stderr):
                    break
                (work / "gmsh.log").replace(work / "gmsh_first.log")
                retried = True
            info = self.writer.write_deck(params, work / "mesh.inp", work / "job.inp")
            info["mesh_high_order_optimized"] = retried
            c = subprocess.run([str(self.ccx), "-i", "job"], cwd=work, capture_output=True, text=True, timeout=7200)
            (work / "ccx.log").write_text(c.stdout + c.stderr, encoding="utf-8")
            if c.returncode != 0 or not (work / "job.frd").exists():
                return failed(f"CalculiX failed (exit {c.returncode})") | {"files": files(), "cleanup": work}
        except Exception as e:
            return failed(f"{type(e).__name__}: {e}") | {"files": files(), "cleanup": work}

        frd = read_frd(work / "job.frd")
        ids = frd["nodes"]
        o = np.argsort(ids)
        series = {"node_id": ids[o].astype(float), "x_mm": frd["coords"][o, 0], "y_mm": frd["coords"][o, 1],
                  "z_mm": frd["coords"][o, 2]}
        d, s = frd["DISP"], frd["STRESS"]
        dmap = {c_: dict(zip(d["ids"].tolist(), d[c_].tolist())) for c_ in ("D1", "D2", "D3")}
        smap = {c_: dict(zip(s["ids"].tolist(), s[c_].tolist())) for c_ in ("SXX", "SYY", "SZZ", "SXY", "SYZ", "SZX")}
        for c_, n_ in (("D1", "ux_mm"), ("D2", "uy_mm"), ("D3", "uz_mm")):
            series[n_] = np.array([dmap[c_].get(int(i), np.nan) for i in ids[o]])
        for c_ in smap:
            series[f"{c_.lower()}_MPa"] = np.array([smap[c_].get(int(i), np.nan) for i in ids[o]])
        blocks = read_dat_blocks(work / "job.dat")
        rf = next(b["rows"] for b in blocks if b["kind"] == "forces" and b["set"] == "NBASE")
        ref = next(b["rows"] for b in blocks if b["kind"] == "displacements" and b["set"] == "NREF")[0]
        xyz = dict(zip(ids.tolist(), frd["coords"].tolist()))
        r_base = np.array([xyz[int(n)] for n in rf[:, 0]])
        outputs = {**info, **{f"cad_{k}": v for k, v in cad.items()},
                   "reaction_force_N": rf[:, 1:4].sum(axis=0).tolist(),
                   "reaction_moment_Nmm": np.cross(r_base, rf[:, 1:4]).sum(axis=0).tolist(),
                   "pin_displacement_mm": ref[1:4].tolist()}
        return {"success": True, "message": f"CalculiX: {info['elements']} C3D10, {info['nodes']} nodes",
                "nfev": None, "series": series, "outputs": outputs, "files": files(), "cleanup": work}

    def tool_versions(self):
        return self._versions


def von_mises(s):
    return np.sqrt(0.5 * ((s["sxx_MPa"] - s["syy_MPa"]) ** 2 + (s["syy_MPa"] - s["szz_MPa"]) ** 2
                          + (s["szz_MPa"] - s["sxx_MPa"]) ** 2)
                   + 3 * (s["sxy_MPa"] ** 2 + s["syz_MPa"] ** 2 + s["szx_MPa"] ** 2))


def assessed(series, p):
    """Nodes in the assessed region (see the module docstring)."""
    z, x = series["z_mm"], series["x_mm"]
    r_pin = np.hypot(x, z - _p(p, "pin_height_mm"))
    return (z > 0.5 * _p(p, "base_thickness_mm")) & (r_pin > _p(p, "pin_diameter_mm"))


def section_check(series, p):
    """Lug section between the gussets and the hole: FE sigma_zz at the section's corner region against
    beam theory, or None when the clear length is under 20 mm."""
    tb, hg, H = _p(p, "base_thickness_mm"), _p(p, "gusset_height_mm"), _p(p, "pin_height_mm")
    dp, R, tl = _p(p, "pin_diameter_mm"), _p(p, "lug_radius_mm"), _p(p, "lug_thickness_mm")
    lo, hi = tb + hg + _p(p, "fillet_radius_mm"), H - dp / 2
    if hi - lo < 20.0:
        return None
    z0 = 0.5 * (lo + hi)
    F = load_vector(p)
    A, Ixx, Iyy = 2 * R * tl, 2 * R * tl**3 / 12, tl * (2 * R) ** 3 / 12
    arm = H - z0
    beam = lambda x, y: F[2] / A - F[0] * arm * x / Iyy - F[1] * arm * y / Ixx
    x, y, z = series["x_mm"], series["y_mm"], series["z_mm"]
    sel = (np.abs(z - z0) < 1.0) & (np.abs(np.abs(x) - R) < 1e-3) & (np.abs(np.abs(y) - tl / 2) < 1e-3)
    if sel.sum() < 4:
        return None
    fe = series["szz_MPa"][sel]
    ref = beam(x[sel], y[sel])
    return {"z0_mm": z0, "max_abs_fe_MPa": float(np.max(np.abs(fe))), "max_abs_beam_MPa": float(np.max(np.abs(ref))),
            "max_err_rel": float(np.max(np.abs(fe - ref)) / np.max(np.abs(ref)))}


class ClevisBracketStudy(Study):
    name = "clevis_bracket"
    models = {"cadquery_ccx_clevis": CadQueryCalculiXClevis}
    metrics = frozenset({"peak_von_mises_MPa", "pin_deflection_mm", "mass_g"})
    param_names = PARAMS
    series_file = "nodal_results.csv"
    compare_description = "max relative difference over nodal columns"

    def derive(self, p):
        reach = _p(p, "lug_thickness_mm") / 2 + _p(p, "gusset_aspect") * _p(p, "gusset_height_mm") + _p(p, "fillet_radius_mm")
        if reach > _p(p, "base_width_mm") / 2:
            raise ValueError("the gussets and their fillets reach past the base plate")
        if _p(p, "base_thickness_mm") + _p(p, "gusset_height_mm") >= _p(p, "pin_height_mm"):
            raise ValueError("the gussets reach the pin height")
        return {"gusset_reach_mm": reach, "load_magnitude_N": float(np.linalg.norm(load_vector(p)))}

    def compute_metrics(self, series, p, case, outputs=None):
        vm = von_mises(series)
        a = assessed(series, p)
        return {"peak_von_mises_MPa": float(np.nanmax(vm[a])),
                "pin_deflection_mm": float(np.linalg.norm(outputs["pin_displacement_mm"])),
                "mass_g": outputs["cad_volume_mm3"] * _p(p, "density_t_per_mm3") * 1e6}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        p, m, out = point["parameters"], point["metrics"], point["solver_outputs"]
        F = load_vector(p)
        Fm = np.linalg.norm(F)
        r_pin = np.array([0.0, 0.0, _p(p, "pin_height_mm")])
        M_load = np.cross(r_pin, F)
        rf, rm = np.array(out["reaction_force_N"]), np.array(out["reaction_moment_Nmm"])
        checks = [
            check("cad_valid", "CadQuery B-rep is a valid solid (1 = no)", 0.0 if out["cad_valid"] else 1.0, 0.5),
            check("mesh_volume", "|meshed volume (straight-sided tets) - CAD volume| / CAD volume",
                  abs(out["mesh_volume_mm3"] - out["cad_volume_mm3"]) / out["cad_volume_mm3"], tol["mesh_volume_rel_tol"]),
            check("force_balance", "|sum of base reactions + pin load| / |pin load|",
                  float(np.linalg.norm(rf + F)) / Fm, tol["equilibrium_rel_tol"]),
            check("moment_balance", "|moment of the base reactions + moment of the pin load| about the origin / "
                  "(|F| x pin height) (the load acts where intended)",
                  float(np.linalg.norm(rm + M_load)) / (Fm * _p(p, "pin_height_mm")), tol["equilibrium_rel_tol"]),
        ]
        sc = section_check(series, p)
        if sc is not None:
            checks.append(check("lug_section_reference", f"max |sigma_zz FE - beam theory| / max |beam| at the lug "
                                f"section corners, z = {sc['z0_mm']:.1f} mm (model form)", sc["max_err_rel"],
                                tol["section_rel_tol"]))
        checks += [
            check("linear_material", "peak von Mises / yield strength", m["peak_von_mises_MPa"] / _p(p, "yield_strength_MPa"),
                  1.0, kind="validity"),
            check("small_deflection", "pin deflection / pin height", m["pin_deflection_mm"] / _p(p, "pin_height_mm"),
                  tol["small_deflection_max"], kind="validity"),
        ]
        clevis_figure(pdir / "response.png", series, p, m, title=(
            f"{point['label']}  (lug {_p(p, 'lug_thickness_mm'):.2f}, gussets {_p(p, 'gusset_thickness_mm'):.2f} x "
            f"{_p(p, 'gusset_height_mm'):.2f} mm; {out['elements']} quadratic tets)"))
        return checks

    def verify_run_level(self, case, manifest, points):
        opt = manifest.get("optimization")
        if opt:
            ok = opt.get("best_label") is not None
            return [check("optimum_found", "a verified candidate meets every requirement with the design margin "
                          "(1 = none)", 0.0 if ok else 1.0, 0.5),
                    check("optimizer_converged", "COBYLA met its final trust-region radius within the evaluation "
                          "limit (1 = no)", 0.0 if opt["optimizer"].get("success") else 1.0, 0.5)], \
                {"best_label": opt.get("best_label"), "evaluations": opt.get("evaluations")}
        size = case.get("sweep", {}).get("parameter")
        if size not in MESH_SIZE_PARAMETERS:
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: float(pt["parameters"][size]))
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(float(pt["parameters"][size]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
        # verification.mesh_study_metrics: the requirement metrics this sweep refines (default: all).
        # A fillet sweep leaves the global mesh, and so the pin deflection, unchanged: its three values
        # differ by round-off and give a meaningless order (clevis_confirm_r1_fillet: 4.72). Such a
        # metric's convergence must come from a global study, which the case header cites.
        all_metrics = sorted({r["metric"] for r in case["requirements"]})
        assessed_metrics = list(tol.get("mesh_study_metrics", all_metrics))
        unknown = sorted(set(assessed_metrics) - set(all_metrics))
        if unknown:
            raise ValueError(f"mesh_study_metrics {unknown} are not requirement metrics")
        detail["not_assessed_by_this_sweep"] = [m_ for m_ in all_metrics if m_ not in assessed_metrics]
        for metric in assessed_metrics:
            # verification.mesh_noise_rel: the mesh-to-mesh scatter of a resolved metric, measured
            # independently (a fillet peak is a nodal maximum on a tet mesh: 1.5 % peak to peak between
            # near-identical designs). Three levels that spread less than that are converged within the
            # noise; their order is meaningless (clevis_confirm_r2: 'divergent', R = 4.4, on a 0.99 %
            # spread). Default 1e-5: round-off only, as before.
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine), design_order=2,
                                           noise_floor=float(tol.get("mesh_noise_rel", 1e-5)))
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
            r = next(r for r in case["requirements"] if r["metric"] == metric)
            worst = fine[0]["metrics"][metric] * (1 + u["uncertainty"])
            checks.append(check(f"requirement_margin_{metric}", f"(finest {metric} x (1 + uncertainty) - limit) / limit, "
                                "must be <= 0", (worst - float(r["limit"])) / float(r["limit"]), 0.0) | {"metric": metric})
        return checks, detail


def clevis_figure(path, series, p, m, *, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from harness.plotting import GRID, SURFACE, TEXT, TEXT_2

    vm = von_mises(series)
    a = assessed(series, p)
    i = int(np.nanargmax(np.where(a, vm, -np.inf)))
    x, y, z = series["x_mm"], series["y_mm"], series["z_mm"]
    fig = plt.figure(figsize=(12, 5), facecolor=SURFACE)
    vmax = float(np.nanmax(vm[a]))
    for k, (elev, azim) in enumerate(((22, -60), (22, 120))):
        ax = fig.add_subplot(1, 2, k + 1, projection="3d")
        sc = ax.scatter(x, y, z, c=np.clip(vm, 0, vmax), cmap="turbo", s=0.6, vmin=0, vmax=vmax)
        ax.scatter([x[i]], [y[i]], [z[i]], s=60, facecolors="none", edgecolors="k", linewidths=1.5)
        ax.view_init(elev=elev, azim=azim)
        ax.set_box_aspect((np.ptp(x), np.ptp(y), np.ptp(z)))
        ax.set_xlabel("x (mm)", color=TEXT_2)
        ax.set_ylabel("y (mm)", color=TEXT_2)
        ax.set_zlabel("z (mm)", color=TEXT_2)
        ax.set_facecolor(SURFACE)
    fig.colorbar(sc, ax=fig.axes, shrink=0.6, label="von Mises (MPa), capped at the assessed peak")
    fig.suptitle(f"{title}\npeak {m['peak_von_mises_MPa']:.1f} MPa at ({x[i]:.1f}, {y[i]:.1f}, {z[i]:.1f}) mm; "
                 f"pin deflection {m['pin_deflection_mm'] * 1e3:.1f} µm; {m['mass_g']:.1f} g", color=TEXT, fontsize=9,
                 x=0.01, ha="left")
    fig.savefig(path, dpi=110, facecolor=SURFACE)
    plt.close(fig)


def optimization_figure(path, case, manifest):
    """History of the candidates: mass and both constraints against evaluation, and the design variables."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from harness.plotting import GRID, SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2

    opt = manifest["optimization"]
    hist = opt["history"]
    k = np.arange(len(hist))
    pts = {pt["label"]: pt for pt in manifest["points"]}
    mass = np.array([h["objective"] for h in hist])
    ver = np.array([h["verified"] for h in hist])
    feas = np.array([h["feasible"] for h in hist])
    names = [v["name"] for v in opt["variables"]]
    lim = {r["metric"]: float(r["limit"]) for r in case["requirements"]}
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(15, 4.2), facecolor=SURFACE)
    a1.plot(k, mass, color=TEXT_2, lw=0.8)
    a1.scatter(k[feas], mass[feas], s=18, color=SERIES_1, label="verified, feasible", zorder=3)
    a1.scatter(k[ver & ~feas], mass[ver & ~feas], s=18, facecolors="none", edgecolors=TEXT_2, label="verified, violates a limit")
    a1.scatter(k[~ver], mass[~ver], s=30, marker="x", color="#b0381a", label="rejected by the checks")
    if opt.get("best_label"):
        b = [h["label"] for h in hist].index(opt["best_label"])
        a1.scatter([b], [mass[b]], s=160, marker="*", color=TEXT, label=f"optimum {opt['best_label']} ({mass[b]:.1f} g)", zorder=4)
    a1.set_xlabel("candidate")
    a1.set_ylabel("mass (g)")
    a1.set_title("Mass", color=TEXT, loc="left", fontsize=10)
    for metric, color in (("peak_von_mises_MPa", SERIES_1), ("pin_deflection_mm", SERIES_2)):
        v = np.array([pts[h["label"]].get("metrics", {}).get(metric, np.nan) for h in hist]) / lim[metric]
        a2.plot(k, v, "o-", ms=3, lw=0.8, color=color, label=f"{metric} / limit")
    a2.axhline(1.0, color=TEXT, lw=1)
    a2.axhline(1 - opt["design_margin"], color=TEXT_2, lw=1, ls="--", label="design margin")
    a2.set_ylim(0, 1.6)
    a2.set_xlabel("candidate")
    a2.set_title("Constraints", color=TEXT, loc="left", fontsize=10)
    for n_, ls in zip(names, ("-", "--", ":")):
        a3.plot(k, [h["variables"][n_] for h in hist], ls, color=TEXT, lw=1.2, label=n_)
    a3.set_xlabel("candidate")
    a3.set_ylabel("mm")
    a3.set_title("Design variables", color=TEXT, loc="left", fontsize=10)
    for a in (a1, a2, a3):
        a.grid(color=GRID, lw=0.6)
        a.legend(frameon=False, fontsize=7.5, labelcolor=TEXT_2)
        a.tick_params(colors=TEXT_2)
        for s_ in a.spines.values():
            s_.set_color(GRID)
    fig.tight_layout()
    fig.savefig(path, dpi=120, facecolor=SURFACE)
    plt.close(fig)


STUDY = ClevisBracketStudy()
STUDY.optimization_figure = optimization_figure

"""Study: linearly tapered cantilever bracket, CAD-to-FEA static pipeline (the design loop's model).

Model:     cadquery_ccx_tapered (models/fea/tapered_bracket.py): CadQuery solid -> STEP ->
           Gmsh 10-node tetrahedra -> CalculiX static, tip shear traction
Reference: beam theory for the tapered cantilever (validation/tapered_beam.py): Timoshenko
           tip deflection by the unit-load method, nominal bending stress M / Z
Run-level: GCI on the requirement metrics when the sweep is the element size

Bending stress metric. The peak stress at the clamped root corner grows without limit with
refinement (a singularity), so it cannot be a design stress, and for h_t / h_r < 1/2 the
bending peak sits inside the span, not at the root. The study therefore measures, on the
tension surface between one root height from the clamp and one tip height from the load
(the smooth region), the ratio of the FE surface fibre stress to the nominal stress
M / Z = 6 F (L - x) / (b h(x)^2) (statics and section geometry), fits that ratio linearly
along x, and reports the peak over the span of ratio x nominal stress, extrapolating the
ratio to the root. The beam-theory check then tests that the measured ratio is close to 1;
the deflection check is fully independent of the metric.

This study is the model inside the optimisation loop (harness/optimize.py): every candidate
is a point of this study and must pass every check here to count.
"""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness.backend_base import Backend, failed
from harness.calculix import read_dat_total_forces, read_frd
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study
from validation import tapered_beam as tb

WRITER = "models/fea/tapered_bracket.py"


def _load_writer(path: Path):
    spec = importlib.util.spec_from_file_location("tapered_bracket_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_W = _load_writer(Path(__file__).resolve().parent.parent / WRITER)
PARAMS = _W.PARAMS + ("yield_strength_MPa",)


def _p(params, k):
    return float(params[k])


def _geom(params):
    return (_p(params, "tip_load_N"), _p(params, "length_mm"), _p(params, "width_mm"),
            _p(params, "root_height_mm"), _p(params, "tip_height_mm"))


class CadQueryCalculiXTapered(Backend):
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
        self._versions = {"cadquery": cadquery.__version__,
                          "gmsh": (g.stdout + g.stderr).strip().splitlines()[-1],
                          "CalculiX": (c.stdout.strip().splitlines() or ["?"])[-1]}

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="tapered_"))
        keep = ("bracket.step", "mesh.geo", "job.inp", "job.dat", "job.sta", "gmsh.log", "ccx.log")

        def files():
            return {n: work / n for n in keep if (work / n).exists()}

        try:
            volume = self.writer.build_step(params, work / "bracket.step")
            self.writer.write_geo(params, work / "mesh.geo")
            g = subprocess.run([str(self.gmsh), "mesh.geo", "-3", "-format", "inp", "-o", "mesh.inp"],
                               cwd=work, capture_output=True, text=True, timeout=1800)
            (work / "gmsh.log").write_text(g.stdout + g.stderr, encoding="utf-8")
            if g.returncode != 0 or not (work / "mesh.inp").exists():
                return failed(f"gmsh failed (exit {g.returncode})") | {"files": files(), "cleanup": work}
            info = self.writer.write_deck(params, work / "mesh.inp", work / "job.inp")
            c = subprocess.run([str(self.ccx), "-i", "job"], cwd=work, capture_output=True,
                               text=True, timeout=3600)
            (work / "ccx.log").write_text(c.stdout + c.stderr, encoding="utf-8")
            if c.returncode != 0 or not (work / "job.frd").exists():
                return failed(f"CalculiX failed (exit {c.returncode}); see ccx.log") | {
                    "files": files(), "cleanup": work}
        except Exception as e:
            return failed(f"{type(e).__name__}: {e}") | {"files": files(), "cleanup": work}

        frd = read_frd(work / "job.frd")
        ids = frd["nodes"]
        o = np.argsort(ids)
        series = {"node_id": ids[o].astype(float), "x_mm": frd["coords"][o, 0],
                  "y_mm": frd["coords"][o, 1], "z_mm": frd["coords"][o, 2]}
        d, s = frd["DISP"], frd["STRESS"]
        if not (np.array_equal(np.sort(d["ids"]), ids[o]) and np.array_equal(np.sort(s["ids"]), ids[o])):
            return failed("displacement or stress block does not cover every node") | {
                "files": files(), "cleanup": work}
        do, so = np.argsort(d["ids"]), np.argsort(s["ids"])
        for c_, n_ in (("D1", "ux_mm"), ("D2", "uy_mm"), ("D3", "uz_mm")):
            series[n_] = d[c_][do]
        for c_ in ("SXX", "SYY", "SZZ", "SXY", "SYZ", "SZX"):
            series[f"{c_.lower()}_MPa"] = s[c_][so]
        outputs = {**info, "volume_mm3": volume,
                   "reaction_root_N": list(read_dat_total_forces(work / "job.dat").get("ROOT", (np.nan,) * 3))}
        return {"success": True, "message": f"CalculiX: {info['elements']} C3D10, {info['nodes']} nodes",
                "nfev": None, "series": series, "outputs": outputs, "files": files(), "cleanup": work}

    def tool_versions(self):
        return self._versions


# ---------------------------------------------------------------------- stress measurement

def surface_ratio(series, params):
    """Tension-surface nodes in the smooth region: (x, FE fibre stress, nominal stress)."""
    F, L, b, hr, ht = _geom(params)
    x, z = series["x_mm"], series["z_mm"]
    h = tb.height(x, L, hr, ht)
    top = np.abs(z - h / 2) < 1e-4
    win = top & (x >= hr) & (x <= L - ht)
    th = np.arctan((ht - hr) / (2 * L))           # slope of the top surface
    c, s = np.cos(th), np.sin(th)
    fibre = series["sxx_MPa"] * c * c + 2 * series["szx_MPa"] * s * c + series["szz_MPa"] * s * s
    return x[win], fibre[win], tb.nominal_stress(x[win], F, L, b, hr, ht)


def stress_profile(series, params, n=2001):
    """Fitted ratio (linear in x), and the design stress along the span (x, ratio, stress)."""
    F, L, b, hr, ht = _geom(params)
    xw, fib, nom = surface_ratio(series, params)
    a1, a0 = np.polyfit(xw, fib / nom, 1)
    xs = np.linspace(0.0, L - ht, n)
    ratio = a0 + a1 * xs
    return xs, ratio, ratio * tb.nominal_stress(xs, F, L, b, hr, ht)


def binned_ratio(series, params, width):
    xw, fib, nom = surface_ratio(series, params)
    edges = np.arange(xw.min(), xw.max() + width, width)
    idx = np.digitize(xw, edges) - 1
    centres, means = [], []
    for k in range(len(edges) - 1):
        sel = idx == k
        if sel.sum() >= 3:
            centres.append(xw[sel].mean())
            means.append(float(np.mean(fib[sel] / nom[sel])))
    return np.array(centres), np.array(means)


# ---------------------------------------------------------------------- study

class TaperedBracketStudy(Study):
    name = "tapered_bracket"
    models = {"cadquery_ccx_tapered": CadQueryCalculiXTapered}
    metrics = frozenset({"tip_deflection_mm", "peak_bending_stress_MPa", "root_bending_stress_MPa",
                         "mass_g"})
    param_names = PARAMS
    series_file = "nodal_results.csv"
    compare_description = "max relative difference over nodal columns"

    def derive(self, params):
        F, L, b, hr, ht = _geom(params)
        if min(F, L, b, hr, ht, _p(params, "element_size_mm")) <= 0:
            raise ValueError("load, dimensions and element size must be positive")
        E, nu = _p(params, "youngs_modulus_MPa"), _p(params, "poisson_ratio")
        s_peak, x_peak = tb.peak_nominal_stress(F, L, b, hr, ht)
        return {"tip_deflection_beam_mm": tb.tip_deflection(F, L, E, nu, b, hr, ht),
                "peak_nominal_stress_MPa": s_peak, "peak_nominal_stress_x_mm": x_peak,
                "root_nominal_stress_MPa": float(tb.nominal_stress(0.0, F, L, b, hr, ht)),
                "volume_closed_form_mm3": tb.volume(L, b, hr, ht),
                "taper_slope": abs(hr - ht) / (2 * L), "root_height_over_length": hr / L}

    def compute_metrics(self, series, params, case, outputs=None):
        L = _p(params, "length_mm")
        tip = np.isclose(series["x_mm"], L, atol=1e-6)
        xs, ratio, sig = stress_profile(series, params)
        i = int(np.argmax(sig))
        return {"tip_deflection_mm": float(-np.mean(series["uz_mm"][tip])),
                "peak_bending_stress_MPa": float(sig[i]),
                "root_bending_stress_MPa": float(sig[0]),
                "mass_g": outputs["volume_mm3"] * _p(params, "density_t_per_mm3") * 1e6}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        p, d, m, out = point["parameters"], point["derived"], point["metrics"], point["solver_outputs"]
        F = _p(p, "tip_load_N")
        xs, ratio, sig = stress_profile(series, p)
        xb, rb = binned_ratio(series, p, 2 * _p(p, "element_size_mm"))
        rf = np.array(out["reaction_root_N"])
        checks = [
            check("cad_volume", "|CadQuery B-rep volume - b L (h_r + h_t) / 2| / closed form",
                  abs(out["volume_mm3"] - d["volume_closed_form_mm3"]) / d["volume_closed_form_mm3"], 1e-9),
            check("load_applied", "|sum of tip nodal forces + F| / F and |tip area from the mesh - b h_t| / (b h_t)",
                  max(abs(out["applied_load_N"] + F) / F,
                      abs(out["tip_area_mm2"] - _p(p, "width_mm") * _p(p, "tip_height_mm"))
                      / (_p(p, "width_mm") * _p(p, "tip_height_mm"))), 1e-9),
            check("equilibrium", "|R_root - (0, 0, F)| / F (sum of reactions)",
                  float(np.linalg.norm(rf - np.array([0.0, 0.0, F]))) / F, tol["equilibrium_rel_tol"]),
            check("deflection_reference", "|tip deflection FE - tapered Timoshenko beam| / beam (model form)",
                  abs(m["tip_deflection_mm"] - d["tip_deflection_beam_mm"]) / d["tip_deflection_beam_mm"],
                  tol["deflection_rel_tol"]),
            check("stress_ratio_reference", "max over the span of |fitted FE fibre stress / nominal M/Z - 1| "
                  "(model form: beam theory)", float(np.max(np.abs(ratio - 1.0))), tol["stress_rel_tol"]),
            check("stress_field_reference", "max over 2-element bins of |mean FE fibre stress / nominal - 1| "
                  "in the smooth region (field, model form)",
                  float(np.max(np.abs(rb - 1.0))) if len(rb) else float("inf"), tol["stress_field_rel_tol"]),
            check("linear_material", "peak bending stress / yield strength",
                  m["peak_bending_stress_MPa"] / _p(p, "yield_strength_MPa"), 1.0, kind="validity"),
            check("small_deflection", "tip deflection / length (geometrically linear analysis)",
                  m["tip_deflection_mm"] / _p(p, "length_mm"), tol["small_deflection_max"], kind="validity"),
            check("beam_reference_valid", "taper slope |h_r - h_t| / 2L (tapered beam theory)",
                  d["taper_slope"], tol["taper_slope_max"], kind="validity"),
            check("slender", "root height / length (beam theory)", d["root_height_over_length"],
                  tol["slenderness_max"], kind="validity"),
        ]
        bracket_figure(pdir / "response.png", series, p, d, m, xs, ratio, sig, xb, rb,
                       title=f"{point['label']}  (h_r {_p(p, 'root_height_mm'):.3f}, h_t {_p(p, 'tip_height_mm'):.3f} mm; "
                             f"{out['elements']} quadratic tets)")
        return checks

    def verify_run_level(self, case, manifest, points):
        opt = manifest.get("optimization")
        if opt:
            ok = opt.get("best_label") is not None
            return [check("optimum_found", "a verified candidate meets every requirement with the design "
                          "margin (1 = none)", 0.0 if ok else 1.0, 0.5),
                    check("optimizer_converged", "COBYLA met its final trust-region radius within the "
                          "evaluation limit (1 = no)", 0.0 if opt["optimizer"].get("success") else 1.0, 0.5)], \
                {"best_label": opt.get("best_label"), "evaluations": opt.get("evaluations")}
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
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine), design_order=2)
            detail[metric] = u
            checks.append(check(f"discretization_{metric}",
                                f"relative discretization uncertainty of {metric}, {describe(u)}",
                                u["uncertainty"], tol["gci_max"]) | {"metric": metric})
            # the requirement must hold with the discretisation error included (the optimum sits on it)
            r = next(r for r in case["requirements"] if r["metric"] == metric)
            worst = fine[0]["metrics"][metric] * (1 + u["uncertainty"])
            checks.append(check(f"requirement_margin_{metric}",
                                f"(finest {metric} x (1 + uncertainty) - limit) / limit, must be <= 0",
                                (worst - float(r["limit"])) / float(r["limit"]), 0.0) | {"metric": metric})
        sc = case.get("spot_check")
        if sc:
            p = case["parameters"]
            lim = {r["metric"]: float(r["limit"]) for r in case["requirements"]}
            ref = tb.optimum(*(_p(p, k) for k in ("tip_load_N", "length_mm", "youngs_modulus_MPa", "poisson_ratio",
                                                   "width_mm")),
                             lim["tip_deflection_mm"], lim["peak_bending_stress_MPa"],
                             tuple(tuple(v) for v in sc["bounds"]), margin=float(sc["design_margin"]))
            m_ref = ref["volume_mm3"] * _p(p, "density_t_per_mm3") * 1e6
            m_fe = fine[0]["metrics"]["mass_g"]
            detail["beam_theory_optimum"] = ref
            checks.append(check("optimum_vs_beam_theory", "|FE optimum mass - beam-theory optimum mass| / beam "
                                "(independent optimum, same limits and margin; model form)",
                                abs(m_fe - m_ref) / m_ref, float(sc["mass_rel_tol"])))
        return checks, detail


def bracket_figure(path, series, p, d, m, xs, ratio, sig, xb, rb, *, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from harness.plotting import GRID, SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2

    F, L, b, hr, ht = _geom(p)
    xw, fib, nom = surface_ratio(series, p)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2), facecolor=SURFACE)
    xr = np.linspace(0, L, 400)
    a1.plot(xr, tb.nominal_stress(xr, F, L, b, hr, ht), color=SERIES_2, lw=2, label="beam theory, M / Z")
    a1.plot(xw, fib, ".", ms=1.5, color=SERIES_1, alpha=0.5, label="FE fibre stress, tension surface")
    a1.plot(xs, sig, color=TEXT, lw=1.2, label="design stress (fitted ratio x M / Z)")
    a1.plot([xs[np.argmax(sig)]], [sig.max()], "o", color=TEXT, ms=5)
    a1.axvspan(0, hr, color=GRID, alpha=0.7, lw=0)
    a1.axvspan(L - ht, L, color=GRID, alpha=0.7, lw=0, label="clamp and load zones (not fitted)")
    a1.set_ylim(0, 1.3 * max(d["peak_nominal_stress_MPa"], float(sig.max())))
    a1.set_xlabel("distance from the clamp (mm)")
    a1.set_ylabel("bending stress (MPa)")
    a1.set_title(f"Peak {m['peak_bending_stress_MPa']:.1f} MPa at {xs[np.argmax(sig)]:.0f} mm", color=TEXT,
                 loc="left", fontsize=10)
    a2.plot(xw, fib / nom, ".", ms=1.5, color=SERIES_1, alpha=0.4, label="FE / nominal, per node")
    a2.plot(xb, rb, "s", ms=3, color=SERIES_1, label="2-element bin means")
    a2.plot(xs, ratio, color=TEXT, lw=1.2, label="linear fit")
    a2.axhline(1.0, color=SERIES_2, lw=1.2, ls="--", label="beam theory")
    a2.set_ylim(0.9, 1.1)
    a2.set_xlabel("distance from the clamp (mm)")
    a2.set_ylabel("FE fibre stress / nominal M/Z")
    a2.set_title(f"Tip deflection {m['tip_deflection_mm']:.4f} mm (beam {d['tip_deflection_beam_mm']:.4f})",
                 color=TEXT, loc="left", fontsize=10)
    for a in (a1, a2):
        a.grid(color=GRID, lw=0.6)
        a.legend(frameon=False, fontsize=8, labelcolor=TEXT_2)
        a.tick_params(colors=TEXT_2)
        for s_ in a.spines.values():
            s_.set_color(GRID)
    fig.suptitle(title, color=TEXT, fontsize=10, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=110, facecolor=SURFACE)
    plt.close(fig)


def optimization_figure(path, case, manifest):
    """Design space (h_r, h_t) from beam theory, with every FE candidate the optimiser tried."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from harness.plotting import GRID, SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2

    p = case["parameters"]
    opt = manifest["optimization"]
    F, L, b = _p(p, "tip_load_N"), _p(p, "length_mm"), _p(p, "width_mm")
    E, nu, rho = _p(p, "youngs_modulus_MPa"), _p(p, "poisson_ratio"), _p(p, "density_t_per_mm3")
    lim = {r["metric"]: float(r["limit"]) for r in case["requirements"]}
    var = {v["name"]: v for v in opt["variables"]}
    hr_ax = np.linspace(var["root_height_mm"]["lower"], var["root_height_mm"]["upper"], 70)
    ht_ax = np.linspace(var["tip_height_mm"]["lower"], var["tip_height_mm"]["upper"], 70)
    HR, HT = np.meshgrid(hr_ax, ht_ax, indexing="ij")
    D = np.vectorize(lambda a, c: tb.tip_deflection(F, L, E, nu, b, a, c))(HR, HT)
    S = np.vectorize(lambda a, c: tb.peak_nominal_stress(F, L, b, a, c)[0])(HR, HT)
    M = tb.volume(L, b, HR, HT) * rho * 1e6
    infeasible = (D > lim["tip_deflection_mm"]) | (S > lim["peak_bending_stress_MPa"])
    fig, ax = plt.subplots(figsize=(7.6, 6.2), facecolor=SURFACE)
    ax.contourf(HR, HT, infeasible.astype(float), levels=[0.5, 1.5], colors=[GRID], alpha=0.8)
    cm = ax.contour(HR, HT, M, levels=12, colors=TEXT_2, linewidths=0.5, alpha=0.6)
    ax.clabel(cm, fmt="%d g", fontsize=7)
    ax.contour(HR, HT, D, levels=[lim["tip_deflection_mm"]], colors=[SERIES_2], linewidths=1.6, linestyles="--")
    ax.contour(HR, HT, S, levels=[lim["peak_bending_stress_MPa"]], colors=[SERIES_2], linewidths=1.6)
    hist = opt["history"]
    xy = np.array([[h["variables"]["root_height_mm"], h["variables"]["tip_height_mm"]] for h in hist])
    ax.plot(xy[:, 0], xy[:, 1], color=SERIES_1, lw=0.6, alpha=0.5)
    for h, (a, c) in zip(hist, xy):
        if not h["verified"]:
            ax.plot(a, c, "x", color="#b0381a", ms=6, mew=1.5)
        else:
            ax.plot(a, c, "o", ms=3.5, color=SERIES_1 if h["feasible"] else TEXT_2,
                    mfc=SERIES_1 if h["feasible"] else "none")
    try:
        ref = tb.optimum(F, L, E, nu, b, lim["tip_deflection_mm"], lim["peak_bending_stress_MPa"],
                         ((var["root_height_mm"]["lower"], var["root_height_mm"]["upper"]),
                          (var["tip_height_mm"]["lower"], var["tip_height_mm"]["upper"])),
                         margin=opt["design_margin"])
        ax.plot(ref["root_height_mm"], ref["tip_height_mm"], "D", ms=9, mfc="none", mec=SERIES_2, mew=1.6,
                label=f"beam-theory optimum ({ref['volume_mm3'] * rho * 1e6:.1f} g)")
    except RuntimeError:
        pass
    if opt.get("best_label"):
        bv = opt["best_variables"]
        ax.plot(bv["root_height_mm"], bv["tip_height_mm"], "*", ms=15, color=TEXT,
                label=f"FE optimum {opt['best_label']} ({opt['best_objective']:.1f} g)")
    ax.plot([], [], "o", ms=4, color=SERIES_1, label="candidate, verified and feasible")
    ax.plot([], [], "o", ms=4, color=TEXT_2, mfc="none", label="candidate, verified, violates a limit")
    ax.plot([], [], "x", color="#b0381a", label="candidate rejected by the checks")
    ax.plot([], [], color=SERIES_2, ls="--", label=f"deflection = {lim['tip_deflection_mm']:g} mm (beam theory)")
    ax.plot([], [], color=SERIES_2, label=f"peak stress = {lim['peak_bending_stress_MPa']:g} MPa (beam theory)")
    ax.set_xlabel("root height h_r (mm)")
    ax.set_ylabel("tip height h_t (mm)")
    ax.set_title(f"{len(hist)} FE candidates; grey: infeasible by beam theory", color=TEXT, loc="left", fontsize=10)
    ax.grid(color=GRID, lw=0.6)
    ax.legend(frameon=False, fontsize=7.5, labelcolor=TEXT_2, loc="upper right")
    ax.tick_params(colors=TEXT_2)
    for s_ in ax.spines.values():
        s_.set_color(GRID)
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=SURFACE)
    plt.close(fig)


STUDY = TaperedBracketStudy()
STUDY.optimization_figure = optimization_figure

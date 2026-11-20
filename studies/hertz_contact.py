"""Study: roller-on-plate contact, CalculiX surface-to-surface contact vs Hertz.

Model:     gmsh_ccx_contact (models/fea/hertz_contact.py): scripted Gmsh mesh of a
           quarter roller on a half block, one-layer hexes in plane strain,
           CalculiX penalty contact, displacement-controlled approach
Reference: Hertz line contact (validation/hertz.py), evaluated at the line load
           the model actually carries
Run-level: GCI on every requirement metric when the sweep is the contact
           element size

Pressure is read from CalculiX's own contact output (CPRESS at the roller's
surface nodes), not from element stresses extrapolated to the surface, which
overstate the surface pressure by several percent on linear hexes (found in
the prototype; see the case file).
"""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit

from harness.backend_base import Backend, failed
from harness.calculix import read_dat_total_forces, read_frd
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study
from validation import hertz

WRITER = "models/fea/hertz_contact.py"


def _load_writer(path: Path):
    spec = importlib.util.spec_from_file_location("hertz_contact_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_W = _load_writer(Path(__file__).resolve().parent.parent / WRITER)


def _p(params, k):
    return float(params[k])


def fit_half_width(x, p, guess_p0, guess_a):
    """Half-width and peak of the best-fit semi-ellipse through the nodal pressures."""
    f = lambda x, p0, a: p0 * np.sqrt(np.clip(1 - (x / a) ** 2, 0, None))  # noqa: E731
    (p0, a), _ = curve_fit(f, x, p, p0=[guess_p0, guess_a])
    return float(a), float(p0)


class GmshCalculiXContact(Backend):
    sources = (WRITER,)

    def __init__(self):
        from studies.fin import find_ccx

        self.ccx = find_ccx()
        self.gmsh = self.ccx.parent / "gmsh.exe"
        if not self.gmsh.exists():
            raise RuntimeError("gmsh.exe not found next to ccx")
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        self.writer = _load_writer(self.source_path(WRITER, source_dir))
        g = subprocess.run([str(self.gmsh), "--version"], capture_output=True, text=True, timeout=60)
        c = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"gmsh": (g.stdout + g.stderr).strip().splitlines()[-1],
                          "CalculiX": (c.stdout.strip().splitlines() or ["?"])[-1]}

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="hertz_"))
        keep = ("mesh.geo", "job.inp", "job.dat", "job.sta", "gmsh.log", "ccx.log")

        def files():
            return {n: work / n for n in keep if (work / n).exists()}

        def fail(msg):
            res = failed(msg)
            res.update(files=files(), cleanup=work)
            return res

        try:
            self.writer.write_geo(params, work / "mesh.geo")
            g = subprocess.run([str(self.gmsh), "mesh.geo", "-3", "-format", "inp", "-o", "mesh.inp"],
                               cwd=work, capture_output=True, text=True, timeout=1200)
            (work / "gmsh.log").write_text(g.stdout + g.stderr, encoding="utf-8")
            if g.returncode != 0 or not (work / "mesh.inp").exists():
                return fail(f"gmsh failed (exit {g.returncode})")
            info = self.writer.write_deck(params, work / "mesh.inp", work / "job.inp")
            c = subprocess.run([str(self.ccx), "-i", "job"], cwd=work, capture_output=True,
                               text=True, timeout=7200)
            (work / "ccx.log").write_text(c.stdout + c.stderr, encoding="utf-8")
            if c.returncode != 0 or not (work / "job.frd").exists():
                return fail(f"CalculiX failed (exit {c.returncode}); see ccx.log")
            ids, xyz, elems = self.writer.read_mesh(work / "mesh.inp")
            r = read_frd(work / "job.frd")
            forces = read_dat_total_forces(work / "job.dat")
        except Exception as e:  # mesh, deck or parse errors are evidence too
            return fail(f"{type(e).__name__}: {e}")

        R = _p(params, "roller_radius_mm")
        coord = dict(zip(ids.tolist(), xyz))
        roller = set(np.unique(elems["ROLLER"][:, 1:]).tolist())
        block = set(np.unique(elems["BLOCK"][:, 1:]).tolist())
        # contact pressure on the roller surface, front face (z = 0), within a quarter radius
        C = r["CONTACT"]
        prof = sorted((coord[int(n)][0], float(p), float(o)) for n, p, o in zip(C["ids"], C["CPRESS"], C["COPEN"])
                      if int(n) in roller and abs(coord[int(n)][2]) < 1e-9 and coord[int(n)][0] <= 0.25 * R
                      and abs(np.hypot(coord[int(n)][0], coord[int(n)][1] - R) - R) < 1e-4 * R)
        x, p, opening = (np.array(v) for v in zip(*prof))
        # in-plane shear below the contact centre, block side (x = 0, z = 0)
        S = r["STRESS"]
        si = {int(n): k for k, n in enumerate(S["ids"])}
        axis = sorted((-coord[n][1], (S["SXX"][si[n]] - S["SYY"][si[n]]) / 2,
                       S["SXX"][si[n]], S["SYY"][si[n]])
                      for n in block if abs(coord[n][0]) < 1e-9 and abs(coord[n][2]) < 1e-9
                      and coord[n][1] > -0.1 * R)
        depth, tau, sxx, syy = (np.array(v) for v in zip(*axis))
        series = {"x_mm": x, "contact_pressure_MPa": p, "contact_opening_mm": opening}
        outputs = {**info, "reaction_totals_N": forces,
                   "axis": {"depth_mm": depth.tolist(), "tau_MPa": tau.tolist(),
                            "sxx_MPa": sxx.tolist(), "syy_MPa": syy.tolist()}}
        return {"success": True, "message": f"CalculiX contact: {info['nodes']} nodes",
                "nfev": None, "series": series, "outputs": outputs, "files": files(), "cleanup": work}

    def tool_versions(self):
        return self._versions


def subsurface_peak(axis) -> tuple[float, float]:
    """Peak of the shear profile below the contact, located between nodes by a parabola
    through the largest nodal value and its two neighbours.

    The largest nodal value alone is a sampled maximum: which node sits nearest
    the true peak changes from mesh to mesh, so it does not converge smoothly
    (contact_roller_mesh run 20261120-120004: 184.3 / 184.2 / 184.3 MPa, which the
    GCI classed as divergent)."""
    d, t = np.asarray(axis["depth_mm"]), np.asarray(axis["tau_MPa"])
    k = int(np.argmax(t))
    if k == 0 or k == len(t) - 1:
        return float(t[k]), float(d[k])
    c2, c1, c0 = np.polyfit(d[k - 1:k + 2], t[k - 1:k + 2], 2)
    z = -c1 / (2 * c2)
    if c2 >= 0 or not d[k - 1] <= z <= d[k + 1]:
        return float(t[k]), float(d[k])
    return float(c0 + c1 * z + c2 * z * z), float(z)


def line_load(params, outputs):
    return 2 * abs(outputs["reaction_totals_N"]["TOP"][1]) / _p(params, "slab_thickness_mm")


def reference(params, P):
    return hertz.line_contact(P, _p(params, "roller_radius_mm"), _p(params, "youngs_modulus_MPa"),
                              _p(params, "poisson_ratio"))


class HertzContactStudy(Study):
    name = "hertz_contact"
    models = {"gmsh_ccx_contact": GmshCalculiXContact}
    metrics = frozenset({"line_load_N_per_mm", "peak_contact_pressure_MPa", "contact_half_width_mm",
                         "max_subsurface_shear_MPa", "max_shear_depth_mm"})
    param_names = _W.PARAMS
    series_file = "contact_profile.csv"
    compare_description = "max relative difference in contact pressure"

    def derive(self, params):
        R, E, nu = (_p(params, k) for k in ("roller_radius_mm", "youngs_modulus_MPa", "poisson_ratio"))
        if min(R, E, _p(params, "approach_mm")) <= 0 or not 0 <= nu < 0.5:
            raise ValueError("positive radius, modulus and approach; 0 <= nu < 0.5")
        return {"E_star_MPa": hertz.effective_modulus(E, nu),
                "penalty_N_per_mm3": _p(params, "penalty_stiffness_factor") * E
                / _p(params, "contact_element_size_mm")}

    def compute_metrics(self, series, params, case, outputs=None):
        P = line_load(params, outputs)
        ref = reference(params, P)
        x, p = series["x_mm"], series["contact_pressure_MPa"]
        a, _ = fit_half_width(x, p, ref["peak_pressure_MPa"], ref["half_width_mm"])
        tau_max, z_max = subsurface_peak(outputs["axis"])
        return {"line_load_N_per_mm": P, "peak_contact_pressure_MPa": float(np.max(p)),
                "contact_half_width_mm": a, "max_subsurface_shear_MPa": tau_max,
                "max_shear_depth_mm": z_max}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        prm, m, out = point["parameters"], point["metrics"], point["solver_outputs"]
        P = m["line_load_N_per_mm"]
        ref = reference(prm, P)
        a, p0 = ref["half_width_mm"], ref["peak_pressure_MPa"]
        rf = out["reaction_totals_N"]
        x, p = series["x_mm"], series["contact_pressure_MPa"]
        h = _p(prm, "contact_element_size_mm")
        force = 2 * float(np.trapezoid(p, x))                       # both halves, per mm
        penetration = max(0.0, -float(np.min(series["contact_opening_mm"])))
        checks = [
            check("equilibrium", "|reaction at the roller top + reaction at the block base| / load",
                  abs(rf["TOP"][1] + rf["BOTTOM"][1]) / abs(rf["TOP"][1]), tol["equilibrium_rel_tol"]),
            check("contact_force_balance", "|2 x integral of contact pressure dx - line load| / line load",
                  abs(force - P) / P, tol["force_balance_rel_tol"]),
            check("hertz_peak_pressure", "|peak contact pressure - Hertz p0 at this load| / p0",
                  abs(m["peak_contact_pressure_MPa"] - p0) / p0, tol["hertz_rel_tol"]),
            check("hertz_half_width", "|fitted contact half-width - Hertz a| / a",
                  abs(m["contact_half_width_mm"] - a) / a, tol["hertz_rel_tol"]),
            check("hertz_subsurface_shear", "|max shear below the contact - Hertz 0.300 p0| / (0.300 p0)",
                  abs(m["max_subsurface_shear_MPa"] - ref["max_shear_MPa"]) / ref["max_shear_MPa"],
                  tol["subsurface_rel_tol"]),
            check("hertz_shear_depth", "|depth of max shear - Hertz 0.786 a| / element size (node-spacing limited)",
                  abs(m["max_shear_depth_mm"] - ref["max_shear_depth_mm"]) / h, tol["depth_elements_tol"]),
            check("resolution", "elements across the contact half-width (Hertz a / element size), inverted",
                  h / a, 1.0 / tol["min_elements_across_contact"], kind="validity"),
            check("penalty_penetration", "max penetration of the penalty contact / approach",
                  penetration / _p(prm, "approach_mm"), tol["penetration_max_fraction"]),
            check("elastic", "max subsurface shear / shear yield (Tresca, yield / 2)",
                  m["max_subsurface_shear_MPa"] / (_p(prm, "yield_strength_MPa") / 2), 1.0, kind="validity"),
        ]
        hertz_figure(pdir / "response.png", series, out["axis"], ref,
                     title=f"{point['label']}  ({out['nodes']} nodes, contact elements {h:g} mm, "
                           f"P' = {P:.1f} N/mm)")
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "contact_element_size_mm":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: pt["parameters"]["contact_element_size_mm"])
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(float(pt["parameters"]["contact_element_size_mm"]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
        for metric in sorted({r["metric"] for r in case["requirements"]}):
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine))
            detail[metric] = u
            checks.append(check(f"discretization_{metric}",
                                f"relative discretization uncertainty of {metric}, {describe(u)}",
                                u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


def hertz_figure(path, series, axis, ref, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from harness.plotting import GRID, SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2

    a, p0 = ref["half_width_mm"], ref["peak_pressure_MPa"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2), facecolor=SURFACE)
    xs = np.linspace(0, 1.6 * a, 400)
    ax1.plot(xs / a, hertz.pressure(xs, a, p0) / p0, color=SERIES_2, lw=2, label="Hertz (exact)")
    ax1.plot(series["x_mm"] / a, series["contact_pressure_MPa"] / p0, "o", ms=4, color=SERIES_1,
             label="CalculiX contact pressure")
    ax1.set_xlim(0, 1.6)
    ax1.set_xlabel("x / a  (distance from the contact centre / Hertz half-width)")
    ax1.set_ylabel("p / p0")
    ax1.set_title("Contact pressure", color=TEXT, loc="left", fontsize=10)
    d = np.array(axis["depth_mm"])
    zs = np.linspace(0, 3 * a, 400)
    ax2.plot(hertz.subsurface_shear(zs, a, p0) / p0, zs / a, color=SERIES_2, lw=2, label="Hertz (exact)")
    ax2.plot(np.array(axis["tau_MPa"]) / p0, d / a, "o", ms=4, color=SERIES_1, label="CalculiX, block below the contact")
    ax2.set_ylim(3, 0)
    ax2.set_xlabel("in-plane shear (σx − σz)/2  / p0")
    ax2.set_ylabel("depth / a")
    ax2.set_title("Shear stress below the contact centre", color=TEXT, loc="left", fontsize=10)
    for ax in (ax1, ax2):
        ax.grid(color=GRID, lw=0.6)
        ax.legend(frameon=False, fontsize=8.5, labelcolor=TEXT_2)
        ax.tick_params(colors=TEXT_2)
        for s in ax.spines.values():
            s.set_color(GRID)
    fig.suptitle(title, color=TEXT, fontsize=10, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=130, facecolor=SURFACE)
    plt.close(fig)


STUDY = HertzContactStudy()

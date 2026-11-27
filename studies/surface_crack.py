"""Study 24 part 2: a semi-elliptical surface crack in the plate of part 1: K along the front, growth life.

Model:     gmsh_ccx_surface_crack (models/fea/surface_crack.py): Gmsh quarter model, 10-node tetrahedra refined at
           the crack front, CalculiX. Each point solves a list of crack shapes (a, c) on the growth path, each with
           two scaled neighbours (a, c) (1 -+ eps) for the energy route
Reference: Newman and Raju's (1981) equations (BS 7910's surface-crack solution, stated accuracy +-5 %), against
           the FE energy route (front average) and the crack-opening route (K along the front); global equilibrium;
           the life integral by two integrators
Answer:    the life from the detectable flaw to a = 0.8 t (the end of Newman-Raju's range, and a lower bound on the
           full life, since breakthrough and the through crack's growth are left out) by the BS 7910 procedure
           (Newman-Raju K at the deepest and surface points, the BS 7910 / IIW law), and again with K scaled by the
           FE's energy-route ratio
Run-level: GCI on the FE metrics when the sweep is the relative front element size
"""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

from harness.backend_base import Backend, failed
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study

WRITER = "models/fea/surface_crack.py"
PARAMS = ("half_width_mm", "half_height_mm", "thickness_mm", "sigma_max_MPa", "stress_ratio", "youngs_modulus_MPa",
          "poisson_ratio", "k_mat_MPa_sqrt_m", "paris_C", "paris_m", "dK_threshold", "initial_depth_mm",
          "initial_half_length_mm", "end_depth_ratio", "front_element_rel", "far_element_size_mm",
          "edge_crack_life_cycles")
MPA_SQRT_M = 31.6227766  # N/mm^1.5 per MPa sqrt(m)
STATIONS = tuple(float(x) for x in range(0, 91, 5))   # degrees, phi = 0 at the surface


def _writer(path: Path):
    spec = importlib.util.spec_from_file_location("surface_crack_writer", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class GmshCalculiXSurfaceCrack(Backend):
    sources = (WRITER,)

    def __init__(self):
        from studies.cantilever import find_freecadcmd

        self.ccx = find_freecadcmd().parent / "ccx.exe"
        if not self.ccx.exists():
            raise RuntimeError("ccx.exe not found next to freecadcmd")
        self.sc = None
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        import gmsh

        self.sc = _writer(self.source_path(WRITER, source_dir))
        c = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"gmsh (Python API)": gmsh.__version__,
                          "calculix": (c.stdout + c.stderr).strip().splitlines()[-1]}

    def _prepare_one(self, work: Path, a: float, c: float, p: dict) -> dict:
        sc = self.sc
        h = float(p["front_element_rel"]) * a          # front element size scales with the crack depth
        work.mkdir(parents=True, exist_ok=True)
        g = dict(Wh=float(p["half_width_mm"]), H=float(p["half_height_mm"]), t=float(p["thickness_mm"]))
        m = sc.mesh(work / "mesh.inp", a=a, c=c, h_front=h, h_far=float(p["far_element_size_mm"]), r_fine=4 * h, **g)
        info = sc.write_deck(work / "mesh.inp", work / "job.inp", a=a, c=c, sigma=float(p["sigma_max_MPa"]),
                             E=float(p["youngs_modulus_MPa"]), nu=float(p["poisson_ratio"]), **g)
        return {"work": work, "a": a, "c": c, "h": h, "info": info, "mesh": m}

    def _run_one(self, job: dict, timeout: float) -> dict:
        work = job["work"]
        r = subprocess.run([str(self.ccx), "-i", "job"], cwd=work, capture_output=True, text=True, timeout=timeout)
        (work / "ccx.log").write_text(r.stdout + r.stderr, encoding="utf-8")
        if r.returncode != 0 or "Job finished" not in r.stdout:
            raise RuntimeError(f"CalculiX failed at a = {job['a']}, c = {job['c']} (exit {r.returncode})")
        top, crack, rf = self.sc.read_node_print(work / "job.dat")
        P = job["info"]["applied_load_N"]
        return job | {"U": self.sc.quarter_energy(top, job["info"]), "crack": crack, "eq": abs(rf + P) / P}

    def solve(self, params, numerics, tolerance_scale=1.0):
        sc, p = self.sc, params
        work = Path(tempfile.mkdtemp(prefix="scrack_"))
        E, nu = float(p["youngs_modulus_MPa"]), float(p["poisson_ratio"])
        t, b, sig = float(p["thickness_mm"]), float(p["half_width_mm"]), float(p["sigma_max_MPa"])
        eps = float(numerics["energy_eps"])
        shapes = [(float(a), float(c)) for a, c in numerics["crack_shapes_mm"]]
        a_chk, c_chk = shapes[0]
        plan = []
        for k, (a, c) in enumerate(shapes):
            for tag, f in (("mid", 1.0), ("lo", 1 - eps), ("hi", 1 + eps)):
                plan.append((f"s{k}_{tag}", a * f, c * f))
        for tag, f in (("chk_lo", 1 - eps / 2), ("chk_hi", 1 + eps / 2)):   # the step check at the first shape
            plan.append((tag, a_chk * f, c_chk * f))
        try:
            jobs = {name: self._prepare_one(work / name, a, c, p) for name, a, c in plan}   # Gmsh: one at a time
            with ThreadPoolExecutor(max_workers=int(numerics.get("parallel_solves", 6))) as ex:
                futs = {n: ex.submit(self._run_one, j, float(numerics.get("solve_timeout_s", 7200)))
                        for n, j in jobs.items()}
                done = {n: f.result() for n, f in futs.items()}
        except (RuntimeError, subprocess.TimeoutExpired) as e:
            return failed(f"{type(e).__name__}: {e}") | {"cleanup": work}
        rows = []
        for k, (a, c) in enumerate(shapes):
            mid, lo, hi = done[f"s{k}_mid"], done[f"s{k}_lo"], done[f"s{k}_hi"]
            h = mid["h"]
            prof = sc.k_profile(mid["crack"], mid["info"], a=a, c=c, E=E, nu=nu, stations_deg=STATIONS,
                                r_min=3 * h, r_max=max(0.3 * a, 6 * h), band=1.5 * h)
            K_fe = np.array([q["K"] for q in prof])
            K_nr = sig * np.sqrt(np.pi * a) * sc.newman_raju_F(a, c, t, b, np.radians(STATIONS))
            dU = (hi["U"] - lo["U"]) / (2 * eps)
            nr_int = sc.energy_integral(STATIONS, K_nr, a, c, E, nu)
            rows.append({"a_mm": a, "c_mm": c, "h_front_mm": h, "nodes": mid["info"]["nodes"],
                         "elements": mid["info"]["elements"], "dU_deps": dU, "nr_integral": nr_int,
                         "opening_integral": sc.energy_integral(STATIONS, K_fe, a, c, E, nu),
                         "K_fe": K_fe.tolist(), "K_nr": K_nr.tolist(), "points": [q["points"] for q in prof],
                         "equilibrium": max(mid["eq"], lo["eq"], hi["eq"]),
                         "load_area": max(abs(j["info"]["area_check"] - 1) for j in (mid, lo, hi))})
        chk = (done["chk_hi"]["U"] - done["chk_lo"]["U"]) / eps
        series = {"a_mm": np.array([r["a_mm"] for r in rows]), "c_mm": np.array([r["c_mm"] for r in rows]),
                  "K_deep_fe": np.array([r["K_fe"][-1] for r in rows]),
                  "K_deep_nr": np.array([r["K_nr"][-1] for r in rows]),
                  "energy_ratio": np.array([np.sqrt(r["dU_deps"] / r["nr_integral"]) for r in rows]),
                  "opening_ratio": np.array([np.sqrt(r["opening_integral"] / r["nr_integral"]) for r in rows])}
        return {"success": True, "message": f"{len(shapes)} shapes x 3 solves + step check, h/a "
                f"{float(p['front_element_rel'])}", "nfev": len(plan), "series": series,
                "outputs": {"rows": rows, "stations_deg": list(STATIONS),
                            "step_check": {"a_mm": a_chk, "c_mm": c_chk, "dU_deps_eps": rows[0]["dU_deps"],
                                           "dU_deps_half_eps": chk}},
                "files": {}, "cleanup": work}

    def tool_versions(self):
        return self._versions


def _nr(params):
    sc = _writer(Path(__file__).resolve().parent.parent / WRITER)
    return sc.newman_raju_F


def growth(params, ratio_of_a=None, *, method="DOP853"):
    """BS 7910 two-point growth of the surface crack from (a0, c0) to a = end_depth_ratio * t, with Newman-Raju K at
    the deepest (phi = 90) and surface (phi = 0) points, each multiplied by ratio_of_a(a) when given. Returns a
    dict with the life and the end state."""
    p = params
    F = _nr(p)
    t, b, smax, R = (float(p[k]) for k in ("thickness_mm", "half_width_mm", "sigma_max_MPa", "stress_ratio"))
    C, m, th = float(p["paris_C"]), float(p["paris_m"]), float(p["dK_threshold"])
    a_end = float(p["end_depth_ratio"]) * t
    s = (lambda a: 1.0) if ratio_of_a is None else ratio_of_a

    def K(a, c, phi):
        return s(a) * smax * np.sqrt(np.pi * a) * F(a, c, t, b, phi)

    def rate(dk):
        return C * dk ** m if dk > th else 0.0

    def rhs(N, y):
        a, c = y
        return [rate((1 - R) * K(a, c, np.pi / 2)), rate((1 - R) * K(a, c, 0.0))]

    def end(N, y):
        return y[0] - a_end
    end.terminal = True
    y0 = [float(p["initial_depth_mm"]), float(p["initial_half_length_mm"])]
    sol = solve_ivp(rhs, [0, 1e9], y0, method=method, events=end, rtol=1e-10, atol=1e-10)
    if not sol.t_events[0].size:
        raise ValueError("the crack did not reach the end depth")
    N = float(sol.t_events[0][0])
    a, c = (float(v) for v in sol.y_events[0][0])
    return {"life": N, "a_end": a, "c_end": c, "K_deep_end": K(a, c, np.pi / 2), "K_surf_end": K(a, c, 0.0),
            "K_deep_a0": K(*y0, np.pi / 2), "K_surf_a0": K(*y0, 0.0), "max_a_over_c": max(sol.y[0] / sol.y[1])}


def ratio_function(a_mm, ratio):
    """Linear in a between the FE shapes, constant beyond them."""
    a_mm, ratio = np.asarray(a_mm, float), np.asarray(ratio, float)
    return lambda a: float(np.interp(a, a_mm, ratio))


class SurfaceCrackStudy(Study):
    name = "surface_crack"
    models = {"gmsh_ccx_surface_crack": GmshCalculiXSurfaceCrack}
    metrics = frozenset({"K_a0_MPa_sqrt_m", "K_a0_nr_MPa_sqrt_m", "energy_ratio_min", "energy_ratio_max",
                         "growth_life_cycles", "growth_life_fe_cycles", "life_over_edge_crack"})
    param_names = PARAMS
    series_file = "k_shapes.csv"
    compare_description = "FE / Newman-Raju K ratio (energy route) per crack shape"

    def derive(self, params):
        if not 0 < float(params["stress_ratio"]) < 1:
            raise ValueError("stress ratio must be between 0 and 1")
        return {}

    def compute_metrics(self, series, params, case, outputs=None):
        g = growth(params)
        gf = growth(params, ratio_function(series["a_mm"], series["energy_ratio"]))
        return {"K_a0_MPa_sqrt_m": float(series["K_deep_fe"][0]) / MPA_SQRT_M,
                "K_a0_nr_MPa_sqrt_m": g["K_deep_a0"] / MPA_SQRT_M,
                "energy_ratio_min": float(np.min(series["energy_ratio"])),
                "energy_ratio_max": float(np.max(series["energy_ratio"])),
                "growth_life_cycles": g["life"], "growth_life_fe_cycles": gf["life"],
                "life_over_edge_crack": g["life"] / float(params["edge_crack_life_cycles"])}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        p, out = point["parameters"], point["solver_outputs"]
        rows, st = out["rows"], np.asarray(out["stations_deg"])
        prof = st >= float(tol["profile_from_deg"])
        ratios = [np.asarray(row["K_fe"])[prof] / np.asarray(row["K_nr"])[prof] for row in rows]
        shape = max(float(r.max() / r.min() - 1) for r in ratios)
        routes = float(np.max(np.abs(np.asarray(series["opening_ratio"]) / np.asarray(series["energy_ratio"]) - 1)))
        sc_ = out["step_check"]
        g = growth(p)
        g2 = growth(p, method="LSODA")
        kmat = float(p["k_mat_MPa_sqrt_m"]) * MPA_SQRT_M
        checks = [
            check("newman_raju", "max |K (FE energy route, front average) / Newman-Raju - 1| over the crack shapes "
                  "(Newman-Raju's stated accuracy 5 %)", float(np.max(np.abs(np.asarray(series["energy_ratio"]) - 1))),
                  tol["newman_raju_rel_tol"]),
            check("profile_shape", f"max over shapes of (max / min - 1) of K (crack opening) / Newman-Raju for phi >= "
                  f"{tol['profile_from_deg']} deg: the shape of K along the front", shape, tol["profile_rel_tol"]),
            check("k_routes", "max |front-average K, crack opening / energy - 1| over the shapes", routes,
                  tol["routes_rel_tol"]),
            check("equilibrium", "max |ligament reaction + applied load| / applied load",
                  max(r["equilibrium"] for r in rows), tol["equilibrium_rel_tol"]),
            check("load_area", "max |sum of nodal loads / (sigma x loaded area) - 1|", max(r["load_area"] for r in rows),
                  tol["equilibrium_rel_tol"]),
            check("energy_step", f"|K (energy, eps) / K (eps / 2) - 1| at a = {sc_['a_mm']:g} mm (step and mesh noise)",
                  abs(np.sqrt(sc_["dU_deps_eps"] / sc_["dU_deps_half_eps"]) - 1), tol["energy_step_rel_tol"]),
            check("life_integral", "|life by DOP853 - by LSODA| / DOP853", abs(g["life"] - g2["life"]) / g["life"],
                  tol["integral_rel_tol"]),
            check("nr_range", "largest a/c on the path (Newman-Raju's equations used here hold for a/c <= 1)",
                  g["max_a_over_c"], 1.0, kind="validity"),
            check("no_fracture_before_end", "max K at the end depth / Kmat (below 1: the crack reaches 0.8 t before "
                  "fracture, so the life to 0.8 t is a lower bound)", max(g["K_deep_end"], g["K_surf_end"]) / kmat, 1.0,
                  kind="validity"),
        ]
        figure(pdir / "response.png", out, series, p, g, title=point["label"])
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "front_element_rel":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: float(pt["parameters"]["front_element_rel"]))
        if len(done) < 3:
            return [check("front_mesh_gci", "needs >= 3 completed front sizes", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(float(pt["parameters"]["front_element_rel"]) for pt in fine)
        checks, detail = [], {"levels_used": [pt["label"] for pt in fine]}
        for metric in ("K_a0_MPa_sqrt_m", "energy_ratio_min", "growth_life_fe_cycles"):
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine), design_order=2,
                                           noise_floor=float(tol.get("mesh_noise_rel", 1e-5)))
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


def figure(path, out, series, p, g, *, title):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2, _style, plt

    st = np.asarray(out["stations_deg"])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
    fig.patch.set_facecolor(SURFACE)
    for k, row in enumerate(out["rows"]):
        lab = f"a {row['a_mm']:g}, c {row['c_mm']:g} mm"
        a1.plot(st, np.asarray(row["K_nr"]) / MPA_SQRT_M, color=TEXT_2 if k % 2 else TEXT, lw=1.0,
                label="Newman-Raju" if k == 0 else None)
        a1.plot(st, np.asarray(row["K_fe"]) / MPA_SQRT_M, "o", color=SERIES_1, ms=3,
                label="FE, crack opening" if k == 0 else None)
        a1.annotate(lab, (90, row["K_nr"][-1] / MPA_SQRT_M), fontsize=7, color=TEXT_2, ha="right", va="bottom")
    a1.set_xlabel("angle along the front, phi (deg; 0 = surface, 90 = deepest)")
    a1.set_ylabel("K at maximum load (MPa sqrt m)")
    a1.legend(frameon=False, fontsize=8)
    a = np.asarray(series["a_mm"])
    a2.plot(a, 100 * (np.asarray(series["energy_ratio"]) - 1), "o-", color=SERIES_1, ms=5, label="energy route (average)")
    a2.plot(a, 100 * (np.asarray(series["opening_ratio"]) - 1), "x-", color=SERIES_2, ms=6, label="crack opening (average)")
    a2.axhspan(-5, 5, color=TEXT_2, alpha=0.15, label="Newman-Raju's stated accuracy")
    a2.set_xlabel("crack depth a (mm)")
    a2.set_ylabel("FE / Newman-Raju - 1 (%)")
    a2.legend(frameon=False, fontsize=8)
    for ax in (a1, a2):
        _style(ax)
    fig.suptitle(f"{title}: life from a = {float(p['initial_depth_mm']):g} mm to {g['a_end']:.1f} mm "
                 f"{g['life']:,.0f} cycles (Newman-Raju)", fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = SurfaceCrackStudy()

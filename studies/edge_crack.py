"""Study F: an edge-cracked steel plate in cyclic tension: stress intensity, critical crack, fatigue crack growth life.

Model:     gmsh_ccx_edge_crack (models/fea/edge_crack.py): Gmsh half model on the crack plane, 6-node triangles refined
           at the tip, CalculiX plane strain. Each point solves a list of crack lengths (and two neighbours of each for
           the energy route), builds K(a), finds the critical crack (toughness or net-section yield) and integrates the
           BS 7910 / IIW crack growth law from the detectable crack to it
Reference: Tada's finite-width edge-crack solution (0.5 % for a/W <= 0.6); the two K routes (energy release rate and
           crack opening) against each other; global equilibrium; the life integral by two quadratures
Run-level: GCI on the requirement metrics and the critical crack when the sweep is the tip element size
"""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from scipy.integrate import quad, simpson
from scipy.interpolate import CubicSpline
from scipy.optimize import brentq

from harness.backend_base import Backend, failed
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study

WRITER = "models/fea/edge_crack.py"
PARAMS = ("width_mm", "half_height_mm", "thickness_mm", "sigma_max_MPa", "stress_ratio", "youngs_modulus_MPa",
          "poisson_ratio", "yield_strength_MPa", "k_mat_MPa_sqrt_m", "paris_C", "paris_m", "dK_threshold",
          "initial_crack_mm", "tip_element_size_mm", "far_element_size_mm")
MPA_SQRT_M = 31.6227766  # N/mm^1.5 per MPa sqrt(m)


def _writer(path: Path):
    spec = importlib.util.spec_from_file_location("edge_crack_writer", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class GmshCalculiXEdgeCrack(Backend):
    sources = (WRITER,)

    def __init__(self):
        from studies.cantilever import find_freecadcmd

        bin_dir = find_freecadcmd().parent
        self.gmsh, self.ccx = bin_dir / "gmsh.exe", bin_dir / "ccx.exe"
        for exe in (self.gmsh, self.ccx):
            if not exe.exists():
                raise RuntimeError(f"{exe.name} not found next to freecadcmd")
        self.ec = None
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        self.ec = _writer(self.source_path(WRITER, source_dir))
        g = subprocess.run([str(self.gmsh), "--version"], capture_output=True, text=True, timeout=60)
        c = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"gmsh": (g.stdout + g.stderr).strip().splitlines()[-1],
                          "calculix": (c.stdout + c.stderr).strip().splitlines()[-1]}

    def _solve_one(self, work: Path, a: float, p: dict) -> dict:
        ec = self.ec
        W, H = float(p["width_mm"]), float(p["half_height_mm"])
        E, nu, sig = float(p["youngs_modulus_MPa"]), float(p["poisson_ratio"]), float(p["sigma_max_MPa"])
        work.mkdir(parents=True, exist_ok=True)
        ec.write_geo(work / "m.geo", a=a, W=W, H=H, h_tip=float(p["tip_element_size_mm"]),
                     h_far=float(p["far_element_size_mm"]))
        g = subprocess.run([str(self.gmsh), "m.geo", "-2", "-format", "inp", "-o", "mesh.inp"], cwd=work,
                           capture_output=True, text=True, timeout=600)
        if g.returncode != 0:
            raise RuntimeError(f"gmsh failed at a = {a}: {g.stdout[-300:]}")
        ec.to_plane_strain(work / "mesh.inp")
        info = ec.write_deck(work / "mesh.inp", work / "job.inp", a=a, W=W, H=H, sigma=sig, E=E, nu=nu)
        c = subprocess.run([str(self.ccx), "-i", "job"], cwd=work, capture_output=True, text=True, timeout=1800)
        (work / "ccx.log").write_text(c.stdout + c.stderr, encoding="utf-8")
        if c.returncode != 0 or "Job finished" not in c.stdout:
            raise RuntimeError(f"CalculiX failed at a = {a} (exit {c.returncode})")
        top, crack, rf = ec.read_node_print(work / "job.dat")
        P = info["applied_load_N_per_mm"]
        return {"U_half": ec.half_energy(top, info), "crack": crack, "info": info, "eq": abs(rf + P) / P,
                "nodes": info["nodes"]}

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="crack_"))
        p = params
        E, nu = float(p["youngs_modulus_MPa"]), float(p["poisson_ratio"])
        h = float(p["tip_element_size_mm"])
        # energy step: absolute (energy_step_mm) if given, else a fraction of a (energy_step_rel). r1 showed a
        # relative step trades mesh noise at short cracks for truncation error at long ones; an absolute step of a
        # few tip elements avoids both
        step = (lambda a: float(numerics["energy_step_mm"])) if "energy_step_mm" in numerics else (
            lambda a: float(numerics["energy_step_rel"]) * a)
        rows = []
        try:
            for a in [float(x) for x in numerics["crack_lengths_mm"]]:
                mid = self._solve_one(work / f"a{a:g}", a, p)
                da = step(a)
                lo = self._solve_one(work / f"a{a:g}_m", a - da, p)
                hi = self._solve_one(work / f"a{a:g}_p", a + da, p)
                G = 2 * (hi["U_half"] - lo["U_half"]) / (2 * da)            # per unit thickness, full crack
                k_en = float(np.sqrt(E * G / (1 - nu ** 2)))
                k_cod, n_cod = self.ec.k_from_opening(mid["crack"], mid["info"], a=a, E=E, nu=nu, r_min=2 * h,
                                                      r_max=max(0.1 * a, 6 * h))
                rows.append({"a_mm": a, "K_energy": k_en, "K_opening": k_cod, "opening_points": n_cod,
                             "K_tada": self.ec.tada_F(a / float(p["width_mm"])) * float(p["sigma_max_MPa"])
                             * np.sqrt(np.pi * a),
                             "equilibrium": max(mid["eq"], lo["eq"], hi["eq"]), "nodes": mid["nodes"]})
            # step check: the central difference again at one crack length with half the step
            a_chk = float(numerics["energy_step_check_mm"])
            da2 = step(a_chk) / 2
            lo2 = self._solve_one(work / "chk_m", a_chk - da2, p)
            hi2 = self._solve_one(work / "chk_p", a_chk + da2, p)
            G2 = 2 * (hi2["U_half"] - lo2["U_half"]) / (2 * da2)
            k_half = float(np.sqrt(E * G2 / (1 - nu ** 2)))
            k_full = next(r["K_energy"] for r in rows if abs(r["a_mm"] - a_chk) < 1e-9)
        except (RuntimeError, StopIteration) as e:
            return failed(f"{type(e).__name__}: {e}") | {"cleanup": work}
        series = {k: np.array([r[k] for r in rows]) for k in ("a_mm", "K_energy", "K_opening", "K_tada")}
        return {"success": True, "message": f"{len(rows)} crack lengths x 3 solves, tip {h} mm", "nfev": 3 * len(rows),
                "series": series, "outputs": {"rows": rows, "step_check": {"a_mm": a_chk, "K_eps": k_full,
                                                                     "K_half_eps": k_half}}, "files": {}, "cleanup": work}

    def tool_versions(self):
        return self._versions


def growth(params, a_mm, K_per_sigma):
    """Critical crack and growth life from the K(a) curve (K at sigma_max, N/mm^1.5). Returns a dict."""
    p = params
    W, smax, R = float(p["width_mm"]), float(p["sigma_max_MPa"]), float(p["stress_ratio"])
    kmat = float(p["k_mat_MPa_sqrt_m"]) * MPA_SQRT_M
    C, m, th = float(p["paris_C"]), float(p["paris_m"]), float(p["dK_threshold"])
    a0 = float(p["initial_crack_mm"])
    F = np.asarray(K_per_sigma) / (smax * np.sqrt(np.pi * np.asarray(a_mm)))   # geometry factor from the model
    spl = CubicSpline(a_mm, F)
    Kmax = lambda a: float(spl(a)) * smax * np.sqrt(np.pi * a)  # noqa: E731
    a_y = W * (1 - smax / float(p["yield_strength_MPa"]))         # net-section yield, uniform tension
    hi = min(a_y, float(a_mm[-1]))
    a_k = brentq(lambda a: Kmax(a) - kmat, a0, hi) if Kmax(hi) > kmat else float("inf")
    a_c = min(a_k, a_y)
    if a_c > float(a_mm[-1]):
        raise ValueError(f"critical crack {a_c:.1f} mm beyond the sampled K(a) ({a_mm[-1]} mm)")
    rate = lambda a: C * max((1 - R) * Kmax(a), 0.0) ** m if (1 - R) * Kmax(a) > th else 0.0  # noqa: E731
    life_q = quad(lambda a: 1 / rate(a), a0, a_c, limit=400)[0]
    xs = np.linspace(a0, a_c, 4001)
    life_s = float(simpson([1 / rate(x) for x in xs], x=xs))
    return {"K_a0": Kmax(a0), "a_toughness_mm": a_k, "a_yield_mm": a_y, "a_crit_mm": a_c,
            "governs": "toughness" if a_k <= a_y else "net-section yield", "life_quad": life_q, "life_simpson": life_s,
            "dK_a0": (1 - R) * Kmax(a0)}


class EdgeCrackStudy(Study):
    name = "edge_crack"
    models = {"gmsh_ccx_edge_crack": GmshCalculiXEdgeCrack}
    metrics = frozenset({"K_a0_MPa_sqrt_m", "crit_crack_mm", "growth_life_cycles", "inspection_interval_cycles",
                         "growth_life_tada_cycles"})
    param_names = PARAMS
    series_file = "k_of_a.csv"
    compare_description = "max relative difference of K(a) by the energy route"

    def derive(self, params):
        if not 0 < float(params["stress_ratio"]) < 1:
            raise ValueError("stress ratio must be between 0 and 1")
        return {}

    def compute_metrics(self, series, params, case, outputs=None):
        a = np.asarray(series["a_mm"])
        g = growth(params, a, np.asarray(series["K_energy"]))
        gt = growth(params, a, np.asarray(series["K_tada"]))
        return {"K_a0_MPa_sqrt_m": g["K_a0"] / MPA_SQRT_M, "crit_crack_mm": g["a_crit_mm"],
                "growth_life_cycles": g["life_quad"], "inspection_interval_cycles": g["life_quad"] / 2,
                "growth_life_tada_cycles": gt["life_quad"]}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        p, rows = point["parameters"], point["solver_outputs"]["rows"]
        W = float(p["width_mm"])
        tada = max(abs(r["K_energy"] / r["K_tada"] - 1) for r in rows if r["a_mm"] / W <= 0.6)
        routes = max(abs(r["K_opening"] / r["K_energy"] - 1) for r in rows)
        sc = point["solver_outputs"]["step_check"]
        g = growth(p, np.asarray(series["a_mm"]), np.asarray(series["K_energy"]))
        checks = [
            check("tada", "max |K (energy route) / Tada - 1| for a/W <= 0.6 (Tada's own accuracy 0.5 %)", tada,
                  tol["tada_rel_tol"]),
            check("k_routes", "max |K (crack opening) / K (energy) - 1| over the crack lengths", routes,
                  tol["routes_rel_tol"]),
            check("equilibrium", "max |ligament reaction + applied load| / applied load", max(r["equilibrium"]
                                                                                             for r in rows),
                  tol["equilibrium_rel_tol"]),
            check("energy_step", f"|K (energy, step eps) / K (step eps / 2) - 1| at a = {sc['a_mm']:g} mm (the central "
                  "difference's step and the mesh noise in U together)", abs(sc["K_eps"] / sc["K_half_eps"] - 1),
                  tol["energy_step_rel_tol"]),
            check("life_integral", "|life by adaptive quadrature - by Simpson on 4000 steps| / quadrature",
                  abs(g["life_quad"] - g["life_simpson"]) / g["life_quad"], tol["integral_rel_tol"]),
            check("crack_range", "critical crack / largest sampled crack (below 1: K(a) is sampled past the critical "
                  "crack)", g["a_crit_mm"] / float(series["a_mm"][-1]), 1.0, kind="validity"),
        ]
        crack_figure(pdir / "response.png", series, g, p, title=point["label"])
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "tip_element_size_mm":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: float(pt["parameters"]["tip_element_size_mm"]))
        if len(done) < 3:
            return [check("tip_mesh_gci", "needs >= 3 completed tip sizes", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(float(pt["parameters"]["tip_element_size_mm"]) for pt in fine)
        checks, detail = [], {"levels_used": [pt["label"] for pt in fine]}
        for metric in ("K_a0_MPa_sqrt_m", "crit_crack_mm", "growth_life_cycles"):
            nf = tol.get("mesh_noise_rel", 1e-5)          # one value, or a table per metric (measured noise)
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine), design_order=2,
                                           noise_floor=float(nf[metric] if isinstance(nf, dict) else nf))
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


def crack_figure(path, series, g, p, *, title):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2, _style, plt

    a = np.asarray(series["a_mm"])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
    fig.patch.set_facecolor(SURFACE)
    a1.plot(a, np.asarray(series["K_tada"]) / MPA_SQRT_M, color=TEXT, lw=1.0, label="Tada (handbook)")
    a1.plot(a, np.asarray(series["K_energy"]) / MPA_SQRT_M, "o", color=SERIES_1, ms=5, label="FE, energy release")
    a1.plot(a, np.asarray(series["K_opening"]) / MPA_SQRT_M, "x", color=SERIES_2, ms=6, label="FE, crack opening")
    a1.axhline(float(p["k_mat_MPa_sqrt_m"]), color=TEXT_2, ls="--", lw=0.8, label="K_mat")
    a1.axvline(g["a_crit_mm"], color=TEXT_2, ls=":", lw=0.8)
    a1.set_xlabel("crack length a (mm)")
    a1.set_ylabel("K at maximum load (MPa sqrt m)")
    a1.legend(frameon=False, fontsize=8)
    rel = np.asarray(series["K_energy"]) / np.asarray(series["K_tada"]) - 1
    a2.plot(a, 100 * rel, "o-", color=SERIES_1, ms=4, label="energy route")
    a2.plot(a, 100 * (np.asarray(series["K_opening"]) / np.asarray(series["K_tada"]) - 1), "x-", color=SERIES_2,
            ms=5, label="crack-opening route")
    a2.axhspan(-0.5, 0.5, color=TEXT_2, alpha=0.15, label="Tada's stated accuracy")
    a2.set_xlabel("crack length a (mm)")
    a2.set_ylabel("FE / Tada - 1 (%)")
    a2.legend(frameon=False, fontsize=8)
    for ax in (a1, a2):
        _style(ax)
    fig.suptitle(f"{title}: critical crack {g['a_crit_mm']:.1f} mm ({g['governs']}), life from "
                 f"{float(p['initial_crack_mm']):g} mm {g['life_quad']:,.0f} cycles", fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = EdgeCrackStudy()

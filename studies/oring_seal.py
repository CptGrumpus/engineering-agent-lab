"""Study 12: O-ring face seal squeezed by a cover, CalculiX axisymmetric hyperelastic contact.

Model:     ccx_oring (models/fea/oring_ccx.py): the upper half of the ring's cross-section (mid-plane symmetry),
           neo-Hookean (E from Shore A by Gent's relation), a steel cover moved down by half the squeeze, the groove's
           walls as steel blocks (or none: a laterally unrestrained ring, Lindley's case), node-to-surface penalty
           contact; CAX8R / CAX6 from Gmsh.
Metrics:   squeeze (from the inputs), closing force per mm of seal, peak contact pressure on the cover (the nodal
           penalty pressure, k x overclosure on the 2D nodes, averaged over adjacent node pairs: node-to-surface
           contact on quadratic faces alternates between corner and mid-side nodes), groove fill from the deformed
           area.
Reference: volume conservation (J about 1), the contact-pressure integral against the cover's reaction, vertical
           equilibrium (cover against symmetry plane), penalty penetration; where the case asks: Lindley's relation
           and Parker's measured band (unrestrained ring), Hertz line contact (small squeeze, at the FE's own force).
Run-level: GCI on every requirement metric when the sweep is the contact element size.
"""

from __future__ import annotations

import importlib.util
import math
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness.backend_base import Backend, failed
from harness.calculix import read_dat_total_forces, read_frd
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study
from validation import oring as ref

WRITER = "models/fea/oring_ccx.py"
PARAMS = ("cross_section_mm", "ring_inner_diameter_mm", "groove_depth_mm", "groove_width_mm",
          "groove_outer_diameter_mm", "groove_walls", "shore_a", "bulk_to_shear", "contact_element_size_mm",
          "far_element_size_mm", "penalty_factor")


def _load_writer(path: Path):
    spec = importlib.util.spec_from_file_location("oring_ccx_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def model_params(params: dict) -> dict:
    """The model's inputs from the physical ones: squeeze, modulus, ring and groove radii."""
    d, h = float(params["cross_section_mm"]), float(params["groove_depth_mm"])
    p = {"cross_section_mm": d, "mean_radius_mm": float(params["ring_inner_diameter_mm"]) / 2 + d / 2,
         "squeeze": (d - h) / d, "youngs_modulus_MPa": ref.gent_youngs_modulus_MPa(float(params["shore_a"])),
         **{k: float(params[k]) for k in ("bulk_to_shear", "contact_element_size_mm", "far_element_size_mm",
                                          "penalty_factor")}}
    for k in ("contact_tension_MPa", "first_increment", "max_increment", "max_increments", "refine_distance_mm"):
        if k in params:
            p[k] = params[k]
    if int(params["groove_walls"]):
        p["groove_width_mm"] = float(params["groove_width_mm"])
        p["groove_inner_radius_mm"] = float(params["groove_outer_diameter_mm"]) / 2 - p["groove_width_mm"]
    return p


class CalculiXORing(Backend):
    sources = (WRITER,)

    def __init__(self):
        from studies.fin import find_ccx

        self.ccx = find_ccx()
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        import gmsh

        self.writer = _load_writer(self.source_path(WRITER, source_dir))
        c = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"CalculiX": (c.stdout.strip().splitlines() or ["?"])[-1], "gmsh": gmsh.__version__}

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="oring_"))
        keep = ("job.inp", "job.dat", "job.sta", "ccx.log")

        def files():
            return {n: work / n for n in keep if (work / n).exists()}

        def fail(msg):
            res = failed(msg)
            res.update(files=files(), cleanup=work)
            return res

        W = self.writer
        p = model_params(params)
        try:
            mesh = W.build_mesh(p)
            info = W.write_deck(mesh, p, work / "job.inp")
            c = subprocess.run([str(self.ccx), "-i", "job"], cwd=work, capture_output=True, text=True,
                               timeout=float(numerics.get("solver_timeout_s", 7200)))
            (work / "ccx.log").write_text(c.stdout + c.stderr, encoding="utf-8")
            if c.returncode != 0 or not (work / "job.frd").exists():
                return fail(f"CalculiX failed (exit {c.returncode}); see ccx.log")
            hist = W.read_force_history(work / "job.dat")
            if not hist or abs(hist[-1][0] - 1.0) > 1e-6:
                return fail(f"CalculiX stopped at step time {hist[-1][0] if hist else 0} of 1")
            fr = read_frd(work / "job.frd")
            tot = read_dat_total_forces(work / "job.dat")
        except Exception as e:  # mesh, deck or parse errors are evidence too
            return fail(f"{type(e).__name__}: {e}")

        nodes, a, Rc = mesh["nodes"], mesh["a"], mesh["Rc"]
        U = fr["DISP"]
        ui = {int(n): k for k, n in enumerate(U["ids"])}
        D = {n: (x + U["D1"][ui[n]], y + U["D2"][ui[n]]) for n, (x, y) in nodes.items() if n in ui}
        seg_to_line = 1.0 / W.SEGMENT / (2 * math.pi * Rc)          # 2-degree reaction -> N per mm of seal
        F = abs(tot["CTOP"][1]) * seg_to_line
        # penalty pressure from the overclosure against the deformed cover bottom (CalculiX's own law, on 2D nodes)
        k_pen = info["penalty_MPa_per_mm"]
        cov = sorted((D[n][0], D[n][1]) for _, _, c in mesh["elems"]["COVER"] for n in c if abs(nodes[n][1] - a) < 1e-9)
        cr, cz = np.array([q[0] for q in cov]), np.array([q[1] for q in cov])
        pres = lambda n: k_pen * max(0.0, D[n][1] - float(np.interp(D[n][0], cr, cz)))  # noqa: E731
        # nodal penalty pressure on the arc's nodes, sorted by radius; CalculiX's node-to-surface contact lumps about
        # equal areas per slave node (the trapezoid rule over the nodes reproduced the reaction to 1.6 % in the
        # prototype, Simpson's (1/6, 2/3, 1/6) weights did not: +11 %), which also makes corner and mid-side nodes
        # alternate; the reported pressure is the two-node moving average along the surface
        arc_nodes = sorted({n for e in W.arc_edges(mesh) for n in e}, key=lambda n: D[n][0])
        r_n = np.array([D[n][0] for n in arc_nodes])
        p_n = np.array([pres(n) for n in arc_nodes])
        F_int = float(np.trapezoid(p_n * r_n, r_n)) / Rc
        r_e, p_e = 0.5 * (r_n[1:] + r_n[:-1]), 0.5 * (p_n[1:] + p_n[:-1])
        on = p_e > 0
        ring_nodes = sorted({v for _, _, c in mesh["elems"]["RING"] for v in c})
        rs = np.array([D[n][0] for n in ring_nodes])
        V0 = W.ring_volume_mm3(nodes, mesh["elems"]["RING"])
        V1 = W.ring_volume_mm3(D, mesh["elems"]["RING"])
        area = sum(abs(_poly_area(np.array([D[q] for q in _ring_poly(W, t, c)]))) for _, t, c in mesh["elems"]["RING"])
        t_h = np.array([q[0] for q in hist])
        F_h = np.array([abs(q[1]) for q in hist]) * seg_to_line
        overclosure = max((D[n][1] - float(np.interp(D[n][0], cr, cz)) for n in ring_nodes), default=0.0)
        series = {"r_mm": r_e, "contact_pressure_MPa": p_e}
        outputs = {**info, "force_per_length_N_per_mm": F, "contact_integral_N_per_mm": F_int,
                   "reaction_sym_N_per_mm": abs(tot["SYM"][1]) * seg_to_line,
                   "peak_contact_pressure_MPa": float(p_e.max()) if len(p_e) else 0.0,
                   "contact_width_mm": float(r_e[on].max() - r_e[on].min()) if on.sum() > 1 else 0.0,
                   "volume_ratio": V1 / V0, "deformed_half_area_mm2": float(area),
                   "ring_r_min_mm": float(rs.min()), "ring_r_max_mm": float(rs.max()),
                   "max_overclosure_mm": float(overclosure), "model": {k: v for k, v in p.items()},
                   "groove": mesh.get("walls"),
                   "force_history": {"squeeze": (t_h * p["squeeze"]).tolist(), "force_N_per_mm": F_h.tolist()}}
        return {"success": True, "message": f"CalculiX: {info['nodes']} nodes, F' {F:.3f} N/mm", "nfev": None,
                "series": series, "outputs": outputs, "files": files(), "cleanup": work}

    def tool_versions(self):
        return self._versions


def _ring_poly(W, t, c):
    order = (0, 4, 1, 5, 2, 6, 3, 7) if t == "CAX8R" else (0, 3, 1, 4, 2, 5)
    return [c[i] for i in order]


def _poly_area(P):
    x, y = P[:, 0], P[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


class ORingSealStudy(Study):
    name = "oring_seal"
    models = {"ccx_oring": CalculiXORing}
    metrics = frozenset({"squeeze_pct", "force_per_length_N_per_mm", "peak_contact_pressure_MPa",
                         "groove_fill_pct", "contact_width_mm"})
    param_names = PARAMS
    series_file = "contact_profile.csv"
    compare_description = "max relative difference in contact pressure"

    def derive(self, params):
        d, h, w = (float(params[k]) for k in ("cross_section_mm", "groove_depth_mm", "groove_width_mm"))
        if not (0 < h < d) or w <= 0:
            raise ValueError("groove depth between 0 and the cross-section; positive width")
        return {"squeeze": (d - h) / d, "youngs_modulus_MPa": ref.gent_youngs_modulus_MPa(float(params["shore_a"])),
                "groove_fill_hand": ref.groove_fill(d, h, w)}

    def compute_metrics(self, series, params, case, outputs=None):
        d, h, w = (float(params[k]) for k in ("cross_section_mm", "groove_depth_mm", "groove_width_mm"))
        return {"squeeze_pct": 100 * (d - h) / d,
                "force_per_length_N_per_mm": outputs["force_per_length_N_per_mm"],
                "peak_contact_pressure_MPa": outputs["peak_contact_pressure_MPa"],
                "groove_fill_pct": 100 * outputs["deformed_half_area_mm2"] / (w * h / 2),
                "contact_width_mm": outputs["contact_width_mm"]}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        prm, m, out = point["parameters"], point["metrics"], point["solver_outputs"]
        F = m["force_per_length_N_per_mm"]
        mp = out["model"]
        travel = out["cover_travel_mm"]
        checks = [
            check("volume_conservation", "|deformed / initial ring volume - 1| (near-incompressible: J about 1)",
                  abs(out["volume_ratio"] - 1), tol["volume_rel_tol"]),
            check("contact_force_balance", "|integral of the contact pressure over the cover / cover reaction - 1|",
                  abs(out["contact_integral_N_per_mm"] / F - 1), tol["force_balance_rel_tol"]),
            check("equilibrium", "|cover reaction - symmetry-plane reaction| / cover reaction (walls frictionless)",
                  abs(F - out["reaction_sym_N_per_mm"]) / F, tol["equilibrium_rel_tol"]),
            check("penalty_penetration", "max overclosure of the ring into the cover / cover travel",
                  out["max_overclosure_mm"] / travel, tol["penetration_max_fraction"]),
        ]
        g = out.get("groove")
        if g:   # a free ring grows in diameter, so its section shrinks: the hand fill holds only in a groove
            checks.append(check("groove_fill_hand", "|groove fill from the deformed area - hand fill (volume "
                                "conserved, ring against the outer wall)| / hand",
                                abs(m["groove_fill_pct"] / 100 / ref.groove_fill(float(prm["cross_section_mm"]),
                                    float(prm["groove_depth_mm"]), float(prm["groove_width_mm"])) - 1),
                                tol["fill_rel_tol"]))
            checks.append(check("in_groove", "ring beyond the groove walls (mm, inner or outer; penalty overclosure "
                                "allowed up to the tolerance; validity)",
                                max(0.0, g["r_in"] - out["ring_r_min_mm"], out["ring_r_max_mm"] - g["r_out"]),
                                tol["in_groove_tol_mm"], kind="validity"))
        c = mp["squeeze"]
        E = mp["youngs_modulus_MPa"]
        d = mp["cross_section_mm"]
        if "lindley_rel_tol" in tol and not g:
            hist = out["force_history"]
            for cs in (0.10, 0.20, 0.30):
                if cs <= c + 1e-9:
                    Ff = float(np.interp(cs, hist["squeeze"], hist["force_N_per_mm"]))
                    Fl = ref.lindley_force_per_length_N_per_mm(d, E, cs)
                    checks.append(check(f"lindley_{int(round(100 * cs))}pct",
                                        f"|FE force - Lindley| / Lindley at {100 * cs:.0f} % squeeze (unrestrained ring)",
                                        abs(Ff - Fl) / Fl, tol["lindley_rel_tol"]))
                    if abs(float(prm["shore_a"]) - 70) < 1e-9:
                        lo, hi = ref.PARKER_70A_0139_N_PER_MM[int(round(100 * cs))]
                        checks.append(check(f"parker_band_{int(round(100 * cs))}pct",
                                            f"FE force outside Parker's 70 Shore A band at {100 * cs:.0f} % "
                                            f"({lo:.3f}-{hi:.3f} N/mm; 0 = inside)",
                                            max(0.0, lo - Ff, Ff - hi), 0.0))
        if "hertz_rel_tol" in tol and not g:
            b_ref, p_ref = ref.hertz_line(F, d / 2, E)
            checks.append(check("hertz_peak_pressure", "|peak contact pressure - Hertz p0 at the FE's force| / p0",
                                abs(m["peak_contact_pressure_MPa"] - p_ref) / p_ref, tol["hertz_rel_tol"]))
            checks.append(check("hertz_contact_width", "|contact width - Hertz 2b at the FE's force| / 2b",
                                abs(m["contact_width_mm"] - 2 * b_ref) / (2 * b_ref), tol["hertz_rel_tol"]))
        oring_figure(pdir / "response.png", series, out, point["label"])
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
        for metric in sorted({r["metric"] for r in case["requirements"]} - {"squeeze_pct"}):
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine))
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


def oring_figure(path, series, out, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from harness.plotting import GRID, SERIES_1, SERIES_2, SURFACE, TEXT

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2), facecolor=SURFACE)
    Rc = out["model"]["mean_radius_mm"]
    ax1.plot(series["r_mm"] - Rc, series["contact_pressure_MPa"], "o-", ms=3, color=SERIES_1)
    ax1.set_xlabel("radius from the ring's centre line (mm)", color=TEXT)
    ax1.set_ylabel("contact pressure on the cover (MPa)", color=TEXT)
    h = out["force_history"]
    ax2.plot(100 * np.array(h["squeeze"]), h["force_N_per_mm"], color=SERIES_2, lw=2)
    ax2.set_xlabel("squeeze (%)", color=TEXT)
    ax2.set_ylabel("closing force per mm of seal (N/mm)", color=TEXT)
    for ax in (ax1, ax2):
        ax.set_facecolor(SURFACE)
        ax.grid(color=GRID, lw=0.5)
        ax.tick_params(colors=TEXT)
    fig.suptitle(title, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=110, facecolor=SURFACE)
    plt.close(fig)


STUDY = ORingSealStudy()

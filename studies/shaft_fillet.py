"""Machine-elements study: a gearbox shaft's shoulder fillet, Kt by CalculiX, fatigue and yield safety by Shigley.

Model:     ccx_shaft_fillet (models/fea/shaft_fillet_ccx.py): half of the stepped shaft (C3D10 from Gmsh), two linear
           load cases on one mesh: bending (symmetry on y = 0) and torsion (antisymmetry), the large end clamped, the
           exact beam tractions on the loaded end.
Metrics:   Kt in bending and Kts in torsion (peak nodal max principal stress and max shear stress on the fillet, on
           the plane y = 0 at x > 0 where the fine mesh is, over 32 M / (pi d^3) and 16 T / (pi d^3)); from them the
           fatigue safety (modified Goodman; ASME elliptic reported) and the first-cycle yield safety at the overload,
           by Shigley's method (validation/shaft_fatigue.py: Marin factors, Neuber notch sensitivity, von Mises
           alternating and mean stresses).
Reference: equilibrium (the clamp's reaction moment against the applied), the applied end load against M / 2, T / 2
           (half model), beam theory in the small section far from the fillet, the published Kt fits (Pilkey 2nd ed.),
           the peak off the plane (cos-corrected for bending) against the on-plane peak.
Run-level: GCI on Kt, Kts and every requirement metric when the sweep is the fillet element size; when the sweep is
           the fillet radius (or scenarios that size the step by d), the smallest radius (or d) meeting each requirement
           (interpolated) in the run detail.
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
from harness.study import Study
from validation import shaft_fatigue as ref

WRITER = "models/fea/shaft_fillet_ccx.py"
PARAMS = ("D_mm", "d_mm", "fillet_radius_mm", "small_length_mm", "large_length_mm", "bending_moment_Nm",
          "torque_Nm", "youngs_modulus_MPa", "poisson_ratio", "ultimate_MPa", "yield_MPa", "overload_factor",
          "element_size_fillet_mm", "element_size_far_mm", "refine_radius_mm", "refine_halfwidth_mm", "mesh_growth")


def _load_writer(path: Path):
    spec = importlib.util.spec_from_file_location("shaft_fillet_ccx_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _principal(S: dict, rows) -> np.ndarray:
    T = np.zeros((len(rows), 3, 3))
    T[:, 0, 0], T[:, 1, 1], T[:, 2, 2] = S["SXX"][rows], S["SYY"][rows], S["SZZ"][rows]
    T[:, 0, 1] = T[:, 1, 0] = S["SXY"][rows]
    T[:, 0, 2] = T[:, 2, 0] = S["SZX"][rows]
    T[:, 1, 2] = T[:, 2, 1] = S["SYZ"][rows]
    return np.linalg.eigvalsh(T)          # ascending


class CalculiXShaft(Backend):
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
        work = Path(tempfile.mkdtemp(prefix="shaft_"))
        keep = ("bending.inp", "torsion.inp", "bending.dat", "torsion.dat", "bending.sta", "torsion.sta", "ccx.log")

        def files():
            return {n: work / n for n in keep if (work / n).exists()}

        def fail(msg):
            res = failed(msg)
            res.update(files=files(), cleanup=work)
            return res

        W = self.writer
        p = dict(params)
        g = W.dims(p)
        d = g["d"]
        s_nom = 32 * float(p["bending_moment_Nm"]) * 1e3 / (math.pi * d ** 3)
        t_nom = 16 * float(p["torque_Nm"]) * 1e3 / (math.pi * d ** 3)
        out: dict = {"sigma_nom_MPa": s_nom, "tau_nom_MPa": t_nom}
        series: dict = {}
        log = []
        try:
            mesh = W.build_mesh(p, work / "mesh.inp")
            out["volume_mm3"] = mesh["volume_mm3"]
            for load in ("bending", "torsion"):
                info = W.write_deck(p, work / "mesh.inp", work / f"{load}.inp", load)
                c = subprocess.run([str(self.ccx), "-i", load], cwd=work, capture_output=True, text=True,
                                   timeout=float(numerics.get("solver_timeout_s", 3600)))
                log.append(c.stdout + c.stderr)
                if c.returncode != 0 or not (work / f"{load}.frd").exists():
                    (work / "ccx.log").write_text("\n".join(log), encoding="utf-8")
                    return fail(f"CalculiX {load} failed (exit {c.returncode}); see ccx.log")
                fr = read_frd(work / f"{load}.frd")
                rf = W.read_node_forces(work / f"{load}.dat")
                out[load] = self._evaluate(W, p, g, fr, rf, info, load, s_nom, t_nom, series)
            (work / "ccx.log").write_text("\n".join(log), encoding="utf-8")
        except Exception as e:  # mesh, deck or parse errors are evidence too
            return fail(f"{type(e).__name__}: {e}")
        out["nodes"] = out["bending"]["nodes"]
        n = max(len(v) for v in series.values())
        series = {k: np.pad(np.asarray(v, float), (0, n - len(v)), constant_values=np.nan) for k, v in series.items()}
        return {"success": True, "message": f"CalculiX: {out['nodes']} nodes, Kt {out['bending']['kt']:.4f}, "
                f"Kts {out['torsion']['kt']:.4f}", "nfev": None, "series": series, "outputs": out, "files": files(),
                "cleanup": work}

    @staticmethod
    def _evaluate(W, p, g, fr, rf, info, load, s_nom, t_nom, series) -> dict:
        S = fr["STRESS"]
        row = {int(n): k for k, n in enumerate(fr["nodes"])}
        X = fr["coords"][[row[int(n)] for n in S["ids"]]]
        ev = _principal(S, np.arange(len(S["ids"])))
        on_fillet = W.fillet_surface_mask(X, p) & (X[:, 0] > 0)
        plane = on_fillet & (np.abs(X[:, 1]) < 1e-6 * g["D"])
        band = on_fillet & (np.abs(X[:, 1]) > 0.5) & (np.abs(X[:, 1]) < 3.0)
        rho_xy = np.hypot(X[:, 0], X[:, 1])
        cth = np.divide(X[:, 0], rho_xy, out=np.ones_like(rho_xy), where=rho_xy > 0)   # nodes on the axis: unused
        if load == "bending":
            v, nom = ev[:, 2], s_nom
            v_off = (ev[:, 2] / cth)[band]                     # sigma ~ cos(theta) around the shaft
        else:
            v, nom = (ev[:, 2] - ev[:, 0]) / 2, t_nom
            v_off = v[band]                                     # axisymmetric
        if not plane.any():
            raise RuntimeError("no fillet nodes on the plane y = 0")
        k = int(np.flatnonzero(plane)[np.argmax(v[plane])])
        ang = W.fillet_angle_deg(X, p)
        order = np.flatnonzero(plane)[np.argsort(ang[plane])]
        series[f"{load}_angle_deg"] = ang[order]
        series[f"{load}_stress_over_nominal"] = v[order] / nom
        # beam theory in the small section (between 30 and 70 % of its length) on the surface in the plane y = 0
        rho = np.hypot(X[:, 0], X[:, 1])
        mid = ((np.abs(rho - g["d"] / 2) < 1e-4 * g["d"]) & (np.abs(X[:, 1]) < 1e-6 * g["D"])
               & (X[:, 2] > 0.3 * g["zs"]) & (X[:, 2] < 0.7 * g["zs"]))
        if load == "bending":
            beam = S["SZZ"][mid] / (s_nom * X[mid, 0] / (g["d"] / 2))
        else:
            tau = np.hypot(S["SZX"][mid], S["SYZ"][mid])
            beam = tau / (t_nom * rho[mid] / (g["d"] / 2))
        # equilibrium: the clamp's reaction moment about the loaded axis (y for bending, z for torsion)
        ids = np.array(list(rf))
        R = np.array([rf[n] for n in ids])
        P = fr["coords"][[row[int(n)] for n in ids]]
        Mr = np.cross(P, R).sum(axis=0)
        axis = 1 if load == "bending" else 2
        target = (float(p["bending_moment_Nm"]) if load == "bending" else float(p["torque_Nm"])) * 1e3 / 2
        applied = info["applied_moment_Nmm"][axis]
        return {"kt": float(v[k] / nom), "peak_angle_deg": float(ang[k]), "peak_xyz": X[k].tolist(),
                "kt_off_plane": float(v_off.max() / nom) if len(v_off) else float("nan"),
                "off_plane_nodes": int(len(v_off)), "plane_nodes": int(plane.sum()),
                "beam_ratio_min": float(beam.min()) if len(beam) else float("nan"),
                "beam_ratio_max": float(beam.max()) if len(beam) else float("nan"), "beam_nodes": int(len(beam)),
                "applied_moment_Nmm": float(applied), "target_moment_Nmm": target,
                "reaction_moment_Nmm": float(-Mr[axis]), "nodes": info["nodes"], "elements": info["elements"]}

    def tool_versions(self):
        return self._versions


def assessment(params: dict, kt_b: float, kt_t: float, edition: str = "shigley11") -> dict:
    f = lambda k: float(params[k])  # noqa: E731
    return ref.assess(f("D_mm"), f("d_mm"), f("fillet_radius_mm"), f("bending_moment_Nm"), f("torque_Nm"),
                      f("ultimate_MPa"), f("yield_MPa"), kt_b=kt_b, kt_t=kt_t, edition=edition,
                      overload=f("overload_factor"))


class ShaftFilletStudy(Study):
    name = "shaft_fillet"
    models = {"ccx_shaft_fillet": CalculiXShaft}
    metrics = frozenset({"kt_bending", "kt_torsion", "fatigue_safety", "fatigue_safety_elliptic", "static_safety"})
    param_names = PARAMS
    series_file = "fillet_stress.csv"
    compare_description = "max relative difference in the fillet stress profiles"

    def derive(self, params):
        f = lambda k: float(params[k])  # noqa: E731
        D, d, r = f("D_mm"), f("d_mm"), f("fillet_radius_mm")
        hand = ref.assess(D, d, r, f("bending_moment_Nm"), f("torque_Nm"), f("ultimate_MPa"), f("yield_MPa"),
                          overload=f("overload_factor"))
        return {"h_over_r": (D - d) / 2 / r, "r_over_d": r / d, "kt_bending_fit": hand["Kt"],
                "kt_torsion_fit": hand["Kts"], "fatigue_safety_hand": hand["n_goodman"],
                "static_safety_hand": hand["n_yield"]}

    def compute_metrics(self, series, params, case, outputs=None):
        kb, kt = outputs["bending"]["kt"], outputs["torsion"]["kt"]
        a = assessment(params, kb, kt)
        return {"kt_bending": kb, "kt_torsion": kt, "fatigue_safety": a["n_goodman"],
                "fatigue_safety_elliptic": a["n_elliptic"], "static_safety": a["n_yield"]}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        prm, m, out = point["parameters"], point["metrics"], point["solver_outputs"]
        f = lambda k: float(prm[k])  # noqa: E731
        D, d, r = f("D_mm"), f("d_mm"), f("fillet_radius_mm")
        checks = []
        for load in ("bending", "torsion"):
            o = out[load]
            checks.append(check(f"equilibrium_{load}", f"|clamp reaction moment - applied| / applied ({load})",
                                abs(o["reaction_moment_Nmm"] - o["applied_moment_Nmm"]) / abs(o["applied_moment_Nmm"]),
                                tol["equilibrium_rel_tol"]))
            checks.append(check(f"end_load_{load}", f"|applied end moment (consistent nodal forces) - half the "
                                f"{'moment' if load == 'bending' else 'torque'}| / half ({load}, half model; "
                                "magnitudes: the torsion tractions turn the end in the negative sense)",
                                abs(abs(o["applied_moment_Nmm"]) - o["target_moment_Nmm"]) / o["target_moment_Nmm"],
                                tol["end_load_rel_tol"]))
            checks.append(check(f"beam_theory_{load}", f"max |surface stress / beam theory - 1| in the small section "
                                f"(30-70 % of its length, plane y = 0, {o['beam_nodes']} nodes; {load})",
                                max(abs(o["beam_ratio_min"] - 1), abs(o["beam_ratio_max"] - 1)),
                                tol["beam_rel_tol"]))
            checks.append(check(f"peak_off_plane_{load}", f"|peak off the plane y = 0 (y 0.5-3 mm"
                                f"{', cos-corrected' if load == 'bending' else ''}) / peak on it - 1| ({load}; "
                                "nodal-stress scatter)", abs(o["kt_off_plane"] / o["kt"] - 1), tol["off_plane_rel_tol"]))
        hr = (D - d) / 2 / r
        try:
            kb_fit, kt_fit = ref.kt_bending(D, d, r), ref.kt_torsion(D, d, r)
            checks.append(check("kt_fit_bending", f"|FE Kt - Pilkey fit {kb_fit:.3f}| / fit (h/r = {hr:.2f})",
                                abs(m["kt_bending"] - kb_fit) / kb_fit, tol["kt_fit_rel_tol"]))
            checks.append(check("kt_fit_torsion", f"|FE Kts - Pilkey fit {kt_fit:.3f}| / fit (h/r = {hr:.2f})",
                                abs(m["kt_torsion"] - kt_fit) / kt_fit, tol["kt_fit_rel_tol"]))
        except ValueError:
            pass   # outside the fits' ranges: no published cross-check at this radius
        shaft_figure(pdir / "response.png", series, out, point["label"])
        return checks

    def verify_run_level(self, case, manifest, points):
        sweep = case.get("sweep", {}).get("parameter")
        tol = case["verification"]
        done = [pt for pt in manifest["points"] if pt["status"] == "completed"]
        if sweep == "element_size_fillet_mm":
            done = sorted(done, key=lambda pt: pt["parameters"]["element_size_fillet_mm"])
            if len(done) < 3:
                return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels", float("inf"), 0.0)], {}
            fine = done[:3]
            hs = tuple(float(pt["parameters"]["element_size_fillet_mm"]) for pt in fine)
            checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
            for metric in ("kt_bending", "kt_torsion", *sorted({r["metric"] for r in case["requirements"]})):
                nf = tol.get("mesh_noise_rel", 1e-5)      # one value, or a table per metric (measured: the noise case)
                u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine),
                                               noise_floor=float(nf[metric] if isinstance(nf, dict) else nf))
                detail[metric] = u
                checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                    f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
            return checks, detail
        if sweep in ("refine_radius_mm", "refine_halfwidth_mm"):
            # the noise case: perturbed meshes at one fillet element size; the peak-to-peak relative spread per metric
            # is the mesh noise floor for the mesh study
            detail = {"meshes": [pt["label"] for pt in done]}
            for metric in sorted(self.metrics):
                v = np.array([pt["metrics"][metric] for pt in done])
                detail[metric] = {"values": v.tolist(), "spread_rel": float((v.max() - v.min()) / abs(v.mean()))}
            return [], detail
        if sweep in ("fillet_radius_mm", "scenario"):
            key = "fillet_radius_mm" if sweep == "fillet_radius_mm" else "d_mm"   # scenarios: the step's size
            done = sorted(done, key=lambda pt: float(pt["parameters"][key]))
            r = np.array([float(pt["parameters"][key]) for pt in done])
            detail = {key: r.tolist()}
            for req in case["requirements"]:
                v = np.array([pt["metrics"][req["metric"]] for pt in done])
                detail[req["metric"]] = v.tolist()
                ok = v >= req["limit"] if req["operator"] in (">=", ">") else v <= req["limit"]
                if ok.all():
                    rmin = float(r[0])
                elif not ok.any():
                    rmin = None
                else:
                    i = int(np.flatnonzero(ok)[0])
                    rmin = float(np.interp(req["limit"], [v[i - 1], v[i]], [r[i - 1], r[i]])) if i else float(r[0])
                detail[f"min_{key}_{req['id']}"] = rmin
            return [], detail
        return [], {}


def shaft_figure(path, series, out, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from harness.plotting import GRID, SERIES_1, SERIES_2, SURFACE, TEXT

    fig, ax = plt.subplots(figsize=(7.5, 4.2), facecolor=SURFACE)
    for load, col, lab in (("bending", SERIES_1, "bending: max principal / (32 M / pi d^3)"),
                           ("torsion", SERIES_2, "torsion: max shear / (16 T / pi d^3)")):
        a = np.asarray(series[f"{load}_angle_deg"], float)
        s = np.asarray(series[f"{load}_stress_over_nominal"], float)
        ok = np.isfinite(a)
        ax.plot(a[ok], s[ok], "o-", ms=3, color=col, label=f"{lab}; peak {out[load]['kt']:.3f}")
    ax.set_xlabel("position on the fillet (deg; 0 = small cylinder, 90 = shoulder face)", color=TEXT)
    ax.set_ylabel("stress / nominal", color=TEXT)
    ax.set_facecolor(SURFACE)
    ax.grid(color=GRID, lw=0.5)
    ax.tick_params(colors=TEXT)
    ax.legend(fontsize=8)
    ax.set_title(title, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=110, facecolor=SURFACE)
    plt.close(fig)


STUDY = ShaftFilletStudy()

"""Study 10 part 2: the track roller in 3D with its ends, against study 10's plane-strain (long roller) answer.

Model:     ccx_roller_3d (models/fea/roller_3d.py): study 10's section extruded along a 30 mm roller on a 60 mm plate,
           the roller's profile (edge radius or logarithmic crown) as a micron drop; CalculiX penalty contact; one
           step per approach, the results interpolated to the target load between the two steps that bracket it.
Metrics:   at the target line load: the peak contact pressure anywhere and where it sits along the roller, the
           pressure at mid-length, their ratio, and the largest shear below the surface (Tresca) anywhere.
Reference: Hertz line contact at mid-length for the local line load there (the long-roller limit, exact for a
           section far from the ends); equilibrium (roller and plate reactions, and the integrated contact pressure);
           the load bracketed by the steps.
Run-level: GCI over contact_element_size_mm (layers along the roller refined with end_layer_mm in the same ratio).
"""

from __future__ import annotations

import importlib.util
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

from harness.backend_base import Backend, failed
from harness.calculix import read_frd
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study
from studies.strut_buckling import read_dat_blocks
from validation import hertz

WRITER = "models/fea/roller_3d.py"
SECTION = "models/fea/hertz_contact.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_W = _load(Path(__file__).resolve().parent.parent / WRITER, "roller_3d_repo")
PARAMS = _W.PARAMS + ("approach_factors",)


def frd_block_times(path: Path) -> list[float]:
    out = []
    for ln in Path(path).read_text(encoding="latin-1").splitlines():
        if ln.startswith("  100C"):
            m = re.match(r"\s+100C\S*\s+\d+\s+(\S+)", ln)
            if m:
                out.append(float(m.group(1)))
    return out


def tresca_max(S: dict, ids_sel: list[int]) -> tuple[float, int]:
    """Largest (s1 - s3) / 2 over the selected nodes, from the nodal stress components."""
    si = {int(n): k for k, n in enumerate(S["ids"])}
    rows = [si[n] for n in ids_sel if n in si]
    T = np.zeros((len(rows), 3, 3))
    for a, b, key in ((0, 0, "SXX"), (1, 1, "SYY"), (2, 2, "SZZ"), (0, 1, "SXY"), (1, 2, "SYZ"), (0, 2, "SZX")):
        v = np.asarray(S[key])[rows]
        T[:, a, b] = v
        T[:, b, a] = v
    ev = np.linalg.eigvalsh(T)
    tau = (ev[:, 2] - ev[:, 0]) / 2
    k = int(np.argmax(tau))
    return float(tau[k]), int(np.asarray(S["ids"])[rows][k])


def read_steps(W, params, work: Path, approaches) -> list[dict]:
    """Per completed step (a step's total time at its end is its number): the reactions, the contact pressure on the
    roller (peak and where, mid-length peak and line load, the peak along the roller) and the largest Tresca shear
    below the contact. Kept apart from the solve so it can be tested on a finished work directory."""
    ids, xyz, elems = W.read_mesh(work / "mesh.inp")
    frd = read_frd(work / "job.frd")
    times = frd_block_times(work / "job.frd")
    dat = read_dat_blocks(work / "job.dat")
    R = float(params["roller_radius_mm"])
    coord = dict(zip(ids.tolist(), xyz))
    roller = set(np.unique(elems["ROLLER"][:, 1:]).tolist())
    block = set(np.unique(elems["BLOCK"][:, 1:]).tolist())
    below = [n for n in block if coord[n][1] < 0 and coord[n][1] > -0.06 * R and abs(coord[n][0]) < 0.06 * R]
    steps = []
    blocks = list(zip(times, frd.get("blocks", [])))
    for k, a in enumerate(approaches, start=1):
        tops = [b for b in dat if b["set"] == "TOP" and round(b["time"]) == k and b["kind"] == "total"]
        bots = [b for b in dat if b["set"] == "BOTTOM" and round(b["time"]) == k and b["kind"] == "total"]
        C = [b for t, (nm, b) in blocks if nm == "CONTACT" and round(t) == k]
        S = [b for t, (nm, b) in blocks if nm == "STRESS" and round(t) == k]
        if not (tops and bots and C and S):
            break
        C, S = C[-1], S[-1]
        # CalculiX writes the contact block for every roller node (zeros inside): keep the surface arc, or the
        # line-load integral across x zigzags through the interior column at x = 0 (found on the trial's output)
        on = [(coord[int(n)], float(p)) for n, p in zip(C["ids"], C["CPRESS"]) if int(n) in roller
              and abs(math.hypot(coord[int(n)][0], coord[int(n)][1] - R) - R) < 1e-4 * R]
        P = np.array([[q[0], q[2], p] for q, p in on])            # x, z, pressure
        kmax = int(np.argmax(P[:, 2]))
        mid = P[np.abs(P[:, 1]) < 1e-9]
        mid = mid[np.argsort(mid[:, 0])]
        q0 = 2 * float(np.trapezoid(mid[:, 2], mid[:, 0]))          # both halves in x, per mm of length
        tau, tau_node = tresca_max(S, below)
        zs = sorted({round(float(z), 6) for z in P[:, 1]})
        # the contact pressure integrated over the quarter patch (trapezoid across x on each layer, then along z):
        # against the reaction it measures how far the nodal pressures smear the contact edge (12 % on the 0.08 mm
        # trial mesh), and it corrects the mid-length line load for the Hertz check
        lines = []
        for z in zs:
            Q = P[np.abs(P[:, 1] - z) < 1e-6]
            Q = Q[np.argsort(Q[:, 0])]
            lines.append(float(np.trapezoid(Q[:, 2], Q[:, 0])))
        integral = float(np.trapezoid(lines, zs))
        steps.append({"approach_mm": float(a), "F_top_N": float(tops[-1]["rows"][0][1]),
                      "F_bottom_N": float(bots[-1]["rows"][0][1]), "p_peak_MPa": float(P[kmax, 2]),
                      "p_peak_z_mm": float(P[kmax, 1]), "p_mid_MPa": float(mid[:, 2].max()),
                      "q_mid_N_per_mm": q0, "contact_integral_N": integral, "tau_max_MPa": tau,
                      "tau_max_xyz_mm": [float(v) for v in coord[tau_node]], "z_profile_mm": zs,
                      "p_along_z_MPa": [float(P[np.abs(P[:, 1] - z) < 1e-6, 2].max()) for z in zs]})
    return steps


class CalculiXRoller3D(Backend):
    sources = (WRITER, SECTION)

    def __init__(self):
        from studies.cantilever import find_freecadcmd

        bin_dir = find_freecadcmd().parent
        self.gmsh, self.ccx = bin_dir / "gmsh.exe", bin_dir / "ccx.exe"
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        _load(self.source_path(SECTION, source_dir), "models.fea.hertz_contact")
        self.W = _load(self.source_path(WRITER, source_dir), "roller_3d_saved")
        g = subprocess.run([str(self.gmsh), "--version"], capture_output=True, text=True, timeout=60)
        c = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"gmsh": (g.stdout + g.stderr).strip().splitlines()[-1],
                          "CalculiX": (c.stdout.strip().splitlines() or ["?"])[-1]}

    def solve(self, params, numerics, tolerance_scale=1.0):
        W = self.W
        work = Path(tempfile.mkdtemp(prefix="roller3d_"))
        keep = ("mesh.geo", "job.inp", "job.dat", "job.sta", "gmsh.log", "ccx.log")

        def files():
            return {n: work / n for n in keep if (work / n).exists()}

        try:
            W.write_geo(params, work / "mesh.geo")
            g = subprocess.run([str(self.gmsh), "mesh.geo", "-3", "-format", "inp", "-o", "mesh.inp"], cwd=work,
                               capture_output=True, text=True, timeout=1800)
            (work / "gmsh.log").write_text(g.stdout + g.stderr, encoding="utf-8")
            if g.returncode != 0 or not (work / "mesh.inp").exists() or "Error" in g.stdout + g.stderr:
                return failed(f"gmsh failed (exit {g.returncode})") | {"files": files(), "cleanup": work}
            a0 = float(W.opt(params, "approach_mm"))
            approaches = [a0 * float(f) for f in params["approach_factors"]]
            info = W.write_deck(params, work / "mesh.inp", work / "job.inp", approaches)
            th = str(int(numerics.get("threads", 6)))
            env = dict(os.environ, OMP_NUM_THREADS=th, CCX_NPROC_EQUATION_SOLVER=th)
            c = subprocess.run([str(self.ccx), "-i", "job"], cwd=work, capture_output=True, text=True, env=env,
                               timeout=float(numerics.get("solver_timeout_s", 21600)))
            (work / "ccx.log").write_text(c.stdout + c.stderr, encoding="utf-8")
            if c.returncode != 0 or not (work / "job.frd").exists():
                return failed(f"CalculiX failed (exit {c.returncode})") | {"files": files(), "cleanup": work}
            steps = read_steps(W, params, work, approaches)
        except Exception as e:  # noqa: BLE001
            return failed(f"{type(e).__name__}: {e}") | {"files": files(), "cleanup": work}

        if len(steps) < 2:
            return failed(f"only {len(steps)} steps completed") | {"files": files(), "cleanup": work}
        target = info["target_quarter_load_N"]
        F = np.array([abs(s["F_top_N"]) for s in steps])
        j = int(np.searchsorted(F, target))
        bracketed = 0 < j < len(F)
        j = min(max(j, 1), len(F) - 1)
        w = (target - F[j - 1]) / (F[j] - F[j - 1])
        interp = {k: float((1 - w) * steps[j - 1][k] + w * steps[j][k])
                  for k in ("approach_mm", "F_top_N", "F_bottom_N", "p_peak_MPa", "p_mid_MPa", "q_mid_N_per_mm",
                            "contact_integral_N",
                            "tau_max_MPa")}
        interp["p_peak_z_mm"] = steps[j]["p_peak_z_mm"]
        outputs = {**info, "steps": steps, "bracketed": bool(bracketed), "interp_weight": float(w),
                   "at_target": interp, "contact_reach_ok": True}
        zs = np.asarray(steps[j]["z_profile_mm"])
        pz = (1 - w) * np.asarray(steps[j - 1]["p_along_z_MPa"]) + w * np.asarray(steps[j]["p_along_z_MPa"]) \
            if len(steps[j - 1]["p_along_z_MPa"]) == len(zs) else np.asarray(steps[j]["p_along_z_MPa"])
        series = {"z_mm": zs, "peak_pressure_MPa": pz}
        return {"success": True, "message": f"CalculiX contact: {info['nodes']} nodes, {len(steps)} steps, load "
                f"{'bracketed' if bracketed else 'NOT bracketed'}", "nfev": None, "series": series,
                "outputs": outputs, "files": files(), "cleanup": work}

    def tool_versions(self):
        return self._versions


class Roller3DStudy(Study):
    name = "roller_3d"
    models = {"ccx_roller_3d": CalculiXRoller3D}
    metrics = frozenset({"peak_contact_pressure_MPa", "mid_contact_pressure_MPa", "peak_over_mid",
                         "peak_position_from_end_mm", "max_subsurface_shear_MPa"})
    param_names = PARAMS
    series_file = "pressure_along_roller.csv"
    compare_description = "max relative difference of the peak pressure along the roller"

    def derive(self, params):
        R, E, nu = (float(params[k]) for k in ("roller_radius_mm", "youngs_modulus_MPa", "poisson_ratio"))
        ref = hertz.line_contact(float(params["line_load_N_per_mm"]), R, E, nu)
        return {"hertz_long_roller": ref, "lundberg_A_um": _W.lundberg_A_um(params),
                "total_load_N": float(params["line_load_N_per_mm"]) * float(params["roller_length_mm"])}

    def compute_metrics(self, series, params, case, outputs=None):
        t = outputs["at_target"]
        L2 = float(params["roller_length_mm"]) / 2
        return {"peak_contact_pressure_MPa": t["p_peak_MPa"], "mid_contact_pressure_MPa": t["p_mid_MPa"],
                "peak_over_mid": t["p_peak_MPa"] / t["p_mid_MPa"],
                "peak_position_from_end_mm": L2 - abs(t["p_peak_z_mm"]),
                "max_subsurface_shear_MPa": t["tau_max_MPa"]}

    def verify_point(self, case, point, pdir, series, backend):
        tol = case["verification"]
        p, out, m = point["parameters"], point["solver_outputs"], point["metrics"]
        t = out["at_target"]
        R, E, nu = (float(p[k]) for k in ("roller_radius_mm", "youngs_modulus_MPa", "poisson_ratio"))
        # the mid-length line load from the nodal pressures, scaled by reaction / pressure integral (the smearing)
        q_corr = t["q_mid_N_per_mm"] * abs(t["F_top_N"]) / t["contact_integral_N"]
        loc = hertz.line_contact(q_corr, R, E, nu)
        target = out["target_quarter_load_N"]
        checks = [
            check("load_bracketed", "the target load lies between two completed steps (0 = yes)",
                  0.0 if out["bracketed"] else 1.0, 0.0, kind="validity"),
            check("equilibrium", "max over the steps of |roller reaction + plate reaction| / roller reaction",
                  max(abs(s["F_top_N"] + s["F_bottom_N"]) / abs(s["F_top_N"]) for s in out["steps"]),
                  tol["equilibrium_rel_tol"]),
            check("contact_integral", "|contact pressure integrated over the patch / roller reaction - 1| at the target "
                  "load (the nodal pressures' smearing of the contact edge)",
                  abs(t["contact_integral_N"] / abs(t["F_top_N"]) - 1), tol["integral_rel_tol"]),
            check("hertz_mid_pressure", "|peak pressure at mid-length - Hertz p0 for the local line load there| / p0 "
                  "(long-roller limit)", abs(t["p_mid_MPa"] / loc["peak_pressure_MPa"] - 1), tol["hertz_rel_tol"]),
            check("elastic", "max subsurface shear / shear yield (Tresca, yield / 2)",
                  m["max_subsurface_shear_MPa"] / (float(p["yield_strength_MPa"]) / 2), 1.0, kind="validity"),
        ]
        roller_figure(pdir / "response.png", series, out, p, m, loc)
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "contact_element_size_mm":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: float(pt["parameters"]["contact_element_size_mm"]))
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(float(pt["parameters"]["contact_element_size_mm"]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
        for metric in sorted({r["metric"] for r in case["requirements"]}):
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine), design_order=2,
                                           noise_floor=tol["mesh_noise_rel"])
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


def roller_figure(path, series, out, p, m, loc):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2, _style, plt

    fig, ax = plt.subplots(figsize=(7, 4))
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    z, pz = np.asarray(series["z_mm"]), np.asarray(series["peak_pressure_MPa"])
    ax.plot(z, pz, "o-", color=SERIES_1, ms=3, lw=1.5, label="3D: peak pressure across the contact, along the roller")
    ax.axhline(loc["peak_pressure_MPa"], color=SERIES_2, ls="--", lw=1.1, label="Hertz, local line load at mid-length")
    ax.axhline(650.0, color=TEXT, ls=":", lw=0.9, label="limit 650 MPa")
    ax.axvline(float(p["roller_length_mm"]) / 2, color=TEXT_2, lw=0.8)
    ax.set_xlabel("distance from mid-length (mm); the roller ends at the grey line")
    ax.set_ylabel("contact pressure (MPa)")
    ax.legend(frameon=False, fontsize=7.5)
    fig.suptitle(f"profile {p['profile']}: peak {m['peak_contact_pressure_MPa']:.0f} MPa, "
                 f"{m['peak_position_from_end_mm']:.2f} mm from the end", fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = Roller3DStudy()

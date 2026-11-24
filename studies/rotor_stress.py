"""Study: IPM rotor lamination at overspeed (study 7), CalculiX plane stress on half a pole of our Prius machine.

Model:     pyleecan_gmsh_ccx_rotor: the pole exported from Pyleecan (models/motor/export_rotor_pole.py, Pyleecan
           environment), meshed by Gmsh and solved by CalculiX (models/fea/rotor_ccx.py): steel centrifugal load, the
           magnet's centrifugal force as a traction on its seat, symmetry on the pole axis and the inter-pole line
Metric:    linearized (membrane plus bending) von Mises stress along radial stress classification lines through the
           bridge (the steel between the pocket's end and the OD), maximum over the bridge; the corner peak is a
           singularity and is reported only
Reference: the same pipeline on the plain annulus against the exact rotating-disk solution (plane stress, free
           edges); force equilibrium of the sector using the constrained reaction components only (CalculiX's RF
           totals include the external loads on free dofs); a fixed-guided beam estimate of the bridge (model form)
Run-level: GCI on the requirement metrics when the sweep is the bridge element size
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness.backend_base import Backend, failed
from harness.calculix import read_dat_total_forces, read_frd
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study
from studies.motor_em import MACHINES

EXPORTER = "models/motor/export_rotor_pole.py"
WRITER = "models/fea/rotor_ccx.py"
PARAMS = ("machine", "speed_rpm", "max_speed_rpm", "yield_strength_MPa", "bridge_element_size_mm",
          "far_element_size_mm", "refine_distance_mm", "scl_count", "scl_points")


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def bridge_scls(geom, xy, stress_xyz, n_lines, n_pts, linearize):
    """Linearize along radial lines across the bridge's angular span; returns arrays (theta_deg, membrane, m + b)."""
    from scipy.interpolate import LinearNDInterpolator

    Rb, Ro = float(geom["bridge_arc_radius_mm"]), float(geom["rotor_outer_radius_mm"])
    arc = [s for s in geom["pocket_half"] if s[0] == "arc"][0]
    t0, t1 = sorted([math.atan2(arc[4], arc[3]), math.atan2(arc[2], arc[1])])
    interp = LinearNDInterpolator(xy, stress_xyz)
    th_out, m_out, mb_out = [], [], []
    for th in np.linspace(t0, t1, int(n_lines)):
        s = np.linspace(0.0, Ro - Rb, int(n_pts))
        r = Rb + s
        v = interp(np.column_stack([r * math.cos(th), r * math.sin(th)]))
        ok = ~np.isnan(v[:, 0])
        s, v = s[ok], v[ok]
        c, sn = math.cos(th), math.sin(th)
        sxx, syy, sxy = v[:, 0], v[:, 1], v[:, 2]
        srr = sxx * c * c + syy * sn * sn + 2 * sxy * c * sn
        stt = sxx * sn * sn + syy * c * c - 2 * sxy * c * sn
        srt = (syy - sxx) * c * sn + sxy * (c * c - sn * sn)
        m, mb = linearize(s, srr, stt, srt)
        th_out.append(math.degrees(th)); m_out.append(m); mb_out.append(mb)
    return np.array(th_out), np.array(m_out), np.array(mb_out)


class GmshCalculiXRotor(Backend):
    # our machine definitions (studies.motor_em.MACHINES), hashed as sources; a case names one by file name. Until
    # 2026-11-24 the study always loaded the first one and ignored the case's machine (every run so far named it).
    sources = (EXPORTER, WRITER, *MACHINES)

    def __init__(self):
        from studies.fin import find_ccx
        from studies.motor_em import pyleecan_python

        self.ccx = find_ccx()
        self.gmsh = self.ccx.parent / "gmsh.exe"
        if not self.gmsh.exists():
            raise RuntimeError("gmsh.exe not found next to ccx")
        self.python = pyleecan_python()
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        self.writer = _load(self.source_path(WRITER, source_dir), "rotor_ccx_saved")
        self.exporter = self.source_path(EXPORTER, source_dir)
        self.machines = {Path(m).name: self.source_path(m, source_dir) for m in MACHINES}
        g = subprocess.run([str(self.gmsh), "--version"], capture_output=True, text=True, timeout=60)
        c = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"gmsh": (g.stdout + g.stderr).strip().splitlines()[-1],
                          "CalculiX": (c.stdout.strip().splitlines() or ["?"])[-1]}

    def _solve_one(self, geom, params, d: Path, with_pocket: bool):
        d.mkdir(parents=True, exist_ok=True)
        self.writer.write_geo(geom, params, d / "mesh.geo", with_pocket=with_pocket)
        g = subprocess.run([str(self.gmsh), "mesh.geo", "-2", "-format", "inp", "-o", "mesh.inp"], cwd=d,
                           capture_output=True, text=True, timeout=1200)
        (d / "gmsh.log").write_text(g.stdout + g.stderr, encoding="utf-8")
        if g.returncode != 0 or not (d / "mesh.inp").exists():
            raise RuntimeError(f"gmsh failed (exit {g.returncode}) in {d.name}")
        info = self.writer.write_deck(geom, params, d / "mesh.inp", d / "job.inp", with_pocket=with_pocket)
        c = subprocess.run([str(self.ccx), "-i", "job"], cwd=d, capture_output=True, text=True, timeout=7200)
        (d / "ccx.log").write_text(c.stdout + c.stderr, encoding="utf-8")
        if c.returncode != 0 or not (d / "job.frd").exists():
            raise RuntimeError(f"CalculiX failed (exit {c.returncode}) in {d.name}; see ccx.log")
        ids, xy, elems = self.writer.read_mesh(d / "mesh.inp")
        S = self.writer.nodal_stress(read_frd(d / "job.frd"))
        vals = np.array([S[int(n)] for n in ids])
        return info, ids, xy, vals, read_dat_total_forces(d / "job.dat")

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="rotor_"))
        keep = ["pole.json", "export.log"] + [f"{t}/{n}" for t in ("pole", "ring")
                                              for n in ("mesh.geo", "job.inp", "job.dat", "job.sta", "gmsh.log",
                                                        "ccx.log")]

        def files():
            return {n.replace("/", "_"): work / n for n in keep if (work / n).exists()}

        try:
            if params["machine"] not in self.machines:
                raise RuntimeError(f"unknown machine {params['machine']!r}: not in studies.motor_em.MACHINES")
            e = subprocess.run([str(self.python), str(self.exporter), str(self.machines[params["machine"]]),
                                "pole.json"], cwd=work,
                               capture_output=True, text=True, timeout=600, env=os.environ | {"PYTHONUTF8": "1"})
            (work / "export.log").write_text(e.stdout + e.stderr, encoding="utf-8")
            if e.returncode != 0:
                raise RuntimeError(f"pole export failed: {e.stderr.strip()[-300:]}")
            geom = json.loads((work / "pole.json").read_text(encoding="utf-8"))
            info, ids, xy, vals, tot = self._solve_one(geom, params, work / "pole", True)
            rinfo, rids, rxy, rvals, rtot = self._solve_one(geom, params, work / "ring", False)
        except Exception as ex:
            res = failed(f"{type(ex).__name__}: {ex}")
            res.update(files=files(), cleanup=work)
            return res
        th, m, mb = bridge_scls(geom, xy, vals, params["scl_count"], params["scl_points"], self.writer.linearize)
        vm = np.sqrt(vals[:, 0] ** 2 - vals[:, 0] * vals[:, 1] + vals[:, 1] ** 2 + 3 * vals[:, 2] ** 2)
        k = int(np.argmax(vm))
        on = np.abs(rxy[:, 1]) < 1e-6
        lam = geom["lamination"]
        sr, st = self.writer.rotating_disk(rxy[on, 0], geom["rotor_bore_radius_mm"], geom["rotor_outer_radius_mm"],
                                           lam["density_kg_m3"] * 1e-12, rinfo["omega_rad_s"], lam["poisson_ratio"])
        ring_err = float(max(np.max(np.abs(rvals[on, 0] - sr)), np.max(np.abs(rvals[on, 1] - st))) / st.max())
        series = {"scl_angle_deg": th, "membrane_vm_MPa": m, "membrane_bending_vm_MPa": mb}
        outputs = {"pole": info, "ring": {k2: rinfo[k2] for k2 in ("nodes", "omega_rad_s")},
                   "reaction_totals_pole": tot, "reaction_totals_ring": rtot,
                   "ring_max_rel_error": ring_err, "ring_hoop_bore_MPa": float(st.max()),
                   "peak_nodal_vm_MPa": float(vm[k]), "peak_xy_mm": xy[k].tolist(),
                   "geometry": {k2: geom[k2] for k2 in ("rotor_bore_radius_mm", "rotor_outer_radius_mm", "stack_mm",
                                                         "poles", "bridge_arc_radius_mm", "seat_half", "magnet_half",
                                                         "lamination", "magnet", "pocket_half")}}
        return {"success": True, "message": f"half pole {info['nodes']} nodes, ring {rinfo['nodes']} nodes",
                "nfev": None, "series": series, "outputs": outputs, "files": files(), "cleanup": work}

    def tool_versions(self):
        return self._versions


def beam_estimate(outputs, params):
    """Fixed-guided beam estimate of one bridge (model form). Each half pole has one bridge. Its load F is the outward
    centrifugal resultant of the half pole piece (the steel between the pocket's outer edge and the OD, from the pole
    axis to the bridge) plus the half pole's magnet. Tension F / (t L) plus end bending 3 F l / (t^2 L) (a beam of
    length l, thickness t, both ends built in, one end displaced)."""
    g = outputs["geometry"]
    Ro, Rb, L = g["rotor_outer_radius_mm"], g["bridge_arc_radius_mm"], g["stack_mm"]
    arc = [s for s in g["pocket_half"] if s[0] == "arc"][0]
    a_end, a_start = sorted([math.atan2(arc[4], arc[3]), math.atan2(arc[2], arc[1])], reverse=True)
    t, l = Ro - Rb, abs(a_end - a_start) * (Ro + Rb) / 2
    x9, y9, x8, y8 = g["pocket_half"][-1][1:5]           # the pocket's outer edge, from the bridge to the outer apex
    th = np.linspace(0.0, a_start, 400)
    poly = np.concatenate([[complex(x8, y8), complex(Ro, 0.0)], Ro * np.exp(1j * th[1:]), [complex(x9, y9)]])
    x, y = poly.real, poly.imag
    cr = x * np.roll(y, -1) - np.roll(x, -1) * y
    A = 0.5 * cr.sum()
    Sx, Sy = np.sum((x + np.roll(x, -1)) * cr) / 6, np.sum((y + np.roll(y, -1)) * cr) / 6
    w = float(params["speed_rpm"]) * 2 * math.pi / 60
    rho = g["lamination"]["density_kg_m3"] * 1e-12
    F_vec = rho * w * w * L * np.array([Sx, Sy]) + np.array(outputs["pole"]["magnet_force_N"])
    F = float(np.hypot(*F_vec))
    sig_t, sig_b = F / (t * L), 3 * F * l / (t * t * L)
    return {"pole_piece_half_area_mm2": float(abs(A)), "load_per_bridge_N": F, "tension_MPa": sig_t,
            "bending_MPa": sig_b, "estimate_MPa": sig_t + sig_b, "bridge_thickness_mm": t, "bridge_length_mm": l}


class RotorStressStudy(Study):
    name = "rotor_stress"
    models = {"pyleecan_gmsh_ccx_rotor": GmshCalculiXRotor}
    metrics = frozenset({"bridge_linearized_vm_MPa", "bridge_membrane_vm_MPa", "bridge_linearized_vm_at_max_speed_MPa",
                         "peak_corner_vm_MPa"})
    param_names = PARAMS
    series_file = "bridge_scl.csv"
    compare_description = "max relative difference of the linearized stress along the bridge"

    def derive(self, params):
        if float(params["speed_rpm"]) <= 0 or int(params["scl_count"]) < 3 or int(params["scl_points"]) < 11:
            raise ValueError("positive speed, at least 3 stress classification lines and 11 points on each")
        return {"speed_ratio_to_max": float(params["speed_rpm"]) / float(params["max_speed_rpm"])}

    def compute_metrics(self, series, params, case, outputs=None):
        mb = np.asarray(series["membrane_bending_vm_MPa"])
        k = (float(params["max_speed_rpm"]) / float(params["speed_rpm"])) ** 2   # stress ~ omega^2 (linear elastic)
        return {"bridge_linearized_vm_MPa": float(mb.max()),
                "bridge_membrane_vm_MPa": float(np.max(series["membrane_vm_MPa"])),
                "bridge_linearized_vm_at_max_speed_MPa": float(mb.max() * k),
                "peak_corner_vm_MPa": float(outputs["peak_nodal_vm_MPa"])}

    def verify_point(self, case, point, pdir, series, backend):
        tol = case["verification"]
        p, out, m = point["parameters"], point["solver_outputs"], point["metrics"]
        pole = out["pole"]
        sc = pole["force_scale"]
        n2 = np.array(pole["inter_pole_normal"])
        tx = out["reaction_totals_pole"]
        R = np.array([0.0, tx["XSYM"][1]]) / sc + float(np.dot(np.array(tx["SYM2"][:2]) / sc, n2)) * n2
        F = np.array(pole["body_force_N"]) + np.array(pole["magnet_force_N"])
        eq = float(np.hypot(*(R + F)) / np.hypot(*F))
        est = beam_estimate(out, p)
        checks = [
            check("rotating_disk", "plain annulus through the same pipeline: max |sigma - exact| / sigma_theta at the "
                  "bore (plane-stress rotating disk, free edges)", out["ring_max_rel_error"], tol["ring_rel_tol"]),
            check("equilibrium", "|steel centrifugal + magnet load + constrained reactions| / |load| (pole axis y and "
                  "inter-pole normal components only)", eq, tol["equilibrium_rel_tol"]),
            check("beam_estimate", "|FE linearized - fixed-guided beam estimate (tension + end bending)| / FE "
                  f"(model form; estimate {est['estimate_MPa']:.0f} MPa)",
                  abs(m["bridge_linearized_vm_MPa"] - est["estimate_MPa"]) / m["bridge_linearized_vm_MPa"],
                  tol["beam_estimate_rel_tol"]),
            check("membrane_elastic", "bridge membrane von Mises / yield (below 1: the section does not yield "
                  "through its thickness, so a linear-elastic model applies to the membrane)",
                  m["bridge_membrane_vm_MPa"] / float(p["yield_strength_MPa"]), 1.0, kind="validity"),
        ]
        rotor_figure(pdir / "response.png", series, m, p, est, title=f"{point['label']}  ({float(p['speed_rpm']):g} rpm,"
                     f" bridge elements {float(p['bridge_element_size_mm']):g} mm)")
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "bridge_element_size_mm":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: float(pt["parameters"]["bridge_element_size_mm"]))
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(float(pt["parameters"]["bridge_element_size_mm"]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
        for metric in sorted({r["metric"] for r in case["requirements"]} | {"bridge_membrane_vm_MPa"}):
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine), design_order=2,
                                           noise_floor=tol.get("mesh_noise_rel", 1e-5))
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


def rotor_figure(path, series, m, p, est, *, title):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2, _style, plt

    fig, ax = plt.subplots(figsize=(8, 4))
    fig.patch.set_facecolor(SURFACE)
    th = series["scl_angle_deg"]
    ax.plot(th, series["membrane_bending_vm_MPa"], color=SERIES_1, lw=1.6, label="membrane + bending von Mises")
    ax.plot(th, series["membrane_vm_MPa"], color=SERIES_1, lw=1.0, ls="--", label="membrane von Mises")
    ax.axhline(float(p["yield_strength_MPa"]), color=SERIES_2, lw=1.2, label=f"yield {float(p['yield_strength_MPa']):g} MPa")
    ax.axhline(est["estimate_MPa"], color=TEXT_2, lw=0.8, ls=":", label=f"beam estimate {est['estimate_MPa']:.0f} MPa")
    ax.set_xlabel("stress classification line angle across the bridge (deg from the pole axis)")
    ax.set_ylabel("linearized stress (MPa)")
    ax.legend(frameon=False, fontsize=8)
    _style(ax)
    fig.suptitle(f"{title}: max {m['bridge_linearized_vm_MPa']:.0f} MPa", fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = RotorStressStudy()

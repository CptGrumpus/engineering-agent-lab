"""Study: preloaded bolted joint with friction contact: clamp, then a side load to slip.

Model:     ccx_bolted_joint (models/fea/bolted_joint_ccx.py): half model of two clamped steel plates,
           structured polar C3D8I mesh, clamp force on the washer areas, surface-to-surface penalty
           contact with Coulomb friction; step 1 preload, step 2 side displacement until gross slip
References (validation/bolted_joint.py, VDI 2230 Part 1, independent of the FE path):
           slip load mu F_V (exact once the whole interface slides); clamped-plate compliance and
           the pressure-cone limit diameter (model form); bolt compliance, embedding loss, load
           factor and opening load (hand method, using the FE plate compliance in the joint diagram)
Run-level: GCI on the requirement metrics when the sweep is the element size

The joint diagram: the FE measures how the plates compress under the clamp force (delta_P) and the
friction the interface can carry; VDI 2230 supplies the bolt compliance and the embedding (settling)
amount. Settling f_Z then costs F_Z = f_Z / (delta_S + delta_P) of clamp force, and both design
loads follow from the residual clamp force F_K = F_V - F_Z: slip mu_FE F_K (Coulomb, linear in the
clamp force) and opening F_K / (1 - Phi_n).
"""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness.backend_base import Backend, failed
from harness.calculix import read_frd
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study
from studies.fin import find_ccx
from studies.strut_buckling import read_dat_blocks
from validation import bolted_joint as bj

WRITER = "models/fea/bolted_joint_ccx.py"


def _load_writer(path: Path):
    spec = importlib.util.spec_from_file_location("bolted_joint_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_W = _load_writer(Path(__file__).resolve().parent.parent / WRITER)
PARAMS = _W.PARAMS + ("bolt_thread", "bolt_shank_length_mm", "bolt_free_thread_length_mm", "bolt_proof_stress_MPa",
                      "embedding_um", "load_introduction_factor")


def _p(params, k):
    return float(params[k])


def clamp_length(p):
    return _p(p, "top_thickness_mm") + _p(p, "bottom_thickness_mm")


class CalculiXBoltedJoint(Backend):
    sources = (WRITER,)

    def __init__(self):
        self.ccx = find_ccx()
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        self.writer = _load_writer(self.source_path(WRITER, source_dir))
        r = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"CalculiX": (r.stdout.strip().splitlines() or ["?"])[-1]}

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="bolted_"))
        m = self.writer.JointMesh(params)
        (work / "job.inp").write_text(self.writer.write_deck(params, m), encoding="utf-8")

        def files():
            return {f.name: f for f in sorted(work.glob("*")) if f.suffix in (".inp", ".dat", ".sta", ".log")
                    and f.stat().st_size < 80e6}

        r = subprocess.run([str(self.ccx), "-i", "job"], cwd=work, capture_output=True, text=True, timeout=14400)
        (work / "ccx.log").write_text(r.stdout + r.stderr, encoding="utf-8")
        if r.returncode != 0 or "Job finished" not in r.stdout:
            return failed(f"CalculiX failed (exit {r.returncode}); see ccx.log") | {"files": files(), "cleanup": work}
        blocks = read_dat_blocks(work / "job.dat")
        get = lambda s: [b for b in blocks if b["set"] == s]
        ut, ub = get("NWASHTOP")[0]["rows"], get("NWASHBOT")[0]["rows"]
        zfix = get("NZFIX")[0]["rows"][0]
        top = [(b["time"], b["rows"][0]) for b in get("NRIMTOP")]
        bot = [(b["time"], b["rows"][0]) for b in get("NRIMBOT")]
        t = np.array([v[0] for v in top]) - 1.0
        fx_top = np.array([v[1][0] for v in top])
        fx_bot = np.array([v[1][0] for v in bot])
        # interface contact pressure along the symmetry line (theta = 0), end of the preload step
        frd = read_frd(work / "job.frd")
        line = [m.nid("top", i, 0, 0) for i in range(m.nr + 1)]
        cp = dict(zip(frd["CONTACT"]["ids"].tolist(), frd["CONTACT"]["CPRESS"].tolist())) if "CONTACT" in frd else {}
        p_line = np.array([cp.get(n, np.nan) for n in line])
        approach = float(ub[:, 3].mean() - ut[:, 3].mean())
        series = {"r_mm": m.r, "contact_pressure_MPa": p_line}
        outputs = {"divisions": [m.nr, m.nt, m.nz1, m.nz2], "elements": m.nr * m.nt * (m.nz1 + m.nz2),
                   "washer_approach_mm": approach, "zfix_reaction_N": [float(v) for v in zfix],
                   "slip_displacement_mm": (t * _p(params, "slip_displacement_mm")).tolist(),
                   "rim_force_top_N": fx_top.tolist(), "rim_force_bottom_N": fx_bot.tolist()}
        # Rigid-limit companion (numerics.rigid_limit_stiffness_factor = k): the same deck with E (and so
        # the contact penalties) k times larger. CalculiX evaluates contact on the deformed surfaces, so
        # the interface tilts by about the strain under the side load and the slip plateau falls short of
        # mu F_V in proportion to 1/E (1.31e-3 / 1.32e-4 / 1.33e-5 at E / 10 E / 100 E). Extrapolating
        # the two plateaus in 1/E gives the rigid-interface slip load, for which Coulomb is exact.
        k = float(numerics.get("rigid_limit_stiffness_factor", 0) or 0)
        if k > 1:
            ps = dict(params, youngs_modulus_MPa=_p(params, "youngs_modulus_MPa") * k)
            stiff = work / "stiff"
            stiff.mkdir()
            (stiff / "job.inp").write_text(self.writer.write_deck(ps, self.writer.JointMesh(ps)), encoding="utf-8")
            rs = subprocess.run([str(self.ccx), "-i", "job"], cwd=stiff, capture_output=True, text=True, timeout=14400)
            (work / "ccx_stiff.log").write_text(rs.stdout + rs.stderr, encoding="utf-8")
            if rs.returncode != 0 or "Job finished" not in rs.stdout:
                return failed(f"CalculiX failed on the rigid-limit companion (exit {rs.returncode})") | {
                    "files": files(), "cleanup": work}
            outputs["rigid_limit_stiffness_factor"] = k
            outputs["rim_force_top_stiff_N"] = [float(b["rows"][0][0]) for b in read_dat_blocks(stiff / "job.dat")
                                                if b["set"] == "NRIMTOP"]
        return {"success": True, "message": f"CalculiX: {outputs['elements']} C3D8I, rim force {fx_top[-1]:.2f} N",
                "nfev": len(t), "series": series, "outputs": outputs, "files": files(), "cleanup": work}

    def tool_versions(self):
        return self._versions


def rigid_limit_slip(s_E: float, s_kE: float, k: float) -> float:
    """Slip load extrapolated to a rigid interface from runs at E and k E: the shortfall from mu F_V is
    linear in 1/E (the interface tilts by about the strain), S(E) = S_rigid - c / E."""
    return s_kE + (s_kE - s_E) / (k - 1)


def contact_diameter(r, p):
    """Diameter where the interface pressure falls to zero (linear interpolation outward)."""
    ok = np.isfinite(p)
    r, p = r[ok], p[ok]
    pos = np.where(p > 1e-6 * np.nanmax(p))[0]
    k = pos[-1]
    if k == len(r) - 1:
        return 2 * float(r[-1])
    return 2 * float(r[k] + (r[k + 1] - r[k]) * p[k] / (p[k] - p[k + 1]))


class BoltedJointStudy(Study):
    name = "bolted_joint"
    models = {"ccx_bolted_joint": CalculiXBoltedJoint}
    metrics = frozenset({"slip_load_N", "plate_compliance_mm_per_N", "contact_diameter_mm", "residual_clamp_force_N",
                         "design_slip_load_N", "opening_load_N"})
    param_names = PARAMS
    series_file = "interface_pressure.csv"
    compare_description = "max relative difference over the interface pressure line"

    def derive(self, p):
        E, lK = _p(p, "youngs_modulus_MPa"), clamp_length(p)
        dW, dh, DA = _p(p, "washer_diameter_mm"), _p(p, "hole_diameter_mm"), _p(p, "plate_outer_diameter_mm")
        dS, parts = bj.bolt_compliance(E, p["bolt_thread"], _p(p, "bolt_shank_length_mm"),
                                       _p(p, "bolt_free_thread_length_mm"))
        dP = bj.plate_compliance(E, lK, dW, dh, DA)
        FV, mu = _p(p, "preload_N"), _p(p, "friction_coefficient")
        FZ = bj.embedding_loss(_p(p, "embedding_um") * 1e-3, dS, dP)
        phi = bj.load_factor(dS, dP, _p(p, "load_introduction_factor"))
        d = bj.THREADS[p["bolt_thread"]]["d"]
        As = np.pi / 4 * ((bj.THREADS[p["bolt_thread"]]["d2"] + bj.THREADS[p["bolt_thread"]]["d3"]) / 2) ** 2
        return {"bolt_compliance_mm_per_N": dS, "plate_compliance_vdi_mm_per_N": dP,
                "cone_limit_diameter_mm": bj.cone_limit_diameter(lK, dW, DA), "slip_load_vdi_N": bj.slip_load(mu, FV),
                "embedding_loss_vdi_N": FZ, "load_factor_vdi": phi,
                "opening_load_vdi_N": bj.opening_load(FV - FZ, phi),
                "design_slip_load_vdi_N": bj.slip_load(mu, FV - FZ),
                "bolt_stress_area_mm2": float(As), "bolt_preload_stress_MPa": FV / As,
                "hole_clearance_mm": (dh - d) / 2}

    def compute_metrics(self, series, p, case, outputs=None):
        FV = _p(p, "preload_N")
        slip = 2 * float(np.mean(outputs["rim_force_top_N"][-3:]))          # half model x 2
        dP = outputs["washer_approach_mm"] / FV
        dS, _ = bj.bolt_compliance(_p(p, "youngs_modulus_MPa"), p["bolt_thread"], _p(p, "bolt_shank_length_mm"),
                                   _p(p, "bolt_free_thread_length_mm"))
        FK = FV - bj.embedding_loss(_p(p, "embedding_um") * 1e-3, dS, dP)
        phi = bj.load_factor(dS, dP, _p(p, "load_introduction_factor"))
        return {"slip_load_N": slip, "plate_compliance_mm_per_N": dP,
                "contact_diameter_mm": contact_diameter(series["r_mm"], series["contact_pressure_MPa"]),
                "residual_clamp_force_N": FK, "design_slip_load_N": slip * FK / FV,
                "opening_load_N": bj.opening_load(FK, phi)}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        p, d, m, out = point["parameters"], point["derived"], point["metrics"], point["solver_outputs"]
        FV, mu = _p(p, "preload_N"), _p(p, "friction_coefficient")
        ft = np.array(out["rim_force_top_N"])
        fb = np.array(out["rim_force_bottom_N"])
        plateau_spread = float(np.ptp(ft[-3:])) / abs(ft[-1])
        slip_err = abs(m["slip_load_N"] - d["slip_load_vdi_N"]) / d["slip_load_vdi_N"]
        if "rim_force_top_stiff_N" in out:
            k = out["rigid_limit_stiffness_factor"]
            s_rigid = rigid_limit_slip(m["slip_load_N"], 2 * float(np.mean(out["rim_force_top_stiff_N"][-3:])), k)
            checks = [
                check("slip_rigid_limit", f"|slip load extrapolated to a rigid interface (E and {k:g} E, linear in "
                      "1/E) - mu F_V| / mu F_V (Coulomb: exact)", abs(s_rigid - d["slip_load_vdi_N"])
                      / d["slip_load_vdi_N"], tol["slip_rigid_rel_tol"]),
                check("slip_deformable", "|slip load (FE, gross slip) - mu F_V| / mu F_V (model form: the interface "
                      "tilts by about the strain under the side load)", slip_err, tol["slip_rel_tol"]),
            ]
        else:
            checks = [check("slip_exact", "|slip load (FE, gross slip) - mu F_V| / mu F_V (Coulomb: exact once the "
                            "whole interface slides)", slip_err, tol["slip_rel_tol"])]
        checks += [
            check("gross_slip_reached", "spread of the rim force over the last three increments / force "
                  "(a plateau: the whole interface slides)", plateau_spread, tol["plateau_rel_tol"]),
            check("clamp_force_balance", "|z reaction at the support| / (F_V / 2) (the clamp forces balance; none "
                  "lost into a support)", abs(out["zfix_reaction_N"][2]) / (FV / 2), tol["equilibrium_rel_tol"]),
            check("shear_balance", "|top rim force + bottom rim force| / rim force, last increment",
                  abs(ft[-1] + fb[-1]) / abs(ft[-1]), tol["equilibrium_rel_tol"]),
            check("plate_compliance_reference", "|plate compliance FE - VDI 2230 pressure cone| / VDI (model form; the "
                  "plates are about 15 % of the joint compliance)", abs(m["plate_compliance_mm_per_N"]
                  - d["plate_compliance_vdi_mm_per_N"]) / d["plate_compliance_vdi_mm_per_N"],
                  tol["plate_compliance_rel_tol"]),
            check("contact_diameter_reference", "|interface contact diameter FE - VDI cone limit D_A,Gr| / D_A,Gr "
                  "(model form)", abs(m["contact_diameter_mm"] - d["cone_limit_diameter_mm"])
                  / d["cone_limit_diameter_mm"], tol["contact_diameter_rel_tol"]),
            check("cone_fits", "VDI cone limit diameter / plate diameter (cone formula valid at or below 1)",
                  d["cone_limit_diameter_mm"] / _p(p, "plate_outer_diameter_mm"), 1.0, kind="validity"),
            check("no_bolt_bearing", "slip displacement / hole clearance (the bolt shank is not modelled: it must not "
                  "touch the hole)", out["slip_displacement_mm"][-1] / d["hole_clearance_mm"], 1.0, kind="validity"),
            check("bolt_within_proof", "preload stress in the bolt / proof stress", d["bolt_preload_stress_MPa"]
                  / _p(p, "bolt_proof_stress_MPa"), tol["bolt_utilisation_max"], kind="validity"),
        ]
        joint_figure(pdir / "response.png", p, d, m, out, series,
                     title=f"{point['label']}  ({out['elements']} C3D8I, half model)")
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
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine), design_order=2)
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


def joint_figure(path, p, d, m, out, series, *, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from harness.plotting import GRID, SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.3), facecolor=SURFACE)
    u = np.array(out["slip_displacement_mm"]) * 1e3
    f = 2 * np.array(out["rim_force_top_N"]) / 1e3
    a1.plot(np.concatenate([[0], u]), np.concatenate([[0], f]), "o-", ms=4, color=SERIES_1, label="FE (both halves)")
    a1.axhline(d["slip_load_vdi_N"] / 1e3, color=SERIES_2, lw=1.5, ls="--", label="mu F_V (assembly preload)")
    a1.axhline(m["design_slip_load_N"] / 1e3, color=TEXT, lw=1.2, label="after embedding loss")
    a1.set_xlabel("side displacement of the top plate (µm)")
    a1.set_ylabel("side load (kN)")
    a1.set_title("Side load until the joint slips", color=TEXT, loc="left", fontsize=10)
    r, pc = series["r_mm"], series["contact_pressure_MPa"]
    a2.plot(r, pc, "o-", ms=3.5, color=SERIES_1, label="FE interface pressure (preload)")
    a2.axvline(_p(p, "washer_diameter_mm") / 2, color=TEXT_2, lw=1, ls=":", label="washer edge")
    a2.axvline(d["cone_limit_diameter_mm"] / 2, color=SERIES_2, lw=1.5, ls="--", label="VDI cone limit D_A,Gr / 2")
    a2.axvline(m["contact_diameter_mm"] / 2, color=TEXT, lw=1.2, label="FE contact edge")
    a2.set_xlabel("radius (mm)")
    a2.set_ylabel("contact pressure (MPa)")
    a2.set_title("Where the plates press together", color=TEXT, loc="left", fontsize=10)
    for a in (a1, a2):
        a.grid(color=GRID, lw=0.6)
        a.legend(frameon=False, fontsize=8, labelcolor=TEXT_2)
        a.tick_params(colors=TEXT_2)
        for s_ in a.spines.values():
            s_.set_color(GRID)
    fig.suptitle(title, color=TEXT, fontsize=10, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=120, facecolor=SURFACE)
    plt.close(fig)


STUDY = BoltedJointStudy()

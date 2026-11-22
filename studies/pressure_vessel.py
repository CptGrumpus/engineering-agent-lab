"""Study 18: pressure vessel shell with a radial nozzle, elastic stress analysis by linearisation (the method of ASME
BPVC Section VIII Division 2, Part 5: protection against plastic collapse, and the primary-plus-secondary range).

Model:     cadquery_ccx_vessel (models/fea/pressure_vessel.py): CadQuery quarter model -> Gmsh C3D10 refined at the
           junction -> CalculiX static; stresses linearised along stress classification lines (harness/linearize.py)
Reference: the far shell against the Lame closed-end cylinder (an exact solution: hoop stress at the bore and the
           linearised membrane); global equilibrium against the exact pressure resultants on both symmetry planes and a
           zero reaction at the single axial support (the pressure on a closed vessel balances itself); CAD and mesh
           volume. No closed form covers the junction: there the evidence is the mesh study of the linearised stresses
           (linearised values converge where a peak at a sharp corner would not).
Run-level: GCI on the requirement metrics when the sweep is element_size_local_mm.

Classification (stated in each case, the analyst's judgement): far from the nozzle the membrane is general primary
(Pm <= S); at the junction lines the membrane is local primary (PL <= 1.5 S) and membrane plus bending is primary plus
secondary (P + Q <= S_PS = 3 S; bending at a gross structural discontinuity is secondary). Peak stress is reported, not
assessed (no fatigue screening here).
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
from harness.linearize import Tet10Sampler, linearize, von_mises
from harness.study import Study
from studies.strut_buckling import read_dat_blocks

WRITER = "models/fea/pressure_vessel.py"


def _load(path: Path):
    spec = importlib.util.spec_from_file_location("pressure_vessel_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_W = _load(Path(__file__).resolve().parent.parent / WRITER)
PARAMS = _W.PARAMS + ("allowable_stress_MPa",)
LINES = ("shell_long", "shell_trans", "nozzle_long", "nozzle_trans", "far")
JUNCTION = LINES[:4]


class CadQueryCalculiXVessel(Backend):
    sources = (WRITER,)

    def __init__(self):
        from studies.cantilever import find_freecadcmd

        bin_dir = find_freecadcmd().parent
        self.gmsh, self.ccx = bin_dir / "gmsh.exe", bin_dir / "ccx.exe"
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        import cadquery

        self.writer = _load(self.source_path(WRITER, source_dir))
        g = subprocess.run([str(self.gmsh), "--version"], capture_output=True, text=True, timeout=60)
        c = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"cadquery": cadquery.__version__, "gmsh": (g.stdout + g.stderr).strip().splitlines()[-1],
                          "CalculiX": (c.stdout.strip().splitlines() or ["?"])[-1]}

    def solve(self, params, numerics, tolerance_scale=1.0):
        W = self.writer
        work = Path(tempfile.mkdtemp(prefix="vessel_"))
        keep = ("vessel.step", "mesh.geo", "job.inp", "job.dat", "job.sta", "gmsh.log", "ccx.log")

        def files():
            return {n: work / n for n in keep if (work / n).exists()}

        try:
            cad = W.build_step(params, work / "vessel.step")
            W.write_geo(params, work / "mesh.geo")
            g = subprocess.run([str(self.gmsh), "mesh.geo", "-3", "-format", "inp", "-o", "mesh.inp"], cwd=work,
                               capture_output=True, text=True, timeout=3600)
            (work / "gmsh.log").write_text(g.stdout + g.stderr, encoding="utf-8")
            if g.returncode != 0 or not (work / "mesh.inp").exists():
                return failed(f"gmsh failed (exit {g.returncode})") | {"files": files(), "cleanup": work}
            info = W.write_deck(params, work / "mesh.inp", work / "job.inp")
            c = subprocess.run([str(self.ccx), "-i", "job"], cwd=work, capture_output=True, text=True,
                               timeout=float(numerics.get("solver_timeout_s", 7200)))
            (work / "ccx.log").write_text(c.stdout + c.stderr, encoding="utf-8")
            if c.returncode != 0 or not (work / "job.frd").exists():
                return failed(f"CalculiX failed (exit {c.returncode})") | {"files": files(), "cleanup": work}
            ids, xyz, eids, elems = W.read_mesh(work / "mesh.inp")
            frd = read_frd(work / "job.frd")
        except Exception as e:  # noqa: BLE001
            return failed(f"{type(e).__name__}: {e}") | {"files": files(), "cleanup": work}

        S = frd["STRESS"]
        smap = {k: dict(zip(S["ids"].tolist(), S[k].tolist())) for k in ("SXX", "SYY", "SZZ", "SXY", "SYZ", "SZX")}
        stress = np.column_stack([[smap[k].get(int(n), np.nan) for n in ids] for k in smap])
        D = frd["DISP"]
        umax = float(np.max(np.sqrt(D["D1"] ** 2 + D["D2"] ** 2 + D["D3"] ** 2)))
        smp = Tet10Sampler(ids, xyz, elems)
        lines, viol, profiles = {}, 0.0, {}
        for name, (pts, axes, cls) in W.scl_lines(params, int(numerics.get("scl_points", 21))).items():
            vals, v = smp.sample(pts, stress)
            viol = max(viol, v)
            s_pos = np.linalg.norm(pts - pts[0], axis=1)
            res = linearize(s_pos, vals, axes)
            lines[name] = {k: (v_.tolist() if isinstance(v_, np.ndarray) else v_) for k, v_ in res.items()} | {
                "class": cls}
            profiles[name] = {"s_mm": s_pos.tolist(), "vm_MPa": von_mises(vals).tolist(),
                              "local": _local(vals, axes).tolist()}
        blocks = read_dat_blocks(work / "job.dat")
        tot = {b["set"]: b["rows"][0] for b in blocks if b["kind"] == "total"}
        back = next(b["rows"][0] for b in blocks if b["kind"] == "forces" and b["set"] == "NBACK")
        corner = xyz[np.vectorize({int(n): k for k, n in enumerate(ids)}.get)(elems[:, :4])]
        mesh_vol = float(np.sum(np.abs(np.einsum("ij,ij->i", corner[:, 1] - corner[:, 0],
                                                 np.cross(corner[:, 2] - corner[:, 0], corner[:, 3] - corner[:, 0]))) / 6))
        r_far = np.linspace(W.dims(params)["Ri"], W.dims(params)["Ro"], 5)
        outputs = {**info, **{f"cad_{k}": v for k, v in cad.items()}, "mesh_volume_mm3": mesh_vol,
                   "reaction_symy_N": [float(x) for x in tot["NSYMY"][:3]],
                   "reaction_symz_N": [float(x) for x in tot["NSYMZ"][:3]],
                   "reaction_back_N": [float(x) for x in back[1:4]],
                   "expected": W.expected_reactions(params), "lines": lines, "profiles": profiles,
                   "sample_violation_max": viol, "max_displacement_mm": umax,
                   "peak_vm_MPa": float(np.nanmax(von_mises(stress))),
                   "lame_far_hoop_MPa": W.lame(params, r_far)[1].tolist()}
        series = {k: np.asarray(profiles["shell_long"][k], float) for k in ("s_mm", "vm_MPa")}
        return {"success": True, "message": f"CalculiX: {info['elements']} C3D10, {info['nodes']} nodes",
                "nfev": None, "series": series, "outputs": outputs, "files": files(), "cleanup": work}

    def tool_versions(self):
        return self._versions


def _local(vals, axes):
    from harness.linearize import rotate

    return rotate(vals, axes)


class PressureVesselStudy(Study):
    name = "pressure_vessel"
    models = {"cadquery_ccx_vessel": CadQueryCalculiXVessel}
    metrics = frozenset({"pm_general_MPa", "pl_max_MPa", "pq_max_MPa", "peak_vm_MPa"}
                        | {f"pl_{n}_MPa" for n in JUNCTION} | {f"pq_{n}_MPa" for n in JUNCTION})
    param_names = PARAMS
    series_file = "scl_shell_long.csv"
    compare_description = "max relative difference of the von Mises stress along the shell SCL"

    def derive(self, params):
        d = _W.dims(params)
        p, S = float(params["pressure_MPa"]), float(params["allowable_stress_MPa"])
        return {"hoop_membrane_pR_over_t_MPa": p * d["Ri"] / d["t"], "allowable_PL_MPa": 1.5 * S,
                "allowable_PS_MPa": 3.0 * S, "d_over_D": d["rni"] / d["Ri"],
                "sqrt_Rt_mm": float(np.sqrt((d["Ri"] + d["t"] / 2) * d["t"])),
                "pressure_area_mean_stress_MPa": pressure_area_stress(params)}

    def compute_metrics(self, series, params, case, outputs=None):
        L = outputs["lines"]
        out = {"pm_general_MPa": L["far"]["membrane_vm"], "peak_vm_MPa": outputs["peak_vm_MPa"]}
        for n in JUNCTION:
            out[f"pl_{n}_MPa"] = L[n]["membrane_vm"]
            out[f"pq_{n}_MPa"] = L[n]["membrane_plus_bending_vm"]
        out["pl_max_MPa"] = max(out[f"pl_{n}_MPa"] for n in JUNCTION)
        out["pq_max_MPa"] = max(out[f"pq_{n}_MPa"] for n in JUNCTION)
        return out

    def verify_point(self, case, point, pdir, series, backend):
        tol = case["verification"]
        p, out = point["parameters"], point["solver_outputs"]
        ex = out["expected"]
        far = out["lines"]["far"]
        prof = out["profiles"]["far"]
        hoop_fe_bore = abs(prof["local"][0][2])  # h-h at the bore (s = 0)
        hoop_lame_bore = out["lame_far_hoop_MPa"][0]
        d = _W.dims(p)
        pm_lame = _lame_linearized_pm(p)
        checks = [
            check("cad_valid", "CadQuery B-rep valid (0 = yes)", 0.0 if out["cad_valid"] else 1.0, 0.0),
            check("mesh_volume", "|mesh volume (straight-sided tets) - CAD volume| / CAD volume",
                  abs(out["mesh_volume_mm3"] - out["cad_volume_mm3"]) / out["cad_volume_mm3"], tol["volume_rel_tol"]),
            check("equilibrium_y", "|support reaction on y = 0 - exact pressure resultant (p x projected wetted area)| "
                  "/ resultant", abs(out["reaction_symy_N"][1] - ex["Ry_N"]) / abs(ex["Ry_N"]), tol["equilibrium_rel_tol"]),
            check("equilibrium_z", "|support reaction on z = 0 - exact resultant (end thrust + nozzle bore)| / resultant",
                  abs(out["reaction_symz_N"][2] - ex["Rz_N"]) / abs(ex["Rz_N"]), tol["equilibrium_rel_tol"]),
            check("self_balance_x", "|reaction at the single axial support| / quarter nozzle thrust (closed vessel: 0)",
                  abs(out["reaction_back_N"][0]) / ex["nozzle_thrust_scale_N"], tol["equilibrium_rel_tol"]),
            check("lame_bore_hoop", "|FE hoop stress at the bore on the far line - Lame| / Lame (exact)",
                  abs(hoop_fe_bore - hoop_lame_bore) / hoop_lame_bore, tol["lame_rel_tol"]),
            check("lame_membrane", "|FE linearised membrane (von Mises) on the far line - the same linearisation of "
                  "the Lame stresses| / Lame (exact)", abs(far["membrane_vm"] - pm_lame) / pm_lame, tol["lame_rel_tol"]),
            check("scl_inside_mesh", "max barycentric violation of the SCL sample points (0 = inside an element; points on "
                  "a curved surface lie about h^2 / 8R outside the straight-sided element, where the quadratic shape "
                  "functions extrapolate smoothly)", out["sample_violation_max"], tol["scl_violation_tol"], kind="validity"),
            check("small_displacement", "max displacement / shell thickness (linear geometry)",
                  out["max_displacement_mm"] / d["t"], 0.1, kind="validity"),
        ]
        vessel_figure(pdir / "response.png", out, point)
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "element_size_local_mm":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: float(pt["parameters"]["element_size_local_mm"]))
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(float(pt["parameters"]["element_size_local_mm"]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
        for metric in sorted({r["metric"] for r in case["requirements"]}):
            vals = tuple(pt["metrics"][metric] for pt in fine)
            u = discretization_uncertainty(hs, vals, design_order=2, noise_floor=tol.get("mesh_noise_rel", 1e-5))
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


def pressure_area_stress(p):
    """Design-by-rule cross-check, a simplified pressure-area balance (the idea of EN 13445-3 clause 9, our own
    simplified form, not the standard's full procedure): in the longitudinal section, the pressure on the fluid area
    within the reinforcement limits is carried by the metal within them, mean stress = p A_p / A_sigma, compared with
    the allowable S. Limits: along the shell sqrt((2 Ri + t) t) from the nozzle's outer surface, along the nozzle
    sqrt((2 rni + tn) tn) from the shell's outer surface; the weld fillet counted as a right triangle."""
    d = _W.dims(p)
    ls = np.sqrt((2 * d["Ri"] + d["t"]) * d["t"])
    ln = np.sqrt((2 * d["rni"] + d["tn"]) * d["tn"])
    a_p = d["Ri"] * (d["rno"] + ls) + d["rni"] * (d["t"] + ln)
    a_s = d["t"] * ls + d["tn"] * (d["t"] + ln) + 0.5 * d["rf"] ** 2
    return float(float(p["pressure_MPa"]) * a_p / a_s)


def _lame_linearized_pm(p):
    """Von Mises of the linearised membrane of the Lame stresses (radial, hoop, axial) through the wall."""
    d = _W.dims(p)
    r = np.linspace(d["Ri"], d["Ro"], 41)
    sr, sh, sa = _W.lame(p, r)
    st = np.zeros((41, 6))
    st[:, 0], st[:, 1], st[:, 2] = sr, sa, sh
    return linearize(r - d["Ri"], st, np.eye(3))["membrane_vm"]


def vessel_figure(path, out, point):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, _style, plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    fig.patch.set_facecolor(SURFACE)
    for ax, names in ((axes[0], ("shell_long", "shell_trans")), (axes[1], ("nozzle_long", "nozzle_trans"))):
        for name, col in zip(names, (SERIES_1, SERIES_2)):
            pr, ln = out["profiles"][name], out["lines"][name]
            s = np.asarray(pr["s_mm"])
            ax.plot(s, pr["vm_MPa"], "-", color=col, lw=1.5, label=f"{name}: von Mises")
            ax.axhline(ln["membrane_vm"], color=col, lw=0.8, ls="--")
            ax.annotate(f"PL {ln['membrane_vm']:.0f}, P+Q {ln['membrane_plus_bending_vm']:.0f} MPa", (s[-1], ln["membrane_vm"]),
                        fontsize=7, ha="right", va="bottom", color=col)
        ax.set_xlabel("distance through the wall (mm)")
        ax.set_ylabel("stress (MPa)")
        ax.legend(frameon=False, fontsize=8)
        _style(ax)
    fig.suptitle(f"{point['label']}: stress along the classification lines (dashed: linearised membrane)", fontsize=10,
                 color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = PressureVesselStudy()

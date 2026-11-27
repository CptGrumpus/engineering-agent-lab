"""Study 18 part 2: the nozzle by limit load (the method of ASME BPVC VIII-2 Part 5.2.3), which needs no
classification line: an elastic-perfectly plastic solid (yield 1.5 S), small displacement theory, the pressure ramped
until the solution no longer converges. The design passes if it carries 1.5 times the design pressure.

Model:     ccx_nozzle_limit (models/fea/nozzle_limit.py): part 1's CadQuery quarter model and mesh
           (models/fea/pressure_vessel.py), a plastic CalculiX deck with one step per load factor.
Metrics:   the collapse load factor (last converged load over the design load) and pressure; for the plain shell its
           ratio to the exact collapse pressure.
Reference: the plain closed-end cylinder (plain_shell = 1) against its exact collapse pressure (Hill); at every
           completed step, the reactions against the load factor times the exact pressure resultants; CAD and mesh
           volume. The collapse is a non-convergence: the reference shows that the solver's stop marks the true
           collapse load, not a numerical failure.
Run-level: GCI on the collapse load factor when the sweep is element_size_local_mm, against a noise floor declared in
           the case (the mesh is regenerated at each size: part 1 measured that scatter).
"""

from __future__ import annotations

import csv
import importlib.util
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

WRITER = "models/fea/nozzle_limit.py"
BASE_WRITER = "models/fea/pressure_vessel.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_NL = _load(Path(__file__).resolve().parent.parent / WRITER, "nozzle_limit_repo")
PARAMS = _NL.PARAMS


def frd_times(path: Path) -> list[float]:
    """The time of each result block in a CalculiX .frd file, in file order (the '100C' record of each block)."""
    out = []
    for ln in Path(path).read_text(encoding="latin-1").splitlines():
        if ln.startswith("  100C"):
            m = re.match(r"\s+100C\S*\s+\d+\s+(\S+)", ln)
            if m:
                out.append(float(m.group(1)))
    return out


class CalculiXNozzleLimit(Backend):
    sources = (WRITER, BASE_WRITER)

    def __init__(self):
        from studies.cantilever import find_freecadcmd

        bin_dir = find_freecadcmd().parent
        self.gmsh, self.ccx = bin_dir / "gmsh.exe", bin_dir / "ccx.exe"
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        import cadquery

        pv = _load(self.source_path(BASE_WRITER, source_dir), "pressure_vessel_saved")
        self.W = _load(self.source_path(WRITER, source_dir), "nozzle_limit_saved")
        self.W.pv = pv                                   # the saved copy of part 1's geometry and mesh
        g = subprocess.run([str(self.gmsh), "--version"], capture_output=True, text=True, timeout=60)
        c = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"cadquery": cadquery.__version__, "gmsh": (g.stdout + g.stderr).strip().splitlines()[-1],
                          "CalculiX": (c.stdout.strip().splitlines() or ["?"])[-1]}

    def solve(self, params, numerics, tolerance_scale=1.0):
        W = self.W
        work = Path(tempfile.mkdtemp(prefix="nozlim_"))
        keep = ("vessel.step", "mesh.geo", "job.inp", "job.dat", "job.sta", "gmsh.log", "ccx.log", "plastic_zone.csv")

        def files():
            return {n: work / n for n in keep if (work / n).exists()}

        try:
            cad = W.build_step(params, work / "vessel.step")
            W.pv.write_geo(params, work / "mesh.geo")
            g = subprocess.run([str(self.gmsh), "mesh.geo", "-3", "-format", "inp", "-o", "mesh.inp"], cwd=work,
                               capture_output=True, text=True, timeout=3600)
            (work / "gmsh.log").write_text(g.stdout + g.stderr, encoding="utf-8")
            if g.returncode != 0 or not (work / "mesh.inp").exists():
                return failed(f"gmsh failed (exit {g.returncode})") | {"files": files(), "cleanup": work}
            info = W.write_deck(params, work / "mesh.inp", work / "job.inp")
            threads = str(int(numerics.get("threads", 8)))
            env = dict(os.environ, OMP_NUM_THREADS=threads, CCX_NPROC_EQUATION_SOLVER=threads)
            c = subprocess.run([str(self.ccx), "-i", "job"], cwd=work, capture_output=True, text=True, env=env,
                               timeout=float(numerics.get("solver_timeout_s", 14400)))
            log = c.stdout + c.stderr
            (work / "ccx.log").write_text(log, encoding="utf-8")
            sched = W.schedule(params)
            hist = W.read_history(work / "job.dat", work / "job.sta", sched)
            if not hist["lambda"]:
                return failed(f"CalculiX completed no step (exit {c.returncode})") | {"files": files(), "cleanup": work}
            ids, xyz, eids, elems = W.pv.read_mesh(work / "mesh.inp")
            zone = self._plastic_zone(work, ids, xyz, sched)
        except Exception as e:  # noqa: BLE001
            return failed(f"{type(e).__name__}: {e}") | {"files": files(), "cleanup": work}

        row = {int(n): k for k, n in enumerate(ids)}
        corner = xyz[np.vectorize(row.get)(elems[:, :4])]
        mesh_vol = float(np.sum(np.abs(np.einsum("ij,ij->i", corner[:, 1] - corner[:, 0],
                                                 np.cross(corner[:, 2] - corner[:, 0], corner[:, 3] - corner[:, 0]))) / 6))
        lam_c = hist["collapse_load_factor"]
        outputs = {**info, **{f"cad_{k}": v for k, v in cad.items()}, "mesh_volume_mm3": mesh_vol,
                   "expected": W.expected_reactions(params), "schedule": sched, "history": hist,
                   "collapse_load_factor": lam_c, "ccx_exit": c.returncode,
                   "ccx_stopped_on_min_increment": "increment size smaller than minimum" in log,
                   "cylinder_collapse_pressure_MPa": W.collapse_pressure_cylinder(params),
                   "yield_MPa": W.yield_stress(params), **zone}
        series = {"lambda": np.asarray(hist["lambda"]), "u_toe_mm": np.asarray(hist["u_toe_mm"]),
                  "u_crotch_mm": np.asarray(hist["u_crotch_mm"]), "u_far_mm": np.asarray(hist["u_far_mm"])}
        msg = (f"CalculiX: {info['elements']} C3D10, {info['nodes']} nodes; "
               + (f"collapse at load factor {lam_c:.4f}" if lam_c else "no collapse up to load_factor_max"))
        return {"success": True, "message": msg, "nfev": None, "series": series, "outputs": outputs,
                "files": files(), "cleanup": work}

    @staticmethod
    def _plastic_zone(work: Path, ids, xyz, sched: list) -> dict:
        """The equivalent plastic strain at load factor 1.5 (the first written field) and at the last completed step
        (CalculiX writes only displacements at the stop), saved for the nodes yielded by then (plastic_zone.csv)."""
        frd = read_frd(work / "job.frd")
        times = frd_times(work / "job.frd")
        blocks = frd.get("blocks", [])
        pe = [(t, b) for t, (name, b) in zip(times, blocks) if name.upper().startswith("PE")]
        if not pe:
            return {"plastic_zone_nodes": 0}
        (t15, first), (tl, last) = pe[0], pe[-1]
        lam = lambda t: sched[int(round(t)) - 1]  # noqa: E731 - a step's total time at its end is its number
        k = [c for c in first if c != "ids"][0]
        m15 = dict(zip(first["ids"].tolist(), first[k].tolist()))
        mst = dict(zip(last["ids"].tolist(), last[k].tolist()))
        # saved: the yielded nodes on the two symmetry cut faces (y = 0, z = 0), the sections a figure shows
        rows = [(int(n), x, y, z, m15.get(int(n), 0.0), mst[int(n)]) for n, (x, y, z) in zip(ids, xyz)
                if mst.get(int(n), 0.0) > 1e-7 and min(abs(y), abs(z)) < 1e-6]
        with open(work / "plastic_zone.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["node", "x_mm", "y_mm", "z_mm", f"peeq_at_{lam(t15):g}", f"peeq_at_{lam(tl):g}"])
            for r in rows:
                w.writerow([r[0]] + [f"{v:.6g}" for v in r[1:]])
        return {"plastic_zone_nodes": len(rows), "peeq_fields_load_factors": [lam(t15), lam(tl)],
                "peeq_max_at_1p5": float(max(m15.values(), default=0.0)),
                "peeq_max_at_last_step": float(max(mst.values(), default=0.0)),
                "yielded_nodes_at_1p5": int(sum(v > 1e-7 for v in m15.values())),
                "yielded_nodes_at_last_step": int(sum(v > 1e-7 for v in mst.values()))}

    def tool_versions(self):
        return self._versions


class NozzleLimitStudy(Study):
    name = "nozzle_limit"
    models = {"ccx_nozzle_limit": CalculiXNozzleLimit}
    metrics = frozenset({"collapse_load_factor", "collapse_pressure_MPa", "collapse_over_cylinder"})
    param_names = PARAMS
    series_file = "load_history.csv"
    compare_description = "max relative difference of the toe displacement along the load history"

    def derive(self, params):
        return {"yield_1p5S_MPa": _NL.yield_stress(params),
                "cylinder_collapse_pressure_MPa": _NL.collapse_pressure_cylinder(params),
                "cylinder_collapse_load_factor": _NL.collapse_pressure_cylinder(params) / float(params["pressure_MPa"]),
                "required_load_factor": 1.5, "schedule": _NL.schedule(params)}

    def compute_metrics(self, series, params, case, outputs=None):
        lam = outputs["collapse_load_factor"]
        if lam is None:                      # no collapse below load_factor_max: report the bound
            lam = float(params["load_factor_max"])
        p = float(params["pressure_MPa"])
        return {"collapse_load_factor": lam, "collapse_pressure_MPa": lam * p,
                "collapse_over_cylinder": lam * p / outputs["cylinder_collapse_pressure_MPa"]}

    def verify_point(self, case, point, pdir, series, backend):
        tol = case["verification"]
        p, out = point["parameters"], point["solver_outputs"]
        h, ex = out["history"], out["expected"]
        lam = np.asarray(h["lambda"])
        ey = np.max(np.abs(np.asarray(h["Ry_N"]) / (lam * ex["Ry_N"]) - 1))
        ez = np.max(np.abs(np.asarray(h["Rz_N"]) / (lam * ex["Rz_N"]) - 1))
        ex_ = np.max(np.abs(np.asarray(h["Rx_back_N"])) / (lam * ex["nozzle_thrust_scale_N"]))
        plain = bool(float(p.get("plain_shell", 0)))
        checks = [
            check("cad_valid", "CadQuery B-rep valid (0 = yes)", 0.0 if out["cad_valid"] else 1.0, 0.0),
            check("mesh_volume", "|mesh volume (straight-sided tets) - CAD volume| / CAD volume",
                  abs(out["mesh_volume_mm3"] - out["cad_volume_mm3"]) / out["cad_volume_mm3"], tol["volume_rel_tol"]),
            check("equilibrium_y", "max over the completed steps of |reaction on y = 0 / (load factor x exact "
                  "resultant) - 1|", float(ey), tol["equilibrium_rel_tol"]),
            check("equilibrium_z", "max over the completed steps of |reaction on z = 0 / (load factor x exact "
                  "resultant) - 1|", float(ez), tol["equilibrium_rel_tol"]),
            check("self_balance_x", "max over the completed steps of |reaction at the single axial support| / (load "
                  "factor x quarter nozzle thrust) (a closed vessel: 0)", float(ex_), tol["equilibrium_rel_tol"]),
            check("collapse_found", "the analysis stopped on non-convergence below load_factor_max (0 = yes): the "
                  "collapse load is bracketed", 0.0 if out["collapse_load_factor"] and out["ccx_stopped_on_min_increment"]
                  else 1.0, 0.0, kind="validity"),
            check("passed_code_load", "the step to load factor 1.5 completed (0 = yes)",
                  0.0 if 1.5 in [round(v, 9) for v in h["lambda"]] else 1.0, 0.0, kind="validity"),
        ]
        if plain:
            pc = (out["collapse_load_factor"] or float("nan")) * float(p["pressure_MPa"])
            checks.append(check("cylinder_exact", "|collapse pressure - exact closed-end cylinder (2 / sqrt 3) "
                                "sigma_y ln(Ro / Ri)| / exact", abs(pc / out["cylinder_collapse_pressure_MPa"] - 1),
                                tol["cylinder_rel_tol"]))
            checks.append(check("cad_hand_volume", "|CAD volume - hand volume| / hand volume (exact for the plain "
                                "shell)", abs(out["cad_volume_mm3"] / out["cad_volume_hand_mm3"] - 1), 1e-9))
        limit_figure(pdir / "response.png", out, point)
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
            u = discretization_uncertainty(hs, vals, design_order=2, noise_floor=tol["mesh_noise_rel"])
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


def limit_figure(path, out, point):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2, _style, plt

    h = out["history"]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    fig.patch.set_facecolor(SURFACE)
    for key, col, lab in (("u_crotch_mm", SERIES_1, "crotch corner"), ("u_toe_mm", SERIES_2, "weld toe"),
                          ("u_far_mm", TEXT_2, "far shell")):
        ax.plot([0] + h[key], [0] + h["lambda"], "o-", color=col, ms=3, lw=1.4, label=lab)
    ax.axhline(1.5, color=TEXT, lw=0.8, ls=":")
    ax.annotate("required: 1.5 x design pressure", (0, 1.5), fontsize=7, va="bottom", color=TEXT)
    lam_c = out["collapse_load_factor"]
    if lam_c:
        ax.axhline(lam_c, color=SERIES_1, lw=0.8, ls="--")
        ax.annotate(f"collapse: {lam_c:.3f}", (0, lam_c), fontsize=7, va="bottom", color=SERIES_1)
    ax.set_xlabel("displacement (mm)")
    ax.set_ylabel("load factor (pressure / design pressure)")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    _style(ax)
    fig.suptitle(f"{point['label']}: limit load, elastic-perfectly plastic (yield {out['yield_MPa']:.0f} MPa)",
                 fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = NozzleLimitStudy()

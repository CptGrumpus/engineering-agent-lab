"""Study 23 part 2: the fan rotor as a 3D solid against the beam model its verdict rests on, with the real rotor's
detail added one feature at a time (hub, bearing journals).

Model:     ccx_rotor_solid (models/fea/rotor_solid.py): CadQuery half solid -> Gmsh C3D10 -> CalculiX *FREQUENCY, the
           bearings as point springs on rigid end faces; and, on the same parameters, the ROSS rotor of part 1
           (models/rotor/fan_rotor.py, in its own environment), now with the optional hub and journals.
Metrics:   the first lateral natural frequency at rest from each (Hz) and their ratio; ROSS's first forward critical
           speed (Campbell 1x crossing, gyroscopic) and the same corrected by the solid's at-rest ratio; the margin of
           the corrected critical over the top running speed (REQ-R1 of part 1: at least 15 %).
Reference: ROSS at rest on the identical rotor (cross-tool); the solid's volume against a hand volume; mesh quality.
Run-level: discretization uncertainty of the solid's frequency over mesh_scale.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness.backend_base import Backend, failed
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study
from studies.rotor_critical import PARAMS as ROSS_PARAMS, ross_python

WRITER = "models/fea/rotor_solid.py"
RUNNER = "models/rotor/fan_rotor.py"
DETAIL = ("hub_diameter_m", "hub_length_m", "journal_diameter_m", "journal_length_m")
PARAMS = ROSS_PARAMS + DETAIL + ("element_size_mm", "mesh_scale")


def _writer(path: Path):
    spec = importlib.util.spec_from_file_location("rotor_solid_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CalculiXRotorSolid(Backend):
    sources = (WRITER, RUNNER)

    def __init__(self):
        from studies.cantilever import find_freecadcmd

        self.ccx = find_freecadcmd().parent / "ccx.exe"
        self.python = ross_python()
        self.rs = None
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        import cadquery
        import gmsh

        self.rs = _writer(self.source_path(WRITER, source_dir))
        self.runner = self.source_path(RUNNER, source_dir)
        c = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        v = subprocess.run([str(self.python), "-c", "import warnings; warnings.filterwarnings('ignore'); import ross; "
                            "print(ross.__version__)"], capture_output=True, text=True, timeout=300)
        self._versions = {"cadquery": cadquery.__version__, "gmsh (Python API)": gmsh.__version__,
                          "calculix": (c.stdout + c.stderr).strip().splitlines()[-1],
                          "ross": v.stdout.strip().splitlines()[-1] if v.stdout.strip() else "?"}

    def solve(self, params, numerics, tolerance_scale=1.0):
        rs, p = self.rs, params
        work = Path(tempfile.mkdtemp(prefix="rotor_solid_"))
        try:
            opt = {k: p[k] for k in DETAIL if p.get(k) not in (None, "", 0, 0.0)}
            (work / "params.json").write_text(json.dumps({k: p[k] for k in ROSS_PARAMS} | opt), encoding="utf-8")
            r = subprocess.run([str(self.python), str(self.runner), "params.json", "ross.json"], cwd=work,
                               capture_output=True, text=True, timeout=float(numerics.get("solver_timeout_s", 1800)))
            if r.returncode != 0:
                raise RuntimeError(f"ROSS failed: {r.stderr[-400:]}")
            ross = json.loads((work / "ross.json").read_text(encoding="utf-8"))
            cad = rs.build_cad(p, work / "rotor.step")
            mesh = rs.build_mesh(work / "rotor.step", work / "mesh.inp",
                                 h=float(p["element_size_mm"]) * float(p["mesh_scale"]))
            info = rs.write_deck(p, work / "mesh.inp", work / "rotor.inp", modes=int(numerics.get("solid_modes", 6)))
            c = subprocess.run([str(self.ccx), "-i", "rotor"], cwd=work, capture_output=True, text=True,
                               timeout=float(numerics.get("solve_timeout_s", 3600)))
            if c.returncode != 0 or "Job finished" not in c.stdout:
                raise RuntimeError(f"CalculiX failed (exit {c.returncode})")
            f_solid = rs.read_frequencies(work / "rotor.dat")
        except (RuntimeError, subprocess.TimeoutExpired, ValueError) as e:
            return failed(f"{type(e).__name__}: {e}") | {"cleanup": work}
        fwd = [c_["rpm"] for c_ in ross["critical_speeds"] if c_["whirl"] == "forward"]
        out = {"cad": cad, "mesh": mesh, "nodes": info["nodes"], "solid_hz": f_solid,
               "ross_0rpm_hz": ross["frequency_0rpm_hz"], "ross_first_forward_critical_rpm": fwd[0] if fwd else None,
               "ross_rotor_mass_kg": ross["rotor_mass_kg"], "speed_max_rpm": float(p["speed_max_rpm"])}
        series = {"mode": np.arange(1, len(f_solid) + 1, dtype=float), "solid_hz": np.asarray(f_solid)}
        return {"success": True, "message": f"{info['nodes']} nodes; solid {f_solid[0]:.3f} Hz, ROSS "
                f"{ross['frequency_0rpm_hz'][0]:.3f} Hz", "nfev": 2, "series": series, "outputs": out, "files": {},
                "cleanup": work}

    def tool_versions(self):
        return self._versions


class RotorSolidStudy(Study):
    name = "rotor_solid"
    models = {"ccx_rotor_solid": CalculiXRotorSolid}
    metrics = frozenset({"solid_f1_hz", "ross_f1_hz", "solid_over_ross", "ross_critical_rpm", "corrected_critical_rpm",
                         "corrected_margin_pct"})
    param_names = PARAMS
    series_file = "frequencies.csv"

    def derive(self, params):
        return {}

    def compute_metrics(self, series, params, case, outputs=None):
        o = outputs
        f_s, f_r = o["solid_hz"][0], o["ross_0rpm_hz"][0]
        crit = o["ross_first_forward_critical_rpm"]
        corr = crit * f_s / f_r if crit else float("nan")
        return {"solid_f1_hz": f_s, "ross_f1_hz": f_r, "solid_over_ross": f_s / f_r, "ross_critical_rpm": crit,
                "corrected_critical_rpm": corr, "corrected_margin_pct": 100 * (corr / o["speed_max_rpm"] - 1)}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        out, m = point["solver_outputs"], point["metrics"]
        checks = [check("cad_volume", "|half solid's volume / hand volume - 1|",
                        abs(out["cad"]["volume_mm3"] / out["cad"]["hand_volume_mm3"] - 1), tol["volume_rel_tol"]),
                  check("mesh_quality", f"{tol['min_scaled_jacobian']} - the smallest scaled Jacobian",
                        float(tol["min_scaled_jacobian"]) - out["mesh"]["min_scaled_jacobian"], 0.0, kind="validity")]
        if float(tol.get("ross_rel_tol", 0) or 0) > 0:
            checks.append(check("solid_vs_ross", "|solid's first lateral frequency at rest / ROSS's - 1| (cross-tool: "
                                "on the rotor ROSS idealises exactly, the beam model must agree)",
                                abs(m["solid_over_ross"] - 1), tol["ross_rel_tol"]))
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "mesh_scale":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: float(pt["parameters"]["mesh_scale"]))
        if len(done) < 3:
            return [check("mesh_gci", "needs >= 3 completed mesh levels", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(float(pt["parameters"]["mesh_scale"]) for pt in fine)
        u = discretization_uncertainty(hs, tuple(pt["metrics"]["solid_f1_hz"] for pt in fine), design_order=2,
                                       noise_floor=float(tol.get("mesh_noise_rel", 1e-5)))
        return [check("discretization_solid_f1", f"relative discretization uncertainty of the solid's f1, "
                      f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": "solid_f1_hz"}], \
            {"levels_used": [pt["label"] for pt in fine], "solid_f1_hz": u}


STUDY = RotorSolidStudy()

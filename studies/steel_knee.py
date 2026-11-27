"""Steel frame study, part 2: the portal's knee (beam to column flange, bolted flange-plated moment connection) as a
3D solid, for its rotational stiffness: is the rigid knee of the frame analysis right?

Model:     ccx_knee (models/fea/moment_connection.py): CadQuery half solid (column and beam stubs with root fillets,
           flange plates, shear tab, continuity plates; bonded) -> Gmsh C3D10 -> CalculiX; column clamped at its base,
           a shear load at the beam's tip.
Metrics:   knee_stiffness_ratio: k L / EI of the spring that, put at the beam's end in the frame's centreline model,
           gives the solid's rotation between a beam section and a column section clear of the joint (L the bay span,
           EI the beam's, tabulated Ix); the same from a second, farther pair of sections; aisc_index_ratio: AISC
           Commentary B3.4b's Ks L / EI (the beam at the column face against the column at the joint's bottom).
Reference: beam theory between two sections of each member (the solid's own section Ix: the root fillets from kdes
           give 0.3-0.8 % less than the tabulated value); the CAD volume against a hand volume; equilibrium of the
           base reactions with the tip load (forces and moment).
Run-level: discretization uncertainty of both ratios over mesh_scale (h_joint and h_far scaled together).
"""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness.backend_base import Backend, failed
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study

WRITER = "models/fea/moment_connection.py"
PARAMS = ("column_shape", "beam_shape", "youngs_modulus_MPa", "poisson_ratio", "plate_thickness_mm",
          "plate_width_mm", "plate_length_mm", "setback_mm", "tab_width_mm", "tab_height_mm", "tab_thickness_mm",
          "continuity_plate_thickness_mm", "column_length_mm", "beam_length_mm", "tip_load_kN", "bay_span_mm",
          "joint_size_mm", "far_size_mm", "mesh_scale", "station_near_mm", "station_far_mm")


def _writer(path: Path):
    spec = importlib.util.spec_from_file_location("moment_connection_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CalculiXKnee(Backend):
    sources = (WRITER,)

    def __init__(self):
        from studies.cantilever import find_freecadcmd

        self.ccx = find_freecadcmd().parent / "ccx.exe"
        if not self.ccx.exists():
            raise RuntimeError("ccx.exe not found next to freecadcmd")
        self.mc = None
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        import cadquery
        import gmsh

        self.mc = _writer(self.source_path(WRITER, source_dir))
        c = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"cadquery": cadquery.__version__, "gmsh (Python API)": gmsh.__version__,
                          "calculix": (c.stdout + c.stderr).strip().splitlines()[-1]}

    def solve(self, params, numerics, tolerance_scale=1.0):
        from harness.calculix import read_frd
        from models.fea import shaft_fillet_ccx as sf

        mc, p = self.mc, params
        work = Path(tempfile.mkdtemp(prefix="knee_"))
        s = float(p["mesh_scale"])
        try:
            cad = mc.build_cad(p, work / "knee.step")
            mesh = mc.build_mesh(p, work / "knee.step", work / "mesh.inp", h_joint=s * float(p["joint_size_mm"]),
                                 h_far=s * float(p["far_size_mm"]))
            info = mc.write_deck(p, work / "mesh.inp", work / "knee.inp")
            r = subprocess.run([str(self.ccx), "-i", "knee"], cwd=work, capture_output=True, text=True,
                               timeout=float(numerics.get("solve_timeout_s", 7200)))
            (work / "knee.log").write_text(r.stdout + r.stderr, encoding="utf-8")
            if r.returncode != 0 or "Job finished" not in r.stdout:
                raise RuntimeError(f"CalculiX failed (exit {r.returncode})")
            fr = read_frd(work / "knee.frd")
            rf = sf.read_node_forces(work / "knee.dat")
        except (RuntimeError, subprocess.TimeoutExpired, ValueError) as e:
            return failed(f"{type(e).__name__}: {e}") | {"cleanup": work}
        g = mc.dims(p)
        U = fr["DISP"]
        row = {int(n): k for k, n in enumerate(fr["nodes"])}
        X = fr["coords"][[row[int(n)] for n in U["ids"]]]
        Uv = np.column_stack([U["D1"], U["D2"], U["D3"]])
        hw = 0.6 * s * float(p["far_size_mm"])             # slab half-width for the section fits
        near, far = float(p["station_near_mm"]), float(p["station_far_mm"])
        st = {"beam_near": ("beam", g["face"] + g["Lp"] + near), "beam_far": ("beam", g["face"] + g["Lp"] + far),
              "col_near": ("column", g["y_plate_bot"] - near), "col_far": ("column", g["y_plate_bot"] - far)}
        rot = {k: mc.section_rotation(X, Uv, ax, at, hw) | {"at": at} for k, (ax, at) in st.items()}
        E = float(p["youngs_modulus_MPa"])
        EI_L = E * g["beam"]["Ix"] / float(p["bay_span_mm"])   # the frame's beam: tabulated Ix
        ks = {}
        for tag in ("near", "far"):
            th = mc.centreline_rotations(p, rot[f"beam_{tag}"]["at"], rot[f"col_{tag}"]["at"])
            fe = abs(rot[f"beam_{tag}"]["theta"] - rot[f"col_{tag}"]["theta"])
            extra = fe - th["beam"] - th["column"]
            ix = mc.aisc_index(p, rot[f"beam_{tag}"]["theta"], rot[f"beam_{tag}"]["at"], rot[f"col_{tag}"]["theta"],
                               rot[f"col_{tag}"]["at"])
            ks[tag] = {"fe_rotation": fe, "centreline_rotation": th["beam"] + th["column"], "extra_rotation": extra,
                       "k_Nmm_per_rad": th["M_joint_Nmm"] / extra, "ratio": th["M_joint_Nmm"] / extra / EI_L,
                       "aisc_index_ratio": ix["Ks_Nmm_per_rad"] / EI_L, "aisc_theta": ix["theta_rad"]}
        # beam theory between the near and far sections of each member (the solid's own Ix)
        tn = mc.centreline_rotations(p, rot["beam_near"]["at"], rot["col_near"]["at"])
        tf_ = mc.centreline_rotations(p, rot["beam_far"]["at"], rot["col_far"]["at"])
        bt = {"beam": (abs(rot["beam_far"]["theta"] - rot["beam_near"]["theta"]), tf_["beam"] - tn["beam"]),
              "column": (abs(rot["col_near"]["theta"] - rot["col_far"]["theta"]), tf_["column"] - tn["column"])}
        # equilibrium: base reactions against the tip load (half model), forces and moment about the origin
        ids = np.array(list(rf))
        R = np.array([rf[n] for n in ids])
        P_half = float(p["tip_load_kN"]) * 1e3 / 2
        Xr = fr["coords"][[row[int(n)] for n in ids]]
        m_react = float((Xr[:, 0] * R[:, 1] - Xr[:, 1] * R[:, 0]).sum())
        eq = {"force": abs(R[:, 1].sum() - P_half) / P_half, "moment": abs(m_react - P_half * g["x_tip"])
              / (P_half * g["x_tip"]), "applied_N": info["applied_force_N"]}
        out = {"cad": cad, "mesh": mesh, "nodes": info["nodes"], "rotations": rot, "stiffness": ks,
               "beam_theory": {k: {"fe": a, "theory": b} for k, (a, b) in bt.items()}, "equilibrium": eq,
               "EI_over_L_Nmm": EI_L}
        series = {"case": np.array([0.0]), "knee_stiffness_ratio": np.array([ks["near"]["ratio"]])}
        return {"success": True, "message": f"{info['nodes']} nodes; k L/EI {ks['near']['ratio']:.2f}, AISC index "
                f"{ks['near']['aisc_index_ratio']:.2f}", "nfev": 1, "series": series, "outputs": out, "files": {},
                "cleanup": work}

    def tool_versions(self):
        return self._versions


class SteelKneeStudy(Study):
    name = "steel_knee"
    models = {"ccx_knee": CalculiXKnee}
    metrics = frozenset({"knee_stiffness_ratio", "knee_stiffness_ratio_far", "aisc_index_ratio"})
    param_names = PARAMS
    series_file = "knee.csv"

    def derive(self, params):
        return {}

    def compute_metrics(self, series, params, case, outputs=None):
        k = outputs["stiffness"]
        return {"knee_stiffness_ratio": k["near"]["ratio"], "knee_stiffness_ratio_far": k["far"]["ratio"],
                "aisc_index_ratio": k["near"]["aisc_index_ratio"]}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        out, m = point["solver_outputs"], point["metrics"]
        checks = [check("cad_volume", "|CAD volume / hand volume - 1| (stubs, plates, tab, continuity plates)",
                        abs(out["cad"]["volume_mm3"] / out["cad"]["hand_volume_mm3"] - 1), tol["volume_rel_tol"])]
        for member, v in out["beam_theory"].items():
            checks.append(check(f"beam_theory_{member}", f"{member}: rotation between its near and far sections "
                                "against beam theory with the solid's own section Ix", abs(v["fe"] / v["theory"] - 1),
                                tol["beam_theory_rel_tol"]))
        eq = out["equilibrium"]
        checks.append(check("equilibrium_force", "|base reaction - tip load| / tip load", eq["force"],
                            tol["equilibrium_rel_tol"]))
        checks.append(check("equilibrium_moment", "|base reaction moment - tip load x lever| / that moment",
                            eq["moment"], tol["equilibrium_rel_tol"]))
        checks.append(check("stations_agree", "k L / EI from the near against the far pair of sections (the joint's "
                            "extra rotation is local, so both must give it)",
                            abs(m["knee_stiffness_ratio_far"] / m["knee_stiffness_ratio"] - 1), tol["stations_rel_tol"]))
        checks.append(check("mesh_quality", f"{tol['min_scaled_jacobian']} - the smallest scaled Jacobian (at or "
                            "below 0: every element above the threshold)",
                            float(tol["min_scaled_jacobian"]) - out["mesh"]["min_scaled_jacobian"], 0.0,
                            kind="validity"))
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
        checks, detail = [], {"levels_used": [pt["label"] for pt in fine]}
        nf = tol.get("mesh_noise_rel", 1e-5)
        for metric in ("knee_stiffness_ratio", "aisc_index_ratio"):
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine), design_order=2,
                                           noise_floor=float(nf[metric] if isinstance(nf, dict) else nf))
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


STUDY = SteelKneeStudy()

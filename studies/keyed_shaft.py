"""Study 26 part 2: the gear seat of the part 1 shaft with its keyway: Kt at the keyway and at the shoulder fillet,
fatigue and overload safety at both (Shigley, as part 1).

Model:     ccx_keyed_shaft (models/fea/keyed_shaft.py): CadQuery half shaft with a DIN 6885 end-milled keyway ->
           STEP -> Gmsh C3D10 -> CalculiX; a coarse global model (bending and torsion) drives three fine submodels:
           the keyway's end at the shoulder together with the fillet ("near"), the keyway's far end ("far") and its
           middle ("middle"). Without a keyway (key_width_mm = 0) only the global model and the fillet submodel run.
Reference: part 1's verified fillet Kt (the keyless case through the same global-submodel path); Le and Le (ASEE
           2013) for an isolated profile keyseat at ANSI proportions (its own case); global against submodel at
           the fillet, where the global mesh resolves it; equilibrium of the global model
Run-level: GCI on the Kt values and the safety factors when the sweep is mesh_scale (all fine sizes x the factor)
"""

from __future__ import annotations

import importlib.util
import math
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from harness.backend_base import Backend, failed
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study
from validation import shaft_fatigue as ref

WRITER = "models/fea/keyed_shaft.py"
PARAMS = ("D_mm", "d_mm", "fillet_radius_mm", "small_length_mm", "large_length_mm", "bending_moment_Nm", "torque_Nm",
          "youngs_modulus_MPa", "poisson_ratio", "ultimate_MPa", "yield_MPa", "overload_factor", "key_width_mm",
          "key_depth_mm", "key_corner_radius_mm", "key_gap_mm", "key_length_mm", "global_key_size_mm",
          "global_fillet_size_mm", "far_size_mm", "sub_key_size_rel", "sub_fillet_size_mm", "mesh_scale",
          "box_margin_mm")
LOADS = ("bending", "torsion")


def _writer(path: Path):
    spec = importlib.util.spec_from_file_location("keyed_shaft_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def boxes(ks, p: dict) -> dict:
    """The submodel boxes (x0, x1, y0, y1, z0, z1): each cut face 3-4 mm or more from the feature it surrounds.
    "fillet*": the shoulder fillet. Keyless, the shaft is axisymmetric and a sector 8 mm wide at +x holds both peaks
    (bending at +x, torsion anywhere); keyed, the whole half ring, because the keyway moves the peaks: bending to
    about 27 deg from the keyway, torsion to the far side (the keyed seat is weaker in torsion, which raises the
    shear on the side away from it; run 20261127-000418, d40). The half ring is two quarter rings (x >= 0, x <= 0):
    as one box it is 330 k nodes at scale 0.8 and 570 k at 0.64, past what SPOOLES solves."""
    g = ks.dims(p)
    x_out = g["D"] / 2 + 1.0                         # beyond the surface: not a cut
    if "B" not in g:
        return {"fillet": (g["R"] - 6.0, x_out, 0.0, 8.0, g["zc"] - 6.0, g["zs"] + 5.0)}
    m = float(p.get("box_margin_mm", 3.0))           # clear distance from the keyway's corner to the cut faces
    x0 = g["R"] - g["t1"] - m
    y1 = g["B"] / 2 + m
    zm = 0.5 * (g["z_k0"] + g["z_k1"])
    return {"fillet_a": (0.0, x_out, 0.0, x_out, g["zc"] - m, g["zs"] + m),
            "fillet_b": (-x_out, 0.0, 0.0, x_out, g["zc"] - m, g["zs"] + m),
            "near": (x0, x_out, 0.0, y1, g["z_k1"] - g["B"] / 2 - m - 1.0, g["zs"] + m),
            "far": (x0, x_out, 0.0, y1, g["z_k0"] - m, g["z_k0"] + g["B"] / 2 + m + 1.0),
            "middle": (x0, x_out, 0.0, y1, zm - m - 1.0, zm + m + 1.0)}


class CalculiXKeyedShaft(Backend):
    sources = (WRITER,)

    def __init__(self):
        from studies.cantilever import find_freecadcmd

        self.ccx = find_freecadcmd().parent / "ccx.exe"
        if not self.ccx.exists():
            raise RuntimeError("ccx.exe not found next to freecadcmd")
        self.ks = None
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        import cadquery
        import gmsh

        self.ks = _writer(self.source_path(WRITER, source_dir))
        c = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"cadquery": cadquery.__version__, "gmsh (Python API)": gmsh.__version__,
                          "calculix": (c.stdout + c.stderr).strip().splitlines()[-1]}

    def _ccx(self, work: Path, name: str, timeout: float):
        r = subprocess.run([str(self.ccx), "-i", name], cwd=work, capture_output=True, text=True, timeout=timeout)
        (work / f"{name}.log").write_text(r.stdout + r.stderr, encoding="utf-8")
        if r.returncode != 0 or "Job finished" not in r.stdout:
            raise RuntimeError(f"CalculiX failed: {work.name}/{name} (exit {r.returncode})")

    def _peaks(self, frd: Path, p: dict, load: str, box=None, skip: float = 0.0) -> dict:
        from harness.calculix import read_frd

        fr = read_frd(frd)
        S = fr["STRESS"]
        row = {int(n): k for k, n in enumerate(fr["nodes"])}
        X = fr["coords"][[row[int(n)] for n in S["ids"]]]
        return self.ks.region_peaks(p, X, self.ks.principal(S), load, szz=np.asarray(S["SZZ"]), box=box, skip=skip)

    def solve(self, params, numerics, tolerance_scale=1.0):
        ks, p = self.ks, params
        work = Path(tempfile.mkdtemp(prefix="keyed_"))
        s = float(p["mesh_scale"])
        rk = float(p.get("key_corner_radius_mm", 0) or 0)
        timeout = float(numerics.get("solve_timeout_s", 7200))
        skip = float(numerics.get("driven_skip_mm", 1.0))     # peaks are not read this close to a driven face
        h_sub_far = float(p.get("sub_far_size_mm", 1.5))
        # the global keyway size at most 0.75 r_k: one quadratic element across a smaller corner arc inverts
        # (rk 0.25 at 0.3 mm: 6 inverted elements, run 20261127-000418)
        h_key_global = min(float(p["global_key_size_mm"]), 0.75 * rk) if rk > 0 else float(p["global_key_size_mm"])
        try:
            gm = {"cad": ks.build_cad(p, work / "global.step")}
            gm["mesh"] = ks.build_mesh(p, work / "global.step", work / "global_mesh.inp",
                                       h_key=h_key_global, h_fillet=float(p["global_fillet_size_mm"]),
                                       h_far=float(p["far_size_mm"]), growth=0.4, band_deg=180.0)
            info = {}
            for load in LOADS:
                (work / load).mkdir()
                info[("global", load)] = ks.write_deck(p, work / "global_mesh.inp", work / load / "global.inp", load)
            with ThreadPoolExecutor(max_workers=2) as ex:
                list(ex.map(lambda ld: self._ccx(work / ld, "global", timeout), LOADS))
            subs = {}
            for name, box in boxes(ks, p).items():
                subs[name] = {"box": box, "cad": ks.build_cad(p, work / f"{name}.step", box=box)}
                # the fillet box holds the keyway's end too, but no keyway peak is read from it: coarser there
                fil = name.startswith("fillet")
                hk = min(s * 0.3, 0.75 * rk) if fil else s * float(p["sub_key_size_rel"]) * max(rk, 1e-9)
                subs[name]["mesh"] = ks.build_mesh(p, work / f"{name}.step", work / f"{name}_mesh.inp", h_key=hk,
                                                   h_fillet=s * float(p["sub_fillet_size_mm"]), h_far=h_sub_far,
                                                   growth=0.45, band_deg=180.0 if fil else 60.0)
                for load in LOADS:
                    info[(name, load)] = ks.write_deck(p, work / f"{name}_mesh.inp", work / load / f"{name}.inp", load,
                                                       box=box, global_frd="global.frd")
            jobs = [(load, name) for name in subs for load in LOADS]
            with ThreadPoolExecutor(max_workers=int(numerics.get("parallel_solves", 6))) as ex:
                list(ex.map(lambda j: self._ccx(work / j[0], j[1], timeout), jobs))
            peaks = {(name, load): self._peaks(work / load / f"{name}.frd", p, load,
                                               box=subs[name]["box"] if name in subs else None, skip=skip)
                     for name in ["global", *subs] for load in LOADS}
            from models.fea import shaft_fillet_ccx as sf
            rf = {load: sf.read_node_forces(work / load / "global.dat") for load in LOADS}
        except (RuntimeError, subprocess.TimeoutExpired, ValueError) as e:
            return failed(f"{type(e).__name__}: {e}") | {"cleanup": work}
        # equilibrium of the global model: the clamp's reaction moment about the loaded axis
        from harness.calculix import read_frd
        eq = {}
        for load in LOADS:
            fr = read_frd(work / load / "global.frd")
            row = {int(n): k for k, n in enumerate(fr["nodes"])}
            ids = np.array(list(rf[load]))
            R = np.array([rf[load][n] for n in ids])
            P = fr["coords"][[row[int(n)] for n in ids]]
            axis = 1 if load == "bending" else 2
            target = (float(p["bending_moment_Nm"]) if load == "bending" else float(p["torque_Nm"])) * 1e3 / 2
            eq[load] = {"applied": info[("global", load)]["applied_moment_Nmm"][axis],
                        "reaction": float(-np.cross(P, R).sum(axis=0)[axis]), "target": target}
        out = {"global": {"cad": gm["cad"], "mesh": gm["mesh"], "nodes": info[("global", "bending")]["nodes"]},
               "subs": {n: {"box": v["box"], "cad": v["cad"], "mesh": v["mesh"], "nodes": info[(n, "bending")]["nodes"],
                            "driven_nodes": info[(n, "bending")]["driven_nodes"]} for n, v in subs.items()},
               "peaks": {f"{n}/{ld}": v for (n, ld), v in peaks.items()}, "equilibrium": eq}
        series = {"case": np.array([0.0]), "kt_fillet_bending": np.array([fillet_peak(out["peaks"], "bending")["k"]])}
        return {"success": True, "message": f"global {out['global']['nodes']} nodes + {len(subs)} submodels",
                "nfev": 2 * (1 + len(subs)), "series": series, "outputs": out, "files": {}, "cleanup": work}

    def tool_versions(self):
        return self._versions


def fillet_peak(pk: dict, load: str) -> dict:
    """The fillet's peak over the fillet submodels (keys "fillet*/<load>")."""
    return max((reg["fillet"] for key, reg in pk.items() if key.startswith("fillet") and key.endswith(load)
                and "fillet" in reg), key=lambda v: v["k"])


def fillet_coverage(out: dict, load: str, keyless: bool, skip: float) -> tuple[float, bool]:
    """Distance (mm) from the global model's fillet peak to the fillet submodels' peak, and whether the global peak
    lies where a fillet submodel reads peaks: inside its box, clear of the faces driven_clear skips. A Kt gap with
    the global peak covered is the global mesh's error; with it outside every box, a missed peak (r0's near box).
    Keyless the shaft is axisymmetric, so the global peak is first turned onto the box's plane (y = 0)."""
    g = out["peaks"][f"global/{load}"]["fillet"]["xyz"]
    s = fillet_peak(out["peaks"], load)["xyz"]
    x, y, z = (math.hypot(g[0], g[1]), 0.0, g[2]) if keyless else g

    def readable(b):
        x0, x1, y0, y1, z0, z1 = b
        return x0 + skip < x < x1 - skip and y < y1 - skip and z0 + skip < z < z1 - skip

    return math.dist(g, s), any(readable(v["box"]) for k, v in out["subs"].items() if k.startswith("fillet"))


def kt_values(out: dict) -> dict:
    """Kt (gross nominal stresses) at the keyway (the largest over its submodels) and at the fillet (its own
    submodel). The fillet box's keyway nodes are coarse there and never count."""
    pk = out["peaks"]
    res = {"kt_fillet_bending": fillet_peak(pk, "bending")["k"], "kt_fillet_torsion": fillet_peak(pk, "torsion")["k"]}
    keyed = lambda key, ld: not key.startswith(("global", "fillet")) and key.endswith(ld)  # noqa: E731
    kb = [v["k"] for key, reg in pk.items() if keyed(key, "bending") for name, v in reg.items() if name.startswith("key_")]
    kt = [v["k"] for key, reg in pk.items() if keyed(key, "torsion") for name, v in reg.items() if name.startswith("key_")]
    if kb:
        res |= {"kt_key_bending": max(kb), "kt_key_torsion": max(kt),
                # Le and Le's definitions: bending at an isolated end, torsion at the long side's middle
                "kt_key_bending_far": pk["far/bending"]["key_far_end"]["k"],
                "kt_key_torsion_middle": pk["middle/torsion"]["key_middle"]["k"],
                "kt_key_bending_far_axial": pk["far/bending"]["key_far_end"]["k_axial"]}
    return res


def safety(params: dict, kts: dict) -> dict:
    f = lambda k: float(params[k])  # noqa: E731
    D, d, M, T, Su, Sy, ov = (f(k) for k in ("D_mm", "d_mm", "bending_moment_Nm", "torque_Nm", "ultimate_MPa",
                                             "yield_MPa", "overload_factor"))
    out = {}
    fil = ref.assess(D, d, f("fillet_radius_mm"), M, T, Su, Sy, kt_b=kts["kt_fillet_bending"],
                     kt_t=kts["kt_fillet_torsion"], overload=ov)
    out |= {"fatigue_safety_fillet": fil["n_goodman"], "static_safety_fillet": fil["n_yield"]}
    if "kt_key_bending" in kts:
        key = ref.assess(D, d, f("key_corner_radius_mm"), M, T, Su, Sy, kt_b=kts["kt_key_bending"],
                         kt_t=kts["kt_key_torsion"], overload=ov)
        out |= {"fatigue_safety_key": key["n_goodman"], "static_safety_key": key["n_yield"]}
    out["fatigue_safety"] = min(v for k, v in out.items() if k.startswith("fatigue"))
    out["static_safety"] = min(v for k, v in out.items() if k.startswith("static"))
    return out


class KeyedShaftStudy(Study):
    name = "keyed_shaft"
    models = {"ccx_keyed_shaft": CalculiXKeyedShaft}
    metrics = frozenset({"kt_fillet_bending", "kt_fillet_torsion", "kt_key_bending", "kt_key_torsion",
                         "kt_key_bending_far", "kt_key_torsion_middle", "kt_key_bending_far_axial",
                         "fatigue_safety_fillet", "static_safety_fillet", "fatigue_safety_key", "static_safety_key",
                         "fatigue_safety", "static_safety"})
    param_names = PARAMS
    series_file = "keyed_shaft.csv"
    compare_description = "the fillet's bending Kt"

    def derive(self, params):
        return {}

    def compute_metrics(self, series, params, case, outputs=None):
        kts = kt_values(outputs)
        return kts | safety(params, kts)

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        out, m = point["solver_outputs"], point["metrics"]
        eq = out["equilibrium"]
        checks = [check(f"equilibrium_{ld}", f"global model: |clamp reaction moment - applied| / target ({ld})",
                        abs(eq[ld]["reaction"] - eq[ld]["applied"]) / eq[ld]["target"], tol["equilibrium_rel_tol"])
                  for ld in LOADS]
        checks += [check(f"load_{ld}", f"|applied end moment| against the target ({ld}; the end face's moment is -T "
                         "about z by the outward normal, so magnitudes are compared; 7-point rule on curved faces)",
                         abs(abs(eq[ld]["applied"]) / eq[ld]["target"] - 1), tol["load_rel_tol"]) for ld in LOADS]
        pk = out["peaks"]
        p = point["parameters"]
        keyless = float(p.get("key_width_mm", 0) or 0) <= 0
        skip = float(case.get("numerics", {}).get("driven_skip_mm", 1.0))
        for ld in LOADS:
            g, sb = pk[f"global/{ld}"]["fillet"]["k"], fillet_peak(pk, ld)["k"]
            dist, covered = fillet_coverage(out, ld, keyless, skip)
            checks.append(check(f"global_vs_sub_fillet_{ld}", f"fillet Kt, global model against its submodel ({ld}): "
                                f"the global mesh resolves the fillet, so the two must agree (peaks {dist:.1f} mm "
                                "apart)", abs(g / sb - 1), tol["global_sub_rel_tol"]))
            checks.append(check(f"fillet_peak_covered_{ld}", f"the global model's fillet peak ({ld}) lies inside a "
                                f"fillet submodel, more than {skip:g} mm from its driven faces (1 = outside every "
                                "box: the submodels miss the peak)" + (", turned onto y = 0 (axisymmetric)" if keyless
                                                                       else ""),
                                0.0 if covered else 1.0, 0.0, kind="validity"))
        sj = min([out["global"]["mesh"]["min_scaled_jacobian"]] + [v["mesh"]["min_scaled_jacobian"]
                                                                    for v in out["subs"].values()])
        checks.append(check("mesh_quality", f"{tol['min_scaled_jacobian']} - the smallest scaled Jacobian over the "
                            "global and submodel meshes (at or below 0: every element above the threshold)",
                            float(tol["min_scaled_jacobian"]) - sj, 0.0, kind="validity"))
        if float(p.get("kt_reference_bending", 0) or 0) > 0:   # the keyless case: part 1's verified fillet Kt
            for ld in LOADS:
                checks.append(check(f"part1_{ld}", f"fillet Kt against part 1's verified value ({ld})",
                                    abs(m[f"kt_fillet_{ld}"] / float(p[f"kt_reference_{ld}"]) - 1),
                                    tol["reference_rel_tol"]))
        if float(p.get("kt_key_reference_bending", 0) or 0) > 0:   # Le and Le (ASEE 2013), isolated profile keyseat
            for ld, metric in (("bending", "kt_key_bending_far"), ("torsion", "kt_key_torsion_middle")):
                checks.append(check(f"keyseat_reference_{ld}", f"{metric} against Le and Le's FE value ({ld})",
                                    abs(m[metric] / float(p[f"kt_key_reference_{ld}"]) - 1),
                                    tol["key_reference_rel_tol"]))
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
        for metric in ("kt_key_bending", "kt_key_torsion", "kt_fillet_bending", "fatigue_safety", "static_safety"):
            if metric not in fine[0]["metrics"]:
                continue
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine), design_order=2,
                                           noise_floor=float(nf[metric] if isinstance(nf, dict) else nf))
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


STUDY = KeyedShaftStudy()

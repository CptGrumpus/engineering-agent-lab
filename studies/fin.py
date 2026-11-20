"""Study: straight rectangular heat-sink fin, 3D steady conduction (CalculiX).

Model:     ccx_fin  (models/thermal/fin_ccx.py writes a structured C3D8 deck; ccx solves)
Reference: 1D fin theory with a convective tip (validation/fin_conduction.py)
Run-level: GCI over the three finest meshes, for an element_size_mm sweep

Results are read from CalculiX's own files: nodal temperatures from the .frd,
the tip-face temperatures (requirement metric, one more digit) and the base
reaction heat flow from the .dat. The convective loss is integrated
here, independently of the deck writer, from the nodal temperatures and the
node coordinates found in the .frd.

CalculiX's RFL total for the fixed base nodes is the conduction part only: the
film load that the consistent integration assigns to those same nodes (from the
side faces of the first element row) is not included. The heat entering
through the base is therefore RFL + that film share; both are reported.
"""

from __future__ import annotations

import glob
import importlib.util
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from scipy.integrate import trapezoid

from harness.backend_base import Backend, failed
from harness.calculix import read_frd
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.plotting import fin_figure
from harness.study import Study
from validation import fin_conduction as ref

PARAMS = ("thickness_mm", "width_mm", "length_mm", "conductivity_W_per_mK", "htc_W_per_m2K",
          "base_temperature_C", "air_temperature_C", "element_size_mm")


def find_ccx() -> Path:
    cands = [Path(os.environ["CCX"])] if os.environ.get("CCX") else []
    for base in (os.environ.get("LOCALAPPDATA", ""), "C:/Program Files"):
        cands += [Path(p) for p in sorted(glob.glob(f"{base}/Programs/FreeCAD*/bin/ccx.exe")
                                          + glob.glob(f"{base}/FreeCAD*/bin/ccx.exe"),
                                          reverse=True)]
    which = shutil.which("ccx")
    if which:
        cands.append(Path(which))
    for c in cands:
        if c.exists():
            return c
    raise RuntimeError("ccx not found: install FreeCAD (bundles CalculiX) or set CCX")


# --------------------------------------------------------------------------- field tools

def _axis_groups(v: np.ndarray, gap: float = 1e-6) -> tuple[np.ndarray, np.ndarray]:
    """Index of each value in the sorted list of distinct positions, and the positions.

    Values closer than `gap` (m) are one position: the .frd prints coordinates
    with 6 significant digits.
    """
    order = np.argsort(v)
    sv = v[order]
    new = np.concatenate([[True], np.diff(sv) > gap])
    gid = np.cumsum(new) - 1
    idx = np.empty(len(v), dtype=int)
    idx[order] = gid
    pos = np.array([sv[gid == g].mean() for g in range(gid[-1] + 1)])
    return idx, pos


def to_grid(coords: np.ndarray, values: np.ndarray):
    """Nodal values on the structured grid: (grid[i, j, k], xs, ys, zs)."""
    ix, xs = _axis_groups(coords[:, 0])
    iy, ys = _axis_groups(coords[:, 1])
    iz, zs = _axis_groups(coords[:, 2])
    if len(xs) * len(ys) * len(zs) != len(values):
        raise ValueError("nodes do not form a structured grid")
    grid = np.full((len(xs), len(ys), len(zs)), np.nan)
    grid[ix, iy, iz] = values
    if np.isnan(grid).any():
        raise ValueError("nodes do not form a structured grid")
    return grid, xs, ys, zs


def _face_loads(theta: np.ndarray, a: np.ndarray, b: np.ndarray, h: float) -> np.ndarray:
    """Consistent nodal film loads h * int(N_n theta) dA on a rectangular grid face.

    theta[i, j] at (a[i], b[j]); bilinear elements. For a rectangle of area A
    the load at a corner is h A / 36 (4 own + 2 + 2 adjacent + 1 opposite).
    """
    da, db = np.diff(a), np.diff(b)
    area = da[:, None] * db[None, :]
    t00, t10, t01, t11 = theta[:-1, :-1], theta[1:, :-1], theta[:-1, 1:], theta[1:, 1:]
    loads = np.zeros_like(theta)
    w = h * area / 36.0
    loads[:-1, :-1] += w * (4 * t00 + 2 * t10 + 2 * t01 + t11)
    loads[1:, :-1] += w * (4 * t10 + 2 * t00 + 2 * t11 + t01)
    loads[:-1, 1:] += w * (4 * t01 + 2 * t00 + 2 * t11 + t10)
    loads[1:, 1:] += w * (4 * t11 + 2 * t10 + 2 * t01 + t00)
    return loads


def film_loads(coords_m: np.ndarray, temps_C: np.ndarray, p: dict) -> np.ndarray:
    """Nodal convective loss (W) on the grid from every exposed face (all but z = 0)."""
    h, ta = float(p["htc_W_per_m2K"]), float(p["air_temperature_C"])
    g, xs, ys, zs = to_grid(coords_m, temps_C - ta)
    q = np.zeros_like(g)
    q[0] += _face_loads(g[0], ys, zs, h)           # x = 0 face
    q[-1] += _face_loads(g[-1], ys, zs, h)         # x = t face
    q[:, 0] += _face_loads(g[:, 0], xs, zs, h)     # y = 0 edge
    q[:, -1] += _face_loads(g[:, -1], xs, zs, h)   # y = w edge
    q[:, :, -1] += _face_loads(g[:, :, -1], xs, ys, h)  # tip
    return q


def convective_loss_W(coords_m: np.ndarray, temps_C: np.ndarray, p: dict) -> float:
    return float(film_loads(coords_m, temps_C, p).sum())


_RFL = re.compile(r"total heat generation for set (\S+)")


def read_dat_heat_totals(path: Path) -> dict:
    """{set: total reaction heat flow (W)} from '*NODE PRINT ... RFL, TOTALS=ONLY'."""
    lines = Path(path).read_text(encoding="latin-1").splitlines()
    out = {}
    for k, line in enumerate(lines):
        m = _RFL.search(line)
        if m:
            for nxt in lines[k + 1:k + 4]:
                if nxt.strip():
                    out[m.group(1)] = float(nxt.split()[0])
                    break
    return out


_NT = re.compile(r"temperatures for set (\S+)")


def read_dat_temperatures(path: Path, nset: str) -> dict:
    """{node id: T} from '*NODE PRINT, NSET=<nset>' with NT (7 significant digits)."""
    lines = Path(path).read_text(encoding="latin-1").splitlines()
    out = {}
    for k, line in enumerate(lines):
        m = _NT.search(line)
        if m and m.group(1) == nset:
            for nxt in lines[k + 1:]:
                parts = nxt.split()
                if not parts:
                    if out:
                        break
                    continue
                if len(parts) != 2 or not parts[0].isdigit():
                    break
                out[int(parts[0])] = float(parts[1])
    return out


# --------------------------------------------------------------------------- backend

class CalculiXFin(Backend):
    sources = ("models/thermal/fin_ccx.py",)

    def __init__(self):
        self.ccx = find_ccx()
        self.model = None
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        src = self.source_path(self.sources[0], source_dir)
        spec = importlib.util.spec_from_file_location("fin_ccx_model", src)
        self.model = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.model)
        r = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"CalculiX": (r.stdout.strip().splitlines() or ["?"])[-1],
                          "ccx": str(self.ccx)}

    def solve(self, params, numerics, tolerance_scale=1.0):
        # tolerance_scale is ignored: the steady linear heat problem is solved directly
        work = Path(tempfile.mkdtemp(prefix="ccx_fin_"))
        (work / "fin.inp").write_text(self.model.write_deck(params), encoding="utf-8")
        env = dict(os.environ, OMP_NUM_THREADS=os.environ.get("OMP_NUM_THREADS", "4"))
        r = subprocess.run([str(self.ccx), "-i", "fin"], cwd=work, env=env,
                           capture_output=True, text=True, timeout=1800)
        (work / "ccx.log").write_text(r.stdout + r.stderr, encoding="utf-8")
        files = {n: work / n for n in ("fin.inp", "fin.dat", "fin.sta", "ccx.log", "fin.frd")
                 if (work / n).exists()}
        frd, dat = work / "fin.frd", work / "fin.dat"
        if r.returncode != 0 or "Job finished" not in r.stdout or not frd.exists():
            res = failed(f"ccx failed (exit {r.returncode}): {r.stdout[-800:]}")
            return res | {"files": files, "cleanup": work}

        res = read_frd(frd)
        coords, nodes = res["coords"], res["nodes"]
        t_ids, t_vals = res["NDTEMP"]["ids"], res["NDTEMP"]["T"]
        if len(t_ids) != len(nodes) or not np.array_equal(np.sort(t_ids), np.sort(nodes)):
            return failed("temperature block does not cover every node") | {
                "files": files, "cleanup": work}
        by_id = dict(zip(t_ids.tolist(), t_vals.tolist()))
        temps = np.array([by_id[n] for n in nodes.tolist()])
        grid, xs, ys, zs = to_grid(coords, temps)
        loads = film_loads(coords, temps, params)
        rfl = read_dat_heat_totals(dat).get("NBASE", float("nan"))
        tip_dat = read_dat_temperatures(dat, "NTIP")
        if len(tip_dat) != len(xs) * len(ys):
            return failed(f"tip temperatures in .dat: {len(tip_dat)} nodes, expected "
                          f"{len(xs) * len(ys)}") | {"files": files, "cleanup": work}

        area = (xs[-1] - xs[0]) * (ys[-1] - ys[0])
        mean_z = trapezoid(trapezoid(grid, ys, axis=1), xs, axis=0) / area
        series = {"z_mm": zs * 1e3, "T_mean_C": mean_z,
                  "T_min_C": grid.min(axis=(0, 1)), "T_max_C": grid.max(axis=(0, 1))}
        tip = grid[:, :, -1]
        outputs = {
            "nodes": int(grid.size), "divisions": [len(xs) - 1, len(ys) - 1, len(zs) - 1],
            "extent_mm": [float(v[-1] - v[0]) * 1e3 for v in (xs, ys, zs)],
            # requirement metric from the .dat (7 digits); the .frd copy (6 digits)
            # is compared with the global minimum at the same precision
            "tip_min_C": min(tip_dat.values()), "tip_min_frd_C": float(tip.min()),
            "tip_mean_C": float(mean_z[-1]),
            "global_min_C": float(grid.min()), "global_max_C": float(grid.max()),
            "base_reaction_rfl_W": rfl,
            "base_node_film_W": float(loads[:, :, 0].sum()),
            "convective_loss_W": float(loads.sum()),
        }
        return {"success": True, "message": f"CalculiX: {outputs['divisions']} hex elements",
                "nfev": None, "series": series, "outputs": outputs, "files": files,
                "cleanup": work}

    def tool_versions(self):
        return self._versions


# --------------------------------------------------------------------------- study

class FinStudy(Study):
    name = "fin"
    models = {"ccx_fin": CalculiXFin}
    metrics = frozenset({"tip_temperature_min_C", "tip_temperature_mean_C", "tip_excess_min_K",
                         "base_heat_flow_W"})
    param_names = PARAMS
    series_file = "profile.csv"
    compare_description = "max relative difference over the cross-section temperature profile"

    def derive(self, params):
        if min(float(params[k]) for k in PARAMS) <= 0:
            raise ValueError("dimensions, conductivity, h and element size must be positive")
        if float(params["base_temperature_C"]) <= float(params["air_temperature_C"]):
            raise ValueError("base must be hotter than the air")
        return {"biot_half_thickness": ref.biot(params),
                "mL": ref.fin_parameter(params) * float(params["length_mm"]) * 1e-3,
                "tip_temperature_1d_C": ref.tip_temperature_C(params),
                "heat_flow_1d_W": ref.heat_flow_W(params),
                "fin_efficiency_1d": ref.fin_efficiency(params),
                "breakeven_htc_1d_W_per_m2K": ref.breakeven_htc(params, 60.0)}

    def compute_metrics(self, series, params, case, outputs=None):
        ta = float(params["air_temperature_C"])
        return {"tip_temperature_min_C": outputs["tip_min_C"],
                "tip_temperature_mean_C": outputs["tip_mean_C"],
                "tip_excess_min_K": outputs["tip_min_C"] - ta,
                "base_heat_flow_W": outputs["base_reaction_rfl_W"] + outputs["base_node_film_W"]}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        p, d, m, out = (point["parameters"], point["derived"], point["metrics"],
                        point["solver_outputs"])
        ta, tb = float(p["air_temperature_C"]), float(p["base_temperature_C"])
        z_m = series["z_mm"] * 1e-3
        t_ref = ref.temperature_C(p, z_m)
        theta_tip_ref = d["tip_temperature_1d_C"] - ta
        q_conv = out["convective_loss_W"]
        checks = [
            check("energy_balance",
                  "|Q_base (RFL + film share at base nodes) - integral h(T - T_air) dA| / Q_conv",
                  abs(m["base_heat_flow_W"] - q_conv) / q_conv, tol["energy_balance_rel_tol"]),
            check("tip_reference",
                  "|tip-face mean excess T (3D) - 1D fin theory| / 1D (model form)",
                  abs(m["tip_temperature_mean_C"] - ta - theta_tip_ref) / theta_tip_ref,
                  tol["tip_reference_rel_tol"]),
            check("heat_flow_reference",
                  "|base heat flow (3D) - 1D fin heat rate| / 1D (model form)",
                  abs(m["base_heat_flow_W"] - d["heat_flow_1d_W"]) / d["heat_flow_1d_W"],
                  tol["heat_flow_reference_rel_tol"]),
            check("profile_reference",
                  "max over z of |cross-section mean T - T_1D(z)| / (T_base - T_air)",
                  float(np.max(np.abs(series["T_mean_C"] - t_ref))) / (tb - ta),
                  tol["profile_reference_rel_tol"]),
            check("tip_is_coldest",
                  "tip-face minimum - global minimum temperature (K); metric must find the coldest point",
                  out["tip_min_frd_C"] - out["global_min_C"], tol["tip_is_coldest_abs_tol_K"]),
            check("one_d_reference_valid",
                  "Biot number h (t/2) / k (1D fin theory valid well below 0.1)",
                  d["biot_half_thickness"], tol["biot_max"], kind="validity"),
        ]
        req = next((r for r in case["requirements"] if r["metric"] == "tip_temperature_min_C"), None)
        nx, ny, nz = out["divisions"]
        fin_figure(pdir / "response.png", series, t_ref, m, limit_C=req["limit"] if req else None,
                   title=(f"{point['label']}  (h {float(p['htc_W_per_m2K']):g} W/m\u00b2K, "
                          f"k {float(p['conductivity_W_per_mK']):g} W/mK, "
                          f"{nx}x{ny}x{nz} hex)"))
        return checks

    def verify_run_level(self, case, manifest, points):
        """GCI on the three finest completed meshes, only for an element_size_mm sweep."""
        if case.get("sweep", {}).get("parameter") != "element_size_mm":
            return [], {}
        tol = case["verification"]
        done = [pt for pt in manifest["points"] if pt["status"] == "completed"]
        done.sort(key=lambda pt: float(pt["parameters"]["element_size_mm"]))
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels",
                          float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(float(pt["parameters"]["element_size_mm"]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
        # the tip excess (T_tip,min - T_air) carries the uncertainty of the
        # requirement metric tip_temperature_min_C (same quantity, offset by T_air)
        for metric, key, gate in (("tip_excess_min_K", "gci_tip_excess_max", "tip_temperature_min_C"),
                                  ("base_heat_flow_W", "gci_heat_flow_max", "base_heat_flow_W")):
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine))
            detail[metric] = u
            checks.append(check(f"discretization_{metric}",
                                f"relative discretization uncertainty of {metric}, {describe(u)}",
                                u["uncertainty"], tol[key]) | {"metric": gate})
        return checks, detail


STUDY = FinStudy()

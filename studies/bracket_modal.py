"""Study: modal analysis of a clamped bracket arm, CAD-to-FEA pipeline.

Model:     cadquery_ccx_modal (models/fea/bracket_modal.py): CadQuery solid ->
           STEP -> Gmsh 10-node tetrahedra -> CalculiX *FREQUENCY
Reference: 1D Timoshenko beam model for flapwise and in-plane bending,
           Saint-Venant torsion, first-mode effective mass and shape
           (validation/beam_vibration.py)
Run-level: GCI on the first frequency when the sweep is the element size
           (eigenvalues of quadratic elements converge at about fourth order)

Modes are classified from CalculiX's effective modal mass table: flapwise
bending (z / rotation about y), in-plane bending (y / rotation about z),
torsion (rotation about x), axial (x).
"""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness.backend_base import Backend, failed
from harness.calculix import read_dat_frequency, read_frd
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.plotting import modal_figure
from harness.study import Study
from validation import beam_vibration as bv

WRITER = "models/fea/bracket_modal.py"
TYPES = ("axial", "in-plane", "flapwise", "torsion")


def _load_writer(path: Path):
    spec = importlib.util.spec_from_file_location("bracket_modal_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_W = _load_writer(Path(__file__).resolve().parent.parent / WRITER)
PARAMS = _W.PARAMS


def _p(params, k):
    return float(params[k])


def classify(eff: np.ndarray, total: np.ndarray) -> list[str]:
    """Mode type from the effective modal mass fractions [x, y, z, rx, ry, rz]."""
    frac = eff / np.where(total > 0, total, np.inf)
    scores = np.column_stack([frac[:, 0], np.maximum(frac[:, 1], frac[:, 5]),
                              np.maximum(frac[:, 2], frac[:, 4]), frac[:, 3]])
    return [TYPES[int(k)] for k in np.argmax(scores, axis=1)]


class CadQueryCalculiXModal(Backend):
    sources = (WRITER,)

    def __init__(self):
        from studies.cantilever import find_freecadcmd

        bin_dir = find_freecadcmd().parent
        self.gmsh, self.ccx = bin_dir / "gmsh.exe", bin_dir / "ccx.exe"
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        import cadquery

        self.writer = _load_writer(self.source_path(WRITER, source_dir))
        g = subprocess.run([str(self.gmsh), "--version"], capture_output=True, text=True, timeout=60)
        c = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"cadquery": cadquery.__version__,
                          "gmsh": (g.stdout + g.stderr).strip().splitlines()[-1],
                          "CalculiX": (c.stdout.strip().splitlines() or ["?"])[-1]}

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="bracket_modal_"))
        keep = ("arm.step", "mesh.geo", "job.inp", "job.dat", "job.sta", "gmsh.log", "ccx.log")

        def files():
            return {n: work / n for n in keep if (work / n).exists()}

        try:
            volume = self.writer.build_step(params, work / "arm.step")
            self.writer.write_geo(params, work / "mesh.geo")
            g = subprocess.run([str(self.gmsh), "mesh.geo", "-3", "-format", "inp", "-o", "mesh.inp"],
                               cwd=work, capture_output=True, text=True, timeout=1800)
            (work / "gmsh.log").write_text(g.stdout + g.stderr, encoding="utf-8")
            if g.returncode != 0 or not (work / "mesh.inp").exists():
                res = failed(f"gmsh failed (exit {g.returncode})")
                res.update(files=files(), cleanup=work)
                return res
            info = self.writer.write_deck(params, work / "mesh.inp", work / "job.inp")
            c = subprocess.run([str(self.ccx), "-i", "job"], cwd=work, capture_output=True,
                               text=True, timeout=7200)
            (work / "ccx.log").write_text(c.stdout + c.stderr, encoding="utf-8")
            if c.returncode != 0 or not (work / "job.frd").exists():
                res = failed(f"CalculiX failed (exit {c.returncode}); see ccx.log")
                res.update(files=files(), cleanup=work)
                return res
        except Exception as e:
            res = failed(f"{type(e).__name__}: {e}")
            res.update(files=files(), cleanup=work)
            return res

        dat = read_dat_frequency(work / "job.dat")
        frd = read_frd(work / "job.frd")
        order = np.argsort(frd["nodes"])
        ids, xyz = frd["nodes"][order], frd["coords"][order]
        series = {"node_id": ids.astype(float), "x_mm": xyz[:, 0], "y_mm": xyz[:, 1],
                  "z_mm": xyz[:, 2]}
        modes = [b for name, b in frd.get("blocks", []) if name == "DISP"]
        for k, blk in enumerate(modes, 1):
            o = np.argsort(blk["ids"])
            for c_, n_ in (("D1", "x"), ("D2", "y"), ("D3", "z")):
                series[f"mode{k}_u{n_}"] = blk[c_][o]
        mesh_text = (work / "mesh.inp").read_text(encoding="utf-8")
        n_elem = sum(1 for ln in mesh_text.split("*ELEMENT", 1)[1].split("*", 1)[0].splitlines()
                     if ln.strip() and ln.strip()[0].isdigit())
        types = classify(dat["effective_mass"], dat["total_effective_mass"])
        outputs = {**info, "elements": n_elem, "volume_mm3": volume,
                   "frequency_Hz": [float(f) for f in dat["frequency_Hz"]],
                   "mode_types": types,
                   "effective_mass": dat["effective_mass"].tolist(),
                   "total_effective_mass": dat["total_effective_mass"].tolist()}
        return {"success": True, "message": f"CalculiX: {n_elem} C3D10, modes " + ", ".join(
                    f"{f:.1f} Hz {t}" for f, t in zip(dat["frequency_Hz"], types)),
                "nfev": None, "series": series, "outputs": outputs, "files": files(),
                "cleanup": work}

    def tool_versions(self):
        return self._versions


def _references(params):
    L, b, h = _p(params, "length_mm"), _p(params, "width_mm"), _p(params, "thickness_mm")
    E, nu, rho = _p(params, "youngs_modulus_MPa"), _p(params, "poisson_ratio"), _p(params, "density_t_per_mm3")
    A = b * h
    f_flap, x, w = bv.timoshenko_modes(L, E, nu, b * h**3 / 12, A, rho, n_modes=3)
    f_in, _, _ = bv.timoshenko_modes(L, E, nu, h * b**3 / 12, A, rho, n_modes=1)
    return {"flap": f_flap, "inplane": f_in, "x": x, "w1": w[0],
            "torsion": bv.torsion_saint_venant(1, L, E, nu, rho, b, h),
            "eff1": bv.effective_mass_fraction(x, w[0], rho, A, L)}


def first_mode_profile(series, params, bins: int = 30):
    """Mean flapwise displacement of mode 1 in bins along the arm."""
    L = _p(params, "length_mm")
    edges = np.linspace(0, L, bins + 1)
    idx = np.clip(np.digitize(series["x_mm"], edges) - 1, 0, bins - 1)
    uz = series["mode1_uz"]
    prof = np.array([uz[idx == k].mean() for k in range(bins)])
    return 0.5 * (edges[1:] + edges[:-1]), prof


class BracketModalStudy(Study):
    name = "bracket_modal"
    models = {"cadquery_ccx_modal": CadQueryCalculiXModal}
    metrics = frozenset({"first_frequency_Hz", "mass_g"})
    param_names = PARAMS
    series_file = "mode_shapes.csv"
    compare_description = "max relative difference over nodal mode-shape columns"

    def derive(self, params):
        L, b, h = _p(params, "length_mm"), _p(params, "width_mm"), _p(params, "thickness_mm")
        if min(L, b, h) <= 0 or int(params["n_modes"]) < 4:
            raise ValueError("positive dimensions and at least 4 modes")
        r = _references(params)
        return {"slenderness_h_over_L": h / L,
                "volume_closed_form_mm3": L * b * h,
                "flapwise_timoshenko_Hz": [float(f) for f in r["flap"]],
                "inplane_timoshenko_Hz": float(r["inplane"][0]),
                "torsion_saint_venant_Hz": float(r["torsion"]),
                "first_mode_eff_mass_fraction_ref": r["eff1"]}

    def compute_metrics(self, series, params, case, outputs=None):
        return {"first_frequency_Hz": outputs["frequency_Hz"][0],
                "mass_g": outputs["volume_mm3"] * _p(params, "density_t_per_mm3") * 1e6}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        p, d, m, out = (point["parameters"], point["derived"], point["metrics"],
                        point["solver_outputs"])
        f = np.array(out["frequency_Hz"])
        types = out["mode_types"]
        flap = [fi for fi, t in zip(f, types) if t == "flapwise"]
        inpl = [fi for fi, t in zip(f, types) if t == "in-plane"]
        tors = [fi for fi, t in zip(f, types) if t == "torsion"]
        missing = (int(types[0] != "flapwise") + int(len(flap) < 2) + int(not inpl) + int(not tors))
        n_cmp = min(3, len(flap))
        flap_err = (max(abs(flap[k] - d["flapwise_timoshenko_Hz"][k]) / d["flapwise_timoshenko_Hz"][k]
                        for k in range(n_cmp)) if n_cmp else float("inf"))
        in_err = (abs(inpl[0] - d["inplane_timoshenko_Hz"]) / d["inplane_timoshenko_Hz"]
                  if inpl else float("inf"))
        t_err = (abs(tors[0] - d["torsion_saint_venant_Hz"]) / d["torsion_saint_venant_Hz"]
                 if tors else float("inf"))
        eff = np.array(out["effective_mass"])
        tot = np.array(out["total_effective_mass"])
        eff1 = float(eff[0, 2] / tot[2]) if tot[2] > 0 else float("inf")
        r = _references(p)
        xb, prof = first_mode_profile(series, p)
        mac = bv.mac(prof, np.interp(xb, r["x"], r["w1"]))
        checks = [
            check("cad_volume", "|CadQuery volume - L b h| / (L b h)",
                  abs(out["volume_mm3"] - d["volume_closed_form_mm3"]) / d["volume_closed_form_mm3"], 1e-9),
            check("modes_identified",
                  "expected modes missing (mode 1 flapwise; >= 2 flapwise, 1 in-plane, 1 torsion)",
                  missing, 0.0),
            check("flapwise_reference",
                  f"max |f_FE - f_Timoshenko| / f_Timoshenko over the first {n_cmp} flapwise modes",
                  flap_err, tol["flap_rel_tol"]),
            check("inplane_reference", "|f_FE - f_Timoshenko| / f_Timoshenko, first in-plane mode (model form)",
                  in_err, tol["inplane_rel_tol"]),
            check("torsion_reference", "|f_FE - f_Saint-Venant| / f_Saint-Venant, first torsion mode (model form)",
                  t_err, tol["torsion_rel_tol"]),
            check("first_mode_effective_mass",
                  "|effective mass fraction of mode 1 (z) - Timoshenko|",
                  abs(eff1 - d["first_mode_eff_mass_fraction_ref"]), tol["eff_mass_abs_tol"]),
            check("first_mode_shape", "1 - MAC(FE mode 1 along the arm, Timoshenko mode 1)",
                  1.0 - mac, 1.0 - tol["mac_min"]),
            check("beam_reference_valid", "thickness / length (beam references need a slender arm)",
                  d["slenderness_h_over_L"], tol["slenderness_max"], kind="validity"),
        ]
        modal_figure(pdir / "response.png", f, types, d, xb, prof, r["x"], r["w1"], m,
                     title=f"{point['label']}  ({out['elements']} quadratic tetrahedra)")
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "element_size_mm":
            return [], {}
        tol = case["verification"]
        done = [pt for pt in manifest["points"] if pt["status"] == "completed"]
        done.sort(key=lambda pt: pt["parameters"]["element_size_mm"])
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels",
                          float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(float(pt["parameters"]["element_size_mm"]) for pt in fine)
        metric = "first_frequency_Hz"
        # eigenvalues of quadratic elements converge at order 2p = 4
        u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine), design_order=4)
        return [check(f"discretization_{metric}",
                      f"relative discretization uncertainty of {metric}, {describe(u)}",
                      u["uncertainty"], tol["gci_frequency_max"]) | {"metric": metric}], \
            {"meshes_used": [pt["label"] for pt in fine], metric: u}


STUDY = BracketModalStudy()

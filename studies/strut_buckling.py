"""Study: pinned-pinned aluminium strut in compression: linear buckling, then the imperfect strut.

Model:     ccx_strut (models/fea/strut_ccx.py): structured C3D8I mesh; CalculiX *BUCKLE for the
           elastic critical load, then a geometrically nonlinear static analysis of the strut
           with an initial sinusoidal bow, ramped to just past first yield
References (validation/column_buckling.py, independent of the FE path):
           Euler with the Engesser shear correction (critical load), the first-mode shape
           (half sine), the amplification law e0 / (1 - P / P_cr), the Southwell plot (P_cr
           from the nonlinear response alone, compared with the eigenvalue), Perry-Robertson
           first yield; validity: Euler range (Johnson otherwise), moderate deflection
Run-level: GCI on the requirement metric and the critical load when the sweep is the element
           size

First yield is where the peak von Mises stress at midspan (integration-point stresses
extrapolated to the nodes) reaches the yield stress, interpolated between load increments.
The material stays linear elastic: past first yield the response is not physical, and the
analysis stops just beyond it.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness.backend_base import Backend, failed
from harness.calculix import HEX8_EXTRAPOLATION
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study
from studies.fin import find_ccx
from validation import column_buckling as cb

WRITER = "models/fea/strut_ccx.py"


def _load_writer(path: Path):
    spec = importlib.util.spec_from_file_location("strut_ccx_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_W = _load_writer(Path(__file__).resolve().parent.parent / WRITER)
PARAMS = _W.PARAMS + ("yield_strength_MPa",)


def _p(params, k):
    return float(params[k])


def _dims(p):
    return _p(p, "youngs_modulus_MPa"), _p(p, "poisson_ratio"), _p(p, "width_mm"), _p(p, "thickness_mm"), \
        _p(p, "length_mm")


# ---------------------------------------------------------------------- .dat parsing

_BLOCK = re.compile(r"^\s*(displacements \(vx,vy,vz\)|stresses \(elem, integ\.pnt\.,sxx,syy,szz,sxy,sxz,syz\)|"
                    r"total force \(fx,fy,fz\)|forces \(fx,fy,fz\)) for set (\S+) and time\s+(\S+)")


def read_dat_blocks(path: Path) -> list[dict]:
    """Every printed block in file order: {"kind", "set", "time", "rows"}."""
    lines = Path(path).read_text(encoding="latin-1").splitlines()
    out, k = [], 0
    while k < len(lines):
        m = _BLOCK.match(lines[k])
        if not m:
            k += 1
            continue
        kind = m.group(1).split()[0]
        rows = []
        k += 1
        while k < len(lines) and not lines[k].strip():
            k += 1
        while k < len(lines) and lines[k].strip() and not _BLOCK.match(lines[k]):
            parts = lines[k].split()
            try:
                rows.append([float(v) for v in parts])
            except ValueError:
                break
            k += 1
        out.append({"kind": kind, "set": m.group(2), "time": float(m.group(3)), "rows": np.array(rows)})
    return out


def buckling_factors(path: Path) -> list[float]:
    text = Path(path).read_text(encoding="latin-1")
    i = text.find("B U C K L I N G   F A C T O R   O U T P U T")
    out = []
    for ln in text[i:].splitlines()[1:]:
        parts = ln.split()
        if len(parts) == 2 and parts[0].isdigit():
            out.append(float(parts[1]))
        elif out and not ln.strip():
            break
    return out


def buckling_modes(path: Path) -> list[np.ndarray]:
    """Eigenvector blocks (rows: node, ux, uy, uz) in mode order, skipping the static pre-buckling
    solution that precedes the first "E I G E N V A L U E   N U M B E R" header."""
    text = Path(path).read_text(encoding="latin-1")
    i = text.find("E I G E N V A L U E    N U M B E R")
    if i < 0:
        return []
    tmp = Path(path).with_suffix(".modes.tmp")
    tmp.write_text(text[i:], encoding="latin-1")
    try:
        return [b["rows"] for b in read_dat_blocks(tmp) if b["kind"] == "displacements"]
    finally:
        tmp.unlink()


# ---------------------------------------------------------------------- backend

class CalculiXStrut(Backend):
    sources = (WRITER,)

    def __init__(self):
        self.ccx = find_ccx()
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        self.writer = _load_writer(self.source_path(WRITER, source_dir))
        r = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"CalculiX": (r.stdout.strip().splitlines() or ["?"])[-1]}

    def _run(self, work, job):
        r = subprocess.run([str(self.ccx), "-i", job], cwd=work, capture_output=True, text=True, timeout=7200)
        (work / f"{job}.log").write_text(r.stdout + r.stderr, encoding="utf-8")
        return r.returncode == 0 and "Job finished" in r.stdout

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="strut_"))
        w = self.writer
        m = w.StrutMesh(params)
        E, nu, b, h, L = _dims(params)
        sy = _p(params, "yield_strength_MPa")
        e0 = _p(params, "imperfection_over_length") * L

        def files():
            return {f.name: f for f in sorted(work.glob("*")) if f.suffix in (".inp", ".dat", ".sta", ".log")
                    and f.stat().st_size < 60e6}

        p_ref = 1000.0
        (work / "buckle.inp").write_text(w.write_buckle_deck(params, m, p_ref), encoding="utf-8")
        if not self._run(work, "buckle"):
            return failed("CalculiX *BUCKLE failed") | {"files": files(), "cleanup": work}
        factors = buckling_factors(work / "buckle.dat")
        if not factors:
            return failed("no buckling factors in buckle.dat") | {"files": files(), "cleanup": work}
        p_cr = factors[0] * p_ref
        # the .dat prints the static pre-buckling solution first (before "EIGENVALUE NUMBER 1"),
        # then one block per mode: reading the first block as mode 1 took the axial pre-buckling
        # state (uz ~ 1e-16 noise) as the mode shape; the MAC check caught it
        modes = buckling_modes(work / "buckle.dat")
        if not modes:
            return failed("no eigenvector blocks in buckle.dat") | {"files": files(), "cleanup": work}
        mode1 = modes[0]                                  # first eigenvector on the axis nodes, in x order
        # load to just past first yield (Perry-Robertson with the FE critical load), never past 0.98 P_cr
        p_max = min(float(numerics["load_over_first_yield"]) * cb.perry_robertson_load(E, sy, b, h, L, e0, p_cr),
                    float(numerics["max_load_over_critical"]) * p_cr)
        n_inc = int(numerics["increments"])
        (work / "nonlinear.inp").write_text(w.write_nonlinear_deck(params, m, p_max, n_inc), encoding="utf-8")
        if not self._run(work, "nonlinear"):
            return failed("CalculiX nonlinear static failed") | {"files": files(), "cleanup": work}
        blocks = read_dat_blocks(work / "nonlinear.dat")
        centre = m.nid(m.nx // 2, m.ny // 2, m.nz // 2)
        conn = m.connectivity()
        mid_nodes = set(m.midspan_nodes())
        P, w_mid, vm_max, rf = [], [], [], []
        for blk in blocks:
            t = blk["time"]
            if blk["kind"] == "displacements" and blk["set"] == "NMID":
                row = blk["rows"][blk["rows"][:, 0] == centre][0]
                P.append(t * p_max)
                w_mid.append(e0 + row[3])
            elif blk["kind"] == "stresses" and blk["set"] == "EMID":
                acc, cnt = {}, {}
                rows = blk["rows"]
                for e in np.unique(rows[:, 0]).astype(int):
                    s = rows[rows[:, 0] == e][:, 2:8]
                    vals = HEX8_EXTRAPOLATION @ s
                    for n, v in zip(conn[e], vals):
                        if n in mid_nodes:
                            acc[n] = acc.get(n, 0.0) + v
                            cnt[n] = cnt.get(n, 0) + 1
                S = np.array([acc[n] / cnt[n] for n in acc])
                sxx, syy, szz, sxy, sxz, syz = S.T
                vm = np.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
                             + 3 * (sxy**2 + sxz**2 + syz**2))
                vm_max.append(float(vm.max()))
            elif blk["kind"] == "total" and blk["set"] == "NMIDAXIS":
                rf.append(list(blk["rows"][0]))
        if not (len(P) == len(vm_max) == n_inc):
            return failed(f"expected {n_inc} increments, got {len(P)} displacement and {len(vm_max)} stress "
                          "blocks") | {"files": files(), "cleanup": work}
        P, w_mid, vm_max = np.array(P), np.array(w_mid), np.array(vm_max)
        # first yield: interpolate the load where the peak von Mises crosses the yield stress
        k = np.argmax(vm_max >= sy) if np.any(vm_max >= sy) else None
        if k is None or k == 0:
            p_fy = float("nan")
        else:
            p_fy = float(np.interp(sy, vm_max[k - 1:k + 1], P[k - 1:k + 1]))
        xs = mode1[:, 0] * 0 + m.x                       # axis nodes are listed in x order
        uz = mode1[:, 3]
        series = {"x_mm": xs, "mode1_uz": uz / np.max(np.abs(uz)), "mode1_uy": mode1[:, 2] / np.max(np.abs(uz))}
        outputs = {"divisions": [m.nx, m.ny, m.nz], "elements": m.nx * m.ny * m.nz,
                   "buckling_factors_x1000N": factors, "critical_load_N": p_cr, "p_max_N": p_max,
                   "imperfection_mm": e0, "load_N": P.tolist(), "midspan_deflection_mm": w_mid.tolist(),
                   "midspan_peak_von_mises_MPa": vm_max.tolist(), "first_yield_load_N": p_fy,
                   "axial_restraint_reaction_last_N": rf[-1] if rf else [np.nan] * 3}
        return {"success": True, "message": f"P_cr {p_cr:.1f} N; first yield {p_fy:.1f} N ({n_inc} increments)",
                "nfev": n_inc, "series": series, "outputs": outputs, "files": files(), "cleanup": work}

    def tool_versions(self):
        return self._versions


# ---------------------------------------------------------------------- study

class StrutBucklingStudy(Study):
    name = "strut_buckling"
    models = {"ccx_strut": CalculiXStrut}
    metrics = frozenset({"critical_load_N", "first_yield_load_N", "southwell_load_N",
                         "deflection_at_first_yield_mm"})
    param_names = PARAMS
    series_file = "mode_shape.csv"
    compare_description = "max relative difference over the normalised first mode"

    def derive(self, params):
        E, nu, b, h, L = _dims(params)
        sy = _p(params, "yield_strength_MPa")
        if min(E, b, h, L, sy) <= 0 or h > b:
            raise ValueError("positive dimensions, and the thickness (weak axis) no larger than the width")
        A, I, r = cb.section(b, h)
        p_cr = cb.critical_load(E, nu, b, h, L)
        e0 = _p(params, "imperfection_over_length") * L
        return {"slenderness_L_over_r": L / r, "euler_load_N": cb.euler_load(E, b, h, L),
                "critical_load_engesser_N": p_cr, "euler_stress_MPa": cb.euler_load(E, b, h, L) / A,
                "johnson_stress_MPa": cb.johnson_stress(E, sy, b, h, L),
                "perry_robertson_load_N": cb.perry_robertson_load(E, sy, b, h, L, e0, p_cr),
                "squash_load_N": sy * A, "thickness_over_length": h / L}

    def compute_metrics(self, series, params, case, outputs=None):
        P, w = np.array(outputs["load_N"]), np.array(outputs["midspan_deflection_mm"])
        e0 = outputs["imperfection_mm"]
        sel = (P >= 0.2 * P[-1]) & (P <= 0.9 * outputs["critical_load_N"])
        p_s, _ = cb.southwell(P[sel], w[sel], e0)
        p_fy = outputs["first_yield_load_N"]
        return {"critical_load_N": outputs["critical_load_N"], "first_yield_load_N": p_fy,
                "southwell_load_N": p_s,
                "deflection_at_first_yield_mm": float(np.interp(p_fy, P, w)) if np.isfinite(p_fy) else float("nan")}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        p, d, m, out = point["parameters"], point["derived"], point["metrics"], point["solver_outputs"]
        E, nu, b, h, L = _dims(p)
        sy = _p(p, "yield_strength_MPa")
        P, w = np.array(out["load_N"]), np.array(out["midspan_deflection_mm"])
        e0 = out["imperfection_mm"]
        pcr = m["critical_load_N"]
        x, uz = series["x_mm"], series["mode1_uz"]
        shape = np.sin(np.pi * x / L)
        mac = float(np.dot(uz, shape) ** 2 / (np.dot(uz, uz) * np.dot(shape, shape)))
        sel = (P >= 0.2 * P[-1]) & (P <= 0.9 * pcr)
        _, e0_fit = cb.southwell(P[sel], w[sel], e0)
        amp = P <= 0.8 * pcr
        amp_err = float(np.max(np.abs(w[amp] - cb.amplified_deflection(P[amp], pcr, e0)) / w[amp]))
        pr = cb.perry_robertson_load(E, sy, b, h, L, e0, pcr)
        rf = np.array(out["axial_restraint_reaction_last_N"])
        checks = [
            check("buckling_reference", "|P_cr FE - Euler with Engesser shear correction| / reference (model form)",
                  abs(pcr - d["critical_load_engesser_N"]) / d["critical_load_engesser_N"], tol["buckling_rel_tol"]),
            check("mode_shape", "1 - MAC(first mode on the axis, half sine) (weak-axis buckling)", 1 - mac,
                  1 - tol["mac_min"]),
            check("southwell_vs_eigenvalue", "|P_cr from the Southwell plot of the nonlinear run - eigenvalue| / "
                  "eigenvalue (two independent FE routes)", abs(m["southwell_load_N"] - pcr) / pcr,
                  tol["southwell_rel_tol"]),
            check("southwell_imperfection", "|initial bow recovered by the Southwell fit - imposed| / imposed",
                  abs(e0_fit - e0) / e0, tol["imperfection_rel_tol"]),
            check("amplification_reference", "max over P <= 0.8 P_cr of |midspan deflection - e0 / (1 - P/P_cr)| / "
                  "deflection (model form: small-deflection theory)", amp_err, tol["amplification_rel_tol"]),
            check("first_yield_bracketed", "first yield reached inside the load range (1 = not reached)",
                  0.0 if np.isfinite(m["first_yield_load_N"]) else 1.0, 0.5),
            check("first_yield_reference", "|first-yield load FE - Perry-Robertson (FE P_cr)| / Perry-Robertson "
                  "(model form: beam stresses)", abs(m["first_yield_load_N"] - pr) / pr, tol["first_yield_rel_tol"]),
            check("equilibrium", "|axial reaction at the midspan restraint| / end load, last increment "
                  "(the two end loads balance)", abs(rf[0]) / out["p_max_N"], tol["equilibrium_rel_tol"]),
            check("euler_range", "Euler stress / (yield / 2): elastic buckling governs at or below 1 "
                  "(Johnson range otherwise)", d["euler_stress_MPa"] / (sy / 2), 1.0, kind="validity"),
            check("moderate_deflection", "midspan deflection at first yield / length",
                  m["deflection_at_first_yield_mm"] / L, tol["deflection_over_length_max"], kind="validity"),
            check("slender", "thickness / length (beam-column references)", d["thickness_over_length"],
                  tol["thickness_over_length_max"], kind="validity"),
        ]
        strut_figure(pdir / "response.png", p, d, m, out, x, uz, shape, pr,
                     title=f"{point['label']}  (L {L:g} mm, {out['elements']} C3D8I, {len(P)} load increments)")
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
        # representative size (V / N)^(1/3) (Celik et al. 2008): the even division counts round the
        # cross-section differently from the nominal element size
        hs = tuple((_p(pt["parameters"], "length_mm") * _p(pt["parameters"], "width_mm")
                    * _p(pt["parameters"], "thickness_mm") / pt["solver_outputs"]["elements"]) ** (1 / 3)
                   for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine], "representative_sizes_mm": hs}
        for metric in sorted({r["metric"] for r in case["requirements"]} | {"critical_load_N"}):
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine), design_order=2)
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


def strut_figure(path, p, d, m, out, x, uz, shape, pr, *, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from harness.plotting import GRID, SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2

    P, w = np.array(out["load_N"]), np.array(out["midspan_deflection_mm"])
    vm = np.array(out["midspan_peak_von_mises_MPa"])
    e0, pcr = out["imperfection_mm"], m["critical_load_N"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(14, 4.2), facecolor=SURFACE)
    pp = np.linspace(0, min(P[-1], 0.985 * pcr), 200)
    a1.plot(cb.amplified_deflection(pp, pcr, e0), pp / 1e3, color=SERIES_2, lw=2, label="e0 / (1 - P/P_cr)")
    a1.plot(w, P / 1e3, "o", ms=3.5, color=SERIES_1, label="FE, geometrically nonlinear")
    a1.axhline(pcr / 1e3, color=TEXT_2, lw=1, ls="--", label=f"P_cr eigenvalue {pcr / 1e3:.2f} kN")
    a1.axhline(m["first_yield_load_N"] / 1e3, color=TEXT, lw=1, label=f"first yield {m['first_yield_load_N'] / 1e3:.2f} kN")
    a1.set_xlabel("midspan deflection (mm)")
    a1.set_ylabel("axial load (kN)")
    a1.set_title("Load against deflection", color=TEXT, loc="left", fontsize=10)
    dd = w - e0
    a2.plot(dd, dd / P * 1e3, "o", ms=3.5, color=SERIES_1, label="FE")
    xx = np.linspace(0, dd.max(), 50)
    a2.plot(xx, (xx / m["southwell_load_N"] + e0 / m["southwell_load_N"]) * 1e3, color=SERIES_2, lw=1.5,
            label=f"fit: P_cr {m['southwell_load_N'] / 1e3:.2f} kN")
    a2.set_xlabel("additional deflection d (mm)")
    a2.set_ylabel("d / P (mm/kN)")
    a2.set_title("Southwell plot", color=TEXT, loc="left", fontsize=10)
    a3.plot(P / 1e3, vm, "o-", ms=3, color=SERIES_1, label="FE peak von Mises at midspan")
    a3.axhline(_p(p, "yield_strength_MPa"), color=TEXT_2, lw=1, ls="--", label="yield")
    a3.axvline(pr / 1e3, color=SERIES_2, lw=1.5, label=f"Perry-Robertson {pr / 1e3:.2f} kN")
    a3.set_xlabel("axial load (kN)")
    a3.set_ylabel("stress (MPa)")
    a3.set_title("First yield", color=TEXT, loc="left", fontsize=10)
    for a in (a1, a2, a3):
        a.grid(color=GRID, lw=0.6)
        a.legend(frameon=False, fontsize=8, labelcolor=TEXT_2)
        a.tick_params(colors=TEXT_2)
        for s_ in a.spines.values():
            s_.set_color(GRID)
    fig.suptitle(title, color=TEXT, fontsize=10, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=120, facecolor=SURFACE)
    plt.close(fig)


STUDY = StrutBucklingStudy()

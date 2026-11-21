"""Study: the Turek-Hron elastic flag on its own (CSM1, CSM2), CalculiX against the benchmark.

Model:     ccx_flag (models/fea/flag_ccx.py): structured plane-strain C3D8I mesh of the flag,
           clamped on the cylinder arc; NLGEOM static under gravity (St. Venant-Kirchhoff), plus the
           linear modes of the unloaded flag
Reference: Turek and Hron (2006) point-A displacements (the requirement: the solid participant must
           reproduce them before it is coupled to the fluid); validation/elastica.py (inextensible
           large-deflection beam under its own weight, and the cantilever bending frequency) as the
           independent check; exact weight for equilibrium
Run-level: GCI on ux(A), uy(A) when the sweep is element_size_mm
"""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness.backend_base import Backend, failed
from harness.calculix import read_dat_frequency
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study
from studies.fin import find_ccx
from studies.strut_buckling import read_dat_blocks
from validation import elastica

WRITER = "models/fea/flag_ccx.py"
BENCH = ("benchmark_ux_A_mm", "benchmark_uy_A_mm")
GAUSS = (-1 / np.sqrt(3), 1 / np.sqrt(3))


def _load_writer(path: Path):
    spec = importlib.util.spec_from_file_location("flag_ccx_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_W = _load_writer(Path(__file__).resolve().parent.parent / WRITER)


def _p(params, k):
    return float(params[k])


def beam(params):
    """Plane-strain beam properties per unit depth (SI): E', EI, q = rho g h, mass per length."""
    nu, h = _p(params, "poisson_ratio"), _p(params, "flag_height_m")
    E = 2 * _p(params, "shear_modulus_Pa") * (1 + nu)
    Ep = elastica.plane_strain_modulus(E, nu)
    rho = _p(params, "density_kg_per_m3")
    return {"E": E, "E_plane_strain": Ep, "EI": Ep * h**3 / 12, "q": rho * _p(params, "gravity_m_per_s2") * h,
            "mass_per_length": rho * h, "L": _p(params, "flag_length_m")}


def clamp_load_share(m) -> float:
    """Share of the flag's weight that a consistent body load puts on the clamp nodes.

    CalculiX leaves loads applied directly on constrained nodes out of their reaction totals, so
    equilibrium is RF_y = W (1 - share). Exact for the bilinear quads of the first column (2 x 2 Gauss).
    """
    total = clamp = 0.0
    for j in range(m.ny):
        for i in range(m.nx):
            X = np.array([m.xy(i, j), m.xy(i + 1, j), m.xy(i + 1, j + 1), m.xy(i, j + 1)])
            for a in GAUSS:
                for b in GAUSS:
                    N = 0.25 * np.array([(1 - a) * (1 - b), (1 + a) * (1 - b), (1 + a) * (1 + b), (1 - a) * (1 + b)])
                    dN = 0.25 * np.array([[-(1 - b), (1 - b), (1 + b), -(1 + b)],
                                          [-(1 - a), -(1 + a), (1 + a), (1 - a)]])
                    detJ = abs(np.linalg.det(dN @ X))
                    total += detJ
                    if i == 0:
                        clamp += (N[0] + N[3]) * detJ
    return clamp / total, total


class CalculiXFlag(Backend):
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
        work = Path(tempfile.mkdtemp(prefix="flag_"))
        w = self.writer
        m = w.FlagMesh(params)
        n_inc = int(numerics["increments"])

        def files():
            return {f.name: f for f in sorted(work.glob("*")) if f.suffix in (".inp", ".dat", ".sta", ".log")
                    and f.stat().st_size < 60e6}

        (work / "static.inp").write_text(w.write_static_deck(params, m, n_inc), encoding="utf-8")
        if not self._run(work, "static"):
            return failed("CalculiX NLGEOM static failed") | {"files": files(), "cleanup": work}
        (work / "frequency.inp").write_text(w.write_frequency_deck(params, m), encoding="utf-8")
        if not self._run(work, "frequency"):
            return failed("CalculiX *FREQUENCY failed") | {"files": files(), "cleanup": work}
        freq = read_dat_frequency(work / "frequency.dat")["frequency_Hz"]
        a, lam, ux, uy, rfy, cl = m.point_a(), [], [], [], [], None
        for blk in read_dat_blocks(work / "static.dat"):
            if blk["kind"] == "displacements" and blk["set"] == "NA":
                row = blk["rows"][blk["rows"][:, 0] == a][0]
                lam.append(blk["time"])
                ux.append(row[1])
                uy.append(row[2])
            elif blk["kind"] == "total" and blk["set"] == "NCLAMP":
                rfy.append(blk["rows"][0][1])
            elif blk["kind"] == "displacements" and blk["set"] == "NCL":
                cl = blk["rows"]
        if len(lam) != n_inc or abs(lam[-1] - 1.0) > 1e-9 or cl is None:
            return failed(f"static step incomplete: {len(lam)} of {n_inc} increments, final time "
                          f"{lam[-1] if lam else 'none'}") | {"files": files(), "cleanup": work}
        share, area = clamp_load_share(m)
        ids = np.array(m.centreline_nodes())
        order = {int(n): k for k, n in enumerate(cl[:, 0])}
        rows = np.array([cl[order[int(n)]] for n in ids])
        x0 = np.array([m.xy(i, m.ny // 2)[0] for i in range(m.nx + 1)])
        series = {"x0_mm": x0, "x_mm": x0 + rows[:, 1], "y_mm": 200.0 + rows[:, 2]}
        weight = _p(params, "density_kg_per_m3") * 1e-12 * _p(params, "gravity_m_per_s2") * 1e3 * area * m.t
        outputs = {"divisions": [m.nx, m.ny], "elements": m.nx * m.ny, "area_mm2": area,
                   "load_fraction": lam, "ux_A_mm": ux, "uy_A_mm": uy, "reaction_y_N": rfy,
                   "weight_N": weight, "clamp_load_share": share, "frequencies_Hz": list(map(float, freq))}
        return {"success": True, "message": f"uy(A) {uy[-1]:.4f} mm, f1 {freq[0]:.4f} Hz ({m.nx} x {m.ny})",
                "nfev": n_inc, "series": series, "outputs": outputs, "files": files(), "cleanup": work}

    def tool_versions(self):
        return self._versions


class FlagCSMStudy(Study):
    name = "flag_csm"
    models = {"ccx_flag": CalculiXFlag}
    metrics = frozenset({"ux_A_mm", "uy_A_mm", "ux_A_deviation_pct", "uy_A_deviation_pct", "first_frequency_Hz"})
    param_names = _W.PARAMS + BENCH
    series_file = "centreline.csv"
    compare_description = "max relative difference over the deflected centreline"

    def derive(self, params):
        b = beam(params)
        if min(b["EI"], b["q"], b["L"]) <= 0:
            raise ValueError("positive stiffness, load and length")
        el = elastica.elastica_tip(b["q"], b["L"], b["EI"])
        return {"youngs_modulus_Pa": b["E"], "load_parameter_qL3_over_EI": b["q"] * b["L"] ** 3 / b["EI"],
                "linear_uy_A_mm": elastica.linear_tip(b["q"], b["L"], b["EI"])["uy"] * 1e3,
                "elastica_ux_A_mm": el["ux"] * 1e3, "elastica_uy_A_mm": el["uy"] * 1e3,
                "beam_frequency_Hz": elastica.cantilever_frequencies(b["L"], b["EI"], b["mass_per_length"], 1)[0],
                "height_over_length": _p(params, "flag_height_m") / b["L"]}

    def compute_metrics(self, series, params, case, outputs=None):
        ux, uy = outputs["ux_A_mm"][-1], outputs["uy_A_mm"][-1]
        bx, by = _p(params, BENCH[0]), _p(params, BENCH[1])
        return {"ux_A_mm": ux, "uy_A_mm": uy, "first_frequency_Hz": outputs["frequencies_Hz"][0],
                "ux_A_deviation_pct": 100 * abs(ux - bx) / abs(bx), "uy_A_deviation_pct": 100 * abs(uy - by) / abs(by)}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        p, d, mt, out = point["parameters"], point["derived"], point["metrics"], point["solver_outputs"]
        b = beam(p)
        lam = np.array(out["load_fraction"])
        uy = np.array(out["uy_A_mm"])
        path_ref = np.array([elastica.elastica_tip(f * b["q"], b["L"], b["EI"])["uy"] * 1e3 for f in lam])
        path_err = float(np.max(np.abs(uy - path_ref)) / abs(path_ref[-1]))
        # deflected centreline against the elastica, both as y(x) from the clamp
        el = elastica.elastica_tip(b["q"], b["L"], b["EI"])
        xr, yr = 250.0 + el["x"] * 1e3, 200.0 + el["y"] * 1e3
        x, y = np.asarray(series["x_mm"]), np.asarray(series["y_mm"])
        inside = (x >= xr[0]) & (x <= xr[-1])
        shape_err = float(np.max(np.abs(y[inside] - np.interp(x[inside], xr, yr))) / abs(el["uy"] * 1e3))
        rf = out["reaction_y_N"][-1]
        expect = out["weight_N"] * (1 - out["clamp_load_share"])
        f1 = out["frequencies_Hz"][0]
        checks = [
            check("increments_complete", "static step reached the full load (1 = not)", 0.0, 0.5),
            check("equilibrium", "|clamp reaction - weight carried through the elements| / weight (the weight "
                  "lumped on the clamp nodes is excluded from CalculiX's reaction total)",
                  abs(rf - expect) / out["weight_N"], tol["equilibrium_rel_tol"]),
            check("elastica_uy", "|uy(A) - elastica| / |elastica| (model form: inextensible beam, root on a straight "
                  "line)", abs(mt["uy_A_mm"] - d["elastica_uy_A_mm"]) / abs(d["elastica_uy_A_mm"]),
                  tol["elastica_uy_rel_tol"]),
            check("elastica_ux", "|ux(A) - elastica| / |elastica| (model form)",
                  abs(mt["ux_A_mm"] - d["elastica_ux_A_mm"]) / abs(d["elastica_ux_A_mm"]), tol["elastica_ux_rel_tol"]),
            check("load_path", "max over increments of |uy(A) - elastica at that load| / |elastica uy at full load| "
                  "(model form)", path_err, tol["elastica_uy_rel_tol"]),
            check("deflected_shape", "max |centreline y - elastica y| at the same x / |elastica uy(A)| (model form)",
                  shape_err, tol["elastica_uy_rel_tol"]),
            check("frequency_reference", "|f1 FE - Euler-Bernoulli cantilever| / beam value (model form)",
                  abs(f1 - d["beam_frequency_Hz"]) / d["beam_frequency_Hz"], tol["frequency_rel_tol"]),
            check("slender", "height / length (beam references)", d["height_over_length"],
                  tol["height_over_length_max"], kind="validity"),
        ]
        flag_figure(pdir / "response.png", p, d, out, x, y, xr, yr, lam, uy, path_ref,
                    title=f"{point['label']}  ({out['elements']} C3D8I, plane strain)")
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
        hs = tuple(np.sqrt(pt["solver_outputs"]["area_mm2"] / pt["solver_outputs"]["elements"]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine], "representative_sizes_mm": hs}
        for metric, req in (("ux_A_mm", "ux_A_deviation_pct"), ("uy_A_mm", "uy_A_deviation_pct"),
                            ("first_frequency_Hz", None)):
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine), design_order=2)
            detail[metric] = u
            c = check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, {describe(u)}",
                      u["uncertainty"], tol["gci_max"])
            checks.append(c | {"metric": req} if req else c)
        return checks, detail


def flag_figure(path, p, d, out, x, y, xr, yr, lam, uy, path_ref, *, title):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2, _style, plt

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.6, 1]})
    fig.patch.set_facecolor(SURFACE)
    a1.plot([250, 600], [200, 200], color=TEXT_2, lw=1.0, ls="--", label="undeformed")
    a1.plot(xr, yr, color=SERIES_2, lw=3, label="elastica (beam reference)")
    a1.plot(x, y, color=SERIES_1, lw=1.4, label="CalculiX centreline")
    a1.plot([600 + _p(p, BENCH[0])], [200 + _p(p, BENCH[1])], "o", mfc="none", color=TEXT, ms=8,
            label="Turek-Hron point A")
    a1.set_xlabel("x (mm)")
    a1.set_ylabel("y (mm)")
    a1.set_aspect("equal", adjustable="datalim")
    a2.plot(lam, -path_ref, color=SERIES_2, lw=3, label="elastica")
    a2.plot(lam, -uy, "o-", color=SERIES_1, ms=3, lw=1.2, label="CalculiX")
    a2.plot([1.0], [-_p(p, BENCH[1])], "o", mfc="none", color=TEXT, ms=8, label="Turek-Hron")
    a2.set_xlabel("load fraction (gravity)")
    a2.set_ylabel("drop of point A (mm)")
    for ax in (a1, a2):
        _style(ax)
        ax.legend(frameon=False, fontsize=8)
    fig.suptitle(title, fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = FlagCSMStudy()


# ====================================================================== CSM3 (dynamic)

BAND = {"uy_mean_mm": (-64.766, -63.607), "uy_amplitude_mm": (64.695, 65.160),
        "ux_mean_mm": (-14.645, -14.305), "frequency_Hz": (1.0956, 1.0995)}
# Turek-Hron CSM3: the range of the three published rows (level 4+0; dt 0.02, 0.01, 0.005, which row
# is which is not labelled on the benchmark page)


def _refined(t, u, k):
    """Parabolic refinement of the sample k (an extremum): (t, u)."""
    if k <= 0 or k >= len(u) - 1:
        return float(t[k]), float(u[k])
    a, b = (u[k + 1] - 2 * u[k] + u[k - 1]) / 2, (u[k + 1] - u[k - 1]) / 2
    if a == 0:
        return float(t[k]), float(u[k])
    s = -b / (2 * a)
    return float(t[k] + s * (t[k + 1] - t[k])), float(u[k] - b * b / (4 * a))


def _cycles(t, u):
    """Times of the downward crossings of the mid level, with hysteresis of a quarter amplitude.

    Robust to a higher mode riding on the main swing: the sudden release also excites mode 2 (6.6 Hz),
    which never decays without damping and made a plain local-extremum search find false troughs (a
    synthetic two-mode test read 1.71 Hz for 1.07; flag_csm3_dt revision 1)."""
    hi, lo = float(np.max(u)), float(np.min(u))
    mid, band = (hi + lo) / 2, (hi - lo) / 4
    out, armed = [], False
    for k in range(1, len(u)):
        if u[k] > mid + band:
            armed = True
        if armed and u[k - 1] > mid >= u[k]:
            out.append(float(t[k - 1] + (mid - u[k - 1]) * (t[k] - t[k - 1]) / (u[k] - u[k - 1])))
            armed = False
    return np.array(out)


def last_period(t, ux, uy):
    """Benchmark definition: max and min over the last full period; mean = (max + min) / 2,
    amplitude = (max - min) / 2, frequency = 1 / period. Periods run between downward mid-level
    crossings of uy (see _cycles); the mean frequency is taken over every full period."""
    t, ux, uy = (np.asarray(v, dtype=float) for v in (t, ux, uy))
    c = _cycles(t, uy)
    if len(c) < 2:
        return None
    t0, t1 = c[-2], c[-1]
    periods = np.diff(c)
    troughs = []
    for a, b in zip(c[:-1], c[1:]):
        idx = np.nonzero((t >= a) & (t <= b))[0]
        troughs.append(_refined(t, uy, idx[np.argmin(uy[idx])])[1])
    troughs = np.array(troughs)
    w = np.nonzero((t >= t0) & (t <= t1))[0]

    def span(u):
        return _refined(t, u, w[np.argmax(u[w])])[1], _refined(t, u, w[np.argmin(u[w])])[1]
    ymax, ymin = span(uy)
    xmax, xmin = span(ux)
    return {"uy_mean_mm": (ymax + ymin) / 2, "uy_amplitude_mm": (ymax - ymin) / 2,
            "ux_mean_mm": (xmax + xmin) / 2, "ux_amplitude_mm": (xmax - xmin) / 2,
            "frequency_Hz": float(1.0 / (t1 - t0)), "mean_frequency_Hz": float(1.0 / periods.mean()),
            "period_spread": float(np.ptp(periods) / periods.mean()),
            "trough_depth_spread": float(np.ptp(troughs) / abs(troughs.mean())),
            "uy_max_last_period_mm": ymax, "periods_seen": int(len(periods)), "t_window": [float(t0), float(t1)]}


def band_deviation(value, band):
    """Distance outside the published band, % of the nearest edge (0 inside it)."""
    lo, hi = min(band), max(band)
    if lo <= value <= hi:
        return 0.0
    edge = lo if value < lo else hi
    return 100 * abs(value - edge) / abs(edge)


def _band_metric(key):
    return f"{key.removesuffix('_mm').removesuffix('_Hz')}_band_dev_pct"


class CalculiXFlagDynamic(CalculiXFlag):
    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="flag3_"))
        w = self.writer
        m = w.FlagMesh(params)
        dt, t_end = _p(params, "time_step_s"), float(numerics["end_time_s"])

        def files():
            return {f.name: f for f in sorted(work.glob("*")) if f.suffix in (".inp", ".dat", ".sta", ".log")
                    and f.stat().st_size < 60e6}

        def history(job):
            T, X, Y = [0.0], [0.0], [0.0]
            for blk in read_dat_blocks(work / f"{job}.dat"):
                if blk["kind"] == "displacements" and blk["set"] == "NA":
                    T.append(blk["time"])
                    X.append(blk["rows"][0][1])
                    Y.append(blk["rows"][0][2])
            return np.array(T), np.array(X), np.array(Y)

        rr = float(numerics.get("newton_residual_rel", 1e-8))
        alpha = float(numerics.get("alpha", 0.0))
        (work / "dynamic.inp").write_text(w.write_dynamic_deck(params, m, dt, t_end, alpha=alpha, residual_rel=rr),
                                          encoding="utf-8")
        if not self._run(work, "dynamic"):
            return failed("CalculiX NLGEOM dynamic failed") | {"files": files(), "cleanup": work}
        t, ux, uy = history("dynamic")
        # small-amplitude companion: gravity / 1000 for a few periods, same mesh and time step; its
        # frequency must be the linear modal one (checks the time integrator on its own)
        small = dict(params) | {"gravity_m_per_s2": _p(params, "gravity_m_per_s2") * 1e-3}
        (work / "small.inp").write_text(w.write_dynamic_deck(small, m, dt, float(numerics["small_end_time_s"]),
                                                             alpha=alpha, residual_rel=rr),
                                        encoding="utf-8")
        (work / "frequency.inp").write_text(w.write_frequency_deck(params, m), encoding="utf-8")
        if not (self._run(work, "small") and self._run(work, "frequency")):
            return failed("CalculiX small-amplitude or *FREQUENCY run failed") | {"files": files(), "cleanup": work}
        ts, _, uys = history("small")
        n_exp = int(round(t_end / dt))
        if len(t) - 1 != n_exp or abs(t[-1] - t_end) > 1e-9 * t_end:
            return failed(f"dynamic step incomplete: {len(t) - 1} of {n_exp} increments") | {"files": files(),
                                                                                           "cleanup": work}
        lp, lps = last_period(t, ux, uy), last_period(ts, 0 * uys, uys)
        if lp is None or lps is None:
            return failed("fewer than two full periods in the history") | {"files": files(), "cleanup": work}
        freq = read_dat_frequency(work / "frequency.dat")["frequency_Hz"]
        series = {"t_s": t, "ux_A_mm": ux, "uy_A_mm": uy}
        outputs = {"divisions": [m.nx, m.ny], "elements": m.nx * m.ny, "increments": n_exp, "last_period": lp,
                   # mean over every full period: a sudden release also excites mode 2 (6.6 Hz), which never
                   # decays without damping and shifts single troughs (flag_csm3_dt revision 1)
                   "small_amplitude_frequency_Hz": lps["mean_frequency_Hz"],
                   "small_amplitude_last_period_frequency_Hz": lps["frequency_Hz"],
                   "small_amplitude_mm": lps["uy_amplitude_mm"],
                   "modal_frequency_Hz": float(freq[0])}
        return {"success": True, "message": f"uy {lp['uy_mean_mm']:.3f} +/- {lp['uy_amplitude_mm']:.3f} mm, "
                f"f {lp['frequency_Hz']:.4f} Hz ({n_exp} steps)", "nfev": n_exp, "series": series,
                "outputs": outputs, "files": files(), "cleanup": work}


class FlagCSM3Study(Study):
    name = "flag_csm3"
    models = {"ccx_flag_dynamic": CalculiXFlagDynamic}
    metrics = frozenset(set(BAND) | {_band_metric(k) for k in BAND})
    param_names = _W.PARAMS + ("time_step_s",)
    series_file = "point_A.csv"
    compare_description = "max relative difference of uy(A) over time"

    def derive(self, params):
        b = beam(params)
        dt = _p(params, "time_step_s")
        if dt <= 0:
            raise ValueError("positive time step")
        f = elastica.cantilever_frequencies(b["L"], b["EI"], b["mass_per_length"], 1)[0]
        return {"beam_frequency_Hz": f, "steps_per_linear_period": 1 / (f * dt),
                "height_over_length": _p(params, "flag_height_m") / b["L"]}

    def compute_metrics(self, series, params, case, outputs=None):
        lp = outputs["last_period"]
        out = {k: lp[k] for k in BAND}
        out |= {_band_metric(k): band_deviation(lp[k], BAND[k]) for k in BAND}
        return out

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        d, out = point["derived"], point["solver_outputs"]
        lp = out["last_period"]
        fs, fm = out["small_amplitude_frequency_Hz"], out["modal_frequency_Hz"]
        checks = [
            check("integrator_small_amplitude", "|mean frequency over every period of a gravity/1000 run - linear "
                  "modal f1| / f1 (the time integrator alone)", abs(fs - fm) / fm, tol["small_amplitude_rel_tol"]),
            check("returns_to_start", "max uy(A) over the last period / amplitude (undamped: the flag swings back to "
                  "its undeformed height)", abs(lp["uy_max_last_period_mm"]) / lp["uy_amplitude_mm"],
                  tol["energy_drift_max"]),
            check("periodic_troughs", "spread of the trough depths of uy(A) over all periods / mean depth",
                  lp["trough_depth_spread"], tol["energy_drift_max"]),
            check("periodic_periods", "spread of the periods / mean period", lp["period_spread"],
                  tol["period_spread_max"]),
            check("frequency_reference", "|f1 modal - Euler-Bernoulli cantilever| / beam value (model form)",
                  abs(fm - d["beam_frequency_Hz"]) / d["beam_frequency_Hz"], tol["frequency_rel_tol"]),
            check("periods_seen", "shortfall of full periods before the last one (needs >= 3)",
                  max(0.0, 3 - lp["periods_seen"]), 0.5),
            check("steps_per_period", "50 / time steps per linear period (below 1: at least 50 steps a period, period "
                  "error of the trapezoidal rule about (2 pi / 50)^2 / 12 = 0.13 %)",
                  50 / d["steps_per_linear_period"], 1.0, kind="validity"),
        ]
        csm3_figure(pdir / "response.png", series, lp, title=f"{point['label']}  ({out['elements']} C3D8I, "
                    f"dt {point['parameters']['time_step_s']:g} s)")
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "time_step_s":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: float(pt["parameters"]["time_step_s"]))
        if len(done) < 3:
            return [check("time_step_convergence", "needs >= 3 completed time steps", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(float(pt["parameters"]["time_step_s"]) for pt in fine)
        checks, detail = [], {"steps_used": [pt["label"] for pt in fine]}
        for metric in BAND:
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine), design_order=2)
            detail[metric] = u
            checks.append(check(f"time_step_{metric}", f"relative time-step uncertainty of {metric}, {describe(u)}",
                                u["uncertainty"], tol["gci_max"]) | {"metric": _band_metric(metric)})
        return checks, detail


def csm3_figure(path, series, lp, *, title):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2, _style, plt

    t, ux, uy = (np.asarray(series[k]) for k in ("t_s", "ux_A_mm", "uy_A_mm"))
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 5.4), sharex=True)
    fig.patch.set_facecolor(SURFACE)
    for ax, u, lab, key in ((a1, uy, "uy(A) (mm)", "uy_mean_mm"), (a2, ux, "ux(A) (mm)", "ux_mean_mm")):
        ax.plot(t, u, color=SERIES_1, lw=1.2, label="CalculiX")
        lo, hi = BAND[key]
        ax.axhspan(lo, hi, color=SERIES_2, alpha=0.35, lw=0, label="Turek-Hron mean (published rows)")
        ax.axvspan(*lp["t_window"], color=TEXT_2, alpha=0.08, lw=0, label="last period (measured)")
        ax.set_ylabel(lab)
        _style(ax)
    a1.legend(frameon=False, fontsize=8, ncol=3, loc="lower left")
    a2.set_xlabel("time (s)")
    fig.suptitle(f"{title}: uy {lp['uy_mean_mm']:.2f} ± {lp['uy_amplitude_mm']:.2f} mm, "
                 f"f {lp['frequency_Hz']:.4f} Hz", fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY_CSM3 = FlagCSM3Study()

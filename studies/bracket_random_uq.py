"""Study H: probabilistic uncertainty on study C (the bracket arm under random vibration).

Question: study C passes on nominal inputs. Is the PASS robust to what a project would not know exactly, and which
input would be worth measuring first? Inputs (independent, all synthetic; approved by the user 2026-11-23):
  damping        modal damping ratio, lognormal (median, sigma_ln)
  test_level_dB  the test's PSD level within its control tolerance, uniform +- tol dB (PSD factor 10^(dB / 10))
  sn_factor      a factor on the EN 1993-1-9 detail category, lognormal (median 1, CoV)
  thickness_mm   plate thickness, normal (nominal, sd)

Model:     cadquery_ccx_random_uq. Study C's CalculiX model (models/fea/bracket_random.py) solved at several plate
           thicknesses (and one off-grid thickness for the check), each giving a modal basis (frequencies,
           participation factors, tip mode shapes, modal hot-spot stresses). For each thickness and each damping on a
           log grid, study C's response (same functions, same frequency grid) gives the von Mises mean squares, the
           sigma_xx spectral moments at every hot-spot point and the tip mean square, per axis. A bicubic spline in
           (log damping, thickness) over their logarithms is the surrogate. The test level scales every mean square
           and moment exactly; the S-N factor enters the Dirlik damage integral exactly.
Outputs:   Monte Carlo (Sobol-sequence samples) of 3 sigma stress, 3 sigma tip displacement and damage; Sobol first
           and total indices (harness/uncertainty.py); per requirement of study C, FORM and importance sampling for
           the failure probability; the damping at which each requirement fails alone.
Checks:    every FE solve passes study C's harmonic and effective-mass checks; the nominal basis reproduces study C's
           numbers; the surrogate against direct evaluation off its grid (damping between nodes, the off-grid
           thickness); the Dirlik integration grid; FORM against importance sampling; importance-sampling CoV; Monte
           Carlo against importance sampling; design points inside the surrogate's range; Sobol intervals (run level,
           over the sample-size sweep).
"""

from __future__ import annotations

import math
import shutil
import tempfile
from pathlib import Path

import numpy as np
from scipy import stats
from scipy.interpolate import RectBivariateSpline
from scipy.optimize import brentq

from harness import uncertainty as U
from harness.backend_base import Backend, failed
from harness.checks import check
from harness.study import Study
from studies import bracket_random as R

INPUTS = ("damping", "test_level_dB", "sn_factor", "thickness_mm")
OUTPUTS = ("stress_3sigma_MPa", "tip_disp_3sigma_mm", "damage")
REQS = {"stress_3sigma_MPa": "stress_limit_MPa", "tip_disp_3sigma_mm": "clearance_mm", "damage": "damage_limit"}
PARAMS = R.PARAMS + ("damping_sigma_ln", "test_level_tolerance_dB", "sn_factor_cov", "thickness_sd_mm",
                     "damage_limit", "n_samples", "seed")


def _p(params, k):
    return float(params[k])


# ------------------------------------------------------------------------------------------------- the response
def load_basis(path: Path) -> dict:
    with np.load(path) as z:
        return {k: z[k] for k in z.files}


def response_moments(basis: dict, zeta: float, S0: float, f_lo: float, f_hi: float, n_log: int = 400,
                     n_res: int = 80) -> dict:
    """Study C's response for one basis and one damping, per axis (x, y, z) and hot-spot point: von Mises mean
    square, sigma_xx spectral moments (m0, m1, m2, m4) and the tip mean square; flat base PSD S0."""
    fn = np.asarray(basis["frequency_Hz"])
    wn, gam, phi, hs = 2 * np.pi * fn, basis["participation"], basis["phi_tip"], basis["hotspot_modal_stress"]
    f = R.freq_grid(fn, zeta, f_lo, f_hi, n_log, n_res)
    w = 2 * np.pi * f
    P = hs.shape[0]
    vm, mom, tip = np.zeros((3, P)), np.zeros((3, P, 4)), np.zeros(3)
    for a in range(3):
        q = R.modal_coords(wn, gam[:, a], zeta, w)
        u = phi.T @ q
        tip[a] = sum(R.integrate(np.abs(u[k]) ** 2 * S0, f) for k in range(3))
        s = np.einsum("pcm,mf->pcf", hs, q)
        vm[a] = [R.vm_mean_square(s[k], S0, f) for k in range(P)]
        sxx = np.abs(s[:, 0, :]) ** 2 * S0
        mom[a] = [R.spectral_moments(sxx[k], f) for k in range(P)]
    return {"vm_ms": vm, "moments": mom, "tip_ms": tip}


def dirlik_damage_vec(m: np.ndarray, T: float, dsc, nz: int = 4000) -> np.ndarray:
    """Study C's dirlik_damage for many moment sets at once: m (n, 4) = m0, m1, m2, m4; dsc scalar or (n,). Same
    range grid (1e-9 to 14 sqrt(m0), nz points, trapezoid), so nz = 4000 reproduces it."""
    m = np.atleast_2d(m)
    m0, m1, m2, m4 = (m[:, k][:, None] for k in range(4))
    xm = m1 / m0 * np.sqrt(m2 / m4)
    g = m2 / np.sqrt(m0 * m4)
    D1 = 2 * (xm - g ** 2) / (1 + g ** 2)
    Rr = (g - xm - D1 ** 2) / (1 - g - D1 + D1 ** 2)
    D2 = (1 - g - D1 + D1 ** 2) / (1 - Rr)
    D3 = 1 - D1 - D2
    Q = 1.25 * (g - D3 - D2 * Rr) / D1
    t = np.linspace(0.0, 1.0, nz)[None, :]
    s = 1e-9 + (14 * np.sqrt(m0) - 1e-9) * t
    Z = s / (2 * np.sqrt(m0))
    p = (D1 / Q * np.exp(-Z / Q) + D2 * Z / Rr ** 2 * np.exp(-Z ** 2 / (2 * Rr ** 2))
         + D3 * Z * np.exp(-Z ** 2 / 2)) / (2 * np.sqrt(m0))
    dsc = np.broadcast_to(np.asarray(dsc, float), (m.shape[0],))[:, None]
    integrand = p / R.ec3_cycles(s, dsc)
    return np.sqrt(m4[:, 0] / m2[:, 0]) * T * np.trapezoid(integrand, s, axis=1)


def outputs_from_moments(vm, mom, tip, T, dsc, nz=4000) -> np.ndarray:
    """(n, 3): 3 sigma von Mises (max over axes and points), 3 sigma tip (max over axes), damage (max over points of
    the sum over axes). vm (n, 3, P), mom (n, 3, P, 4), tip (n, 3); dsc scalar or (n,)."""
    n, _, P = vm.shape
    stress = 3 * np.sqrt(vm.reshape(n, -1).max(axis=1))
    tipd = 3 * np.sqrt(tip.max(axis=1))
    dsc = np.broadcast_to(np.asarray(dsc, float), (n,))
    dmg = np.zeros((n, P))
    for a in range(3):
        for k in range(P):
            dmg[:, k] += dirlik_damage_vec(mom[:, a, k, :], T, dsc, nz)
    return np.column_stack([stress, tipd, dmg.max(axis=1)])


class Surrogate:
    """Bicubic splines in (log damping, thickness) over the logarithms of every mean square and moment."""

    def __init__(self, zetas, thick, table):
        self.lz, self.h = np.log(np.asarray(zetas)), np.asarray(thick, float)
        first = table[0][0]
        self.P = first["vm_ms"].shape[1]
        flat = np.array([[np.concatenate([t["vm_ms"].ravel(), t["moments"].ravel(), t["tip_ms"]]) for t in row]
                         for row in table])                               # (Nz, Nh, Q)
        logq = np.log(np.maximum(flat, 1e-300))
        ky = min(3, len(self.h) - 1)
        self.splines = [RectBivariateSpline(self.lz, self.h, logq[:, :, j], kx=3, ky=ky) for j in range(logq.shape[2])]
        self.clipped = 0

    def __call__(self, zeta, h):
        zeta, h = np.atleast_1d(zeta).astype(float), np.atleast_1d(h).astype(float)
        lz = np.clip(np.log(zeta), self.lz[0], self.lz[-1])
        hc = np.clip(h, self.h[0], self.h[-1])
        self.clipped += int(np.sum((lz != np.log(zeta)) | (hc != h)))
        q = np.exp(np.column_stack([s.ev(lz, hc) for s in self.splines]))
        n, P = len(zeta), self.P
        return {"vm_ms": q[:, :3 * P].reshape(n, 3, P), "moments": q[:, 3 * P:15 * P].reshape(n, 3, P, 4),
                "tip_ms": q[:, 15 * P:15 * P + 3]}


def distributions(params: dict) -> list:
    tol = _p(params, "test_level_tolerance_dB")
    cov = _p(params, "sn_factor_cov")
    return [stats.lognorm(_p(params, "damping_sigma_ln"), scale=_p(params, "damping_ratio")),
            stats.uniform(-tol, 2 * tol),
            stats.lognorm(math.sqrt(math.log(1 + cov ** 2)), scale=1.0),
            stats.norm(_p(params, "thickness_mm"), _p(params, "thickness_sd_mm"))]


def make_model(sur: Surrogate, params: dict, nz: int, chunk: int = 2048):
    T, dsc = _p(params, "duration_per_axis_s"), _p(params, "detail_category_MPa")

    def model(X):
        X = np.atleast_2d(X)
        out = np.empty((len(X), 3))
        for i in range(0, len(X), chunk):
            x = X[i:i + chunk]
            r = sur(x[:, 0], x[:, 3])
            sc = 10 ** (x[:, 1] / 10)
            out[i:i + chunk] = outputs_from_moments(r["vm_ms"] * sc[:, None, None],
                                                    r["moments"] * sc[:, None, None, None],
                                                    r["tip_ms"] * sc[:, None], T, dsc * x[:, 2], nz)
        return out
    return model


def limits(params: dict) -> np.ndarray:
    return np.array([_p(params, "yield_MPa") / 1.5, _p(params, "clearance_mm"), _p(params, "damage_limit")])


# ------------------------------------------------------------------------------------------------- the backend
class CadQueryCalculiXRandomUQ(Backend):
    sources = (R.WRITER,)

    def __init__(self):
        self.fe = R.CadQueryCalculiXRandom()
        self._cache: dict = {}
        self._keep = Path(tempfile.mkdtemp(prefix="bracket_uq_fe_"))   # FE files, kept across points

    def close(self):
        shutil.rmtree(self._keep, ignore_errors=True)

    def prepare(self, source_dir=None, log_dir=None):
        self.fe.prepare(source_dir, log_dir)

    def tool_versions(self):
        return self.fe.tool_versions()

    def _fe(self, params, numerics, h):
        """Study C's solve at thickness h on the mesh made at the nominal thickness, z scaled (no remeshing noise).
        Cached across points; its files are returned with the first point that needed them."""
        keep = self._keep
        key = (round(h, 6), _p(params, "element_size_mm"), int(params["n_modes"]))
        if key not in self._cache:
            p = dict(params) | {"thickness_mm": h, "mesh_thickness_mm": _p(params, "thickness_mm")}
            res = self.fe.solve(p, numerics)
            sub = f"fe_h{h:.4f}"
            files = {}
            for name, src in (res.get("files") or {}).items():
                dst = keep / sub / name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
                files[f"{sub}/{name}"] = dst
            if res.get("cleanup"):
                shutil.rmtree(res["cleanup"], ignore_errors=True)
            if not res["success"]:
                raise RuntimeError(f"FE solve at thickness {h} mm failed: {res['message']}")
            o = res["outputs"]
            eff = np.array(o["effective_mass"]).sum(axis=0)[:3] / np.array(o["total_effective_mass"])[:3]
            self._cache[key] = {
                "basis": load_basis(keep / sub / "modal_basis.npz"), "files": files, "new": True,
                "summary": {"thickness_mm": h, "stress_3sigma_MPa": o["stress_3sigma_MPa"],
                            "tip_disp_3sigma_mm": o["tip_disp_3sigma_mm"], "damage_dirlik": o["damage_dirlik"],
                            "first_frequency_Hz": o["frequency_Hz"][0], "harmonic_max_rel_error": max(o["harmonic_max_rel_error"]),
                            "harmonic_steps": o["harmonic_steps"], "effective_mass_min": float(eff.min()),
                            "nodes": o.get("nodes")}}
        return self._cache[key]

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="bracket_uq_"))
        try:
            out, series, files = uq_analysis(self, params, numerics, work)
        except Exception as e:  # noqa: BLE001
            return failed(f"{type(e).__name__}: {e}") | {"cleanup": work}
        return {"success": True, "message": (f"pf_any {out['pf_any']:.2e}; damage p99 {out['damage_p99']:.2e}; "
                                             f"{out['n_model_calls']} surrogate calls"),
                "nfev": out["n_model_calls"], "series": series, "outputs": out, "files": files, "cleanup": work}


def direct_outputs(basis, zeta, params, numerics, scale=1.0, sn=1.0, nz=4000) -> np.ndarray:
    S0 = _p(params, "psd_g2_per_Hz") * R.G ** 2
    r = response_moments(basis, zeta, S0, _p(params, "f_low_Hz"), _p(params, "f_high_Hz"),
                         int(numerics.get("n_log", 400)), int(numerics.get("n_res", 80)))
    return outputs_from_moments(r["vm_ms"][None] * scale, r["moments"][None] * scale, r["tip_ms"][None] * scale,
                                _p(params, "duration_per_axis_s"), _p(params, "detail_category_MPa") * sn, nz)[0]


def uq_analysis(backend, params, numerics, work: Path):
    nodes = [float(h) for h in numerics["thickness_nodes_mm"]]
    h_chk = float(numerics["thickness_check_mm"])
    h0, z0 = _p(params, "thickness_mm"), _p(params, "damping_ratio")
    fe = {h: backend._fe(params, numerics, h) for h in nodes + [h_chk]}
    files = {k: v for h in fe if fe[h].pop("new", False) for k, v in fe[h]["files"].items()}
    S0 = _p(params, "psd_g2_per_Hz") * R.G ** 2
    f_lo, f_hi = _p(params, "f_low_Hz"), _p(params, "f_high_Hz")
    n_log, n_res = int(numerics.get("n_log", 400)), int(numerics.get("n_res", 80))
    zetas = np.geomspace(float(numerics["zeta_grid_min"]), float(numerics["zeta_grid_max"]), int(numerics["zeta_grid_n"]))
    table = [[response_moments(fe[h]["basis"], z, S0, f_lo, f_hi, n_log, n_res) for h in nodes] for z in zetas]
    sur = Surrogate(zetas, nodes, table)
    nz = int(numerics.get("dirlik_points", 1000))
    model = make_model(sur, params, nz)
    dists = distributions(params)
    lim = limits(params)

    # 1. nominal: the basis at h0 reproduces study C; the surrogate at the nominal point
    if h0 not in fe:
        raise ValueError("the nominal thickness must be one of the thickness nodes")
    nom_direct = direct_outputs(fe[h0]["basis"], z0, params, numerics)
    s = fe[h0]["summary"]
    nom_fe = np.array([s["stress_3sigma_MPa"], s["tip_disp_3sigma_mm"], s["damage_dirlik"]])
    x_nom = np.array([[z0, 0.0, 1.0, h0]])
    nom_sur = model(x_nom)[0]
    nom_sur_4000 = make_model(sur, params, 4000)(x_nom)[0]

    # 2. surrogate against direct evaluation off its grid
    zc = [float(z) for z in numerics["zeta_check"]]
    off = []
    for z in zc:
        for h in (h_chk, h0):
            d = direct_outputs(fe[h]["basis"], z, params, numerics, nz=nz)
            m = model(np.array([[z, 0.0, 1.0, h]]))[0]
            off.append({"zeta": z, "thickness_mm": h, "direct": d.tolist(), "surrogate": m.tolist(),
                        "rel_error": (np.abs(m / d - 1)).tolist()})
    off_err = np.array([o["rel_error"] for o in off])

    # 3. Monte Carlo and Sobol indices (outputs: stress, tip, log10 damage)
    n, seed = int(params["n_samples"]), int(params["seed"])
    sur.clipped = 0
    tr = lambda y: np.column_stack([y[:, 0], y[:, 1], np.log10(y[:, 2])])       # noqa: E731
    sob = U.sobol_indices(lambda X: tr(model(X)), dists, n, seed=seed, n_boot=int(numerics.get("n_boot", 200)),
                          return_samples=True)
    clipped_mc = sur.clipped
    Y = np.concatenate([sob["fA"], sob["fB"]])
    Y[:, 2] = 10 ** Y[:, 2]
    mc = [U.failure_probability(lim[j] - Y[:, j]) for j in range(3)]
    mc_any = U.failure_probability(np.min(1 - Y / lim[None, :], axis=1))

    # 4. FORM and importance sampling per requirement, g = ln(limit) - ln(value)
    rel = []
    for j in range(3):
        gj = lambda x, j=j: float(math.log(lim[j]) - math.log(model(x[None, :])[0, j]))   # noqa: E731
        try:
            fo = U.form(gj, dists, max_iter=int(numerics.get("form_max_iter", 60)))
        except RuntimeError as e:
            rel.append({"output": OUTPUTS[j], "form_error": str(e)})
            continue
        sur.clipped = 0
        imp = U.importance_sampling(lambda X, j=j: np.log(lim[j]) - np.log(model(X)[:, j]), dists, fo["u_star"],
                                    int(numerics.get("is_samples", 20000)), seed=seed + 11 + j)
        x_star = fo["x_star"]
        rel.append({"output": OUTPUTS[j], "limit": float(lim[j]), "beta": fo["beta"], "pf_form": fo["pf"],
                    "x_star": dict(zip(INPUTS, map(float, x_star))), "alpha": dict(zip(INPUTS, map(float, fo["alpha"]))),
                    "form_iterations": fo["iterations"], "pf_is": imp["pf"], "is_cov": imp["cov"],
                    "is_ci": list(imp["ci"]), "is_hits": imp["hits"], "is_clipped": sur.clipped,
                    "x_star_in_range": bool(zetas[0] <= x_star[0] <= zetas[-1] and nodes[0] <= x_star[3] <= nodes[-1]),
                    "pf_mc": mc[j]["pf"], "mc_ci": list(mc[j]["ci"]), "mc_failures": mc[j]["failures"]})

    # 5. the damping at which each requirement fails alone (other inputs nominal)
    zfail = {}
    for j in range(3):
        f = lambda lz, j=j: math.log(model(np.array([[math.exp(lz), 0.0, 1.0, h0]]))[0, j] / lim[j])   # noqa: E731
        a, b = math.log(zetas[0]), math.log(zetas[-1])
        if f(a) < 0:
            zfail[OUTPUTS[j]] = {"zeta": None, "note": f"no failure down to the grid's {zetas[0]:.2e}"}
        elif f(b) > 0:
            zfail[OUTPUTS[j]] = {"zeta": None, "note": "fails across the whole grid"}
        else:
            zfail[OUTPUTS[j]] = {"zeta": math.exp(brentq(f, a, b, xtol=1e-6))}

    pf_is = [r.get("pf_is", math.inf) for r in rel]
    names = ("stress", "tip", "logdamage")
    out = {"inputs": list(INPUTS), "distributions": {
               "damping": f"lognormal median {z0}, sigma_ln {_p(params, 'damping_sigma_ln')}",
               "test_level_dB": f"uniform +- {_p(params, 'test_level_tolerance_dB')} dB",
               "sn_factor": f"lognormal median 1, CoV {_p(params, 'sn_factor_cov')}",
               "thickness_mm": f"normal {h0}, sd {_p(params, 'thickness_sd_mm')}"},
           "fe": [fe[h]["summary"] for h in nodes + [h_chk]], "thickness_nodes_mm": nodes, "thickness_check_mm": h_chk,
           "zeta_grid": [float(zetas[0]), float(zetas[-1]), len(zetas)],
           "nominal_fe": nom_fe.tolist(), "nominal_direct": nom_direct.tolist(), "nominal_surrogate": nom_sur.tolist(),
           "nominal_surrogate_dirlik4000": nom_sur_4000.tolist(), "offgrid": off,
           "offgrid_max_rel_error": off_err.max(axis=0).tolist(),
           "sobol": {nm: {"S1": dict(zip(INPUTS, sob["S1"][k].tolist())), "ST": dict(zip(INPUTS, sob["ST"][k].tolist())),
                          "S1_ci": dict(zip(INPUTS, sob["S1_ci"][k].tolist())),
                          "ST_ci": dict(zip(INPUTS, sob["ST_ci"][k].tolist()))} for k, nm in enumerate(names)},
           "n_samples": n, "n_model_calls": int(sob["n_calls"]), "mc_clipped": clipped_mc,
           "mc_quantiles": {OUTPUTS[j]: {q: float(np.quantile(Y[:, j], q)) for q in (0.5, 0.9, 0.99, 0.999)}
                            for j in range(3)},
           "mc_pf_any": mc_any["pf"], "mc_pf_any_ci": list(mc_any["ci"]),
           "reliability": rel, "damping_to_fail": zfail,
           "pf_any": float(min(1.0, sum(pf_is))),
           "damage_p99": float(np.quantile(Y[:, 2], 0.99)),
           "stress_3sigma_p99_MPa": float(np.quantile(Y[:, 0], 0.99)),
           "tip_3sigma_p99_mm": float(np.quantile(Y[:, 1], 0.99))}
    qs = np.linspace(0.001, 0.999, 999)
    series = {"probability": qs} | {f"{OUTPUTS[j]}_quantile": np.quantile(Y[:, j], qs) for j in range(3)}
    return out, series, files


# --------------------------------------------------------------------------------------------------- the study
class BracketRandomUQStudy(Study):
    name = "bracket_random_uq"
    models = {"cadquery_ccx_random_uq": CadQueryCalculiXRandomUQ}
    metrics = frozenset({"pf_any", "damage_p99", "stress_3sigma_p99_MPa", "tip_3sigma_p99_mm",
                         "st_logdamage_damping", "st_logdamage_test_level", "st_logdamage_sn_factor",
                         "st_logdamage_thickness"})
    param_names = PARAMS
    series_file = "quantiles.csv"
    compare_description = "max relative difference over the output quantile curves"

    def derive(self, params):
        for k in ("damping_sigma_ln", "sn_factor_cov", "thickness_sd_mm"):
            if _p(params, k) <= 0:
                raise ValueError(f"{k} must be positive")
        return {"stress_limit_MPa": _p(params, "yield_MPa") / 1.5, "n_model_calls": int(params["n_samples"]) * 6}

    def compute_metrics(self, series, params, case, outputs=None):
        st = outputs["sobol"]["logdamage"]["ST"]
        return {"pf_any": outputs["pf_any"], "damage_p99": outputs["damage_p99"],
                "stress_3sigma_p99_MPa": outputs["stress_3sigma_p99_MPa"], "tip_3sigma_p99_mm": outputs["tip_3sigma_p99_mm"],
                "st_logdamage_damping": st["damping"], "st_logdamage_test_level": st["test_level_dB"],
                "st_logdamage_sn_factor": st["sn_factor"], "st_logdamage_thickness": st["thickness_mm"]}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        out = point["solver_outputs"]
        fe = out["fe"]
        nf, nd, ns = (np.array(out[k]) for k in ("nominal_fe", "nominal_direct", "nominal_surrogate"))
        off = np.array(out["offgrid_max_rel_error"])
        rel = [r for r in out["reliability"] if "pf_is" in r]
        form_is = max((abs(math.log(r["pf_is"] / r["pf_form"])) for r in rel if r["pf_is"] > 0 and r["pf_form"] > 0),
                      default=math.inf)
        mc_is = max((0.0 if r["mc_ci"][0] <= r["pf_is"] <= r["mc_ci"][1] else 1.0) for r in rel) if rel else math.inf
        checks = [
            check("fe_harmonic", "max over the FE solves of study C's harmonic check (modal sum against CalculiX)",
                  max(f["harmonic_max_rel_error"] if f["harmonic_steps"] == 3 else math.inf for f in fe),
                  tol["harmonic_rel_tol"]),
            check("fe_effective_mass", "1 - least effective-mass fraction over x, y, z and the FE solves",
                  1 - min(f["effective_mass_min"] for f in fe), 1 - tol["effective_mass_min"]),
            check("nominal_reproduces_study_c", "max |response from the saved basis / study C's own numbers - 1| over "
                  "stress, tip and damage at the nominal point", float(np.max(np.abs(nd / nf - 1))),
                  tol["basis_rel_tol"]),
            check("surrogate_nominal", "max |surrogate / direct - 1| over stress and tip at the nominal point "
                  "(damping between grid nodes)", float(np.max(np.abs(ns[:2] / nd[:2] - 1))), tol["surrogate_rel_tol"]),
            check("surrogate_offgrid_stress_tip", "max |surrogate / direct - 1| over stress and tip at the check "
                  "dampings, on the off-grid thickness and the nominal one", float(off[:2].max()),
                  tol["surrogate_rel_tol"]),
            check("surrogate_offgrid_damage", "max |surrogate / direct - 1| of the damage at the same points",
                  float(off[2]), tol["surrogate_damage_rel_tol"]),
            check("dirlik_grid", "|nominal damage with the sampling grid / with study C's 4000 points - 1|",
                  abs(ns[2] / out["nominal_surrogate_dirlik4000"][2] - 1), tol["dirlik_grid_rel_tol"]),
            check("form_vs_importance_sampling", "max over the requirements of |ln(pf importance sampling / pf FORM)|",
                  form_is, math.log(tol["form_is_factor"])),
            check("importance_sampling_cov", "max coefficient of variation of the importance-sampling estimates",
                  max((r["is_cov"] for r in rel), default=math.inf), tol["is_cov_max"]),
            check("mc_vs_importance_sampling", "importance-sampling estimate outside the Monte Carlo Wilson 95 % "
                  "interval for any requirement (0 = inside for all)", mc_is, 0.0),
            check("design_points_in_range", "design points outside the surrogate's damping and thickness range "
                  "(count)", float(sum(not r["x_star_in_range"] for r in rel) + (3 - len(rel))), 0.0),
        ]
        uq_figure(pdir / "uq.png", series, out, case, title=point["label"])
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "n_samples":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: pt["parameters"]["n_samples"])
        if len(done) < 2:
            return [check("sobol_convergence", "needs >= 2 completed sample sizes", math.inf, 0.0)], {}
        big, prev = done[-1], done[-2]
        sb, sp = big["solver_outputs"]["sobol"], prev["solver_outputs"]["sobol"]
        width = max(0.5 * (ci[1] - ci[0]) for nm in sb for ci in sb[nm]["ST_ci"].values())
        shift = max(abs(sb[nm]["ST"][i] - sp[nm]["ST"][i]) for nm in sb for i in INPUTS)
        detail = {"largest": big["label"], "previous": prev["label"], "st_ci_halfwidth_max": width,
                  "st_change_max": shift}
        return [check("sobol_ci_width", f"max half-width of the total-index 95 % intervals at {big['label']}",
                      width, tol["sobol_ci_max"]),
                check("sobol_stable", f"max change of a total index from {prev['label']} to {big['label']}",
                      shift, tol["sobol_ci_max"])], detail


def uq_figure(path, series, out, case, *, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, _style

    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2), facecolor=SURFACE)
    p = np.asarray(series["probability"])
    lim = {r["output"]: r["limit"] for r in out["reliability"] if "limit" in r}
    a = ax[0]
    a.semilogx(np.asarray(series["damage_quantile"]), p, color=SERIES_1, lw=1.5)
    if "damage" in lim:
        a.axvline(lim["damage"], color=SERIES_2, lw=1.2, label=f"limit {lim['damage']:g}")
    a.set_xlabel("qualification damage (Dirlik, Miner over 3 axes)")
    a.set_ylabel("cumulative probability")
    a.legend(frameon=False, fontsize=8)
    a = ax[1]
    st = out["sobol"]["logdamage"]["ST"]
    s1 = out["sobol"]["logdamage"]["S1"]
    y = np.arange(len(INPUTS))
    a.barh(y + 0.2, [st[i] for i in INPUTS], height=0.4, color=SERIES_1, label="total")
    a.barh(y - 0.2, [s1[i] for i in INPUTS], height=0.4, color=SERIES_2, label="first order")
    a.set_yticks(y, INPUTS)
    a.set_xlabel("Sobol index of log10 damage")
    a.legend(frameon=False, fontsize=8)
    a = ax[2]
    rel = [r for r in out["reliability"] if "beta" in r]
    a.bar([r["output"].split("_")[0] for r in rel], [r["beta"] for r in rel], color=SERIES_1)
    a.set_ylabel("reliability index beta (FORM)")
    for i, r in enumerate(rel):
        a.text(i, r["beta"], f"pf {r['pf_is']:.1e}", ha="center", va="bottom", fontsize=8, color=TEXT)
    for a in ax:
        _style(a)
    fig.suptitle(f"{title}: P(fail any) <= {out['pf_any']:.1e} (sum over requirements); damage 99th percentile "
                 f"{out['damage_p99']:.2e}", fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


STUDY = BracketRandomUQStudy()

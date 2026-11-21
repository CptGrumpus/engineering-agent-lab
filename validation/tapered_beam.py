"""Linearly tapered rectangular cantilever with a tip load: beam theory and its optimum.

Independent reference for the bracket optimisation loop (models/fea/tapered_bracket.py).
It shares no code with the finite element path.

Cantilever of length L, constant width b, height h(x) = h_r + (h_t - h_r) x / L from the
clamped root (x = 0) to the loaded tip (x = L), tip load F.

    tip deflection  d = F int_0^L (L - x)^2 / (E I(x)) dx + F int_0^L dx / (kappa G A(x))
                    (unit-load method, bending plus Timoshenko shear; Cowper kappa)
    nominal stress  s(x) = M / Z = 6 F (L - x) / (b h(x)^2)     (statics and section geometry)

For h_t / h_r < 1/2 the nominal stress peaks inside the span, at x / L = 2 - 1 / c with
c = 1 - h_t / h_r, not at the root.

Exact checks on the reference itself (tests/test_tapered_bracket.py): the prismatic limit
equals validation/beam_theory.timoshenko_tip; the interior peak location matches a dense
search; the optimum satisfies its active constraints.
"""

from __future__ import annotations

import numpy as np
from scipy.integrate import quad
from scipy.optimize import minimize


def cowper_kappa(nu: float) -> float:
    return 10 * (1 + nu) / (12 + 11 * nu)


def height(x, L, hr, ht):
    return hr + (ht - hr) * np.asarray(x, float) / L


def tip_deflection(F, L, E, nu, b, hr, ht) -> float:
    G = E / (2 * (1 + nu))
    kap = cowper_kappa(nu)
    bend = quad(lambda x: (L - x) ** 2 / (E * b * height(x, L, hr, ht) ** 3 / 12), 0, L,
                epsabs=0, epsrel=1e-12)[0]
    shear = quad(lambda x: 1.0 / (kap * G * b * height(x, L, hr, ht)), 0, L, epsabs=0, epsrel=1e-12)[0]
    return F * (bend + shear)


def nominal_stress(x, F, L, b, hr, ht):
    return 6 * F * (L - np.asarray(x, float)) / (b * height(x, L, hr, ht) ** 2)


def peak_nominal_stress(F, L, b, hr, ht) -> tuple[float, float]:
    """(peak nominal bending stress, its x)."""
    c = 1 - ht / hr
    x_star = (2 - 1 / c) * L if c > 0.5 else 0.0
    return float(nominal_stress(x_star, F, L, b, hr, ht)), float(x_star)


def volume(L, b, hr, ht) -> float:
    return b * L * (hr + ht) / 2


def optimum(F, L, E, nu, b, deflection_max, stress_max, bounds, margin=0.0) -> dict:
    """Lightest (h_r, h_t) with d <= deflection_max (1 - margin), s_peak <= stress_max (1 - margin),
    within bounds = ((hr_lo, hr_hi), (ht_lo, ht_hi)). Multi-start SLSQP on the smooth beam model."""
    dmax, smax = deflection_max * (1 - margin), stress_max * (1 - margin)
    # the stress limit at 401 stations along the span: smooth constraints (the peak itself has a
    # kink where it leaves the root at h_t / h_r = 1/2, which SLSQP cannot handle)
    xs = np.linspace(0, L, 401)[:-1]
    cons = [{"type": "ineq", "fun": lambda v: 1 - tip_deflection(F, L, E, nu, b, *v) / dmax},
            {"type": "ineq", "fun": lambda v: 1 - nominal_stress(xs, F, L, b, *v) / smax},
            # and the exact peak, which the stations can miss by ~1e-5 (smooth away from c = 1/2)
            {"type": "ineq", "fun": lambda v: 1 - peak_nominal_stress(F, L, b, *v)[0] / smax}]
    best = None
    for start in ((bounds[0][1], bounds[1][1]), (0.5 * sum(bounds[0]), 0.5 * sum(bounds[1])),
                  (bounds[0][1], bounds[1][0])):
        r = minimize(lambda v: volume(L, b, *v), start, method="SLSQP", bounds=bounds,
                     constraints=cons, options={"ftol": 1e-12, "maxiter": 500})
        # judged on the constraints, not on SLSQP's flag: at a corner with several active
        # constraints it stops with "positive directional derivative" at the optimum
        ok = all(np.all(c["fun"](r.x) >= -1e-6) for c in cons) and \
            peak_nominal_stress(F, L, b, *r.x)[0] <= smax * (1 + 1e-6)
        if ok and (best is None or r.fun < best.fun):
            best = r
    if best is None:
        raise RuntimeError("no feasible beam-theory optimum")
    hr, ht = (float(v) for v in best.x)
    s, xs = peak_nominal_stress(F, L, b, hr, ht)
    return {"root_height_mm": hr, "tip_height_mm": ht, "volume_mm3": volume(L, b, hr, ht),
            "tip_deflection_mm": tip_deflection(F, L, E, nu, b, hr, ht),
            "peak_stress_MPa": s, "peak_stress_x_mm": xs}

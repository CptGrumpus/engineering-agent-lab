"""1D straight-fin theory with a convective tip (independent reference).

Incropera, DeWitt, Bergman & Lavine, Fundamentals of Heat and Mass Transfer,
Table 3.4 case A. Uniform cross-section A = w t, perimeter P = 2 (w + t),
m^2 = h P / (k A), excess temperature theta = T - T_air, x from the base:

    theta / theta_b = [cosh m(L - x) + (h / m k) sinh m(L - x)]
                      / [cosh mL + (h / m k) sinh mL]
    q_f = sqrt(h P k A) theta_b [sinh mL + (h / m k) cosh mL]
                                / [cosh mL + (h / m k) sinh mL]

Assumes the temperature is uniform over each cross-section (Biot number
h (t/2) / k << 1). SI units inside; inputs in the case-file units.
Does not import from models/.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import brentq


def _geometry(p: dict) -> tuple[float, float, float, float, float]:
    t = float(p["thickness_mm"]) * 1e-3
    w = float(p["width_mm"]) * 1e-3
    L = float(p["length_mm"]) * 1e-3
    k = float(p["conductivity_W_per_mK"])
    h = float(p["htc_W_per_m2K"])
    return t, w, L, k, h


def fin_parameter(p: dict) -> float:
    """m in 1/m."""
    t, w, _, k, h = _geometry(p)
    return math.sqrt(h * 2 * (w + t) / (k * w * t))


def biot(p: dict) -> float:
    """Biot number across the half-thickness, h (t/2) / k."""
    t, _, _, k, h = _geometry(p)
    return h * t / 2 / k


def excess_ratio(p: dict, x_m) -> np.ndarray:
    """theta(x) / theta_b for x in metres from the base."""
    _, _, L, k, h = _geometry(p)
    m = fin_parameter(p)
    r = h / (m * k)
    x = np.asarray(x_m, dtype=float)
    return ((np.cosh(m * (L - x)) + r * np.sinh(m * (L - x)))
            / (math.cosh(m * L) + r * math.sinh(m * L)))


def temperature_C(p: dict, x_m) -> np.ndarray:
    tb, ta = float(p["base_temperature_C"]), float(p["air_temperature_C"])
    return ta + (tb - ta) * excess_ratio(p, x_m)


def tip_temperature_C(p: dict) -> float:
    return float(temperature_C(p, float(p["length_mm"]) * 1e-3))


def heat_flow_W(p: dict) -> float:
    t, w, L, k, h = _geometry(p)
    m = fin_parameter(p)
    r = h / (m * k)
    theta_b = float(p["base_temperature_C"]) - float(p["air_temperature_C"])
    return (math.sqrt(h * 2 * (w + t) * k * w * t) * theta_b
            * (math.sinh(m * L) + r * math.cosh(m * L))
            / (math.cosh(m * L) + r * math.sinh(m * L)))


def fin_efficiency(p: dict) -> float:
    """q_f / (h A_exposed theta_b), A_exposed = P L + A_tip."""
    t, w, L, _, h = _geometry(p)
    theta_b = float(p["base_temperature_C"]) - float(p["air_temperature_C"])
    area = 2 * (w + t) * L + w * t
    return heat_flow_W(p) / (h * area * theta_b)


def breakeven_htc(p: dict, tip_limit_C: float) -> float:
    """h (W/m^2K) at which the 1D tip temperature equals tip_limit_C."""
    def f(h):
        return tip_temperature_C(p | {"htc_W_per_m2K": h}) - tip_limit_C
    return brentq(f, 1e-3, 1e5, xtol=1e-10)

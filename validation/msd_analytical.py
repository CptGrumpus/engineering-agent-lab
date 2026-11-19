"""Closed-form step response of a linear mass-spring-damper.

Independent reference for models/msd.py. Deliberately self-contained: it takes
raw m, c, k, F values and does not import the model code.

Reference: standard second-order system step response, e.g. Ogata,
"Modern Control Engineering", or Rao, "Mechanical Vibrations".
"""

from __future__ import annotations

import math

import numpy as np

# Treat |zeta - 1| below this as critically damped to avoid 0/0 in the
# under/over-damped formulas.
_CRITICAL_BAND = 1e-9


def damping_ratio(m: float, c: float, k: float) -> float:
    return c / (2.0 * math.sqrt(k * m))


def step_response(t, m: float, c: float, k: float, force: float) -> np.ndarray:
    """Displacement x(t) for a step force applied at t=0 from rest."""
    t = np.asarray(t, dtype=float)
    xs = force / k
    wn = math.sqrt(k / m)
    zeta = damping_ratio(m, c, k)

    if abs(zeta - 1.0) < _CRITICAL_BAND:
        return xs * (1.0 - np.exp(-wn * t) * (1.0 + wn * t))

    if zeta < 1.0:
        root = math.sqrt(1.0 - zeta**2)
        wd = wn * root
        return xs * (
            1.0 - np.exp(-zeta * wn * t) * (np.cos(wd * t) + (zeta / root) * np.sin(wd * t))
        )

    root = math.sqrt(zeta**2 - 1.0)
    s1 = -wn * (zeta - root)  # slow pole
    s2 = -wn * (zeta + root)  # fast pole
    return xs * (1.0 + (s2 * np.exp(s1 * t) - s1 * np.exp(s2 * t)) / (s1 - s2))


def overshoot_pct(m: float, c: float, k: float) -> float:
    """Closed-form peak overshoot (percent of final value)."""
    zeta = damping_ratio(m, c, k)
    if zeta >= 1.0 - _CRITICAL_BAND:
        return 0.0
    return 100.0 * math.exp(-zeta * math.pi / math.sqrt(1.0 - zeta**2))


def static_deflection(k: float, force: float) -> float:
    return force / k

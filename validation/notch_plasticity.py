"""Notch-root plasticity: Neuber's rule and Glinka's strain-energy method, residual stress.

Independent reference for the notched-strap proof-load study (models/fea/strap_plastic.py). It
shares no code with the finite element path; both read the same material table from the case.

Material: linear elastic (E) up to the first table stress, then isotropic hardening along a
multilinear curve of (plastic strain, stress) points; the uniaxial strain is
eps(s) = s / E + eps_p(s), eps_p interpolated linearly in the table (0 below the first point).

At a notch root (uniaxial stress at the free surface) with elastic peak stress s_e = Kt S:
    Neuber (1961)    s * eps = s_e^2 / E                      (upper estimate of the strain)
    Glinka (1985)    integral_0^eps s d eps = s_e^2 / (2 E)    (lower estimate; equivalent strain energy)
For contained yielding in plane stress the true notch strain lies between the two, usually near
Neuber. After unloading, if the unloading is elastic (no reversed yield), the residual stress is
    s_res = s_max - s_e.

Exact checks on the reference itself (tests/test_strap_plastic.py): both rules return the elastic
point when s_e is below yield; Glinka's strain never exceeds Neuber's; the strain-energy integral
of the piecewise-linear curve is exact.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import brentq


class Material:
    def __init__(self, E: float, plastic_strain, stress):
        self.E = float(E)
        self.ep = np.asarray(plastic_strain, float)
        self.s = np.asarray(stress, float)
        if self.ep[0] != 0 or np.any(np.diff(self.ep) <= 0) or np.any(np.diff(self.s) <= 0):
            raise ValueError("table must start at zero plastic strain and increase in both columns")

    @property
    def yield_stress(self) -> float:
        return float(self.s[0])

    def plastic_strain(self, s):
        s = np.asarray(s, float)
        return np.where(s <= self.s[0], 0.0, np.interp(s, self.s, self.ep, right=np.nan))

    def strain(self, s):
        return np.asarray(s, float) / self.E + self.plastic_strain(s)

    def energy(self, s) -> float:
        """integral_0^eps(s) sigma d eps, exact for the piecewise-linear curve."""
        s = float(s)
        w = min(s, self.s[0]) ** 2 / (2 * self.E)
        if s <= self.s[0]:
            return w
        knots = np.concatenate([self.s[self.s < s], [s]])
        eps = self.strain(knots)
        return w + float(np.sum(0.5 * (knots[1:] + knots[:-1]) * np.diff(eps)))


def neuber(mat: Material, s_elastic: float) -> tuple[float, float]:
    """(stress, strain) at the notch root by Neuber's rule."""
    target = s_elastic**2 / mat.E
    if s_elastic <= mat.yield_stress:
        return s_elastic, s_elastic / mat.E
    s = brentq(lambda v: v * float(mat.strain(v)) - target, mat.yield_stress, mat.s[-1], xtol=1e-12)
    return float(s), float(mat.strain(s))


def glinka(mat: Material, s_elastic: float) -> tuple[float, float]:
    """(stress, strain) at the notch root by Glinka's equivalent strain-energy density method."""
    target = s_elastic**2 / (2 * mat.E)
    if s_elastic <= mat.yield_stress:
        return s_elastic, s_elastic / mat.E
    s = brentq(lambda v: mat.energy(v) - target, mat.yield_stress, mat.s[-1], xtol=1e-12)
    return float(s), float(mat.strain(s))


def residual_after_elastic_unloading(s_max: float, s_elastic: float) -> float:
    return s_max - s_elastic

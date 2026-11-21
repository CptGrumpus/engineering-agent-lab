"""Pinned-pinned column in compression: elastic buckling, imperfection amplification, first yield.

Independent reference for the strut buckling study (models/fea/strut_ccx.py). It shares no
code with the finite element path.

Column of length L, rectangular b x h section (buckling about the weak axis, bending through h),
modulus E, Poisson nu, yield stress s_y, both ends pinned on the centroidal axis.

    Euler            P_E = pi^2 E I / L^2,  I = b h^3 / 12
    with shear       P_cr = P_E / (1 + P_E / (kappa G A))       (Engesser; Timoshenko & Gere 2.18)
    Johnson          s_cr = s_y - (s_y / (2 pi))^2 (L / r)^2 / E for s_E > s_y / 2 (inelastic range;
                     the elastic eigenvalue overstates the capacity there)
    imperfection     initial bow w0(x) = e0 sin(pi x / L): the midspan deflection under P is
                     e0 / (1 - P / P_cr)   (exact for this shape within small-deflection theory)
    Southwell        additional deflection d = w - e0 against d / P is a straight line of
                     slope P_cr (Southwell 1932): P_cr is read from the nonlinear response alone
    first yield      Perry-Robertson: the mean stress s at which s (1 + eta / (1 - s / s_E)) = s_y,
                     eta = e0 c / r^2, c = h / 2, r^2 = I / A

Exact checks on the reference itself (tests/test_strut_buckling.py): the shear correction
vanishes for a slender column; the Perry-Robertson root satisfies its defining equation; the
Southwell fit recovers P_cr exactly from amplification-law data.
"""

from __future__ import annotations

import numpy as np


def section(b, h):
    A = b * h
    I = b * h**3 / 12
    return A, I, np.sqrt(I / A)


def euler_load(E, b, h, L):
    return np.pi**2 * E * section(b, h)[1] / L**2


def cowper_kappa(nu):
    return 10 * (1 + nu) / (12 + 11 * nu)


def critical_load(E, nu, b, h, L):
    """Euler load with the Engesser shear correction (Cowper shear coefficient)."""
    PE = euler_load(E, b, h, L)
    G = E / (2 * (1 + nu))
    return PE / (1 + PE / (cowper_kappa(nu) * G * b * h))


def johnson_stress(E, sy, b, h, L):
    r = section(b, h)[2]
    return sy - (sy / (2 * np.pi)) ** 2 * (L / r) ** 2 / E


def euler_range(E, sy, b, h, L):
    """True where elastic buckling governs (Euler stress at or below half the yield stress)."""
    A = section(b, h)[0]
    return euler_load(E, b, h, L) / A <= sy / 2


def amplified_deflection(P, P_cr, e0):
    """Total midspan deflection of a column with an initial sinusoidal bow e0."""
    return e0 / (1 - np.asarray(P, float) / P_cr)


def perry_robertson_load(E, sy, b, h, L, e0, P_cr=None):
    """Axial load at first yield of the imperfect column (elastic, sinusoidal bow e0)."""
    A, I, r = section(b, h)
    sE = (P_cr if P_cr is not None else euler_load(E, b, h, L)) / A
    eta = e0 * (h / 2) / r**2
    a = 0.5 * (sy + (1 + eta) * sE)
    s = a - np.sqrt(a * a - sy * sE)
    return float(s * A)


def southwell(P, w_total, e0):
    """P_cr and the fitted e0 from the nonlinear response: d / P = d / P_cr + e0 / P_cr."""
    P = np.asarray(P, float)
    d = np.asarray(w_total, float) - e0
    slope, intercept = np.polyfit(d, d / P, 1)
    P_cr = 1.0 / slope
    return float(P_cr), float(intercept * P_cr)

"""Hertz line contact: an elastic cylinder on an elastic half-space (plane strain).

Independent reference for models/fea/hertz_contact.py (K. L. Johnson, Contact
Mechanics, 1985, chapter 4: two-dimensional contact of cylinders). Inputs are
the line load per unit length P' (N/mm), the cylinder radius R and both
bodies' elastic constants.

    1/E* = (1 - nu1^2)/E1 + (1 - nu2^2)/E2
    a    = sqrt(4 P' R / (pi E*))          contact half-width
    p0   = 2 P' / (pi a)                    peak pressure
    p(x) = p0 sqrt(1 - x^2/a^2),  |x| <= a

Below the centre of the contact (x = 0, depth z):
    sigma_z = -p0 a / sqrt(a^2 + z^2)
    sigma_x = -(p0 / a) ((a^2 + 2 z^2) / sqrt(a^2 + z^2) - 2 z)
    tau_1   = (sigma_x - sigma_z) / 2,  max 0.300 p0 at z = 0.786 a
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize_scalar


def effective_modulus(E1, nu1, E2=None, nu2=None) -> float:
    E2 = E1 if E2 is None else E2
    nu2 = nu1 if nu2 is None else nu2
    return 1.0 / ((1 - nu1**2) / E1 + (1 - nu2**2) / E2)


def line_contact(P, R, E1, nu1, E2=None, nu2=None) -> dict:
    Es = effective_modulus(E1, nu1, E2, nu2)
    a = float(np.sqrt(4 * P * R / (np.pi * Es)))
    p0 = 2 * P / (np.pi * a)
    z_star = float(minimize_scalar(lambda z: -subsurface_shear(z, a, p0), bounds=(0.1 * a, 2 * a),
                                   method="bounded", options={"xatol": 1e-10 * a}).x)
    return {"E_star_MPa": Es, "half_width_mm": a, "peak_pressure_MPa": p0,
            "max_shear_MPa": float(subsurface_shear(z_star, a, p0)), "max_shear_depth_mm": z_star}


def pressure(x, a, p0):
    x = np.asarray(x, float)
    return p0 * np.sqrt(np.clip(1 - (x / a) ** 2, 0.0, None))


def subsurface_stresses(z, a, p0):
    z = np.asarray(z, float)
    r = np.sqrt(a**2 + z**2)
    sz = -p0 * a / r
    sx = -(p0 / a) * ((a**2 + 2 * z**2) / r - 2 * z)
    return sx, sz


def subsurface_shear(z, a, p0):
    sx, sz = subsurface_stresses(z, a, p0)
    return (sx - sz) / 2

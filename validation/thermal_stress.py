"""Thermal stress in a plate strip held at both ends: beam theory in plane strain.

Independent reference for the stress stage of the cold-plate chain (models/thermal/
cold_plate_ccx.py). It shares no code with the finite element path.

The plate is wide and held in width (plane strain, eps_z = 0) and spans x = 0..L between
two supports that stop axial growth and rotation (clamped ends) and hold the mid-plane
height. Through the thickness y (centroid y_c, thickness t) the temperature rise above the
stress-free assembly temperature is dT(x, y). Plane sections remain plane and the
through-thickness stress is zero, so with E' = E / (1 - nu^2) and alpha' = (1 + nu) alpha

    sigma_x = E' (e(x) + kappa(x) (y - y_c) - alpha' dT)
    N  = integral sigma_x dy          constant (no axial load between the supports)
    M  = integral sigma_x (y - y_c) dy = M0 + V x   (no transverse load)

Clamped ends: integral e dx = 0 (no length change), integral kappa dx = 0 (no end rotation)
and integral (L - x) kappa dx = 0 (no end deflection). That fixes N, M0 and V. Then

    sigma_z = nu sigma_x - E alpha dT        (eps_z = 0, sigma_y = 0)

Exact case (tests): uniform dT gives sigma_x = sigma_z = -E alpha dT / (1 - nu) everywhere.
Model form: beam theory neglects sigma_y and the shear deformation; it is accurate away from
the supports (Saint-Venant, about a plate thickness) and where dT varies slowly along x on
the scale of t.
"""

from __future__ import annotations

import numpy as np


def _seg_integrals(y, f):
    """Exact integrals of a piecewise-linear f over y: (int f dy, int f y dy) per column.

    f has shape (nx, ny) on nodes y (ny,)."""
    y0, y1 = y[:-1], y[1:]
    f0, f1 = f[:, :-1], f[:, 1:]
    d = y1 - y0
    i0 = np.sum(0.5 * (f0 + f1) * d, axis=1)
    # int over [y0, y1] of (f0 + (f1 - f0) s) (y0 + d s) d ds, s in [0, 1]
    i1 = np.sum(d * (f0 * y0 + (f0 * d + (f1 - f0) * y0) / 2 + (f1 - f0) * d / 3), axis=1)
    return i0, i1


def clamped_strip(x, y, dT, *, E, nu, alpha):
    """Stress field from beam theory on the node grid.

    x (nx,) positions between the supports (x[0] and x[-1] are the supports), y (ny,)
    through-thickness positions, dT (nx, ny) temperature rise. Units consistent (mm, MPa).
    Returns sigma_x, sigma_z, von_mises (nx, ny) and the section resultants."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    dT = np.asarray(dT, float)
    Ep, ap = E / (1 - nu**2), (1 + nu) * alpha
    t = y[-1] - y[0]
    yc = 0.5 * (y[0] + y[-1])
    eta = y - yc
    inertia = t**3 / 12
    i0, i1 = _seg_integrals(eta, dT)
    T_mean = i0 / t                     # section-mean temperature rise
    M_T = i1                            # thermal moment integral dT (y - y_c) dy
    xs = x - x[0]
    L = xs[-1]

    def integ(f):                       # trapezoid: exact for piecewise-linear data
        return float(np.sum(0.5 * (f[1:] + f[:-1]) * np.diff(xs)))

    N = -Ep * ap * t * integ(T_mean) / L
    # kappa = (M0 + V x)/(E' I) + alpha' M_T / I ; solve integral kappa = 0, integral (L-x) kappa = 0
    w0, w1 = np.ones_like(xs), xs
    A = np.array([[integ(w0), integ(w1)],
                  [integ((L - xs) * w0), integ((L - xs) * w1)]]) / (Ep * inertia)
    rhs = -ap / inertia * np.array([integ(M_T), integ((L - xs) * M_T)])
    M0, V = np.linalg.solve(A, rhs)
    M = M0 + V * xs
    kappa = M / (Ep * inertia) + ap * M_T / inertia
    e = N / (Ep * t) + ap * T_mean
    sx = Ep * (e[:, None] + kappa[:, None] * eta[None, :] - ap * dT)
    sz = nu * sx - E * alpha * dT
    vm = np.sqrt(sx**2 + sz**2 - sx * sz)
    return {"sigma_x": sx, "sigma_z": sz, "von_mises": vm, "N": N, "M0": M0, "V": V,
            "membrane_stress": N / t, "T_mean": T_mean, "M_T": M_T}


def uniform_restrained_stress(E, nu, alpha, dT):
    """sigma_x = sigma_z for a uniform rise dT, held in x and z, free in y."""
    return -E * alpha * dT / (1 - nu)


def clamped_strip_buckling_stress(E, nu, t, L):
    """Euler buckling stress of a clamped-clamped plate strip in plane strain:
    sigma_cr = 4 pi^2 E' I / (t L^2) = pi^2 E' t^2 / (3 L^2)."""
    return np.pi**2 * E / (1 - nu**2) * t**2 / (3 * L**2)

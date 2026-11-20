"""Free vibration of a clamped-free (cantilever) beam: independent references.

Euler-Bernoulli (exact): f_n = (beta_n L)^2 / (2 pi L^2) * sqrt(E I / (rho A)),
beta_n L = 1.87510, 4.69409, 7.85476, 10.99554, ...

Timoshenko (shear deformation and rotary inertia): solved here by a 1D finite
element model, independent of the 3D model under test. Two-node elements with
linear interpolation of deflection w and rotation theta, one-point (reduced)
integration of the shear term so they do not lock, and consistent mass for
translation (rho A) and rotation (rho I). With n_el elements the frequency
error falls as 1/n_el^2; the default is far below the 3D model's tolerances
(checked against the Euler-Bernoulli limit in the tests).

Torsion (Saint-Venant, warping free): f_n = (2n - 1) / (4 L) * sqrt(G J / (rho I_p)),
with J for a rectangle from Roark (a >= b half-widths):
J = a b^3 [16/3 - 3.36 (b/a) (1 - b^4 / (12 a^4))]. A clamped root restrains
warping and stiffens short bars, so this is a model-form reference.

Units: N, mm, tonne, s (density in t/mm^3, frequency in Hz).
"""

from __future__ import annotations

import numpy as np
from scipy.linalg import eigh

BETA_L = (1.875104068711961, 4.694091132974175, 7.854757438237613, 10.99554073487547)


def euler_bernoulli(n: int, L, E, I, rho, A) -> float:
    return BETA_L[n - 1] ** 2 / (2 * np.pi * L**2) * np.sqrt(E * I / (rho * A))


def cowper_kappa_rect(nu: float) -> float:
    return 10 * (1 + nu) / (12 + 11 * nu)


def timoshenko_modes(L, E, nu, I, A, rho, n_modes: int = 4, n_el: int = 1200,
                     kappa: float | None = None):
    """(frequencies in Hz, x nodes, deflection mode shapes [n_modes, n_nodes])."""
    G = E / (2 * (1 + nu))
    k = cowper_kappa_rect(nu) if kappa is None else kappa
    kGA = k * G * A
    le = L / n_el
    ndof = 2 * (n_el + 1)
    K = np.zeros((ndof, ndof))
    M = np.zeros((ndof, ndof))
    kb = E * I / le * np.array([[0, 0, 0, 0], [0, 1, 0, -1], [0, 0, 0, 0], [0, -1, 0, 1]], float)
    b = np.array([-1 / le, -0.5, 1 / le, -0.5])          # shear strain at the midpoint
    ks = kGA * le * np.outer(b, b)
    mw = rho * A * le / 6 * np.array([[2, 1], [1, 2]])
    mr = rho * I * le / 6 * np.array([[2, 1], [1, 2]])
    me = np.zeros((4, 4))
    me[np.ix_([0, 2], [0, 2])] = mw
    me[np.ix_([1, 3], [1, 3])] = mr
    for e in range(n_el):
        idx = slice(2 * e, 2 * e + 4)
        K[idx, idx] += kb + ks
        M[idx, idx] += me
    free = np.arange(2, ndof)                              # clamp w and theta at x = 0
    Kf, Mf = K[np.ix_(free, free)], M[np.ix_(free, free)]
    lam, vec = eigh(Kf, Mf, subset_by_index=[0, n_modes - 1])
    freqs = np.sqrt(lam) / (2 * np.pi)
    w = np.zeros((n_modes, n_el + 1))
    w[:, 1:] = vec[0::2, :].T
    return freqs, np.linspace(0, L, n_el + 1), w


def effective_mass_fraction(x, w, rho, A, L) -> float:
    """Fraction of the beam mass in a bending mode, for base excitation along w."""
    m = rho * A
    num = np.trapezoid(m * w, x) ** 2
    den = np.trapezoid(m * w**2, x) * (m * L)
    return float(num / den)


def torsion_rect_J(width, thickness) -> float:
    a, b = max(width, thickness) / 2, min(width, thickness) / 2
    return a * b**3 * (16 / 3 - 3.36 * (b / a) * (1 - b**4 / (12 * a**4)))


def torsion_saint_venant(n: int, L, E, nu, rho, width, thickness) -> float:
    G = E / (2 * (1 + nu))
    J = torsion_rect_J(width, thickness)
    Ip = width * thickness * (width**2 + thickness**2) / 12
    return (2 * n - 1) / (4 * L) * np.sqrt(G * J / (rho * Ip))


def mac(a, b) -> float:
    """Modal assurance criterion between two mode-shape vectors (1 = identical shape)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    return float(np.dot(a, b) ** 2 / (np.dot(a, a) * np.dot(b, b)))

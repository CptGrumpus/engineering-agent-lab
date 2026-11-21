"""Cantilever under its own weight: linear beam theory and the large-deflection elastica.

Independent reference for the Turek-Hron CSM tests (the elastic flag: clamped at one end, gravity
as a dead load). Units are the caller's; everything per unit depth for a plane-strain strip.

Elastica (inextensible Euler-Bernoulli, no shear): arc length s from the clamp, slope theta(s),
uniform dead load q per unit (undeformed) length acting in -y. Moment equilibrium of the free part
[s, L] gives

    EI theta''(s) = q (L - s) cos theta(s),   theta(0) = 0,   theta'(L) = 0

and the tip displacement is (int cos theta ds - L, int sin theta ds). For small q it tends to the
linear result u_y = -q L^4 / (8 EI), and u_x ~ -(1/2) int theta^2 ds (second order).

Free vibration (linear, Euler-Bernoulli): f_n = (beta_n L)^2 / (2 pi L^2) sqrt(EI / (rho A)).
"""

from __future__ import annotations

import numpy as np
from scipy.integrate import cumulative_trapezoid, solve_bvp

BETA_L = (1.8751040687119611, 4.6940911329741, 7.8547574382376)   # cantilever roots of cos cosh = -1


def plane_strain_modulus(E: float, nu: float) -> float:
    """Bending modulus of a wide strip (plane strain): E / (1 - nu^2)."""
    return E / (1.0 - nu * nu)


def linear_tip(q: float, L: float, EI: float) -> dict:
    """Linear cantilever under a uniform load q (per length): tip deflection and slope."""
    return {"uy": -q * L**4 / (8 * EI), "ux": 0.0, "slope": -q * L**3 / (6 * EI)}


def elastica_tip(q: float, L: float, EI: float, n: int = 2001, tol: float = 1e-10) -> dict:
    """Large-deflection cantilever under a uniform dead load q (per undeformed length) in -y."""
    k = q / EI
    s = np.linspace(0.0, L, n)

    def f(s, y):                       # y = (theta, theta')
        return np.vstack([y[1], k * (L - s) * np.cos(y[0])])

    def bc(ya, yb):
        return np.array([ya[0], yb[1]])

    lin = -k * (L**3 - (L - s) ** 3) / 6.0          # linear slope as the starting guess
    guess = np.vstack([lin, -k * (L - s) ** 2 / 2.0])
    sol = solve_bvp(f, bc, s, guess, tol=tol, max_nodes=200000)
    if not sol.success:
        raise RuntimeError(f"elastica BVP did not converge: {sol.message}")
    th = sol.sol(s)[0]
    x = cumulative_trapezoid(np.cos(th), s, initial=0.0)
    y = cumulative_trapezoid(np.sin(th), s, initial=0.0)
    return {"ux": float(x[-1] - L), "uy": float(y[-1]), "slope": float(th[-1]), "s": s, "x": x, "y": y,
            "theta": th, "load_parameter": k * L**3}


def cantilever_frequencies(L: float, EI: float, mass_per_length: float, modes: int = 3) -> list[float]:
    """Linear Euler-Bernoulli bending frequencies (Hz) of a clamped-free beam."""
    return [b**2 / (2 * np.pi * L**2) * np.sqrt(EI / mass_per_length) for b in BETA_L[:modes]]

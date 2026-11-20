"""Laminar flow between parallel plates: exact and correlation references.

Fully developed (plane Poiseuille) flow, gap H, mean velocity U, viscosity mu,
y measured from the lower wall:

    u(y)    = 6 U (y/H) (1 - y/H)          (u_max = 1.5 U)
    -dp/dx  = 12 mu U / H^2
    tau_w   = 6 mu U / H  = (-dp/dx) H / 2  (force balance on the fluid slab)

Hydraulic diameter of a parallel-plate channel: D_h = 2H.

Developing flow from a uniform inlet profile (Shah & London, "Laminar Flow
Forced Convection in Ducts", 1978; also Shah, J. Fluids Eng. 100 (1978) 177):

    L_hy / D_h  = 0.315 / (1 + 0.0175 Re) + 0.011 Re
    f_app Re    = 3.44 / sqrt(x+)
                  + (24 + K/(4 x+) - 3.44 / sqrt(x+)) / (1 + C x+^-2),
                  x+ = x / (D_h Re),  K(inf) = 0.674,  C = 2.9e-5
    dp(0 -> x)  = 4 f_app (x / D_h) * rho U^2 / 2

f_app is the Fanning apparent friction factor (wall friction plus momentum
change in the entrance region). The correlation is quoted to within a few
percent of the boundary-layer solutions, so it is a model-form reference, not
an exact one.
"""

from __future__ import annotations

import math

import numpy as np


def hydraulic_diameter(H: float) -> float:
    return 2.0 * H


def reynolds(U: float, H: float, rho: float, mu: float) -> float:
    return rho * U * hydraulic_diameter(H) / mu


def velocity_profile(y, U: float, H: float):
    eta = np.asarray(y) / H
    return 6.0 * U * eta * (1.0 - eta)


def pressure_gradient(U: float, H: float, mu: float) -> float:
    """-dp/dx (Pa/m, positive) for fully developed flow."""
    return 12.0 * mu * U / H**2


def wall_shear_stress(U: float, H: float, mu: float) -> float:
    return 6.0 * mu * U / H


def entrance_length(U: float, H: float, rho: float, mu: float) -> float:
    Re = reynolds(U, H, rho, mu)
    return hydraulic_diameter(H) * (0.315 / (1.0 + 0.0175 * Re) + 0.011 * Re)


def apparent_friction_re(x_plus: float) -> float:
    s = 3.44 / math.sqrt(x_plus)
    return s + (24.0 + 0.674 / (4.0 * x_plus) - s) / (1.0 + 2.9e-5 / x_plus**2)


def pressure_drop_developing(L: float, U: float, H: float, rho: float, mu: float) -> float:
    """Pressure drop (Pa) from a uniform inlet over length L (Shah & London)."""
    Re = reynolds(U, H, rho, mu)
    Dh = hydraulic_diameter(H)
    f_app = apparent_friction_re(L / (Dh * Re)) / Re
    return 4.0 * f_app * (L / Dh) * 0.5 * rho * U**2


# Kinetic-energy flux coefficient of plane Poiseuille flow: <u^3> / U^3 = 54/35.
ALPHA_POISEUILLE = 54.0 / 35.0


def total_pressure_drop_uniform_entry(L, U, H, rho, mu) -> float:
    """Flux-weighted total-pressure drop over a channel with a uniform entry
    profile (alpha = 1) and a fully developed exit profile (alpha = 54/35)."""
    return (pressure_drop_developing(L, U, H, rho, mu)
            - (ALPHA_POISEUILLE - 1.0) * 0.5 * rho * U**2)


def lubrication_friction(q: float, mu: float, heights, dx: float) -> float:
    """Friction pressure loss int 12 mu q / h(x)^3 dx (locally fully developed flow),
    for flow q per unit width through a duct of slowly varying height h(x) (m),
    sampled at uniform spacing dx (trapezoidal rule)."""
    h = np.asarray(heights, float)
    return float(np.trapezoid(12.0 * mu * q / h**3, dx=dx))


def header_total_pressure_drop(H, L, Hs, Ls, Lc, U, rho, mu, contraction_height) -> float:
    """Approximate supply-to-outlet total-pressure drop (Pa), lengths in m.

    Supply duct and contraction: locally fully developed friction (lubrication
    theory). Channel: Shah & London from a uniform entry. The real entry profile
    lies between uniform and developed, so this is a model-form estimate.
    """
    q = U * H
    s = np.linspace(0.0, 1.0, 2001)
    supply = 12.0 * mu * q * Ls / Hs**3
    contraction = lubrication_friction(q, mu, contraction_height(s, H, Hs), Lc / (len(s) - 1))
    return supply + contraction + total_pressure_drop_uniform_entry(L, U, H, rho, mu)

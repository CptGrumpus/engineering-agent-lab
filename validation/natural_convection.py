"""Study 11, natural convection and radiation: references (no CFD).

- de Vahl Davis, "Natural convection of air in a square cavity: a bench mark numerical solution", Int. J. Numer.
  Methods Fluids 3, 249-264 (1983), Table V (read from the paper, checked against the page image 2026-11-24):
  2D square cavity of side L, Boussinesq fluid, Pr = 0.71, vertical walls at Th (x = 0) and Tc, horizontal walls
  insulated, no slip. Lengths scaled by L, velocities by kappa / L, T = (T - Tc) / (Th - Tc). u_max is the largest
  horizontal velocity on the vertical mid-plane (at height z), w_max the largest vertical velocity on the horizontal
  mid-plane (at x), Nu the average Nusselt number over the cavity, Nu_half on the vertical mid-plane, Nu_0 on the hot
  wall. Table VII: estimated error of the bench mark 0.1 / 0.2 / 0.3 / 1 % at Ra 1e3 / 1e4 / 1e5 / 1e6.
- Two grey diffuse surfaces exchanging radiation (net exchange between two surfaces forming an enclosure; e.g.
  Incropera and DeWitt, Fundamentals of Heat and Mass Transfer, Table 13.3): infinite parallel plates and long
  concentric cylinders.
"""

from __future__ import annotations

SIGMA = 5.670374419e-8   # W / (m^2 K^4), Stefan-Boltzmann constant (CODATA 2018, exact by the 2019 SI definition)

PRANDTL = 0.71
#: Ra -> bench mark solution (de Vahl Davis 1983, Table V)
DE_VAHL_DAVIS = {
    1e3: {"u_max": 3.649, "u_max_z": 0.813, "w_max": 3.697, "w_max_x": 0.178, "Nu": 1.118, "Nu_half": 1.118,
          "Nu_0": 1.117, "Nu_max": 1.505, "Nu_max_z": 0.092, "psi_mid": 1.174},
    1e4: {"u_max": 16.178, "u_max_z": 0.823, "w_max": 19.617, "w_max_x": 0.119, "Nu": 2.243, "Nu_half": 2.243,
          "Nu_0": 2.238, "Nu_max": 3.528, "Nu_max_z": 0.143, "psi_mid": 5.071},
    1e5: {"u_max": 34.73, "u_max_z": 0.855, "w_max": 68.59, "w_max_x": 0.066, "Nu": 4.519, "Nu_half": 4.519,
          "Nu_0": 4.509, "Nu_max": 7.717, "Nu_max_z": 0.081, "psi_mid": 9.111},
    1e6: {"u_max": 64.63, "u_max_z": 0.850, "w_max": 219.36, "w_max_x": 0.0379, "Nu": 8.800, "Nu_half": 8.799,
          "Nu_0": 8.817, "Nu_max": 17.925, "Nu_max_z": 0.0378, "psi_mid": 16.32},
}
#: Table VII: estimated error of the bench mark solution, fraction
DE_VAHL_DAVIS_ERROR = {1e3: 0.001, 1e4: 0.002, 1e5: 0.003, 1e6: 0.01}


def rayleigh(g: float, beta: float, dT: float, L: float, nu: float, kappa: float) -> float:
    return g * beta * dT * L ** 3 / (nu * kappa)


def parallel_plates_flux(T1: float, T2: float, eps1: float, eps2: float) -> float:
    """Net radiative flux (W/m^2) from plate 1 to plate 2, infinite grey diffuse parallel plates."""
    return SIGMA * (T1 ** 4 - T2 ** 4) / (1.0 / eps1 + 1.0 / eps2 - 1.0)


def concentric_cylinders_per_length(T1: float, T2: float, eps1: float, eps2: float, r1: float, r2: float) -> float:
    """Net radiative heat (W per m of length) from the inner cylinder (r1) to the outer (r2), long, grey, diffuse."""
    import math

    A1 = 2 * math.pi * r1
    return SIGMA * A1 * (T1 ** 4 - T2 ** 4) / (1.0 / eps1 + (r1 / r2) * (1.0 / eps2 - 1.0))

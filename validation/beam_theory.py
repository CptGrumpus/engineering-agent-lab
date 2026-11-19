"""Closed-form cantilever references (rectangular section, tip load F).

Units: mm, N, MPa. Independent of the FreeCAD/CalculiX model.

    I = b h^3 / 12,  A = b h,  G = E / (2 (1 + nu))
    Euler-Bernoulli tip deflection   d_EB = F L^3 / (3 E I)
    Timoshenko shear contribution    d_s  = F L / (kappa G A)
    Cowper (1966) shear coefficient  kappa = 10 (1 + nu) / (12 + 11 nu)
    Bending stress at the outer fibre, distance x from the root:
                                     sigma(x) = 6 F (L - x) / (b h^2)

Reference: Timoshenko & Gere, "Mechanics of Materials"; Cowper, J. Appl. Mech.
33 (1966) 335-340.
"""

from __future__ import annotations


def second_moment(b: float, h: float) -> float:
    return b * h**3 / 12.0


def euler_bernoulli_tip(F, L, E, b, h) -> float:
    return F * L**3 / (3.0 * E * second_moment(b, h))


def cowper_kappa(nu: float) -> float:
    return 10.0 * (1.0 + nu) / (12.0 + 11.0 * nu)


def timoshenko_tip(F, L, E, nu, b, h) -> float:
    G = E / (2.0 * (1.0 + nu))
    return euler_bernoulli_tip(F, L, E, b, h) + F * L / (cowper_kappa(nu) * G * b * h)


def timoshenko_deflection(x, F, L, E, nu, b, h):
    """Deflection along the beam (x from the root): bending + shear parts."""
    G = E / (2.0 * (1.0 + nu))
    I = second_moment(b, h)
    return F * x**2 * (3 * L - x) / (6 * E * I) + F * x / (cowper_kappa(nu) * G * b * h)


def bending_stress(F, L, b, h, x: float = 0.0) -> float:
    return 6.0 * F * (L - x) / (b * h**2)

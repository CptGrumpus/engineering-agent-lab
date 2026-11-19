"""Single-degree-of-freedom mass-spring-damper, solved numerically.

Equation of motion (SI units):

    m * x'' + c * x' + k * x = F(t),   F(t) = F for t >= 0 (ideal step)
    x(0) = 0,  x'(0) = 0

This module is the *model under test*. It must not import anything from
``validation/`` so that the reference solution stays independent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp


@dataclass(frozen=True)
class MSDParameters:
    mass_kg: float
    stiffness_N_per_m: float
    damping_ratio: float
    step_force_N: float

    @classmethod
    def from_dict(cls, d: dict) -> "MSDParameters":
        p = cls(
            mass_kg=float(d["mass_kg"]),
            stiffness_N_per_m=float(d["stiffness_N_per_m"]),
            damping_ratio=float(d["damping_ratio"]),
            step_force_N=float(d["step_force_N"]),
        )
        if p.mass_kg <= 0 or p.stiffness_N_per_m <= 0:
            raise ValueError("mass_kg and stiffness_N_per_m must be positive")
        if p.damping_ratio < 0:
            raise ValueError("damping_ratio must be non-negative")
        if p.step_force_N == 0:
            raise ValueError("step_force_N must be non-zero")
        return p

    @property
    def damping_N_s_per_m(self) -> float:
        return 2.0 * self.damping_ratio * math.sqrt(self.stiffness_N_per_m * self.mass_kg)

    @property
    def natural_frequency_rad_per_s(self) -> float:
        return math.sqrt(self.stiffness_N_per_m / self.mass_kg)

    def derived(self) -> dict:
        return {
            "damping_N_s_per_m": self.damping_N_s_per_m,
            "natural_frequency_rad_per_s": self.natural_frequency_rad_per_s,
            "natural_frequency_Hz": self.natural_frequency_rad_per_s / (2 * math.pi),
        }


def simulate(
    p: MSDParameters,
    *,
    t_end_s: float,
    n_points: int,
    method: str,
    rtol: float,
    atol: float,
) -> dict:
    """Integrate the step response. Returns arrays plus solver diagnostics."""
    m, c, k, f = p.mass_kg, p.damping_N_s_per_m, p.stiffness_N_per_m, p.step_force_N

    def rhs(_t, y):
        x, v = y
        return (v, (f - c * v - k * x) / m)

    t_eval = np.linspace(0.0, t_end_s, n_points)
    sol = solve_ivp(
        rhs, (0.0, t_end_s), (0.0, 0.0),
        method=method, t_eval=t_eval, rtol=rtol, atol=atol,
    )
    return {
        "t": sol.t,
        "x": sol.y[0] if sol.success else None,
        "v": sol.y[1] if sol.success else None,
        "success": bool(sol.success),
        "message": str(sol.message),
        "nfev": int(sol.nfev),
    }

"""Stress concentration at a central circular hole in a finite-width plate in tension.

Peterson's Stress Concentration Factors (Pilkey and Pilkey, 3rd ed., chart 4.1,
fitted to Howland's 1930 solution), net-section basis, 0 <= d/W <= 1:

    Kt_net = 3.00 - 3.13 (d/W) + 3.66 (d/W)^2 - 1.53 (d/W)^3
    sigma_net   = F / ((W - d) t)
    sigma_peak  = Kt_net * sigma_net

Limits: d/W -> 0 gives Kt_net = 3 (Kirsch, infinite plate); d/W -> 1 gives
Kt_net -> 2.0.
The fit is a model-form reference (within about 1-2 % of the classical
solution), not an exact one.
"""

from __future__ import annotations


def kt_net(d: float, W: float) -> float:
    b = d / W
    if not 0 <= b < 1:
        raise ValueError("need 0 <= d/W < 1")
    return 3.00 - 3.13 * b + 3.66 * b**2 - 1.53 * b**3


def gross_stress(F: float, W: float, t: float) -> float:
    return F / (W * t)


def net_stress(F: float, W: float, d: float, t: float) -> float:
    return F / ((W - d) * t)


def peak_stress(F: float, W: float, d: float, t: float) -> float:
    return kt_net(d, W) * net_stress(F, W, d, t)


def kirsch_sigma_xx_on_ligament(y, r: float, sigma_far: float):
    """Infinite-plate (Kirsch) sigma_xx along the ligament x = 0, y >= r.

    sigma_xx = sigma (1 + r^2/(2 y^2) + 3 r^4/(2 y^4)); 3 sigma at the hole edge.
    Used only for the shape of the stress decay in figures; the finite-width
    plate differs from it, which is why Peterson is the check.
    """
    return sigma_far * (1 + r**2 / (2 * y**2) + 3 * r**4 / (2 * y**4))

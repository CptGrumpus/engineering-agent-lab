"""Grid Convergence Index (GCI) for mesh-refinement studies.

Procedure from Celik et al., "Procedure for Estimation and Reporting of
Uncertainty Due to Discretization in CFD Applications", J. Fluids Eng. 130
(2008) 078001, which follows Roache (1998) and is the method adopted by
ASME V&V 20.

Inputs are three solutions on successively refined meshes with representative
sizes h1 < h2 < h3 (1 = finest).

Convergence regime from R = e21 / e32 (e21 = f2 - f1, e32 = f3 - f2):
    0 < R < 1   monotone      -> GCI (Richardson extrapolation applies)
    R < 0       oscillatory   -> uncertainty = Fs * half the range of the three
                                 solutions / |f1| (Stern et al., J. Fluids Eng.
                                 123 (2001) 793; Celik et al. 2008 note that GCI
                                 is not valid for oscillatory convergence)
    R >= 1      divergent     -> no estimate (infinite uncertainty)
"""

from __future__ import annotations

import math


def gci(h: tuple[float, float, float], f: tuple[float, float, float], safety: float = 1.25,
        max_iter: int = 100) -> dict:
    h1, h2, h3 = h
    f1, f2, f3 = f
    if not h1 < h2 < h3:
        raise ValueError("mesh sizes must satisfy h1 < h2 < h3 (1 = finest)")
    r21, r32 = h2 / h1, h3 / h2
    e21, e32 = f2 - f1, f3 - f2
    if e21 == 0 or e32 == 0:
        return {"converged_exactly": True, "order": float("nan"), "gci_fine": 0.0,
                "extrapolated": f1, "convergence_ratio": 0.0, "r21": r21, "r32": r32}
    ratio = e21 / e32  # in (0, 1) for monotone convergence
    s = math.copysign(1.0, e32 / e21)
    p = abs(math.log(abs(e32 / e21))) / math.log(r21)
    for _ in range(max_iter):  # fixed-point iteration for non-constant refinement ratio
        q = math.log((r21**p - s) / (r32**p - s))
        p_new = abs(math.log(abs(e32 / e21)) + q) / math.log(r21)
        if abs(p_new - p) < 1e-12:
            p = p_new
            break
        p = p_new
    f_ext = (r21**p * f1 - f2) / (r21**p - 1)
    rel21 = abs((f1 - f2) / f1)
    return {
        "converged_exactly": False,
        "order": p,
        "extrapolated": f_ext,
        "rel_error_fine": rel21,
        "rel_error_extrapolated": abs((f_ext - f1) / f_ext),
        "gci_fine": safety * rel21 / (r21**p - 1),
        "convergence_ratio": ratio,
        "r21": r21,
        "r32": r32,
    }


def discretization_uncertainty(h, f, safety: float = 1.25) -> dict:
    """Relative discretization uncertainty of the finest solution, by regime."""
    f1, f2, f3 = f
    e21, e32 = f2 - f1, f3 - f2
    if e21 == 0 and e32 == 0:
        return {"regime": "converged", "uncertainty": 0.0}
    if e32 == 0 or e21 / e32 >= 1:
        return {"regime": "divergent", "uncertainty": float("inf"),
                "convergence_ratio": float("inf") if e32 == 0 else e21 / e32}
    ratio = e21 / e32
    if ratio < 0:
        return {"regime": "oscillatory", "convergence_ratio": ratio,
                "uncertainty": safety * 0.5 * (max(f) - min(f)) / abs(f1)}
    g = gci(h, f, safety)
    return {"regime": "monotone", "uncertainty": g["gci_fine"], **g}

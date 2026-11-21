"""Local linear response surface: choosing a design when the constraint is noisy.

An optimiser driven by a noisy constraint (a peak stress that scatters from mesh to mesh) stops
among points that sit on both sides of the limit, and the best evaluated point that meets it can be
far from the converged region (clevis_opt_r2 reported its starting design). Fitting the constraint
linearly over the converged candidates averages the noise; the design is then placed where the fit
sits a chosen number of residual standard deviations inside the limit, without leaving the region
the candidates sampled. The design still needs its own verified evaluation and mesh study: the fit
only chooses it.
"""

from __future__ import annotations

import numpy as np


def fit_linear(X, y) -> dict:
    """Least squares y = c0 + c . x; residual standard deviation and the covariance factor."""
    X, y = np.asarray(X, dtype=float), np.asarray(y, dtype=float)
    A = np.c_[np.ones(len(X)), X]
    if len(y) <= A.shape[1]:
        raise ValueError(f"need more than {A.shape[1]} points for a linear fit in {X.shape[1]} variables")
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ coef
    sd = float(np.sqrt(resid @ resid / (len(y) - A.shape[1])))
    return {"coef": coef, "residual_sd": sd, "cov_factor": np.linalg.inv(A.T @ A)}


def predict(fit: dict, x) -> tuple[float, float]:
    """Fitted value and its standard error at x."""
    a = np.r_[1.0, np.asarray(x, dtype=float)]
    return float(a @ fit["coef"]), float(fit["residual_sd"] * np.sqrt(a @ fit["cov_factor"] @ a))


def design_inside_limit(X, constraint, limit: float, n_sd: float, order) -> dict:
    """Start at the centroid of the sampled points and move one variable at a time, in the given order
    (most mass-efficient first), until the fitted constraint equals limit - n_sd x residual sd. Each
    variable stops at the edge of the sampled range, so the design never extrapolates.

    constraint must decrease as the variables in `order` increase (a stress against thicknesses)."""
    X = np.asarray(X, dtype=float)
    fit = fit_linear(X, constraint)
    target = limit - n_sd * fit["residual_sd"]
    lo, hi = X.min(axis=0), X.max(axis=0)
    x = X.mean(axis=0)
    for i in order:
        value, _ = predict(fit, x)
        if value <= target:
            break
        slope = fit["coef"][1 + i]
        if slope >= 0:
            raise ValueError(f"the fitted constraint does not fall as variable {i} grows")
        x[i] = min(hi[i], x[i] + (target - value) / slope)
    value, se = predict(fit, x)
    return {"x": x, "fitted": value, "se": se, "target": target, "fit": fit,
            "reached": bool(value <= target + 1e-9 * abs(target))}

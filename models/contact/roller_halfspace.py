"""Study 10 part 2: the roller's contact along its length, ends and crown included, by the influence-coefficient
method on two elastic half-spaces (Boussinesq; Love's rectangle; Johnson, Contact Mechanics, sections 3.2 and 3.4).

The contact plane is gridded in rectangles (x across the contact, y along the roller), quarter symmetric (x >= 0,
y >= 0: the roller's mid-length at y = 0). A uniform pressure on a rectangle displaces the surface of a half-space by
Love's closed form; the two bodies' displacements add with 1/E* = (1 - nu1^2)/E1 + (1 - nu2^2)/E2. The gap is
  h(x, y) = x^2 / (2 R) + d(y) + u(x, y) - delta >= 0,  p >= 0,  p h = 0,
with d(y) the roller's profile drop (models/fea/roller_3d.drop_um, the same profiles as the FE model) and delta the
approach, adjusted until the total load is the target. Each delta is a non-negative least-squares problem (the
influence matrix is symmetric positive definite: min 1/2 p'Kp - b'p, p >= 0, solved as NNLS on its Cholesky factor).

Limits of the method: both bodies are half-spaces. The roller's end face is not modelled (the half-space continues
past it): near a sharp end the method overstates the pressure peak a little, and the plate is taken as much wider
and deeper than the contact (true here). The subsurface shear is not computed; the pressure is the requirement.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.linalg import cho_factor, solve_triangular
from scipy.optimize import nnls


def _love(a, b):
    """The kernel of Love's rectangle: a ln(b + r) + b ln(a + r), r = sqrt(a^2 + b^2) (0 at the origin)."""
    r = np.sqrt(a * a + b * b)
    with np.errstate(divide="ignore", invalid="ignore"):
        t1 = np.where(np.abs(a) > 0, a * np.log(np.where(b + r > 0, b + r, 1.0)), 0.0)
        t2 = np.where(np.abs(b) > 0, b * np.log(np.where(a + r > 0, a + r, 1.0)), 0.0)
    return t1 + t2


def rect_influence(x, y, x1, x2, y1, y2):
    """Surface displacement x pi E* at (x, y) from a unit pressure on [x1, x2] x [y1, y2] (the integral of 1 / rho)."""
    return (_love(x - x1, y - y1) - _love(x - x2, y - y1) - _love(x - x1, y - y2) + _love(x - x2, y - y2))


def influence_matrix(xf, yf, E_star):
    """K[i, j]: displacement at the centre of cell i from a unit pressure on cell j and its three mirror images
    (quarter symmetry about x = 0 and y = 0)."""
    xc, yc = 0.5 * (xf[1:] + xf[:-1]), 0.5 * (yf[1:] + yf[:-1])
    X, Y = np.meshgrid(xc, yc, indexing="ij")
    px, py = X.ravel(), Y.ravel()
    x1 = np.repeat(xf[:-1], len(yc)); x2 = np.repeat(xf[1:], len(yc))
    y1 = np.tile(yf[:-1], len(xc)); y2 = np.tile(yf[1:], len(xc))
    K = np.zeros((len(px), len(px)))
    for sx in (1, -1):
        for sy in (1, -1):
            a1, a2 = (x1, x2) if sx == 1 else (-x2, -x1)
            b1, b2 = (y1, y2) if sy == 1 else (-y2, -y1)
            K += rect_influence(px[:, None], py[:, None], a1[None, :], a2[None, :], b1[None, :], b2[None, :])
    return K / (math.pi * E_star), px, py


def contact_lcp(K: np.ndarray, b: np.ndarray, tol: float = 1e-12, max_iter: int = 500) -> np.ndarray:
    """p >= 0, h = K p - b >= 0, p h = 0, by an active set: solve on the cells in contact, drop those with tension,
    add those that overlap, until neither happens. (The collocated influence matrix is not symmetric on a graded grid,
    so no Cholesky; it is positive enough for the set to settle in a few passes.)"""
    n = len(b)
    act = b > 0
    p = np.zeros(n)
    scale = max(float(np.abs(b).max()), 1e-30)
    for _ in range(max_iter):
        p[:] = 0.0
        idx = np.flatnonzero(act)
        if len(idx):
            p[idx] = np.linalg.solve(K[np.ix_(idx, idx)], b[idx])
        neg = idx[p[idx] < 0]
        if len(neg):
            act[neg] = False
            continue
        h = K @ p - b
        over = np.flatnonzero((~act) & (h < -tol * scale))
        if len(over) == 0:
            return p
        act[over] = True
    raise RuntimeError("contact active set did not settle")


def solve(p: dict, *, nx: int = 24, x_max: float | None = None, y_fine: float = 0.1, y_growth: float = 1.15,
          y_max_cell: float = 1.0, load_tol: float = 1e-6, drop_um=None) -> dict:
    """Contact pressure on the quarter grid at the target load (line load x roller length). Returns the pressure field
    (MPa), the peak and where it sits, the mid-length peak, the approach and the solver's load error."""
    R, L2 = float(p["roller_radius_mm"]), float(p["roller_length_mm"]) / 2
    E, nu = float(p["youngs_modulus_MPa"]), float(p["poisson_ratio"])
    E_star = 1.0 / (2 * (1 - nu * nu) / E)
    W4 = float(p["line_load_N_per_mm"]) * 2 * L2 / 4            # the quarter's load
    a0 = math.sqrt(4 * float(p["line_load_N_per_mm"]) * R / (math.pi * E_star))   # Hertz half-width, uniform line load
    xm = float(x_max) if x_max else 2.2 * a0
    xf = np.linspace(0.0, xm, nx + 1)
    # y: fine at the roller's end (and at z_fine, where an edge radius starts), growing towards mid-length
    zf = float(p.get("z_fine_mm", 0) or 0) or L2
    def faces(length, fine_end):
        hs, tot, h = [], 0.0, y_fine
        while tot + h < length:
            hs.append(h); tot += h; h = min(h * y_growth, y_max_cell)
        hs.append(length - tot)
        if len(hs) > 1 and hs[-1] < 0.5 * hs[-2]:
            hs[-2] += hs.pop()
        hs = np.asarray(hs) * length / sum(hs)
        return hs[::-1] if fine_end else hs
    hs = list(faces(zf, True)) + (list(faces(L2 - zf, False)) if zf < L2 - 1e-9 else [])
    yf = np.concatenate([[0.0], np.cumsum(hs)])
    K, px, py = influence_matrix(xf, yf, E_star)
    area = np.outer(np.diff(xf), np.diff(yf)).ravel()
    if drop_um is None:
        from models.fea.roller_3d import drop_um as _drop
        drop_um = _drop
    h0 = px ** 2 / (2 * R) + 1e-3 * drop_um(p, py)

    def at(delta):
        q = contact_lcp(K, delta - h0)
        return q, float(q @ area)

    d1, d2 = 0.5 * a0 * a0 / R, 1.5 * a0 * a0 / R                 # bracket the approach, then secant on the load
    (q1, F1), (q2, F2) = at(d1), at(d2)
    for _ in range(60):
        d = d2 + (W4 - F2) * (d2 - d1) / (F2 - F1) if F2 != F1 else 1.1 * d2
        d1, q1, F1 = d2, q2, F2
        d2 = max(d, 1e-9)
        q2, F2 = at(d2)
        if abs(F2 / W4 - 1) < load_tol:
            break
    P = q2.reshape(len(xf) - 1, len(yf) - 1)
    k = int(np.argmax(q2))
    q_mid = 2 * float(P[:, 0] @ np.diff(xf))                    # the line load the mid-length section carries
    return {"pressure_MPa": P, "xf": xf, "yf": yf, "peak_MPa": float(q2[k]), "peak_y_mm": float(py[k]),
            "peak_x_mm": float(px[k]), "mid_peak_MPa": float(P[:, 0].max()), "mid_line_load_N_per_mm": q_mid,
            "approach_mm": d2,
            "load_error": abs(F2 / W4 - 1), "cells": int(len(q2)), "E_star": E_star, "a0_mm": a0,
            "contact_x_max_mm": float(px[q2 > 0].max()) if np.any(q2 > 0) else 0.0}


def hertz_elliptic(W: float, Rx: float, Ry: float, E_star: float) -> dict:
    """Hertz's elliptical contact of a body with principal radii Rx (across) and Ry (along) on a flat, total load W:
    semi-axes a (x) and b (y), peak pressure p0 = 3 W / (2 pi a b) (Johnson, section 4.2: the eccentricity from the
    ratio of the curvatures through the complete elliptic integrals)."""
    from scipy.optimize import brentq
    from scipy.special import ellipe, ellipk

    A, B = 1 / (2 * Rx), 1 / (2 * Ry)                         # gap h = A x^2 + B y^2
    if A < B:
        raise ValueError("expects Rx <= Ry (the ellipse long along y)")
    # with e^2 = 1 - (a/b)^2 for b > a: B / A = [(1/k^2) E(e) - K(e)] ... solved numerically below
    def ratio(e2):
        Ke, Ee = ellipk(e2), ellipe(e2)
        return ((Ke - Ee) / e2) / ((Ee / (1 - e2) - Ke) / e2) - B / A   # B/A = (K - E) / (E/(1-e2) - K)
    e2 = brentq(ratio, 1e-12, 1 - 1e-15)
    Ke, Ee = ellipk(e2), ellipe(e2)
    # along the major axis the gap coefficient is B = p0 a (K - E) / (E* e^2 b^2) (Johnson, a the minor and b the
    # major semi-axis; the circular limit gives pi p0 / (4 a)), and W = (2/3) pi a b p0, so
    # b^3 = 3 W (K - E) / (2 pi E* e^2 B). Check: for a long ellipse the minor axis tends to 2 p0 R / E*, Hertz's line
    # contact for the central line load.
    b = (3 * W * (Ke - Ee) / (2 * math.pi * e2 * E_star * B)) ** (1 / 3)
    a = b * math.sqrt(1 - e2)
    return {"a_mm": a, "b_mm": b, "p0_MPa": 3 * W / (2 * math.pi * a * b), "e2": e2}

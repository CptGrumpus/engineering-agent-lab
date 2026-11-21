"""Steady 2D conduction in a flat plate: exact Fourier series solution.

Independent reference for the solid stage of the cold-plate chain (models/thermal/
cold_plate_ccx.py). It shares no code with the finite element path.

Plate 0 <= x <= L (along the flow), 0 <= y <= t (y = 0 wetted face, y = t outer face),
conductivity k, Laplace's equation inside, and

    y = t   heat flux into the plate        k dT/dy = Q(x)
    y = 0   film to the coolant (Robin)     k dT/dy = h (T - R(x))
    x = 0, L   adiabatic

with h constant and Q, R piecewise constant on given segments (as the finite element deck
applies them, one value per element face). Adiabatic ends make cos(n pi x / L) the
eigenfunctions; each mode is solved exactly in y on the decaying exponential basis
exp(-lambda y), exp(-lambda (t - y)), which stays finite for any number of terms.

Exact checks on the reference itself (tests/test_cold_plate.py): uniform Q and R give the
1D slab solution T = R + Q/h + Q y / k; the heat leaving through the film equals the heat
put in; the series converges as the number of terms grows.
"""

from __future__ import annotations

import numpy as np


def cosine_coefficients(edges, values, L, n_terms):
    """Cosine series coefficients c_0..c_N of a piecewise-constant function on [0, L].

    f(x) = c_0 + sum_n c_n cos(n pi x / L); exact for the piecewise-constant data."""
    a, b = np.asarray(edges[:-1], float), np.asarray(edges[1:], float)
    v = np.asarray(values, float)
    n = np.arange(1, n_terms + 1)
    lam = n * np.pi / L
    c = np.empty(n_terms + 1)
    c[0] = float(np.sum(v * (b - a))) / L
    # (2/L) sum_j v_j (sin(lam b_j) - sin(lam a_j)) / lam, accumulated segment by segment
    acc = np.zeros(n_terms)
    for aj, bj, vj in zip(a, b, v):
        if vj != 0.0:
            acc += vj * (np.sin(lam * bj) - np.sin(lam * aj))
    c[1:] = 2.0 / L * acc / lam
    return c


def mode_amplitudes(Qn, Rn, L, t, k, h):
    """Per-mode (C_n, D_n) of T_n(y) = C exp(-lam y) + D exp(-lam (t - y)), n >= 1,
    and (a, b) of the mean mode T_0(y) = a + b y."""
    n = np.arange(1, len(Qn))
    lam = n * np.pi / L
    E = np.exp(-lam * t)
    kl = k * lam
    Q, R = Qn[1:], Rn[1:]
    # y = 0:  (-kl - h) C + (kl - h) E D = -h R
    # y = t:  (-kl E) C + kl D = Q
    det = -kl * (kl + h) + kl * (kl - h) * E**2
    C = (-h * R * kl - (kl - h) * E * Q) / det
    D = (-(kl + h) * Q - kl * E * h * R) / det
    b0 = Qn[0] / k
    a0 = Rn[0] + Qn[0] / h
    return lam, C, D, a0, b0


def temperature(x, y, *, L, t, k, h, q_edges, q_values, r_edges, r_values, n_terms=20000):
    """T at points (x, y) (arrays of equal shape), units consistent (e.g. mm, W, K)."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    Qn = cosine_coefficients(q_edges, q_values, L, n_terms)
    Rn = cosine_coefficients(r_edges, r_values, L, n_terms)
    lam, C, D, a0, b0 = mode_amplitudes(Qn, Rn, L, t, k, h)
    out = np.full(x.shape, a0) + b0 * y
    flat_x, flat_y = x.ravel(), y.ravel()
    res = out.ravel()
    chunk = max(1, 4_000_000 // max(1, len(lam)))
    for s in range(0, len(flat_x), chunk):
        xx, yy = flat_x[s:s + chunk, None], flat_y[s:s + chunk, None]
        modes = C * np.exp(-lam * yy) + D * np.exp(-lam * (t - yy))
        res[s:s + chunk] += np.sum(np.cos(lam * xx) * modes, axis=1)
    return res.reshape(x.shape)

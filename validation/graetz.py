"""Thermal entry (Graetz) problem: laminar flow between parallel plates, hydrodynamically
fully developed, both walls heated at a uniform flux q from x = 0.

Independent reference for the heated coolant channel (models/cfd/heated_channel_openfoam.py).
It shares no code with the CFD path.

Method: the energy equation without axial conduction (valid for Peclet >> 1),

    rho cp u(y) dT/dx = k d2T/dy2,   u(y) = 6 U (y/H)(1 - y/H),   -k dT/dn = q at both walls,

is discretised across the gap only (N finite-volume cells) and solved exactly along
x with the matrix exponential, so the only discretisation is in y.

Exact checks on the reference itself:
    bulk temperature   T_b(x) = T_in + 2 q x / (rho cp U H)          (energy balance)
    fully developed    Nu = h Dh / k = 140/17 = 8.2353,  Dh = 2 H    (Shah and London 1978)
"""

from __future__ import annotations

import numpy as np
from scipy.linalg import expm

NU_FULLY_DEVELOPED = 140.0 / 17.0


def wall_minus_bulk_developed(q, H, k):
    """Fully developed T_wall - T_bulk = q Dh / (k Nu), Dh = 2H."""
    return q * 2 * H / (k * NU_FULLY_DEVELOPED)


def bulk_temperature(x, T_in, q, H, U, rho, cp):
    return T_in + 2 * q * np.asarray(x, float) / (rho * cp * U * H)


def thermal_entry(x, *, H, U, rho, cp, k, q, T_in, n_cells=400):
    """Wall and bulk temperature at stations x (m) after the start of heating.

    H gap (m), U mean velocity (m/s), q wall heat flux (W/m2, into the fluid at both walls).
    Returns {"x", "T_wall", "T_bulk", "Nu"} with Nu = q Dh / (k (T_wall - T_bulk))."""
    x = np.atleast_1d(np.asarray(x, float))
    n = int(n_cells)
    dy = H / n
    yc = (np.arange(n) + 0.5) * dy
    # cell-averaged velocity: integral of the parabola over each cell (exact), so the flow rate is exact
    yf = np.arange(n + 1) * dy
    prim = 6 * U * (yf**2 / (2 * H) - yf**3 / (3 * H**2))
    u = np.diff(prim) / dy
    cap = rho * cp * u * dy                         # J/(m^2 K) per unit x, per unit depth
    # d(theta)/dx = A theta + b  (theta = T - T_in), conduction between neighbours, flux in at walls
    A = np.zeros((n + 1, n + 1))                    # last row/col: constant forcing
    g = k / dy
    for i in range(n):
        if i > 0:
            A[i, i - 1] += g; A[i, i] -= g
        if i < n - 1:
            A[i, i + 1] += g; A[i, i] -= g
        A[i, :] /= cap[i]
    A[0, n] = q / cap[0]
    A[n - 1, n] = q / cap[n - 1]
    y0 = np.zeros(n + 1)
    y0[n] = 1.0
    T_wall, T_bulk = [], []
    order = np.argsort(x)
    xs = x[order]
    state, x_prev = y0, 0.0
    out_w, out_b = np.empty(len(x)), np.empty(len(x))
    for j, xi in zip(order, xs):
        state = expm(A * (xi - x_prev)) @ state
        x_prev = xi
        th = state[:n]
        # wall temperature: the wall flux q crosses half a cell of conduction from the cell centre
        tw = 0.5 * (th[0] + th[-1]) + q * (dy / 2) / k
        tb = float(np.sum(u * th) / np.sum(u))
        out_w[j], out_b[j] = T_in + tw, T_in + tb
    nu = q * 2 * H / (k * (out_w - out_b))
    return {"x": x, "T_wall": out_w, "T_bulk": out_b, "Nu": nu, "y": yc}

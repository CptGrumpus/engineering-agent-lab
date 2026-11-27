"""Study 11 part 2: the cold-plate passage's cross-section with its side walls, fully developed flow and heat
transfer, by finite volumes (Python, SciPy sparse).

Study 11 modelled the passage (1 mm deep, much wider) as parallel plates: no side walls. In the real 1 x W mm passage
the flow slows near the side walls, and the broad walls, heated, run hotter there. How much hotter depends on how far
the plate spreads heat across the width, so two bounds:
  "H2": uniform heat flux on the broad walls, the side walls adiabatic (a thin wall that spreads nothing: the upper
        bound on the hot spot);
  "H1": the broad wall at one temperature across the width at each section, the side walls adiabatic (a plate that
        conducts perfectly across the width: the lower bound).
And, for checking: "H1_4": all four walls at one temperature with the flux shared over the whole perimeter (the
classic rectangular-duct case, tabulated); and side = "symmetry" replaces the side wall by a symmetry plane (the
parallel-plate limit, exact).

The quarter section: y across the gap (0 at mid-gap, H/2 at the broad wall), z across the width (0 at mid-width,
W/2 at the side wall), cell-centred finite volumes, uniform in y, graded in z towards the side wall (geometric, the
cell at the wall dz_min = dy, growing by `growth` up to dz_max).

Fully developed, constant axial gradient: mu lap(u) = dp/dx; k lap(T) = rho cp u dTb/dx, so with
theta = T - T_ref, lap(theta) = (u / u_mean) q P_h / (k A) (P_h the heated perimeter and A the area of the section,
both of the quarter), with the wall flux (H2) or the wall temperature (H1) as boundary condition.
"""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def z_faces(W2: float, dz_min: float, growth: float, dz_max: float) -> np.ndarray:
    """Cell faces from z = 0 to W/2, the finest cell (dz_min) at the side wall, growing inward."""
    hs, tot, h = [], 0.0, dz_min
    while tot + h < W2:
        hs.append(h)
        tot += h
        h = min(h * growth, dz_max)
    hs.append(W2 - tot)
    if hs[-1] < 0.5 * hs[-2]:
        hs[-2] += hs.pop()
    hs = np.asarray(hs) * W2 / sum(hs)
    return np.concatenate([[0.0], np.cumsum(hs[::-1])])          # fine at z = W/2


def _laplacian(yf, zf, dirichlet: dict):
    """Finite-volume Laplacian on the cell grid (ny, nz), flattened y-fastest... returns (A, b_coeff) where
    dirichlet maps 'top' (y = H/2) / 'side' (z = W/2) to True if that wall is held at theta = 0 (else adiabatic or
    symmetric: zero normal gradient, or a flux added by the caller). Mid-planes y = 0, z = 0 are symmetry."""
    ny, nz = len(yf) - 1, len(zf) - 1
    yc, zc = 0.5 * (yf[1:] + yf[:-1]), 0.5 * (zf[1:] + zf[:-1])
    dy, dz = np.diff(yf), np.diff(zf)
    idx = lambda i, j: i * nz + j  # noqa: E731 - i along y, j along z
    rows, cols, vals = [], [], []
    for i in range(ny):
        for j in range(nz):
            k = idx(i, j)
            diag = 0.0
            # y neighbours (area dz[j] per unit length, divided by the cell volume dy dz: 1 / dy / distance)
            for di in (-1, 1):
                ii = i + di
                if 0 <= ii < ny:
                    c = 1.0 / (dy[i] * abs(yc[ii] - yc[i]))
                    rows.append(k); cols.append(idx(ii, j)); vals.append(c)
                    diag -= c
                elif di == 1 and dirichlet.get("top"):
                    diag -= 1.0 / (dy[i] * (yf[-1] - yc[i]))       # theta = 0 at the wall face
            for dj in (-1, 1):
                jj = j + dj
                if 0 <= jj < nz:
                    c = 1.0 / (dz[j] * abs(zc[jj] - zc[j]))
                    rows.append(k); cols.append(idx(i, jj)); vals.append(c)
                    diag -= c
                elif dj == 1 and dirichlet.get("side"):
                    diag -= 1.0 / (dz[j] * (zf[-1] - zc[j]))
            rows.append(k); cols.append(k); vals.append(diag)
    A = sp.csr_matrix((vals, (rows, cols)), shape=(ny * nz, ny * nz))
    return A, yc, zc, dy, dz


def solve(H: float, W: float, *, bc: str = "H2", side: str = "wall", ny: int = 40, growth: float = 1.08,
          dz_max_over_dy: float = 8.0, q: float = 1.0, k: float = 1.0, plate_conductance_rel: float = 0.0) -> dict:
    """Fully developed section. Lengths in any consistent unit; q (W/m2) and k (W/m K) set the temperature scale.
    Returns the velocity field (normalised to a unit mean), the temperature excess fields and the quantities the
    study uses: fRe, the broad wall's peak and mean excess over the bulk, and the Nusselt number on the hydraulic
    diameter (with the mean wall temperature of the heated walls)."""
    H2, W2 = H / 2, W / 2
    yf = np.linspace(0.0, H2, ny + 1)
    dy0 = H2 / ny
    zf = z_faces(W2, dy0, growth, dz_max_over_dy * dy0)
    wall_side = side == "wall"
    # flow: lap(phi) = -1, phi = 0 on the walls (top, and the side if it is a wall)
    A, yc, zc, dy, dz = _laplacian(yf, zf, {"top": True, "side": wall_side})
    vol = np.outer(dy, dz).ravel()
    phi = spla.spsolve(A.tocsc(), -np.ones(A.shape[0]))
    umean = float(np.sum(phi * vol) / np.sum(vol))
    u = phi / umean                                          # unit mean velocity
    # Fanning f Re on the hydraulic diameter: with mu lap(u) = -G, u = (G / mu) phi; tau_w P = G A, so
    # f Re = (G Dh / 4) / (rho um^2 / 2) x rho um Dh / mu = Dh^2 / (2 mean(phi))  (24 for parallel plates)
    Dh = 4 * (H * W) / (2 * (H + W)) if wall_side else 2 * H
    fRe = Dh ** 2 / (2 * umean)
    # heat: the heated perimeter of the quarter and its area
    if bc == "H1_4":
        Ph = W2 + (H2 if wall_side else 0.0)
    else:
        Ph = W2
    Aq = H2 * W2
    S = u * q * Ph / (k * Aq)                                # lap(theta) = S
    if bc == "H2":
        L, *_ = _laplacian(yf, zf, {"top": False, "side": False})
        b = S * 1.0
        top = (np.arange(len(yc) * len(zc)) // len(zc)) == len(yc) - 1
        b[top] -= q / k / dy[-1]                             # the wall flux into the top cells (lap = div grad)
        # pure Neumann: pin the gauge with one extra equation (mean theta = 0)
        n = L.shape[0]
        M = sp.bmat([[L, sp.csr_matrix(vol[:, None])], [sp.csr_matrix(vol[None, :]), None]]).tocsc()
        sol = spla.spsolve(M, np.concatenate([b, [0.0]]))
        theta = sol[:n]
    elif bc == "plate":
        # the broad wall as a conducting sheet (conductance G = k_s t_p per unit length, here relative: G / k, a
        # length): its temperature Tw(z) is solved with the fluid; the heat q enters the sheet, spreads along z by
        # conduction and leaves into the fluid's top cells. G = 0 is H2, G -> infinity is H1. The sheet ends at the
        # side wall with no flux (the side wall adiabatic), and is symmetric at z = 0.
        L, *_ = _laplacian(yf, zf, {"top": False, "side": False})
        n, nz = L.shape[0], len(zc)
        dhalf = yf[-1] - yc[-1]
        top_rows = (len(yc) - 1) * nz + np.arange(nz)
        cw = 1.0 / (dy[-1] * dhalf)
        Grel = float(plate_conductance_rel)
        rows, cols, vals = [], [], []
        for j, r in enumerate(top_rows):          # fluid top cells: + cw (Tw_j - theta)
            rows += [r, r]; cols += [r, n + j]; vals += [-cw, cw]
        for j in range(nz):                       # sheet: G (d2Tw/dz2) / dz + q / k - (Tw - theta_top) / dhalf = 0
            diag = -1.0 / dhalf
            for jj in (j - 1, j + 1):
                if 0 <= jj < nz:
                    c = Grel / (dz[j] * abs(zc[jj] - zc[j]))
                    rows.append(n + j); cols.append(n + jj); vals.append(c)
                    diag -= c
            rows += [n + j, n + j]; cols += [n + j, top_rows[j]]; vals += [diag, 1.0 / dhalf]
        C = sp.csr_matrix((vals, (rows, cols)), shape=(n + nz, n + nz))
        Lx = sp.bmat([[L, None], [None, sp.csr_matrix((nz, nz))]]).tocsr() + C
        b = np.concatenate([S, -q / k * np.ones(nz)])
        wvol = np.concatenate([vol, np.zeros(nz)])
        M = sp.bmat([[Lx, sp.csr_matrix(wvol[:, None])], [sp.csr_matrix(wvol[None, :]), None]]).tocsc()
        sol = spla.spsolve(M, np.concatenate([b, [0.0]]))
        theta, tw_plate = sol[:n], sol[n:n + nz]
    elif bc == "H1":
        L, *_ = _laplacian(yf, zf, {"top": True, "side": False})
        theta = spla.spsolve(L.tocsc(), S)
    elif bc == "H1_4":
        L, *_ = _laplacian(yf, zf, {"top": True, "side": wall_side})
        theta = spla.spsolve(L.tocsc(), S)
    else:
        raise ValueError(bc)
    T = theta.reshape(len(yc), len(zc))
    Uf = u.reshape(len(yc), len(zc))
    tb = float(np.sum(u * theta * vol) / np.sum(u * vol))
    # the broad wall's temperature along z: extrapolated from the top cell with the wall flux (H2) or 0 (H1)
    if bc == "H2":
        tw = T[-1, :] + q / k * (yf[-1] - yc[-1])
    elif bc == "plate":
        tw = tw_plate
    else:
        tw = np.zeros(len(zc))
    wmean = float(np.sum(tw * dz) / np.sum(dz))
    nu = q * Dh / (k * (wmean - tb)) if bc != "H1_4" else q * Dh / (k * (0.0 - tb))
    return {"fRe": fRe, "Dh": Dh, "u": Uf, "theta": T, "yc": yc, "zc": zc, "zf": zf, "tw_z": tw,
            "wall_peak_excess": float(tw.max() - tb), "wall_mean_excess": wmean - tb, "Nu": nu,
            "peak_at_z": float(zc[int(np.argmax(tw))]), "cells": int(len(yc) * len(zc))}

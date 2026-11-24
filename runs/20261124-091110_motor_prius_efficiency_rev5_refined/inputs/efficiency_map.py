"""Efficiency map of a permanent-magnet machine from its dq look-up table (study 7). Pure numpy/scipy.

The table (studies/motor_lut.py) gives, on a regular (id, iq) grid of rms dq currents: the mean torque, the mean dq flux
linkages (rms, Pyleecan's sign: T = 3 p (phi_d iq - phi_q id)) and per core the iron-loss coefficients A, B, C (W) with
P_fe = A f + B f^2 + C f^1.5 at electrical frequency f. A magnetostatic field does not depend on speed, so the table
serves every speed.

At each speed the table is interpolated (cubic) onto a fine current grid. Each fine point has
  copper loss   P_cu = 3 R I^2               (I = |(id, iq)|, the phase rms current; DC resistance at the winding
                                              temperature, no AC copper loss)
  iron loss     P_fe = A f + B f^2 + C f^1.5
  phase voltage V = |(R id - w phi_q, R iq + w phi_d)|  (rms, steady state, w electrical rad/s)
and is feasible if V <= the voltage limit, I <= the current limit and T > 0 (motoring). For each target torque, the
feasible point within a narrow torque band with the least loss is the operating point (maximum efficiency per amp
below base speed, flux weakening above it fall out of the same search). Efficiency = T w_m / (T w_m + P_cu + P_fe):
motor only, no mechanical loss, no inverter (user's framing 2026-11-22).
"""

from __future__ import annotations

import numpy as np
from scipy.interpolate import RegularGridInterpolator

FIELDS = ("torque_mean_Nm", "phi_d_Wb", "phi_q_Wb", "iron_A_W", "iron_B_W", "iron_C_W")


def interpolants(grid: dict, method: str = "cubic") -> dict:
    """grid: {"id": (n_d,), "iq": (n_q,), field: (n_d, n_q)} with id and iq ascending."""
    return {k: RegularGridInterpolator((grid["id"], grid["iq"]), grid[k], method=method) for k in FIELDS}


def fine_grid(grid: dict, step_A: float = 1.0, method: str = "cubic") -> dict:
    f = interpolants(grid, method)
    ids = np.arange(grid["id"][0], grid["id"][-1] + step_A / 2, step_A)
    iqs = np.arange(grid["iq"][0], grid["iq"][-1] + step_A / 2, step_A)
    D, Q = np.meshgrid(ids, iqs, indexing="ij")
    pts = np.column_stack([D.ravel(), Q.ravel()])
    out = {"id": D.ravel(), "iq": Q.ravel()}
    for k in FIELDS:
        out[k] = f[k](pts)
    return out


def resistance(r20_ohm: float, temp_C: float, alpha_per_K: float = 0.00393) -> float:
    return r20_ohm * (1 + alpha_per_K * (temp_C - 20.0))


def operating_points(fine: dict, *, speed_rpm: float, torques_Nm, pole_pairs: int, r_ohm: float, v_max_rms: float,
                     i_max_rms: float, band_rel: float = 0.005, band_abs_Nm: float = 0.5) -> dict:
    """Lowest-loss feasible point for each target torque at one speed; NaN where none is feasible."""
    w_e = 2 * np.pi * speed_rpm / 60 * pole_pairs
    f = w_e / (2 * np.pi)
    w_m = 2 * np.pi * speed_rpm / 60
    i_d, i_q, T = fine["id"], fine["iq"], fine["torque_mean_Nm"]
    I = np.hypot(i_d, i_q)
    p_cu = 3 * r_ohm * I ** 2
    p_fe = fine["iron_A_W"] * f + fine["iron_B_W"] * f ** 2 + fine["iron_C_W"] * f ** 1.5
    v = np.hypot(r_ohm * i_d - w_e * fine["phi_q_Wb"], r_ohm * i_q + w_e * fine["phi_d_Wb"])
    ok = (v <= v_max_rms) & (I <= i_max_rms) & (T > 0)
    loss = p_cu + p_fe
    keys = ("torque_Nm", "id_A", "iq_A", "current_A", "voltage_V", "p_cu_W", "p_fe_W", "efficiency_pct")
    res = {k: np.full(len(torques_Nm), np.nan) for k in keys}
    res["t_max_Nm"] = float(np.max(T[ok])) if ok.any() else 0.0
    for j, Tt in enumerate(torques_Nm):
        cand = ok & (np.abs(T - Tt) <= max(band_rel * Tt, band_abs_Nm))
        if not cand.any():
            continue
        k = np.flatnonzero(cand)[np.argmin(loss[cand])]
        p_out = T[k] * w_m
        res["torque_Nm"][j], res["id_A"][j], res["iq_A"][j] = T[k], i_d[k], i_q[k]
        res["current_A"][j], res["voltage_V"][j] = I[k], v[k]
        res["p_cu_W"][j], res["p_fe_W"][j] = p_cu[k], p_fe[k]
        res["efficiency_pct"][j] = 100 * p_out / (p_out + loss[k])
    return res


def efficiency_map(fine: dict, *, speeds_rpm, torques_Nm, **kw) -> dict:
    rows = {k: [] for k in ("speed_rpm", "target_torque_Nm", "torque_Nm", "id_A", "iq_A", "current_A", "voltage_V",
                            "p_cu_W", "p_fe_W", "efficiency_pct")}
    t_max = []
    for n in speeds_rpm:
        r = operating_points(fine, speed_rpm=n, torques_Nm=torques_Nm, **kw)
        t_max.append(r.pop("t_max_Nm"))
        rows["speed_rpm"] += [float(n)] * len(torques_Nm)
        rows["target_torque_Nm"] += [float(t) for t in torques_Nm]
        for k, v in r.items():
            rows[k] += list(v)
    out = {k: np.asarray(v, float) for k, v in rows.items()}
    out["t_max_by_speed_Nm"] = np.asarray(t_max)
    return out

"""Linear 2-DOF quarter-car model, solved numerically (model under test).

Coordinates are measured from static equilibrium (gravity cancels), positive up.

    ms * zs'' = -ks (zs - zu) - cs (zs' - zu')
    mu * zu'' =  ks (zs - zu) + cs (zs' - zu') - kt (zu - zr(t))

Tire: linear point-contact spring, no tire damping, always in contact.
Must not import from validation/.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.integrate import solve_ivp

from excitation.road import Road

G = 9.80665
PARAMS = ("sprung_mass_kg", "unsprung_mass_kg", "suspension_stiffness_N_per_m",
          "damping_N_s_per_m", "tire_stiffness_N_per_m", "road", "speed_m_per_s")


def unpack(params: dict) -> tuple[float, float, float, float, float]:
    ms = float(params["sprung_mass_kg"])
    mu = float(params["unsprung_mass_kg"])
    ks = float(params["suspension_stiffness_N_per_m"])
    cs = float(params["damping_N_s_per_m"])
    kt = float(params["tire_stiffness_N_per_m"])
    if min(ms, mu, ks, kt) <= 0 or cs < 0:
        raise ValueError("masses and stiffnesses must be positive; damping non-negative")
    return ms, mu, ks, cs, kt


def derived(params: dict) -> dict:
    ms, mu, ks, cs, kt = unpack(params)
    k_ride = ks * kt / (ks + kt)
    return {
        "ride_rate_N_per_m": k_ride,
        "body_frequency_Hz_approx": math.sqrt(k_ride / ms) / (2 * math.pi),
        "wheel_hop_frequency_Hz_approx": math.sqrt((ks + kt) / mu) / (2 * math.pi),
        "body_damping_ratio_approx": cs / (2 * math.sqrt(k_ride * ms)),
        "static_tire_load_N": (ms + mu) * G,
    }


def simulate(params: dict, *, t_end_s: float, n_points: int, method: str, rtol: float,
             atol: float) -> dict:
    ms, mu, ks, cs, kt = unpack(params)
    road = Road(params)

    if road.kind == "bump":
        zr = lambda t: float(road.zr(t))  # noqa: E731
        # integrate in two segments so the solver never steps across the bump end
        breaks = [0.0, min(road.duration, t_end_s), t_end_s]
    else:
        zr = road.zr
        breaks = [0.0, t_end_s]

    def rhs(t, y):
        zs, vs, zu, vu = y
        f_susp = ks * (zs - zu) + cs * (vs - vu)
        return (vs, -f_susp / ms, vu, (f_susp - kt * (zu - zr(t))) / mu)

    t_eval = np.linspace(0.0, t_end_s, n_points)
    y0 = np.zeros(4)
    ys, nfev = [], 0
    for a, b in zip(breaks[:-1], breaks[1:]):
        if b <= a:
            continue
        last = b == breaks[-1]
        mask = (t_eval >= a) & ((t_eval <= b) if last else (t_eval < b))
        sol = solve_ivp(rhs, (a, b), y0, method=method, rtol=rtol, atol=atol,
                        t_eval=t_eval[mask], dense_output=True)
        nfev += sol.nfev
        if not sol.success:
            return {"success": False, "message": str(sol.message), "nfev": nfev, "series": None}
        ys.append(sol.y)
        y0 = sol.sol(b)
    y = np.concatenate(ys, axis=1)
    return {
        "success": True, "message": "ok", "nfev": nfev,
        "series": {"t_s": t_eval, "zs_m": y[0], "vs_m_per_s": y[1], "zu_m": y[2],
                   "vu_m_per_s": y[3], "zr_m": np.asarray(road.zr(t_eval), float)},
    }

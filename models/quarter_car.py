"""2-DOF quarter-car model, solved numerically (model under test).

Coordinates are measured from static equilibrium (gravity cancels), positive up.

    ms * zs'' = -ks (zs - zu) - cs (zs' - zu')
    mu * zu'' =  ks (zs - zu) + cs (zs' - zu') + F_tire

Tire (parameter tire_model):
  "linear"   F_tire = kt (zr - zu): point-contact spring that can pull the wheel
             down, so it is valid only while the tire stays loaded (default).
  "liftoff"  the tire pushes but never pulls: the total tire load W + kt (zr - zu)
             (W = static corner weight) is floored at zero, so F_tire = -W while the
             wheel is in the air. Integration stops exactly at each lift-off and
             touchdown (solve_ivp event location) and restarts in the other phase,
             so the integrator never steps across the kink in the force.
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


MAX_CONTACT_SWITCHES = 200      # more than this means chattering, not bouncing


def simulate(params: dict, *, t_end_s: float, n_points: int, method: str, rtol: float,
             atol: float) -> dict:
    tire = str(params.get("tire_model", "linear"))
    if tire == "liftoff":
        return _simulate_liftoff(params, t_end_s=t_end_s, n_points=n_points, method=method,
                                 rtol=rtol, atol=atol)
    if tire != "linear":
        raise ValueError(f"unknown tire_model {tire!r} (linear | liftoff)")
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


def _simulate_liftoff(params: dict, *, t_end_s, n_points, method, rtol, atol) -> dict:
    ms, mu, ks, cs, kt = unpack(params)
    road = Road(params)
    W = (ms + mu) * G
    zr = (lambda t: float(road.zr(t))) if road.kind == "bump" else road.zr
    breaks = [road.duration] if road.kind == "bump" and road.duration < t_end_s else []

    def compression(t, y):                      # static deflection + dynamic; < 0 means airborne
        return W / kt + zr(t) - y[2]

    def rhs_factory(contact):
        def rhs(t, y):
            zs, vs, zu, vu = y
            f_susp = ks * (zs - zu) + cs * (vs - vu)
            f_tire = kt * (zr(t) - zu) if contact else -W
            return (vs, -f_susp / ms, vu, (f_susp + f_tire) / mu)
        return rhs

    t_eval = np.linspace(0.0, t_end_s, n_points)
    out = np.empty((4, n_points))
    y0, a, contact, nfev, events = np.zeros(4), 0.0, True, 0, []
    filled = 0
    while a < t_end_s:
        b = min([x for x in breaks if x > a + 1e-15] + [t_end_s])
        ev = lambda t, y: compression(t, y)  # noqa: E731
        ev.terminal = True
        ev.direction = -1 if contact else 1
        sol = solve_ivp(rhs_factory(contact), (a, b), y0, method=method, rtol=rtol, atol=atol,
                        events=ev, dense_output=True)
        nfev += sol.nfev
        if not sol.success:
            return {"success": False, "message": str(sol.message), "nfev": nfev, "series": None}
        end = sol.t_events[0][0] if len(sol.t_events[0]) else b
        last = end >= t_end_s
        mask = (t_eval >= a) & ((t_eval <= end) if last else (t_eval < end))
        idx = np.nonzero(mask)[0]
        if len(idx):
            out[:, idx] = sol.sol(t_eval[idx])
            filled += len(idx)
        y0 = sol.sol(end)
        if len(sol.t_events[0]):
            events.append((float(end), "liftoff" if contact else "touchdown"))
            contact = not contact
            if len(events) > MAX_CONTACT_SWITCHES:
                return {"success": False, "message": "tire contact chattering", "nfev": nfev,
                        "series": None}
        a = end
    if filled != n_points:
        return {"success": False, "message": f"filled {filled} of {n_points} output points",
                "nfev": nfev, "series": None}
    return {
        "success": True, "message": "ok", "nfev": nfev, "outputs": {"tire_events": events},
        "series": {"t_s": t_eval, "zs_m": out[0], "vs_m_per_s": out[1], "zu_m": out[2],
                   "vu_m_per_s": out[3], "zr_m": np.asarray(road.zr(t_eval), float)},
    }

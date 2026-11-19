"""Independent references for the linear quarter car.

Does not import the model under test (models/quarter_car.py). It shares only
the road definition (excitation/road.py).

1. Transfer functions from road displacement Zr(s), derived by hand from the
   Laplace-transformed equations of motion:

       P(s) = ms s^2 + cs s + ks          (sprung-mass dynamic stiffness)
       Q(s) = mu s^2 + cs s + ks + kt     (unsprung-mass dynamic stiffness)
       C(s) = cs s + ks                   (suspension coupling)
       D(s) = P Q - C^2

       Zs/Zr = kt C / D
       Zu/Zr = kt P / D

   Derived outputs: body acceleration s^2 Zs, suspension travel Zs - Zu,
   tire deflection Zu - Zr (tire load variation = kt (Zu - Zr)).

2. Steady-state RMS of each output for a sum of sinusoids whose frequencies are
   all periodic in the analysis window: RMS^2 = sum_i |H(j w_i)|^2 A_i^2 / 2.

3. Time response to an arbitrary road via the state-space matrix exponential
   (scipy.signal.lsim, first-order hold), with the state matrices assembled here.

4. Eigenvalues (decay rate of free transients).
"""

from __future__ import annotations

import numpy as np
from scipy import signal

from excitation.road import Road, iso8608_sinusoids


def _p(params):
    return (float(params["sprung_mass_kg"]), float(params["unsprung_mass_kg"]),
            float(params["suspension_stiffness_N_per_m"]), float(params["damping_N_s_per_m"]),
            float(params["tire_stiffness_N_per_m"]))


def frequency_response(params: dict, freq_hz) -> dict:
    ms, mu, ks, cs, kt = _p(params)
    s = 2j * np.pi * np.asarray(freq_hz, float)
    P = ms * s**2 + cs * s + ks
    Q = mu * s**2 + cs * s + ks + kt
    C = cs * s + ks
    D = P * Q - C**2
    zs = kt * C / D
    zu = kt * P / D
    return {
        "body_accel": s**2 * zs,          # (m/s^2) per m of road
        "travel": zs - zu,                # m per m
        "tire_deflection": zu - 1.0,      # m per m
    }


def steady_state_rms(params: dict) -> dict:
    """Exact window RMS for the iso8608 sum-of-sinusoids road."""
    ms, mu, ks, cs, kt = _p(params)
    road = iso8608_sinusoids(params)
    h = frequency_response(params, road.freq_hz)
    a2 = road.amp_m**2 / 2.0
    static = (ms + mu) * 9.80665
    return {
        "body_accel_rms_m_per_s2": float(np.sqrt(np.sum(np.abs(h["body_accel"]) ** 2 * a2))),
        "suspension_travel_rms_mm": 1e3 * float(np.sqrt(np.sum(np.abs(h["travel"]) ** 2 * a2))),
        "tire_load_rms_ratio": kt * float(np.sqrt(np.sum(np.abs(h["tire_deflection"]) ** 2 * a2)))
        / static,
    }


def state_space(params: dict):
    """x = [zs, vs, zu, vu], input u = zr."""
    ms, mu, ks, cs, kt = _p(params)
    A = np.array([
        [0, 1, 0, 0],
        [-ks / ms, -cs / ms, ks / ms, cs / ms],
        [0, 0, 0, 1],
        [ks / mu, cs / mu, -(ks + kt) / mu, -cs / mu],
    ])
    B = np.array([[0], [0], [0], [kt / mu]])
    return A, B


def slowest_decay_rate(params: dict) -> float:
    """Smallest |Re(lambda)| over the system eigenvalues [1/s]."""
    A, _ = state_space(params)
    return float(np.min(np.abs(np.linalg.eigvals(A).real)))


def time_response(params: dict, t: np.ndarray, refine: int = 10) -> dict:
    """Response from rest via matrix exponential on a grid `refine` x finer than t."""
    A, B = state_space(params)
    sys = signal.StateSpace(A, B, np.eye(4), np.zeros((4, 1)))
    t_fine = np.linspace(t[0], t[-1], (len(t) - 1) * refine + 1)
    road = Road(params)
    _, _, x = signal.lsim(sys, np.asarray(road.zr(t_fine), float), t_fine, interp=True)
    x = x[::refine]
    return {"zs_m": x[:, 0], "vs_m_per_s": x[:, 1], "zu_m": x[:, 2], "vu_m_per_s": x[:, 3]}

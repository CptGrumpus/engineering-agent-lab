"""Road inputs (load definitions), shared by models and reference solutions.

This module defines *what the road is*; it contains no vehicle dynamics. Both
the models under test and the independent references import it, so they are
guaranteed to see the same excitation.

Road types
----------
bump      one-period (1 - cos) bump of height h and length L traversed at speed V
          zr(t) = h/2 * (1 - cos(2*pi*V*t/L)) for 0 <= t <= L/V, else 0
iso8608   random road per ISO 8608 displacement PSD
          Gd(n) = Gd(n0) * (n/n0)^-2,  n0 = 0.1 cycles/m
          realised as a sum of sinusoids at temporal frequencies f_i = i / T_w
          (T_w = analysis window), amplitude A_i = sqrt(2 * Gd(n_i) * dn),
          dn = df / V, phases uniform on [0, 2*pi) from a fixed seed.
          Using f_i = i / T_w makes every component periodic in the analysis
          window, so window RMS values have an exact closed form.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

N0 = 0.1  # reference spatial frequency [cycles/m]


@dataclass(frozen=True)
class Sinusoids:
    freq_hz: np.ndarray
    amp_m: np.ndarray
    phase_rad: np.ndarray

    def zr(self, t):
        t = np.atleast_1d(np.asarray(t, float))
        w = 2 * np.pi * self.freq_hz
        return np.sin(np.outer(t, w) + self.phase_rad) @ self.amp_m

    def vr(self, t):
        t = np.atleast_1d(np.asarray(t, float))
        w = 2 * np.pi * self.freq_hz
        return np.cos(np.outer(t, w) + self.phase_rad) @ (self.amp_m * w)


def iso8608_sinusoids(params: dict) -> Sinusoids:
    v = float(params["speed_m_per_s"])
    gd_n0 = float(params["road_Gd_n0_m3"])
    window = float(params["window_s"])
    n_min, n_max = float(params["n_min_cyc_per_m"]), float(params["n_max_cyc_per_m"])
    df = 1.0 / window
    i = np.arange(math.ceil(n_min * v / df), math.floor(n_max * v / df) + 1)
    f = i * df
    n = f / v
    dn = df / v
    amp = np.sqrt(2.0 * gd_n0 * (n / N0) ** -2 * dn)
    rng = np.random.default_rng(int(params["road_seed"]))
    phase = rng.uniform(0.0, 2 * np.pi, size=f.size)
    return Sinusoids(f, amp, phase)


class Road:
    """Callable road: zr(t), vr(t) for a parameter dict (scalar or array t)."""

    def __init__(self, params: dict):
        self.kind = params["road"]
        if self.kind == "bump":
            self.h = float(params["bump_height_m"])
            self.duration = float(params["bump_length_m"]) / float(params["speed_m_per_s"])
        elif self.kind == "iso8608":
            self.sines = iso8608_sinusoids(params)
        else:
            raise ValueError(f"unknown road type {self.kind!r} (bump | iso8608)")

    def zr(self, t):
        if self.kind == "bump":
            t = np.asarray(t, float)
            inside = (t >= 0) & (t <= self.duration)
            return np.where(inside, 0.5 * self.h * (1 - np.cos(2 * np.pi * t / self.duration)), 0.0)
        return self.sines.zr(t) if np.ndim(t) else float(self.sines.zr(t)[0])

    def vr(self, t):
        if self.kind == "bump":
            t = np.asarray(t, float)
            inside = (t >= 0) & (t <= self.duration)
            w = 2 * np.pi / self.duration
            return np.where(inside, 0.5 * self.h * w * np.sin(w * t), 0.0)
        return self.sines.vr(t) if np.ndim(t) else float(self.sines.vr(t)[0])

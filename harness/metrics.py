"""Step-response metrics computed from a sampled time series."""

from __future__ import annotations

import numpy as np

METRICS = {
    "overshoot_pct",
    "settling_time_s",
    "static_deflection_mm",
    "peak_displacement_mm",
}


def step_metrics(t: np.ndarray, x: np.ndarray, settling_band_fraction: float) -> dict:
    """Overshoot, settling time, and deflection from a step response.

    The final sample is taken as the final value; the steady-state check in
    verification confirms that the simulation was long enough for this to hold.
    Settling time is the first sample after the last excursion outside the band,
    so its resolution is the output grid step.
    """
    xf = float(x[-1])
    peak = float(np.max(x))
    overshoot = max(0.0, (peak - xf) / abs(xf) * 100.0)

    outside = np.nonzero(np.abs(x - xf) > settling_band_fraction * abs(xf))[0]
    settling = 0.0 if outside.size == 0 else float(t[min(outside[-1] + 1, len(t) - 1)])

    return {
        "overshoot_pct": overshoot,
        "settling_time_s": settling,
        "static_deflection_mm": xf * 1e3,
        "peak_displacement_mm": peak * 1e3,
    }

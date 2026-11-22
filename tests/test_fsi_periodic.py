"""Turek-Hron periodic statistics (FSI2 / FSI3): the benchmark's mean / amplitude / frequency on a known signal."""

import numpy as np
import pytest

from studies.turek_hron_fsi import periodic_stats


def test_periodic_stats_recovers_known_signal():
    t = np.arange(0, 15, 0.001)
    f = 1.93
    s = {"t_s": t, "uy_A_m": 1.3e-3 + 8.16e-2 * np.sin(2 * np.pi * f * t),
         "ux_A_m": -1.485e-2 + 1.27e-2 * np.cos(4 * np.pi * f * t),
         "drag_N_per_m": 215.06 + 77.65 * np.sin(4 * np.pi * f * t + 0.3),
         "lift_N_per_m": 0.61 + 237.8 * np.sin(2 * np.pi * f * t + 1)}
    st = periodic_stats(s, 4)
    assert st["uy_A_amp"] == pytest.approx(8.16e-2, rel=1e-4)
    assert st["drag_mean"] == pytest.approx(215.06, rel=1e-4)
    assert st["drag_amp"] == pytest.approx(77.65, rel=1e-3)
    assert st["ux_A_mean"] == pytest.approx(-1.485e-2, rel=1e-3)
    assert st["uy_A_freq_Hz"] == pytest.approx(f, rel=2e-3)
    assert st["drag_freq_Hz"] == pytest.approx(2 * f, rel=2e-3)
    assert st["uy_period_freq_Hz"] == pytest.approx(f, rel=1e-4)


def test_periodic_stats_needs_whole_periods():
    t = np.arange(0, 1, 0.001)
    s = {k: np.sin(2 * np.pi * 1.0 * t) for k in ("uy_A_m", "ux_A_m", "drag_N_per_m", "lift_N_per_m")} | {"t_s": t}
    with pytest.raises(ValueError):
        periodic_stats(s, 4)

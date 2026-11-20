import numpy as np
import pytest

from models.fatigue import sn_6061 as sn


def test_basquin_fit_and_independent_high_cycle_value():
    f = sn.fit_basquin("both")
    assert f["n_points"] == 25
    assert -0.12 < f["b"] < -0.05                       # typical range for metals
    # extrapolated to 1e9 reversals, the fit lands within 3 % of ASM's 96.5 MPa
    assert sn.amplitude_at(1e9, f) == pytest.approx(96.5, rel=0.03)


def test_life_round_trip_and_monotonic():
    f = sn.fit_basquin("both")
    for s in (80.0, 120.0, 200.0):
        n = sn.life_cycles(s, f)
        assert sn.amplitude_at(2 * n, f) == pytest.approx(s, rel=1e-12)
    assert sn.life_cycles(100.0, f) > sn.life_cycles(150.0, f)


def test_notch_and_mean_stress():
    assert sn.notch_sensitivity(8.0) == pytest.approx(1 / (1 + 0.635 / 8))
    assert sn.fatigue_notch_factor(1.0, 8.0) == pytest.approx(1.0)        # no notch
    kt = 2.4
    assert 1.0 < sn.fatigue_notch_factor(kt, 0.5) < sn.fatigue_notch_factor(kt, 50.0) < kt
    # SWT: fully reversed is unchanged; zero-to-tension raises the amplitude by sqrt(2)
    assert sn.swt_amplitude(100.0, -100.0) == pytest.approx(100.0)
    assert sn.swt_amplitude(100.0, 0.0) == pytest.approx(50.0 * np.sqrt(2))
    assert sn.swt_amplitude(-10.0, -50.0) == 0.0

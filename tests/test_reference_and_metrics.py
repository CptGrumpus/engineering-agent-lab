import math

import numpy as np
import pytest

from harness.metrics import step_metrics
from validation import msd_analytical as ref

M, K, F = 1.0, 1000.0, 10.0


def c_for(zeta):
    return 2 * zeta * math.sqrt(K * M)


@pytest.mark.parametrize("zeta", [0.0, 0.1, 0.5, 1.0, 2.0])
def test_reference_starts_at_rest(zeta):
    t = np.array([0.0, 1e-7])
    x = ref.step_response(t, M, c_for(zeta), K, F)
    assert x[0] == pytest.approx(0.0, abs=1e-15)
    # zero initial velocity: displacement grows ~t^2, not ~t
    assert abs(x[1]) < 1e-10


@pytest.mark.parametrize("zeta", [0.1, 0.5, 1.0, 2.0])
def test_reference_final_value(zeta):
    x = ref.step_response(np.array([50.0]), M, c_for(zeta), K, F)
    assert x[0] == pytest.approx(F / K, rel=1e-9)


def test_reference_continuous_through_critical_damping():
    t = np.linspace(0, 0.5, 501)
    crit = ref.step_response(t, M, c_for(1.0), K, F)
    under = ref.step_response(t, M, c_for(1.0 - 1e-6), K, F)
    over = ref.step_response(t, M, c_for(1.0 + 1e-6), K, F)
    assert np.max(np.abs(under - crit)) / (F / K) < 1e-5
    assert np.max(np.abs(over - crit)) / (F / K) < 1e-5


@pytest.mark.parametrize("zeta", [0.1, 0.3, 0.5, 0.7])
def test_closed_form_overshoot_matches_dense_peak(zeta):
    t = np.linspace(0, 2, 200001)
    x = ref.step_response(t, M, c_for(zeta), K, F)
    peak_os = (x.max() - F / K) / (F / K) * 100
    assert peak_os == pytest.approx(ref.overshoot_pct(M, c_for(zeta), K), abs=1e-6)


def test_metrics_on_synthetic_signal():
    t = np.linspace(0, 1, 1001)
    x = np.ones_like(t)
    x[:100] = 1.5  # 50 % above final value until t = 0.099
    m = step_metrics(t, x, 0.02)
    assert m["overshoot_pct"] == pytest.approx(50.0)
    assert m["settling_time_s"] == pytest.approx(0.1)
    assert m["static_deflection_mm"] == pytest.approx(1000.0)


def test_metrics_monotonic_signal_has_no_overshoot():
    t = np.linspace(0, 1, 1001)
    x = 1 - np.exp(-10 * t)
    m = step_metrics(t, x, 0.02)
    assert m["overshoot_pct"] == 0.0
    # settles when |x - x_end| <= 2 % of x_end -> exp(-10 t) - exp(-10) <= 0.02 x_end
    assert m["settling_time_s"] == pytest.approx(0.391, abs=2e-3)

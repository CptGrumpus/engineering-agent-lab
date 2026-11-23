"""Study G (rotor critical speeds): the parts that do not need ROSS."""

import numpy as np
import pytest

from studies.rotor_critical import STUDY, _forward, separation_margin_pct


def test_separation_margin_below_inside_above():
    assert separation_margin_pct(850.0, 1000.0, 3000.0) == pytest.approx(15.0)
    assert separation_margin_pct(3450.0, 1000.0, 3000.0) == pytest.approx(15.0)
    # inside the range: negative, by the nearer edge
    assert separation_margin_pct(2900.0, 1000.0, 3000.0) == pytest.approx(-100 * 100 / 3000)
    assert separation_margin_pct(1100.0, 1000.0, 3000.0) == pytest.approx(-10.0)


def test_metrics_use_forward_whirl_only():
    crit = [{"rpm": 2909.0, "whirl": "backward"}, {"rpm": 4000.0, "whirl": "forward"},
            {"rpm": 9000.0, "whirl": "mixed"}]
    assert [c["rpm"] for c in _forward(crit)] == [4000.0, 9000.0]
    series = {"speed_rpm": np.array([1000.0, 3000.0]), "disc_amp_x_m": np.array([1e-6, 3e-6]),
              "disc_amp_y_m": np.array([2e-6, 1e-6])}
    params = {"speed_min_rpm": 1000, "speed_max_rpm": 3000}
    m = STUDY.compute_metrics(series, params, {}, {"critical_speeds": crit, "rotor_mass_kg": 40.0})
    assert m["first_forward_critical_rpm"] == 4000.0
    assert m["separation_margin_pct"] == pytest.approx(100 * 1000 / 3000)
    assert m["unbalance_amp_max_um"] == pytest.approx(3.0)


def test_odd_element_count_rejected():
    p = {"n_elements": 21, "speed_min_rpm": 1000, "speed_max_rpm": 3000, "campbell_max_rpm": 9000}
    with pytest.raises(ValueError):
        STUDY.derive(p)

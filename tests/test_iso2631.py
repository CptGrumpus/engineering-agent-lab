"""ISO 2631-1 Wk weighting used for ride comfort."""

import numpy as np
import pytest

from validation import iso2631 as w


def test_wk_matches_the_standards_table():
    for f, v in w.TABLE_WK.items():
        assert abs(w.wk(f)) == pytest.approx(v, abs=1.5e-3)     # Table 3 is given to 3 decimals


def test_time_domain_filter_matches_the_transfer_function_for_a_sinusoid():
    f, a0 = 5.0, 1.0
    t = np.linspace(0, 30, 300001)
    y = w.weighted_series(t, a0 * np.sin(2 * np.pi * f * t))
    late = t > 20                                                 # start-up transient gone
    assert np.sqrt(np.mean(y[late] ** 2)) == pytest.approx(abs(w.wk(f)) * a0 / np.sqrt(2), rel=1e-3)


def test_comfort_classes():
    assert w.comfort_class(0.2) == "not uncomfortable"
    assert w.comfort_class(0.94) == "fairly uncomfortable"
    assert w.comfort_class(3.0) == "extremely uncomfortable"

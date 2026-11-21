"""Local linear response surface (harness/response_surface.py)."""

import numpy as np
import pytest

from harness.response_surface import design_inside_limit, fit_linear, predict


def _noisy_plane(n=40, sd=0.5, seed=1):
    rng = np.random.default_rng(seed)
    X = np.c_[rng.uniform(9.9, 10.6, n), rng.uniform(7.9, 9.1, n), rng.uniform(35.7, 36.7, n)]
    y = 222.4 - 3.77 * X[:, 0] - 3.52 * X[:, 1] - 1.53 * X[:, 2] + rng.normal(0, sd, n)
    return X, y


def test_fit_recovers_the_plane_and_the_noise():
    X, y = _noisy_plane()
    f = fit_linear(X, y)
    assert f["coef"][1:] == pytest.approx([-3.77, -3.52, -1.53], abs=0.6)
    assert 0.35 < f["residual_sd"] < 0.65
    value, se = predict(f, X.mean(axis=0))
    assert se < f["residual_sd"]                       # the fit at the centroid beats one sample


def test_design_reaches_the_target_without_leaving_the_sampled_box():
    X, y = _noisy_plane()
    d = design_inside_limit(X, y, limit=97.5, n_sd=2.0, order=(1, 2, 0))
    assert d["reached"] and d["fitted"] == pytest.approx(d["target"])
    assert np.all(d["x"] >= X.min(axis=0)) and np.all(d["x"] <= X.max(axis=0))


def test_needs_more_points_than_coefficients():
    with pytest.raises(ValueError):
        fit_linear(np.eye(3), [1.0, 2.0, 3.0])

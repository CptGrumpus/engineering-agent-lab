"""harness.uncertainty against closed forms: Ishigami's Sobol indices, linear limit states (FORM exact)."""

import math

import numpy as np
import pytest
from scipy import stats

from harness import uncertainty as U

A_ISH, B_ISH = 7.0, 0.1


def ishigami(x):
    return np.sin(x[:, 0]) + A_ISH * np.sin(x[:, 1]) ** 2 + B_ISH * x[:, 2] ** 4 * np.sin(x[:, 0])


def ishigami_exact():
    a, b, p = A_ISH, B_ISH, math.pi
    V1 = 0.5 * (1 + b * p ** 4 / 5) ** 2
    V2 = a ** 2 / 8
    V13 = b ** 2 * p ** 8 * (1 / 18 - 1 / 50)
    V = V1 + V2 + V13
    return np.array([V1, V2, 0.0]) / V, np.array([V1 + V13, V2, V13]) / V


def test_sobol_indices_of_the_ishigami_function():
    dists = [stats.uniform(-math.pi, 2 * math.pi)] * 3
    r = U.sobol_indices(ishigami, dists, 2 ** 14, seed=3, n_boot=100)
    s1, st = ishigami_exact()
    assert r["S1"] == pytest.approx(s1, abs=0.02)
    assert r["ST"] == pytest.approx(st, abs=0.02)
    assert r["n_calls"] == 2 ** 14 * 5
    for k in range(3):                                   # the bootstrap interval brackets the exact value
        assert r["ST_ci"][k, 0] - 0.01 <= st[k] <= r["ST_ci"][k, 1] + 0.01


def test_sobol_indices_of_a_linear_model_are_its_variance_shares():
    dists = [stats.norm(0, 1), stats.norm(0, 2), stats.norm(0, 3)]
    r = U.sobol_indices(lambda x: x.sum(axis=1), dists, 2 ** 13, seed=1, n_boot=20)
    want = np.array([1, 4, 9]) / 14
    assert r["S1"] == pytest.approx(want, abs=0.02) and r["ST"] == pytest.approx(want, abs=0.02)


def test_form_is_exact_for_a_linear_limit_state_in_normal_variables():
    R, S = stats.norm(10.0, 1.0), stats.norm(6.0, 1.5)
    beta = 4.0 / math.sqrt(1.0 + 1.5 ** 2)
    r = U.form(lambda x: x[0] - x[1], [R, S])
    assert r["beta"] == pytest.approx(beta, rel=1e-6)
    assert r["pf"] == pytest.approx(stats.norm.cdf(-beta), rel=1e-5)
    assert r["alpha"] == pytest.approx(np.array([1.0, -1.5]) / math.sqrt(3.25), abs=1e-6)


def test_form_is_exact_for_log_capacity_minus_log_demand_in_lognormal_variables():
    R, S = stats.lognorm(0.1, scale=200.0), stats.lognorm(0.3, scale=80.0)
    beta = math.log(200 / 80) / math.hypot(0.1, 0.3)
    r = U.form(lambda x: math.log(x[0]) - math.log(x[1]), [R, S])
    assert r["beta"] == pytest.approx(beta, rel=1e-6)


def test_importance_sampling_and_plain_monte_carlo_agree_with_the_exact_probability():
    R, S = stats.norm(10.0, 1.0), stats.norm(6.0, 1.5)
    g = lambda x: x[:, 0] - x[:, 1]                       # noqa: E731
    exact = stats.norm.cdf(-4.0 / math.sqrt(3.25))        # about 1.3e-2
    f = U.form(lambda x: x[0] - x[1], [R, S])
    imp = U.importance_sampling(g, [R, S], f["u_star"], 20000, seed=2)
    assert imp["ci"][0] <= exact <= imp["ci"][1] and imp["cov"] < 0.02
    mc = U.failure_probability(g(U.sample([R, S], 2 ** 16, seed=4, method="random")))
    assert mc["ci"][0] <= exact <= mc["ci"][1]


def test_importance_sampling_reaches_a_probability_far_below_plain_sampling():
    R, S = stats.norm(10.0, 0.5), stats.norm(4.0, 0.5)    # beta 8.49, pf about 1e-17
    beta = 6.0 / math.sqrt(0.5)
    f = U.form(lambda x: x[0] - x[1], [R, S])
    imp = U.importance_sampling(lambda x: x[:, 0] - x[:, 1], [R, S], f["u_star"], 20000, seed=5)
    assert imp["pf"] == pytest.approx(stats.norm.cdf(-beta), rel=0.1)


def test_wilson_interval_at_zero_failures():
    r = U.failure_probability(np.ones(1000))
    assert r["pf"] == 0 and r["ci"][0] == 0 and r["ci"][1] == pytest.approx(3.83e-3, rel=0.01)


def test_samples_follow_their_marginals():
    x = U.sample([stats.norm(5, 2), stats.lognorm(0.2, scale=3.0)], 2 ** 12, seed=0)
    assert x[:, 0].mean() == pytest.approx(5, abs=0.01) and x[:, 0].std() == pytest.approx(2, rel=0.01)
    assert np.median(x[:, 1]) == pytest.approx(3.0, rel=0.01)

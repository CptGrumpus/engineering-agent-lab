"""Bracket optimisation loop: the tapered-beam reference, the stress measurement, and the
optimisation driver's handling of unverified candidates."""

import numpy as np
import pytest

from harness.optimize import _constraint_values
from validation import beam_theory as bt
from validation import tapered_beam as tb

F, L, E, NU, B = 1000.0, 200.0, 210000.0, 0.3, 20.0


def test_prismatic_limit_equals_the_cantilever_reference():
    assert tb.tip_deflection(F, L, E, NU, B, 20, 20) == pytest.approx(bt.timoshenko_tip(F, L, E, NU, B, 20), rel=1e-12)
    assert tb.peak_nominal_stress(F, L, B, 20, 20) == (pytest.approx(bt.bending_stress(F, L, B, 20)), 0.0)


def test_interior_stress_peak_location_matches_a_dense_search():
    for hr, ht in ((30, 10), (26, 8.7), (25, 6), (30, 16)):
        x = np.linspace(0, L, 200001)
        s = tb.nominal_stress(x, F, L, B, hr, ht)
        peak, xp = tb.peak_nominal_stress(F, L, B, hr, ht)
        assert peak == pytest.approx(s.max(), rel=1e-9)
        assert xp == pytest.approx(x[np.argmax(s)], abs=2e-3)


def test_tapered_deflection_against_a_closed_form_bending_integral():
    # Euler-Bernoulli part for a linear taper, closed form (Roark-type integral) via substitution
    hr, ht = 30.0, 10.0
    c = (ht - hr) / L
    def integrand_exact(x):
        return (L - x) ** 2 / (E * B * (hr + c * x) ** 3 / 12)
    from scipy.integrate import quad
    bend = F * quad(integrand_exact, 0, L, epsrel=1e-13)[0]
    G = E / (2 * (1 + NU))
    shear = F * np.log(ht / hr) / c / (tb.cowper_kappa(NU) * G * B)
    assert tb.tip_deflection(F, L, E, NU, B, hr, ht) == pytest.approx(bend + shear, rel=1e-10)


def test_beam_optimum_is_stress_governed_at_mid_span_for_a_100_mpa_allowable():
    o = tb.optimum(F, L, E, NU, B, 1.0, 100.0, ((10, 40), (6, 40)), margin=0.005)
    assert o["peak_stress_MPa"] == pytest.approx(99.5, rel=1e-5)
    assert o["tip_deflection_mm"] < 0.995                                 # deflection not active
    assert o["peak_stress_x_mm"] == pytest.approx(100.0, abs=0.5)         # h_t / h_r = 1/3
    assert o["tip_height_mm"] / o["root_height_mm"] == pytest.approx(1 / 3, abs=2e-3)


def test_constraint_values_with_margin():
    reqs = [{"metric": "d", "operator": "<=", "limit": 1.0}, {"metric": "s", "operator": "<=", "limit": 100.0}]
    g = _constraint_values({"d": 0.995, "s": 101.0}, reqs, 0.005)
    assert g[0] == pytest.approx(0.0, abs=1e-12) and g[1] == pytest.approx(-0.015)


def test_stress_profile_recovers_beam_theory_from_exact_surface_data():
    from studies.tapered_bracket import stress_profile
    hr, ht = 26.0, 8.7
    x = np.linspace(0, L, 801)
    h = tb.height(x, L, hr, ht)
    s = tb.nominal_stress(x, F, L, B, hr, ht)
    th = np.arctan((ht - hr) / (2 * L))
    # a field whose fibre stress along the top surface equals M/Z: sigma_xx = s / cos^2
    series = {"x_mm": x, "z_mm": h / 2, "sxx_MPa": s / np.cos(th) ** 2, "szx_MPa": 0 * x, "szz_MPa": 0 * x}
    p = dict(tip_load_N=F, length_mm=L, width_mm=B, root_height_mm=hr, tip_height_mm=ht)
    xs, ratio, sig = stress_profile(series, p)
    assert np.allclose(ratio, 1.0, atol=1e-12)
    assert sig.max() == pytest.approx(tb.peak_nominal_stress(F, L, B, hr, ht)[0], rel=1e-6)

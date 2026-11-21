"""Notch-root plasticity references: Neuber, Glinka, the material curve and its energy integral."""

import numpy as np
import pytest

from validation import notch_plasticity as npl

EP = [0.0, 0.0002, 0.0005, 0.001, 0.002, 0.004, 0.007, 0.012, 0.02, 0.04, 0.08]
SP = [223.8, 234.9, 250.5, 262.9, 276.0, 289.7, 301.3, 312.9, 324.3, 340.4, 357.3]
MAT = npl.Material(68900.0, EP, SP)


def test_curve_is_elastic_below_first_yield_and_passes_through_the_table():
    assert MAT.strain(200.0) == pytest.approx(200.0 / 68900.0)
    assert MAT.strain(276.0) == pytest.approx(276.0 / 68900.0 + 0.002)


def test_energy_integral_is_exact_for_the_piecewise_linear_curve():
    s = np.linspace(0, 300.0, 300001)
    e = MAT.strain(s)
    assert MAT.energy(300.0) == pytest.approx(np.trapezoid(s, e), rel=1e-8)


def test_both_rules_return_the_elastic_point_below_yield():
    for rule in (npl.neuber, npl.glinka):
        s, e = rule(MAT, 200.0)
        assert s == 200.0 and e == pytest.approx(200.0 / 68900.0)


def test_glinka_strain_never_exceeds_neuber_and_both_satisfy_their_equations():
    for se in (250.0, 349.3, 450.0):
        sn, en = npl.neuber(MAT, se)
        sg, eg = npl.glinka(MAT, se)
        assert eg <= en and sg <= sn
        assert sn * en == pytest.approx(se**2 / 68900.0, rel=1e-9)
        assert MAT.energy(sg) == pytest.approx(se**2 / (2 * 68900.0), rel=1e-9)


def test_table_must_be_monotonic():
    with pytest.raises(ValueError):
        npl.Material(68900.0, [0.0, 0.001, 0.0005], [220.0, 250.0, 260.0])

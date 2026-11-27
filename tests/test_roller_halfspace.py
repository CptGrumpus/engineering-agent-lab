"""Study 10 part 2: the half-space contact solver against Hertz."""
import math

import numpy as np
import pytest

from models.contact import roller_halfspace as RH
from validation import hertz

BASE = dict(roller_radius_mm=50.0, roller_length_mm=30.0, youngs_modulus_MPa=210000.0, poisson_ratio=0.3,
            line_load_N_per_mm=500.0, profile="none")


def test_love_rectangle_centre_of_a_square():
    # integral of 1/rho over a square of side 2c, at its centre: 8 c ln(1 + sqrt 2)
    c = 0.7
    assert RH.rect_influence(0.0, 0.0, -c, c, -c, c) == pytest.approx(8 * c * math.log(1 + math.sqrt(2)), rel=1e-12)


def test_long_straight_roller_mid_length_is_hertz_line_contact():
    r = RH.solve(BASE | {"roller_length_mm": 200.0}, nx=24, y_max_cell=4.0)
    ref = hertz.line_contact(r["mid_line_load_N_per_mm"], 50.0, 210000.0, 0.3)
    assert r["mid_peak_MPa"] == pytest.approx(ref["peak_pressure_MPa"], rel=2e-3)
    assert r["load_error"] < 1e-5


def test_crowned_roller_is_hertz_elliptical_contact():
    Rc = 3000.0
    E_star = 1 / (2 * 0.91 / 210000.0)
    h = RH.hertz_elliptic(20000.0, 50.0, Rc, E_star)
    assert h["a_mm"] == pytest.approx(2 * h["p0_MPa"] * 50.0 / E_star, rel=0.02)   # long ellipse: line-contact limit
    r = RH.solve(BASE | {"roller_length_mm": 40.0}, nx=24, x_max=1.6 * h["a_mm"], y_fine=0.25, y_max_cell=0.5,
                 drop_um=lambda _p, y: 1e3 * np.asarray(y) ** 2 / (2 * Rc))
    assert r["peak_MPa"] == pytest.approx(h["p0_MPa"], rel=2e-3)


def test_active_set_on_a_small_problem():
    K = np.array([[2.0, 0.5], [0.4, 1.0]])
    b = np.array([1.0, -1.0])                 # the second point is open
    p = RH.contact_lcp(K, b)
    assert p[1] == 0.0 and p[0] == pytest.approx(0.5)
    assert (K @ p - b)[1] >= 0

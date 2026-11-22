"""Rotor overspeed study (study 7): linearization and the rotating-disk reference on cases with known answers."""

import math

import numpy as np
import pytest

from models.fea.rotor_ccx import linearize, rotating_disk


def test_linearize_separates_membrane_and_bending():
    s = np.linspace(0.0, 2.0, 201)
    stt = 100.0 + 50.0 * (1 - s)           # 100 MPa membrane, 50 MPa bending (linear across t = 2)
    zero = np.zeros_like(s)
    m, mb = linearize(s, zero, stt, zero)
    assert m == pytest.approx(100.0, rel=1e-9)
    assert mb == pytest.approx(150.0, rel=1e-9)


def test_linearize_removes_a_peak():
    s = np.linspace(0.0, 1.0, 2001)
    peak = 400.0 * np.exp(-((s - 0.0) / 0.02) ** 2)   # a local peak at one surface, like a notch
    zero = np.zeros_like(s)
    m, mb = linearize(s, zero, 100.0 + peak, zero)
    assert mb < 100.0 + 400.0 / 2                      # the linearized value is far below the peak


def test_linearize_von_mises_with_shear():
    s = np.linspace(0.0, 1.0, 11)
    m, mb = linearize(s, np.zeros_like(s), np.zeros_like(s), np.full_like(s, 10.0))
    assert m == pytest.approx(math.sqrt(3) * 10.0) and mb == pytest.approx(math.sqrt(3) * 10.0)


def test_rotating_disk_free_edges_and_bore_value():
    a, b, rho, w, nu = 55.0, 80.0, 7650e-12, 754.0, 0.3
    sr, st = rotating_disk(np.array([a, b]), a, b, rho, w, nu)
    assert abs(sr[0]) < 1e-12 and abs(sr[1]) < 1e-12          # traction-free bore and rim
    assert st[0] == pytest.approx((3 + nu) / 4 * rho * w ** 2 * (b * b + (1 - nu) / (3 + nu) * a * a), rel=1e-12)

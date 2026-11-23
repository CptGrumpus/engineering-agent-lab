"""Study F (edge crack): growth and critical-crack logic against the closed-form hand estimate (no CalculiX)."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest
from scipy.integrate import quad

from studies.edge_crack import STUDY, growth

spec = importlib.util.spec_from_file_location("ec", Path(__file__).resolve().parent.parent / "models/fea/edge_crack.py")
ec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ec)

P = {"width_mm": 100.0, "sigma_max_MPa": 150.0, "stress_ratio": 0.1, "yield_strength_MPa": 355.0,
     "k_mat_MPa_sqrt_m": 100.0, "paris_C": 5.21e-13, "paris_m": 3.0, "dK_threshold": 63.0, "initial_crack_mm": 2.0}
A = np.array([2, 4, 7, 10, 15, 20, 25, 30, 35, 40, 45], float)


def tada_K(a):
    return np.array([ec.tada_F(x / 100.0) for x in a]) * 150.0 * np.sqrt(np.pi * a)


def test_growth_reproduces_closed_form():
    g = growth(P, A, tada_K(A))
    K = lambda a: ec.tada_F(a / 100) * 150 * np.sqrt(np.pi * a)  # noqa: E731
    a_c = 37.1
    assert g["a_crit_mm"] == pytest.approx(a_c, abs=0.1)
    assert g["governs"] == "toughness"
    exact = quad(lambda a: 1 / (5.21e-13 * (0.9 * K(a)) ** 3), 2.0, g["a_crit_mm"])[0]
    assert g["life_quad"] == pytest.approx(exact, rel=2e-3)      # spline of F over 11 points
    assert g["life_quad"] == pytest.approx(93256, rel=5e-3)


def test_net_section_yield_can_govern():
    a = np.concatenate([A, [50.0, 55.0, 60.0]])
    g = growth(dict(P, k_mat_MPa_sqrt_m=400.0), a, tada_K(a))    # K stays under 400 MPa sqrt m up to 60 mm
    assert g["governs"] == "net-section yield"
    assert g["a_crit_mm"] == pytest.approx(100 * (1 - 150 / 355))


def test_critical_crack_beyond_sample_rejected():
    with pytest.raises(ValueError):
        growth(dict(P, k_mat_MPa_sqrt_m=400.0), A, tada_K(A))      # yield crack 57.7 mm, sample ends at 45


def test_stress_ratio_validated():
    with pytest.raises(ValueError):
        STUDY.derive({"stress_ratio": 1.0})


def test_opening_route_recovers_exact_field():
    # crack-face opening of an exact K field: uy = 4 (1 - nu^2) K / E sqrt(r / 2 pi)
    E, nu, K, a = 210000.0, 0.3, 500.0, 10.0
    xs = np.linspace(0, a - 0.01, 200)
    disp = {i + 1: (0.0, 4 * (1 - nu ** 2) * K / E * np.sqrt((a - x) / (2 * np.pi)), 0.0) for i, x in enumerate(xs)}
    info = {"node_x": {i + 1: x for i, x in enumerate(xs)}}
    k, n = ec.k_from_opening(disp, info, a=a, E=E, nu=nu, r_min=0.05, r_max=1.0)
    assert n > 3 and k == pytest.approx(K, rel=1e-9)

"""Stress linearisation (ASME VIII-2 Annex 5-A method) and C3D10 sampling."""

import numpy as np
import pytest

from harness.linearize import Tet10Sampler, linearize, rotate, tet10_shape, von_mises

AX = np.eye(3)  # n = x (through the wall), m = y, h = z


def test_linear_profile_is_reproduced_exactly():
    t, a, b = 16.0, 100.0, -2.0
    s = np.linspace(0, t, 21)
    st = np.zeros((21, 6))
    st[:, 2] = a + b * s          # hoop (h-h)
    st[:, 1] = 0.5 * (a + b * s)  # meridional (m-m)
    st[:, 0] = -3.5 * (1 - s / t)  # through-wall: membrane only
    r = linearize(s, st, AX)
    assert r["membrane"][2] == pytest.approx(a + b * t / 2)
    assert r["bending"][2] == pytest.approx(-b * t / 2)
    assert r["at_start"][2] == pytest.approx(a) and r["at_end"][2] == pytest.approx(a + b * t)
    assert r["bending"][0] == 0.0 and r["membrane"][0] == pytest.approx(-1.75)


def test_lame_membrane_hoop_is_pR_over_t():
    """Equilibrium: the mean hoop stress of a thick cylinder is p Ri / t exactly (closed ends: axial is uniform)."""
    p, Ri, Ro = 3.5, 500.0, 516.0
    r = np.linspace(Ri, Ro, 41)
    A, B = p * Ri**2 / (Ro**2 - Ri**2), p * Ri**2 * Ro**2 / (Ro**2 - Ri**2)
    st = np.zeros((41, 6))
    st[:, 0], st[:, 2], st[:, 1] = A - B / r**2, A + B / r**2, A  # radial (n), hoop (h), axial (m)
    res = linearize(r - Ri, st, AX)
    assert res["membrane"][2] == pytest.approx(p * Ri / (Ro - Ri), rel=1e-8)
    assert res["membrane"][0] == pytest.approx(-p * Ri / (Ri + Ro), rel=1e-6)  # mean radial stress


def test_rotation_and_von_mises():
    s = np.array([100.0, 0, 0, 0, 0, 0])
    c, d = np.cos(np.pi / 6), np.sin(np.pi / 6)
    R = np.array([[c, d, 0], [-d, c, 0], [0, 0, 1]])
    r = rotate(s, R)
    assert von_mises(r) == pytest.approx(100.0)
    assert r[0] == pytest.approx(100 * c**2) and r[3] == pytest.approx(-100 * c * d)


def test_tet10_sampling_is_exact_for_quadratic_fields():
    corners = np.array([[0, 0, 0], [2.0, 0, 0], [0, 1.5, 0], [0, 0, 1.0]])
    from harness.linearize import EDGES
    nodes = np.vstack([corners] + [(corners[a] + corners[b]) / 2 for a, b in EDGES])
    f = lambda x: 1 + 2 * x[..., 0] - x[..., 1] + 0.5 * x[..., 2] ** 2 + x[..., 0] * x[..., 1]  # noqa: E731
    smp = Tet10Sampler(np.arange(1, 11), nodes, [np.arange(1, 11)])
    pts = np.array([[0.3, 0.2, 0.1], [0.5, 0.5, 0.2]])
    val, viol = smp.sample(pts, f(nodes)[:, None])
    assert viol == 0.0
    assert np.allclose(val[:, 0], f(pts))
    assert np.allclose(tet10_shape(np.array([0.25] * 4)).sum(), 1.0)

"""Plane frame solver (validation/frame2d.py) against exact results of beam and beam-column theory."""

import math

import numpy as np
import pytest

from validation.frame2d import Frame

E, A, I = 200e3, 5000.0, 4.0e7      # N/mm2, mm2, mm4


def test_fixed_fixed_beam_uniform_load():
    """End moment w L^2 / 12, mid-span deflection w L^4 / (384 E I)."""
    L, w = 6000.0, 20.0
    f = Frame()
    a, m, b = f.node(0, 0), f.node(L / 2, 0), f.node(L, 0)
    f.member(a, m, E, A, I, w=-w)
    f.member(m, b, E, A, I, w=-w)
    f.support(a); f.support(b)
    U = f.solve()
    assert U[3 * m + 1] == pytest.approx(-w * L ** 4 / (384 * E * I), rel=1e-10)
    assert abs(f.end_forces[0][2]) == pytest.approx(w * L * L / 12, rel=1e-10)
    assert f.reactions[1] + f.reactions[7] == pytest.approx(w * L, rel=1e-12)


@pytest.mark.parametrize("n_el", [1, 4])
def test_cantilever_axial_and_lateral_load_exact(n_el):
    """Compression P and tip load H: M_base = H tan(kL) / k; tension: H tanh(kL) / k (exact, any subdivision)."""
    L, H = 4000.0, 1000.0
    Pcr = math.pi ** 2 * E * I / (4 * L * L)
    for P in (0.5 * Pcr, -0.5 * Pcr):
        f = Frame()
        ns = [f.node(0, L * i / n_el) for i in range(n_el + 1)]
        for i in range(n_el):
            f.member(ns[i], ns[i + 1], E, A, I)
        f.support(ns[0])
        f.load(ns[-1], fx=H, fy=-P)
        f.solve(second_order=True)
        k = math.sqrt(abs(P) / (E * I))
        exact = H * (math.tan(k * L) if P > 0 else math.tanh(k * L)) / k
        assert abs(f.reactions[2]) == pytest.approx(exact, rel=1e-6)
        assert f.axial[0] == pytest.approx(P, rel=1e-9)


def test_pinned_beam_column_with_uniform_load_exact():
    """Mid-span moment of a pinned beam-column, uniform load w and compression P: (w / k^2) (sec(kL / 2) - 1)."""
    L, w = 6000.0, 15.0
    Pcr = math.pi ** 2 * E * I / L ** 2
    P = 0.4 * Pcr
    f = Frame()
    a, m, b = f.node(0, 0), f.node(L / 2, 0), f.node(L, 0)
    f.member(a, m, E, A, I, w=-w)
    f.member(m, b, E, A, I, w=-w)
    f.support(a, True, True, False)
    f.support(b, False, True, False)
    f.load(b, fx=-P)
    f.solve(second_order=True)
    k = math.sqrt(P / (E * I))
    exact = w / k ** 2 * (1 / math.cos(k * L / 2) - 1)
    assert abs(f.end_forces[0][5]) == pytest.approx(exact, rel=1e-8)


def test_portal_frame_equilibrium_and_symmetry():
    """Fixed-base portal under a uniform beam load and a sway load: reactions balance the loads, moments too."""
    H, B, w, Hx = 4000.0, 6000.0, 35.0, 15e3
    f = Frame()
    n0, n1, n2, n3 = f.node(0, 0), f.node(0, H), f.node(B, H), f.node(B, 0)
    f.member(n0, n1, E, A, I)
    f.member(n1, n2, E, A, I, w=-w)
    f.member(n2, n3, E, A, I)
    f.support(n0); f.support(n3)
    f.load(n1, fx=Hx)
    for second in (False, True):
        f.solve(second_order=second)
        R = f.reactions
        assert R[0] + R[9] == pytest.approx(-Hx, rel=1e-9)
        assert R[1] + R[10] == pytest.approx(w * B, rel=1e-9)
        # moments about the left base: reactions + loads = 0, the loads at their displaced positions (second order:
        # the gravity load moved by the sway is the P-Delta moment; first order: U = 0 in this sum's sense is exact)
        Mr = R[2] + R[11] + B * R[10]
        u_top = (f.U[3 * n1] + f.U[3 * n2]) / 2 if second else 0.0
        v_top = f.U[3 * n1 + 1] if second else 0.0
        Ml = -Hx * (H + v_top) - w * B * (B / 2 + u_top)
        # the P-Delta formulation is linear in the chord rotation, so second order leaves an O(theta^2) residual:
        # 5e-6 of w B^2 here (sway / height about 2.5e-3); first order closes to round-off
        assert Mr + Ml == pytest.approx(0.0, abs=(2e-5 if second else 1e-9) * w * B * B)
    first = Frame()
    for x, y in f.nodes:
        first.node(x, y)
    first.members, first.fixed, first.loads = f.members, f.fixed, {}
    first.solve()
    assert first.reactions[2] == pytest.approx(-first.reactions[11], rel=1e-9)   # symmetric gravity: equal and opposite
    second_sway = f.U[3 * n1]
    f.solve(second_order=False)
    assert second_sway > f.U[3 * n1]                                            # P-Delta increases the sway

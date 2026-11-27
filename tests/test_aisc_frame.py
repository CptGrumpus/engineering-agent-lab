"""validation/aisc_frame.py (direct analysis method on the plane-frame solver) against Example C.1A of the AISC v16.0
Design Examples: a pinned-base W12x65 / W18x40 portal, 20 ft by 30 ft, 2.40 kip/ft on the beam, 36.0 kips at each
column top, a 144-kip leaning column tied to the right column, notional load 0.576 kip, 80 % stiffness (LRFD).

The example's figures print three significant figures from commercial software whose settings it does not give
(shear deformation, for one, which our solver leaves out and which would add drift). Measured agreement: forces and
moments within 0.7 %, drift within 1.7 % (first order) and 0.7 % (second order); the tolerances are 1 % on forces
and 2 % on drift.
"""
import pytest

from validation import aisc360 as a
from validation.aisc_frame import portal, tau_b

KW = dict(H=240.0, L=360.0, E=29000.0, w=2.40 / 12, P_tops=(36.0, 36.0), H_left=0.576, base="pinned",
          stiffness_factor=0.8, P_leaning=144.0)


def run(second_order):
    return portal(col=a.shape("W12X65"), beam=a.shape("W18X40"), second_order=second_order, **KW)


@pytest.mark.parametrize("second_order, drift, mb, mc, hb, hc, vb, vc", [
    (False, 0.181, 113, 124, 5.64, 6.21, 71.6, 72.4),      # Fig. C.1A-3
    (True, 0.290, 109, 127, 5.52, 6.26, 71.4, 72.6),       # Fig. C.1A-4
])
def test_c1a(second_order, drift, mb, mc, hb, hc, vb, vc):
    r = run(second_order)
    assert r["drift"] == pytest.approx(drift, rel=0.02)
    assert abs(r["left"]["M_top"]) / 12 == pytest.approx(mb, rel=0.01)
    assert abs(r["right"]["M_top"]) / 12 == pytest.approx(mc, rel=0.01)
    assert abs(r["reactions"]["left"][0]) == pytest.approx(hb, rel=0.01)
    assert abs(r["reactions"]["right"][0]) == pytest.approx(hc, rel=0.01)
    assert r["reactions"]["left"][1] == pytest.approx(vb, rel=0.005)
    assert r["reactions"]["right"][1] == pytest.approx(vc, rel=0.005)


def test_c1a_equilibrium_and_tau_b():
    r = run(True)
    total = 2.40 * 30 + 2 * 36.0                           # leaning column carries its own 144 kips to its base
    # 1e-6, not machine precision: in second order the link to the leaning column tilts very slightly (its two ends
    # shorten differently), so its axial force puts about 2e-5 kips of the leaning load on the frame
    assert r["reactions"]["left"][1] + r["reactions"]["right"][1] == pytest.approx(total, rel=1e-6)
    # horizontal: all supports together balance the notional load; in second order the leaning column's pinned base
    # takes part of it (its P-Delta shear, 144 kips x drift / H)
    assert sum(r["frame"].reactions[0::3]) == pytest.approx(-0.576, abs=1e-9)
    lean_base = r["reactions"]["left"][0] + r["reactions"]["right"][0] + 0.576
    # the leaning column sways with the right column's top (the link is nearly rigid), not the frame's average drift
    assert -lean_base == pytest.approx(144.0 * r["right"]["ux_top"] / 240.0, rel=1e-3)
    assert tau_b(1.0 * r["right"]["N"], 50 * 19.1) == 1.0  # alpha Pr / Pns = 0.076 (the example: 0.0760)
    assert r["right"]["N"] / 955 == pytest.approx(0.0760, abs=5e-4)


def test_second_order_drift_ratio():
    assert run(True)["drift"] / run(False)["drift"] == pytest.approx(1.60, rel=0.02)


# ---------------------------------------------------------------- knee springs and slip (study 28 part 2)
def _sec(A, I):
    return {"A": A, "Ix": I}


@pytest.mark.parametrize("k_ratio", [2.0, 20.0, 1e9])
def test_semi_rigid_portal_symmetric_gravity_closed_form(k_ratio):
    """Fixed-base portal, symmetric UDL, axially rigid, first order: compatibility at the knee (column top
    stiffness 4 EIc / h, beam end rotation w L^3 / 24 EIb - M L / 2 EIb, spring M / k) gives
    M = (w L^2 / 12)(L / 2 EIb) / (h / 4 EIc + L / 2 EIb + 1 / k); k -> infinity is Kleinlogel's w L^2 / (6 (k + 2))."""
    from validation.aisc_frame import portal

    E, H, L, w, Ic, Ib = 200e3, 4000.0, 6000.0, 35.0, 7.1e7, 1.2e8
    k = k_ratio * E * Ib / L
    r = portal(H=H, L=L, E=E, col=_sec(1e9, Ic), beam=_sec(1e9, Ib), w=w, second_order=False, knee_k=k)
    want = (w * L * L / 12) * (L / (2 * E * Ib)) / (H / (4 * E * Ic) + L / (2 * E * Ib) + 1 / k)
    # A = 1e9 mm2 is stiff, not rigid: the beam's thrust still shortens it (2e-8 here)
    assert abs(r["beam_end_moments"][0]) == pytest.approx(want, rel=1e-6)
    assert abs(r["beam_end_moments"][1]) == pytest.approx(want, rel=1e-6)


def test_knee_slip_secant_and_pinned_limit():
    from validation.aisc_frame import portal

    E, H, L, w, Ic, Ib = 200e3, 4000.0, 6000.0, 35.0, 7.1e7, 1.2e8
    k, slip = 20 * E * Ib / L, 0.004
    r = portal(H=H, L=L, E=E, col=_sec(6000.0, Ic), beam=_sec(5700.0, Ib), w=w, H_left=15e3, stiffness_factor=0.8,
               knee_k=k, knee_slip=slip)
    for m, ks in zip(r["beam_end_moments"], r["knee_springs"]):          # rotation = slip + M / (0.8 k)
        assert abs(m) / ks == pytest.approx(slip + abs(m) / (0.8 * k), rel=1e-8)
    rigid = portal(H=H, L=L, E=E, col=_sec(6000.0, Ic), beam=_sec(5700.0, Ib), w=w, H_left=15e3, stiffness_factor=0.8)
    assert abs(r["drift"]) > abs(rigid["drift"])
    pinned = portal(H=H, L=L, E=E, col=_sec(1e9, Ic), beam=_sec(1e9, Ib), w=w, second_order=False, knee_k=k,
                    knee_slip=10.0, n_beam=2)
    assert abs(pinned["beam_M_mid"]) == pytest.approx(w * L * L / 8, rel=2e-3)

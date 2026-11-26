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
    assert -lean_base == pytest.approx(144.0 * r["drift"] / 240.0, rel=1e-6)
    assert tau_b(1.0 * r["right"]["N"], 50 * 19.1) == 1.0  # alpha Pr / Pns = 0.076 (the example: 0.0760)
    assert r["right"]["N"] / 955 == pytest.approx(0.0760, abs=5e-4)


def test_second_order_drift_ratio():
    assert run(True)["drift"] / run(False)["drift"] == pytest.approx(1.60, rel=0.02)

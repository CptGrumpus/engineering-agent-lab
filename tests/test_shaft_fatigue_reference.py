"""Machine-elements study hand references: shoulder-fillet Kt fits, Neuber's constant, Marin factors, Goodman."""

import math

import pytest

from validation import shaft_fatigue as S

KPSI = 1 / S.KPSI_PER_MPA


def test_neuber_constant_against_the_shigley_solutions_manual():
    """Worked values in the 11th-edition chapter-6 solutions (sqrt(in)): bending 68 / 85 / 120 / 64 kpsi, torsion 68.

    The manual's torsion value at 64 kpsi (0.07800) disagrees with its own fit (0.07766) while the 68 kpsi value agrees
    to five digits: an arithmetic slip in the manual, so it is not used here.
    """
    for sut, ref in ((68, 0.09799), (85, 0.07690), (120, 0.04770), (64, 0.10373)):
        assert S.neuber_sqrt_a_mm(sut * KPSI) / S.SQRT_MM_PER_SQRT_IN == pytest.approx(ref, abs=1e-5)
    assert S.neuber_sqrt_a_mm(68 * KPSI, torsion=True) / S.SQRT_MM_PER_SQRT_IN == pytest.approx(0.07335, abs=1e-5)
    with pytest.raises(ValueError):
        S.neuber_sqrt_a_mm(300)


def test_notch_sensitivity_and_kf_worked_example():
    """Solutions manual 6-47: sqrt(a) 0.10373, r 0.1 in -> q 0.75; Kt 1.5 -> Kf 1.38."""
    q = S.notch_sensitivity(0.1, 0.10373)
    assert q == pytest.approx(0.75, abs=0.005)
    assert S.kf(1.5, q) == pytest.approx(1.38, abs=0.005)


def test_marin_factors_against_worked_values():
    """Manual 6-1 (b): ka = 3.04 (570)^-0.217 = 0.767, kb = 1.24 (25)^-0.107 = 0.879, Se = 192 MPa."""
    se = S.endurance_limit(570, 25)
    assert se["ka"] == pytest.approx(0.767, abs=5e-4)
    assert se["kb"] == pytest.approx(0.879, abs=5e-4)
    assert se["Se"] == pytest.approx(192, abs=0.5)
    assert S.endurance_limit(1500, 25)["Se_prime"] == 700.0
    assert S.endurance_limit(1000, 32, "shigley10")["ka"] / S.endurance_limit(1000, 32)["ka"] == pytest.approx(
        1.065, abs=1e-3)


def test_kt_fit_limits_and_trends():
    """Kt falls as the fillet grows, rises with the step; the two bending ranges meet at h/r = 2 within 0.2 %."""
    assert S.kt_bending(40, 32, 1.4) > S.kt_bending(40, 32, 1.6) > S.kt_bending(40, 32, 2.0) > 1
    assert S.kt_bending(48, 32, 1.6) > S.kt_bending(40, 32, 1.6)
    lo = S._kt((S.PILKEY_BENDING[0],), 40, 32, 2.0)
    hi = S._kt((S.PILKEY_BENDING[1],), 40, 32, 2.0)
    assert hi == pytest.approx(lo, rel=2e-3)
    assert S.kt_torsion(40, 32, 1.6) < S.kt_bending(40, 32, 1.6)
    with pytest.raises(ValueError):
        S.kt_torsion(40, 32, 0.5)   # h/r = 8, outside 0.25-4


def test_pilkey_and_roark_bending_fits_agree():
    """Two published fits of the same charts (Pilkey 2nd ed., Roark 8th ed.) within 2.5 % at h/r 0.5-2."""
    for r in (2.0, 3.0, 4.0, 8.0):
        assert S.kt_bending(40, 32, r, S.ROARK_BENDING_LOW) == pytest.approx(S.kt_bending(40, 32, r), rel=0.025)


def test_assessment_hand_check():
    """The combined-loading chain by hand at the nominal shaft (D 40, d 32, r 1.6; M 300, T 500; 42CrMo4)."""
    a = S.assess(40, 32, 1.6, 300, 500, 1000, 750)
    sa, tm = 32 * 300e3 / (math.pi * 32 ** 3), 16 * 500e3 / (math.pi * 32 ** 3)
    assert a["sigma_a_nom"] == pytest.approx(sa) and a["tau_m_nom"] == pytest.approx(tm)
    assert a["n_goodman"] == pytest.approx(1 / (a["Kf"] * sa / a["Se"] + math.sqrt(3) * a["Kfs"] * tm / 1000))
    assert (a["n_elliptic"] * a["sigma_a_vm"] / a["Se"]) ** 2 + (a["n_elliptic"] * a["sigma_m_vm"] / 750) ** 2 == \
        pytest.approx(1)
    assert a["n_yield"] == pytest.approx(750 / (1.5 * math.hypot(a["Kf"] * sa, math.sqrt(3) * a["Kfs"] * tm)))


def test_minimum_radius_is_where_the_safety_factor_crosses():
    r = S.minimum_radius(40, 32, 300, 500, 1000, 750, 2.0, 1.0, 4.0, key="n_yield")
    assert S.assess(40, 32, r, 300, 500, 1000, 750)["n_yield"] == pytest.approx(2.0, abs=1e-6)
    assert S.minimum_radius(40, 32, 300, 500, 1000, 750, 5.0, 1.0, 4.0) is None

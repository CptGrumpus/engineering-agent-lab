"""Study 12 hand references: Gent, Lindley, Hertz line contact, Parker's band, the tolerance stack."""

import math

import pytest

from validation import oring as O


def test_gent_against_the_published_table():
    """Wikipedia's Shore durometer table (Gent): 50 -> 2.456, 70 -> 5.520, 90 -> 20.844 MPa."""
    assert O.gent_youngs_modulus_MPa(50) == pytest.approx(2.456, abs=1e-3)
    assert O.gent_youngs_modulus_MPa(70) == pytest.approx(5.520, abs=1e-3)
    assert O.gent_youngs_modulus_MPa(90) == pytest.approx(20.844, abs=1e-3)
    with pytest.raises(ValueError):
        O.gent_youngs_modulus_MPa(30)


def test_lindley_scales_with_size_and_modulus():
    f = O.lindley_force_per_length_N_per_mm(3.53, 5.52, 0.2)
    assert f == pytest.approx(3.53 * 5.52 * (1.25 * 0.2 ** 1.5 + 50 * 0.2 ** 6))
    assert O.lindley_force_per_length_N_per_mm(7.06, 5.52, 0.2) == pytest.approx(2 * f)


def test_hertz_line_contact_consistency():
    """p0 = 2F/(pi b) and the mean pressure over 2b is F/(2b) = pi p0 / 4."""
    b, p0 = O.hertz_line(1.0, 1.765, 5.52)
    assert b == pytest.approx(math.sqrt(4 * 1.0 * 1.765 / (math.pi * 5.52 / 0.75)))
    assert 1.0 / (2 * b) == pytest.approx(math.pi * p0 / 4)


def test_parker_band_is_monotone_and_spans_the_hand_estimates():
    lo = [v[0] for _, v in sorted(O.PARKER_70A_0139_N_PER_MM.items())]
    hi = [v[1] for _, v in sorted(O.PARKER_70A_0139_N_PER_MM.items())]
    assert lo == sorted(lo) and hi == sorted(hi)
    for c, (a, b) in O.PARKER_70A_0139_N_PER_MM.items():   # Lindley at 70 Shore A falls inside Parker's band
        assert a < O.lindley_force_per_length_N_per_mm(3.53, O.gent_youngs_modulus_MPa(70), c / 100) < b


def test_stack_corners():
    s = O.stack(3.53, 0.10, 2.79, 0.05, 4.80, 0.05)
    assert s["squeeze_min"] == pytest.approx((3.43 - 2.84) / 3.43)
    assert s["squeeze_max"] == pytest.approx((3.63 - 2.74) / 3.63)
    assert s["fill_max"] == pytest.approx(math.pi * 3.63 ** 2 / 4 / (2.74 * 4.75))


def test_study_inputs_to_model():
    """Physical inputs -> squeeze, Gent modulus, ring and groove radii (ring against the outer wall)."""
    from studies.oring_seal import model_params
    p = {"cross_section_mm": 3.53, "ring_inner_diameter_mm": 50.0, "groove_depth_mm": 2.79, "groove_width_mm": 4.80,
         "groove_outer_diameter_mm": 57.06, "groove_walls": 1, "shore_a": 70.0, "bulk_to_shear": 1000.0,
         "contact_element_size_mm": 0.05, "far_element_size_mm": 0.2, "penalty_factor": 10.0}
    m = model_params(p)
    assert m["squeeze"] == pytest.approx((3.53 - 2.79) / 3.53)
    assert m["youngs_modulus_MPa"] == pytest.approx(O.gent_youngs_modulus_MPa(70))
    assert m["mean_radius_mm"] + 3.53 / 2 == pytest.approx(57.06 / 2)          # ring OD on the groove OD
    assert m["groove_inner_radius_mm"] == pytest.approx(57.06 / 2 - 4.80)
    assert "groove_inner_radius_mm" not in model_params(p | {"groove_walls": 0})

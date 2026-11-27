"""Study 25 part 2: the cover model's bolt pattern and plate reference."""
import math

import pytest

from models.fea import oring_cover as OC


def test_bolt_patterns_are_symmetric_about_both_axes():
    assert [round(math.degrees(a), 6) for a in OC.bolt_angles(4)] == [45.0]
    assert [round(math.degrees(a), 6) for a in OC.bolt_angles(6)] == [30.0, 90.0]
    assert [round(math.degrees(a), 6) for a in OC.bolt_angles(8)] == [22.5, 67.5]
    with pytest.raises(ValueError):
        OC.bolt_angles(5)


def test_mindlin_reduces_to_kirchhoff_for_a_thin_plate():
    p = {"cover_diameter_mm": 96.0, "cover_thickness_mm": 0.01, "youngs_modulus_MPa": 68900.0, "poisson_ratio": 0.33,
         "pressure_MPa": 1e-9}
    D = 68900.0 * 0.01 ** 3 / (12 * (1 - 0.33 ** 2))
    kirchhoff = 1e-9 * 48.0 ** 4 * (5.33) / (64 * D * 1.33)
    assert OC.mindlin_centre_deflection(p) == pytest.approx(kirchhoff, rel=1e-6)


def test_mindlin_shear_term_at_the_reference_thickness():
    p = {"cover_diameter_mm": 96.0, "cover_thickness_mm": 6.0, "youngs_modulus_MPa": 68900.0, "poisson_ratio": 0.33,
         "pressure_MPa": 0.3}
    D = 68900.0 * 6.0 ** 3 / (12 * (1 - 0.33 ** 2))
    kirchhoff = 0.3 * 48.0 ** 4 * 5.33 / (64 * D * 1.33)
    assert OC.mindlin_centre_deflection(p) / kirchhoff - 1 == pytest.approx(
        32 * 1.33 * 36 / (12 * 0.67 * (5 / 6) * 5.33 * 48 ** 2), rel=1e-9)

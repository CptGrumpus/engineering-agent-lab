"""Study 2 part 2: the 3D strap's layers, through-thickness integration and plane-stress lookup."""
import numpy as np
import pytest

from models.fea import strap_3d as S3
from studies.strap_3d import plane_stress_peak

P = {"thickness_mm": 4.0, "hole_element_size_mm": 0.267, "z_layers": 0, "hole_diameter_mm": 16.0}


def test_layers_refine_with_the_hole_mesh():
    assert S3.n_layers(P) == 7
    assert S3.n_layers(P | {"hole_element_size_mm": 0.4}) == 5
    assert S3.n_layers(P | {"hole_element_size_mm": 0.178}) == 11
    assert S3.n_layers(P | {"z_layers": 2}) == 2
    assert S3.n_layers(P | {"hole_element_size_mm": 2.0}) == 4


def test_layer_heights_grade_to_the_face():
    c = S3.layer_heights(4, 2.0)
    assert c[-1] == pytest.approx(1.0)
    steps = np.diff([0.0] + c)
    assert steps == pytest.approx([8 / 15, 4 / 15, 2 / 15, 1 / 15])


def test_through_mean_is_exact_for_a_quadratic_per_element():
    z = np.array([0.0, 0.25, 0.5, 1.0, 1.5, 1.75, 2.0])   # three elements, corner / mid-side / corner
    s = 3 + z * z
    assert S3.through_mean(z, s, 2.0) == pytest.approx(3 + 4 / 3, rel=1e-12)
    with pytest.raises(ValueError):
        S3.through_mean(z[:-1], s[:-1], 2.0)


def test_plane_stress_reference_by_hole_size():
    assert plane_stress_peak({"plane_stress_peak_MPa": 116.988, "hole_diameter_mm": 16.0}) == 116.988
    table = {"14": 110.473, "16": 116.988}
    assert plane_stress_peak({"plane_stress_peak_MPa": table, "hole_diameter_mm": 14.0}) == 110.473

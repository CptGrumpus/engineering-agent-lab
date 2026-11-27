"""Study 10 part 2: the 3D roller's layer grading and end profiles."""
import math

import numpy as np
import pytest

from models.fea import roller_3d as R3

P = {"roller_length_mm": 30.0, "plate_width_mm": 60.0, "end_layer_mm": 0.2, "layer_growth": 1.3,
     "far_element_size_mm": 4.0, "youngs_modulus_MPa": 210000.0, "poisson_ratio": 0.3, "line_load_N_per_mm": 500.0}


def test_graded_layers_fill_the_length_and_are_fine_at_the_end():
    hs = R3.graded(15.0, 0.2, 1.3, 2.0, fine_at_end=True)
    assert sum(hs) == pytest.approx(15.0, rel=1e-12)
    assert hs[-1] == pytest.approx(min(hs), rel=1e-12)
    assert all(isinstance(h, float) for h in hs)               # no numpy reprs in the .geo
    assert max(b / a for a, b in zip(hs[1:], hs[:-1])) <= 1.3 * 1.5   # growth bounded (the last layer absorbs the rest)


def test_roller_and_plate_layers():
    roller, beyond = R3.layers(P)
    assert sum(roller) == pytest.approx(15.0) and sum(beyond) == pytest.approx(15.0)
    assert roller[-1] == pytest.approx(beyond[0], rel=0.2)       # the two sides of the roller's end match


def test_edge_profile():
    p = P | {"profile": "edge", "edge_radius_mm": 1.0, "cap_um": 60.0}
    z = np.array([0.0, 13.9, 14.0, 14.3, 15.0])
    d = R3.drop_um(p, z)
    assert d[:3] == pytest.approx([0.0, 0.0, 0.0])
    assert d[3] == pytest.approx(1e3 * (1 - math.sqrt(1 - 0.09)))   # 46.1 um at 0.3 mm into the radius
    assert d[4] == 60.0                                              # capped


def test_log_profile_reaches_zm_at_the_end():
    p = P | {"profile": "log", "crown_A_um": 2.0, "crown_zm_um": 20.0, "cap_um": 60.0}
    d = R3.drop_um(p, np.array([0.0, 7.5, 15.0]))
    assert d[0] == 0.0
    assert d[2] == pytest.approx(20.0, rel=1e-9)
    assert 0 < d[1] < 1.0                                            # gentle in the middle


def test_lundberg_parameter():
    # 2 Q / (pi l E'), E' = E / (1 - nu^2): 2 x 500 / (pi x 230769) mm
    assert R3.lundberg_A_um(P) == pytest.approx(1e3 * 2 * 500 / (math.pi * 210000 / 0.91), rel=1e-12)

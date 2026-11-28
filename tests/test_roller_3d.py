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


def _step(F, mid, profile, zs):
    k = int(np.argmax(profile))
    keys = ("approach_mm", "q_mid_N_per_mm", "contact_integral_N", "tau_max_MPa")
    return {"F_top_N": -F, "F_bottom_N": F, "p_mid_MPa": mid, "p_peak_MPa": float(profile[k]),
            "p_peak_z_mm": float(zs[k]), "z_profile_mm": list(zs), "p_along_z_MPa": list(profile)} | dict.fromkeys(keys, 1.0)


# roller_fe_end p01 (end layer 0.05 mm), the bracketing pair at 0.98 / 1.02 of the approach, reduced to four layers
ZS = np.array([0.0, 7.0, 12.04, 14.628])
LO = _step(3652.9, 639.6, np.array([639.6, 637.0, 601.2, 466.3]), ZS)
HI_JUMP = _step(3831.1, 653.1, np.array([653.1, 650.0, 609.7, 692.0]), ZS)
HI_STEADY = _step(3831.1, 653.1, np.array([653.1, 650.0, 614.0, 480.0]), ZS)


def test_target_peak_comes_from_the_interpolated_profile_not_each_steps_maximum():
    from studies.roller_3d import interpolate_to_target

    t, j, w, bracketed, zs, pz = interpolate_to_target([LO, HI_JUMP], 3750.0)
    assert bracketed and j == 1 and w == pytest.approx((3750.0 - 3652.9) / (3831.1 - 3652.9))
    assert t["p_peak_MPa"] == pytest.approx(pz.max()) and t["p_peak_z_mm"] == 0.0
    assert t["p_peak_MPa"] == pytest.approx((1 - w) * 639.6 + w * 653.1)     # mid-length, not
    assert (1 - w) * LO["p_peak_MPa"] + w * HI_JUMP["p_peak_MPa"] > 660       # the blend of the two steps' maxima
    with pytest.raises(ValueError):
        interpolate_to_target([LO, _step(3831.1, 653.1, np.array([653.1, 650.0, 609.7]), ZS[:3])], 3750.0)


def test_end_consistency_flags_a_jumping_end_and_passes_a_steady_one():
    from studies.roller_3d import END_CONSISTENCY_TOL, end_consistency

    jump, r = end_consistency([LO, HI_JUMP], 1, 15.0)
    assert r == pytest.approx([601.2 / 639.6, 692.0 / 653.1]) and jump > 0.1 > END_CONSISTENCY_TOL
    steady, r = end_consistency([LO, HI_STEADY], 1, 15.0)
    assert r[1] == pytest.approx(614.0 / 653.1) and steady < 0.005 < END_CONSISTENCY_TOL

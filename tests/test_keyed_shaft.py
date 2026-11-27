"""Study 26 part 2 (keyed shaft): CAD volumes by hand, submodel boxes, deck formatting (no CalculiX)."""

import math

import numpy as np
import pytest

from models.fea import keyed_shaft as ks
from studies.keyed_shaft import boxes, safety

P = {"D_mm": 45.0, "d_mm": 36.0, "fillet_radius_mm": 1.8, "small_length_mm": 90.0, "large_length_mm": 60.0,
     "key_width_mm": 10.0, "key_depth_mm": 5.0, "key_corner_radius_mm": 0.4, "key_gap_mm": 2.0, "key_length_mm": 40.0}


def test_g14_fits_calculix_fields():
    for v in (-2.751132655021138e-13, 1.2371056560109001e-15, -123456.78901234567, 0.1 + 0.2):
        assert len(ks.g14(v)) <= 20
        assert float(ks.g14(v)) == pytest.approx(v, rel=1e-13)


def test_cad_volumes_by_hand(tmp_path):
    pytest.importorskip("cadquery")
    keyless = ks.build_cad(dict(P, key_width_mm=0.0), tmp_path / "a.step")["volume_mm3"]   # half model
    R, Rl, rf = 18.0, 22.5, 1.8
    cyl = math.pi * R ** 2 * 90 + math.pi * Rl ** 2 * 60
    # fillet: the spandrel between the corner square and the quarter arc, area rf^2 (1 - pi/4), centroid
    # rf (10 - 3 pi) / (3 (4 - pi)) from its corner at radius R (Pappus)
    fillet = rf ** 2 * (1 - math.pi / 4) * 2 * math.pi * (R + rf * (10 - 3 * math.pi) / (3 * (4 - math.pi)))
    assert keyless == pytest.approx((cyl + fillet) / 2, rel=1e-6)
    keyed = ks.build_cad(P, tmp_path / "b.step")["volume_mm3"]
    # keyway: stadium area (L - B) B + pi B^2 / 4 = 378.5 mm^2 times the depth under the circle (5.0 at the centre,
    # 4.29 at the sides, about 4.77 on average), less the corner fillets: about 1805 mm^3 for the whole shaft
    removed = 2 * (keyless - keyed)
    assert 1790 < removed < 1810


def test_boxes_clear_the_keyway():
    g = ks.dims(P)
    b = boxes(ks, P)
    assert set(b) == {"fillet_a", "fillet_b", "near", "far", "middle"}
    x0, x1, y0, y1, z0, z1 = b["near"]
    assert x0 == pytest.approx(g["R"] - g["t1"] - 3.0) and y1 == pytest.approx(g["B"] / 2 + 3.0)
    assert z0 < g["z_k1"] - g["B"] / 2 and z1 > g["zs"]
    assert x1 > g["D"] / 2                            # not a cut
    for name in ("fillet_a", "fillet_b"):             # together the whole half ring, 3 mm either side of the fillet
        x0, x1, y0, y1, z0, z1 = b[name]
        assert y1 > g["D"] / 2 and z0 == pytest.approx(g["zc"] - 3.0) and z1 == pytest.approx(g["zs"] + 3.0)
    assert b["fillet_a"][0] == b["fillet_b"][1] == 0.0
    assert b["fillet_a"][1] > g["D"] / 2 and b["fillet_b"][0] < -g["D"] / 2


def test_driven_clear_skips_cut_faces_only():
    box = (0.0, 30.0, 0.0, 30.0, 10.0, 20.0)
    X = np.array([[0.5, 5, 15], [5, 5, 15], [5, 5, 10.8], [5, 5, 19.5], [5, 29.5, 15], [5, 0.0, 15]])
    assert ks.driven_clear(X, box, 1.0).tolist() == [False, True, False, False, False, True]   # y = 0: symmetry
    assert ks.driven_clear(X, None, 1.0).all() and ks.driven_clear(X, box, 0.0).all()


def test_fillet_peak_is_the_max_over_fillet_boxes():
    from studies.keyed_shaft import fillet_peak
    pk = {"fillet_a/torsion": {"fillet": {"k": 1.6}}, "fillet_b/torsion": {"fillet": {"k": 1.7}},
          "near/torsion": {"fillet": {"k": 9.0}}, "fillet_b/bending": {"fillet": {"k": 2.1}}}
    assert fillet_peak(pk, "torsion")["k"] == 1.7 and fillet_peak(pk, "bending")["k"] == 2.1


def test_safety_reproduces_part1_at_the_fillet():
    p = dict(P, fillet_radius_mm=1.6, bending_moment_Nm=300.0, torque_Nm=500.0, ultimate_MPa=1000.0, yield_MPa=750.0,
             overload_factor=1.5)
    s = safety(p, {"kt_fillet_bending": 2.2246154438973256, "kt_fillet_torsion": 1.5923779246662075})
    assert s["fatigue_safety"] == pytest.approx(1.6179705406171383, rel=1e-9)   # part 1, p03_d36
    assert s["static_safety"] == pytest.approx(2.518655464778272, rel=1e-9)

"""Study 26 part 2 (keyed shaft): CAD volumes by hand, submodel boxes, deck formatting (no CalculiX)."""

import math

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
    assert set(b) == {"near", "far", "middle"}
    x0, x1, y0, y1, z0, z1 = b["near"]
    assert x0 == pytest.approx(g["R"] - g["t1"] - 3.0) and y1 == pytest.approx(g["B"] / 2 + 3.0)
    assert z0 < g["z_k1"] - g["B"] / 2 and z1 > g["zs"]
    assert x1 > g["D"] / 2                            # not a cut


def test_safety_reproduces_part1_at_the_fillet():
    p = dict(P, fillet_radius_mm=1.6, bending_moment_Nm=300.0, torque_Nm=500.0, ultimate_MPa=1000.0, yield_MPa=750.0,
             overload_factor=1.5)
    s = safety(p, {"kt_fillet_bending": 2.2246154438973256, "kt_fillet_torsion": 1.5923779246662075})
    assert s["fatigue_safety"] == pytest.approx(1.6179705406171383, rel=1e-9)   # part 1, p03_d36
    assert s["static_safety"] == pytest.approx(2.518655464778272, rel=1e-9)

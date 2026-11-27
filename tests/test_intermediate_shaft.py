"""Study 26: the detailed intermediate shaft (models/cad/intermediate_shaft.py) against hand volumes and the study's
own keyed half model."""

import pytest

pytest.importorskip("cadquery")

from models.cad import intermediate_shaft as m  # noqa: E402
from models.fea import keyed_shaft as ks  # noqa: E402


def _half_keyway(tmp_path, d, D, B, t1, rk, L, name):
    """Volume one keyway removes, from the study's half model (x2), on a plain step of the same seat diameter."""
    p = {"D_mm": D, "d_mm": d, "fillet_radius_mm": 1.0, "small_length_mm": 90.0, "large_length_mm": 20.0,
         "key_width_mm": B, "key_depth_mm": t1, "key_corner_radius_mm": rk, "key_gap_mm": 2.0, "key_length_mm": L}
    plain = ks.build_cad(dict(p, key_width_mm=0.0), tmp_path / f"{name}0.step")["volume_mm3"]
    return 2 * (plain - ks.build_cad(p, tmp_path / f"{name}1.step")["volume_mm3"])


@pytest.mark.parametrize("design", list(m.DESIGNS))
def test_body_matches_hand_volume(design):
    assert m.build(design, with_keyways=False).val().Volume() == pytest.approx(m.hand_volume(design), rel=1e-9)


@pytest.mark.parametrize("design", list(m.DESIGNS))
def test_keyways_match_the_study_model(design, tmp_path):
    s = m.DESIGNS[design]
    removed = m.build(design, with_keyways=False).val().Volume() - m.build(design).val().Volume()
    k_seat, k_pin = m.keyways(s)
    ref = (_half_keyway(tmp_path, s["seat"], s["collar"], *s["key_seat"], k_seat["z1"] - k_seat["z0"], "s")
           + _half_keyway(tmp_path, s["pinion"], s["collar"], *s["key_pinion"], k_pin["z1"] - k_pin["z0"], "p"))
    # 1.3-2.4e-5 apart: OpenCASCADE's volume integration on the blended corner faces, whole against half solid
    assert removed == pytest.approx(ref, rel=1e-4)


def test_the_analysed_region_is_the_study_geometry():
    s = m.DESIGNS["d36"]
    k = m.keyways(s)[0]
    assert (s["seat"], s["collar"]) == (36.0, 45.0) and s["key_seat"] == (10.0, 5.0, 0.4)
    assert k["z1"] == pytest.approx(m.Z_SHOULDER - s["fillet"] - 2.0) and k["z1"] - k["z0"] == 40.0
    assert all(z1 <= m.Z_SEAT or z0 >= m.Z_PINION_END for z0, z1 in m.grooves(s))   # grooves on the journals

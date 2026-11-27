"""Study 28 part 2: the knee's solid model (models/fea/moment_connection.py) against hand volumes and AISC areas."""
import pytest

from models.fea import moment_connection as mc
from validation import aisc360

IN = 25.4
P = {"column_shape": "W10X33", "beam_shape": "W14X30", "youngs_modulus_MPa": 200000.0, "poisson_ratio": 0.3,
     "plate_thickness_mm": 0.5 * IN, "plate_width_mm": 6.0 * IN, "plate_length_mm": 6.5 * IN, "setback_mm": 0.5 * IN,
     "tab_width_mm": 3.5 * IN, "tab_height_mm": 9.0 * IN, "tab_thickness_mm": 0.375 * IN,
     "continuity_plate_thickness_mm": 0.5 * IN, "column_length_mm": 800.0, "beam_length_mm": 1000.0,
     "tip_load_kN": 10.0}


@pytest.mark.parametrize("label", ["W10X33", "W14X30", "W18X50", "W14X99"])
def test_half_section_with_root_fillets_is_half_the_tabulated_area(label):
    s = mc.section_mm(aisc360.shape(label))
    assert 2 * mc.half_area(s) == pytest.approx(s["A"], rel=0.005)     # the database rounds A to 3 figures


def test_knee_solid_matches_hand_volume(tmp_path):
    pytest.importorskip("cadquery")
    cad = mc.build_cad(P, tmp_path / "knee.step")
    assert cad["volume_mm3"] == pytest.approx(cad["hand_volume_mm3"], rel=1e-9)
    no_cp = mc.build_cad(dict(P, continuity_plate_thickness_mm=0.0), tmp_path / "knee0.step")
    assert no_cp["volume_mm3"] == pytest.approx(no_cp["hand_volume_mm3"], rel=1e-9)


def test_centreline_rotations_by_hand():
    g = mc.dims(P)
    E, Pn, a = 200000.0, 10e3, g["x_tip"]
    r = mc.centreline_rotations(P, 600.0, -700.0)
    assert r["beam"] == pytest.approx(Pn * (a * 600 - 600 ** 2 / 2) / (E * g["beam"]["Ix_model"]), rel=1e-12)
    assert r["M_joint_Nmm"] == pytest.approx(Pn * a)


def test_modelled_ix_is_close_to_the_tabulated():
    """The solid's section (root fillets from kdes) is 0.3-0.8 % less stiff than the rolled profile's tabulated Ix."""
    for label, rel in (("W14X30", 0.0081), ("W10X33", 0.0030)):
        s = mc.section_mm(aisc360.shape(label))
        assert 1 - s["Ix_model"] / s["Ix"] == pytest.approx(rel, abs=0.0005)

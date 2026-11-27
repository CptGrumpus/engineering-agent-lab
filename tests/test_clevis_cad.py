"""Study 12: the optimised clevis as a deliverable (models/cad/clevis.py) against the analysed solid."""
import pytest

pytest.importorskip("cadquery")

from models.cad import clevis as CL  # noqa: E402


def volume(shape) -> float:
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps

    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape.wrapped, g, 1e-9)
    return g.Mass()


def test_deliverable_is_the_analysed_solid_less_the_mounting_holes():
    va = volume(CL.analysed_solid("D").val())
    vd = volume(CL.build("D")["clevis"].val())
    assert vd == pytest.approx(va - CL.hole_volume("D"), rel=1e-9)


def test_analysed_mass_is_the_studys():
    # 371.94 g recorded by the study (clevis_confirm_r2b); the solid's own volume gives 371.99 g (1.3e-4)
    assert volume(CL.analysed_solid("D").val()) * 2.7e-3 == pytest.approx(371.94, rel=5e-4)


def test_mounting_holes_clear_the_lug_and_gussets():
    s = CL.DESIGNS["D"]
    lg = s["gusset_aspect"] * s["gusset_height_mm"] + s["lug_thickness_mm"] / 2
    for (x, y), d in [(xy, s["bolt_d"]) for xy in s["bolt_holes"]] + [(xy, s["dowel_d"]) for xy in s["dowel_holes"]]:
        assert abs(x) - d / 2 > s["lug_radius_mm"] + s["fillet_radius_mm"]          # clear of the lug and its fillet
        assert abs(y) - d / 2 > lg or abs(x) - d / 2 > s["gusset_thickness_mm"] / 2 + s["fillet_radius_mm"]

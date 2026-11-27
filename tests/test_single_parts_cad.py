"""Studies 2/3/14 and 13: the strap and the strut as deliverable parts, against hand volumes and the studies'
geometry and end conditions."""
import pytest

pytest.importorskip("cadquery")

from models.cad import strap as ST  # noqa: E402
from models.cad import strut as SU  # noqa: E402


def volume(w) -> float:
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps

    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(w.val().wrapped, g, 1e-9)
    return g.Mass()


@pytest.mark.parametrize("mod,design", [(ST, "d16"), (ST, "d14"), (SU, "l587")])
def test_hand_volumes(mod, design):
    parts, hv = mod.build(design), mod.hand_volumes(design)
    for k, w in parts.items():
        assert volume(w) == pytest.approx(hv[k], rel=1e-9), (design, k)


def test_strap_is_the_analysed_strap():
    s = ST.DESIGNS["d16"]
    assert (s["L"], s["W"], s["t"], s["hole_d"]) == (160, 40, 4, 16)
    assert s["L"] / 2 - s["pin_from_end"] - s["pin_d"] / 2 > 3 * s["hole_d"]     # pin holes far from the cable hole


def test_strut_is_pinned_about_its_weak_axis():
    w = SU.build("l587")["strut"].val()
    bb = w.BoundingBox()
    assert bb.zlen == pytest.approx(16.0)        # the thickness (weak axis) along z
    assert bb.ylen == pytest.approx(25.0)        # the pins run across the width (y)
    # a pin hole along y: a line along y through the first pin's centre misses the material
    import cadquery as cq
    probe = cq.Workplane("XZ").circle(1.0).extrude(30, both=True).val()
    assert w.intersect(probe).Volume() == pytest.approx(0.0, abs=1e-9)
    assert SU.DESIGNS["l587"]["L"] == 587.0

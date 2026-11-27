"""Studies 11 and 15: the detailed cold plate (models/cad/cold_plate.py) against hand volumes and clearances."""
import pytest

pytest.importorskip("cadquery")

from models.cad import cold_plate as CP  # noqa: E402


def volume(w) -> float:
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps

    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(w.val().wrapped, g, 1e-9)
    return g.Mass()


@pytest.fixture(scope="module")
def parts():
    return CP.build("study11")


def test_every_part_matches_its_hand_volume(parts):
    hv = CP.hand_volumes("study11")
    assert set(parts) == set(hv)
    for k, w in parts.items():
        assert volume(w) == pytest.approx(hv[k], rel=1e-8), k


def test_no_part_overlaps_another(parts):
    names = list(parts)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            common = parts[a].intersect(parts[b]).vals()
            assert (common[0].Volume() if common else 0.0) < 1e-6, (a, b)


def test_the_analysed_passage():
    s = CP.DESIGNS["study11"]
    assert (s["pass_h"], s["pass_w"], s["pass_l"], s["cover_t"]) == (1.0, 20.0, 60.0, 3.0)
    g = CP.geometry(s)
    assert g["port_z"] + s["port_d"] / 2 < g["z_top"]                # the port stays under the top face
    assert g["port_z"] - s["port_d"] / 2 >= s["pass_h"] - s["well_h"]  # and inside the well's depth

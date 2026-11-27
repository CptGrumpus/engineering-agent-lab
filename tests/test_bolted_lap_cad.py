"""Study 16: the detailed bolted lap joint (models/cad/bolted_lap.py) against hand volumes and clearances."""
import pytest

pytest.importorskip("cadquery")

from models.cad import bolted_lap as BL  # noqa: E402


def volume(w) -> float:
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps

    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(w.val().wrapped, g, 1e-9)
    return g.Mass()


@pytest.fixture(scope="module")
def parts():
    return BL.build("m8")


def test_every_part_matches_its_hand_volume(parts):
    hv = BL.hand_volumes("m8")
    assert set(parts) == set(hv)
    for k, w in parts.items():
        assert volume(w) == pytest.approx(hv[k], rel=1e-9), k


def test_no_part_overlaps_another(parts):
    names = list(parts)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            common = parts[a].intersect(parts[b]).vals()
            assert (common[0].Volume() if common else 0.0) < 1e-6, (a, b)


def test_the_studys_grip_and_bolt():
    p = BL.DESIGNS["m8"]
    assert 2 * p["t"] == 12.0                                   # the study's clamp length (shank 8 + free thread 4)
    assert p["bolt_l"] - 2 * p["t"] - p["nut_m"] > 4 * 1.25     # at least four M8 threads protrude
    assert p["hole_d"] - p["d"] == 1.0                           # the study's 9 mm clearance hole

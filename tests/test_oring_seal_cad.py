"""Study 25: the detailed face-seal assembly (models/cad/oring_cover.py) against hand volumes, its intended overlaps
(the O-ring's squeeze, the screws' thread engagement) and clearances."""
import math

import pytest

pytest.importorskip("cadquery")

from models.cad import oring_cover as OC  # noqa: E402


def volume(w) -> float:
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps

    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(w.val().wrapped, g, 1e-9)
    return g.Mass()


def overlap(a, b) -> float:
    common = a.intersect(b).vals()
    return common[0].Volume() if common else 0.0


@pytest.fixture(scope="module")
def parts():
    return OC.build("nominal")


def test_every_part_matches_its_hand_volume(parts):
    hv = OC.hand_volumes("nominal")
    assert set(parts) == set(hv)
    for k, w in parts.items():
        assert volume(w) == pytest.approx(hv[k], rel=1e-9), k


def test_the_oring_overlaps_the_cover_by_its_squeeze(parts):
    assert overlap(parts["oring"], parts["cover"]) == pytest.approx(OC.squeeze_overlap_volume("nominal"), rel=1e-6)
    s = OC.DESIGNS["nominal"]
    assert 100 * (s["cs"] - s["groove_h"]) / s["cs"] == pytest.approx(20.96, abs=0.01)   # part 1's nominal squeeze


def test_screws_engage_the_flange_by_the_thread_annulus(parts):
    s = OC.DESIGNS["nominal"]
    engaged = s["shank_l"] - s["cover_t"] - s["washer_t"]
    annulus = math.pi / 4 * (s["shank_d"] ** 2 - s["tap_d"] ** 2) * engaged
    for k in range(4):
        assert overlap(parts[f"screw_{k}"], parts["flange"]) == pytest.approx(annulus, rel=1e-6)


def test_everything_else_is_clear(parts):
    intended = {("oring", "cover")} | {(f"screw_{k}", "flange") for k in range(4)}
    names = list(parts)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if (a, b) in intended or (b, a) in intended:
                continue
            assert overlap(parts[a], parts[b]) < 1e-6, (a, b)

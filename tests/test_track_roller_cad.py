"""Study 10 part 2: the detailed track roller (models/cad/track_roller.py) against hand volumes and clearances."""
import math

import pytest

pytest.importorskip("cadquery")

from models.cad import track_roller as TR  # noqa: E402


def volume(w) -> float:
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps

    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(w.val().wrapped, g, 1e-9)
    return g.Mass()


@pytest.fixture(scope="module")
def parts():
    return TR.build("crowned")


def test_every_part_matches_its_hand_volume(parts):
    hv = TR.hand_volumes("crowned")
    assert set(parts) == set(hv)
    for k, w in parts.items():
        # the crowned ring's profile is a spline through 61 points of the drop: 1e-6 against the exact integral
        assert volume(w) == pytest.approx(hv[k], rel=1e-5 if k == "outer_ring" else 1e-9), k


def test_no_part_overlaps_another(parts):
    names = list(parts)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            common = parts[a].intersect(parts[b]).vals()
            assert (common[0].Volume() if common else 0.0) < 1e-6, (a, b)


def test_the_crown_is_part_2s_design():
    z, r, A = TR.crown_profile(TR.DESIGNS["crowned"])
    assert A == pytest.approx(1.3 * 1.3793428, rel=1e-6)                 # 1.3 x Lundberg's A, micron
    assert 1e3 * (50.0 - r[0]) == pytest.approx(3.674, abs=1e-3)          # the drop 1 mm from the end
    assert r[len(r) // 2] == pytest.approx(50.0, abs=1e-12)               # none at mid-length


def test_needles_fit_between_the_rings():
    s = TR.DESIGNS["crowned"]
    assert s["pitch_d"] / 2 - s["needle_d"] / 2 == pytest.approx(s["d_ir_out"] / 2)
    assert s["pitch_d"] / 2 + s["needle_d"] / 2 == pytest.approx(s["d_or_in"] / 2)
    assert math.pi * s["pitch_d"] / s["n_needles"] > s["needle_d"]

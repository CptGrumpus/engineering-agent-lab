"""Study 23 part 2: the detailed rotor assembly (models/cad/fan_rotor.py) against hand volumes and clearances."""
import math

import pytest

pytest.importorskip("cadquery")

from models.cad import fan_rotor as fr  # noqa: E402


@pytest.fixture(scope="module")
def parts():
    return fr.build("d65")


def test_every_part_matches_its_hand_volume(parts):
    hv = fr.hand_volumes("d65")
    for name, w in parts.items():
        # the shaft's keyway by a 4000-strip quadrature of its curved top: 3.5e-8
        assert w.val().Volume() == pytest.approx(hv[name], rel=1e-6), name


def test_keyway_quadrature_against_a_closed_form():
    # a keyway as deep as the shaft's radius (t1 = R) over a straight slot is half a cylinder segment's area times L
    R, b, L = 30.0, 10.0, 1e6                       # L >> b: the round ends' share is negligible (b / L)
    seg = b * math.sqrt(R * R - b * b / 4) / 2 + R * R * math.asin(b / (2 * R))   # area of |y| < b/2 inside the circle
    assert fr.keyway_volume(R, b, L, R) == pytest.approx(seg * L, rel=1e-5)


def test_no_part_overlaps_its_neighbours(parts):
    for a, b in (("shaft", "key"), ("hub", "key"), ("hub", "shaft"), ("disc", "hub"), ("weld_front", "disc"),
                 ("weld_back", "hub")):
        common = parts[a].intersect(parts[b]).vals()
        assert (common[0].Volume() if common else 0.0) < 1e-6, (a, b)


def test_the_analysed_geometry():
    s = fr.DESIGNS["d65"]
    assert (s["L"], s["d"], s["D"], s["w"], s["dh"], s["lh"], s["dj"], s["lj"]) == (1000, 65, 400, 25, 130, 100, 55, 50)

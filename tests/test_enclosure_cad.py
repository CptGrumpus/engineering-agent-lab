"""Study 27: the detailed enclosure (models/cad/enclosure.py) against hand volumes, its thread engagements and
clearances."""
import pytest

pytest.importorskip("cadquery")

from models.cad import enclosure as EN  # noqa: E402


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
    return EN.build("as_drawn")


def test_every_part_matches_its_hand_volume(parts):
    hv = EN.hand_volumes("as_drawn")
    assert set(parts) == set(hv)
    for k, w in parts.items():
        assert volume(w) == pytest.approx(hv[k], rel=1e-8), k


def test_only_the_threads_overlap(parts):
    th = EN.thread_overlaps("as_drawn")
    intended = {}
    for k in range(4):
        intended[("housing", f"cap_screw_front_{k}")] = th["cap"]
        intended[("housing", f"cap_screw_back_{k}")] = th["cap"]
        intended[(f"standoff_{k}", f"board_screw_{k}")] = th["board"]
    names = list(parts)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            v = overlap(parts[a], parts[b])
            want = intended.get((a, b), intended.get((b, a), 0.0))
            assert v == pytest.approx(want, abs=1e-6), (a, b)


def test_the_study_geometry():
    s = EN.DESIGNS["as_drawn"]
    assert (s["W"], s["H"], s["D"], s["t"], s["board_l"], s["board_t"], s["u1_l"]) == (150, 60, 200, 2, 100, 2, 20)
    # C1 sits 5-15 mm from the board's left end, as the client's footprint says
    assert s["c1_x_from_left"] - s["c1_d"] / 2 == 5.0 and s["c1_x_from_left"] + s["c1_d"] / 2 == 15.0

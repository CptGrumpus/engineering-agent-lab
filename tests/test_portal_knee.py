"""Study 28 part 2: the detailed knee assembly (models/cad/portal_knee.py) against hand volumes, clearances and the
analysed geometry."""
import pytest

pytest.importorskip("cadquery")

from models.cad import portal_knee as pk  # noqa: E402


@pytest.fixture(scope="module", params=list(pk.DESIGNS))
def built(request):
    return request.param, pk.build(request.param), pk.hand_volumes(request.param)


def _kind(name):
    for key, kind in (("weld_top_plate", "weld_plate"), ("weld_bottom_plate", "weld_plate"), ("weld_tab", "weld_tab"),
                      ("_head", "head"), ("_nut", "nut"), ("_washer", "washer"), ("continuity", "continuity_plate"),
                      ("_plate", "plate")):
        if key in name:
            return kind
    if name.endswith("_shank"):
        return "shank_web" if name.startswith("bolt_w") else "shank_flange"
    return name


def test_every_part_matches_its_hand_volume(built):
    _, parts, hv = built
    for name, w in parts.items():
        assert w.val().Volume() == pytest.approx(hv[_kind(name)], rel=1e-9), name


def test_bolt_count_and_the_analysed_plate_length(built):
    design, parts, _ = built
    n = pk.DESIGNS[design]["n"]
    assert sum(1 for k in parts if k.endswith("_shank")) == 2 * 2 * n + 3          # two flanges x two lines + web
    L = pk.layout(design)
    assert L["Lp"] == pytest.approx({"slip_critical6": 241.3, "bearing4": 165.1}[design])   # as cases/steel_knee_*


def test_no_part_overlaps_its_neighbours(built):
    _, parts, _ = built
    pairs = [("top_plate", "bolt_t0_shank"), ("beam", "bolt_t0_shank"), ("beam", "bolt_b1_shank"),
             ("beam", "bolt_t0_nut"), ("beam", "bolt_w1_shank"), ("shear_tab", "bolt_w1_shank"), ("column", "top_plate"),
             ("column", "bottom_plate"), ("shear_tab", "beam"), ("weld_tab_inner", "beam"),
             ("weld_top_plate_lower", "beam"), ("continuity_plate_front", "column"), ("bolt_t0_nut", "bolt_t0_shank")]
    for a, b in pairs:
        common = parts[a].intersect(parts[b]).vals()
        assert (common[0].Volume() if common else 0.0) < 1e-6, (a, b)

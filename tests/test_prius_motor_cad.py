"""Study 20 (study 7 in the repo): the detailed motor CAD (models/cad/prius_motor.py) against the analysed section, the
client's drawing, hand areas and volumes, and the bill of materials."""
import json
import math
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("cadquery")

from models.cad import prius_motor as pm  # noqa: E402

D, SEC = pm.DESIGNS["rev5"], pm.section()
DRAW = json.loads((Path(__file__).resolve().parents[1] / "validation/motor_ornl/drawing_stator/drawing_stator.json")
                  .read_text(encoding="utf-8"))
R = SEC["stator_Rext"]


@pytest.fixture(scope="module")
def parts():
    return pm.build("rev5")


def test_section_is_the_client_geometry():
    assert R == pytest.approx(10.600 / 2 * 25.4, abs=1e-9)                    # drawing: OD 10.600 in
    assert SEC["stator_Rint"] == pytest.approx(6.375 / 2 * 25.4, abs=1e-9)    # bore 6.375 in
    assert SEC["rotor_Rint"] == pytest.approx(4.356 / 2 * 25.4, abs=1e-3)     # rotor bore 4.356 in
    assert (SEC["slots"], SEC["poles"]) == (48, 8)
    for loop in SEC["pole_magnets"]:                                         # BOM: 18.9 x 6.5 mm
        assert abs(pm.loop_area([pm._from_json(e) for e in loop])) == pytest.approx(18.9 * 6.5, rel=1e-9)


def test_feature_sizes_match_the_drawing_measurements():
    ears = DRAW["ears"]
    assert np.mean([e["hole_centre_radius_mm"] for e in ears]) == pytest.approx(D["ear_hole_r"], abs=0.05)
    assert np.mean([e["tab_end_radius_about_hole_mm"] for e in ears]) == pytest.approx(D["ear_end_r"], abs=0.02)
    for e in ears:                                                           # the dimensioned hole, measured
        assert e["hole_diameter_mm"] == pytest.approx(D["ear_hole_d"], abs=0.06)
    # the drawing's features sit 3.75 deg before the model's (its slots at 7.5 k, the model's at 3.75 + 7.5 k)
    for e in ears:
        assert min(abs((e["hole_angle_deg"] + 3.75 - a + 180) % 360 - 180) for a in D["ears_deg"]) < 0.2
    clean = [n for n in DRAW["notches"] if n["found"] and n["depth_mm"] < 2.6]   # wider windows hold dimension lines
    assert len(clean) >= 5
    model = D["large_notches_deg"] + D["small_notches_deg"]
    for n in clean:
        assert min(abs((n["centre_deg"] + 3.75 - a + 180) % 360 - 180) for a in model) < 0.2
        w, d = (D["notch_large"][:2] if n["width_mm"] > 9 else D["notch_small"])
        assert n["width_mm"] == pytest.approx(w, abs=0.5) and n["depth_mm"] == pytest.approx(d, abs=0.15)
    keys = DRAW["rotor"]["keys"]
    assert len(keys) == len(D["keys_deg"])
    for k in keys:
        assert min(abs((k["centre_deg"] - a + 180) % 360 - 180) for a in D["keys_deg"]) < 0.2
        assert k["width_mm"] == pytest.approx(D["key_w"], abs=0.05)
        assert k["top_radius_mm"] == pytest.approx(D["key_top_r"], abs=0.1)


def test_the_ear_reproduces_the_drawn_outline():
    g = pm.ear_geometry(D, R)
    measured_tips = [e["tab_tip_radius_mm"] for e in DRAW["ears"][:2]]     # the third window holds a dimension line
    assert all(abs(g["tip_radius"] - t) < 0.3 for t in measured_tips)
    assert R - (math.hypot(*g["C"]) - D["relief_r"]) == pytest.approx(D["relief_depth"], abs=1e-9)
    # relief tangent to the flank: its centre is relief_r from the flank line
    al = math.radians(D["ear_flank_deg"])
    n = (math.sin(al), math.cos(al))
    dist = (g["C"][0] - D["ear_hole_r"]) * n[0] + g["C"][1] * n[1]
    assert dist == pytest.approx(D["ear_end_r"] + D["relief_r"], abs=1e-9)
    assert 19.5 < g["A"][1] < 21.0                                          # the drawn corner at about 20-20.5 mm


def _closed_with_od(edges, a0, a1):
    """A feature's edges closed by the outer circle from its end back to its start: the area it adds (+) or cuts (-)."""
    return edges + [pm._arc_through((0.0, 0.0), R, math.radians(a1), math.radians(a0))]


def test_notch_areas_against_closed_forms():
    def strip(w, d):   # area inside the circle over |y| <= w / 2 and outside the chord line x = R - d
        h = w / 2
        return h * math.sqrt(R * R - h * h) + R * R * math.asin(h / R) - w * (R - d)
    w, d = D["notch_small"]
    e, a0, a1 = pm.notch_edges(D, "small", 37.5, R)
    assert abs(pm.loop_area(_closed_with_od(e, a0, a1))) == pytest.approx(strip(w, d), rel=1e-10)
    w, d, r = D["notch_large"]
    e, a0, a1 = pm.notch_edges(D, "large", 7.5, R)
    hand = strip(w, d) - 2 * r * r * (1 - math.pi / 4)          # the two rounded floor corners keep their spandrels
    assert abs(pm.loop_area(_closed_with_od(e, a0, a1))) == pytest.approx(hand, rel=1e-10)


def test_ear_area_against_a_grid_count():
    """Independent of the edges: count a 0.01 mm grid against the ear's definition (disc or tab, less the reliefs)."""
    e, a0, a1 = pm.ear_edges(D, 0.0, R)
    cad = pm.loop_area(_closed_with_od(e, a0, a1))               # tab outside the circle less the reliefs inside it
    g = pm.ear_geometry(D, R)
    rh, Re, Rr = D["ear_hole_r"], D["ear_end_r"], D["relief_r"]
    al = math.radians(D["ear_flank_deg"])
    h = 0.01
    x = np.arange(R - 3.0, rh + Re + 0.5, h) + h / 2
    y = np.arange(-23.0, 23.0, h) + h / 2
    X, Y = np.meshgrid(x, y, indexing="ij")
    disc = X * X + Y * Y <= R * R
    # tab: inside both flank lines and, beyond the tangent points, inside the end circle
    inside_flanks = (X - rh) * math.sin(al) + np.abs(Y) * math.cos(al) <= Re
    beyond = (X - rh) * math.cos(al) - np.abs(Y) * math.sin(al) > 0          # past the tangent line through the centre
    tab = inside_flanks & (~beyond | ((X - rh) ** 2 + Y ** 2 <= Re * Re))
    relief = ((X - g["C"][0]) ** 2 + (np.abs(Y) - g["C"][1]) ** 2) < Rr * Rr
    material = (disc | tab) & ~relief
    grid = (material.sum() - disc.sum()) * h * h
    assert grid == pytest.approx(cad, rel=3e-3)


def test_stator_volume_is_the_exact_section_times_the_stack(parts):
    a = pm.stator_section_area(D, SEC)
    assert parts["stator"].isValid()
    assert parts["stator"].Volume() == pytest.approx(a["lamination"] * D["stator_stack"], rel=1e-9)


def test_rotor_volume_is_the_annulus_plus_keys_less_the_pockets(parts):
    assert parts["rotor"].isValid()
    assert abs(pm.loop_area(pm.rotor_inner_edges(D, SEC))) == pytest.approx(
        math.pi * SEC["rotor_Rint"] ** 2 - 2 * pm.key_area(D, SEC), rel=1e-12)
    voids, mags = pm.pole_loops(SEC, 0)
    pocket = sum(abs(pm.loop_area(lp)) for lp in voids + mags)            # equal to the union: the regions tile
    area = (math.pi * (SEC["rotor_Rext"] ** 2 - SEC["rotor_Rint"] ** 2) + 2 * pm.key_area(D, SEC)
            - SEC["poles"] * pocket)
    assert parts["rotor"].Volume() == pytest.approx(area * D["rotor_stack"], rel=1e-9)


def test_magnets_windings_and_end_rings(parts):
    assert len(parts["magnets"]) == 16 and len(parts["windings"]) == 48
    for m in parts["magnets"][:2]:
        assert m.Volume() == pytest.approx(18.9 * 6.5 * D["magnet_length"], rel=1e-9)
        common = parts["rotor"].intersect(m)
        assert common.Volume() < 1e-6                                       # in its pocket, not in the steel
    zone = abs(pm.loop_area([pm._from_json(e) for e in SEC["winding_edges"]]))
    assert parts["windings"][0].Volume() == pytest.approx(zone * D["stator_stack"], rel=1e-9)
    assert parts["stator"].intersect(parts["windings"][0]).Volume() < 1e-6
    for ring in parts["end_rings"]:
        assert ring.Volume() == pytest.approx(pm.end_ring_volume_hand(D, SEC), rel=1e-9)
    assert SEC["stator_Rint"] - SEC["rotor_Rext"] == pytest.approx(0.7747, abs=1e-4)   # the air gap


def test_masses_against_the_bill_of_materials(parts):
    m = pm.masses(parts)
    # BOM (ORNL/TM-2010/253 Table 2.7): stator core 19.05 kg; magnets 16 x 77 g. The core at the stand-in grade's
    # density (7650 kg/m^3), as a solid stack: 0.9 % light without the drawing's ears and notches, 0.02 % with them.
    assert m["stator_core_kg"] == pytest.approx(19.05, rel=0.005)
    assert m["magnets_kg"] == pytest.approx(16 * 0.077, rel=0.005)


def test_step_round_trip(tmp_path):
    import cadquery as cq
    path = tmp_path / "motor.step"
    parts = pm.export("rev5", path)
    text = path.read_text(encoding="utf-8", errors="replace")
    assert "('Author')" in text and "Users" not in text
    solids = cq.importers.importStep(str(path)).solids().vals()
    assert len(solids) == 1 + 48 + 2 + 1 + 16
    built = (parts["stator"].Volume() + sum(w.Volume() for w in parts["windings"])
             + sum(r.Volume() for r in parts["end_rings"]) + parts["rotor"].Volume()
             + sum(m.Volume() for m in parts["magnets"]))
    assert sum(s.Volume() for s in solids) == pytest.approx(built, rel=1e-6)
    # the instanced magnets land where the built ones are (centres of mass, as sets)
    small = sorted((round(s.Center().x, 3), round(s.Center().y, 3)) for s in solids
                   if abs(s.Volume() - parts["magnets"][0].Volume()) < 1e-3)
    ref = sorted((round(m.Center().x, 3), round(m.Center().y, 3)) for m in parts["magnets"])
    assert small == ref

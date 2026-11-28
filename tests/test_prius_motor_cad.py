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


def test_magnets_and_slot_windings(parts):
    assert len(parts["magnets"]) == 16 and len(parts["windings"]) == 48
    for m in parts["magnets"][:2]:
        assert m.Volume() == pytest.approx(18.9 * 6.5 * D["magnet_length"], rel=1e-9)
        common = parts["rotor"].intersect(m)
        assert common.Volume() < 1e-6                                       # in its pocket, not in the steel
    zone = abs(pm.loop_area([pm._from_json(e) for e in SEC["winding_edges"]]))
    assert parts["windings"][0].Volume() == pytest.approx(zone * D["stator_stack"], rel=1e-9)
    assert parts["stator"].intersect(parts["windings"][0]).Volume() < 1e-6
    assert SEC["stator_Rint"] - SEC["rotor_Rext"] == pytest.approx(0.7747, abs=1e-4)   # the air gap


def _vol(shape):
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    p = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape.wrapped, p, 1e-9)
    return p.Mass()


def test_coil_layout_is_the_analysed_single_layer_winding():
    coils = pm.coil_layout(SEC)
    assert len(coils) == 24 and all(sum(c["phase"] == ph for c in coils) == 8 for ph in "ABC")   # BOM: 8 per phase
    used = sorted(k for c in coils for k in c["slots"])
    assert used == list(range(48))                         # every slot side once: single layer
    for c in coils:
        a, b = c["slots"]
        assert SEC["slot_phases"][a][0] == SEC["slot_phases"][b][0] == c["phase"]
        assert SEC["slot_phases"][a] != SEC["slot_phases"][b]          # go and return: opposite turn signs
    assert sorted({c["span"] for c in coils}) == [5, 7] and sum(c["span"] for c in coils) / 24 == 6   # full pitch
    assert SEC["turns_per_slot"] == [D["turns_per_coil"]]
    # the layout repeats every pole pair, which the STEP's instancing by 90 deg relies on
    assert SEC["slot_phases"] == SEC["slot_phases"][:12] * 4
    # slot centres: the winding zone of slot 0 is centred at half a pitch
    pts = [p for e in SEC["winding_edges"] for p in (e["b"], e["e"])]
    assert math.degrees(math.atan2(sum(p[1] for p in pts), sum(p[0] for p in pts))) == pytest.approx(
        pm.slot_deg(SEC, 0), abs=1e-6)


def test_end_turns_against_exact_hand_volumes(parts):
    turns = parts["end_turns"]
    assert len(turns) == 48
    A = pm.zone_area(SEC)
    for T in pm.end_tiers(D, SEC):
        assert T["d"] * T["w"] == pytest.approx(A, rel=1e-12)          # the bundle keeps the slot zone's area
    for t in turns:
        s, c = t["solid"], t["coil"]
        assert s.isValid()
        assert _vol(s) == pytest.approx(pm.end_turn_volume_hand(D, SEC, c), rel=1e-7)
        bb = s.BoundingBox()
        far = D["stator_stack"] / 2 + D["end_extension"]
        sign = 1 if t["end"] == "a" else -1
        assert (bb.zmax if sign > 0 else -bb.zmin) == pytest.approx(far if c["role"] == "outer" else far - pm.end_turn_shape(D, SEC, c)["w"], abs=1e-6)
        assert (bb.zmin if sign > 0 else -bb.zmax) == pytest.approx(D["stator_stack"] / 2, abs=1e-6)   # on the stack face
    # the -z turn (the +z turn turned over about its middle radial line, so the STEP can instance it) is the +z
    # turn's mirror image
    for t in [u for u in turns if u["end"] == "b" and u["coil"]["sector"] == 0]:
        a = next(u for u in turns if u["coil"] == t["coil"] and u["end"] == "a")["solid"]
        mir = a.mirror("XY")
        assert _vol(t["solid"].intersect(mir)) == pytest.approx(_vol(mir), rel=1e-7)
    # the face before thickening, on the tier's inner cylinder: (r_in / r_t) w L, OCC's area against the hand length
    c = pm.coil_layout(SEC)[4]
    sh = pm.end_turn_shape(D, SEC, c)
    T = sh["tier"]
    face = pm._end_turn_face(T["r_in"], T["r_t"], 0.0, sh["S"], 0.0, sh["H"], sh["R"], sh["w"])
    assert face.isValid() and face.Area() == pytest.approx(T["r_in"] / T["r_t"] * sh["w"] * sh["L"], rel=1e-9)


def test_end_turn_clearances(parts):
    turns = parts["end_turns"]
    tiers = pm.end_tiers(D, SEC)
    # clear of the bore (the rotor goes in axially): the inner tier starts at the slot zone's inner radius
    assert tiers[0]["r_in"] - SEC["stator_Rint"] > 1.0
    assert tiers[-1]["r_out"] < SEC["stator_Rext"] - 15                  # on the yoke face, well inside the OD
    for t in turns:
        rmin = min(math.hypot(v.X, v.Y) for v in t["solid"].Vertices())
        assert rmin >= tiers[t["coil"]["tier"]]["r_in"] - 1e-6
    # the first pole pair's six turns at one end overlap in angle: no two of them share volume (tiers apart
    # radially, a group's two coils nested and touching)
    first = [t for t in turns if t["coil"]["sector"] == 0 and t["end"] == "a"]
    for i in range(len(first)):
        for j in range(i + 1, len(first)):
            assert first[i]["solid"].intersect(first[j]["solid"]).Volume() < 1e-6
    # neighbouring pole pairs' turns of the same tier do not meet; nor do the turns and the stator core
    a0 = next(t for t in turns if t["coil"]["sector"] == 0 and t["coil"]["tier"] == 2 and t["end"] == "a" and t["coil"]["role"] == "outer")
    a1 = next(t for t in turns if t["coil"]["sector"] == 1 and t["coil"]["tier"] == 2 and t["end"] == "a" and t["coil"]["role"] == "outer")
    assert a0["solid"].intersect(a1["solid"]).Volume() < 1e-6
    for t in first:
        assert parts["stator"].intersect(t["solid"]).Volume() < 1e-6


def test_copper_against_the_bom_and_the_efficiency_study(parts):
    cu = pm.copper(D, SEC)
    # BOM 6.8 kg includes the leads and the jumpers between coils, which are not drawn: the turns come in under it
    assert 0.94 * 6.8 < cu["kg"] < 6.8
    # the efficiency study's end connection (semicircle over the 6-slot span at the slot mid radius): 120.6 mm
    assert cu["mean_end_turn_mm"] == pytest.approx(120.6, rel=0.06)
    # the solids carry the same copper: zone and bundle volumes times the copper fraction of the zone
    vol = sum(w.Volume() for w in parts["windings"]) + sum(_vol(t["solid"]) for t in parts["end_turns"])
    assert vol * cu["copper_fill_of_zone"] * 1e-9 * pm.DENSITY["copper"] == pytest.approx(cu["kg"], rel=1e-7)


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
    assert len(solids) == 1 + 48 + 48 + 1 + 16
    built = (parts["stator"].Volume() + sum(w.Volume() for w in parts["windings"])
             + sum(t["solid"].Volume() for t in parts["end_turns"]) + parts["rotor"].Volume()
             + sum(m.Volume() for m in parts["magnets"]))
    assert sum(s.Volume() for s in solids) == pytest.approx(built, rel=1e-6)
    # the instanced magnets land where the built ones are (centres of mass, as sets)
    small = sorted((round(s.Center().x, 3), round(s.Center().y, 3)) for s in solids
                   if abs(s.Volume() - parts["magnets"][0].Volume()) < 1e-3)
    ref = sorted((round(m.Center().x, 3), round(m.Center().y, 3)) for m in parts["magnets"])
    assert small == ref
    # and the instanced end turns where the built ones are (centres of mass, as sets)
    # (the only solids beyond the stack faces)
    got = np.array([s.Center().toTuple() for s in solids if abs(s.Center().z) > D["stator_stack"] / 2])
    ref = np.array([t["solid"].Center().toTuple() for t in parts["end_turns"]])
    assert len(got) == len(ref) == 48
    assert max(np.min(np.linalg.norm(got - r, axis=1)) for r in ref) < 1e-3

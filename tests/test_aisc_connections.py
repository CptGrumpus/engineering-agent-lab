"""validation/aisc_connections.py against Example II.B-1 of the AISC v16.0 Companion, Vol. 1: Design Examples
(bolted flange-plated FR moment connection, W18x50 beam to a W14x99 column flange; LRFD).

The example prints three significant figures and rounds some intermediates (noted where it matters): tolerance
0.5 % unless stated. Its geometry: 7/8 in. Group A bolts (threads included), standard holes; flange plates 7 x 3/4 in.
(A572 Gr. 50), two rows of four bolts at 3 in. pitch on a 4 in. gage, edge distances 1 1/2 in.; web plate 9 x 3/8 in.,
three bolts at 3 in., 1 1/2 in. edge; 1/4 in. web-plate welds, E70. Fy 50, Fu 65 ksi throughout; kip, inch.
"""
import pytest

from validation import aisc360
from validation import aisc_connections as c

FY, FU, D = 50.0, 65.0, 0.875
DH = c.hole_std(D)
BEAM, COL = aisc360.shape("W18X50"), aisc360.shape("W14X99")
MU = 1.2 * 42 + 1.6 * 126            # kip-ft
VU = 1.2 * 7 + 1.6 * 21              # kips
TP, BP = 0.75, 7.0                   # flange plate


def close(value, expected, rel=0.005):
    return value == pytest.approx(expected, rel=rel)


def test_required_strengths():
    assert close(MU, 252) and close(VU, 42.0)
    assert close(MU * 12 / BEAM["d"], 168)                   # flange force at the faying surface (bolts)
    assert close(MU * 12 / (BEAM["d"] + TP), 161, 0.003)     # at the plate's mid-thickness (plate, welds)


def test_hole_and_bolt_shear():
    assert DH == pytest.approx(15 / 16)
    assert close(c.bolt_shear(D), 24.3)


def test_slip_resistance_examples_j4a_j4b_j5():
    assert close(c.slip_resistance(0.75, ns=2), 19.0)              # J.4A: Class A, standard / short-slotted
    assert close(c.slip_resistance(0.75, ns=2, phi=0.70), 13.3)    # J.4B: long-slotted holes
    assert close(c.slip_resistance(0.75, ns=1), 9.49, 0.002)       # combined tension and shear example, Tu = 0


def test_beam_flange_rupture_f13():
    Afg = BEAM["bf"] * BEAM["tf"]
    Afn = Afg - 2 * (DH + 1 / 16) * BEAM["tf"]
    assert close(Afg, 4.28) and close(Afn, 3.14, 0.006)
    assert close(c.flange_rupture_moment(FY, FU, Afg, Afn, BEAM["Sx"]) / 12, 318)


def test_web_plate_bolts_bearing_tearout():
    t = 0.375
    assert close(c.bearing(D, t, FU), 38.4) and close(c.tearout(3 - DH, t, FU), 45.2)
    assert close(c.tearout(1.5 - DH / 2, t, FU), 22.6)
    assert close(c.bearing(D, BEAM["tw"], FU), 36.4) and close(c.tearout(3 - DH, BEAM["tw"], FU), 42.8)
    assert close(c.bolt_row_strength(3, D, t, FU, 3.0, 1.5), 71.2)


def test_web_plate_shear_block_and_welds():
    t, L = 0.375, 9.0
    assert close(c.shear_yield(FY, L * t), 101)
    assert close(c.shear_rupture(FU, (L - 3 * (DH + 1 / 16)) * t), 65.9)
    # block shear: n = 3, lev = 1 1/2, leh = 2 in.: shear planes 7 1/2 in. gross, 5 in. net; tension 1 1/2 in. net
    assert close(c.block_shear(FY, FU, 7.5 * t, (7.5 - 2.5 * (DH + 1 / 16)) * t, (2 - 0.5 * (DH + 1 / 16)) * t), 82.2)
    assert close(2 * c.fillet_weld(4, L), 100)
    assert close(c.shear_rupture(FU, 2 * L * COL["tf"]), 410)


def test_flange_plate_bolts():
    assert close(c.bearing(D, TP, FU), 76.5) and close(c.tearout(3 - DH, TP, FU), 90.8)
    assert close(c.tearout(1.5 - DH / 2, TP, FU), 45.2)
    assert close(c.bearing(D, BEAM["tf"], FU), 58.4) and close(c.tearout(3 - DH, BEAM["tf"], FU), 68.7)
    assert close(c.tearout(1.5 - DH / 2, BEAM["tf"], FU), 34.4)
    assert close(2 * c.bolt_row_strength(4, D, TP, FU, 3.0, 1.5), 194)      # bolt shear governs every bolt


def test_flange_plate_tension_compression():
    # the example rounds Fy Ag to 263 kips before phi: 237 against 236.25 exact
    assert close(c.tension_yield(FY, BP * TP), 237, 0.004)
    assert close(c.tension_rupture(FU, (BP - 2 * (DH + 1 / 16)) * TP), 183)
    assert close(c.compression_short(FY, BP, TP, 3.0), 237, 0.004)


def test_flange_plate_and_beam_flange_block_shear():
    a = DH + 1 / 16
    # case 1: two blocks outside the bolt rows, n = 4, s = 3, lev = leh = 1 1/2
    case1 = 2 * c.block_shear(FY, FU, 10.5 * TP, (10.5 - 3.5 * a) * TP, (1.5 - 0.5 * a) * TP)
    assert close(case1, 381)
    # case 3: one bolt row in shear, tension across the gage to the far edge
    agv = 10.5 * TP
    assert close(c.block_shear(FY, FU, agv, agv - 3.5 * a * TP, (4 + 1.5 - 1.5 * a) * TP), 300)
    # beam flange: lev 1 1/4 (1/4 in. underrun), leh (7.50 - 4) / 2
    tf, leh = BEAM["tf"], (BEAM["bf"] - 4) / 2
    assert close(2 * c.block_shear(FY, FU, 10.25 * tf, (10.25 - 3.5 * a) * tf, (leh - 0.5 * a) * tf), 294)


def test_flange_plate_weld_size():
    puf = MU * 12 / (BEAM["d"] + TP)
    dmin = puf / (2 * c.fillet_weld(1, BP, theta_deg=90))
    assert close(c.k_ds(90), 1.5) and close(dmin, 5.51, 0.003)


def test_column_j10():
    lb = TP
    assert close(c.flange_local_bending(FY, COL["tf"]), 171)
    assert close(c.web_local_yielding(FY, COL["tw"], COL["kdes"], lb), 186)
    assert close(c.web_crippling(FY, COL["tw"], COL["tf"], COL["d"], lb), 233)
    # Manual Table 9-4's end-of-member constants, as the example lists them: R1 = phi Fyw tw 2.5k, R3 = phi 0.40 ...
    assert close(c.web_local_yielding(FY, COL["tw"], COL["kdes"], 0.0, near_end=True), 83.7)
    assert close(c.web_crippling(FY, COL["tw"], COL["tf"], COL["d"], 0.0, near_end=True), 108)


def test_end_forms_halve_or_reduce():
    assert c.flange_local_bending(FY, 0.78, near_end=True) == pytest.approx(0.5 * c.flange_local_bending(FY, 0.78))
    assert c.web_compression_buckling(FY, 0.5, 12.0, near_end=True) == pytest.approx(
        0.5 * c.web_compression_buckling(FY, 0.5, 12.0))
    full = c.panel_zone_shear(FY, 10.0, 0.3, 0.0, 500.0)
    assert full == pytest.approx(0.90 * 0.60 * FY * 10.0 * 0.3)
    assert c.panel_zone_shear(FY, 10.0, 0.3, 300.0, 500.0) == pytest.approx(full * (1.4 - 0.6))


# ---------------------------------------------------------------- the whole connection, validation/flange_plated.py
EXAMPLE_GEOMETRY = {
    "bolt": {"d": D, "Fnv": 54.0},
    # lev_beam 1 1/4 in. (1 1/2 less 1/4 in. underrun, as the example's block shear; its tearout check at 1 1/2 in.
    # is not governing either way: bolt shear 24.3 < tearout 26.0 at 1 1/4 in.)
    "fp": {"b": BP, "t": TP, "Fy": FY, "Fu": FU, "gage": 4.0, "n": 4, "s": 3.0, "le": 1.5, "lev_beam": 1.25,
           "D16": 6},
    "wp": {"L": 9.0, "t": 0.375, "Fy": FY, "Fu": FU, "n": 3, "s": 3.0, "le": 1.5, "leh": 2.0, "D16": 4},
    "col": {"z_top": None, "z_bot": None},
}


def test_flange_plated_connection_reproduces_example_ii_b_1():
    from validation import flange_plated as fpc

    r = {x["id"]: x for x in fpc.checks(BEAM, COL, EXAMPLE_GEOMETRY, MU * 12, VU)}
    expected = {"beam_flange_rupture": 318 * 12, "web_bolts": 71.2, "web_plate_shear_yield": 101,
                "web_plate_shear_rupture": 65.9, "web_plate_block_shear": 82.2, "web_plate_welds": 100,
                "column_flange_rupture_web_welds": 410, "flange_bolts": 194, "flange_plate_tension_yield": 237,
                "flange_plate_tension_rupture": 183, "flange_plate_compression": 237, "flange_plate_block_shear_1": 381,
                "flange_plate_block_shear_3": 300, "beam_flange_block_shear": 294, "column_flange_local_bending": 171,
                "column_web_yielding_top": 186, "column_web_yielding_bottom": 186, "column_web_crippling": 233}
    for cid, cap in expected.items():
        assert close(r[cid]["capacity"], cap), (cid, r[cid]["capacity"], cap)
    # the example sizes the plate welds: 5.51 sixteenths needed, 3/8 in. (6) chosen
    assert close(r["flange_plate_welds"]["ratio"], 5.51 / 6, 0.003)
    assert close(r["flange_bolts"]["demand"], 168) and close(r["flange_plate_tension_yield"]["demand"], 161, 0.003)
    assert all(x["ratio"] <= 1.0 for x in r.values())         # the example's verdict: every check o.k.

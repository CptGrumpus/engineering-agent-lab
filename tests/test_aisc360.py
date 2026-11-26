"""validation/aisc360.py against the worked answers of the AISC v16.0 Companion, Vol. 1: Design Examples (LRFD).

The examples print three significant figures and sometimes round an intermediate (noted where it matters), so the
tolerance is 0.5 % unless stated. Fy 50 ksi (ASTM A992), E 29,000 ksi; kip, inch.
"""
import pytest

from validation import aisc360 as a

E, FY = 29000.0, 50.0
FT = 12.0


def close(value, expected, rel=0.005):
    return value == pytest.approx(expected, rel=rel)


# ---------------------------------------------------------------- compression
def test_e1c_w14x132_pinned_30ft():
    # the example interpolates Manual Table 4-14 (phi Fcr 23.0 ksi): 892 kips
    r = a.compression(a.shape("W14X132"), E, FY, 30 * FT, 30 * FT)
    assert close(r["phiPn"], 892)


def test_e1d_w14x90_x_axis_governs():
    r = a.compression(a.shape("W14X90"), E, FY, 30 * FT, 15 * FT)
    assert close(r["Lc_over_r"], 58.6, 0.002) and close(r["Fe"], 83.3) and close(r["Fn"], 38.9)
    assert close(r["Pn"], 1030) and close(r["phiPn"], 927)
    assert not r["elements"]["web"]["slender"] and not r["elements"]["flange"]["slender"]


def test_e1e_w16x31_slender_web():
    s = a.shape("W16X31")
    r5 = a.compression(s, E, FY, 5 * FT, 5 * FT)          # E7 reduces the web: Ae 8.44 in2, 349 / 314 kips
    assert r5["elements"]["web"]["slender"] and r5["elements"]["web"]["be"] < r5["elements"]["web"]["b"]
    assert close(r5["Ae"], 8.44) and close(r5["Pn"], 349) and close(r5["phiPn"], 314)
    r10 = a.compression(s, E, FY, 10 * FT, 10 * FT)        # web fully effective at this stress: Ae = Ag
    assert r10["Ae"] == pytest.approx(s["A"])
    assert close(r10["phiPn"], 189, 0.008)                 # the example rounds Lc/r to 103 first (Fn 23.0 vs 23.2)
    r15 = a.compression(s, E, FY, 15 * FT, 15 * FT)
    assert close(r15["Pn"], 96.8) and close(r15["phiPn"], 87.1)


def test_table_6_1_w14x99_14ft():                          # the strengths Example H.1B takes from Table 6-1
    assert close(a.compression(a.shape("W14X99"), E, FY, 14 * FT, 14 * FT)["phiPn"], 1130)


# ---------------------------------------------------------------- flexure
def test_f1_w18x50_three_bracing_cases():
    s = a.shape("W18X50")
    r = a.flexure(s, E, FY, 0.0)                           # F.1-1B, continuously braced: Mp
    assert r["regime"] == "yielding" and close(r["Mp"] / FT, 421) and close(r["phiMn"] / FT, 379)
    assert close(r["Lp"] / FT, 5.83) and close(r["Lr"] / FT, 16.9, 0.005)
    r = a.flexure(s, E, FY, 35 * FT / 3, 1.01)             # F.1-2B, third points (example rounds Lb to 11.7 ft)
    assert r["regime"] == "inelastic LTB" and close(r["phiMn"] / FT, 304)
    r = a.flexure(s, E, FY, 35 * FT / 2, 1.30)             # F.1-3B, midspan: elastic LTB
    assert r["regime"] == "elastic LTB" and close(r["Mn"] / FT, 320) and close(r["phiMn"] / FT, 288)


def test_f3b_w21x48_noncompact_flange():
    r = a.flexure(a.shape("W21X48"), E, FY, 0.0)
    assert r["flange"] == "noncompact" and r["governs"] == "FLB"
    assert close(r["Mn"] / FT, 442) and close(r["phiMn"] / FT, 398)


def test_table_6_1_w14x99_flexure_14ft():
    r = a.flexure(a.shape("W14X99"), E, FY, 14 * FT, 1.0)
    assert r["flange"] == "noncompact" and close(r["phiMn"] / FT, 642)


def test_cb_uniform_load_simple_span():
    assert a.cb(1.0, 0.75, 1.0, 0.75) == pytest.approx(1.136, abs=0.001)


# ---------------------------------------------------------------- shear and interaction
def test_g1b_w24x62_shear():
    r = a.shear(a.shape("W24X62"), E, FY)
    assert r["phi"] == 1.0 and r["Cv1"] == 1.0 and close(r["phiVn"], 306)


def test_h1b_interaction():
    r = a.interaction(400, 1130, 250, 642, 80.0, 311)
    assert r["equation"] == "H1-1a" and r["ratio"] == pytest.approx(0.929, abs=0.001)
    assert a.interaction(100, 1130, 250, 642)["equation"] == "H1-1b"


# ---------------------------------------------------------------- the frame's own members
def test_frame_members_classified():
    w10, w14 = a.shape("W10X33"), a.shape("W14X30")
    f10 = a.flexure(w10, E, FY, 0.0)
    assert f10["flange"] == "compact"                      # bf/2tf 9.15 against 0.38 sqrt(E/Fy) = 9.152: by 0.002
    c14 = a.compression(w14, E, FY, 20 * FT, 20 * FT)
    assert c14["elements"]["web"]["slender"]               # h/tw 45.4 > 35.9: E7 applies to the beam's axial force


def test_si_conversion_round_trip():
    s, si = a.shape("W10X33"), a.to_si(a.shape("W10X33"))
    assert si["A"] == pytest.approx(s["A"] * 645.16) and si["Ix"] == pytest.approx(s["Ix"] * 25.4 ** 4)
    e_si, fy_si = 199948.0, 344.738                        # 29,000 and 50 ksi in MPa
    p_in = a.compression(s, E, FY, 4000 / 25.4, 4000 / 25.4)["phiPn"]           # kips
    p_si = a.compression(si, e_si, fy_si, 4000.0, 4000.0)["phiPn"] / 4448.222   # N -> kips
    assert p_si == pytest.approx(p_in, rel=1e-4)

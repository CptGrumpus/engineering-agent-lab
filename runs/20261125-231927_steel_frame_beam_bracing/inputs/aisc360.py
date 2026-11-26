"""AISC 360-22 member strength checks for rolled, doubly symmetric I-shapes (W-shapes), LRFD (steel frame study).

Written from the Specification (references/aisc/A360-22W-ewr.pdf, the user's download; gitignored) and tested against
the worked answers of the v16.0 Companion, Vol. 1: Design Examples (tests/test_aisc360.py). Unit-agnostic: give E, Fy
and the section properties in one consistent system (kip and inch for the examples; N and mm for the frame).

Covered:
- Chapter E: flexural buckling (E3) with slender-element effective area (E7) for a slender web or flange. Torsional
  and flexural-torsional buckling (E4) is not checked: for rolled W-shapes with the torsional unbraced length equal
  to the weak-axis one it does not govern (Commentary E4, as Example E.1D notes).
- Chapter F: major-axis flexure, F2 (compact web and flanges: yielding, lateral-torsional buckling) and F3 (compact
  web, noncompact or slender flanges: adds flange local buckling).
- Chapter G: major-axis shear, G2.1 (web shear; kv = 5.34, no stiffeners).
- Chapter H: H1.1 interaction of axial force and flexure (Eq. H1-1a / H1-1b).
- Cb by Eq. F1-1 from the quarter-point moments.

Section properties are the Shapes Database v16.0 values (validation/aisc_shapes_subset.json: the shapes used here;
the full database stays in references/aisc/, gitignored). Slenderness ratios are the tabulated bf/2tf and h/tw, as
the Design Examples use them.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

PHI_C, PHI_B, PHI_V_ROLLED, PHI_V = 0.90, 0.90, 1.00, 0.90
SHAPES_FILE = Path(__file__).with_name("aisc_shapes_subset.json")


def shape(label: str) -> dict:
    """Section properties (kip and inch) of a shape in the subset file, by its AISC manual label ('W10X33')."""
    data = json.loads(SHAPES_FILE.read_text(encoding="utf-8"))["shapes"]
    return dict(data[label.upper()])


def to_si(sec: dict) -> dict:
    """The same section in N-mm units: lengths in mm, A in mm2, I in mm4, Z and S in mm3, Cw in mm6."""
    inch = 25.4
    power = {"d": 1, "bf": 1, "tw": 1, "tf": 1, "kdes": 1, "rx": 1, "ry": 1, "rts": 1, "ho": 1, "A": 2,
             "Ix": 4, "Iy": 4, "J": 4, "Zx": 3, "Sx": 3, "Zy": 3, "Sy": 3, "Cw": 6}
    out = {}
    for k, v in sec.items():
        out[k] = v * inch ** power[k] if k in power and v is not None else v
    return out


def _lim(E, Fy, c):
    return c * math.sqrt(E / Fy)


# ---------------------------------------------------------------- Chapter E: compression
def compression(sec: dict, E: float, Fy: float, Lcx: float, Lcy: float) -> dict:
    """Design compressive strength phi_c Pn (E3, with E7 when an element is slender). Lcx, Lcy: effective lengths."""
    A = sec["A"]
    slender_ratio = max(Lcx / sec["rx"], Lcy / sec["ry"])
    Fe = math.pi ** 2 * E / slender_ratio ** 2                                   # E3-4
    if Fy / Fe <= 2.25:                                                          # Lc/r <= 4.71 sqrt(E/Fy)
        Fn = 0.658 ** (Fy / Fe) * Fy                                             # E3-2
    else:
        Fn = 0.877 * Fe                                                          # E3-3
    # E7: effective area. Web: stiffened (Table B4.1a case 5, lambda_r 1.49 sqrt(E/Fy); Table E7.1 case (a):
    # c1 0.18, c2 1.31). Flange: unstiffened (case 1, 0.56 sqrt(E/Fy); Table E7.1 case (c): c1 0.22, c2 1.49).
    Ae = A
    detail = {}
    for name, lam, lam_r, c1, c2, width, t, count in (
            ("web", sec["h/tw"], _lim(E, Fy, 1.49), 0.18, 1.31, sec["h/tw"] * sec["tw"], sec["tw"], 1),
            ("flange", sec["bf/2tf"], _lim(E, Fy, 0.56), 0.22, 1.49, sec["bf"] / 2, sec["tf"], 4)):
        slender = lam > lam_r
        be = width
        if slender and lam > lam_r * math.sqrt(Fy / Fn):                         # E7-3 applies
            Fel = (c2 * lam_r / lam) ** 2 * Fy                                   # E7-5
            be = width * (1 - c1 * math.sqrt(Fel / Fn)) * math.sqrt(Fel / Fn)    # E7-3
        Ae -= count * (width - be) * t
        detail[name] = {"lambda": lam, "lambda_r": lam_r, "slender": slender, "b": width, "be": be}
    Pn = Fn * Ae                                                                 # E7-1 (= E3-1 when Ae = Ag)
    return {"Lc_over_r": slender_ratio, "Fe": Fe, "Fn": Fn, "Ae": Ae, "Pn": Pn, "phiPn": PHI_C * Pn,
            "elements": detail}


# ---------------------------------------------------------------- Chapter F: major-axis flexure
def cb(m_max: float, m_a: float, m_b: float, m_c: float) -> float:
    """Eq. F1-1 from the absolute moments: maximum, and at the quarter, centre and three-quarter points."""
    m_max, m_a, m_b, m_c = (abs(v) for v in (m_max, m_a, m_b, m_c))
    return 12.5 * m_max / (2.5 * m_max + 3 * m_a + 4 * m_b + 3 * m_c)


def flexure(sec: dict, E: float, Fy: float, Lb: float, Cb: float = 1.0) -> dict:
    """Design major-axis flexural strength phi_b Mn of a W-shape (F2, or F3 for a noncompact or slender flange)."""
    lam_w, lam_pw = sec["h/tw"], _lim(E, Fy, 3.76)
    if lam_w > lam_pw:
        raise ValueError(f"web noncompact in flexure (h/tw {lam_w} > {lam_pw:.1f}): F4/F5 not implemented")
    Mp = Fy * sec["Zx"]                                                          # F2-1
    Sx, rts, ho, J = sec["Sx"], sec["rts"], sec["ho"], sec["J"]
    Lp = 1.76 * sec["ry"] * math.sqrt(E / Fy)                                    # F2-5
    jc = J * 1.0 / (Sx * ho)                                                     # c = 1 (doubly symmetric)
    Lr = 1.95 * rts * E / (0.7 * Fy) * math.sqrt(jc + math.sqrt(jc ** 2 + 6.76 * (0.7 * Fy / E) ** 2))  # F2-6
    if Lb <= Lp:
        M_ltb, regime = Mp, "yielding"
    elif Lb <= Lr:
        M_ltb = min(Cb * (Mp - (Mp - 0.7 * Fy * Sx) * (Lb - Lp) / (Lr - Lp)), Mp)  # F2-2
        regime = "inelastic LTB"
    else:
        Fcr = Cb * math.pi ** 2 * E / (Lb / rts) ** 2 * math.sqrt(1 + 0.078 * jc * (Lb / rts) ** 2)  # F2-4
        M_ltb, regime = min(Fcr * Sx, Mp), "elastic LTB"                         # F2-3
    lam_f, lam_pf, lam_rf = sec["bf/2tf"], _lim(E, Fy, 0.38), _lim(E, Fy, 1.0)
    if lam_f <= lam_pf:
        M_flb, flange = Mp, "compact"
    elif lam_f <= lam_rf:
        M_flb = Mp - (Mp - 0.7 * Fy * Sx) * (lam_f - lam_pf) / (lam_rf - lam_pf)  # F3-1
        flange = "noncompact"
    else:
        h_tw = sec["h/tw"]
        kc = min(max(4 / math.sqrt(h_tw), 0.35), 0.76)
        M_flb, flange = 0.9 * E * kc * Sx / lam_f ** 2, "slender"               # F3-2
    Mn = min(M_ltb, M_flb)
    return {"Mp": Mp, "Lp": Lp, "Lr": Lr, "regime": regime, "flange": flange, "M_ltb": M_ltb, "M_flb": M_flb,
            "Mn": Mn, "phiMn": PHI_B * Mn, "governs": "LTB" if M_ltb <= M_flb else "FLB"}


# ---------------------------------------------------------------- Chapter G: major-axis shear
def shear(sec: dict, E: float, Fy: float) -> dict:
    """Design web shear strength phi_v Vn (G2.1), unstiffened web (kv = 5.34)."""
    Aw = sec["d"] * sec["tw"]
    h_tw = sec["h/tw"]
    if h_tw <= _lim(E, Fy, 2.24):                                                # G2.1(a): rolled I-shapes
        phi, Cv1 = PHI_V_ROLLED, 1.0
    else:                                                                        # G2.1(b)
        phi, kv = PHI_V, 5.34
        Cv1 = 1.0 if h_tw <= 1.10 * math.sqrt(kv * E / Fy) else 1.10 * math.sqrt(kv * E / Fy) / h_tw
    Vn = 0.6 * Fy * Aw * Cv1                                                     # G2-1
    return {"Aw": Aw, "Cv1": Cv1, "phi": phi, "Vn": Vn, "phiVn": phi * Vn}


# ---------------------------------------------------------------- Chapter H: interaction
def interaction(Pr: float, Pc: float, Mrx: float, Mcx: float, Mry: float = 0.0, Mcy: float = 1.0) -> dict:
    """H1-1a / H1-1b ratio (required over available; compression or tension in Pr)."""
    p = abs(Pr) / Pc
    m = abs(Mrx) / Mcx + abs(Mry) / Mcy
    if p >= 0.2:
        return {"equation": "H1-1a", "ratio": p + 8.0 / 9.0 * m}
    return {"equation": "H1-1b", "ratio": p / 2 + m}

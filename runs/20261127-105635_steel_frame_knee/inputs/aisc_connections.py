"""AISC 360-22 connection limit states (Chapter J, and F13.1 for the beam at its bolt holes), LRFD (steel frame
study, part 2: the beam-to-column moment connection).

Written from the Specification (references/aisc/A360-22W-ewr.pdf, the user's download; gitignored) and tested against
Example II.B-1 of the v16.0 Companion, Vol. 1: Design Examples (bolted flange-plated FR moment connection,
tests/test_aisc_connections.py). The Manual's tables the example reads (7-1 bolt shear, 8-2 weld, 9-3 block shear,
9-4 column web) are computed here from the Specification's equations they tabulate.

Units: kip and inch, as the Design Examples (Fy, Fu, Fnv, E in ksi). Every function returns the design strength
phi R_n unless its name says otherwise.

Covered:
- J3: bolt shear (J3-1), bearing and tearout at a hole (J3-6a, J3-6c; deformation at service load a consideration),
  standard hole sizes (Table J3.3), a bolt group as the sum of each bolt's least strength (Commentary J3.7); slip
  resistance of slip-critical bolts (J3-4, Table J3.1 pretensions).
- J2.4: fillet weld strength with the directional factor k_ds (J2-5), in the Manual's per-sixteenth form (Eq. 8-2a).
- J4: tension yielding and rupture (J4-1, J4-2), shear yielding and rupture (J4-3, J4-4), block shear (J4-5),
  compression of a short element (J4.4, KL/r <= 25).
- F13.1: the beam's flexural strength at bolt holes in its tension flange (F13-1).
- J10: flange local bending (J10-1), web local yielding (J10-2, J10-3), web local crippling (J10-4, J10-5a),
  web compression buckling (J10-8), panel-zone shear without the panel-zone deformation term (J10-9, J10-10),
  each with its column-end form where the force acts within the Specification's distance of the member's end.
"""

from __future__ import annotations

import math

PHI_BOLT, PHI_RUPTURE, PHI_YIELD_T, PHI_SHEAR_YIELD = 0.75, 0.75, 0.90, 1.00
E_STEEL = 29000.0


# --- J3: bolts -------------------------------------------------------------------------------------------------

def hole_std(d: float) -> float:
    """Standard hole diameter, Table J3.3 (inch bolts): d + 1/16 below 1 in., d + 1/8 from 1 in."""
    return d + (1 / 16 if d < 1.0 else 1 / 8)


def bolt_shear(d: float, Fnv: float = 54.0) -> float:
    """phi r_n per bolt per shear plane, J3-1. Fnv 54 ksi: Group A (A325), threads not excluded (N), Table J3.2."""
    return PHI_BOLT * Fnv * math.pi * d ** 2 / 4


def bearing(d: float, t: float, Fu: float) -> float:
    """phi r_n, bearing at a bolt hole, J3-6a: 2.4 d t Fu."""
    return PHI_BOLT * 2.4 * d * t * Fu


def tearout(lc: float, t: float, Fu: float) -> float:
    """phi r_n, tearout at a bolt hole, J3-6c: 1.2 lc t Fu (lc: clear distance to the edge or the next hole)."""
    return PHI_BOLT * 1.2 * lc * t * Fu


def bolt_strength(d: float, t: float, Fu: float, lc: float, Fnv: float = 54.0) -> float:
    """One bolt in one ply: the least of shear, bearing and tearout."""
    return min(bolt_shear(d, Fnv), bearing(d, t, Fu), tearout(lc, t, Fu))


def bolt_row_strength(n: int, d: float, t: float, Fu: float, s: float, le: float, Fnv: float = 54.0) -> float:
    """A line of n bolts loaded along the line toward the edge: one edge bolt (lc = le - dh/2), n - 1 interior bolts
    (lc = s - dh). Commentary J3.7: the group's strength is the sum over its bolts."""
    dh = hole_std(d)
    return bolt_strength(d, t, Fu, le - dh / 2, Fnv) + (n - 1) * bolt_strength(d, t, Fu, s - dh, Fnv)


#: Table J3.1, minimum bolt pretension, Group 120 (A325) bolts, kips, by diameter in inches
PRETENSION_GROUP_120 = {0.5: 12.0, 0.625: 19.0, 0.75: 28.0, 0.875: 39.0, 1.0: 51.0, 1.125: 56.0, 1.25: 71.0}


def slip_resistance(d: float, ns: int = 1, mu: float = 0.30, hf: float = 1.0, phi: float = 1.00,
                    Du: float = 1.13) -> float:
    """phi r_n per bolt for the limit state of slip, J3-4: mu Du hf Tb ns. phi 1.00 for standard holes and short
    slots perpendicular to the load (J3.9(a)), 0.85 oversized and short slots parallel, 0.70 long slots; mu 0.30 for
    a Class A surface (0.50 Class B); Tb from Table J3.1 (Group 120)."""
    return phi * mu * Du * hf * PRETENSION_GROUP_120[d] * ns


# --- J2: welds --------------------------------------------------------------------------------------------------

def k_ds(theta_deg: float) -> float:
    """J2-5 directional strength increase of a fillet weld loaded at theta to its axis."""
    return 1.0 + 0.50 * math.sin(math.radians(theta_deg)) ** 1.5


def fillet_weld(D16: float, length: float, theta_deg: float = 0.0, FEXX: float = 70.0) -> float:
    """phi R_n of a fillet weld of leg D16 sixteenths and the given length (Manual Eq. 8-2a: phi 0.75 x 0.60 FEXX x
    0.707 x leg; 1.392 kip/in per sixteenth for E70)."""
    return 0.75 * 0.60 * FEXX * (math.sqrt(2) / 2) / 16 * D16 * length * k_ds(theta_deg)


# --- J4: affected elements ----------------------------------------------------------------------------------------

def tension_yield(Fy: float, Ag: float) -> float:
    return PHI_YIELD_T * Fy * Ag


def tension_rupture(Fu: float, Ae: float) -> float:
    return PHI_RUPTURE * Fu * Ae


def shear_yield(Fy: float, Agv: float) -> float:
    return PHI_SHEAR_YIELD * 0.60 * Fy * Agv


def shear_rupture(Fu: float, Anv: float) -> float:
    return PHI_RUPTURE * 0.60 * Fu * Anv


def block_shear(Fy: float, Fu: float, Agv: float, Anv: float, Ant: float, Ubs: float = 1.0) -> float:
    """J4-5: phi [0.60 Fu Anv + Ubs Fu Ant], at most phi [0.60 Fy Agv + Ubs Fu Ant]."""
    return PHI_RUPTURE * min(0.60 * Fu * Anv + Ubs * Fu * Ant, 0.60 * Fy * Agv + Ubs * Fu * Ant)


def compression_short(Fy: float, b: float, t: float, L: float, K: float = 0.65) -> float:
    """J4.4: a plate b x t between restraints L apart; P_n = Fy Ag when K L / r <= 25 (else Chapter E: raises)."""
    r = t / math.sqrt(12)
    if K * L / r > 25:
        raise ValueError(f"J4.4: KL/r = {K * L / r:.1f} > 25, Chapter E applies")
    return 0.90 * Fy * b * t


# --- F13.1: the beam at its bolt holes -----------------------------------------------------------------------------

def flange_rupture_moment(Fy: float, Fu: float, Afg: float, Afn: float, Sx: float) -> float | None:
    """phi M_n by F13-1 when tensile rupture of the flange holes limits it (Fu Afn < Yt Fy Afg); None otherwise."""
    Yt = 1.0 if Fy / Fu <= 0.8 else 1.1
    if Fu * Afn >= Yt * Fy * Afg:
        return None
    return 0.90 * Fu * Afn / Afg * Sx


# --- J10: the column under concentrated flange forces --------------------------------------------------------------

def flange_local_bending(Fyf: float, tf: float, near_end: bool = False) -> float:
    """J10-1: phi 0.90 x 6.25 Fyf tf^2, halved when the force acts within 10 tf of the member's end."""
    return 0.90 * 6.25 * Fyf * tf ** 2 * (0.5 if near_end else 1.0)


def web_local_yielding(Fyw: float, tw: float, k: float, lb: float, near_end: bool = False) -> float:
    """J10-2 (more than d from the end): Fyw tw (5k + lb); J10-3 (within d): Fyw tw (2.5k + lb); phi 1.00."""
    return 1.00 * Fyw * tw * ((2.5 if near_end else 5.0) * k + lb)


def web_crippling(Fyw: float, tw: float, tf: float, d: float, lb: float, near_end: bool = False,
                  E: float = E_STEEL) -> float:
    """J10-4 (at least d/2 from the end): 0.80 tw^2 [1 + 3 (lb/d)(tw/tf)^1.5] root(E Fyw tf / tw); within d/2,
    J10-5a (lb/d <= 0.2): 0.40 tw^2 [...] (J10-5b above 0.2). phi 0.75; Qf = 1 (W-shape)."""
    root = math.sqrt(E * Fyw * tf / tw)
    if not near_end:
        return 0.75 * 0.80 * tw ** 2 * (1 + 3 * (lb / d) * (tw / tf) ** 1.5) * root
    if lb / d <= 0.2:
        return 0.75 * 0.40 * tw ** 2 * (1 + 3 * (lb / d) * (tw / tf) ** 1.5) * root
    return 0.75 * 0.40 * tw ** 2 * (1 + (4 * lb / d - 0.2) * (tw / tf) ** 1.5) * root


def web_compression_buckling(Fyw: float, tw: float, h: float, near_end: bool = False, E: float = E_STEEL) -> float:
    """J10-8 (a pair of compressive forces on both flanges): phi 0.90 x 24 tw^3 root(E Fyw) / h; halved within d/2
    of the end."""
    return 0.90 * 24 * tw ** 3 * math.sqrt(E * Fyw) / h * (0.5 if near_end else 1.0)


def panel_zone_shear(Fy: float, dc: float, tw: float, Pr: float, Pc: float) -> float:
    """J10.6(a), the effect of panel-zone deformation on frame stability not accounted for: phi 0.90 x 0.60 Fy dc tw
    (J10-9) when Pr <= 0.4 Pc, x (1.4 - Pr / Pc) above (J10-10). Pc = Fy A (the column's axial yield strength)."""
    base = 0.90 * 0.60 * Fy * dc * tw
    return base if Pr <= 0.4 * Pc else base * (1.4 - Pr / Pc)

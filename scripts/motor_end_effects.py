"""Study 7, the 18 % flux excess, step 3: hand estimate of 3D end effects on the open-circuit back-EMF.

The 2D model (revision 5) is an extrusion over 83.82 mm with the magnet as long as the stack. The real rotor
differs at the two ends in three ways, each estimated on its own and as a band (low / high):

1. Gap fringing at the stack ends (adds gap permeance; the fringe flux enters the stator teeth and links the
   winding): positive.
2. Magnet leakage across the pocket ends at the rotor end faces, from the pole piece to the yoke through air
   (the end clamping piece is taken as non-magnetic: ORNL/TM-2004/137 Fig. 9 shows a copper-coloured disc, unlike
   the grey laminations beside it; the material is not stated anywhere, so it is a client question): negative.
3. Lengths: magnet 83.1 mm (BOM) and rotor stack 83.6 mm (BOM; 3.290 in on TM-2004/137 Fig. 9) against the
   model's 83.82 mm for both: negative.

Magnet circuit per pole, referred to the magnet face (revision 5's hand estimate, CALIBRATION_PLAN.md):
magnet t / mu_r = 6.5 / 1.129 = 5.757 mm in series with strip 0.30 mm and an effective gap G = 1.07 mm.
A parallel leakage permeance P_l on the load side lowers the useful flux by (P_l / P_load) * R_m / (R_m + R_load);
an added gap permeance dP raises it by (dP / P_gap) * R_gap / (R_m + R_load).

Run: python scripts/motor_end_effects.py   (no inputs; prints the band and writes nothing)
"""
from math import log, pi

L_MODEL = 83.82      # mm, the model's stack and magnet length
L_ROTOR = 83.6       # mm, rotor stack (BOM 83.6; Fig. 9: 3.290 in = 83.57)
L_MAGNET = 83.1      # mm, magnet length (BOM)
T_MAG, MU_R = 6.5, 1.129
STRIP, G = 0.30, 1.07          # mm, polymer strip and effective series gap (revision 5's hand estimate)
W_MAG, POCKET = 18.9, 6.80     # mm, magnet width, pocket thickness
GAP = 0.775                    # mm, drawing
POLES = 8
ROTOR_OD = 160.5

r_m = T_MAG / MU_R
r_load = STRIP + G
k_leak = r_m / (r_m + r_load)          # share of the circuit in the magnet
a_face = 2 * W_MAG                     # magnet face per pole (V of two magnets), mm (per mm of length)
p_load = a_face * L_MODEL / r_load     # load permeance per pole / mu0, mm


def semicircle_strip(boundary, sep, width):
    """Permeance / mu0 between two coplanar faces separated by sep, each width wide, along boundary (mm)."""
    return boundary / pi * log(1 + 2 * width / sep)


def band(low, high):
    return f"{min(low, high):+.2f} to {max(low, high):+.2f} %"


# 1. Gap fringing at both ends: quarter-circle paths from the rotor's end face to the stator tooth end faces.
pole_pitch = pi * ROTOR_OD / POLES
fringe = {}
for case, (arc_frac, kc, w) in {"low": (0.60, 1.10, 5.0), "high": (0.75, 1.05, 15.0)}.items():
    arc = arc_frac * pole_pitch
    g_eff = kc * GAP
    p_gap = arc * L_MODEL / g_eff
    dp = 2 * arc / pi * log(1 + pi * w / (2 * g_eff))   # both ends
    fringe[case] = 100 * (dp / p_gap) * (g_eff / (r_m + r_load))

# 2. Leakage across the pocket ends at both end faces (non-magnetic clamping piece).
leak = {}
for case, (extra, w) in {"low": (4.0, 6.0), "high": (8.0, 15.0)}.items():
    boundary = a_face + extra                 # both magnets plus the barrier ends
    p_l = 2 * semicircle_strip(boundary, POCKET, w)
    leak[case] = -100 * (p_l / p_load) * k_leak

# 3. Lengths: the model's magnet is 83.82 mm; the real magnet 83.1 mm. Low: magnet source alone; high: plus the
#    rotor stack (the bridges' fixed leakage scales with steel length, partly offsetting, so the band brackets).
length = {"low": -100 * (1 - L_MAGNET / L_MODEL) * 0.7, "high": -100 * (1 - L_MAGNET / L_MODEL)}

total_lo = fringe["high"] + leak["low"] + length["low"]
total_hi = fringe["low"] + leak["high"] + length["high"]

print(f"pole pitch {pole_pitch:.1f} mm, load permeance per pole {p_load:.0f} mm (x mu0), magnet share {k_leak:.3f}")
print(f"1. gap fringing          {band(fringe['low'], fringe['high'])}")
print(f"2. pocket-end leakage    {band(leak['low'], leak['high'])}")
print(f"3. magnet / stack length {band(length['low'], length['high'])}")
print(f"total (hand)             {band(total_lo, total_hi)}")
emf, ornl = 105.2, 89.38
for d in (total_lo, total_hi, -3.7):
    v = emf * (1 + d / 100)
    print(f"  at {d:+.1f} %: {v:.1f} V per 1000 rpm, {100 * (v / ornl - 1):+.1f} % on ORNL")

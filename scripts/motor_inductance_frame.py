"""Study 7, the inductance mismatch, step 1 (framing, no runs): revision 5's Ld / Lq against ORNL's "static
measurements" (TM-2006/423 p. 51: Lq 5 mH, Ld 1.92 mH; method, frequency, current and rotor positioning not stated).

    .venv/Scripts/python.exe scripts/motor_inductance_frame.py

1. Convention: any terminal convention scales both axes by one factor, so it cannot give Ld low and Lq high.
2. Split into the mean (Ld + Lq) / 2 and the saliency term (Lq - Ld) / 2.
3. Hand estimates of what the 2D model leaves out or defines differently:
   a. end-winding leakage (Pyrhonen, Design of Rotating Electrical Machines, eq. 4.80 form: L = (4 m / Q) mu0 l_w
      lambda_w N^2, lambda_w 0.2-0.5), from the efficiency study's turn length (408.8 mm) and the stack;
   b. small-signal (incremental) against secant inductance at zero current, from revision 5's saved fluxes;
   c. rotor misalignment in a static test: L_meas,d = Ld cos^2 e + Lq sin^2 e (and the reverse for q): the error e that
      would make the model read ORNL's Ld, and what it then gives for Lq.
"""
import math

MU0 = 4e-7 * math.pi
ORNL = {"Ld": 1.92e-3, "Lq": 5.0e-3}
MODEL = {"Ld": 1.72e-3, "Lq": 5.50e-3}             # revision 5, run 20261123-150432 (secant: 0 to -25 A; 6.25 A)
PSI_D = (0.14542, 0.10250, 0.06088)                 # psi_d (Wb, rms dq) at id 0 / -25 / -50 A, iq 6.25 A
LQ_AT = {6.25: 5.50e-3, 18.75: 5.43e-3}

print("1. convention: ORNL / model ratio  Ld %.3f, Lq %.3f  (opposite sides of 1: no single factor)" %
      (ORNL["Ld"] / MODEL["Ld"], ORNL["Lq"] / MODEL["Lq"]))
for name, L in (("ORNL", ORNL), ("model", MODEL)):
    print(f"2. {name:5s}: mean {(L['Ld'] + L['Lq']) / 2 * 1e3:.3f} mH, saliency term {(L['Lq'] - L['Ld']) / 2 * 1e3:.3f} mH")
print("   model against ORNL: mean %+.1f %%, saliency term %+.1f %%" % (
    100 * ((MODEL["Ld"] + MODEL["Lq"]) / (ORNL["Ld"] + ORNL["Lq"]) - 1),
    100 * ((MODEL["Lq"] - MODEL["Ld"]) / (ORNL["Lq"] - ORNL["Ld"]) - 1)))

# a. end-winding leakage
m, Q, N = 3, 48, 72
l_turn, l_stack = 0.4088, 0.08382
l_w = (l_turn - 2 * l_stack) / 2                    # one end, per conductor
for lam in (0.2, 0.5):
    L_ew = 4 * m / Q * MU0 * l_w * lam * N ** 2
    print(f"3a. end winding (lambda_w {lam}): {L_ew * 1e3:.3f} mH per phase, on both axes: "
          f"Ld {(MODEL['Ld'] + L_ew) / ORNL['Ld'] * 100 - 100:+.1f} %, Lq {(MODEL['Lq'] + L_ew) / ORNL['Lq'] * 100 - 100:+.1f} %")

# b. incremental at zero current (linear extrapolation of the two secants / the two Lq points)
s1, s2 = (PSI_D[0] - PSI_D[1]) / 25, (PSI_D[1] - PSI_D[2]) / 25
ld_inc = s1 + (s1 - s2) / 2
lq_inc = LQ_AT[6.25] + (LQ_AT[6.25] - LQ_AT[18.75]) / 2
print(f"3b. incremental at zero current: Ld {ld_inc * 1e3:.3f} mH ({ld_inc / ORNL['Ld'] * 100 - 100:+.1f} %), "
      f"Lq {lq_inc * 1e3:.3f} mH ({lq_inc / ORNL['Lq'] * 100 - 100:+.1f} %)")

# c. misalignment
s2e = (ORNL["Ld"] - MODEL["Ld"]) / (MODEL["Lq"] - MODEL["Ld"])
e = math.degrees(math.asin(math.sqrt(s2e)))
lq_mis = MODEL["Lq"] - (MODEL["Lq"] - MODEL["Ld"]) * s2e
print(f"3c. misalignment that reproduces ORNL's Ld: {e:.1f} deg electrical ({e / 4:.1f} deg mechanical); "
      f"Lq then {lq_mis * 1e3:.2f} mH ({lq_mis / ORNL['Lq'] * 100 - 100:+.1f} %)")

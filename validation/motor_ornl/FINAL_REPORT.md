# 2004 Prius traction motor: final report (study 7)

Closed 2026-11-24 with open items (the user's decision: there is no client to answer the remaining questions, so they
are listed as a client would receive them). Every number below has a case file with its predictions written before the
run, and a committed run report. The record of how the study got here: `RESULTS.md` (the blind pass),
`CALIBRATION_PLAN.md` (every revision and diagnostic), `STATUS.md` (short version), `CLIENT_DATA.md` (inputs).

## Summary

The motor was modelled in open-source tools (Pyleecan + FEMM 2D magnetostatics, a lumped thermal network, CalculiX for
rotor stress) from the data a client would hand over: ORNL's lamination drawing, the bill of materials (magnet size
and mass, winding), the measured magnet properties and the measured phase resistance. Nothing is fitted.

- **The model's magnet-driven flux is about 18 % above the measured motor's**, consistently: back-EMF +17.7 %,
  locked-rotor torque +17 to +19 % at almost every current, compared like for like.
- **The cause is very likely how fully the magnets are magnetised in the assembled rotor.** An independent second
  solver (ElmerFEM) reproduces the 2D field to 0.1 %; the lamination grade (at most 0.35 %) and 3D end effects
  (1.3-3.7 %) are too small; the magnets sit on the drawing's stops. ORNL's measured no-load air-gap flux density
  (TM-2004/137 Fig. 13) is the model's scaled down uniformly by 1.148 where the field is level, which is what a
  magnetisation shortfall does and what a geometry or leakage error does not. 14.8 % in the 2D gap field plus the end
  effects accounts for the 18 % in back-EMF. An effective remanence about 13-15 % below the re-saturated sample's
  would close it; it has not been fitted, because the client can settle it with one fluxmeter test.
- **The design verdicts on the client's data:** the rated torque and rated power hold, the continuous rating holds
  at the nominal housing fit, the open-circuit voltage at top speed and the rotor bridges at overspeed fail.

## Design verdicts (client data, uncalibrated: revision 5)

| Requirement | Result | Verdict |
|---|---|---|
| REQ-M1 open-circuit voltage at 6000 rpm <= 500 V (inverter fault) | 1002 V peak line to line (run 20261123-223450); ORNL measured 850 V | **Fail** on the model and on the motor itself: the inverter must hold the voltage down at speed |
| REQ-M2 400 N m within 25 A/mm2 (212 A rms) | 171 A cold, 177 A hot | **Pass** |
| REQ-M3 every operating point within 25 A/mm2 | above 212 A the density limit is exceeded | **Fail** above 212 A (a short-time rating) |
| REQ-M4 rotor bridges below yield at 7200 rpm (stand-in grade, 335 MPa) | 415.0 MPa (mesh uncertainty 1.5 %) | **Fail**, verified; elastic at 6000 rpm (about 288 MPa); a 412 MPa+ grade would pass |
| REQ-M5 rated 50 kW to 6000 rpm (500 V, 212 A) | 55.85 kW cold, 51.65 kW hot | **Pass** (cold verified) |
| REQ-TH1 25 kW continuous, 1250-6000 rpm (synthetic 65 C jacket) | 27.7 kW nominal; 24.0 kW at the loosest stator-to-housing fit | **Pass** nominal, **Fail** at the 0.08 mm interface gap |

Because the model's flux is high, the flux-dependent verdicts lean optimistic for torque per ampere and pessimistic for
open-circuit voltage; with the magnets' measured strength (once known) REQ-M5's margin would shrink (the calibrated
machine gave 48.0 kW cold).

## Against ORNL's tests (the validation limits agreed before any test data was seen)

| Test | Model (client data) | Limit | Verdict |
|---|---|---|---|
| Back-EMF per 1000 rpm, line to line | 105.2 V (mesh fineness 8, magnets at 25 C) against 89.4 V: +17.7 % (the tables' fineness-2 value at 20 C, 105.8 V, is +18.3 %) | 5 % | Fail |
| Locked-rotor torque, like for like | +17 to +19 % | 10 % | Fail |
| Motor efficiency, 393 points (median, hot) | 4.4 points high | 2 points | Fail; the gap is mostly the losses a motor-only model leaves out (mechanical, magnet eddy current, AC copper), not the flux (blind +24 % flux: 5.2 points) |
| No-load air-gap flux density (Fig. 13) | plateau 1.148 x ORNL's, uniform within 3.4 % | (diagnostic) | supports the magnetisation explanation |

## Open items: what the client would be asked

From `CLIENT_QUESTIONS.md`, in order of how much they could change the result:

1. **How are the rotor magnets magnetised in production, and to what fraction of saturation?** A fluxmeter test on one
   magnet out of the rotor (half a day) settles the 18 %.
2. Do the magnets sit on the drawn stops in production? (The drawing says yes; the air-gap field's uniform scaling
   agrees.)
3. What is the rotor's end clamping piece made of? (A steel piece would change the end effects.)
4. Which lamination grade is used? (Matters for iron loss and for REQ-M4; under 0.4 % on back-EMF.)
5. A Hall-probe scan of the no-load air-gap field on one motor (ORNL's Fig. 13 already does most of this job).
6. How were the static inductances measured? (The model's saliency differs by 23 %; the method decides whether that
   is the model.)

## Limits

- 2D electromagnetics; end effects estimated by hand (1.3-3.7 %), not modelled.
- Motor-only losses (copper and iron); no mechanical, magnet eddy-current or AC copper loss.
- Thermal: steady state, synthetic cooling, no thermal test data.
- Rotor stress: stand-in lamination grade, sharp pocket corners, no hub fit.
- Two weak spots of the tables, reported: the lowest q-axis row (iq 6.25 A and below) fails the dq-torque check, and
  the thermal network's hot-corner state at 5500 rpm in one cooling scenario has no fixed point (a real switch between
  two near-equal-loss operating points, confirmed on refined tables).

## Evidence

- Efficiency: runs `20261124-062847_motor_prius_efficiency_rev5` (and `_refined`), scored in
  `validation/motor_ornl/rev5_efficiency_vs_ornl.json`; tables `motor_prius_lut_*_rev5`.
- Thermal: `20261124-063338_motor_prius_thermal_rev5`; rotor: `20261124-063835_motor_prius_rotor_overspeed_rev5_mesh`.
- Back-EMF and torque: `motor_prius_rev5_*` runs; locked-rotor emulation `scripts/motor_locked_rotor.py`.
- The 18 % diagnosis: `CALIBRATION_PLAN.md` steps 1-5; Elmer check `validation/motor_ornl/elmer_check/`; Fig. 13
  comparison `validation/motor_ornl/fig13/fig13_comparison.json` (`scripts/motor_fig13.py`).

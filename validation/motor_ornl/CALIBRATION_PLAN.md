# Study 7, post-test revision: calibrate on back-EMF, predict the rest (plan, written 2026-11-22 ~19:30, before any
of it was computed)

The blind verdicts (`RESULTS.md`) stay as the record. This revision follows the user's rule (CLAUDE.md, "Use only
information a real project would have"): the back-EMF test is the routine first test on any existing motor, so it
may calibrate the model; ORNL's measured air-gap flux map (TM-2004/137 Fig. 13) is teardown-only and stays unopened.

## Calibration data
ORNL back-EMF, 89.78 V rms per 1000 rpm, read as line-to-line (see the protocol log). Our committed model gives
111.25 V line-to-line full-waveform rms (110.88 fundamental): the flux linkage must come down by the factor
k = 89.78 / 111.25 = 0.807.

## Two hypotheses, each made to match the back-EMF exactly
- **A, weaker magnets:** remanence scaled (models/motor/build_prius_ornl.py --br). Found by open-circuit runs at three
  remanence values and interpolation; then the MTPA torque curve in FEMM at the calibrated remanence (currents 25, 50,
  75, 100, 125, 150, 200, 250 A rms; interpolated between them).
- **B, fewer series turns:** turns x k with the same copper area per slot. Exact from the committed cold table: with
  turns scaled by k, flux linkage lambda_B(i) = k lambda(k i), torque T_B(i) = T(k i), resistance x k^2; the copper loss
  at a given torque is unchanged.

## Choosing between them (torque becomes calibration data)
At ORNL's seven locked-rotor currents (Fig. 3.10 values), under both current readings (peak: I / sqrt 2 rms; rms):
the hypothesis-and-reading pair with the smallest rms relative torque error is selected. Recorded as a choice made
with the data: after it, torque agreement is not evidence.

## The out-of-sample test
Motor efficiency at the 393 Table B-1 points, with the selected hypothesis, scored against the unchanged 2-point limit;
reported (a) as the model stands (motor-only: copper and iron) and (b) with the losses the efficiency study left out,
estimated only from information a real project would have: none is available here without new sources, so (b) is
reported as the size of gap the omitted losses would have to explain, not as a fitted correction.

## Predictions (before computing anything)
- B's torque: low at small currents and closer at large ones (T(k i) shifts the curve; ORNL's curve is flatter than
  ours): about -15 % at 50 A and within 5 % at 250 A with the peak reading; with the rms reading +20 to +30 % at 50 A.
- A needs a remanence of about 1.03 T (back-EMF falls about 1.14 % per 1 % of remanence, from the earlier scratch
  sensitivity), implausibly low for sintered NdFeB at 25 C: a hint toward B or a third cause, not proof. A's torque:
  about -15 to -19 % against our blind curve at low current, less at high current (saturation): within about 10 % of
  ORNL at every current with the peak reading.
- Selection: A with the peak reading, narrowly.
- Efficiency (out of sample): B leaves it within 0.5 point of the blind map below base speed (same copper loss for the
  same torque); A lowers it by 1-2 points at high torque (more current) and raises it slightly at light load (less iron
  loss). Either way the median gap stays 3-5 points: most of it is the omitted losses, not the flux.

## Results (2026-11-22 22:15; predictions above unchanged)
- **Back-EMF calibration** (`motor_prius_cal_oc_br`, run 20261122-192029): hypothesis A needs a remanence of
  **1.036 T** (16.6 % below the 1.243 T read from TM-2004/137 Fig. 14); predicted about 1.03 T. Hypothesis B needs
  the series turns x 0.807.
- **Selection on torque** (`motor_prius_cal_torque_br`, run 20261122-195712; `scripts/motor_calibration.py`,
  `calibration.json`): **A with the peak reading, rms error 8.7 %** (-3.6 % to +13.5 % over ORNL's seven currents);
  B 10.7 % (-17 % to +4 %); the rms reading is far worse for both (47 % and 31 %). As predicted, A narrowly. Three of
  the seven points remain outside the original 10 % band (high current), so even the calibrated model over-predicts
  torque at high current by 12-14 %.
- **Out-of-sample efficiency for A: not yet run.** It needs dq tables at 1.036 T (cold and hot, several hours of
  FEMM); B's is scored (median 5.3 points high, unchanged from the blind map's 5.2), which supports the prediction that
  most of the efficiency gap is the omitted losses, not the flux.

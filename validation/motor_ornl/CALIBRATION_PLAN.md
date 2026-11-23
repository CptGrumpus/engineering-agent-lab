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

## Revision (2026-11-22 ~22:30, user's go-ahead): re-decide A against B on a routine test, not on torque
Why: torque is the higher-value test and a weak discriminator here (8.7 % against 10.7 % rms); once used to choose it
stops being evidence. A real job would choose with the cheapest routine measurement that separates the hypotheses.
Phase resistance and inductance do: B (series turns x 0.807) scales every inductance and the resistance by
0.807^2 = 0.651; A (remanence only) leaves them unchanged apart from saturation. ORNL gives no measured resistance
(masked search of every ORNL document we hold). TM-2006/423 p. 51 (not yet opened; located with every digit masked)
states that "Lq is greater than Ld ... based on static measurements" with values in mH. Static inductance is a routine
client test (CLAUDE.md, realistic information).

Predictions, written BEFORE opening p. 51 (model values from the committed blind cold dq tables, runs
20261122-102002 and 133946; L = d(phi)/d(i) from the zero-current point, rms dq, i.e. per-phase synchronous values):
| | Ld (mH), low current (25 A rms) | Lq (mH), low current (6-12 A rms) | Lq at 100 A rms |
|---|---|---|---|
| A (remanence 1.036 T): about the blind values, within +-5 % (less magnet flux saturates the bridges a little less) | 1.70 | 5.38 | 2.67 |
| B (turns x 0.807): x 0.651 | 1.11 | 3.50 | 1.74 |
Reading rules, agreed before the page is read: (1) compare at the current the page states; if none, at low current
(a static LCR-type test); (2) if the page says line-to-line, compare with 2 x the per-phase values (A 3.40 / 10.8, B
2.22 / 7.0 mH); if it does not say, report both readings; (3) the hypothesis whose values are nearer on both Ld and Lq
in a reading the page supports is selected; if the readings disagree or the conditions make the 35 % gap unreadable,
neither is selected and both are carried as a band. Lq / Ld (3.2 in both) does not discriminate and is reported only.


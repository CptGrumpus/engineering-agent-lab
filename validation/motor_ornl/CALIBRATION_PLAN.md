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

### Result (2026-11-22 22:21; TM-2006/423 p. 51: Lq 5 mH, Ld 1.92 mH, "static measurements", no current or convention stated)
| Reading | Ld 1.92: A 1.70 / B 1.11 | Lq 5.0: A 5.38 / B 3.50 | Nearer on both |
|---|---|---|---|
| per-phase dq | A +13 %, B +73 % | A -7 %, B +43 % | **A** |
| line-to-line (measured / 2 per phase) | A -44 %, B -14 % | A -54 %, B -29 % | B (far from both) |
Rule 2 reports both readings; rule 3 selects in the reading the page supports: the page uses the values as Ld and Lq in
the dq torque equation, which defines them per phase. **Hypothesis A is selected on the static inductances.** Caveat,
stated: this rule was written after the torque scores were known (both rules pick A). With selection now on
inductance, A's torque against ORNL (rms error 8.7 %, -3.6 % to +13.5 %, three of seven points outside the original
10 % band) is reported as a comparison, with that caveat, not as a fit. Also reported: the measured saliency Lq / Ld is
2.6 against the model's 3.2 (Ld 13 % above the model): the d-axis path is not quite ours (the thinner 5.31 mm magnet
and its pocket clearance are the first suspect; not modelled). Next: the out-of-sample efficiency for A (dq tables at
1.036 T, cold and hot).

## Result: the out-of-sample efficiency test for A (2026-11-23 03:30; predictions in cases/motor_prius_efficiency_br.toml, b2d7092)
Four dq tables at 1.036 T (cold, hot and their low-q-current supplements; c6d39dc) and the efficiency case built from
them (run 20261123-032756_motor_prius_efficiency_br), scored once against ORNL's Table B-1 (`calibration.json`):

| | blind (1.243 T) | B (turns x 0.807) | **A (remanence 1.036 T)** |
|---|---|---|---|
| median efficiency, ours (hot) minus ORNL, over 393 points | 5.21 points | 5.32 | **4.50** |
| 10th-90th percentile | 3.4-7.9 | 3.4-8.3 | 2.9-7.7 |
| points within 2 points of our cold-hot band | 3 | 3 | 6 |

- The 2-point limit is still missed by a wide margin: A closes about 0.7 of the 5 points. This plan's prediction (the
  median gap stays 3-5 points, most of it the omitted losses) holds; the case's sharper prediction (the gap GROWS to
  5.5-7, because A raises our light-load efficiency) had the direction wrong.
- A design consequence nobody asked for, found by the same case: with A's weaker magnets, REQ-M5 (50 kW to 6000 rpm
  at 500 V and our 212 A design current) FAILS, 48.0 kW cold and 44.5 kW hot (blind model: 58.6 / 53.7). Less magnet
  flux means less torque per ampere in field weakening. The verdict was flux-dependent all along.
- The case's verification failed: my back-EMF reference came from a different mesh (fineness 8, not the tables' 2:
  0.1 % apart, as expected); the half-table iron-loss check misses 5 % (6.9 / 7.5 %); the unresolved 10 N m row
  trips the map check cold instead of hot. None of these touches the comparison above, which uses the full tables.
- What remains: the efficiency gap is mostly losses the model leaves out (mechanical, magnet eddy-current, AC copper),
  which no routine client data here would size; and the d-axis saliency (2.6 measured against 3.2).

## Revision 2 (2026-11-23 ~10:55): the no-load (spin) loss test as calibration data, then efficiency again
*Why:* revision 1's efficiency gap (median 4.5 points, hypothesis A) is mostly losses the model leaves out: friction,
windage and oil drag, magnet eddy currents, iron loss above the datasheet value. A no-load spin-loss test sizes them
together and is routine for a motor supplier, so a contractor would have it (user's standing rule, 2026-11-23: "as long
as we expect this information to be available from a contractor for the work, then we can assume we can use it").
*Data:* ORNL/TM-2006/423 sec. 3.2.3, Table 3.7 "Summary of hybrid drive system losses", column "Motor-Rotor Losses, W"
against motor-shaft speed (12 rows, oil near room temperature): configuration A (real rotor) minus configuration B (a
dummy shaft on bearings), windings not energised. Located by a masked text search (every digit replaced) at 10:45; the
method text was read masked; no number in the table has been read. Declared: the masked layout shows the column's
digit counts, two before the decimal point in the first row and three from the fourth row (10-99 W, then 100-999 W).
*Caveats (stated before opening):* the spin test ran in the transaxle with oil at room temperature; the efficiency
test (Table B-1) ran the motor in its own casing with transmission oil, the rotor coupled straight to the dynamometer,
coolant 35 C (some points much colder) and the stator often hot. Oil drag and bearing friction transfer only roughly.
*Model value (computed before opening, committed cold dq table of hypothesis A, run 20261122-222259, id = iq = 0,
stator + rotor):* open-circuit iron loss 15 / 35 / 61 / 92 / 167 / 262 / 374 / 505 W at 500 / 1000 / 1500 / 2000 /
3000 / 4000 / 5000 / 6000 rpm (the blind machine: 22 / 52 / ... / 743 W; less magnet flux, less iron loss).
*Method (fixed before opening):* residual R(n) = measured motor-rotor loss - model open-circuit iron loss, signed, at
the table's speeds; linear interpolation in speed; beyond the table's range a least-squares R = a n + b n^2. Two
readings of what R is, since one test cannot separate them: (a) additive, load-independent (friction, drag): add R(n)
to every map point's loss; (b) multiplicative, an iron-loss factor k(n) = measured / model applied to the map's iron
loss at load. The operating point does not change in (a) (a constant per speed); in (b) it is re-optimised. Score
hypothesis A's hot and cold maps at the same 393 Table B-1 points, same 2-point limit, once, as revision 2.
*Predictions (before opening):*
- P1 The measured motor-rotor loss exceeds our open-circuit iron loss at every speed from 1000 rpm, by a factor 1.3-2.5
  at the top test speed (iron above datasheet: punching, harmonics; plus friction and oil drag; magnet eddy small).
- P2 Revision 2, reading (a): median gap (hot minus ORNL) falls from 4.50 to 3.0-4.0 points; reading (b) within 0.5
  point of (a). The 2-point limit still FAILS. Light-load, high-speed points improve most.
- P3 The residual R grows faster than linearly with speed (b > 0).

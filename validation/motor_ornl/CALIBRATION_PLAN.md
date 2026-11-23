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

## Revision 2 (2026-11-23 ~10:30; time corrected from '~10:55'): the no-load (spin) loss test as calibration data, then efficiency again
*Why:* revision 1's efficiency gap (median 4.5 points, hypothesis A) is mostly losses the model leaves out: friction,
windage and oil drag, magnet eddy currents, iron loss above the datasheet value. A no-load spin-loss test sizes them
together and is routine for a motor supplier, so a contractor would have it (user's standing rule, 2026-11-23: "as long
as we expect this information to be available from a contractor for the work, then we can assume we can use it").
*Data:* ORNL/TM-2006/423 sec. 3.2.3, Table 3.7 "Summary of hybrid drive system losses", column "Motor-Rotor Losses, W"
against motor-shaft speed (12 rows, oil near room temperature): configuration A (real rotor) minus configuration B (a
dummy shaft on bearings), windings not energised. Located by a masked text search (every digit replaced) at about 10:28 (corrected from '10:45'); the
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

### Result (Table 3.7 opened 2026-11-23 10:32, once; `scripts/motor_noload.py` -> `noload_revision2.json`)
Only the speed and motor-rotor columns were transcribed (`tm2006_423_table_3_7.csv`).

| Motor speed, rpm | 494 | 1000 | 1506 | 1991 | 2501 | 3007 | 3501 | 3999 | 4505 | 4999 | 5492 | 6006 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Measured motor-rotor loss, W | 19.8 | 31.6 | 60.2 | 109.0 | 135.9 | 161.7 | 205.3 | 242.1 | 297.4 | 323.9 | 404.9 | 472.8 |
| Model open-circuit iron loss, W | 14.7 | 35.5 | 61.6 | 91.3 | 127.4 | 168.1 | 212.4 | 261.6 | 316.3 | 374.2 | 436.3 | 505.8 |
| Measured / model | 1.35 | 0.89 | 0.98 | 1.19 | 1.07 | 0.96 | 0.97 | 0.93 | 0.94 | 0.87 | 0.93 | 0.93 |

- **P1 MISSED.** The measured no-load loss matches the model's open-circuit iron loss (0.87-1.35, and 3-13 % BELOW it
  from 3000 rpm), although it also contains the rotor's oil drag. The model does not underestimate the no-load loss.
- **P2 MISSED.** Median efficiency gap (hot minus ORNL, 393 points): revision 1 4.496 (reproduced exactly), revision 2
  4.479 (additive) and 4.461 (multiplicative), not 3.0-4.0. Within 2 points of the cold-hot band: 6 -> 7 points. The
  2-point limit still FAILS.
- **P3 MISSED.** The residual is small and falls with speed (R = 0.0049 n - 2.06e-6 n^2 W, b < 0).
- **What it shows.** The 4.5-point gap is load-dependent. Diagnostic on the already-open Table B-1 (ORNL's loss
  minus ours, hot map, medians per bin): about 0.2-0.3 kW at 500-1500 rpm below 100 N m, 1.9 kW at 200-400 N m;
  1.9-2.8 kW at 4500-6000 rpm below 100 N m. A least-squares split over all points: missing = 0.50 x our copper loss
  + 3.8 x our iron loss at load - 263 W. Candidates: copper loss about 1.5x ours (winding hotter than the assumed 100 C:
  Table B-1 records the stator temperature; end-winding length; the DC resistance is not reported); load-dependent
  iron and magnet losses the 2D sinusoidal-current model leaves out (PWM ripple from the inverter, field-weakening
  harmonics, magnet eddy currents under armature reaction). AC strand effects are small (0.91 mm strands, skin depth
  about 3.3 mm at 400 Hz).

## Revision 3 (2026-11-23 ~10:37; time corrected from "~10:50"): each test point's measured winding temperature
*Why:* revision 2 left the gap load-dependent, with copper loss about 1.5x ours at the hot, high-torque points. The
efficiency maps assume one winding temperature (100 C hot, 20 C cold); ORNL recorded the stator-winding temperature
at every Table B-1 point. Using a test's measured operating condition as an input matches conditions; the measured
efficiencies stay unused until the score.
*Transcription repair (found while preparing this; no new data opened, Table B-1 was opened 2026-11-22 18:48):* the
committed `tm2006_423_table_b1.csv` had the stator temperature empty in all 428 rows and, in 345 rows, the dc voltage
in the `v_ph` column and `i_ph` empty (the parser shifted columns where three rows lack the dc current). None of these
columns was used in any score. Rebuilt by matching each row to the report text on its dc, mechanical and ac powers
(428 of 428 unique); the scored columns (speed, torque, efficiencies, powers) are unchanged, checked row by row;
`v_dc` and `i_dc` added. Every row's speed x torque matches its mechanical power within 2 % (it always did).
*Method:* as revision 1 (hypothesis A, committed dq tables, same 393 points, same 2-point limit), but the phase
resistance at each point is R20 (1 + 0.00393 (T_winding - 20)) with ORNL's measured T_winding, in both scenarios; the
scenarios then differ only in magnet temperature (20 C or 80 C tables). Operating points re-optimised. Reported also
with revision 2's additive no-load residual.
*Predictions (before computing):*
- P1 Median gap (hot magnets minus ORNL) 4.3-4.7 points (median winding temperature 108 C, about the assumed 100 C):
  the hot points (150-207 C) improve, the cool ones (43-80 C) get slightly worse. Still FAIL.
- P2 In the 500-1500 rpm, 200-400 N m bin (windings mostly 130-200 C), the missing loss falls by 20-40 %.

### Result (computed once, 2026-11-23; `scripts/motor_noload.py` -> `noload_revision2.json`, keys rev3_*)
- **P1 MISSED, in the good direction.** Median gap 4.50 -> **4.05 points** (predicted 4.3-4.7); with revision 2's
  no-load residual 4.03. 10th-90th percentile 2.7-7.0 (was 2.9-7.7). Points within 2 points of the band: 6 -> 14 of
  393. The median moved more than the median temperature suggested because the points with most copper loss are the
  hot ones. The 2-point limit still FAILS.
- **P2 HELD.** Missing loss at 500-1500 rpm, 200-400 N m (79 points): 1918 -> 1429 W, -25 %.
- **What is left:** about 4 points, growing with speed at load. Copper is now at the measured temperature; the rest
  points at load-dependent iron and magnet losses the 2D model with sinusoidal currents leaves out: the inverter's PWM
  ripple (switching frequency is routine inverter data), field-weakening harmonics, magnet eddy currents. Sizing them
  needs a PWM-current time-stepping model: a separate piece of work, scoped before starting.

### Diagnostic after revision 3 (2026-11-23 10:52; documentation only, nothing fed back into the model)
User's rule, 2026-11-23: any ORNL data may be opened; only what a real job would provide may be used in the model.
Table B-1 also records the phase current at each point (rms, average of three phases; column rebuilt above). At the
same speed and torque, ORNL's motor drew **6-30 % more current than our model's loss-optimal point** (median 1.11;
about 1.06-1.13 below 2500 rpm, 1.22-1.30 above 3500 rpm). The copper loss of that extra current, 3 R (I_ORNL^2 -
I_ours^2) at the measured winding temperature, is **43 % of the missing loss** over all 393 points and about three
quarters of it at 500-1500 rpm, 200-400 N m (1053 of 1429 W). So much of the efficiency gap is torque per ampere, not
an omitted loss term: the model makes its torque with too little current. That agrees with the static inductances
(measured saliency Lq / Ld 2.6 against the model's 3.2: less reluctance torque in the real machine) and with the
locked-rotor torque (A's torque 3.6 % low to 13.5 % high). The rest of the gap (about 57 %) grows with speed: iron and
magnet losses at load, PWM.
*Next (revision 4, design data only):* the model's magnet fills the 6.80 mm pocket (Pyleecan's HoleM50 cannot leave a
gap); ORNL's design report (TM-2004/120) gives the magnet as 19.24 x 5.31 mm, so the pocket holds about 1.5 mm of air.
That changes the magnet's working point, the d-axis path (Ld) and the leakage through the bridges. A drawing a client
would provide; it was set aside on 2026-11-21 for a 0.4 % back-EMF estimate, which did not look at inductance.

## Revision 4 (2026-11-23 10:56, before any computation): the magnet at its design size, no calibration
*Why:* every model so far fills the 6.80 mm V pocket (ORNL/TM-2005/33 Fig. 21, measured) with magnet (Pyleecan's
HoleM50 cannot leave a gap), 18.9 mm wide. ORNL's design report (TM-2004/120 Table 5.3, re-downloaded 2026-11-23,
sha256 6548edc4...) gives the magnet as 5.31 mm thick, 38.48 mm for the pair (19.24 each), with the same bridge
(1.45 mm), stack (83.57 mm) and turns (9 per coil, one layer) as ours. A drawing a client would provide. Set aside on
2026-11-21 on a scratch estimate of -0.4 % back-EMF: that estimate thinned the POCKET with the magnet (no air). A
5.31 mm magnet in the drawn 6.80 mm pocket leaves about 1.5 mm of air (or glue: magnetically the same) in series
with the magnet face, which a magnetic-circuit estimate puts at about -25 % on the magnet flux: the size of the blind
model's error, which revision 1 absorbed into the remanence (1.243 -> 1.036 T).
*Hypothesis:* the blind flux error is the magnet geometry, not the magnet material. Test it with the material as
measured (ORNL/TM-2004/137 Fig. 14: Br 1.243 T, recoil permeability 1.129, as the blind model) and NO calibration.
*Model:* Pyleecan HoleUD from the HoleM50 pocket (convert_to_UD): each magnet rectangle replaced by a 19.24 x 5.31 mm
magnet and an air strip, three placements bracketing the unknown fit: against the outer (air-gap side) face, centred,
against the inner face. Same stator, steel (M330-35A), mesh fineness 8, open circuit at 1000 rpm.
*Magnetic-circuit estimate (per magnet, flux = (Br t / mu_r) / (t / (mu_r A) + air strip / A + gap reluctance), less a
saturated-bridge leakage of about 2.6 T mm):* blind geometry 17.5 Br; design magnet without air 17.4 Br (-0.4 %, the
old scratch); design magnet with the 1.49 mm strip 13.5 Br; useful flux ratio about 0.74.
*Predictions:*
- P1 Back-EMF at Br 1.243 T: 75-95 V rms line-to-line per 1000 rpm on every placement (estimate about 82; the blind
  model 110.9; ORNL measured 89.78). If it lands within 5 % of 89.78 (85.3-94.3), the geometry explains the blind
  miss without touching the material.
- P2 The placement moves the back-EMF by under 3 % (the strip is in series wherever it sits; only the bridge
  saturation pattern shifts).
- P3 Ld changes by under 5 % from the blind model's (the magnet plus strip present about the same air-equivalent
  thickness, 6.19 against 6.02 mm), so revision 4 does NOT fix the saliency (2.6 measured against 3.2): the
  torque-per-ampere gap stays for a later revision.
*Then, if P1 holds:* the design-magnet machine at Br 1.243 T replaces hypothesis A (remanence 1.036 T) as the
calibrated model; static inductances, locked-rotor torque, efficiency and the design verdicts are re-run on it, each
with predictions first.
*Addendum (2026-11-23 12:05, time corrected from "11:05"; user's decision "Run 1.12 T too"; written before the 1.243 T result was read):* carry
both remanence sources until the data decides: ORNL's measured sample curve (TM-2004/137 Fig. 14, 1.243 T) and the
design report's value (TM-2004/120 Table 5.4, "Magnet strength 1.12 T"), set aside on 2026-11-21 as "probably a hot
value" without a check. The same three placements at 1.12 T.
- P5 Back-EMF at 1.12 T = 0.88-0.89 x its value at 1.243 T, placement by placement (the calibration runs showed about
  1.2 % of back-EMF per 1 % of remanence near 1.0 T; 1.12 / 1.243 = 0.901); 66-85 V per 1000 rpm on P1's band.

### Source check on revision 4's geometry (2026-11-23 12:24): the sources disagree on the air layer (its reading of 1.12 T is corrected at 13:32, below)
Revision 4 combines two hardware sources: the lamination drawing (TM-2005/33 Fig. 21: the punched pocket, 6.80 mm,
measured on 8 poles) and the magnet size in the design report (TM-2004/120 Table 5.3: 5.31 mm). But the same design
report's own model sketch (Fig. 5.2) and its Flux2D flux map (Fig. 5.10, p. 37) draw the magnet FILLING its pocket,
and its lumped model ran at 1.12 T, below the 1.243 T measured on a sample: ORNL's parametric model looks like the
same simplification ours made (pocket = magnet), compensated with a lower remanence. A schematic of a parametric
model is weaker evidence about the hardware than a lamination drawing, so revision 4 remains the better-supported
reading, but it is a hypothesis, not a finding, until a lamination drawing and a magnet drawing (or the magnet
retention method: adhesive, resin, a spring) settle whether 1.5 mm of non-magnetic material really sits in series
with each magnet. On a real job that is one question to the client. Carried as a model-form bracket alongside the
placement: pocket filled (the blind geometry, 110.9 V) against magnet plus air (79-85 V).

### Source found: the magnets are polymer-moulded (2026-11-23 12:28; supersedes the 12:24 note's open question)
User, 2026-11-23 ~12:27: if a client would know it, look for it in the literature and use it. ORNL's teardown report
(TM-2004/137, Hsu, Ayers and Coomer, July 2004, Pub57348.pdf, sha256 32469ab0...; the report whose Fig. 14 gave the
magnet B-H line), p. 9-10: "the magnets are molded with a polymer that enables the final sizing of the PMs to be
inexpensively honed to the correct dimensions and shapes for the final assembly ... The PMs with the polymer coating
are inserted into the slots of the rotor core" (Figs. 10-12; the photo shows the 2004 magnets in a white polymer frame,
face width about 19-20 mm on the ruler, matching 19.24 mm). A magnet drawing or supplier spec would state this, so a
client would have it. So the non-magnetic layer is real: a 5.31 mm magnet in a polymer shell sized to the 6.80 mm
pocket. ORNL's parametric model (TM-2004/120 Figs. 5.2, 5.10), which fills the pocket, simplified it away.
*Placement:* a moulded shell is most naturally symmetric, about 0.75 mm of polymer on each face: the CENTRED placement
is the primary model (back-EMF 82.37 V per 1000 rpm, -7.8 % on ORNL, uncalibrated). Outer and inner stay as the bounds
of an asymmetric shell (85.31 / 79.26 V). Chosen on the design information, not on the back-EMF match (the outer
placement matches better; choosing it for that would be calibration).
*Logged:* reading p. 11's text also printed the axis labels of Fig. 13 (the measured air-gap flux, teardown-only);
no data values, and nothing of it is used.

### Result of P5 (2026-11-23 13:15; run 20261123-120639_motor_prius_rev4_oc_br112, case motor_prius_rev4_oc_br112.toml)
VERIFICATION PASS, 15/15 checks. Back-EMF fundamental, V rms line-to-line per 1000 rpm, at 1.12 T: outer 75.17,
centre 72.58, inner 69.81; ratio to 1.243 T 0.881 on every placement. **P5 held** (each value inside its band, at the
low end). Against ORNL's test (about 89.38 V as a fundamental): -15.9 / -18.8 / -21.9 %, against -4.6 / -7.8 / -11.3 % at
1.243 T. Peak at 6000 rpm 726 / 701 / 672 V: REQ-M1 still fails on every placement (limit 500 V; ORNL measured 850).

*What it decides:* the drawn magnet (in its polymer shell) at 1.12 T misses the test by 16-22 %; at 1.243 T by 5-11 %.
The measured sample remanence stays the primary value. Neither run is calibrated; the 1.12 T run is not used to tune
anything.

### Correction to the 12:24 note: what ORNL's 1.12 T is (2026-11-23 13:32; source check after the run)
The 12:24 note read ORNL's 1.12 T as a lower remanence that compensates a magnet filling its pocket. That was an
inference about intent from a sketch, and the report's own definitions point elsewhere:
- TM-2004/120 Table 5.4 (sha256 6548edc4...) lists "Magnet strength, Tesla", abbreviation **BrT**, 1.12, as an
  input to the SPEED lumped-parameter model (SPEEDCAD), the same value for the low- and high-speed cases, and again for
  the second IPM design in Sect. 5.5.
- The report's Appendix D, Table D.2 (SPEEDCAD magnet parameters) defines **Br** as the "magnet remanence at 20 C",
  with separate temperature coefficients for Br and HcJ. BrT is not in that partial list; in SPEED's naming, a T
  suffix marks the value at the magnet's working temperature. Not confirmed from the report itself.
- The report's NdFeB temperature coefficient (Table 5.2) is -0.1 %/C; 1.243 T at 20 C becomes 1.12 T at about 119 C.
  The same report's stator winding temperature tests (p. 71: chiller at 23 C) expected the rotor
  above 90 C. The build script already called 1.12 T "probably a hot value" (2026-11-21), unchecked until now.
**Reading now:** 1.12 T is most likely ORNL's hot design value for the same material, not a calibration. ORNL's design
study is not "wrong": it is a parametric design tool (lumped model plus Flux2D) for a design-trend report, not a
model validated against the Prius tests, and it simplifies the pocket the way our blind model did. Whether its filled
pocket at a hot 1.12 T happened to give the right cold back-EMF is not checked here (its back-EMF output is not used).
What stays open: (1) the temperature of the 1.243 T sample curve (not stated; taken as 20 C) and of ORNL's back-EMF
test (not stated; the test is a routine room-temperature spin); (2) the extrapolation of the sample curve to H = 0
(measured points span -7.2 to -4.7 kOe). Both move the primary back-EMF by a few percent.
*Hot-magnet use of the 1.12 T run:* if 1.12 T is the value at about 120 C, this run is the hot-magnet back-EMF on the
revision-4 geometry (useful for the hot efficiency and REQ-M5 checks later; REQ-M1's worst case is the cold magnet).

## Revision 4 overturned by the client's data (2026-11-23 13:55; see CLIENT_DATA.md)
From about 13:50 the study runs as a regular client project (user's decision): the client data pack is collected first.
ORNL/TM-2010/253 (Burress et al., 2011) Table 2.7 gives the 2004 Prius magnet as 83.1 x 18.9 x 6.5 mm, 10.2 cm3,
77 g (bare NdFeB density 7.55 g/cm3; a 5.31 mm magnet would need 9.1 g/cm3), 16 magnets, 1.232 kg. Revision 4's
5.31 mm came from ORNL's design-study model (TM-2004/120 Table 5.3, SPEED's LM), not the hardware. The 1.5 mm
non-magnetic layer does not exist; about 0.3 mm of polymer does. Revision 4's finding ("the drawn magnet explains most
of the blind miss") is withdrawn; its runs stay as the record of a model built on a wrong input. The same report's
Fig. 2.72 measures the 2004 Prius magnet at 1.255 T (20 C), about -0.10 %/C: our 1.243 T was right, and 1.12 T is the
magnet at about 125 C. With every client input now measured and matching, the blind geometry's +24 % is a model-form
or manufacturing gap. Next: revision 5 (the client-data model) with predictions, then the candidate causes one at a time
(STATUS.md).

## Revision 5 (2026-11-23 14:16, before any computation): the client-data model
*Why:* the client data pack (CLIENT_DATA.md) measures every input a client supplies: magnet 83.1 x 18.9 x 6.5 mm,
remanence 1.255 T at 20 C (-0.10 %/C), winding, stack, stator geometry and copper (masses agree), the test at 25 C.
*Model:* revision 4's HoleUD construction with the measured magnet, centred in the drawn 6.80 mm pocket (0.15 mm of
polymer each side), Br 1.255 T at 20 C, alpha -0.10 %/C, magnet at 25 C; air gap 0.775 mm (drawing) and 0.730 mm (BOM).
Machines: build_prius_ornl.py --client-magnet centre [--airgap-mm 0.73]; case cases/motor_prius_rev5_oc.toml.
*Hand estimate (made before the run):* on a fixed geometry EMF = a Br - b, the bridges saturated so b does not scale
with Br. Revision 4's two remanences (82.37 V at 1.243 T, 72.58 V at 1.12 T) give a = 79.6 V/T, b = 16.6 V. With the
same b, the blind geometry has a = 102.5 V/T. Scaling a by magnet width x (t/mu_r) / (t/mu_r + strip + G) between the
blind and revision-4 geometries fixes an effective series gap G = 1.07 mm. Revision 5 (t 6.5 mm, strip 0.30 mm):
a = 97.5 V/T, Br(25 C) = 1.2487 T, EMF = 105.2 V; at the 0.730 mm gap (G about 0.05 mm smaller) 106.1 V.
*Predictions:*
- P1 Gap 0.775 mm: 103-108 V rms line to line per 1000 rpm (+15 to +21 % on ORNL's 89.38).
- P2 Gap 0.730 mm: 0.5-1.5 % above P1's value.
- P3 The client data does NOT close the gap: both outside +-5 %. The cause is then model form or manufacturing.
- P4 Peak at 6000 rpm 980-1060 V; REQ-M1 FAIL (ORNL measured 850 V).
- P5 Every point check passes; 35-60 min.

### Revision 5, static inductances (2026-11-23 14:18, predictions before the run; case motor_prius_rev5_inductance.toml)
Small dq table on the revision-5 machine (centred, 0.775 mm gap), id 0 / -25 / -50 A, iq 6.25-18.75 A rms, magnets at
25 C; Ld and Lq per phase (rms dq) from the low-current points, as the blind values (1.70 / 5.38 mH).
- P1 Ld 1.62-1.78 mH: 7-16 % below ORNL's 1.92 (revision 5's d-axis air-equivalent 6.06 mm against the blind 6.02).
- P2 Lq 5.1-5.6 mH: 2-12 % above ORNL's 5.0.
- P3 Lq / Ld 3.0-3.4 against 2.6: the d-axis gap remains.
- P4 Checks pass; 20-45 min. Runs after the revision-5 open-circuit case (one FEMM at a time).

### Result of revision 5 (2026-11-23 15:04; run 20261123-141642_motor_prius_rev5_oc)
VERIFICATION PASS. Back-EMF 105.2 V (gap 0.775 mm) and 106.1 V (gap 0.730 mm) per 1000 rpm, line to line: +17.7 % and
+18.7 % on ORNL. Every prediction held; P1 and P2 landed on the hand estimate to 0.1 V. Peak at 6000 rpm 998.5 / 1010 V
(REQ-M1 FAIL; ORNL 850). **The client's data does not close the gap.** Every input a client supplies is now measured
and in the model, so the remaining 18 % is model form or manufacturing. Candidates, each to be tested on its own:
(a) magnetisation level in the assembled rotor (the 1.255 T is a re-saturated sample); (b) 3D end effects; (c) an
independent check of the 2D field. No calibration: the model is reported as it stands, +18 % on back-EMF.

### Diagnostic: ORNL's back-EMF and ORNL's low-current torque disagree (2026-11-23 15:07; hand calculation, no new run)
dq torque at the best current angle, T = 1.5 p (psi iq + (Ld - Lq) id iq), p = 4, with ORNL's static inductances
(Ld 1.92, Lq 5.0 mH), at ORNL's locked-rotor currents read as peak (TM-2004/185: phase currents Ia, -Ia/2, -Ia/2):
| Current (A peak) | ORNL measured | ORNL's back-EMF flux (0.1742 Wb) | Revision 5's flux (0.2051 Wb) |
|---|---|---|---|
| 50 | 74 N m | 65.3 (-11.7 %) | 73.5 (-0.7 %) |
| 75 | 118 N m | 113.2 (-4.0 %) | 125.0 (+5.9 %) |
Above 75 A constant inductances overstate the reluctance torque (saturation; the model's own Lq falls from 5.4 to
2.7 mH by 100 A rms), so only the low-current points carry information. At 50 A, where saturation matters least, ORNL's
back-EMF flux with ORNL's inductances is 12 % short of ORNL's torque; ORNL's back-EMF would need Lq - Ld = 4.5 mH
there (static: 3.08 mH, and inductances fall with current, they do not rise). The revision-5 flux reproduces the
50 A torque within 1 %. Reading: ORNL's two tests do not agree with each other at low current by about the size of
the model's back-EMF excess. This does NOT show that the back-EMF test is wrong (ORNL's report says ANL's back-EMF data
agree with it; the static inductances' current and convention are not stated), but it means the +18 % cannot be
called model error with confidence. The FEMM torque of revision 5 at 50 and 75 A is the next check (case
motor_prius_rev5_torque.toml, predictions before the run).

### Result of revision 5's static inductances (run 20261123-150432, ended 15:10)
VERIFICATION PASS. Ld 1.72 mH (ORNL 1.92: -10.6 %), Lq 5.50 mH (ORNL 5.0: +10 %), Lq / Ld 3.20 (ORNL 2.6). P1-P3 held:
the client data leaves the inductances where the blind model had them (1.70 / 5.38). FEMM's torque at ORNL's
locked-rotor currents (case motor_prius_rev5_torque, running) is the next comparison.

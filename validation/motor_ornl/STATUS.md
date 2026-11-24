# Study 7 (2004 Prius motor against ORNL's tests): where it stands

Updated 2026-11-24 06:42 (time from `date`). Since about 13:50 the study runs as a **regular client project**
(user's decision): every piece of information a client would hand over is collected in `CLIENT_DATA.md` and used as
input; what the job must predict (torque, efficiency) stays a validation target. The record of earlier steps:
`RESULTS.md` (the blind pass), `CALIBRATION_PLAN.md` (revisions 1-4, predictions before each run), `DRAWING_AUDIT.md`.

## What the blind pass was for, and why it has ended

The blind pass measured how far a model built from drawings alone can be trusted before any test data (+24 % on
back-EMF, +5 points on efficiency), and it exposed process faults that open data would have hidden: a template that
silently filled the magnet pocket, a flawed estimate used to dismiss a source, and a calibration that made back-EMF
match while hiding the error in torque and efficiency. Those lessons are in the project skills. Its cost: it held back
data a client gives on day one, so later revisions guessed values that should have been looked up. Revision 4 is the
clearest case (below).

## Back-EMF, every model so far

Line-to-line, V rms per 1000 rpm, fundamental. ORNL's test: 89.78 V full waveform, about 89.38 V fundamental
(room temperature, power meter, line to line: settled in `CLIENT_DATA.md`).

| Model | Magnet | Remanence | Back-EMF | Against ORNL | Status |
|---|---|---|---|---|---|
| Blind (2026-11-21) | 18.9 x 6.80 mm, fills the pocket | 1.243 T | 110.9 | +24 % | closest to the measured hardware |
| Revision 1 | fills the pocket | 1.036 T (fitted) | 89.4 | 0 % by construction | calibration; withdrawn as a model |
| Revision 4, centred | 19.24 x 5.31 mm + 1.5 mm non-magnetic layer | 1.243 T | 82.4 | -7.8 % | **overturned**: the magnet is 6.5 mm thick |
| Revision 4 at 1.12 T | same | 1.12 T | 72.6 | -18.8 % | 1.12 T is the magnet at about 125 C |
| **Revision 5 (client data)** | 18.9 x 6.5 mm centred, 0.15 mm polymer each side | 1.255 T at 20 C, magnet at 25 C | **105.2** (gap 0.775) / 106.1 (gap 0.730) | **+17.7 / +18.7 %** | the client's dimensions, masses, magnet data and tests in the model; predicted to 0.1 V |

## What the client data settled (2026-11-23 13:55)

- **Magnet: 83.1 x 18.9 x 6.5 mm, 77 g each** (ORNL/TM-2010/253 Table 2.7; size, volume and mass agree). Revision 4
  used 5.31 mm from ORNL's design-study model, which is not the hardware. Its "geometry explains the miss" is wrong.
- **Magnet material: 1.255 T at 20 C, about -0.10 %/C** (measured on a 2004 Prius magnet, TM-2010/253 Fig. 2.72).
  Our 1.243 T was right within 1 %.
- **Winding, stack, stator geometry, copper mass**: all match the model.
- **Phase resistance: 69 mOhm at 21 C measured**; our computed 59.6 mOhm was 14 % low. The measured value is used
  from now on.
- **Air gap: 0.73 mm** in the BOM against 0.775 mm from the drawing: a band to carry.

So with the client's own data the model sits near the blind geometry and reads about 20 % high on back-EMF, and the
cause is **not** in any input a client supplies. Is ORNL wrong? No: the test is a careful room-temperature
power-meter measurement, and ORNL's design-study model (filled pocket, 1.12 T hot) is a design tool, not a claim about
this motor's back-EMF.

## Where the 18 % stands (2026-11-23 20:52)

Ruled out: the solver (an independent ElmerFEM model agrees to 0.1 %), the lamination steel (at most 0.35 %), the
measurement side, and every client input already used. Bounded: 3D end effects, 1.3-3.7 %. Left, in order
(CALIBRATION_PLAN step 4): the drawing's magnet stops were measured at 21:23 and the model already puts every
magnet on them (pockets within 0.075 mm), so the leading hypothesis is the magnetisation level in the assembled
rotor (88-90 % of the re-saturated sample; settled by a fluxmeter test on one magnet). Questions for the client: `CLIENT_QUESTIONS.md`.

## Closed (2026-11-24): final report `FINAL_REPORT.md`

The study is closed with open items (the user's decision). ORNL's measured no-load air-gap field (TM-2004/137 Fig. 13,
step 5 of the plan) is the model's scaled uniformly by 1.148 on the plateau: the 18 % is a magnetisation shortfall in
all likelihood (14.8 % in the 2D gap field plus 1.3-3.7 % end effects), to be settled by the client's fluxmeter test.

## Design checks and efficiency on the client-data model (2026-11-24)

All on revision 5, uncalibrated, with the measured phase resistance (69 mOhm at 21 C). Predictions in each case header.

| Check | Revision 5 | Earlier (blind / calibrated) | Case, run |
|---|---|---|---|
| Efficiency map, peak | 97.22 % cold, 96.87 % hot | 97.41 / 97.05 blind | `motor_prius_efficiency_rev5`, 20261124-062847 |
| Against ORNL Table B-1 (393 points), median hot minus ORNL | **+4.37 points** (p10-p90 2.8-7.1), limit 2 | +5.21 blind, +4.50 calibrated | `scripts/motor_rev5_vs_ornl.py` |
| REQ-M2, current for 400 N m | 171 A cold, 177 A hot (limit 212): pass | 168 A blind | merged tables |
| REQ-M5, rated power to 6000 rpm | 55.85 kW cold (verified), 51.65 kW hot: pass | 58.6 / 48.0 kW | efficiency run |
| REQ-TH1, continuous rating | 27.70 kW nominal: pass (unverified, section check 5.3 %); 23.99 kW at the 0.08 mm fit: fail (verified) | 30.2 / 28.1 kW | `motor_prius_thermal_rev5`, 20261124-063338 |
| REQ-M4, bridges at 7200 rpm | **415.0 MPa** against 335: fail, verified (GCI 1.5 %) | 424.4 MPa | `motor_prius_rotor_overspeed_rev5_mesh`, 20261124-063835 |

The efficiency gap barely moves with the flux (blind +24 % flux: 5.2 points; calibrated: 4.5; client data +18 %:
4.4): it is mostly the losses the motor-only model leaves out (mechanical, magnet eddy current, AC copper) and the
torque per ampere. Known weak spots, reported: the dq tables' lowest q-axis row (iq 6.25 A) fails the dq-torque
check in six columns; the hot map's light-load row above 4000 rpm fails the half-table check; the thermal network's
hot-corner state at 5500 rpm in one cooling scenario has no fixed point (operating point discontinuous there).

## Next steps (no calibration)

1. Done 15:04: **revision 5, the client-data model**, +17.7 % (gap 0.775 mm) / +18.7 % (0.730 mm), as predicted.
   **Torque, like for like (revision 5, 17:13):** reproducing ORNL's locked-rotor procedure (largest torque over shaft
   angle, ripple included; scripts/motor_locked_rotor.py), the model is +17.5 % at 50 A and 17-19 % high at almost
   every current, matching its +17.7 % on back-EMF. ORNL's back-EMF, inductances and torque are consistent with each
   other once ripple is counted. (An earlier note here said the two tests disagreed; that compared ORNL's maximum with
   the model's mean, and is withdrawn.) So the model's magnet-driven flux is about 18 % high in two independent tests.
2. **Find the model-form cause** of what remains, one effect at a time, each with a hand estimate first:
   (a) how fully the magnets are magnetised in the assembled rotor (a question for the client's production engineer;
   the literature on in-rotor magnetising of high-coercivity NdFeB gives the typical range); (b) 3D end effects
   (done 17:57, hand estimate, scripts/motor_end_effects.py: -1.3 to -2.4 %, -3.7 % from the Chalmers 3D model;
   below the 5 % threshold, no 3D model; the model would read +13 to +16 %. End clamping piece non-magnetic from
   TM-2004/137 Fig. 9's photo: a client question);
   (c) a check of the 2D field with an independent solver on the same geometry (done 20:22, ElmerFEM,
   models/motor/elmer_em.py: lambda1 +0.10 % on FEMM's, waveform within 0.13 %, gap field +0.09 %: the 2D field
   is right; the excess is in the shared inputs or in what 2D leaves out); (d) the bridges' lamination steel (done 19:12, run 20261123-172758:
   three grades within -0.35 to +0.14 % of 105.16 V: not the cause).
3. Done 15:10: **static inductances** on revision 5: Ld 1.72 mH (-10.6 % on ORNL's 1.92), Lq 5.50 mH (+10 % on 5.0),
   saliency 3.2 against 2.6, as predicted: the client data does not fix them. Framed 21:51
   (scripts/motor_inductance_frame.py, CALIBRATION_PLAN): not a convention; the mean is +4.3 %, the saliency term
   +22.7 %; end-winding leakage and the small-signal slope do not touch the saliency; a 3 deg rotor misalignment or
   eddy currents at the test frequency would. Decided by how the test was made: client question 6, no run until then.
4. Done 17:09 (torque, revision 5) and 17:13 (locked-rotor emulation): torque 17-19 % high like for like. Then efficiency (with the measured resistance) and the design verdicts; then refresh
   `reports/motor/`.

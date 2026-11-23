# Study 7 (2004 Prius motor against ORNL's tests): where it stands

Updated 2026-11-23 15:05 (time from `date`). Since about 13:50 the study runs as a **regular client project**
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
| **Revision 5 (client data)** | 18.9 x 6.5 mm centred, 0.15 mm polymer each side | 1.255 T at 20 C, magnet at 25 C | **105.2** (gap 0.775) / 106.1 (gap 0.730) | **+17.7 / +18.7 %** | every client input measured and in the model; predicted to 0.1 V |

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

## Next steps (no calibration)

1. Done 15:04: **revision 5, the client-data model**, +17.7 % (gap 0.775 mm) / +18.7 % (0.730 mm), as predicted.
   **A tension to resolve first:** the blind model's locked-rotor torque was only +6.9 % high at 50 A (rising to
   +23.7 % at 250 A; RESULTS.md, current read as peak), while its back-EMF was +24 %. At low current torque follows
   the magnet flux, so if the magnet flux alone were 24 % high the 50 A torque should be about 20 % high. The two
   tests disagree on how much magnet flux the motor has. (Corrected 15:07: an earlier line here said the torque
   excess was largest at low current; it is the smallest.)
2. **Find the model-form cause** of what remains, one effect at a time, each with a hand estimate first:
   (a) how fully the magnets are magnetised in the assembled rotor (a question for the client's production engineer;
   the literature on in-rotor magnetising of high-coercivity NdFeB gives the typical range); (b) 3D end effects;
   (c) a check of the 2D model against an independent hand magnetic circuit for the same geometry.
3. **Static inductances** against Ld 1.92 / Lq 5.0 mH on the revision-5 machine.
4. **Torque per ampere at low current on the revision-5 machine against ORNL's locked-rotor test**, moved up: it
   tells whether the model's magnet flux is high (torque high too) or the back-EMF comparison carries something
   else (torque close). Then efficiency (with the measured resistance) and the design verdicts; then refresh
   `reports/motor/`.

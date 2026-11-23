# Study 7 (2004 Prius motor against ORNL's tests): where it stands

Updated 2026-11-23 13:40. The record of each step is in `RESULTS.md` (the blind comparison) and `CALIBRATION_PLAN.md`
(every revision since, with its predictions written before the run). This page is the short version.

## Back-EMF, every model so far

Line-to-line, V rms per 1000 rpm, fundamental. ORNL's routine test: 89.78 V full waveform, about 89.38 V fundamental.

| Model | Magnet | Remanence | Back-EMF | Against ORNL | Calibrated? |
|---|---|---|---|---|---|
| Blind (2026-11-21) | fills the 6.80 mm pocket | 1.243 T (ORNL sample curve) | 110.9 | +24 % | no |
| Revision 1, hypothesis A | fills the pocket | 1.036 T (fitted) | 89.4 | 0 % by construction | **yes** |
| Revision 4, centred (primary) | 5.31 mm magnet in a polymer shell | 1.243 T | 82.4 | -7.8 % | no |
| Revision 4, outer / inner (bounds) | same, shell thicker on one face | 1.243 T | 85.3 / 79.3 | -4.6 / -11.3 % | no |
| Revision 4 at ORNL's design value | same, centred | 1.12 T | 72.6 | -18.8 % | no |
| (outer / inner) | | 1.12 T | 75.2 / 69.8 | -15.9 / -21.9 % | no |

Peak voltage at 6000 rpm, REQ-M1 (limit 500 V): fails on every model (ORNL measured 850 V).

## Is ORNL's study wrong?

No. ORNL's reports hold three different kinds of information, and they should not be mixed up:

1. **Test measurements** (TM-2006/423: back-EMF, locked-rotor torque, efficiency map, inductances). These are the
   reference. Our models are scored against them.
2. **Hardware facts** (TM-2005/33 lamination drawing; TM-2004/137 teardown: magnet sample B-H curve, polymer-moulded
   magnets). These are what a client's drawings and specs would give us, and revision 4 is built from them.
3. **A design-study model** (TM-2004/120: a SPEED lumped-parameter model plus Flux2D, used to explore design trends).
   It draws the magnet filling its pocket and uses a "magnet strength" BrT of 1.12 T. Its own parameter list defines Br
   as the remanence at 20 C, and 1.243 T at -0.1 %/C is 1.12 T at about 119 C, so 1.12 T is most likely a hot design
   value, not a fudge. A design-trend model is allowed to simplify; it was never presented as a validated model of
   this motor.

An earlier note (12:24) read the 1.12 T as a lower remanence that compensates for the filled pocket. That was an
inference from a sketch; the report's own definitions point to a hot value instead. Corrected in `CALIBRATION_PLAN.md`.

## Is our model more accurate?

On back-EMF, the revision-4 model is closer to the hardware and gets within 8 % (centred) **with nothing fitted**. The
calibrated model (revision 1) matches back-EMF exactly, but only because its remanence was fitted to it; it then
missed torque per ampere by 12-14 % and efficiency by 4.5 points. A model that is close without fitting is better
evidence than one that is exact because of fitting.

It is not yet shown to be more accurate overall. Still open:
- **The remaining -8 %**, not explained. The drawing audit (`DRAWING_AUDIT.md`, 13:40) checked every dimension and
  material value: the winding is now confirmed by ORNL's design report (9 turns per coil, one layer, series), the
  hub ring and other small items add up to about 1-1.5 %, and the live candidates are the magnet's remanence and
  temperature, where the magnet sits along its pocket (the drawn stops, not yet measured), and what ORNL's "scaled"
  back-EMF means. 2D end effects would lower the value further, not raise it.
- **Inductances and torque.** Revision 4 is predicted NOT to fix the d-axis inductance (saliency 3.2 in the model
  against 2.6 measured). That test comes next; if it fails as predicted, a second effect remains to find.
- **Efficiency and the design verdicts** (REQ-M1, REQ-M5, thermal rating) must be recomputed on the revision-4 machine.

## Next, one effect at a time

1. Done 13:40: the drawing-against-model audit (`DRAWING_AUDIT.md`).
2. Static inductances on the centred machine against ORNL's Ld 1.92 / Lq 5.0 mH (prediction P3 first).
3. Torque per ampere (locked rotor), then efficiency and the design verdicts, each with predictions first, carrying
   the placement band (outer / inner) throughout.
4. Refresh `reports/motor/` (the published report, version 8, does not include revisions 2-4).

# Study 7 blind comparison: results (2026-11-22, ~19:00)

Our committed predictions against ORNL's measurements in ORNL/TM-2006/423 (Staunton et al., May 2006). Every
prediction was committed before any of this data was opened; the protocol log is `reports/motor/blind_comparison_log.md`.
Computed by `scripts/motor_blind_comparison.py` (output `comparison.json`, `comparison.png`) from the extracted data in
this folder: `tm2006_423_back_emf.csv` (Table 3.4), `tm2006_423_table_b1.csv` (Appendix B, Table B-1, 428 test points),
and the locked-rotor peaks typed into the script (Fig. 3.10; Table 3.2 maxima beside them).

## Verdicts against the limits agreed on 2026-11-21 (unchanged)

| Quantity | Limit | Prediction | ORNL | Difference | Verdict |
|---|---|---|---|---|---|
| Back-EMF constant | 5 % | 110.9 V rms line-to-line per 1000 rpm (fundamental; 111.3 full waveform) | 89.8 V rms per 1000 rpm (12 points, 500-6000 rpm, 25 C oil; spread 83.7-91.5) | **+23.5 %** (line-to-line reading); -28.5 % if ORNL's values were phase voltages | **FAIL** either way |
| Peak torque at seven currents (locked rotor) | 10 % | MTPA from the cold dq table | 74 / 118 / 154 / 199 / 221 / 286 / 337 N m at 50-250 A | current read as peak: +6.9 / +7.8 / +14.0 / +11.6 / +20.6 / +21.5 / +23.7 %; read as rms: +55 to +65 % | **FAIL** (pass at 50 and 75 A only, and only if ORNL's DC current is a peak) |
| Motor efficiency at sample points | 2 points | the efficiency model, hot (windings 100 C, magnets 80 C) and cold scenarios | 393 points of Table B-1 inside our map (500-6000 rpm, >= 10 N m) | ours higher by 5.2 points (median, hot; 10th-90th percentile 3.4-7.9); cold 6.3 | **FAIL**: 3 of 393 points within 2 points of our cold-hot band |

Conventions (argued before scoring, from the reports' text and ORNL's own numbers; see the log): ORNL's back-EMF read as
line-to-line (no neutral for an oscilloscope; their Vpeak / Vrms at 6000 rpm, 1.57, matches our line-to-line waveform,
1.56, not our phase waveform, 1.37). The locked-rotor current is a DC value ("DC Current (Amps)" in the interim
report); whether it is the peak of a balanced instant or an rms equivalent is not stated, so both readings are shown.

## What it says

One fault explains most of it: **our magnet flux linkage is about 24 % too high.** The back-EMF scales with it directly;
the torque per amp follows it (closest at low current, where the comparison is least sensitive to saturation and to the
current convention); and a stronger magnet needs less current for the same torque, so our copper loss is low and our
efficiency high. The efficiency gap also contains the losses the efficiency study left out by design (mechanical,
inverter-harmonic iron loss, magnet eddy-current and AC copper loss: the map was stated as an upper bound), but at about
5 points it is far larger than those alone usually are.

The design checks that depend on the flux move with it: REQ-M1 (open-circuit voltage at 6000 rpm) is overstated by about
24 % but still fails (ORNL measured 850 V peak, against the 500 V bus); REQ-M2 / REQ-M5 margins are optimistic.

## Candidate causes (hypotheses for a documented revision; not acted on)

1. Magnet remanence: ours 1.243 T, extrapolated from ORNL's measured B-H line (its points span -7.2 to -4.7 kOe);
   ORNL/TM-2004/120 gives 1.12 T (scratch sensitivity -11 % back-EMF).
2. Magnet size: ORNL/TM-2004/120's 19.24 x 5.31 mm against our 18.9 x 6.80 mm pocket fill (scratch: -2.4 % thickness,
   +2.0 % width).
3. Winding: 9 turns per coil in series (Pyleecan's, consistent with "9 conductor bundles per slot" in ORNL's text, but
   turns per bundle and parallel paths are not confirmed). The back-EMF scales with series turns.
4. 3D end leakage, absent from the 2D model (a few percent on an 84 mm stack).
5. ORNL's "scaled" back-EMF: the scaling is not explained in the report.
(The lamination grade is ruled out: three grades moved the back-EMF by 0.13 %.)
1, 2 and 4 together reach about -14 %, not -24 %, so the winding (3) stays a live suspect.

**Next diagnostic, proposed, not done:** ORNL/TM-2004/137 Fig. 13 (the measured no-load air-gap flux density) separates
the magnet side from the winding side: if our air-gap field matches it, the excess is in the winding; if ours is about 24 %
high, it is in the magnets. Any change that follows is a new, documented revision; the verdicts above stay as the blind
result.

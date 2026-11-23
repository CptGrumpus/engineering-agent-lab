# Traction motor: the 2004 Prius motor rebuilt from published drawings, then tested blind

[Portfolio index](../PORTFOLIO.md) · Electric machines

> **Draft (updated 2026-11-23).** Every prediction below was written before any of Oak Ridge National Laboratory's (ORNL's)
> measurements of this motor was opened. The blind comparison has now been run, once, against limits agreed in
> advance: **all three missed** (see "The blind comparison"). A post-test calibration on routine data followed: it
> narrows the efficiency gap only a little and flips the rated-power verdict (see "The post-test revision"). The full reports, the extracted data and the protocol
> log are in `reports/motor/` and `validation/motor_ornl/`.

| | |
|---|---|
| **Answer so far** | **Blind comparison against ORNL's measurements: fail on all three agreed limits.** Back-EMF +23.5 % (limit 5 %), torque +7 to +24 % (limit 10 %), motor efficiency about 5 points high (limit 2). One fault explains most of it: the model's magnet flux linkage is about 24 % too high. **Calibrated afterwards on routine data** (magnet remanence 1.036 T, chosen on the static inductances): the efficiency gap narrows only from 5.2 to 4.5 points, and to 4.05 with each test point's measured winding temperature (most of the rest is torque per ampere: ORNL's motor drew 6-30 % more current for the same torque), and the rated-power verdict flips to a fail (48 kW at 6000 rpm). The predictions as written:  back-EMF 110.9 V rms line-to-line per 1000 rpm at 20 °C; torque 119-606 N m from 50 to 350 A rms (400 N m at about 168 A); an efficiency map with a 97.4 % peak (motor only). Design checks: the rated 400 N m fits inside the copper limit (REQ-M2 pass), and the rated 50 kW holds to 6000 rpm (58.6 kW, verified; but not after calibration, above). Two fails a design review would want to know about: the open-circuit voltage at top speed is about 1040 V against a 500 V bus (REQ-M1), and the rotor bridges exceed the stand-in steel's yield at overspeed (424 against 335 MPa, REQ-M4). Thermal network (synthetic 65 °C water jacket): about 230 N m continuous to 2000 rpm and 42-48 kW from 2500 to 6000 rpm, limited by the magnets (150 °C) at every speed, not the winding; the efficiency map's hot corner understates the magnets by 13-25 K. Recomputed on the calibrated machine: 214 N m to 1250 rpm (28.1 kW, still above the 25 kW requirement) and 40-45 kW above 2500 rpm; the requirement fails at the loosest stator-to-housing fit in the scenario set. |
| **Discipline** | Electric machines: electromagnetics, losses, thermal, rotor stress |
| **Tools** | Pyleecan (geometry, drives FEMM), FEMM 4.2 (2D magnetostatics), CalculiX (rotor stress, slot heat conduction), Gmsh, Python |
| **Methods** | Machine rebuilt from published drawings (PDF vector data); open-circuit and loaded magnetostatics; maximum torque per amp; dq look-up tables with iron-loss coefficients; loss-minimising current search under voltage and current limits; a lumped thermal network coupled to the losses; mesh studies; a blind-validation protocol |

![Our slot (from ORNL's drawing) against the one Pyleecan ships for this motor](img/motor_slot_vs_ornl_fig21.png)

## The question

Can an open-source toolchain predict a production traction motor well enough for early design screening? The test
case is the 2004 Toyota Prius motor (48 slots, 8 poles, interior V magnets, 50 kW, 400 N m), which ORNL took apart,
drew and measured. Two kinds of answer are kept apart:

- **Design checks,** from our models with internal verification only: does the rated torque fit inside the copper's
  current limit, does the rated power hold to top speed, does the rotor survive overspeed, and what happens if the
  inverter stops switching at top speed?
- **Validation,** against ORNL's measurements, once, at the end, with limits agreed before any data was seen:
  back-EMF within 5 %, torque within 10 %, efficiency within 2 points at sample points.

## The answers so far

| Check | Result | Status |
|---|---|---|
| REQ-M1: open-circuit voltage at 6000 rpm ≤ 500 V (inverter fault) | Blind model: about 1040 V line-to-line peak. **Calibrated (A): 856.5 V** (mesh uncertainty 0.07 %); ORNL measured 850 V at 5998 rpm | **Fail**, verified on both: the machine needs the inverter to hold its voltage down at speed |
| REQ-M2: 400 N m within 25 A/mm² of copper current density | 400 N m at about 168 A rms, 19.8 A/mm² | **Pass** |
| REQ-M3: every operating point within 25 A/mm² | the limit is 212 A rms; 250 A and above exceed it | **Fail** above 212 A (a short-time rating question) |
| REQ-M4: rotor bridges below yield at 7200 rpm overspeed | 424 MPa against 335 MPa (M330-35A) | **Fail**, verified; elastic at 6000 rpm (295 MPa). A stronger grade (M250-35A, 455 MPa typical) would pass |
| REQ-M5: rated 50 kW from base speed to 6000 rpm (500 V, 212 A) | Blind model: 58.6 kW at the worst speed (6000 rpm), 20 °C; 53.7 kW hot. Calibrated (magnets 1.036 T): 48.0 kW cold, 44.5 kW hot | Blind: **Pass** (verified cold). Calibrated: **Fail** (unverified) |
| REQ-TH1: at least 25 kW continuous from 1250 to 6000 rpm (winding hotspot ≤ 180 °C, magnets ≤ 150 °C; jacket 65 °C, synthetic) | Blind model: 30.2 kW at the worst speed (1250 rpm); 26.2-34.3 kW over ten cooling and material scenarios. **Calibrated (A): 28.1 kW**; 24.3-31.9 kW over the scenarios | Blind: **Pass**. Calibrated: **Pass** at the nominal stator-to-housing fit, **Fail** (24.3 kW, verified) at the loosest fit (0.08 mm interface gap). In six scenarios the slot-hotspot check misses its 5 % by 0.1-2.2 points; a bound shows that cannot move the answer |

Blind predictions, for the comparison at the end: back-EMF **110.9 V** per 1000 rpm; MTPA torque **118.8 / 251.6 /
366.6 / 456.9 / 522.3 / 569.4 / 606.4 N m** at 50-350 A rms; an efficiency map from 500 to 6000 rpm, peaking at
**97.4 %** at 2500 rpm and 80 N m (cold), 97.0 % hot. These are motor-only efficiencies (copper and iron loss;
mechanical, magnet and inverter losses left out), so they are upper bounds on what a dynamometer would measure.

![Motor-only efficiency map, cold, with the torque limit at the 212 A design current](../runs/20261122-175650_motor_prius_efficiency_r1/points/p00_cold/response.png)

*(One cell per computed point, 250 rpm by 10 N m; the map stops at 400 N m. Drawn from a rerun of the efficiency run
that reproduced it bit for bit; the first figure's contour fill left a false gap under the limit line.)*

## The blind comparison

Run once, on 2026-11-22, against ORNL/TM-2006/423 (back-EMF from 500 to 6000 rpm, locked-rotor torque at seven
currents, and 393 measured efficiency points), with the limits agreed the day before. Each step is in the protocol log,
including a column I misread in ORNL's back-EMF table and caught before any score was written.

| Quantity | Limit | Our prediction against ORNL's measurement | Verdict |
|---|---|---|---|
| Back-EMF constant | 5 % | 110.9 against 89.8 V rms per 1000 rpm: +23.5 % | **Fail** |
| Peak torque at 50-250 A | 10 % | +7 % at 50 and 75 A, rising to +24 % at 250 A (ORNL's DC current read as a peak; read as rms, +55-65 %) | **Fail** |
| Motor efficiency at 393 test points | 2 points | ours higher by 5.2 points (median; 3.4-7.9 for 80 % of points) | **Fail** |

![Our predictions against ORNL's measurements](../validation/motor_ornl/comparison.png)

**What it means.** The three misses point the same way: the model carries about 24 % too much magnet flux. That raises
the back-EMF directly, the torque per amp with it, and the efficiency (a stronger magnet needs less current, so less
copper loss), on top of the losses the efficiency map left out by design. The verdicts stand as the blind result. The
suspects, in order: the magnets' remanence (ours 1.24 T from ORNL's B-H line; another ORNL report gives 1.12 T), their
size, the winding's series turns, and 3D end leakage that a 2D model leaves out. The first three together explain
about 14 %, so the winding stays a suspect. The next step is a diagnostic, not a fit: ORNL's measured air-gap field
(a figure in its design report, still unopened) separates the magnet side from the winding side. Any model change will
be a documented revision, with these verdicts kept.

**What survives.** The toolchain, the verification and the design workflow all ran as intended; the miss is in one
design input, found by a single honest comparison, which is what the comparison was for. REQ-M1 still fails with ORNL's
own numbers (850 V peak at 6000 rpm against a 500 V bus). ORNL also reports continuous ratings of 15-21 kW at base
speed (105 to 35 °C coolant); our thermal network gives about 30 kW under its synthetic 65 °C jacket, so with the
flux 24 % high (and so the current low) and an assumed cooling system, it is optimistic too (thermal was not in the
agreed validation set).

## The post-test revision

The blind verdicts stay on the record. The revision uses only the kind of data a client would hand over for an existing
motor, and spends it deliberately ([plan](../validation/motor_ornl/CALIBRATION_PLAN.md), predictions committed before
each step):

- **Calibrate on the routine test.** Two explanations fit ORNL's back-EMF exactly: (A) weaker magnets, remanence
  1.036 T instead of 1.243 T, or (B) fewer effective turns (× 0.807).
- **Choose with the cheapest test that separates them.** I first chose with the locked-rotor torque (A: 8.7 % rms error,
  B: 10.7 %), which spends the torque data and barely separates them. Asked whether a client would even have that
  test, I switched to the static inductances, which a client usually would have. A turns error scales inductance by
  0.807² = 0.65; a magnet error does not. ORNL's static Ld = 1.92 mH and Lq = 5 mH sit near A (1.70 and 5.38 mH, per
  phase) and far from B (1.11 and 3.50 mH). **A is selected.**
- **What the calibrated model still gets wrong.** Torque: within 4 % at low current but 12-14 % high at 150-250 A
  (three of ORNL's seven currents outside the original 10 % band). The measured saliency Lq / Ld is 2.6 against our
  3.2, so the d-axis path is not quite right (the thinner real magnet is the first suspect).
- **Out of sample: efficiency, with A's dq tables.** Over ORNL's 393 measured points our (hot) efficiency is now
  4.5 points high at the median, against 5.2 for the blind model and 5.3 for B. Still far outside the 2-point limit:
  the calibration fixes the flux, and the remaining gap is losses this model leaves out (mechanical, magnet eddy
  currents, AC copper). My sharper prediction, that A would widen the gap, had the direction wrong; the plan's
  looser one (it stays 3-5 points) held.
- **A design verdict flips.** With the weaker magnets the motor no longer holds 50 kW to 6000 rpm at 500 V and the
  212 A design current (REQ-M5): 48.0 kW cold, 44.5 kW hot at 6000 rpm, against 58.6 / 53.7 before. Less magnet flux
  is less torque per ampere in field weakening. I had predicted the opposite. A design review using the blind model
  would have signed off a requirement the calibrated model fails, which is the strongest argument on this page for
  calibrating against a routine test before trusting a flux-dependent verdict.
- **Its own checks:** the calibrated efficiency run fails verification on three checks, none of which touches the
  comparison: my back-EMF reference came from a different mesh (0.1 % apart), the half-table iron-loss estimate misses
  its 5 % (7 %), and the unresolved 10 N m row trips the map check in the other scenario.
- **Efficiency, revisited with more routine data (revisions 2 and 3).** A no-load spin-loss test is routine supplier
  data, and ORNL has one (the unpowered rotor spun in its housing). I predicted it would show the model's no-load loss
  1.3-2.5 times too low and close much of the gap. It matched the model (0.87-1.35 times our iron loss) and moved the
  gap by 0.02 points: the no-load loss was never the problem. ORNL also logged the winding temperature at every test
  point (43-207 °C, where the maps assumed 100 °C); using it closed the median gap from 4.50 to 4.05 points and a
  quarter of the missing loss at high torque. Still a fail against 2 points.
- **Where the rest of the gap comes from (a diagnostic, not used in the model).** At the same speed and torque, ORNL's
  motor drew 6-30 % more current than ours. That extra current's copper loss is 43 % of what is missing, three
  quarters at low speed and high torque. So the model makes its torque with too little current, which fits the low
  measured saliency.
- **The magnet as drawn (revision 4, in progress).** Every model so far filled the 6.80 mm rotor pocket with magnet,
  because the Pyleecan template does. ORNL's design report gives the magnet as 5.31 mm, and its teardown report shows
  why: the magnets are moulded into a polymer shell sized to the slot. Modelled that way, with the magnet material
  as ORNL measured it and nothing calibrated, the back-EMF comes out 7.8 % below the measurement with the magnet
  centred in its shell (4.6 % and 11.3 % low at the extremes of the fit), against 23.5 % high blind. The blind miss
  was mostly geometry, which the earlier "weaker magnets" calibration had absorbed. Still to run on the drawn-magnet
  machine, each with predictions first: inductances, torque per ampere, efficiency and the design verdicts.
- **While doing this, a transcription error.** The efficiency table's winding temperature, phase voltage and phase
  current had been transcribed wrongly (empty, or shifted by one column in 345 of 428 rows). None of them had been
  used in a score, and the scored columns were checked row by row against the table's own identities; they were right.
- **The continuous rating, recomputed.** The thermal network on A's tables gives 28.1 kW at 1250 rpm, against 30.2
  kW: the same heat allows the same current (97 A), and the weaker magnets give 7 % less torque for it. The 25 kW
  requirement still passes at the nominal stator-to-housing fit, but now fails at the loosest fit in the scenario set
  (24.3 kW at a 0.08 mm interface gap), so the rating depends on a number a client would be asked for: the press-fit
  interference or a measured interface resistance. I predicted the torque at 4000-6000 rpm would rise (less
  field-weakening current); it fell 5-10 %. Below 90 A the loss-minimising search picks the same currents, so there is
  no field-weakening current to free.

## How it works

- **The machine.** Pyleecan ships a model of this motor, but rebuilt from ORNL's dimensioned drawing (read from the
  PDF's vector outline, not by eye) its slot is 145 mm², not 218, and its air gap 0.775 mm, not 0.750. The magnet
  pockets, bridges and magnet material come from ORNL's design reports (the magnet's measured B-H line was opened
  by decision, as a material input like a datasheet). The lamination grade isn't published: M330-35A stands in, and
  two other grades bracket it.
- **Electromagnetics.** FEMM solves 2D magnetostatics over one electrical period. Open circuit gives the back-EMF;
  loaded runs sweep the current angle for the maximum torque per amp.
- **Efficiency.** Look-up tables of torque, dq flux linkage and iron-loss coefficients over the dq current plane
  (FEMM, 169 plus 91 solves per magnet temperature), then, at every speed and torque, the current with the least
  copper plus iron loss that the 500 V bus can drive.
- **Rotor.** CalculiX, plane stress, centrifugal and magnet loads at 7200 rpm, stresses linearised across the bridges.
- **Thermal.** A lumped network built from the geometry (yoke, teeth, slot winding, liner, end windings, end-space
  air, housing, rotor; Mellor's T-equivalent circuits, exact for 1D conduction), with the losses taken from the dq
  tables at the network's own temperatures (copper resistance, magnet flux) and iterated to a steady state. The
  continuous envelope is the largest torque per speed within the winding and magnet limits. Cooling, the insulation
  class and the magnet grade aren't published, so they are synthetic and swept; the stator-housing interface and
  end-space coefficients come from measured machines in the literature.

## How I know it's right (before the test data)

- **Independent routes inside the model:** the power balance (Σ i·dφ/dt against torque × speed) checks FEMM's
  torque to 0.1-0.4 %; winding theory checks the flux linkage to 0.3-0.6 %; the dq torque equation checks the
  tables' fluxes; the efficiency tables reproduce the open-circuit and torque studies (2.7 × 10⁻⁶ and 0.2 %).
- **The rotor pipeline on an exact case:** a plain rotating disk matches the closed form to 4 × 10⁻⁴.
- **The thermal network against CalculiX:** 2D conduction on half a slot pitch with the same losses and boundary
  conditions: winding mean within 3-6 %, teeth within 2-5 %, yoke within 2 %, slot hotspot 4-7 % low (see below).
- **Mesh studies** on every quantity, with the coarsest mesh dropped where it left the thin bridges under one element.
- **Sensitivity to what isn't published:** the three lamination grades move the back-EMF 0.13 % and the torque under
  2 %; the unmeasured deep-saturation tail of the steel's curve moves the high-current torque about 2 %.

## What the checks caught

- **A copper area 1.57 times too large.** ORNL quotes a slot fill of 0.84, and the first version applied it to the
  whole slot. Re-reading the definition: it is the fill of the *squares* of the insulated wires. The bare copper is
  about 0.59 of the slot, so the 25 A/mm² limit is 212 A, not 333 A. Torques didn't change; two verdicts did (REQ-M2's
  margin fell from 52 % to 19 %, REQ-M3 now fails above 212 A). Caught and corrected before any test data was seen.
- **A library model that wasn't the motor it was named after.** Pyleecan's Prius slot is half as large again as
  ORNL's drawing; the drawing itself turned out to be stretched 1.1 % in x, and was corrected before use.
- **An efficiency map that looked finished.** The first map passed its spot checks against the torque and
  open-circuit studies, but its interpolation check failed, all on one row of the table. At light load and high speed
  the best operating point used 2-5 A of q-axis current, inside the table's first 25 A cell, and the map there moved
  by up to 10 points with the table spacing. Finer rows at low current fixed it everywhere from 20 N m up (to under
  1 point); the 10 N m row above 4000 rpm is reported as unresolved.
- **Hot magnets cost more than their remanence.** At 80 °C the magnets lose 6 % of their remanence, but the motor
  lost 7 % of its flux: the saturated bridges keep their leakage flux.
- **A hotspot in the wrong place.** The network first put the slot's hottest point at the middle of the winding
  (a slab between walls at one temperature) and read 10 % low on the rise. CalculiX put it at the top of the slot, by
  the tooth tips: the teeth carry the winding's heat out to the yoke, so they are hottest at the bore. Reading the
  hotspot there halved the error; the remaining 4-7 % is the 2D field a lumped model leaves out, and a bound shows it
  cannot move the envelope.
- **The magnets, not the copper, set the continuous rating.** With no heat path through the shaft and only
  conduction across the 0.77 mm air gap, the rotor floats at the temperature of the tooth tips, the hottest iron. A
  better air gap made it slightly worse: it ties the rotor closer to those tips.
- **A leak in a blind protocol, recorded rather than hidden.** A line filter on one ORNL report let through some of
  ORNL's own *model* results (not measurements). They are logged with their time and declared in every case that
  followed; extraction is whitelist-only since.

## Limits

- 2D magnetostatics: no end effects, no eddy currents in the magnets, no AC copper loss.
- The lamination grade, the end-winding length and the copper temperature are estimates; their effects are bracketed
  or stated.
- Thermal: steady state only (no short-time ratings); cooling, insulation class and magnet grade synthetic; the
  rotor's paths (air gap, end space, shaft) are the least checked and set the answer; no thermal test data is used.
- Efficiency map: the 10 N m row above 4000 rpm is unresolved (the loss-optimal current sits inside the table's
  first cell), and with hot magnets one cell there (4500 rpm, 10 N m) fails the interpolation check, so the hot
  REQ-M5 result (53.7 kW) is a pass but unverified. Both are left as stated limits rather than revised: light load at
  high speed does not bear on any requirement, and a calibrated model would rebuild the tables anyway.
- Validated against ORNL's measurements once: it failed (above). The calibrated model (magnets 1.036 T) fixes the
  back-EMF by construction and moves torque and efficiency closer, but it is calibrated, not validated; the blind
  model's flux-dependent numbers on this page (REQ-M1, REQ-M5, the thermal rating) are about 24 % optimistic in flux,
  and REQ-M5 already fails once that is corrected. The thermal rating, recomputed with it, falls to 28.1 kW and fails
  at the loosest housing fit.

## Evidence

- Reports: `reports/motor/` (overview, design inputs, open circuit, torque, efficiency), built from the runs by
  `reports/motor/build_report.py`; thermal: `runs/20261122-174925_motor_prius_thermal_r1/report.md` (blind), `runs/20261123-071007_motor_prius_thermal_br/report.md` (calibrated)
- Cases (predictions before each run, results after): `cases/motor_prius_*.toml`
- Blind comparison: `validation/motor_ornl/RESULTS.md`, the data extracted from ORNL/TM-2006/423, and
  `scripts/motor_blind_comparison.py`; protocol log `reports/motor/blind_comparison_log.md`
- Code: `models/motor/`, `studies/motor_em.py`, `studies/motor_torque.py`, `studies/motor_lut.py`,
  `studies/motor_efficiency.py`, `studies/motor_thermal.py` (with `models/motor/thermal_network.py`,
  `models/motor/stator_section_ccx.py`), `studies/rotor_stress.py`

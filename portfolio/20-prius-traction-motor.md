# Traction motor: the 2004 Prius motor rebuilt from published drawings, then tested blind

[Portfolio index](../PORTFOLIO.md) · Electric machines

> **Closed 2026-11-24 with open items** (final report: `validation/motor_ornl/FINAL_REPORT.md`; updated 10:56). The study began as a blind test: every prediction was written before any of Oak
> Ridge National Laboratory's (ORNL's) measurements was opened, and the blind comparison **missed all three limits**.
> Since then it has run as a regular client project: everything a client would hand over is collected and used, and
> nothing is fitted (see "Run as a client project"). The current state is at the top of the table below; the earlier
> sections stay as the record. Reports and data: `reports/motor/`, `validation/motor_ornl/` (`STATUS.md` is the short
> version).

| | |
|---|---|
| **Where it stands** | **Built from the client's own data (drawing, bill of materials, measured magnet properties, routine tests), the model's magnet-driven flux is about 18 % high, consistently:** back-EMF +17.7 % and locked-rotor torque +17 to +19 % at almost every current, compared like for like. ORNL's measurements agree with each other. Every input a client supplies is in the model and matches, down to the magnet stops on the drawing, so the cause is in the model's form or in how the motor was built; candidates are being tested one at a time, without calibrating (steel: ruled out, three grades within 0.35 %; end effects: 1.3-3.7 %, too small to explain it; an independent second solver (ElmerFEM) on the same geometry agrees with the FEMM model to 0.1 %, so the 2D field is right; the magnets sit on the drawing's stops as modelled. The leading explanation left is how fully the magnets are magnetised in the assembled rotor, and ORNL's measured no-load air-gap flux density (TM-2004/137 Fig. 13) backs it: the model's field is ORNL's scaled uniformly by 1.148 where the field is level, which a magnetisation shortfall does and a geometry or leakage error does not; 14.8 % plus the end effects makes the 18 %. A half-day fluxmeter test on one magnet would settle it). REQ-M1 fails on every model and on ORNL's own numbers. **Every design check is now recomputed on the client-data model (revision 5, 2026-11-24), uncalibrated:** efficiency map from four new dq tables with the client's measured phase resistance (69 mΩ, 15 % above the geometric value): peak 97.2 % cold, 96.9 % hot; against ORNL's 393 efficiency points the motor-only map is 4.4 points high at the median (blind 5.2, calibrated 4.5), still over the 2-point limit, and the gap is the losses the model leaves out more than the flux. Rated power holds (REQ-M5: 55.9 kW cold, 51.6 kW hot); 400 N m needs 171 A (REQ-M2 pass); continuous rating 27.7 kW (REQ-TH1 pass, fails at the loosest housing fit); rotor bridges 415 MPa at overspeed against 335 (REQ-M4 fail, verified). |
| **History** | **Blind comparison against ORNL's measurements: fail on all three agreed limits.** Back-EMF +23.5 % (limit 5 %), torque +7 to +24 % (limit 10 %), motor efficiency about 5 points high (limit 2). One fault explains most of it: the model's magnet flux linkage is about 24 % too high. **Calibrated afterwards on routine data** (magnet remanence 1.036 T, chosen on the static inductances): the efficiency gap narrows only from 5.2 to 4.5 points, and to 4.05 with each test point's measured winding temperature (most of the rest is torque per ampere: ORNL's motor drew 6-30 % more current for the same torque), and the rated-power verdict flips to a fail (48 kW at 6000 rpm). The predictions as written:  back-EMF 110.9 V rms line-to-line per 1000 rpm at 20 °C; torque 119-606 N m from 50 to 350 A rms (400 N m at about 168 A); an efficiency map with a 97.4 % peak (motor only). Design checks: the rated 400 N m fits inside the copper limit (REQ-M2 pass), and the rated 50 kW holds to 6000 rpm (58.6 kW, verified; but not after calibration, above). Two fails a design review would want to know about: the open-circuit voltage at top speed is about 1040 V against a 500 V bus (REQ-M1), and the rotor bridges exceed the stand-in steel's yield at overspeed (424 against 335 MPa, REQ-M4). Thermal network (synthetic 65 °C water jacket): about 230 N m continuous to 2000 rpm and 42-48 kW from 2500 to 6000 rpm, limited by the magnets (150 °C) at every speed, not the winding; the efficiency map's hot corner understates the magnets by 13-25 K. Recomputed on the calibrated machine: 214 N m to 1250 rpm (28.1 kW, still above the 25 kW requirement) and 40-45 kW above 2500 rpm; the requirement fails at the loosest stator-to-housing fit in the scenario set. |
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
| REQ-M2: 400 N m within 25 A/mm² of copper current density | 400 N m at about 168 A rms, 19.8 A/mm². **Client data (rev. 5): 171 A** (177 A hot) | **Pass** |
| REQ-M3: every operating point within 25 A/mm² | the limit is 212 A rms; 250 A and above exceed it | **Fail** above 212 A (a short-time rating question) |
| REQ-M4: rotor bridges below yield at 7200 rpm overspeed | 424 MPa against 335 MPa (M330-35A). **Client data (rev. 5): 415 MPa** (the BOM's lighter magnet, -4.7 % load; mesh uncertainty 1.5 %) | **Fail**, verified on both; elastic at 6000 rpm (295 MPa). A stronger grade (M250-35A, 455 MPa typical) would pass |
| REQ-M5: rated 50 kW from base speed to 6000 rpm (500 V, 212 A) | Blind model: 58.6 kW at the worst speed (6000 rpm), 20 °C; 53.7 kW hot. Calibrated (magnets 1.036 T): 48.0 kW cold, 44.5 kW hot. **Client data (rev. 5): 55.9 kW cold, 51.6 kW hot** | Blind: **Pass** (verified cold). Calibrated: **Fail** (unverified). Client data: **Pass** (verified cold; hot unverified on the light-load interpolation check) |
| REQ-TH1: at least 25 kW continuous from 1250 to 6000 rpm (winding hotspot ≤ 180 °C, magnets ≤ 150 °C; jacket 65 °C, synthetic) | Blind model: 30.2 kW at the worst speed (1250 rpm); 26.2-34.3 kW over ten cooling and material scenarios. **Calibrated (A): 28.1 kW**; 24.3-31.9 kW over the scenarios. **Client data (rev. 5): 27.7 kW**; 24.0-31.5 kW | Blind: **Pass**. Calibrated and client data: **Pass** at the nominal stator-to-housing fit, **Fail** (24.3 / 24.0 kW, verified) at the loosest fit (0.08 mm interface gap). In six scenarios the slot-hotspot check misses its 5 % by 0.1-2.2 points; a bound shows that cannot move the answer |

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
- **The magnet as drawn (revision 4; overturned the same afternoon, see the next section).** Every model so far filled the 6.80 mm rotor pocket with magnet,
  because the Pyleecan template does. ORNL's design report gives the magnet as 5.31 mm, and its teardown report shows
  why: the magnets are moulded into a polymer shell sized to the slot. Modelled that way, with the magnet material
  as ORNL measured it and nothing calibrated, the back-EMF comes out 7.8 % below the measurement with the magnet
  centred in its shell (4.6 % and 11.3 % low at the extremes of the fit), against 23.5 % high blind. The blind miss
  was mostly geometry, which the earlier "weaker magnets" calibration had absorbed. **Wrong:** the 5.31 mm came from
  ORNL's design-study model, not the hardware; the measured magnet is 6.5 mm (next section).
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

## Run as a client project (2026-11-23)

The blind pass measured how far a model built from drawings alone can be trusted, and it exposed process faults that
open data would have hidden (a template that silently filled the magnet pocket, a calibration that hid the error).
Its cost was that it held back data a client gives on day one, so later revisions guessed values that should have been
looked up. From the afternoon of 2026-11-23 the study runs as a normal job: everything a client would provide is
collected first ([client data pack](../validation/motor_ornl/CLIENT_DATA.md)) and used as input; the tests the job
must predict (torque, efficiency) stay targets; predictions still come before each run.

**What the client's data settled.** ORNL's later benchmark report (ORNL/TM-2010/253, Table 2.7) is a bill of materials
for this motor:

- **The magnet is 83.1 × 18.9 × 6.5 mm, 77 g.** That is bare NdFeB's density, so 6.5 mm is the magnet itself.
  Revision 4's 5.31 mm came from ORNL's design-study model; at that size the magnet would need 9.1 g/cm³. Revision 4's
  explanation was withdrawn, and a lesson went into the skills: cross-check a dimension that drives a revision
  against mass and volume.
- **The magnet material: 1.255 T at 20 °C, -0.10 %/°C** (measured on a 2004 Prius magnet). Our original 1.243 T was
  right; ORNL's 1.12 T is that magnet at about 125 °C.
- **Winding, stack, stator geometry and copper** all match (the stator core and copper masses confirm them).
- **Phase resistance, measured: 69 mΩ at 21 °C**, 14 % above our computed value; the measured one is used from now on.
- **The back-EMF test:** line to line, oil at 25 °C, a power meter, repeated to rule out heating.

**Revision 5, the client-data model** (nothing fitted; predictions committed before each run, all held):

| Quantity | Model | ORNL | Difference |
|---|---|---|---|
| Back-EMF, V rms line to line per 1000 rpm | 105.2 (gap 0.775 mm) / 106.1 (0.730 mm) | 89.4 | +17.7 / +18.7 % |
| Static inductance Ld / Lq | 1.72 / 5.50 mH | 1.92 / 5.0 mH | -10.6 / +10 % |
| Locked-rotor torque at 50 / 250 A, like for like | 87.0 / 411.8 N m | 74 / 337 N m | +17.5 / +22.2 % (12-22 %, mostly 17-19 %, over the seven currents) |

**Comparing torque like for like.** ORNL reports the largest torque over shaft angle, ripple included; the model's
default output is the mean. The mean read only +4 % at 50 A. The model's saved phase currents fix ORNL's locked-rotor
path exactly, and along it the model's maximum is +17.5 %. That also showed ORNL's data are self-consistent: ORNL's
back-EMF and inductances give a mean torque of 65.3 N m at 50 A, the model's ripple lifts the maximum 13.4 % above the
mean, and 65.3 × 1.134 = 74.0 N m, exactly what ORNL measured. (An earlier note that ORNL's two tests disagreed had
compared a maximum with a mean; it is withdrawn.)

**Where that leaves it.** The model carries about 18 % too much magnet-driven flux, in two independent tests, with
every client input measured and in the model. Candidates, cheapest first: other published models of this motor (none
found that states inputs and numbers); the lamination steel in the bridges (ruled out: three plausible grades move
the back-EMF -0.35 to +0.14 %); 3D end effects (a hand estimate gives -1.3 to -2.4 %, a published 3D model of this
motor -3.7 %: at most a fifth of the excess; the rotor's end clamping piece looks non-magnetic in ORNL's photo, a
question for the client); a second, independent 2D solver on the same geometry (ElmerFEM: within 0.1 % of the FEMM
model's flux linkage, waveform and gap field, so the 2D field is right); the magnet's position along each pocket
(measured on the drawing: every magnet sits on its stop, as modelled, with at most 0.4 mm of play); and the magnets'
magnetisation level in the assembled rotor, which a client's
production engineer could answer or a half-day fluxmeter test on one magnet would settle. The inductance mismatch is a
separate effect: the model's average inductance is within 4.3 % of the test, but its saliency (Lq - Ld) is 23 %
larger, which no model-side omission explains; how the static test was made (rotor positioning, test frequency) would,
and is a question for the client.

## How it works

- **The machine.** Pyleecan ships a model of this motor, but rebuilt from ORNL's dimensioned drawing (read from the
  PDF's vector outline, not by eye) its slot is 145 mm², not 218, and its air gap 0.775 mm, not 0.750. The magnet
  pockets and bridges come from the drawing and ORNL's design report; since revision 5 the magnet (size and
  temperature-dependent remanence) comes from ORNL's bill-of-materials report (TM-2010/253). The lamination grade isn't published: M330-35A stands in, and
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
- **A dimension taken from a design study.** Revision 4 rested on a 5.31 mm magnet from ORNL's parametric design
  report and seemed to explain most of the blind miss. The bill of materials gives 6.5 mm and 77 g, and 77 g at
  5.31 mm would need an impossible density. One mass check would have caught it.
- **A comparison with the wrong statistic.** ORNL's locked-rotor torque is a maximum over shaft angle, ripple
  included; comparing it with the model's mean made the model look 4 % high at 50 A (it is 17.5 %) and produced a
  false "ORNL's tests disagree" diagnosis, withdrawn the same hour. The comparison now emulates ORNL's procedure from
  the model's saved data (`scripts/motor_locked_rotor.py`).
- **A leak in a blind protocol, recorded rather than hidden.** A line filter on one ORNL report let through some of
  ORNL's own *model* results (not measurements). They are logged with their time and declared in every case that
  followed; extraction is whitelist-only since.

## The motor as built

The motor is delivered as a detailed CadQuery assembly ([`models/cad/prius_motor.py`](../models/cad/prius_motor.py),
[STEP](cad/prius_motor_rev5.step)): the stator core with its three mounting ears, nine edge notches and 48 slots, the
slot windings and the 24 coils' end turns at both ends, the rotor core with its V pockets and hub keys, and the 16
magnets.
The cross-section is the analysed one (revision 5), from the same Pyleecan export the independent Elmer model used,
so the CAD and the analysis share one geometry. Stack lengths are the bill of materials': stator 84.0 mm, rotor
83.6 mm, magnets 83.1 mm.

The features the 2D model leaves out come from the client's lamination drawing. It dimensions the ear holes
(0.360 in), the ear root reliefs (R0.234 in) and both notch sizes, but not where they sit or the ear's outline, so
those were measured from the drawing's vector paths ([`scripts/motor_drawing_stator.py`](../scripts/motor_drawing_stator.py)).
The page was scaled by the 10.600 in outer diameter; the 6.375 in bore then reads within 0.075 mm, and the three
holes 9.10-9.17 mm against the drawn 9.144.

**The mass check closes.** The core as drawn weighs 19.05 kg at the stand-in steel's density (7650 kg/m³), the bill of
materials' 19.05 kg to 0.02 %. Without the ears and notches it is 18.88 kg, 0.9 % light: the drawing's features are
what the 2D model was missing. (This is a solid stack; a stacking factor below 1 would make it lighter, so the
agreement also says the real core is close to full density at that steel's value. The grade is still a client
question.) The 16 magnets weigh 1.233 kg against the bill of materials' 16 × 77 g.

**How I know the CAD is right.** Every part matches its exact section area (lines and arcs summed by Green's theorem)
or a hand volume to 10⁻⁹; each ear's area also matches an independent count on a 0.01 mm grid within 0.3 %. The
magnets sit in their pockets and the windings in their slots without overlap, and the air gap is the model's
0.775 mm. The STEP file re-imports with all 114 solids and the same total volume.

**What the drawing corrected.** The drawing audit had recorded four hub keys; the drawing shows two, 180° apart and
5.04 mm wide (the teardown's count was not re-read). The drawing's view is also turned half a slot pitch from the
model's frame, so its features were placed by where they sit relative to the slots: every ear and notch is on a
tooth centre.

**The end windings.** The end turns are wired as the analysed model's winding: single layer, two-slot phase belts,
each pole pair's three phase groups joining a belt to the opposite one six slots on, 8 coils per phase in series as
the bill of materials gives. Every outer coil's crown sits at the teardown's "approximately 1.5 in" extension. (An
earlier version drew a plain ring 19.4 mm long, the machine file's overhang: half the teardown's figure.) The data
does not give how the coils are arranged, so that part is a plausible layout, marked synthetic in the source: each
group as two concentric coils, the three groups of a pole pair in three radial tiers (they overlap in angle, so they
cannot share a radius), straight legs and a rounded top. Each turn keeps the slot zone's cross-section and matches its
exact hand volume to 2 × 10⁻⁸. The tiers fill the slot depth (82.0-115.2 mm radius), 1.0 mm clear of the bore, and no two
turns share volume.

**Two independent checks on the end turns.** From the turns, the copper weighs 6.57 kg, 3.3 % under the bill of
materials' 6.8 kg, which also counts the leads and the jumpers between coils (not drawn). The mean end turn, 116.0 mm,
is 3.8 % under the 120.6 mm the efficiency study assumed for its computed phase resistance (a semicircle over the coil
span). With the phases in separate tiers their end turns differ (111.5, 116.1 and 120.3 mm), so their resistances
would differ by about 2 %. A real three-tier winding has that asymmetry too; whether this one is three-tier is not in
the data.

**Simplified or not drawn.** Where a coil side leaves its slot and re-forms into its tier, the transition (a few mm
in a real winding) is not drawn: the turn starts on the stack face. Not drawn: the leads and jumpers, the shaft, the
rotor's hub and end plates, and the transaxle case the ears bolt into. None of the last four is in the client data,
and the bill of materials' 10.2 kg rotor includes the shaft, hub and end plates (the drawn rotor core is 5.20 kg).

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
- Client-data model (revision 5): about 18 % high on magnet-driven flux, cause not yet found; flux-dependent design
  numbers (REQ-M1, REQ-M5, the thermal rating) are not final until it is.
- Validated against ORNL's measurements once: it failed (above). The calibrated model (magnets 1.036 T) fixes the
  back-EMF by construction and moves torque and efficiency closer, but it is calibrated, not validated; the blind
  model's flux-dependent numbers on this page (REQ-M1, REQ-M5, the thermal rating) are about 24 % optimistic in flux,
  and REQ-M5 already fails once that is corrected. The thermal rating, recomputed with it, falls to 28.1 kW and fails
  at the loosest housing fit.

## Evidence

- Reports: `reports/motor/` (overview, design inputs, open circuit, torque, efficiency), built from the runs by
  `reports/motor/build_report.py`; thermal: `runs/20261122-174925_motor_prius_thermal_r1/report.md` (blind), `runs/20261123-071007_motor_prius_thermal_br/report.md` (calibrated)
- Client-data model (revision 5): [efficiency](../runs/20261124-062847_motor_prius_efficiency_rev5/report.md) (scored against ORNL in `validation/motor_ornl/rev5_efficiency_vs_ornl.json`), [thermal](../runs/20261124-063338_motor_prius_thermal_rev5/report.md), [rotor overspeed](../runs/20261124-063835_motor_prius_rotor_overspeed_rev5_mesh/report.md), and the four dq tables `runs/2026112{3,4}-*_motor_prius_lut_*_rev5`
- Cases (predictions before each run, results after): `cases/motor_prius_*.toml`
- Client project: `validation/motor_ornl/STATUS.md` (short version), `CLIENT_DATA.md`, `DRAWING_AUDIT.md`,
  `CALIBRATION_PLAN.md` (every revision and diagnostic, predictions first); cases `cases/motor_prius_rev5_*.toml`;
  `scripts/motor_locked_rotor.py`
- Blind comparison: `validation/motor_ornl/RESULTS.md`, the data extracted from ORNL/TM-2006/423, and
  `scripts/motor_blind_comparison.py`; protocol log `reports/motor/blind_comparison_log.md`
- Detailed CAD: [`models/cad/prius_motor.py`](../models/cad/prius_motor.py) (section kept in
  `models/cad/prius_rev5_section.json`), [STEP](cad/prius_motor_rev5.step), tests `tests/test_prius_motor_cad.py`; the
  drawing's features measured by `scripts/motor_drawing_stator.py` into `validation/motor_ornl/drawing_stator/`
- Code: `models/motor/`, `studies/motor_em.py`, `studies/motor_torque.py`, `studies/motor_lut.py`,
  `studies/motor_efficiency.py`, `studies/motor_thermal.py` (with `models/motor/thermal_network.py`,
  `models/motor/stator_section_ccx.py`), `studies/rotor_stress.py`

# Traction motor, blind: the 2004 Prius motor rebuilt from published drawings

[Portfolio index](../PORTFOLIO.md) · Electric machines

> **Draft, in progress (2026-11-22).** Every prediction below was written before any of Oak Ridge National
> Laboratory's (ORNL's) measurements of this motor was opened. That test data stays sealed until the study is
> complete; the comparison against it is the last step. The full reports, with every run and the blind protocol
> log, are in `reports/motor/`.

| | |
|---|---|
| **Answer so far** | Blind predictions written: back-EMF 110.9 V rms line-to-line per 1000 rpm at 20 °C; torque 119-606 N m from 50 to 350 A rms (400 N m at about 168 A); an efficiency map with a 97.4 % peak (motor only). Design checks: the rated 400 N m fits inside the copper limit (REQ-M2 pass), and the rated 50 kW holds to 6000 rpm (58.6 kW, verified). Two fails a design review would want to know about: the open-circuit voltage at top speed is about 1040 V against a 500 V bus (REQ-M1), and the rotor bridges exceed the stand-in steel's yield at overspeed (424 against 335 MPa, REQ-M4). |
| **Discipline** | Electric machines: electromagnetics, losses, rotor stress |
| **Tools** | Pyleecan (geometry, drives FEMM), FEMM 4.2 (2D magnetostatics), CalculiX (rotor stress), Python |
| **Methods** | Machine rebuilt from published drawings (PDF vector data); open-circuit and loaded magnetostatics; maximum torque per amp; dq look-up tables with iron-loss coefficients; loss-minimising current search under voltage and current limits; mesh studies; a blind-validation protocol |

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
| REQ-M1: open-circuit voltage at 6000 rpm ≤ 500 V (inverter fault) | about 1040 V line-to-line peak | **Fail**, verified: the machine needs the inverter to hold its voltage down at speed |
| REQ-M2: 400 N m within 25 A/mm² of copper current density | 400 N m at about 168 A rms, 19.8 A/mm² | **Pass** |
| REQ-M3: every operating point within 25 A/mm² | the limit is 212 A rms; 250 A and above exceed it | **Fail** above 212 A (a short-time rating question) |
| REQ-M4: rotor bridges below yield at 7200 rpm overspeed | 424 MPa against 335 MPa (M330-35A) | **Fail**, verified; elastic at 6000 rpm (295 MPa). A stronger grade (M250-35A, 455 MPa typical) would pass |
| REQ-M5: rated 50 kW from base speed to 6000 rpm (500 V, 212 A) | 58.6 kW at the worst speed (6000 rpm), magnets and copper at 20 °C; 53.7 kW hot | **Pass** (verified cold; hot unverified) |

Blind predictions, for the comparison at the end: back-EMF **110.9 V** per 1000 rpm; MTPA torque **118.8 / 251.6 /
366.6 / 456.9 / 522.3 / 569.4 / 606.4 N m** at 50-350 A rms; an efficiency map from 500 to 6000 rpm, peaking at
**97.4 %** at 2500 rpm and 80 N m (cold), 97.0 % hot. These are motor-only efficiencies (copper and iron loss;
mechanical, magnet and inverter losses left out), so they are upper bounds on what a dynamometer would measure.

![Motor-only efficiency map, cold, with the torque limit at the 212 A design current](../runs/20261122-153450_motor_prius_efficiency_r1/points/p00_cold/response.png)

*(The white band between the map's edge and the torque-limit line is a plotting artefact of the contour fill next to
empty cells; the map's last feasible torque equals the limit at every speed.)*

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

## How I know it's right (before the test data)

- **Independent routes inside the model:** the power balance (Σ i·dφ/dt against torque × speed) checks FEMM's
  torque to 0.1-0.4 %; winding theory checks the flux linkage to 0.3-0.6 %; the dq torque equation checks the
  tables' fluxes; the efficiency tables reproduce the open-circuit and torque studies (2.7 × 10⁻⁶ and 0.2 %).
- **The rotor pipeline on an exact case:** a plain rotating disk matches the closed form to 4 × 10⁻⁴.
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
- **A leak in a blind protocol, recorded rather than hidden.** A line filter on one ORNL report let through some of
  ORNL's own *model* results (not measurements). They are logged with their time and declared in every case that
  followed; extraction is whitelist-only since.

## Limits

- 2D magnetostatics: no end effects, no eddy currents in the magnets, no AC copper loss.
- The lamination grade, the end-winding length and the copper temperature are estimates; their effects are bracketed
  or stated.
- Steady temperatures only (cold and hot corners); the thermal network is still to come.
- Validation against ORNL's measurements has not happened yet. Until it does, these are predictions.

## Evidence

- Reports: `reports/motor/` (overview, design inputs, open circuit, torque, efficiency), built from the runs by
  `reports/motor/build_report.py`
- Cases (predictions before each run, results after): `cases/motor_prius_*.toml`
- Code: `models/motor/`, `studies/motor_em.py`, `studies/motor_torque.py`, `studies/motor_lut.py`,
  `studies/motor_efficiency.py`, `studies/rotor_stress.py`

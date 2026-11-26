---
name: frame-requirements
description: Turn an engineering question (a client's design question, a spec, a "will this part / channel / suspension meet X?") into a case file with measurable requirements, units, operating conditions, input tolerances, assumptions paired with validity checks, and verification tolerances fixed before the first run. Use this before building or running any new simulation study, whenever the user describes a design question, a requirement, a pass/fail criterion, a tolerance study, or asks "does it meet...", "how sure are we...", "what gap/size/rate should...", and whenever a case file needs to be revised after a result.
---

# Frame requirements

Writes the case file (`cases/<name>.toml`) that a study is judged against. This
comes first: a model built before the question is pinned down tends to answer an
easier question than the one asked. The template is
[assets/case-template.toml](assets/case-template.toml).

This skill does not build models (`build-model`) or run them (`run-case`).

## Why the order matters

Requirements, metric definitions, and verification tolerances are fixed before
the first evidence run. If they are chosen after seeing results, every "pass" is
suspect, because the limits could have been moved to fit. Changing one later
is allowed, but only with a written reason, as a new or revised case, with the
earlier run kept as evidence.

## Procedure

### 1. Restate the decision

Write one or two sentences: what decision the result will inform, and what
answer would change it. "Does the channel stay within a 30 Pa pump budget across
the gap tolerance?" is a decision; "simulate the channel" is not. Show the
restatement to the user before going further.

### 2. Define each requirement so it measures what the hardware experiences

For each requirement: `id`, plain-language `text`, the `metric` the model will
compute, `operator`, `limit`, `units`, and where the limit came from (client
spec, standard, or synthetic).

The hard part is the metric definition. Ask what the real system sees, then
check that the metric measures that, not a convenient proxy:

- A pump must supply the inlet total pressure minus the outlet static pressure.
  The outlet dynamic head is usually lost in the outlet header. A total-pressure
  drop that stops at the channel exit leaves out about a quarter of the budget
  in the coolant-channel example.
- Peak stress at a sharp clamp corner or re-entrant edge is a singularity. It
  grows with mesh refinement and never converges, so a requirement on it can't
  be verified. Use stress extrapolated from the smooth region, or a linearized
  or hot-spot stress the governing standard defines.
- Comfort in vehicle dynamics is usually frequency-weighted (ISO 2631). If the
  metric is unweighted, say so as a limitation.
- A blanket electronics limit ("hottest component 85 C, mean air 60 C") is a
  proxy. Real thermal specs are per part, from datasheets and a derating policy:
  - junction at least 25 K under Tj max, the case limit following from the
    junction-to-case resistance times the power;
  - the laminate under its UL 796 MOT less a margin;
  - electrolytic capacitor life, about 2x per 10 K below its rating, at its
    position on the board;
  - other parts within their ambient rating.

  Study 11 found this late. Its bridge redesign cooled U1 but made the board
  hotter than U1. The blanket limit could not say whether that mattered, and the
  part-by-part list (`validation/enclosure/CLIENT_REQUIREMENTS.md`) changes which
  design is needed. Ask for the bill of materials, the datasheet limits and the
  part positions at framing. If the requirements change after results are known,
  record when they were written and the rule behind each limit.

  The outcome (2026-11-25, 14 settled runs): the capacitor's life governed, and
  no cooling path fixed it. With a painted interior the bridge cooled U1 by up
  to 33 K but C1 by under 9 K, because C1 sits on a board heated by its own 10 W. The answer that
  passes is a part change (a 125 C capacitor), and the limit for that part
  follows from the client's own rule, re-derived, not chosen. When a remedy
  targets one part, check that it reaches the part that governs. When only a
  part change passes, present it as the client's decision, with the derivation.

If the definition is a judgement call, state it in the requirement text and the
assumptions, so a reviewer can disagree with it explicitly. When the judgement could
decide the verdict, plan a case that varies it before reporting a thin margin: study
18's nozzle passed by 0.9 % on lines at the weld toes and failed by 24 % on a line
through the crotch, on the same verified model.

### 3. Operating conditions and input ranges

List every input with units: geometry, materials, loads, fluid properties
(with source, e.g. IAPWS tables), operating point. Then ask which inputs are
uncertain or toleranced: manufacturing tolerance, temperature range, load range.
In the coolant-channel example the input range (−16 % / +27 %) was hundreds of
times larger than the numerical uncertainty (0.04 %). A single nominal run would
have hidden that the requirements conflict.

Plan a scenario sweep (`[[sweep.scenarios]]`, each a named set of parameters)
for the corners of the input ranges. State what is held fixed (e.g. flow rate
fixed by the pump, so velocity follows the gap).

Tag every input with where a real project would get it (CLAUDE.md, "Use only information a real project would
have"): spec or datasheet (with its tolerance), a routine test on existing hardware, or teardown / answer-key data,
which a workflow may not lean on. When unsure, treat it as available and say so.

### 4. Assumptions, each with a check where possible

Every modelling assumption either gets a validity check or is listed as a
limitation. Examples from this repo:

| Assumption | Validity check |
|---|---|
| Linear tire, wheel stays on the road | dynamic tire load < static load |
| Linear elastic material | stress / yield < 1 |
| Small deflection | deflection / length below a set fraction |
| Laminar flow | Re below the transition limit |
| Fully developed where measured | entrance length ends before the window; profile constant across it |
| 2D (wide channel) | separate 3D check with side walls |

A validity failure means the model is the wrong tool for that point. It is
reported as such, not tuned away.

### 5. Verification tolerances

For each check the study will run, set a tolerance and a one-line reason in the
TOML comment. Base it on what the decision needs, not on what you expect the
model to achieve:

- Exact references (closed form, exact series): tight, e.g. 1 % on the
  requirement metric, 1e-6 on conservation.
- Model-form references (correlations, beam theory for a 3D solid, lubrication
  theory): looser, and labelled as model form, with the reason (e.g. "correlation
  assumes a uniform entry profile; guards against gross errors only").
- Mesh convergence: GCI limit on each requirement metric.
- Iterative convergence: on the quantity of interest, not only residuals.

### 6. Write predictions before confirmation runs

When a run is meant to confirm an estimate (a scaling result, a limit, a
hand calculation), write the predicted value and how it was derived into the
case file header before running. A prediction that holds is strong evidence;
one written afterwards is not.

### 6a. Blind validation against test data

When test data exists for the comparison (study 7: ORNL's Prius measurements), keep it sealed until every
prediction is written into a case file.

- Read reports that mix design data and test data by **whitelist**: print only lines matching design terms, with
  numbers masked unless they are what you need. A blacklist of performance words leaks: table values sit on their
  own lines and labels are abbreviations (study 7 saw ORNL model results this way, and recorded it).
- Render only the figure you need, cropped to its image block; check what else shares the page.
- Material properties measured by the same lab are a judgement call for the user, not for you.
- Keep a protocol log (what was opened, when, why) and declare any prior knowledge in the case headers. Take every
  time from the clock (`date`), never from memory: study 7's revision log carried two times 15-25 min ahead of the
  clock until they were corrected, and a third because `date` ran in the same command that wrote the entry. Run
  `date` on its own first, read it, then write.
- Agree the validation limits before the data is seen; after that, any change is a documented revision.
- Agree how the data will be read at the same time: line-to-line or phase, peak or rms, which table or figure, what
  temperature. Test reports often don't say (study 7: the back-EMF and locked-rotor tables state neither, and the
  torque comparison swings from +7 % to +60 % on the current convention).
- Give each prediction a band from its largest input uncertainties, and check the agreed limit is reachable with it.
  Study 7 bracketed inputs that hardly mattered (lamination grade, 0.13 %) and carried none of the one that did: two
  sources gave the magnet's remanence as 1.24 and 1.12 T (11 % in back-EMF). The blind back-EMF missed by 24 %; a band
  would have shown before the data that a 5 % limit was a gamble.
- When sources conflict, carry both until the data decides; don't pick one and explain the other away ("probably a
  hot value" was never checked).
- Compare the statistic the test reports, not the one the model prints by default. ORNL's locked-rotor torque is
  the largest over shaft angle, ripple included; the model's MTPA torque is a mean. At 50 A the model's mean read +4 %
  and its emulated maximum +17.5 %; comparing the mean with the maximum also produced a false "ORNL's tests disagree"
  diagnosis (study 7, 2026-11-23, withdrawn). Emulate the test's procedure from the model's saved data
  (scripts/motor_locked_rotor.py) before reading any difference.
- When paired quantities miss in opposite directions (study 7: Ld -10.6 %, Lq +10 %), no convention or scale factor
  can be the cause; split them into the mean and the difference (mean +4.3 %, saliency term +22.7 %) and ask what
  changes only the difference. If the answer is in how the test was made and the client documents do not say, it is
  a client question, not a model revision (scripts/motor_inductance_frame.py).
- Check that a hand estimate's simplifications hold across the whole band, not only at its nominal point. Study G's
  Rayleigh estimate (17/35 of the shaft mass at mid-span, the factor for a simply supported mode shape) matched ROSS
  within 0.2 % on stiff bearings but ran 2 % high on soft ones: with soft bearings the shaft also translates, so more
  of its mass takes part. A case right at a limit (60 mm, margin 14.3 % against 15) is where that 2 % decides the
  verdict: widen the band at the soft end or run that corner before predicting its side of the limit.
- Predict the quantity that is measured. A loss model that leaves terms out by design (mechanical, inverter
  harmonics) gives an upper bound, not a prediction of a measured efficiency: estimate the missing terms, or set the
  limit with them in mind (study 7: 5.2 points high against a 2-point limit).
- Internal checks verify the solver on your inputs, not the inputs: study 7 passed every one (power balance, winding
  theory, mesh studies) with the magnet flux 24 % high.
- After a blind miss, keep the verdict on the record. Test data used to diagnose or calibrate stops being evidence;
  validate the revision on quantities that weren't used (calibrate one, predict the rest).
- When two explanations both fit the calibration, choose between them with the cheapest routine measurement that
  separates them (resistance, inductance, a tap test), not with the next high-value test. Study 7 first chose with
  the locked-rotor torque: a weak discriminator (8.7 % against 10.7 % rms error) that then stopped being evidence. A
  turns error scales resistance and inductance by k^2 and a magnet error does not, so the static inductances separate
  them by 35 % (the user asked whether a contract job would even have the torque data; often it would not).
- After a calibration, re-run every design verdict that depends on the calibrated quantity before reporting it. Study 7's
  rated-power requirement (50 kW to 6000 rpm) passed with the blind model (58.6 kW) and failed with the calibrated
  magnets (48.0 kW): less magnet flux, less field-weakening torque per ampere. I had predicted the opposite from
  voltage headroom; check the sign with the torque equation, not intuition.
- In field weakening the voltage limit, not the magnets, sets the stator flux, so a weaker magnet barely changes the
  iron loss there. Study 7's revision 5 (back-EMF 4.6 % lower) was predicted to gain up to 0.3 point at light load
  above 3000 rpm from less iron loss; iron loss moved 0.1-1 %, and the 15 % higher measured resistance plus 2-4 %
  more current won (-0.04 to -0.40 point). Predict a map change from its loss split (copper against iron at that
  point, and which one the change touches), not from the flux alone.
- Transcribe a test table before reasoning from it: run-together PDF text puts a frequency column where the voltage
  should be (study 7, caught before scoring).
- Audit every column of a transcription, not only the ones being scored: check each row against identities in the
  table itself (speed x torque = mechanical power; efficiency = output / input power). Study 7's Table B-1 scored
  columns were right on all 428 rows, but the stator temperature was empty in every row and the phase voltage and
  current shifted in 345 (three rows lacked one value); nobody noticed for a day because nothing used them, until the
  temperature was the next thing needed.
- After the blind comparison, more test material may be opened to diagnose and document (user, 2026-11-23: "we can
  open up as much of the ORNL data as we want ... we just need to make sure we don't USE anything we wouldn't be
  provided with a real job"). Opening and using are different: a model input, a calibration or a choice between
  hypotheses may rest only on what a client would provide (specs, datasheets, routine tests such as back-EMF,
  resistance, inductance, no-load losses, and the operating conditions recorded with a test). Teardown-only data
  (study 7: the measured air-gap flux map) may be looked at and reported, never fed back into the model. When the
  line is unclear, ask, and log the decision either way.
- Even when data is allowed, locate it with a masked search, write the method and predictions, then open it once.
  Study 7 revision 2 predicted that ORNL's no-load spin loss would exceed the model's open-circuit iron loss 1.3-2.5
  times and close a 4.5-point efficiency gap; it matched the model (0.87-1.35) and moved the gap by 0.02 points. The
  miss was the finding: the gap is load-dependent.
- Isolate each effect and test it locally before carrying the model further (user, 2026-11-23: "otherwise
  calibration moves error elsewhere and hides it"): one change per revision, scored on its own against its own
  reference or measurement, with every geometry difference and assumption tracked in the case. Calibration is
  sometimes acceptable but is the risky option: when used, state what it could be hiding and re-test the quantities
  it was not fitted to.
- A calibrated value far outside its own measurement is a model-form alarm, not a material finding. Study 7's
  back-EMF fit needed the remanence at 1.036 T against the 1.243 T measured on a sample (-17 %, about four times any
  plausible material scatter). Both hypotheses on the table were knobs (remanence, turns); none was "the model is
  not the drawing". It was: the magnet filled its pocket. Modelled as drawn, with the material as measured and
  nothing fitted, the back-EMF came within 4.6-11 % (revision 4), from +23.5 % blind. Order: geometry and template
  fidelity first (build-model step 3), then material and conditions, calibration last; and when a fit is needed,
  list model-form causes as hypotheses beside the parameter ones.
- A calibration makes the fitted quantity right by construction and says nothing about the others. A wrong knob
  can match the back-EMF exactly and still misplace inductance, saturation, leakage and torque per ampere, because
  it changes the material where the model's error was in the circuit. Prefer the explanation that reproduces the
  measurement without fitting, then check it on quantities it was not tuned to.
- Match the test's operating conditions with what the test recorded before blaming the model: study 7 assumed one
  winding temperature (100 C); ORNL logged 43-207 C per point, and using it closed 0.45 points of the gap and a
  quarter of the missing loss at high torque (revision 3).
- Before using, dismissing or explaining away a number from a source, read the source's own definition of it: its
  abbreviation, glossary or parameter list, and the condition (temperature, load, units) it is stated at. Separate a
  source's measurements and hardware facts from its own design-study model inputs; the latter are neither data nor
  errors. Study 7 read ORNL's design-report "magnet strength" of 1.12 T as a value lowered to compensate a filled pocket;
  the report labels it BrT and defines Br as the remanence at 20 C, and 1.243 T at -0.1 %/C is 1.12 T at about
  119 C: most likely a hot value (corrected the same day, CALIBRATION_PLAN.md). Do not infer intent from a sketch.
- Assemble the client data pack BEFORE the first model revision, not one item per revision: drawings, bill of
  materials with masses, material data, routine tests, and the reports that benchmark the same hardware later.
  Cross-check every dimension that drives a revision against an independent quantity (mass, volume, density). Study
  7 revision 4 rested on a 5.31 mm magnet from a design-study table; a later benchmark report (ORNL/TM-2010/253
  Table 2.7) gives 6.5 mm, 10.2 cm3 and 77 g, and 77 g at 5.31 mm would need 9.1 g/cm3, impossible for NdFeB. One
  search for "2004 Prius magnet mass" would have prevented a revision built on a wrong input (user, 2026-11-23:
  "stop guessing values ... stop being afraid to view things that we would usually have").
- When a report's text leaves out a fact (a material, a part, a length), look at its photographs and drawings
  before calling it unknown. A part photographed next to a known material in the same light is evidence; record it
  as "from the photo", carry the other case as a band, and still put it to the client. Study 7's rotor end clamping
  piece: no material in any text; TM-2004/137 Fig. 9 shows a copper-coloured disc beside grey laminations (non-
  magnetic, so end leakage of 1-2 %, not the large short a steel plate would give), and the same photo gives the
  rotor stack, 3.290 in, against the model's 83.82 mm.

### 7. Missing information

List what the user has not specified (a width, a tolerance, a temperature
range). Ask for it. If the user wants to proceed anyway, choose a value, mark it
"synthetic" in the assumptions, and say how the result scales with it.

## Revising a case after a result

- Never loosen a tolerance or move a limit to make a run pass.
- Keep the failed run in `runs/`; it is evidence.
- Write a new case (or a clearly versioned revision) whose header says what
  failed, why, and what changed. Examples: `qc_bump` → `qc_speed_bump` (wheel
  lift-off at 36 km/h), `channel_mesh` → `channel_header_mesh` (singular inlet).
- If a smoke test (a coarse run in the scratchpad, not in `runs/`) shows a metric
  definition or convergence criterion is wrong, it may be changed before the
  evidence run. Record that in the case header: what the smoke test showed and
  that the limit itself did not move.
- Before an expensive revision, test the cheapest suspect with a scratch probe and
  put its numbers in the new header (study 6: a finer solid moved the drifting
  displacement 0.035 %, so the 6-hour revision kept the solid and changed the fluid
  meshes). Probe the finest planned level's cost too, and change one thing at a
  time: study 19's r1 changed the mesh family and the axial length together, and the
  length change alone stalled the solver (the probe had shown f unchanged, but not
  the convergence rate at the finer levels).
- When the coarsest level is outside the asymptotic range (an apparent order far
  from the design order), drop it and add a finer one; do not keep it for continuity.
- If the revision needs an input that does not exist yet (a run id), commit the
  predictions first with a placeholder that cannot run, then fill it in a separate
  commit that says the predictions are unchanged.
- After the run, score every prediction in a Results block in the header: HELD,
  PARTLY or MISSED, with the reason. Misses stay in; they are the record of what
  the model taught you. Edit only comments then: `tests/test_case_records.py` fails when a
  case's settings no longer equal its latest committed run's `inputs/case.toml`; a
  changed setting is a new case or revision, never an edit after the run.

## Output

1. `cases/<name>.toml` from the template, validated with
   `.venv/Scripts/python.exe -c "from harness.case import load_case; load_case('cases/<name>.toml')"`
   (needs the model registered; before `build-model` has run, check the
   structure by eye against the template).
2. A short message to the user: the decision, the requirements with their
   sources, the input ranges, the assumptions that are synthetic, and the
   questions still open.

## Human judgment needed

The requirement limits, which input ranges matter, and whether a metric
definition matches the real system. Propose; let the user decide.

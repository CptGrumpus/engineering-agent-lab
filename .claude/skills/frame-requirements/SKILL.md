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

If the definition is a judgement call, state it in the requirement text and the
assumptions, so a reviewer can disagree with it explicitly.

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
- Keep a protocol log (what was opened, when, why) and declare any prior knowledge in the case headers.
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
- Predict the quantity that is measured. A loss model that leaves terms out by design (mechanical, inverter
  harmonics) gives an upper bound, not a prediction of a measured efficiency: estimate the missing terms, or set the
  limit with them in mind (study 7: 5.2 points high against a 2-point limit).
- Internal checks verify the solver on your inputs, not the inputs: study 7 passed every one (power balance, winding
  theory, mesh studies) with the magnet flux 24 % high.
- After a blind miss, keep the verdict on the record. Test data used to diagnose or calibrate stops being evidence;
  validate the revision on quantities that weren't used (calibrate one, predict the rest).
- Transcribe a test table before reasoning from it: run-together PDF text puts a frequency column where the voltage
  should be (study 7, caught before scoring).

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
  the model taught you.

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

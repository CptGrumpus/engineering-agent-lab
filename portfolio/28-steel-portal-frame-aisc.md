# Steel portal frame to AISC 360-22, by the Direct Analysis Method

[Portfolio index](../PORTFOLIO.md) · Structures and machines

| | |
|---|---|
| **Answer** | The equipment-platform frame (W10x33 columns 4.0 m, W14x30 beam 6.0 m, fixed bases, ASTM A992) **passes all three of the client's requirements** under their factored loads (35 kN/m on the beam, 15 kN lateral): the largest combined axial-and-bending ratio (AISC Eq. H1-1) is **0.80**, in the beam under gravity plus wind, governed by lateral-torsional buckling over its unbraced 6.0 m span; the columns reach 0.45. Live-load deflection **4.1 mm** (limit L/360 = 16.7 mm), service drift **2.6 mm** (limit H/400 = 10.0 mm). The beam's bracing was not specified, so it was taken as unbraced (conservative): bracing it at midspan cuts the largest ratio to **0.48**, and the verdict does not depend on it. Verification: the analysis reproduces AISC's own worked Direct Analysis Method example (C.1A) within 0.7 % on forces and 1.7 % on drift; the member checks reproduce 12 worked answers of the AISC Design Examples within 0.5 %; first-order moments match the closed-form portal solution to 4e-9; AISC's approximate B1-B2 method agrees with the exact second-order moment to 0.05 %. The client and loads are synthetic. |
| **Discipline** | Structural steel design: frame stability and member design to a building code |
| **Tools** | Python (a plane-frame solver written and verified for this study), AISC 360-22 and the v16.0 Design Examples |
| **Methods** | Second-order plane-frame analysis by the direct stiffness method with exact stability functions (P-Delta and P-delta); the Direct Analysis Method (80 % stiffness, notional loads, effective length = unbraced length); AISC 360-22 Chapters E (with slender-web effective area), F, G and H; serviceability |

## The question

A client's equipment platform rests on a single-bay steel portal: two W10x33 columns 4.0 m tall with fixed bases,
rigidly connected to a W14x30 beam spanning 6.0 m, all ASTM A992 (yield 345 MPa). The client gives the factored
loads (LRFD): 35 kN/m on the beam and 15 kN lateral at beam level; and the service loads: 12 kN/m live and 10 kN
lateral. Does the frame meet AISC 360-22?

| ID | Requirement | Limit |
|---|---|---|
| REQ-A1 | Every member's combined axial and flexural ratio, Eq. H1-1, by the Direct Analysis Method | at most 1.0 |
| REQ-A2 | Beam deflection under the service live load | L/360 = 16.7 mm |
| REQ-A3 | Frame drift under the service lateral load | H/400 = 10.0 mm |

## The answer

| Member | Gravity + notional load | Gravity + lateral load | Governing limit state |
|---|---|---|---|
| Beam (W14x30) | 0.789 | **0.801** | Lateral-torsional buckling, unbraced 6.0 m (Cb 1.26) |
| Leeward column (W10x33) | 0.385 | 0.452 | Flexure near the plastic moment (Cb 2.2), small axial load |
| Windward column | 0.381 | 0.313 | |

**All three requirements pass.** Shear is far from critical (at most 22 % of capacity). The frame is stiff: the
second-order drift is only 2 % above the first-order drift, so stability effects are small, and the notional loads
need not be added to the wind case (Specification C2.2b(d): only above a ratio of 1.7).

**The beam's bracing decides the margin, not the verdict.** The client has not said how the beam is braced against
lateral-torsional buckling. The base case takes no credit for the platform deck (unbraced over 6.0 m). If the deck
or a brace holds the beam's compression flange:

| Beam unbraced length | Largest ratio | Governing |
|---|---|---|
| 6.0 m (no bracing; the base case) | 0.801 | the beam |
| 3.0 m (braced at midspan) | 0.477 | the beam |
| 1.5 m (quarter points; below Lp = 1.60 m) | 0.452 | the leeward column (beam 0.389) |

**Questions for the client:** how is the beam braced (deck attachment, kicker braces)? And is the frame braced out of
its plane at the beam level, as assumed for the columns' weak axis?

## How it works

- **Analysis.** A plane-frame solver by the direct stiffness method, with the exact stiffness of a member under axial
  load (stability functions), so both P-Delta (frame sway) and P-delta (member bowing) are exact without subdividing
  members; second order by iterating on the axial forces. Members can carry end hinges (needed for leaning columns).
- **Direct Analysis Method** (Specification Chapter C): every stiffness reduced to 80 %; notional loads of 0.2 % of
  the gravity load to stand for out-of-plumbness; the extra reduction tau_b checked (axial load about 5 % of the
  squash load, so tau_b = 1); effective length equal to the unbraced length.
- **Member checks** (Chapters E, F, G, H): compression with the effective area of the beam's slender web (h/tw 45.4 >
  35.9, Section E7), flexure with lateral-torsional buckling and flange local buckling (the column's flange is
  compact by 0.002 on the ratio), web shear, and the H1-1 interaction. Cb is computed from each member's own
  second-order moment diagram.
- **Serviceability** with full (unreduced) stiffness: the beam's live-load deflection relative to its ends, and the
  drift under the service lateral load with the live load on the beam, second order.

## How I know it's right

- **The analysis against AISC's own worked example.** Design Example C.1A (a pinned-base portal with a leaning
  column, by the Direct Analysis Method) rerun inside every point: drift 0.288 against 0.290 in., knee moments 109 and
  128 against 109 and 127 kip-ft, base shears and reactions within 0.7 %.
- **The member checks against the worked answers of nine AISC Design Examples** (and the Manual table values one
  of them uses): columns E.1C, E.1D and E.1E (a
  slender web at three lengths), beams F.1-1B, F.1-2B and F.1-3B (yielding, inelastic and elastic lateral-torsional
  buckling) and F.3B (a noncompact flange), shear G.1B, interaction H.1B and its table values; all within 0.5 %
  except where the example rounds an intermediate value (0.8 %, stated in the test).
- **First order against the closed form** for a fixed-base portal (Kleinlogel): knee moment under the beam load and
  base moment under the lateral load agree to 4e-9.
- **Second order two ways**: the exact solution against AISC's approximate B1-B2 method (Appendix 8): 0.05 %.
- **Equilibrium** to 3e-14; the same answer with 2 or 8 elements per member (3e-10).

## What the checks caught

- **A wrong check, and a commit that went in with it failing.** The C.1A equilibrium test first compared the
  leaning column's base shear with the frame's average drift; the leaning column sways with the column it is tied to. A shell pipe (`pytest | tail`) hid the failure from the commit gate; the fix and the rule
  (gate commits on the test runner's own exit code) are recorded.
- **The approximate method's lateral case carried the gravity load a second time**, so B1-B2 came out 85 % above the
  exact moment (148 against 80 kN m). With the "no translation" and "lateral translation" analyses properly
  separated, B2 = 1.02 and the two agree to 0.05 %.
- **The column's flange sits on the compact limit**: bf/2tf 9.15 against 0.38 sqrt(E/Fy) = 9.152, compact by 0.002.
  The comparison is made at full precision and the test pins the classification, so a change in rounding or in the
  section data shows up as a failing test, not a silent change of limit state.

## Limits

- Plane frame; rigid knees and fixed bases assumed adequate (connections, base plates and anchors not designed).
- The bracing assumptions above (beam unbraced; columns braced out of plane at the beam).
- Loads as given by the client (no load derivation); no dynamic, fatigue or vibration assessment of the equipment.
- The prediction for the base case was not blind (a development run printed the values first; the case file says
  so); the evidence is the checks above, and the bracing sensitivity's predictions were made before its run.
- Synthetic client and loads.

## Evidence

- Base case: [`steel_frame_portal`](../runs/20261125-231923_steel_frame_portal/report.md); bracing sensitivity:
  [`steel_frame_beam_bracing`](../runs/20261125-231927_steel_frame_beam_bracing/report.md); cases with predictions and
  results: `cases/steel_frame_portal.toml`, `cases/steel_frame_beam_bracing.toml`
- Code: `validation/frame2d.py` (solver, tests in `tests/test_frame2d_reference.py`), `validation/aisc_frame.py`
  (Direct Analysis Method portal, `tests/test_aisc_frame.py` against C.1A), `validation/aisc360.py` (member checks,
  `tests/test_aisc360.py` against the Design Examples), `studies/steel_frame.py`
- References: ANSI/AISC 360-22 and the v16.0 Companion Design Examples, free from AISC (not redistributed); section
  properties from the AISC Shapes Database v16.0 (the shapes used: `validation/aisc_shapes_subset.json`)

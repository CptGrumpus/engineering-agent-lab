# Sealed electronics enclosure: natural convection and radiation, and what it takes to pass

[Portfolio index](../PORTFOLIO.md) · Thermal and fluids

| | |
|---|---|
| **Answer** | The sealed aluminium box as drawn (150 x 60 mm section, 200 mm deep; a board carrying 10 W with a 5 W regulator U1; 40 C ambient) **fails the client's requirement list**. With a painted interior (emissivity 0.9), U1, the board laminate and the internal air pass, but the bulk capacitor C1 runs at **89-91 C** against its **70 C** life limit (about 15,000 h of the 50,000 h asked). With a bare-metal interior (0.1) everything fails (U1 157-164 C, C1 149-153 C). **No bridge or shell fixes C1 with the part as specified**: C1 sits on a nearly isothermal board, so the best redesign still holds it at **76.9 C**. **What passes everything**: a painted interior, C1 changed to a **125 C, 5,000 h** capacitor (its life limit becomes 90 C by the client's own derating rule), and a thermal bridge from U1 to the lid of at least **2 W/mK** effective conductivity for margin: at 2-5 W/mK, C1 is at **79-82 C** (8-11 K under its new limit), U1 at **69-77 C** (limit 115), the board at **79-82 C** (limit 105), the air at **62-63 C** (limit 70). The part change is the client's decision. Verification: each model part checked against an exact or benchmark answer first (natural convection within 0.6 % of de Vahl Davis; radiation within 0.9 % of exact exchange); every final run settled (heat balance within 0.05 %), and the settled values land within 0.02 K of the extrapolations made from shorter runs; a 1 mm mesh moves the result by 0.05 K. The client, loads, limits and parts are synthetic. |
| **Discipline** | Electronics cooling: conjugate heat transfer with natural convection and radiation |
| **Tools** | OpenFOAM 14 (foamMultiRun, fvDOM radiation), Python |
| **Methods** | 2D conjugate heat transfer (air, board, component, aluminium shell, bridge), laminar natural convection with a perfect gas, grey diffuse radiation by the discrete ordinates method, transient to a settled state; staged verification against benchmarks; corner study over the uncertain inputs; per-part limits derived from datasheets and a derating policy |

## The question

A sealed aluminium enclosure (2D section 150 x 60 mm, 200 mm deep) holds a 100 x 2 mm circuit board at mid-height that
dissipates 10 W, with a 20 mm regulator U1 on it dissipating 5 W. Outside: still air at 40 C (convection 5 W/m2K, paint
emissivity 0.85). The interior finish is open (emissivity 0.1 bare to 0.9 painted) and the board's in-plane
conductivity is uncertain (copper planes: bracketed at 5 and 20 W/mK). Does the design meet the client's thermal
requirements at every combination, and if not, what fixes it?

**The requirements came in two rounds.** The first brief gave two blanket limits: hottest component 85 C (REQ-D1) and
mean internal air 60 C (REQ-D2). Blanket limits are proxies, so the client was asked for per-part data, and sent a
requirement list with datasheet values and a derating policy ([`CLIENT_REQUIREMENTS.md`](../validation/enclosure/CLIENT_REQUIREMENTS.md),
revision B, synthetic):

| ID | Requirement | Limit | Derived from |
|---|---|---|---|
| REQ-E1 | U1 junction at or below 125 C | U1 case 115 C | Tj max 150 C less 25 K; 2.0 K/W x 5 W junction to case |
| REQ-E2 | Board laminate at or below 105 C anywhere | 105 C | FR-4 maximum operating temperature 130 C less 25 K |
| REQ-E3 | C1 (105 C, 5,000 h electrolytic, 5-15 mm from the board's left end) lasts 50,000 h | 70 C | Life doubles per 10 K below rating: 71.8 C, rounded down for ripple heating |
| REQ-E4 | Commercial-grade parts within their 0-70 C ambient rating | Internal air 70 C | Their datasheet rating |

For the record: revision B was written after the first redesign results were known (but before the final, settled
runs), so it is not a blind test. Every limit is derived from a stated rule, so none was chosen to make a design
pass. The first round's verdicts stay on record below.

## The answer

**As drawn** (settled runs, 9,000 s of simulated time for the bare interior):

| Board | Interior | U1 (REQ-E1, 115 C) | Board max (REQ-E2, 105 C) | C1 (REQ-E3, 70 C) | Air (REQ-E4, 70 C) |
|---|---|---|---|---|---|
| 5 W/mK | 0.9 | 98.4 C pass | 95.8 C pass | **89.2 C FAIL** | 66.9 C pass |
| 20 W/mK | 0.9 | 94.2 C pass | 93.4 C pass | **90.9 C FAIL** | 67.0 C pass |
| 5 W/mK | 0.1 | **164.3 C FAIL** | **160.7 C FAIL** | **149.4 C FAIL** | **84.3 C FAIL** |
| 20 W/mK | 0.1 | **157.4 C FAIL** | **156.4 C FAIL** | **152.7 C FAIL** | **84.5 C FAIL** |

A bare interior sheds the board's heat almost only by convection (radiation carries 23 % of it, against 75 % when
painted), and nothing survives it. With paint, only C1 fails: at 89-91 C an electrolytic rated 5,000 h at 105 C lasts
about 13,000-15,000 h, not 50,000.

**The redesign** (5 W/mK board, the worse for U1): the walls become a 2 mm aluminium shell (it conducts along the walls,
which a boundary condition cannot), and a bridge (a thermal pad or a pillar with a gap pad) joins U1's top to the lid
across the 29 mm gap. Settled values, 9,000 s:

| Bridge | Interior | U1 | Board max | C1 | Air | Fails |
|---|---|---|---|---|---|---|
| none (shell only) | 0.9 | 95.6 C | 93.6 C | 85.4 C | 65.8 C | E3 |
| 1 W/mK | 0.9 | 84.3 C | 84.8 C | 84.6 C | 64.2 C | E3 |
| 2 W/mK | 0.9 | 77.5 C | 82.1 C | 82.1 C | 63.1 C | E3 |
| 5 W/mK | 0.9 | 69.4 C | 79.2 C | 79.2 C | 61.8 C | E3 |
| 20 W/mK | 0.9 | 62.6 C | 76.9 C | 76.9 C | 60.6 C | E3 |
| none (shell only) | 0.1 | 154.6 C | 152.7 C | 129.9 C | 80.8 C | all four |
| 1 W/mK | 0.1 | 107.0 C | 116.6 C | 116.6 C | 72.1 C | E2, E3, E4 |
| 2 W/mK | 0.1 | 90.8 C | 107.0 C | 107.0 C | 69.0 C | E2, E3 |
| 5 W/mK | 0.1 | 75.6 C | 97.9 C | 97.9 C | 65.8 C | E3 |
| 20 W/mK | 0.1 | 65.2 C | 91.6 C | 91.6 C | 63.5 C | E3 |

The bridge cools U1 a great deal but C1 only a little. Once U1 is cooled, the board's own 10 W makes its far ends the
hottest part, and C1 sits at the left end (in every bridged run, C1's footprint holds the board maximum, within 0.2 K).
Moving C1 along the board does not help either: as drawn the coolest point of the board is its very end, 87.1 C,
only 2 K under C1's footprint.

**Recommendation** (for the client to approve, since it changes a part):
1. **Paint the interior** (emissivity 0.9 or better). With bare metal every design fails at least one requirement,
   and even with the new C1 below, the 5 and 20 W/mK bridges leave it at 97.9 / 91.6 C, over its 90 C limit.
2. **Change C1 to a 125 C, 5,000 h electrolytic.** By the client's own rule its life limit becomes 125 - 10 log2(10) =
   91.8 C, 90 C after the same 1.8 K ripple allowance. (A 105 C, 10,000 h part gives 80 C: too tight.)
3. **Add a bridge of at least 2 W/mK** effective conductivity (U1's width, full gap: 3.6 K/W through the box's depth
   at 2 W/mK, 1.45 K/W at 5). With paint and the new C1: C1 at 82.1 C (2 W/mK) or 79.2 C (5 W/mK) against 90 C, U1 at
   77.5 / 69.4 C against 115 C, the board at 82.1 / 79.2 C against 105 C, the air at 63.1 / 61.8 C against 70 C.
   Without a bridge the new C1 would pass by only 4.6 K (85.4 C, shell only) and as drawn not at all on the 20 W/mK
   board (90.9 C).

**The first round's verdicts** (REQ-D1 hottest component 85 C, REQ-D2 mean air 60 C), kept for the record: as drawn
both fail at every corner; a bridge of at least 5 W/mK meets REQ-D1 at both finishes (69.4 / 75.6 C); REQ-D2 fails in
every design (60.6-84.5 C). Revision B replaced both: the 60 C air limit had no part behind it.

## How it works

- **One model, conjugate heat transfer.** OpenFOAM's multi-region solver couples the air (laminar natural convection,
  perfect gas, buoyancy), the solid board and U1 (volumetric heat sources), and in the redesign the aluminium
  shell and the bridge. The board is solid so it spreads heat: a first prototype with fixed surface fluxes put U1
  at 154 C.
- **Radiation** between the inside surfaces by the discrete ordinates method (grey, diffuse; the air transparent).
- **Transient to a settled state**: a steady coupled solve looked converged for thousands of iterations and then
  diverged, so every run marches in time until the temperatures stop moving, and the heat balance confirms it.
- **Outside**: convection and radiation to ambient on the shell's outer faces.
- **Per-part metrics**: U1's hottest point, the board's maximum, and C1 as the largest board temperature under its
  footprint, read from each run's final temperature field.

## How I know it's right

- **Stage 1, natural convection**: the square cavity of de Vahl Davis (Rayleigh 1e3-1e6): Nusselt number and peak
  velocities within 0.05-0.62 % of the benchmark table; a three-mesh study at Rayleigh 1e6 converges the Nusselt number
  to 0.07 % of the benchmark (one peak velocity's convergence order came out anomalous: reported, not hidden).
- **Stage 2, radiation**: grey exchange between concentric cylinders against the exact two-surface formula: 0.92 %
  at the 4 directions per quarter the box runs use (limit 1 %), 0.21 and 0.05 % at 8 and 16; 0.11-0.21 % over
  emissivities 0.1-0.9 at 8 directions.
- **Settled, and checked by energy**: heat leaving the box against the 15 W put in closes to under 0.01 % in the
  as-drawn runs and under 0.05 % in the redesign runs (limit 1 %); the temperatures moved by under 0.01 K over the
  last tenth of each run.
- **Predictions held**: every final value was predicted before its run, from shorter runs extrapolated to the settled
  state, to within 0.3 K. All 14 landed within 0.02 K; every requirement verdict predicted for them held, and the
  three C1 verdicts predicted as uncertain (redesign, painted, 2-20 W/mK) came out as fails.
- **Mesh**: the 20 W/mK, emissivity-0.9 corner on 1 mm cells (2 mm in the study) moves U1 by 0.05 K and the air by
  0.13 K.

## What the checks caught

- **Energy created by a boundary-condition name.** With two pattern-matched names for the solids' interfaces, the
  general one also matched the air interface, so the board never lost its radiated heat: the walls shed 671 W/m2
  against 178.6 put in. The heat balance caught it; explicit interface names fixed it.
- **A wall boundary condition cannot spread heat.** Modelling the walls as a boundary condition loses each face's heat
  where it arrives: fine for the original design, wrong for a bridge that dumps 5 W into a 20 mm strip of lid (it would
  sit about 110 K above ambient). The redesign models the walls as a solid shell.
- **A 1.9 % accounting error that looked like an unsettled run.** Six redesign runs failed the 1 % heat balance by
  1.2-2.9 %. The cause was my post-processing: it multiplied the wall fluxes by one 2 mm face area, but the mesher
  rounds each block to whole cells, so the box's perimeter came out 1.9 % short. With exact face areas (now read from
  the mesh, with a test) the totals showed the real issue: the shell and bridge give the box a slow mode (time constant
  about 20 minutes), so the first 1-hour runs had not settled. The settling check on U1 alone had passed every one of
  them: it is too weak for a slow mode, and the heat balance is now the settling test. The 2.5-hour reruns confirmed
  the extrapolated values to 0.02 K.
- **A blanket limit hid the part that decides the design.** Under the first brief the bridge looked like the answer
  (U1 passes at 5 W/mK). Asking for per-part limits showed that the capacitor's life governs, and that no bridge fixes it.
- **My predictions were wrong in instructive ways**: the 1 W/mK bridge ran 15 K cooler than my hand estimate, and at
  low emissivity the bridges ran 2.5-22 K hotter than at high emissivity, not "a few K"; the shell alone helped 8.6 K at
  low emissivity against 2.8 K at high. Each miss is written into its case file next to the prediction.

## Limits

- 2D section: the box's end walls are left out (less wall area, conservative); a 3D model would credit them.
- Laminar flow (Rayleigh number about 1e5-1e6 on the box height), grey diffuse surfaces, transparent air.
- Radiation at 4 directions per quarter: 0.92 % from exact in the stage-2 test, and radiation carries about 75 % of
  the walls' inside heat with a painted interior.
- C1 is represented by the board temperature under its footprint (its own ripple loss is covered by the client's
  1.8 K allowance); U1's hottest model point stands for its case (conservative); REQ-E4 uses the mean internal air,
  since a 2D section has no local air per part.
- The redesign was run on the 5 W/mK board only. As drawn, the 20 W/mK board puts C1 1.7 K hotter; the recommended
  design's 8-11 K margin covers that, but it is not run.
- The bridge is one effective conductivity standing for a pillar and its gap pad, with perfect contact; a real pad's
  contact resistance must be added to the thermal-resistance budget.
- Synthetic loads, limits, parts and outside conditions; no test data.

## Evidence

- Stage 1: [`cavity_devahldavis`](../runs/20261124-105442_cavity_devahldavis/report.md),
  [`cavity_mesh_ra1e6`](../runs/20261124-105444_cavity_mesh_ra1e6/report.md); stage 2:
  [`annulus_angular`](../runs/20261124-110740_annulus_angular/report.md),
  [`annulus_emissivity`](../runs/20261124-110742_annulus_emissivity/report.md)
- As drawn, against revision B: [`k5, 0.9`](../runs/20261125-162808_enclosure_k5_eps0p9_e/report.md),
  [`k20, 0.9`](../runs/20261125-162813_enclosure_k20_eps0p9_e/report.md),
  [`k5, 0.1`](../runs/20261125-162817_enclosure_k5_eps0p1_e/report.md),
  [`k20, 0.1`](../runs/20261125-162821_enclosure_k20_eps0p1_e/report.md); first round:
  [`enclosure_k5_eps0p9`](../runs/20261124-144014_enclosure_k5_eps0p9/report.md),
  [`enclosure_k20_eps0p9`](../runs/20261124-144021_enclosure_k20_eps0p9/report.md),
  [`enclosure_k5_eps0p1`](../runs/20261124-144011_enclosure_k5_eps0p1/report.md),
  [`enclosure_k20_eps0p1`](../runs/20261124-144017_enclosure_k20_eps0p1/report.md); mesh check
  [`enclosure_k20_eps0p9_mesh1mm`](../runs/20261124-161733_enclosure_k20_eps0p9_mesh1mm/report.md)
- Redesign, settled (9,000 s): `runs/20261125-1125*_enclosure_fix_k5_*_long` (ten runs; results and both rounds'
  verdicts in each case header); the first 3,600 s set: `runs/20261124-1714*` and `runs/20261124-1715*`
- All 14 final runs scored against revision B:
  [`client_requirements_revB_scores.json`](../validation/enclosure/client_requirements_revB_scores.json)
  (`scripts/score_client_requirements.py`)
- Cases with predictions and results: `cases/cavity_*.toml`, `cases/annulus_*.toml`, `cases/enclosure_*.toml`; model
  `models/cfd/enclosure_openfoam.py`, study `studies/enclosure_thermal.py`

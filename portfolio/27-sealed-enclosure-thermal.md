# Sealed electronics enclosure: natural convection and radiation, and the fix for the hot component

[Portfolio index](../PORTFOLIO.md) · Thermal and fluids

| | |
|---|---|
| **Answer** | The sealed aluminium box as drawn (150 x 60 mm section, 200 mm deep; a board carrying 10 W with a 5 W component; 40 C ambient) **fails both requirements at every corner** of the uncertain inputs: the component reaches **94-98 C** with a high-emissivity interior and **156-163 C** with a bare-metal one (limit 85), the mean air **67-84 C** (limit 60). **A conduction path from the component to the lid fixes the component**: with an aluminium shell modelled and a pad or pillar of effective conductivity **5 W/mK**, the component sits at **70 C** (emissivity 0.9) and **76 C** (0.1), so it passes at both interior finishes; 2 W/mK passes only with a high-emissivity interior (78 against 91 C). **The air limit still fails with every bridge** (61-72 C): the board's own 10 W heats the air, and passing REQ-D2 needs a path for that heat too. Verification: every model part is checked against an exact or benchmark answer first (natural convection within 0.6 % of de Vahl Davis; radiation within 0.9 % of the exact exchange at the angular resolution the box uses); a 1 mm mesh moves the corner result by 0.05 K. The redesign runs stopped before the box fully settled; extrapolated to the settled state, their heat balance closes to 0.03-0.30 % and no verdict changes (details below). With a bridge the **board** becomes the hottest part (79.7 / 98.4 C at 5 W/mK): REQ-D1 names the component, so whether it should cover the rest of the board is open with the client. The client, loads and limits are synthetic. |
| **Discipline** | Electronics cooling: conjugate heat transfer with natural convection and radiation |
| **Tools** | OpenFOAM 14 (foamMultiRun, fvDOM radiation), Python |
| **Methods** | 2D conjugate heat transfer (air, board, component, aluminium shell, bridge), laminar natural convection with a perfect gas, grey diffuse radiation by the discrete ordinates method, transient to a settled state; staged verification against benchmarks; corner study over the uncertain inputs; heat-balance and settling checks with extrapolation to the settled state |

## The question

A sealed aluminium enclosure (2D section 150 x 60 mm, 200 mm deep) holds a 100 x 2 mm circuit board at mid-height that
dissipates 10 W, with a 20 mm component on it dissipating 5 W. Outside: still air at 40 C (convection 5 W/m2K, paint
emissivity 0.85). Does the hottest component stay at or below 85 C (REQ-D1), and the mean internal air at or below 60 C
(REQ-D2), whatever the interior finish (emissivity 0.1 bare to 0.9 painted, REQ-D3)? The board's in-plane conductivity
is uncertain (copper planes): bracket it at 5 and 20 W/mK. If it fails, what fixes it?

## The answer

As drawn, at the four corners:

| Board | Interior emissivity | Hottest component | Mean air | Radiation share |
|---|---|---|---|---|
| 5 W/mK | 0.9 | **98.4 C** | **66.9 C** | 75 % |
| 20 W/mK | 0.9 | **94.2 C** | **67.0 C** | 76 % |
| 5 W/mK | 0.1 | **163.2 C** (unverified, settling) | **83.9 C** | 22 % |
| 20 W/mK | 0.1 | **156.3 C** (unverified, settling) | **84.1 C** | 22 % |

Both limits fail everywhere, and by far at low emissivity: a bare interior sheds the board's heat almost only by
convection. The emissivity-0.1 corners had not finished settling (0.6 K over the last tenth of the run against 0.3);
extrapolated, the component settles near 164 C, so no verdict depends on it.

The redesign, on the worse board (5 W/mK): the walls become a 2 mm aluminium shell (it conducts along the walls, which a
boundary condition cannot), and a bridge (a thermal pad or a pillar with a gap pad) joins the component's top to the lid
across the 29 mm gap:

| Bridge conductivity | Component, emissivity 0.9 | Component, emissivity 0.1 | Board maximum, 0.9 / 0.1 | Mean air, 0.9 / 0.1 |
|---|---|---|---|---|
| none (shell only) | 95.7 C | 154.6 C | 93.7 / 152.7 C | 65.9 / 80.8 C |
| 1 W/mK | 84.8 C (passes by 0.2 K) | 106.6 C | 85.2 / 116.3 C | 64.5 / 71.9 C |
| 2 W/mK | 78.0 C | 91.1 C | 82.5 / 107.3 C | 63.5 / 69.1 C |
| **5 W/mK** | **70.0 C** | **76.1 C** | 79.7 / 98.4 C | 62.3 / 66.2 C |
| 20 W/mK | 63.3 C | 65.8 C | 77.5 / 92.2 C | 61.1 / 64.0 C |

Once the bridge cools the component, the board away from it is the hottest part of the assembly: at 5 W/mK it reaches 79.7 C with a painted interior and 98.4 C with a bare one. REQ-D1 as written names the component, so the verdicts above stand, but if other parts on the board carry the same 85 C limit, the bare-interior design fails on them. That is the client's call, and it is the first question to put to them.

**Recommendation:** a bridge of at least 5 W/mK effective conductivity (component width, full gap: 1.45 K/W through the
box's depth) meets REQ-D1 for both interior finishes with 9 K of margin, provided the limit applies to the
component only (see the board temperatures above). A high-emissivity interior alone is not
enough (shell only: 95.7 C). REQ-D2 needs a second path: the board's 10 W must reach the walls by conduction too (board
edges clamped to the walls, or a full-area gap pad), or the limit must be relaxed; neither is assessed here.

## How it works

- **One model, conjugate heat transfer.** OpenFOAM's multi-region solver couples the air (laminar natural convection,
  perfect gas, buoyancy), the solid board and component (volumetric heat sources), and in the redesign the aluminium
  shell and the bridge. The board is solid so it spreads heat: a first prototype with fixed surface fluxes put the
  component at 154 C.
- **Radiation** between the inside surfaces by the discrete ordinates method (grey, diffuse; the air transparent).
- **Transient to a settled state**: a steady coupled solve looked converged for thousands of iterations and then
  diverged, so every run marches in time until the temperatures stop moving, and the heat balance confirms it.
- **Outside**: convection and radiation to ambient on the shell's outer faces.

## How I know it's right

- **Stage 1, natural convection**: the square cavity of de Vahl Davis (Rayleigh 1e3-1e6): Nusselt number and peak
  velocities within 0.05-0.62 % of the benchmark table; a three-mesh study at Rayleigh 1e6 converges the Nusselt number
  to 0.07 % of the benchmark (one peak velocity's convergence order came out anomalous: reported, not hidden).
- **Stage 2, radiation**: grey exchange between concentric cylinders against the exact two-surface formula: 0.92 %
  at the 4 directions per quarter the box runs use (limit 1 %), 0.21 and 0.05 % at 8 and 16; 0.11-0.21 % over
  emissivities 0.1-0.9 at 8 directions.
- **Heat balance**: heat leaving the box against the 15 W put in: 0.46-0.74 % at the four corners (limit 1 %).
- **Mesh**: the 20 W/mK, emissivity-0.9 corner on 1 mm cells (2 mm in the study) moves the component by 0.05 K and the
  air by 0.13 K, against margins of 9 and 7 K.
- **Settling**: the component's change over the last tenth of the run, and the heat balance (below).

## What the checks caught

- **Energy created by a boundary-condition name.** With two pattern-matched names for the solids' interfaces, the
  general one also matched the air interface, so the board never lost its radiated heat: the walls shed 671 W/m2
  against 178.6 put in. The heat balance caught it; explicit interface names fixed it.
- **A wall boundary condition cannot spread heat.** Modelling the walls as a boundary condition loses each face's heat
  where it arrives: fine for the original design, wrong for a bridge that dumps 5 W into a 20 mm strip of lid (it would
  sit about 110 K above ambient). The redesign models the walls as a solid shell.
- **A 1.9 % accounting error that looked like an unsettled run.** Six redesign runs failed the 1 % heat balance by
  1.2-2.9 %. The cause was my post-processing: it multiplied the wall fluxes by one 2 mm face area, but the mesher
  rounds each block to whole cells, so blocks of 25 and 29 mm have 2.08 and 2.07 mm faces, and the box's perimeter came
  out 1.9 % short. With exact face areas (now read from the mesh, with a test) the totals showed what was really
  happening: the shell and bridge give the box a slow mode (time constant about 20 minutes, five times the original
  box's), so at the 1-hour mark 8 of the 10 runs were outside 1 % (the bridged ones still cooling, heat out up to 4 %
  above the input). Extrapolating each run to its settled state closes the heat balance to 0.03-0.30 % and moves the
  component by at most 0.64 K and the air by at most 0.58 K, changing no
  verdict. The settling check on the component alone had passed every run: it is too weak for a slow mode, and the
  heat balance is now the settling test.
- **My predictions were wrong in instructive ways**: the 1 W/mK bridge ran 15 K cooler than my hand estimate, and at
  low emissivity the bridges ran 2.5-22 K hotter than at high emissivity, not "a few K"; the shell alone helped 8.6 K at
  low emissivity against 2.8 K at high. Each miss is written into its case file next to the prediction.

## Limits

- 2D section: the box's end walls are left out (less wall area, conservative); a 3D model would credit them.
- Laminar flow (Rayleigh number about 1e5-1e6 on the box height), grey diffuse surfaces, transparent air.
- Radiation at 4 directions per quarter: 0.92 % from exact in the stage-2 test, and radiation carries about 75 % of
  the walls' inside heat with a painted interior.
- The redesign was run on the 5 W/mK board only (the worse one); the mesh check covers one as-drawn corner at two
  levels.
- The bridge is one effective conductivity standing for a pillar and its gap pad, with perfect contact; a real pad's
  contact resistance must be added to the 1.45 K/W budget.
- Synthetic loads, limits and outside conditions; no test data.
- The redesign verdicts rest on runs stopped about one time constant early plus extrapolation; a set of longer runs
  (about 2.5 hours of simulated time) would verify them directly.

## Evidence

- Stage 1: [`cavity_devahldavis`](../runs/20261124-105442_cavity_devahldavis/report.md),
  [`cavity_mesh_ra1e6`](../runs/20261124-105444_cavity_mesh_ra1e6/report.md); stage 2:
  [`annulus_angular`](../runs/20261124-110740_annulus_angular/report.md),
  [`annulus_emissivity`](../runs/20261124-110742_annulus_emissivity/report.md)
- Corners: [`enclosure_k5_eps0p9`](../runs/20261124-144014_enclosure_k5_eps0p9/report.md),
  [`enclosure_k20_eps0p9`](../runs/20261124-144021_enclosure_k20_eps0p9/report.md),
  [`enclosure_k5_eps0p1`](../runs/20261124-144011_enclosure_k5_eps0p1/report.md),
  [`enclosure_k20_eps0p1`](../runs/20261124-144017_enclosure_k20_eps0p1/report.md); mesh check
  [`enclosure_k20_eps0p9_mesh1mm`](../runs/20261124-161733_enclosure_k20_eps0p9_mesh1mm/report.md)
- Redesign: `runs/20261124-1714*_enclosure_fix_k5_eps0p1_*` and `runs/20261124-1715*_enclosure_fix_k5_eps0p9_*` (ten
  runs; corrected heat balance and settled extrapolation in each case header)
- Cases with predictions and results: `cases/cavity_*.toml`, `cases/annulus_*.toml`, `cases/enclosure_*.toml`; model
  `models/cfd/enclosure_openfoam.py`, study `studies/enclosure_thermal.py`

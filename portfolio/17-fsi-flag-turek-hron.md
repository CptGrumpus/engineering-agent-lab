# Flexible flag behind a cylinder: fluid-structure interaction, built one verified stage at a time

[Portfolio index](../PORTFOLIO.md) · Fluids and structures (coupled)

> **Draft, in progress (updated 2026-11-23).** The solid and fluid stages are verified. The coupled stage
> (preCICE): the steady case (FSI1) reproduces the benchmark within 1 %; the two periodic cases (FSI2, FSI3)
> reproduce it within 2 % and 9 % on one mesh, but their verification failed on a check that turned out to be
> unable to measure what it claimed (below), so they are not verified yet. Next: measure FSI1's mesh-to-mesh scatter
> (running), then a periodic rerun with a force-transfer check that works for a swinging flag.

| | |
|---|---|
| **Answer so far** | Both single-physics halves reproduce the published Turek-Hron benchmark before any coupling. Solid, static (CSM1, CSM2): the tip displacement extrapolates to within 0.015 % of the published values. Fluid (CFD1): drag within 0.07 %, lift within 0.6 % on every mesh. Solid, dynamic (CSM3): frequency 1.0946 Hz, 0.09 % from the published band (verified). Fluid at Re 100 (CFD2): drag within 0.014 % when extrapolated, lift within 0.7 % on the finer meshes. Coupled, steady (FSI1): drag and lift verified (0.03 % and 0.18 % from the published values on the finest mesh, mesh uncertainty 0.03 % and 0.3 %); the tip displacement is within 1 % on every mesh, but scatters by about ±0.5 % between meshes, so its mesh uncertainty can't be estimated. Coupled, periodic (FSI2, FSI3): the oscillation starts on its own and every published quantity is reproduced. FSI3 mesh study, three levels: on the finest mesh every requirement passes (tip amplitude -1.1 %); frequency and drag mean verified (mesh uncertainty 0.13 % and 0.9 %), and the tip amplitude extrapolates to 0.02 % from the benchmark (uncertainty 1.45 %). FSI2: within 2.1 % on two mesh levels that agree to 0.7 %; the finest level crashes at 8.8 s (diagnosis open). |
| **Discipline** | Structures (large deflection, dynamics), fluids, fluid-structure interaction |
| **Tools** | CalculiX (solid), OpenFOAM 14 with Gmsh (fluid), Python; preCICE 3.4.1 with OpenFOAM v2512 for the coupled stage |
| **Methods** | Geometrically nonlinear static and dynamic FE, a large-deflection elastica as an independent reference, steady laminar CFD, mesh and time-step refinement with GCI, published benchmark values as the acceptance requirement |

![The flag bending under its own weight: CalculiX against the elastica and the benchmark point](../runs/20261121-131111_flag_csm1_mesh/points/p02_element_size_mm-1.25/response.png)

## The question

A flexible flag sits in the wake of a cylinder in a channel. The flow bends it and the flag's motion
changes the flow. Turek and Hron (2006) published the standard benchmark for this, with reference values
for each half on its own (the CSM and CFD tests) and for the coupled problem (FSI1 to FSI3).

A coupled simulation that doesn't match is hard to debug: the error could be in the fluid, the solid or
the coupling. So the plan is the one the cold-plate chain used. Each participant has to reproduce its own
published results first, and only then are they coupled.

## The answers so far

- **Solid, static (CSM1, CSM2).** The flag hangs under gravity. Point A at its tip drops 66.08 mm in CSM1
  on the finest mesh, extrapolating to 66.108 mm against the published 66.102. The stiffer CSM2 flag
  matches to the same 0.01 %.
- **Fluid (CFD1, Re 20).** Drag 14.300 N/m on 208,000 cells, extrapolating to 14.303 against the
  published 14.293, with a 0.02 % mesh uncertainty. Lift lands within 0.6 % of the published 1.119 on
  every mesh, but it scatters between meshes (see below).
- **Solid, dynamic (CSM3).** Released from rest, the flag swings at **1.0946 Hz** (time-step uncertainty 0.013 %),
  0.09 % under the published band of 1.0956 to 1.0995. The horizontal mean is inside the band. The vertical mean and
  amplitude sit inside the band or within 0.08 % of it, but are formally unverified: they move by only 0.03 to
  0.09 % between time steps, without a clean convergence pattern.
- **Fluid at Re 100 (CFD2).** Drag converges to 136.719 N/m against the published 136.700 (0.014 %, mesh
  uncertainty 0.11 %). Lift is 10.61 on the finest mesh, 0.7 % from the published 10.53, with the same
  mesh-to-mesh scatter as CFD1.
- **Coupled, steady (FSI1).** Three fluid meshes (5 / 2.5 / 1.25 mm), all 4800 coupling windows converged on each.
  Drag converges at order 2.75 to 14.299 N/m against the published 14.294 (0.03 %). The tip's vertical
  displacement is 0.4 % and then 1.0 % below the published value as the mesh refines, moving away from it, which is
  not explained yet; lift jitters by about 2 % from one time step to the next (coupling noise on a force 5 % the
  size of drag). Not verified. Two cheap probes before the revision: lift's jitter is zero-mean coupling noise (a tighter
  coupling tolerance cut it 72 times and left every mean unchanged to five digits), and a finer solid moves the tip
  only 0.035 %, so the solid is not the cause of the drift. The revision averages over the last 2 s,
  judges steadiness by drift, tightens the coupling, and uses fluid meshes of 2.5 / 1.77 / 1.25 mm: the 5 mm mesh
  was too coarse to belong in the sequence (+5.8 %). Revision result (5 h): every check passes on every mesh; drag
  14.298 N/m and lift 0.762 N/m verified; the tip displacement reads 0.8175 / 0.8212 / 0.8130 mm against the
  published 0.8209, within 1 % each time but up and then down. The "drift away" was scatter: the new middle mesh sits
  on the benchmark. Three regenerated meshes cannot separate a ±0.5 % scatter from a trend, so that verdict stays
  unverified (it passes its 3 % limit on every mesh). **Second revision (2026-11-23):** four meshes of one nominal
  size measured that scatter (tip vertical 1.94 %, drag 0.075 %, lift 1.12 % peak to peak, horizontal 0.20 %),
  and a new check caught a fifth mesh that wrapped one cell around the flag's corner and read 28 % low with every
  other check passing. Declaring the measured scatter, the rerun (identical to five digits) verifies the tip's
  vertical displacement (0.96 % from the benchmark, uncertainty 0.63 %), drag and lift. Only the horizontal tip
  displacement, a second-order quantity 3 % of the vertical, stays unverified: within 0.7 % of the benchmark on every
  mesh, but its changes grow as the mesh refines, as predicted before the run.
- **Coupled, periodic (FSI2, FSI3), one fluid mesh (2.5 mm).** Nothing is done to start the oscillation: the
  flow and the flag start symmetric and at rest, and the swing grows on its own from about 5 s (FSI2) and 3 s (FSI3),
  settling to a repeatable cycle (the last two periods agree to 1e-4 or better). Every coupling window converged
  (15000 and 16000 windows, 6.5-7 iterations each).

  | | FSI2 (Re 100, flag 10x denser than the fluid) | FSI3 (Re 200, equal density) |
  |---|---|---|
  | tip vertical amplitude | 82.1 mm against 81.6 (+0.7 %) | 33.9 mm against 35.0 (-3.1 %) |
  | frequency | 1.931 Hz against 1.93 | 5.464 Hz against 5.46 |
  | drag mean / amplitude | 217.4 / 78.0 N/m against 215.1 / 77.7 | 469.8 / 25.3 against 460.5 / 27.7 |
  | lift amplitude | 242.7 N/m against 237.8 (+2.1 %) | 153.4 against 153.9 (-0.3 %) |
  | tip horizontal mean | -15.0 mm against -14.85 (1.1 %) | -2.70 mm against -2.88 (6.2 %) |
  | wall time (one core each, side by side) | 7 h 42 min | 8 h 24 min |

  Every requirement passes (limits from the benchmark's own spread, set before the runs), and every prediction of
  the values landed in its range. The verdicts are marked unverified anyway: see the force-transfer check below.
  FSI3's misses are inside the spread between the benchmark's own mesh levels; whether they are ours needs a mesh and
  time-step study.
- **Mesh studies (FSI2, FSI3), 2026-11-23/24.** Three fluid meshes each (3.54 / 2.5 / 1.77 mm) run side by side,
  with the window-by-window force-transfer check that replaced the defective one; predictions were committed in the
  case files before the runs. Every level that finished passes every check (force transfer about 3e-9), and each
  2.5 mm level repeats its earlier single run to 4 digits or better.

  **FSI3, all three levels:** the finest mesh passes every requirement (tip amplitude -1.1 %, drag mean +1.2 %,
  lift amplitude +0.2 %), and the coarsest misses only the tip amplitude (-8.4 % against a 5 % limit, the miss
  predicted as likeliest). So the earlier -3.1 % was the mesh. Across the three levels:

  | | result | extrapolated to zero cell size | benchmark |
  |---|---|---|---|
  | frequency | 5.453 / 5.464 / 5.455 Hz, uncertainty 0.13 % | | 5.46 |
  | drag mean | converges (order 2.2), uncertainty 0.90 % | 462.7 N/m | 460.5 (+0.5 %) |
  | tip vertical amplitude | converges (order 2.9), uncertainty 1.45 % | 34.997 mm | 34.99 (+0.02 %) |
  | drag and lift amplitude | change too fast between levels for a clean order (3.6 and 5.3 against 2) | none | |
  | tip horizontal mean | converges slowly (order 0.9), uncertainty 20 % | | |

  Frequency and drag mean are verified under 1 %. The tip amplitude converges onto the benchmark, but its mesh
  uncertainty (1.45 %) is just over the 1 % target at these sizes. The force amplitudes are reported, not tuned.

  **FSI2:** the 3.54 and 2.5 mm levels agree within 0.1-0.7 % on every benchmark quantity. The 1.77 mm level
  crashed twice at the same step (8.836 s of 15). The log ends kept since the first crash show the cause: the
  largest Courant number, about 2.2 all run, jumped to 5.8 and then 17.9 in two steps before the pressure solver
  failed. That fits either a mesh cell collapsing as the flag swings through, or the one-pass pressure-velocity
  solver going unstable; the log alone can't tell which. FSI3's finest mesh ran its full 8 s at a Courant number of
  2.36 with the same settings, with half the swing. So for now FSI2 has two mesh levels and no three-level
  uncertainty.

## How it works

- **Solid.** A structured hex mesh of the flag, clamped on the cylinder arc. It's one element thick and
  held in z, which makes it plane strain. CalculiX solves it geometrically nonlinear (the flag's tip drops
  by a fifth of its length) with the benchmark's St. Venant-Kirchhoff material.
- **Fluid.** Gmsh meshes the channel round the cylinder and flag. `gmshToFoam` converts it, and OpenFOAM
  solves steady laminar flow with the benchmark's parabolic inflow. Forces are integrated on the body.
- **Coupled.** preCICE couples OpenFOAM v2512 and CalculiX (its official adapters); the version
  of OpenFOAM the rest of this portfolio uses isn't supported by the adapter.

## How I know it's right

- **An independent reference for the solid.** A large-deflection elastica (a nonlinear beam solved
  separately in Python) agrees with the FE to 0.7 % for the tip drop and 1 % for the sideways pull-in.
  That remaining gap is what a beam theory leaves out: the flag's root sits on the cylinder arc and flexes
  a little.
- **Exact equilibrium.** The clamp reaction equals the flag's weight once the share CalculiX applies
  directly to the clamped nodes is added back (that share is computed exactly from the mesh).
- **The time integrator on its own.** A companion run at a thousandth of the gravity swings at the
  linear natural frequency to 0.1 %.
- **The inflow, face by face.** The inlet velocity matches the benchmark's parabola at every face to
  6 × 10⁻⁸, and mass is conserved to 10⁻¹³.
- **Mesh and time-step refinement**, with a GCI on every requirement, and the benchmark values as the
  pass criterion.

## What the checks caught

- **The benchmark doesn't say plane strain or plane stress.** The elastica settled it before any FE run:
  plane strain matches to 0.7 %, plane stress misses by 17 %.
- **A standard inflow condition that isn't the profile it claims.** OpenFOAM's parabolic inlet was 1.6 %
  low at mid-channel and 1.5 % high near the walls. It scales the profile by the largest face distance on
  the inlet, not the true half-height. My first explanation (the cylinder counted as a wall) was tested
  and was wrong. The inlet now sets the benchmark's exact parabola, checked face by face.
- **A diagnosis that was wrong, and the rerun that showed it.** The finest time step diverged late in the run. I first blamed the Newton tolerance, but loosening it changed nothing: same increment, same iteration history. The real cause was energy building up in the flag's stiff high-frequency modes under the undamped scheme. A little standard numerical damping (HHT, alpha -0.05) fixed it, and left the 1.1 Hz swing's frequency unchanged to 1e-4.
- **The time-stepping scheme adds energy to a large swing.** The trapezoidal rule only conserves energy
  for linear problems. At a 0.01 s step the flag climbed 1.9 mm higher each swing and its frequency rose
  by 1.3 %. The drift falls about four times per halving of the step, and the checks reject the coarse
  steps. The published rows themselves differ by up to 1.8 % between their time steps.
- **My own frequency measurement was being fooled.** The sudden release also excites the flag's second
  mode, which never decays without damping and shifts the troughs. A synthetic two-mode test showed the
  trough finder reading 1.71 Hz for 1.07. Cycles are now counted from mid-level crossings, and the
  frequency became steady across time steps at 1.095 Hz.
- **Lift scatters with the mesh.** Gmsh regenerates the mesh at each size rather than refining it, and
  lift is a small difference of large pressure forces, so it scatters by about ±0.6 % from mesh to mesh.
  One CFD1 mesh study verified it and the next withheld it; CFD2 shows the same. The fix (nested meshes, or measuring that scatter
  first) is the next revision; the tolerance stays.
- **A jittering force that wasn't unsteady flow.** In the coupled steady case lift changed sign about 600 times in
  800 steps, ±2 % peak to peak, with no drift. At Re 20 the flow can't shed vortices, so a steadiness check that
  measured peak to peak was measuring coupling noise. Judging steadiness by drift (the mean of each half of the last
  2 s) and reporting window means fixed the check without loosening it; a tighter coupling tolerance shrank the noise
  itself.
- **A suspect ruled out cheaply.** The tip displacement moved away from the benchmark as the fluid mesh refined. The
  obvious suspect, the solid mesh held at 2.5 mm, was tested on one point first: halving it moved the tip 0.035 % and
  took four times as long. The six-hour revision went to the fluid side instead.
- **A check that could not measure what it claimed.** The force-transfer check (fluid force on the flag + the
  clamp reaction in the solid = 0) failed both periodic runs, at 1.5 and 0.9 against 0.01. The prediction had said
  why it needs care: a swinging flag's own inertia is in that balance at any instant, and cancels only over whole
  periods. The code was asked for whole-period means, but under the coupling adapter CalculiX writes the reaction
  only at the very last step (the file stayed empty for 8 hours, then held one entry), so there was nothing to
  average, and the code quietly fell back to the end-of-run values. FSI1 passed the same check only because a
  steady flag has no inertia. The failures stand on record; the check now reports "not evaluable" instead of
  falling back, and the rerun will compare the force the solid receives each window with the fluid's force at the
  same instant, which involves no inertia at all.
- **Smaller finds.** CalculiX uses one print frequency for every request in a step, so one request
  silently thinned another's output. The `.dat` file's seven digits limit how well equilibrium can close.

## Limits

- 2D, as the benchmark defines it.
- FSI3: one time step; the force amplitudes and the horizontal tip mean have no mesh uncertainty (see the mesh
  study). FSI2: two mesh levels only (the finest crashed), one time step.
- Laminar, as the benchmark defines it; the transient fluid solver is first order in its mesh motion.
- The published reference values are themselves numerical, and their rows are not all labelled with the
  time step they used.

## Evidence

- solid, static: [CSM1 mesh study](../runs/20261121-131111_flag_csm1_mesh/report.md),
  [CSM2 mesh study](../runs/20261121-131133_flag_csm2_mesh/report.md) (both verification PASS)
- solid, dynamic: [CSM3, final](../runs/20261121-184353_flag_csm3_dt_r3/report.md) (frequency and ux verified), with the [first run](../runs/20261121-132448_flag_csm3_dt/report.md) (energy drift), [r1](../runs/20261121-142836_flag_csm3_dt_r1/report.md) and [r2](../runs/20261121-164522_flag_csm3_dt_r2/report.md) (the divergence and the wrong diagnosis) kept as evidence
- coupled, steady: [FSI1 first mesh study](../runs/20261121-203031_turek_hron_fsi1_mesh/report.md) (drag converged; lift noise and the tip drift withheld it); [revision 1](../runs/20261122-125809_turek_hron_fsi1_mesh_r1/report.md) (drag and lift verified; tip within 1 %, its mesh uncertainty not estimable), with its predictions and Results in `cases/turek_hron_fsi1_mesh_r1.toml`
- coupled, periodic: [FSI2](../runs/20261122-184933_turek_hron_fsi2/report.md), [FSI3](../runs/20261122-185044_turek_hron_fsi3/report.md) (verification FAIL on the defective check; predictions and Results in `cases/turek_hron_fsi2.toml`, `cases/turek_hron_fsi3.toml`)
- coupled, periodic, mesh studies: FSI3 [3.54 mm](../runs/20261123-161047_turek_hron_fsi3_mesh_a/report.md),
  [2.5 mm](../runs/20261123-161107_turek_hron_fsi3_mesh_b/report.md),
  [1.77 mm](../runs/20261123-161128_turek_hron_fsi3_mesh_c/report.md), combined check
  `validation/turek_hron/fsi3_mesh_study.json`; FSI2 [3.54 mm](../runs/20261123-123332_turek_hron_fsi2_mesh_a/report.md),
  [2.5 mm](../runs/20261123-123352_turek_hron_fsi2_mesh_b/report.md),
  [1.77 mm, crashed](../runs/20261123-180658_turek_hron_fsi2_mesh_c/report.md); predictions and Results in
  `cases/turek_hron_fsi{2,3}_mesh_{a,b,c}.toml`
- fluid: [CFD1 first mesh study](../runs/20261121-140245_turek_hron_cfd1_mesh/report.md) (lift verified), [CFD1 refined](../runs/20261121-140657_turek_hron_cfd1_mesh_r1/report.md) (drag verified), [CFD2](../runs/20261121-151947_turek_hron_cfd2_mesh/report.md) (drag verified, lift withheld on mesh noise)
- case files: `cases/flag_csm1_mesh.toml`, `cases/flag_csm2_mesh.toml`, `cases/flag_csm3_dt.toml`,
  `cases/flag_csm3_dt_r1.toml`, `cases/turek_hron_cfd1_mesh.toml`, `cases/turek_hron_cfd1_mesh_r1.toml`,
  `cases/turek_hron_cfd2_mesh.toml` (predictions, smoke-test findings and results in the headers)
- code: `models/fea/flag_ccx.py`, `studies/flag_csm.py`, `validation/elastica.py`,
  `models/cfd/turek_hron_openfoam.py`, `models/cfd/run_turek_hron.sh`, `studies/turek_hron_cfd.py`

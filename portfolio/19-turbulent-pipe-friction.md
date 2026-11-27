# Turbulent pipe friction: RANS against measured data, and what one mesh hides

[Portfolio index](../PORTFOLIO.md) · Thermal and fluids

> **Study 19 has two parts.** Part 1 (below): attached flow, pipe friction against a correlation of measurements.
> [Part 2](#part-2-separated-flow-behind-a-step-against-measurements): separated flow behind a backward-facing step,
> scored once against Driver and Seegmiller's measurements: reattachment and skin friction pass, pressure recovery
> fails by 0.0027 against a 0.02 limit.

| | |
|---|---|
| **Answer** | Yes, with the viscous sublayer resolved. k-omega SST predicts the smooth-pipe friction factor at Re 10⁵ about 2.4 % above Prandtl's law, extrapolated to zero cell size from three meshes (mesh uncertainty 0.5 %, verified), inside the 5 % a pressure-drop budget needs. Within 2 % across Re 2 × 10⁴ to 2 × 10⁶. With wall functions instead it sits about 5 % low whatever the mesh and wherever the wall cell sits: not usable to 5 %. |
| **Discipline** | Fluids, turbulence modelling, validation against measured data |
| **Tools** | OpenFOAM 14 (k-omega SST), Python |
| **Methods** | Fully developed RANS on a periodic axisymmetric wedge; low-Reynolds and wall-function wall treatments; an exact force balance; mesh studies with GCI; comparison with Prandtl's smooth-pipe law (Nikuradse's measurements), Blasius and Petukhov |

![Friction factor against Prandtl's law: the mesh study, the Reynolds sweep and the wall-function placement](img/pipe_friction.png)

## The question

Can this OpenFOAM RANS setup be trusted for turbulent pressure-drop budgets, such as a coolant line or a heat-exchanger
passage? The requirement (REQ-T1): the friction factor within 5 % of Prandtl's smooth-pipe law,
1/√f = 2.0 log₁₀(Re √f) − 0.8. That law is a fit to Nikuradse's measurements and the smooth curve of the Moody
chart, so this is the portfolio's first comparison with measured data, through a correlation (about ±2 % scatter).

## The answer

- **Resolved sublayer (y+ below 1):** f = 0.01813 / 0.01828 / 0.01835 on 160 / 320 / 640 radial cells, extrapolating
  to 0.01842, **+2.4 %** on Prandtl, with a mesh uncertainty of 0.48 %. REQ-T1 passes, verified, with a clear margin.
  The meshes never stop changing; what converges is the estimate. Each halving of the cells halves the change
  (+0.83 %, then +0.38 %), so the error falls in proportion to the cell size and what is left after 640 cells is about
  one more such step, +0.38 %: the extrapolated value. That holds only while the changes keep shrinking at a steady
  rate, which is why the study needed three meshes and checks the rate (observed order 0.84, then 0.98) before
  extrapolating.
  (The coarser study, 80 / 160 / 320 cells, gave the same extrapolation with an uncertainty of 1.05 %, just over the
  1 % limit; one finer level settled it.)
- **Across Reynolds numbers** (Re 2 × 10⁴ to 2 × 10⁶, on 60-120 cells): within 1.4 % of Prandtl at every point. Those
  meshes carry the same kind of mesh error as the 80-cell point above, so read them as about 2-3 % high when converged.
- **Wall functions** (first cell in the log layer): 5.0-5.4 % below Prandtl at every Reynolds number. Refining the
  core four times moves f by 0.1 %, and moving the first cell from y+ 29 to 196 moves it from −5.2 to −4.75 %. The
  offset belongs to the wall treatment, so no mesh choice makes it pass with a margin.

## How it works

The pipe is a 5° wedge, one cell thick, with the two ends joined (cyclic), so the flow is the fully developed state
with no inlet to model. A fixed bulk velocity is held by a momentum source, which reports the pressure gradient it
needs. Radial cells grade towards the wall so the first cell sits at the requested y+. D = 0.1 m, ν = 10⁻⁶ m²/s.

## How I know it's right

- **An exact force balance:** in steady periodic flow the wall shear and the applied pressure gradient must balance
  exactly, two independent routes to f. They agree to 10⁻⁹ or better on every converged mesh; before convergence they differ,
  so this check also catches an unconverged run.
- **The bulk velocity** is held to 10⁻¹³, the wall shear is uniform along the wall, and the pressure gradient's
  change over the last 10 % of iterations is under 10⁻⁸.
- **The model's validity:** first-cell y+ inside each treatment's range; the mean velocity follows the log law
  within 2.5-3.4 % (its constants scatter by a few per cent between experiments).
- **Mesh studies** with every level halving every cell, and the extrapolated value reported, not a single mesh.

## What the checks caught

- **A good agreement that was mesh error.** The first smoke test gave f 0.9 % below Prandtl on 80 cells: reassuring
  and wrong. The mesh study moved it to +0.7 % at 160 cells and +1.6 % at 320; the friction factor converges at
  about first order (0.84, then 0.98), not the scheme's second, and the converged value is about 2.4 % *above*
  Prandtl. Quoting one mesh would have got the sign wrong.
- **A fix that broke convergence.** At Re 2 × 10⁶ checkMesh flagged the wedge's aspect ratio (2884): its fixed 2 mm
  axial length against sub-micron wall cells. Tying the length to the cells fixed that and left the converged f
  unchanged, but it slowed the solver by orders of magnitude on the finest meshes: a 160-cell mesh that converged in
  15,000 iterations no longer converged in 80,000, and the 320-cell point never did. Its unconverged value even looked
  plausible (flat against 160 cells). The force balance exposed it (7 × 10⁻³ instead of 10⁻⁹ or better). The revision went back
  to the fixed length, which checkMesh accepts at this Reynolds number, and every point converged in minutes. The
  finest level (640 cells) needed the length halved, not cut twenty-fold: a probe showed it still converges, slowly
  (300,000 iterations), and the two coarser levels repeated their earlier values exactly at the shorter length.
- **A suspect mesh that wasn't the problem.** The wall-function offset first looked like a coarse outer mesh (25-40
  cells). A probe at four times the cells moved f by 0.1 %; a placement sweep confirmed the wall treatment itself.

## Part 2: separated flow behind a step, against measurements

**The question.** Part 1 showed the setup (k-omega SST, wall layer resolved) gets attached-flow friction right. Is
it good enough for separated flow, for example placing a heat-transfer surface or a sensor in a duct with a step?
The test is Driver and Seegmiller's backward-facing step (ERCOFTAC case 030: step 12.7 mm, Re 37,500 on the step
height, air at 44.2 m/s). Three limits, agreed before any comparison data was opened: where the flow reattaches
within 10 %; the skin friction from 10 to 30 step heights within 15 % rms; the pressure recovery to 30 step heights
within 0.02.

**The answer: two of three.**

| | Ours | Measured | Limit | Verdict |
|---|---|---|---|---|
| Reattachment length (step heights) | 6.40 | 6.26 ± 0.10 | 10 % | **Pass**, +2.3 % |
| Skin friction, 10-30 step heights | 1-10 % low at every station | | 15 % rms | **Pass**, 7.0 % rms |
| Pressure recovery to 30 step heights | 0.153 | 0.131 | 0.02 | **Fail**, +0.023 |

![Skin friction and pressure along the step-side wall against the measurements](../validation/step_driver_seegmiller/comparison.png)

The pressure peak behind reattachment is close (about 0.177 against 0.163, read from the plot); downstream, the measured pressure falls back
faster than ours. That is what the tunnel's side-wall boundary layers do (the span is 12 step heights): they thicken,
squeeze the core flow and lower the pressure. A 2D model has no side walls. It was stated as a limit in the framing;
the comparison puts it at about 0.023 in recovery, just over what the limit allows.

**Is that explanation big enough? A hand estimate says yes** (added 2026-11-27, under the portfolio's standing rule:
an explanation of a miss is a claim to test, not a conclusion). Each side wall's boundary layer was grown along the
tunnel by the momentum integral, driven by our own 2D wall pressure, from the inflow the case description gives; its
displacement thickness narrows the core, which then runs faster and recovers less. By 30 step heights the core runs
1.6-3.0 % faster and the recovery drops by 0.028 to 0.052, depending on how thick the side walls' boundary layers start
(a quarter of the floor's to one and a half times it; the shape factor bracketed 1.4-1.8 changes it by 0.003). Every
case is at least the 0.022 the model misses by, so the side walls can account for the miss; the estimate cannot say
exactly how much of it, because the side walls' own inflow is not in the case description. A 3D model with the side
walls would settle it ([`sidewall_estimate.py`](../validation/step_driver_seegmiller/sidewall_estimate.py)).

**How I know it's the model and not the numerics.**
- **Inflow matched first,** on what the case description gives (not the answer): the momentum thickness 4 step
  heights upstream within 0.7 %.
- **Mesh study** (about 36k, 71k and 142k cells): reattachment 6.414, 6.408, 6.404, mesh uncertainty 0.2 %; skin
  friction at 20 step heights 1.9 %. The pressure recovery changes by under 0.001 between meshes (its steps grow,
  so no formal uncertainty), far below the 0.0027 by which it fails.
- **Outlet length** (30 or 50 step heights): reattachment changes by 1 × 10⁻⁶. **Inlet turbulence** (0.5-2 %):
  0.06 %. Neither matters.
- **Reported, not hidden:** the finest mesh stopped at its 80,000-iteration cap just short of its velocity residual
  target (3.6 × 10⁻⁷ against 2 × 10⁻⁷). That is a verification fail on that mesh. Its effect on the verdicts is
  bounded by the mesh-to-mesh spread above.
- **Honest about what was known:** the measured reattachment length was seen when the data was downloaded and is
  declared in every case file; the skin friction and pressure tables were opened only to write the comparison script
  after the predictions were committed, and the comparison ran once.

**Predictions against outcome:** reattachment within about 3 % (held, +2.3 %); skin friction passes, low near 10
step heights (passed, but low at 16-28 instead); pressure recovery passes, moderate confidence (missed).

## Limits

- Smooth walls only; no roughness (the Colebrook range).
- The reference is a correlation of measurements, with about ±2 % scatter, not the measurements themselves.
- One turbulence model (k-omega SST as implemented in openfoam.org v14).
- Part 2: 2D, so no tunnel side walls (the pressure-recovery miss); one geometry and Reynolds number.

## Evidence

- low-Re mesh studies: [first](../runs/20261122-104218_pipe_rans_mesh/report.md) (40 / 80 / 160),
  [revision 1](../runs/20261122-134230_pipe_rans_mesh_r1/report.md) (the stalled solver),
  [revision 2](../runs/20261122-153857_pipe_rans_mesh_r2/report.md) (80 / 160 / 320, converged),
  [revision 3](../runs/20261122-202459_pipe_rans_mesh_r3/report.md) (160 / 320 / 640: verified)
- [Reynolds sweep](../runs/20261122-104744_pipe_rans_reynolds/report.md), wall functions:
  [core mesh study](../runs/20261122-135114_pipe_rans_wf_mesh/report.md) and
  [first-cell placement](../runs/20261122-140211_pipe_rans_wf_yplus/report.md)
- case files: `cases/pipe_rans_*.toml` (predictions before each run, results scored after)
- code: `models/cfd/pipe_openfoam.py`, `models/cfd/run_pipe.sh`, `studies/pipe_flow.py`, `tests/test_pipe_flow.py`;
  figure `scripts/make_pipe_figure.py`
- part 2: [mesh study](../runs/20261122-233146_step_mesh/report.md), [outlet length](../runs/20261122-233146_step_outlet/report.md),
  [inlet turbulence](../runs/20261123-035753_step_inlet_tu/report.md); the one comparison
  `validation/step_driver_seegmiller/RESULTS.md` and its protocol log `PROTOCOL.md`; case files `cases/step_*.toml`;
  code `models/cfd/step_openfoam.py`, `studies/step_flow.py`, `tests/test_step_flow.py`

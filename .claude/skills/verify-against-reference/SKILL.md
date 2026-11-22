---
name: verify-against-reference
description: Verify a completed simulation or CAD run against independent checks (analytical references, conservation, convergence, mesh GCI, model-validity limits, cross-tool comparison) using tolerances fixed in the case file. Use when the user asks to verify, check, validate numerically, or sanity-check a run in runs/.
---

# Verify a run against independent references

## Supported

Any run produced by the `run-case` skill. Checks are defined per study in
`studies/<name>.py` (`verify_point`, and `verify_run_level` for checks that need several
points). References live in `validation/` and must not import from `models/`; keep it that way.

| Study | Per-point checks | Run-level checks |
|---|---|---|
| mass-spring-damper (`msd`) | closed-form step response, overshoot, settling, steady state, energy balance, solver convergence | - |
| quarter car (bump) (`quarter_car`) | matrix-exponential reference, peak accel, return to rest, energy balance (Simpson), solver convergence, **no_wheel_lift (validity)** | - |
| quarter car (iso8608) (`quarter_car`) | window RMS vs closed-form transfer functions, transient decayed, energy balance, solver convergence, **no_wheel_lift (validity)** | - |
| cantilever FEA (`cantilever`) | reaction equilibrium, tip deflection vs Timoshenko, extrapolated root stress vs beam theory, **linear_material, small_deflection (validity)** | discretization uncertainty (GCI or oscillatory half-range) over the 3 finest meshes |
| mounting plate (`mounting_plate`) | valid solid, volume vs closed form, bounding box, hole count/positions/diameters, STEP round trip | - |
| strap with a hole (CAD to FEA) (`strap_hole`) | CAD area, applied load, equilibrium, force across the ligament, uniform far field, Kt vs Peterson (model form), **linear_material (validity)** | GCI on every requirement metric (hole-edge element size sweep), with the design-order test |
| bracket modal (vibration) (`bracket_modal`) | CAD volume, modes identified, flapwise and in-plane vs Timoshenko, torsion vs Saint-Venant (model form), first-mode effective mass, first-mode shape (MAC), **beam_reference_valid (validity)** | GCI on the first frequency (element-size sweep) |
| strap fatigue (chained) (`strap_fatigue`) | FE equilibrium, ligament force, Kt vs Peterson, S-N fit scatter, S-N extrapolation vs ASM high-cycle value, life round trip, **elastic_notch (validity)** | - |
| roller contact (`hertz_contact`) | equilibrium, contact force balance, Hertz peak pressure / half-width / subsurface shear / shear depth at the carried load, penalty penetration, **resolution, elastic (validity)** | GCI on peak pressure and subsurface shear |
| duct flow (CFD, 3D) (`duct_flow`) | checkMesh, Ux residual, pressure-gradient history (last 10 % of iterations), no cross-flow, imposed mean velocity, pressure gradient and full velocity field vs exact rectangular-duct series, **laminar (validity)** | GCI on the pressure gradient (cells_across_gap sweep) |
| heat-sink fin (CalculiX, 3D conduction) (`fin`) | energy balance (base RFL + base-node film share vs convective loss integrated from nodal temperatures), tip-face mean and base heat flow vs 1D fin theory with convective tip (model form), cross-section-mean temperature profile vs 1D, tip-face minimum is the global minimum, **one_d_reference_valid (Biot, validity)** | GCI on the tip excess temperature and base heat flow (element_size_mm sweep) |
| channel flow (CFD) (`channel_flow`) | checkMesh, iterative convergence, mass conservation, imposed flow rate, force balance (tau_w vs pressure gradient), Poiseuille profile / pressure gradient / wall shear, pressure-drop correlation (model form), **laminar, entrance_before_window, fully_developed (validity)** | GCI over the 3 finest meshes (cells_across_gap sweep) on the fully developed metrics and the pressure drops |
| cold plate, thermal chain (OpenFOAM + CalculiX) (`cold_plate`) | per stage before its result is used. CFD: checkMesh, field convergence, flow rate, developed inflow, exact energy balance, wall temperature vs thermal-entry reference with the converged flux profile (model form; outside 2 gap heights of the plate edges, where the flux steps), wall symmetry. Coupling and handoffs: loop converged, interface temperature and flux, heat handed to the CFD and passed by the plate, nodal temperatures into the stress solve. Plate: every node vs the exact 2D Fourier series, 1D slab (model form). Stress: exact uniform-temperature case through the same deck, reaction balance, membrane force and peak / field vs beam theory in plane strain (model form). **laminar, reference_assumption, linear_material, no_buckling, thin_plate (validity)** | GCI on every requirement metric (cells_across_gap sweep; the plate is refined with the CFD) |
| tapered bracket (optimisation loop) (`tapered_bracket`) | CAD volume, load applied (sum and tip area), reaction equilibrium, tip deflection vs tapered Timoshenko beam (model form), fitted FE stress / M/Z ratio and 2-element bin means vs 1 (model form), **linear_material, small_deflection, beam_reference_valid, slender (validity)** | optimisation run: optimum found, optimiser converged; confirmation run: GCI on the requirement metrics (element_size_mm sweep) |
| heated channel, thermal entry (CFD) (`heated_channel`) | checkMesh, temperature convergence, flow rate, developed inflow, laminar, exact energy balance, wall temperature vs Graetz (exact along x), peak vs reference, reference assumption (no axial conduction) | GCI on the requirement metrics (cells across the gap) |
| strut buckling (`strut_buckling`) | equilibrium, critical load vs Euler with Engesser shear correction, half-sine mode shape, amplification e0 / (1 - P/P_cr), Southwell P_cr vs the eigenvalue and the imperfection, first yield vs Perry-Robertson and bracketed by increments; validity: slender, Euler range, moderate deflection | GCI on the requirement metric and the critical load |
| strap proof test, plasticity (`strap_plastic`) | equilibrium loaded and unloaded, elastic Kt vs Peterson, notch strain bracketed by Neuber and Glinka, Neuber reference, residual stress vs Neuber with elastic unloading and exactly by superposition of the FE's own runs, elastic unloading; validity: contained yield, net section elastic, small strain | GCI on the requirement metrics (hole element ratio) |
| bolted joint, friction contact (`bolted_joint`) | clamp-force and shear balance, gross slip reached, slip load extrapolated to a rigid interface = mu x clamp force (exact; companion solve at 100 E), deformable slip load vs mu x clamp force (model form: the interface tilts with the strain), plate compliance and contact diameter vs VDI 2230 (model form), pressure cone fits; validity: bolt within proof load, no bolt bearing | GCI on the requirement metrics (element size) |
| clevis bracket (3D optimisation loop) (`clevis_bracket`) | valid B-rep, meshed volume vs CAD volume, force and moment equilibrium of the base reactions with the pin load, lug section vs beam theory where clear of gussets and hole (model form); validity: below yield, small deflection. No closed form for the whole part: the fillet peak's mesh convergence is the deciding evidence | optimisation: optimum found, optimiser converged; element-size sweeps: GCI, and each requirement checked with the uncertainty added |
| Turek-Hron flag, static (FSI solid stage) (`flag_csm`) | increments complete, equilibrium (clamp reaction + weight lumped on the clamp nodes, computed exactly from the mesh), point A vs the large-deflection elastica (model form), load path and deflected centreline vs elastica, modal f1 vs Euler-Bernoulli; validity: slender. Requirement: point A within 1 % / 2 % of the published CSM1 / CSM2 values | GCI on ux(A), uy(A), f1 (element_size_mm) |
| Turek-Hron flag, dynamic (`flag_csm3`) | small-amplitude companion run at the modal frequency (integrator alone), returns to its start height each swing, trough depths and periods repeat (energy drift), modal f1 vs beam theory, enough periods; validity: steps per period. Requirements: last-period mean, amplitude, frequency within the band of the published CSM3 rows | time-step GCI on the band metrics (time_step_s) |
| Turek-Hron fluid stage (CFD) (`turek_hron_cfd`) | checkMesh, SIMPLE residual targets met, force history settled, inflow equals the benchmark parabola at every inlet face, flow rate (midpoint sampling error), mass conservation; validity: laminar. Requirement: drag and lift within 1 % / 2 % of the published CFD values | GCI on drag and lift (cell_size_m) |
| Turek-Hron FSI, coupled (`turek_hron_fsi`) | checkMesh, every coupling window converged, steady state reached, force transfer (fluid force on the flag + clamp reaction in the solid = 0), inflow parabola at every inlet face; validity: laminar. Requirement: point A displacements, drag and lift against the published FSI values | GCI on the requirement metrics (fluid_cell_size_m) |
| electric-machine electromagnetics (`motor_em`) | three-phase symmetry of the flux-linkage fundamental and 120 deg shifts, flux linkage from winding theory and the air-gap field's fundamental vs FEMM's coil integration (model form), zero mean open-circuit torque; validity: time steps per electrical period. Test data (ORNL) is kept for a separate blind comparison | GCI on the requirement metrics and the flux linkage (mesh_fineness) |

Two kinds of check, both gating verification:
- **numerical**: were the equations solved correctly?
- **validity**: does an assumption of the model hold for this result? A validity FAIL
  means the model is the wrong tool for that point. Say so plainly. Do not suggest
  loosening the limit. The fix is a different scenario or a better model, and that is
  the user's call.

A failed run-level check that names a metric (mesh convergence of that metric) withholds
the verdict of every requirement on that metric at every point; the report says so.

Tolerances come from `[verification]` in the run's saved `inputs/case.toml`.

## Procedure

1. Confirm `runs/<run_id>/manifest.json` exists. If the user did not name a run, use the newest
   directory in `runs/` and say which one you picked.
2. Run `.venv/Scripts/python.exe -m harness verify runs/<run_id>`.
   Exit code 0 means every check passed. Exit code 1 means at least one FAIL or NOT_RUN.
3. Read `runs/<run_id>/verification.json`. For each point, report the status. For each FAIL,
   give the value, the tolerance, and the ratio between them.
4. Look at one or two `points/<label>/response.png` plots, at least the worst-case point, and
   say whether the overlay and error panel agree with the numbers.
5. Interpret failures. Do not fix them silently:
   - `reference_agreement` + `solver_convergence` fail together: the solver tolerance is too
     loose, or the model differs from the reference equations.
   - `reference_agreement` fails alone: the model and reference disagree on the equations
     (units, sign, parameter mapping).
   - `steady_state` fails: `t_end_s` is too short; metrics that use the final value are
     unreliable.
   - `energy_balance` fails: the output grid is too coarse for the integral, or the
     model dissipates energy wrongly.
   - FEA `tip_deflection_reference` fails while the discretization check fails too: the mesh is
     too coarse or the element type is too stiff (for example linear tets in bending).
   - `discretization_*` reports regime `divergent`: the refinement study is not converging.
     Check the mesh sizes and element order before reading any result.

## Cross-tool check

When a case file has a `[cross_check]` section (for example `cases/msd_step_modelica.toml`
checked against case `msd_step`), compare it with a completed run of the other case:

1. Find a run of the `against_case` with the same sweep. If there isn't one, run that case with
   the `run-case` skill.
2. Run `.venv/Scripts/python.exe -m harness compare runs/<this_run> runs/<other_run>`.
   This writes `cross_check_<other_run>.json` into `<this_run>`.
3. Run `.venv/Scripts/python.exe -m harness report runs/<this_run>` again so the report
   includes the cross-check table.

The two tools agreeing does not replace the analytical check. It adds evidence that neither
implementation has a set-up error, such as a sign, units, or parameter-mapping slip, that the
other lacks.

## Rules

- A solver success message or a plausible plot is not verification.
- Never loosen a tolerance to turn a FAIL into a PASS. Changing a tolerance needs a written
  reason, an edited case file, and a new run.
- If `verify` raises "no longer matches the hash", the saved inputs were edited after the run.
  Report this. Do not re-hash.
- These checks establish **numerical verification** only. Say so. Physical validation needs test
  data, and none exists for synthetic cases.

## Artifacts

`verification.json`, plus `points/<label>/{checks.json, reference.csv, response.png}`.

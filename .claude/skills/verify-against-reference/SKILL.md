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
| mass-spring-damper | closed-form step response, overshoot, settling, steady state, energy balance, solver convergence | - |
| quarter car (bump) | matrix-exponential reference, peak accel, return to rest, energy balance (Simpson), solver convergence, **no_wheel_lift (validity)** | - |
| quarter car (iso8608) | window RMS vs closed-form transfer functions, transient decayed, energy balance, solver convergence, **no_wheel_lift (validity)** | - |
| cantilever FEA | reaction equilibrium, tip deflection vs Timoshenko, extrapolated root stress vs beam theory, **linear_material, small_deflection (validity)** | discretization uncertainty (GCI or oscillatory half-range) over the 3 finest meshes |
| mounting plate | valid solid, volume vs closed form, bounding box, hole count/positions/diameters, STEP round trip | - |
| strap with a hole (CAD to FEA) | CAD area, applied load, equilibrium, force across the ligament, uniform far field, Kt vs Peterson (model form), **linear_material (validity)** | GCI on every requirement metric (hole-edge element size sweep), with the design-order test |
| duct flow (CFD, 3D) | checkMesh, Ux residual, pressure-gradient history (last 10 % of iterations), no cross-flow, imposed mean velocity, pressure gradient and full velocity field vs exact rectangular-duct series, **laminar (validity)** | GCI on the pressure gradient (cells_across_gap sweep) |
| heat-sink fin (CalculiX, 3D conduction) | energy balance (base RFL + base-node film share vs convective loss integrated from nodal temperatures), tip-face mean and base heat flow vs 1D fin theory with convective tip (model form), cross-section-mean temperature profile vs 1D, tip-face minimum is the global minimum, **one_d_reference_valid (Biot, validity)** | GCI on the tip excess temperature and base heat flow (element_size_mm sweep) |
| channel flow (CFD) | checkMesh, iterative convergence, mass conservation, imposed flow rate, force balance (tau_w vs pressure gradient), Poiseuille profile / pressure gradient / wall shear, pressure-drop correlation (model form), **laminar, entrance_before_window, fully_developed (validity)** | GCI over the 3 finest meshes (cells_across_gap sweep) on the fully developed metrics and the pressure drops |

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

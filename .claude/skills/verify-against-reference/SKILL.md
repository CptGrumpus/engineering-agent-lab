---
name: verify-against-reference
description: Verify a completed simulation run against independent checks (analytical reference, energy balance, steady state, solver convergence) using tolerances fixed in the case file. Use when the user asks to verify, check, validate numerically, or sanity-check a run in runs/.
---

# Verify a run against independent references

## Supported

Runs produced by the `run-case` skill for model `msd`. The reference is the closed-form
step response in `validation/msd_analytical.py`. That module does not import the model code;
keep it that way.

## Checks (per sweep point)

| Check | What it shows |
|---|---|
| `reference_agreement` | Numerical x(t) matches the closed-form solution over the full time history |
| `overshoot_reference` | The overshoot metric matches the closed-form formula |
| `settling_reference` | The settling-time metric matches the analytical curve |
| `steady_state` | x(t_end) is close to F/k, so the simulation ran long enough for "final value" to mean something |
| `energy_balance` | Work in = kinetic + potential + dissipated energy (a conservation check) |
| `solver_convergence` | Tightening rtol/atol 100x does not change the answer |

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
   - `energy_balance` fails: the output grid is too coarse for the trapezoid integral, or the
     model dissipates energy wrongly.

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

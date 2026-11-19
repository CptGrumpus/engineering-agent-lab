---
name: requirements-report
description: Produce a requirements-compliance report for a run, tracing each requirement to its result, margin, verification checks, and evidence files, with limitations stated. Use when the user asks for a report, compliance summary, review package, or "did it meet requirements" for a run in runs/.
---

# Requirements-compliance report

## Inputs

A run directory in `runs/`. Run `verify-against-reference` first. Without it, every verdict is
marked *unverified*.

## Procedure

1. Run `.venv/Scripts/python.exe -m harness report runs/<run_id>`.
   It writes `report.md` (for people) and `report.json` (for machines).
2. Read `report.md` and give the user a short summary:
   - Overall verification status and simulation status.
   - For each requirement: which sweep points pass or fail, and the smallest margin among the
     passing points. Name any point within about 10 % of a limit as sensitive.
   - The design region that meets every requirement (for example, "ζ between 0.5 and 2.0
     meets REQ-001..003").
   - Any verdict marked *(unverified)* or *NO RESULT*, with the reason.
3. Point the user to `runs/<run_id>/report.md` and the worst-case `response.png`.

## Verdict rules (applied by the harness; do not override)

| Verification | Requirement met | Verdict |
|---|---|---|
| PASS | yes / no | PASS / FAIL |
| FAIL or not run | yes / no | PASS (unverified) / FAIL (unverified) |
| point did not complete | - | NO RESULT |

## Rules

- Report failed requirements and failed checks as plainly as passes. Do not hide them as
  "minor".
- Keep these separate: **numerical error** (the verification checks), **modeling assumptions**
  (the `assumptions` list in the case file), and **physical uncertainty** (not quantified for
  synthetic cases).
- Never state that a design is accepted. The report ends with "Pending human review" on
  purpose. Engineering acceptance belongs to the user.
- Do not edit `report.md` by hand. If something is wrong, fix the harness or the case and
  regenerate the report.

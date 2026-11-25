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
- A write-up's headline (a portfolio page's Answer, a summary line) carries the verification
  status too, not only the requirement verdicts: "passes every requirement" over runs whose
  verification FAILed on a cross-check misleads (study 12, page 25: two narrow misses were
  in the case files but not in the Answer). Quote each check's number from the run's
  checks.json for every point, not one point's value as "or better".
- Take every headline number from one named evidence mesh, and every range over all evidence runs, computed from
  their checks.json, not from memory of one run. Page 26 said yield safety 1.82 (the 0.1 mm mesh) in the Answer and
  1.83 (the 0.14 mm evidence mesh) in the table, and its Kt-fit range left out two runs (the dashboard session caught
  both).
- Quote a verification test's accuracy at the setting the evidence runs use, not the best setting tested. Page 27
  said radiation "within 0.05 %" (16 directions per quarter) while every enclosure run used 4 (0.92 %, against a 1 %
  limit). Count pass/fail lists from checks.json too (page 27 said five failed heat balances; it was six), and round
  once, from the raw value (98.4456 is 98.4, not 98.45 then 98.5).
- When a fix cools the part a requirement names, report the other parts' maxima as well: the enclosure's bridge
  cooled the component and left the board the hottest part (85.2 C at 1 W/mK, over the 85 C limit the component
  passed). A requirement's scope is the client's call; the write-up must put the question to them.
- Keep these separate: **numerical error** (the verification checks), **modeling assumptions**
  (the `assumptions` list in the case file), and **physical uncertainty** (not quantified for
  synthetic cases).
- Never state that a design is accepted. The report ends with "Pending human review" on
  purpose. Engineering acceptance belongs to the user.
- Do not edit `report.md` by hand. If something is wrong, fix the harness or the case and
  regenerate the report.

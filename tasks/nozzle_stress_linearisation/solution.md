# Reference solution: nozzle junction stresses, design by analysis

**Method.** Stress linearisation along the classification line, as in ASME BPVC Section VIII
Division 2, Annex 5-A (here in our own words), with t = 16 mm:

- membrane: σ_m = (1/t) ∫ σ ds for **every** component, including the shears;
- bending: σ_b = (6/t²) ∫ σ (t/2 − s) ds for the two normal components tangent to the wall
  only (axial and hoop), not for the radial component along the line or the shears;
- PL = von Mises of the membrane tensor; P + Q = von Mises of (membrane ± bending) at
  s = 0 and s = t, the larger of the two.

With 21 equally spaced points, Simpson's rule and the trapezoid rule agree to 0.005 % on PL
and 0.14 % on P + Q.

**Result.**

| | Value | Limit | Verdict |
|---|---|---|---|
| Membrane components (r, a, h, τ_ra, τ_ah, τ_hr) | 7.69, 64.10, 234.11, −11.56, 0.08, −0.05 MPa | | |
| Bending (a, h) | −100.52, −12.82 MPa | | |
| PL | **205.13 MPa** | 207 | met, by 1.87 MPa (0.9 %) |
| P + Q | **239.57 MPa**, inner surface (211.48 at the outer) | 414 | met |

The margin on PL is thin, but it is real for this model: the same line on three meshes gave
205.04 / 205.13 / 205.13 MPa (GCI 0.03 %).

The verdict is for this line, as the task fixes it. For the nozzle as a design, the placement is a
judgement: a line through the crotch corner gives PL 256.7 MPa and fails (study 18's placement cases).
A grader should not accept "the nozzle needs no pad" as a design conclusion beyond the stated line.

**Evidence.** Portfolio study 18 ([page](../../portfolio/18-pressure-vessel-nozzle.md)): run
`20261122-102842_pv_nozzle_mesh`, finest mesh, line `shell_long`. The table in the task is that
run's sampled profile rounded to 0.01 MPa; `harness/linearize.py` on the rounded table gives the
values above (checked in `tests/test_tasks.py`). The same run checks equilibrium exactly and
the far shell against the Lamé cylinder.

**Grading tolerances.** PL ±0.3 % (the integration rule does not matter at that level; dropping
the shear components does), P + Q ±0.5 %, the surface and both verdicts exact.

## Traps this task is designed to expose

| Trap | What it produces | Criterion that fails |
|---|---|---|
| Averaging the von Mises stress through the wall instead of the components | PL 211.8 MPa: the PL verdict flips to "fails" | PL, PL verdict |
| Comparing the surface peak with the membrane limit | 239.4 MPa against 207: "fails" | PL, PL verdict |
| Linearising the hoop component alone | 234.1 MPa: "fails" | PL, PL verdict |
| Tresca instead of von Mises | PL 228.7 MPa: "fails" | PL, PL verdict |
| Dropping the shear components from the membrane | PL 204.1 MPa (still passes) | PL |
| Bending applied to every component, including the radial one and the shears | P + Q 242.0 MPa (+1.0 %) | P + Q |
| Bending sign reversed (s measured from the outer surface) | P + Q governed at the "outer" surface | governing surface |

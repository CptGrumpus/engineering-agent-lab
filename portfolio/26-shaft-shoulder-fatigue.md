# Gearbox shaft shoulder: fatigue and overload safety at the fillet, and the step that passes

[Portfolio index](../PORTFOLIO.md) · Structures and vibration

| | |
|---|---|
| **Answer** | The intermediate shaft as drawn (42CrMo4 Q&T, D 40 -> d 32 mm, fillet 1.6 +0.4 / -0.2 mm; rotating bending 300 N m, steady torque 500 N m) **fails both requirements**: fatigue safety **1.19** at the nominal fillet and **1.15** at its lower tolerance (limit 1.5, modified Goodman), first-cycle yield safety at a 1.5 x overload **1.83 / 1.77** (limit 2.0). **No fillet that fits under the 4 mm shoulder reaches 1.5** (1.47 at 3.9 mm). Scaling the step does: the smallest small diameter meeting both is **35.1 mm**, so a **36 mm seat with a 45 mm shoulder** (fillet 1.8 mm) gives fatigue safety **1.62** and yield safety **2.52** across the fillet tolerance. Verification: two checks fail, neither on a verdict: the mesh study's check on the torsion factor Kts (it creeps up 0.12 % at the finest level, against a measured noise floor of 0.11 %; no requirement uses Kts directly) and the element quality at a 3.7 mm fillet (0.065 against 0.1; that point is unverified, its neighbours at 3.5 and 3.9 mm pass). The client, loads and limits are synthetic; the material values are catalogue values and every fatigue relation is from a fetched, published source. |
| **Discipline** | Machine elements: shaft fatigue at a stress concentration |
| **Tools** | Gmsh (Python API), CalculiX, Python |
| **Methods** | 3D half model (symmetry for bending, antisymmetry for torsion), Kt and Kts from FE, Shigley's stress-life method (Marin factors, Neuber notch sensitivity, von Mises combined stresses, modified Goodman, ASME elliptic), mesh study with a measured noise floor, published Kt fits (Pilkey, Roark) |

![Stress along the fillet, bending and torsion, at the recommended 36 mm step](../runs/20261124-155125_shaft_fillet_size/points/p03_d36/response.png)

## The question

A two-stage gearbox's intermediate shaft steps from a 40 mm shoulder to a 32 mm seat through a 1.6 mm fillet (+0.4 /
-0.2 mm). It carries a rotating bending moment of 300 N m (fully reversed at the fillet) and a steady torque of 500 N m.
Is the fatigue safety at the fillet at least 1.5 (REQ-S1), is the first-cycle yield safety under a 1.5 x overload at
least 2.0 (REQ-S2), and what is the smallest fillet radius that meets REQ-S1 (REQ-S3)?

## The answer

| Fillet radius | Kt (bending) | Kts (torsion) | Fatigue safety (Goodman) | ASME elliptic | Yield safety at 1.5 x |
|---|---|---|---|---|---|
| 1.4 mm (lower tolerance) | 2.232 | 1.599 | **1.15** | 1.39 | **1.77** |
| 1.6 mm (nominal) | 2.136 | 1.548 | **1.19** | 1.44 | **1.83** |
| 2.0 mm (upper tolerance) | 1.988 | 1.475 | 1.26 | 1.53 | 1.92 |
| 2.5 mm | 1.858 | 1.409 | 1.33 | 1.61 | 2.02 |
| 3.0 mm | 1.763 | 1.361 | 1.38 | 1.69 | 2.09 |
| 3.5 mm | 1.690 | 1.325 | 1.43 | 1.75 | 2.16 |
| 3.7 mm | 1.664 | 1.312 | 1.45 (unverified) | 1.77 | 2.18 |
| 3.9 mm (0.1 mm below the shoulder height) | 1.640 | 1.300 | 1.47 | 1.79 | 2.20 |

REQ-S1 fails at every radius and REQ-S2 across the whole tolerance band (it passes from about 2.4 mm). So REQ-S3 has no
answer on this step: the fillet cannot be made large enough under a 4 mm shoulder.

What does pass: scaling the step with its diameter (D = 1.25 d, fillet 0.05 d at its -0.2 mm tolerance), with the same
loads and material:

| Small diameter d | Shoulder D | Fillet (lower tol.) | Fatigue safety | Yield safety |
|---|---|---|---|---|
| 32 mm (as drawn) | 40 mm | 1.40 mm | 1.15 | 1.77 |
| 34 mm | 42.5 mm | 1.50 mm | 1.37 | **2.12** |
| 35 mm | 43.75 mm | 1.55 mm | 1.49 | 2.32 |
| **36 mm** | **45 mm** | **1.60 mm** | **1.62** | **2.52** |
| 38 mm | 47.5 mm | 1.70 mm | 1.90 | 2.96 |

Interpolated, the smallest d is 35.1 mm for fatigue and 33.3 mm for yield. A 36 mm seat is the recommendation with
margin; a stronger steel or a rolled fillet are the other levers, not assessed here.

## How it works

- **Kt from the FE model.** CalculiX solves half of the stepped shaft (the profile revolved by 180 degrees, 10-node
  tetrahedra from Gmsh, refined along the fillet). Two linear load cases on one mesh: bending (the plane through the
  axis is a symmetry plane) and torsion (the same plane is antisymmetric). The large end is clamped; on the loaded end
  the exact beam stresses are applied as consistent nodal forces, so the small section carries the beam field from the
  end on. Kt is the peak nodal max principal stress on the fillet over 32 M / (pi d^3); Kts the peak max shear over
  16 T / (pi d^3). Both peaks sit 15-17 degrees up the fillet from the small cylinder.
- **Fatigue by Shigley's method** (Mechanical Engineering Design, 11th ed., chapter 6, checked against the published
  solutions manual's worked values): Se' = 0.5 Sut; machined surface factor and size factor; notch sensitivity from
  Neuber's constant for steels (separate bending and torsion fits) at the fillet radius; Kf and Kfs on the alternating
  bending and mean torsion stresses, combined by von Mises; modified Goodman (and ASME elliptic beside it).
- **Yield**: von Mises of the overload stresses with Kf and Kfs applied (the conservative form Shigley uses for shafts).
- DIN 743 is a paid standard and was not used.

## How I know it's right

- **Equilibrium**: the clamp's reaction moment matches the applied moment to 1e-7 in both load cases.
- **Load introduction**: the consistent nodal forces give M / 2 and T / 2 on the half model to 1.4e-5.
- **Beam theory** in the small section, away from the fillet: within 0.3-0.6 % at every point (0.6 % on the finest
  mesh, 0.3-0.5 % at the 0.14 mm evidence mesh).
- **Published fits**: FE Kt is 1.5-6.7 % above Pilkey's fit of Peterson's charts (more at small radii), Kts 1.8-2.7 %
  below. Recent finite-element work finds Peterson's bending values up to 15 % low, so this is the expected direction;
  the FE value is used for the verdicts. Two published fits of the same charts (Pilkey 2nd ed., Roark 8th ed.) differ by
  up to 2.2 % themselves.
- **Mesh study** (fillet elements 0.28 / 0.2 / 0.14 / 0.1 mm) with a **measured noise floor** (five perturbed meshes at
  0.14 mm: 0.11-0.23 %): Kt, the fatigue and the yield safety converge within the noise (uncertainty about 0.1 %); Kts
  creeps up 0.12 % at the finest level, just above its 0.11 % floor, so that one check fails. No requirement uses Kts
  directly; its whole range over four meshes is 0.27 %, against margins of 9-23 % on the verdicts.
- **Off-plane consistency**: the peak read away from the refined plane (cos-corrected for bending) agrees with the
  on-plane peak within 0.04-1.3 %, closing with refinement.
- **Reference relations unit-tested** against the source's own worked numbers (Neuber's constant, notch sensitivity,
  Kf, surface and size factors, endurance limit).

## What the checks caught

- **A sign, not a stress.** The first mesh run failed its end-load check by exactly 200 % in torsion: the tractions turn
  the end in the negative sense and the check compared signed values. The equilibrium check passed; the end-load check
  now compares magnitudes. The run is kept.
- **Nodal-stress noise read as divergence.** Kts and the yield safety moved by 0.1-0.2 % between fine meshes and the
  convergence index called them divergent. A finer level did not settle it (it added another noisy sample); measuring
  the noise with perturbed meshes did, as in the cracked-plate study.
- **A maximum over many nodes is biased upward.** Taking the peak over every fillet node picked nodes 1.6-1.9 mm off the
  plane that read 0.9 % above the true peak, which bending's cos(theta) variation forbids. The peak is read on the
  refined plane; the off-plane maximum became a check.
- **Straight-sided end faces lost 1.8 % of the moment** (the polygon under the circle); integrating on the curved
  quadratic faces closes it to 1.4e-5.
- **A sliver face inverted the mesh.** At a 3.9 mm fillet the shoulder face is 0.1 mm wide and 14 curved tetrahedra
  turned inside out; Gmsh's high-order optimisation untangles them (the optimised mesh moves the 3.5 mm result by
  0.03 %), and an element-quality check now guards it. It caught one more: at 3.7 mm the optimised mesh's worst
  element is poor (scaled Jacobian 0.065, under the 0.1 floor), so that point is reported unverified.
- **The textbook's own editions differ.** Shigley's 11th edition lowered the machined surface factor (6.5 % less
  endurance limit at 1000 MPa than the 10th); the 10th would give fatigue safety about 1.25 at the nominal fillet, still
  a fail. And the solutions manual has an arithmetic slip in one worked value (torsion, 64 kpsi), caught because every
  fit was tested against more than one worked example.

## Limits

- Shigley's stress-life method with catalogue material values; no test certificates, no reliability factor (the mean
  endurance limit), no residual stresses, surface rolling or peening.
- No fretting or press-fit stress from a gear or bearing seated at the shoulder; no torsional alternation (steady
  torque).
- Elastic Kt; the yield check applies Kf to the overload (conservative).
- No physical test data.

## Evidence

- Mesh study [`shaft_fillet_mesh_r2`](../runs/20261124-160912_shaft_fillet_mesh_r2/report.md) (with the measured noise floor), noise
  [`shaft_fillet_noise`](../runs/20261124-154527_shaft_fillet_noise/report.md), radius
  [`shaft_fillet_radius`](../runs/20261124-152828_shaft_fillet_radius/report.md) and
  [`shaft_fillet_radius_r1`](../runs/20261124-160916_shaft_fillet_radius_r1/report.md), sizing
  [`shaft_fillet_size`](../runs/20261124-155125_shaft_fillet_size/report.md); the earlier mesh runs are kept
  (`runs/20261124-151223_shaft_fillet_mesh`, `runs/20261124-152823_shaft_fillet_mesh_r1`)
- Cases with predictions and results: `cases/shaft_fillet_*.toml`; model `models/fea/shaft_fillet_ccx.py`, study
  `studies/shaft_fillet.py`, references `validation/shaft_fatigue.py`

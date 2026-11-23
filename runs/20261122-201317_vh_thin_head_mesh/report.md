# Engineering review report: vh_thin_head_mesh

- **Run:** `20261122-201317_vh_thin_head_mesh`
- **Generated:** 2026-11-23T01:13:51+00:00
- **Case file SHA-256:** `094ff780644602902fff78f2c0c575697b7697782f70ea36f33a204fe0ea5a31`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Tools:** CalculiX This is Version 2.22
- **Code version:** git `4c77fe0eafecda65fba9b5bdb38291fd0893d47a` (uncommitted changes present)
- **Simulation status:** completed
- **Verification status:** FAIL

> **Warning:** verification did not pass for every point. Requirement verdicts marked *(unverified)* are not supported by evidence and must not be used for acceptance.

## Scope

Cylindrical shell (Ri 500 mm, t 16 mm) closed by an 8 mm hemispherical head (flush bore, a step outside), 3.5 MPa; axisymmetric CAX8 in CalculiX; mesh 2 / 1 / 0.5 mm through the wall (aspect 2); stresses linearised through the wall near the junction.

**Assumptions**

- Linear elastic steel, E 200 GPa, nu 0.3; small displacement (checked).
- Axisymmetric: the study-18 shell (Ri 500 mm, t 16 mm, 3.5 MPa) closed by a hemispherical head with the same bore; the shell's far end is the vessel's mid-length plane (symmetry, u_z = 0), 1000 mm (11 sqrt(R t)) from the junction. No nozzle (the nozzle sits mid-shell, far from the head).
- With a head thinner than the shell the outside steps down at the junction with no taper and no weld detail (a fabricated joint would taper the thicker plate; the step makes a re-entrant corner whose peak is not assessed here).
- Classification as at the nozzle: membrane on the lines within the junction region (3 sqrt(R t) = 270 mm of the junction, along the wall, on both sides) is local primary (PL), membrane plus bending there primary plus secondary (P + Q); the far head line (60 deg from the junction) is general primary (Pm). S_PS = 3 S.
- Allowable S = 138 MPa: synthetic, as in the rest of study 18; not from ASME Section II.

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-HJ1 | General primary membrane stress in the head away from the junction shall not exceed S (138 MPa). | `pm_head_MPa` | <= 138 MPa |
| REQ-HJ2 | Local primary membrane stress in the head-to-shell junction region (shell and head lines) shall not exceed 1.5 S (207 MPa). | `pl_junction_MPa` | <= 207 MPa |
| REQ-HJ3 | Primary plus secondary stress in the head-to-shell junction region shall not exceed S_PS = 3 S (414 MPa). | `pq_junction_MPa` | <= 414 MPa |

## Summary across points

| Point | element_size_mm | REQ-HJ1 | REQ-HJ2 | REQ-HJ3 | Checks |
|---|---|---|---|---|---|
| p00_element_size_mm-2 | 2 | 110.2 MPa: **PASS** | 127 MPa: **PASS (unverified)** | 173.3 MPa: **PASS (unverified)** | 6/6 PASS |
| p01_element_size_mm-1 | 1 | 110.2 MPa: **PASS** | 127 MPa: **PASS (unverified)** | 172.8 MPa: **PASS (unverified)** | 6/6 PASS |
| p02_element_size_mm-0.5 | 0.5 | 110.2 MPa: **PASS** | 127 MPa: **PASS (unverified)** | 171.8 MPa: **PASS (unverified)** | 6/6 PASS |

## Run-level checks

Checks that use several points together (for example mesh convergence).

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| discretization_pl_junction_MPa | relative discretization uncertainty of pl_junction_MPa, divergent (R = 6.439): no estimate | inf | 0.03 | FAIL |
| discretization_pm_head_MPa | relative discretization uncertainty of pm_head_MPa, converged to within the noise floor (spread 5.6e-07 <= 1e-05) | 3.53e-07 | 0.03 | PASS |
| discretization_pq_junction_MPa | relative discretization uncertainty of pq_junction_MPa, divergent (R = 2.200): no estimate | inf | 0.03 | FAIL |

A failed run-level check withholds the verdicts of requirements on `pl_junction_MPa`, `pq_junction_MPa` at every point: they are marked *(unverified)* in the table above.

![Requirement metrics across the sweep](sweep.png)

## Point details

### p00_element_size_mm-2

Parameters: shell_inner_radius_mm = 500, shell_thickness_mm = 16, head_thickness_mm = 8, shell_length_mm = 1000, pressure_MPa = 3.5, youngs_modulus_MPa = 2e+05, poisson_ratio = 0.3, element_size_mm = 2, element_aspect = 2, allowable_stress_MPa = 138

Derived: hoop_membrane_p_Ri_over_t_MPa = 109.4, allowable_PL_MPa = 207, allowable_PS_MPa = 414, sqrt_Rt_mm = 90.16, head_rule_thickness_mm = 6.341, lame_pm_shell_MPa = 96.21, lame_pm_head_MPa = 110.2

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-HJ1 | 110.2 MPa | <= 138 | 27.8 | **PASS** | [point.json](points/p00_element_size_mm-2/point.json) |
| REQ-HJ2 | 127 MPa | <= 207 | 80 | **PASS (unverified)** | [point.json](points/p00_element_size_mm-2/point.json) |
| REQ-HJ3 | 173.3 MPa | <= 414 | 241 | **PASS (unverified)** | [point.json](points/p00_element_size_mm-2/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| equilibrium_z | |axial reaction on the mid-length plane / 2-degree segment - p pi Ri^2| / p pi Ri^2 (exact: the pressure on the head's projected area) | 6.25e-08 | 1e-05 | PASS |
| lame_shell_membrane | |far-shell linearised membrane (von Mises) - the same linearisation of Lame| / Lame (exact) | 5.66e-04 | 5e-03 | PASS |
| lame_head_membrane | |far-head linearised membrane (von Mises) - the thick sphere's| / exact | 5.62e-05 | 5e-03 | PASS |
| lame_shell_hoop_range | |far-shell hoop stress, bore minus outside, FE - Lame| / Lame (the through-wall gradient, not only the mean) | 1.92e-04 | 5e-03 | PASS |
| small_displacement (validity) | max displacement / shell thickness (linear geometry) | 1.86e-02 | 1e-01 | PASS |
| far_lines_far (validity) | junction region / distance of the far lines (the far shell line at L / 2; the head line at the stated angle): far lines outside the bending zone | 5.41e-01 | 1e+00 | PASS |

![p00_element_size_mm-2 response](points/p00_element_size_mm-2/response.png)

### p01_element_size_mm-1

Parameters: shell_inner_radius_mm = 500, shell_thickness_mm = 16, head_thickness_mm = 8, shell_length_mm = 1000, pressure_MPa = 3.5, youngs_modulus_MPa = 2e+05, poisson_ratio = 0.3, element_size_mm = 1, element_aspect = 2, allowable_stress_MPa = 138

Derived: hoop_membrane_p_Ri_over_t_MPa = 109.4, allowable_PL_MPa = 207, allowable_PS_MPa = 414, sqrt_Rt_mm = 90.16, head_rule_thickness_mm = 6.341, lame_pm_shell_MPa = 96.21, lame_pm_head_MPa = 110.2

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-HJ1 | 110.2 MPa | <= 138 | 27.8 | **PASS** | [point.json](points/p01_element_size_mm-1/point.json) |
| REQ-HJ2 | 127 MPa | <= 207 | 80 | **PASS (unverified)** | [point.json](points/p01_element_size_mm-1/point.json) |
| REQ-HJ3 | 172.8 MPa | <= 414 | 241 | **PASS (unverified)** | [point.json](points/p01_element_size_mm-1/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| equilibrium_z | |axial reaction on the mid-length plane / 2-degree segment - p pi Ri^2| / p pi Ri^2 (exact: the pressure on the head's projected area) | 6.25e-08 | 1e-05 | PASS |
| lame_shell_membrane | |far-shell linearised membrane (von Mises) - the same linearisation of Lame| / Lame (exact) | 5.66e-04 | 5e-03 | PASS |
| lame_head_membrane | |far-head linearised membrane (von Mises) - the thick sphere's| / exact | 5.65e-05 | 5e-03 | PASS |
| lame_shell_hoop_range | |far-shell hoop stress, bore minus outside, FE - Lame| / Lame (the through-wall gradient, not only the mean) | 1.90e-04 | 5e-03 | PASS |
| small_displacement (validity) | max displacement / shell thickness (linear geometry) | 1.86e-02 | 1e-01 | PASS |
| far_lines_far (validity) | junction region / distance of the far lines (the far shell line at L / 2; the head line at the stated angle): far lines outside the bending zone | 5.41e-01 | 1e+00 | PASS |

![p01_element_size_mm-1 response](points/p01_element_size_mm-1/response.png)

### p02_element_size_mm-0.5

Parameters: shell_inner_radius_mm = 500, shell_thickness_mm = 16, head_thickness_mm = 8, shell_length_mm = 1000, pressure_MPa = 3.5, youngs_modulus_MPa = 2e+05, poisson_ratio = 0.3, element_size_mm = 0.5, element_aspect = 2, allowable_stress_MPa = 138

Derived: hoop_membrane_p_Ri_over_t_MPa = 109.4, allowable_PL_MPa = 207, allowable_PS_MPa = 414, sqrt_Rt_mm = 90.16, head_rule_thickness_mm = 6.341, lame_pm_shell_MPa = 96.21, lame_pm_head_MPa = 110.2

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-HJ1 | 110.2 MPa | <= 138 | 27.8 | **PASS** | [point.json](points/p02_element_size_mm-0.5/point.json) |
| REQ-HJ2 | 127 MPa | <= 207 | 80 | **PASS (unverified)** | [point.json](points/p02_element_size_mm-0.5/point.json) |
| REQ-HJ3 | 171.8 MPa | <= 414 | 242 | **PASS (unverified)** | [point.json](points/p02_element_size_mm-0.5/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| equilibrium_z | |axial reaction on the mid-length plane / 2-degree segment - p pi Ri^2| / p pi Ri^2 (exact: the pressure on the head's projected area) | 6.25e-08 | 1e-05 | PASS |
| lame_shell_membrane | |far-shell linearised membrane (von Mises) - the same linearisation of Lame| / Lame (exact) | 5.66e-04 | 5e-03 | PASS |
| lame_head_membrane | |far-head linearised membrane (von Mises) - the thick sphere's| / exact | 5.68e-05 | 5e-03 | PASS |
| lame_shell_hoop_range | |far-shell hoop stress, bore minus outside, FE - Lame| / Lame (the through-wall gradient, not only the mean) | 1.93e-04 | 5e-03 | PASS |
| small_displacement (validity) | max displacement / shell thickness (linear geometry) | 1.86e-02 | 1e-01 | PASS |
| far_lines_far (validity) | junction region / distance of the far lines (the far shell line at L / 2; the head line at the stated angle): far lines outside the bending zone | 5.41e-01 | 1e+00 | PASS |

![p02_element_size_mm-0.5 response](points/p02_element_size_mm-0.5/response.png)

## Limitations

- Elastic analysis only; pressure only (no weight, no supports, no thermal gradients, no fatigue).
- Thin-shell discontinuity theory is an independent check only with equal thicknesses; with a thinner head the FE is checked by its exact far fields, equilibrium and the mesh study.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

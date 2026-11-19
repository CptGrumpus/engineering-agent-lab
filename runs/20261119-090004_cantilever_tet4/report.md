# Engineering review report: cantilever_tet4

- **Run:** `20261119-090004_cantilever_tet4`
- **Generated:** 2026-11-19T14:01:14+00:00
- **Case file SHA-256:** `81cb0ff909a3c62cff32bf9fa7f44557b03905ae6f6fd339ed314566eed018e0`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2; Windows-11-10.0.26100-SP0
- **Tools:** freecadcmd C:\Users\mrstego\AppData\Local\Programs\FreeCAD 1.1\bin\freecadcmd.exe; CalculiX This is Version 2.22; FreeCAD 1.1.4
- **Code version:** git `cf813cec2ea2e8d2fea2f44f46ba0521707f8d32` (uncommitted changes present)
- **Simulation status:** completed
- **Verification status:** FAIL

> **Warning:** verification did not pass for every point. Requirement verdicts marked *(unverified)* are not supported by evidence and must not be used for acceptance.

## Scope

Steel cantilever, 200 x 20 x 20 mm, clamped at x = 0, 1000 N downward tip load distributed over the free end face. Mesh refinement (characteristic length 8 -> 1.95 mm, ratio 1.6) with LINEAR (4-node) tetrahedra; checks tip stiffness and root bending stress requirements.

**Assumptions**

- Linear elastic, isotropic, homogeneous steel (E = 210 GPa, nu = 0.3); checked against yield.
- Small deflections and strains (geometrically linear); checked: tip deflection / L.
- Ideal clamp: all displacements fixed on the x = 0 face (stiffer than a real bolted joint).
- Tip load applied as a uniform traction over the x = L face.
- Root bending stress is evaluated by extrapolating the top-fibre stress from 0.25L-0.75L to x = 0, because the clamp corners are stress singularities (peak FE stress there grows with mesh refinement).

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-C1 | Tip deflection under the 1000 N service load shall not exceed 1.0 mm. | `tip_deflection_mm` | <= 1 mm |
| REQ-C2 | Root bending stress shall not exceed 213 MPa (S355 yield / 1.67). | `root_bending_stress_MPa` | <= 213 MPa |

## Summary across points

| Point | mesh_size_mm | REQ-C1 | REQ-C2 | Checks |
|---|---|---|---|---|
| p00_mesh_size_mm-8 | 8 | 0.647 mm: **PASS (unverified)** | 82.22 MPa: **PASS (unverified)** | 3/5 FAIL |
| p01_mesh_size_mm-5 | 5 | 0.7884 mm: **PASS (unverified)** | 110.8 MPa: **PASS (unverified)** | 3/5 FAIL |
| p02_mesh_size_mm-3.125 | 3.125 | 0.8825 mm: **PASS (unverified)** | 129.8 MPa: **PASS (unverified)** | 3/5 FAIL |
| p03_mesh_size_mm-1.95312 | 1.95312 | 0.9236 mm: **PASS (unverified)** | 139.5 MPa: **PASS (unverified)** | 3/5 FAIL |

## Run-level checks

Checks that use several points together (for example mesh convergence).

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| discretization_tip_deflection_mm | relative discretization uncertainty of tip_deflection_mm, monotone (R = 0.437): GCI_fine, observed order 1.76, extrapolated 0.955426 | 0.0431 | 0.01 | FAIL |
| discretization_root_bending_stress_MPa | relative discretization uncertainty of root_bending_stress_MPa, monotone (R = 0.515): GCI_fine, observed order 1.41, extrapolated 149.909 | 0.0928 | 0.02 | FAIL |

![Requirement metrics across the sweep](sweep.png)

## Point details

### p00_mesh_size_mm-8

Parameters: length_mm = 200, width_mm = 20, height_mm = 20, youngs_modulus_MPa = 2.1e+05, poisson_ratio = 0.3, yield_strength_MPa = 355, tip_load_N = 1000, mesh_size_mm = 8, element_order = 1st

Derived: slenderness_L_over_h = 10, tip_deflection_euler_bernoulli_mm = 0.9524, tip_deflection_timoshenko_mm = 0.9597, root_bending_stress_beam_theory_MPa = 150

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-C1 | 0.647 mm | <= 1 | 0.353 | **PASS (unverified)** | [point.json](points/p00_mesh_size_mm-8/point.json) |
| REQ-C2 | 82.22 MPa | <= 213 | 131 | **PASS (unverified)** | [point.json](points/p00_mesh_size_mm-8/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| equilibrium | |R_fixed - (0, 0, F)| / F (sum of reactions) | 1.02e-12 | 1e-06 | PASS |
| tip_deflection_reference | |tip deflection FE - Timoshenko| / Timoshenko | 3.26e-01 | 2e-02 | FAIL |
| root_stress_reference | |extrapolated root stress FE - 6FL/(bh^2)| / beam theory | 4.52e-01 | 2e-02 | FAIL |
| linear_material (validity) | root bending stress / yield strength (linear elastic only below 1) | 2.32e-01 | 1e+00 | PASS |
| small_deflection (validity) | tip deflection / length (geometrically linear analysis) | 3.23e-03 | 1e-02 | PASS |

![p00_mesh_size_mm-8 response](points/p00_mesh_size_mm-8/response.png)

### p01_mesh_size_mm-5

Parameters: length_mm = 200, width_mm = 20, height_mm = 20, youngs_modulus_MPa = 2.1e+05, poisson_ratio = 0.3, yield_strength_MPa = 355, tip_load_N = 1000, mesh_size_mm = 5, element_order = 1st

Derived: slenderness_L_over_h = 10, tip_deflection_euler_bernoulli_mm = 0.9524, tip_deflection_timoshenko_mm = 0.9597, root_bending_stress_beam_theory_MPa = 150

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-C1 | 0.7884 mm | <= 1 | 0.212 | **PASS (unverified)** | [point.json](points/p01_mesh_size_mm-5/point.json) |
| REQ-C2 | 110.8 MPa | <= 213 | 102 | **PASS (unverified)** | [point.json](points/p01_mesh_size_mm-5/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| equilibrium | |R_fixed - (0, 0, F)| / F (sum of reactions) | 4.20e-12 | 1e-06 | PASS |
| tip_deflection_reference | |tip deflection FE - Timoshenko| / Timoshenko | 1.78e-01 | 2e-02 | FAIL |
| root_stress_reference | |extrapolated root stress FE - 6FL/(bh^2)| / beam theory | 2.61e-01 | 2e-02 | FAIL |
| linear_material (validity) | root bending stress / yield strength (linear elastic only below 1) | 3.12e-01 | 1e+00 | PASS |
| small_deflection (validity) | tip deflection / length (geometrically linear analysis) | 3.94e-03 | 1e-02 | PASS |

![p01_mesh_size_mm-5 response](points/p01_mesh_size_mm-5/response.png)

### p02_mesh_size_mm-3.125

Parameters: length_mm = 200, width_mm = 20, height_mm = 20, youngs_modulus_MPa = 2.1e+05, poisson_ratio = 0.3, yield_strength_MPa = 355, tip_load_N = 1000, mesh_size_mm = 3.125, element_order = 1st

Derived: slenderness_L_over_h = 10, tip_deflection_euler_bernoulli_mm = 0.9524, tip_deflection_timoshenko_mm = 0.9597, root_bending_stress_beam_theory_MPa = 150

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-C1 | 0.8825 mm | <= 1 | 0.118 | **PASS (unverified)** | [point.json](points/p02_mesh_size_mm-3.125/point.json) |
| REQ-C2 | 129.8 MPa | <= 213 | 83.2 | **PASS (unverified)** | [point.json](points/p02_mesh_size_mm-3.125/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| equilibrium | |R_fixed - (0, 0, F)| / F (sum of reactions) | 3.15e-12 | 1e-06 | PASS |
| tip_deflection_reference | |tip deflection FE - Timoshenko| / Timoshenko | 8.05e-02 | 2e-02 | FAIL |
| root_stress_reference | |extrapolated root stress FE - 6FL/(bh^2)| / beam theory | 1.35e-01 | 2e-02 | FAIL |
| linear_material (validity) | root bending stress / yield strength (linear elastic only below 1) | 3.66e-01 | 1e+00 | PASS |
| small_deflection (validity) | tip deflection / length (geometrically linear analysis) | 4.41e-03 | 1e-02 | PASS |

![p02_mesh_size_mm-3.125 response](points/p02_mesh_size_mm-3.125/response.png)

### p03_mesh_size_mm-1.95312

Parameters: length_mm = 200, width_mm = 20, height_mm = 20, youngs_modulus_MPa = 2.1e+05, poisson_ratio = 0.3, yield_strength_MPa = 355, tip_load_N = 1000, mesh_size_mm = 1.953, element_order = 1st

Derived: slenderness_L_over_h = 10, tip_deflection_euler_bernoulli_mm = 0.9524, tip_deflection_timoshenko_mm = 0.9597, root_bending_stress_beam_theory_MPa = 150

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-C1 | 0.9236 mm | <= 1 | 0.0764 | **PASS (unverified)** | [point.json](points/p03_mesh_size_mm-1.95312/point.json) |
| REQ-C2 | 139.5 MPa | <= 213 | 73.5 | **PASS (unverified)** | [point.json](points/p03_mesh_size_mm-1.95312/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| equilibrium | |R_fixed - (0, 0, F)| / F (sum of reactions) | 3.62e-12 | 1e-06 | PASS |
| tip_deflection_reference | |tip deflection FE - Timoshenko| / Timoshenko | 3.76e-02 | 2e-02 | FAIL |
| root_stress_reference | |extrapolated root stress FE - 6FL/(bh^2)| / beam theory | 6.97e-02 | 2e-02 | FAIL |
| linear_material (validity) | root bending stress / yield strength (linear elastic only below 1) | 3.93e-01 | 1e+00 | PASS |
| small_deflection (validity) | tip deflection / length (geometrically linear analysis) | 4.62e-03 | 1e-02 | PASS |

![p03_mesh_size_mm-1.95312 response](points/p03_mesh_size_mm-1.95312/response.png)

## Limitations

- Synthetic geometry and load; not a specific part.
- Beam theory is an approximate reference for a 3D clamped solid (L/h = 10): agreement within ~1 % is expected, not exact.
- The max von Mises value is reported for information only; it sits at a singular clamp corner and is mesh-dependent.
- No physical test data.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

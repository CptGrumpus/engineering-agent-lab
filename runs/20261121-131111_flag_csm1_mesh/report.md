# Engineering review report: flag_csm1_mesh

- **Run:** `20261121-131111_flag_csm1_mesh`
- **Generated:** 2026-11-21T18:11:28+00:00
- **Case file SHA-256:** `a4743a75841218f47cd5d7e06a996ef2497ffdd82d5ca41f475de1683bb82758`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Tools:** CalculiX This is Version 2.22
- **Code version:** git `fea8e67765680000672273b44ac416863a8bbcdd` (uncommitted changes present)
- **Simulation status:** completed
- **Verification status:** PASS

## Scope

Turek-Hron CSM1: the elastic flag alone (plane strain, St. Venant-Kirchhoff, mu_s 0.5 MPa, nu 0.4, rho 1000 kg/m3) clamped on the cylinder and bent by gravity (2 m/s2); CalculiX NLGEOM static, C3D8I elements of 5 / 2.5 / 1.25 mm; checked against the benchmark, a large-deflection elastica and beam vibration theory.

**Assumptions**

- Plane strain, per unit depth: the benchmark is 2D, and the elastica only matches it with the plane-strain modulus E / (1 - nu^2) (plane stress would give a 17 % larger drop).
- St. Venant-Kirchhoff material (CalculiX *ELASTIC under NLGEOM), as the benchmark defines it.
- The cylinder is rigid: the flag's left end, on the cylinder arc, is fully clamped.
- Gravity is a dead load applied in equal increments; the static solution is path independent (elastic).

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-S1 | Before it is coupled to the fluid, the solid model shall reproduce the Turek-Hron CSM1 vertical displacement of point A within 1 %. | `uy_A_deviation_pct` | <= 1 % |
| REQ-S2 | It shall reproduce the CSM1 horizontal displacement of point A within 2 % (a second-order quantity, about a tenth of the vertical one). | `ux_A_deviation_pct` | <= 2 % |

## Summary across points

| Point | element_size_mm | REQ-S1 | REQ-S2 | Checks |
|---|---|---|---|---|
| p00_element_size_mm-5 | 5 | 0.1828 %: **PASS** | 0.3182 %: **PASS** | 8/8 PASS |
| p01_element_size_mm-2.5 | 2.5 | 0.07966 %: **PASS** | 0.139 %: **PASS** | 8/8 PASS |
| p02_element_size_mm-1.25 | 1.25 | 0.03228 %: **PASS** | 0.05643 %: **PASS** | 8/8 PASS |

## Run-level checks

Checks that use several points together (for example mesh convergence).

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| discretization_ux_A_mm | relative discretization uncertainty of ux_A_mm, monotone (R = 0.461): GCI_fine, observed order 1.12, extrapolated -7.18869 | 0.000883 | 0.01 | PASS |
| discretization_uy_A_mm | relative discretization uncertainty of uy_A_mm, monotone (R = 0.459): GCI_fine, observed order 1.12, extrapolated -66.1076 | 0.000503 | 0.01 | PASS |
| discretization_first_frequency_Hz | relative discretization uncertainty of first_frequency_Hz, monotone (R = 0.441): GCI_fine, observed order 1.18, extrapolated 1.07176 | 0.000256 | 0.01 | PASS |

![Requirement metrics across the sweep](sweep.png)

## Point details

### p00_element_size_mm-5

Parameters: shear_modulus_Pa = 5e+05, density_kg_per_m3 = 1000, poisson_ratio = 0.4, gravity_m_per_s2 = 2, flag_length_m = 0.35, flag_height_m = 0.02, cylinder_radius_m = 0.05, element_size_mm = 5, benchmark_ux_A_mm = -7.188, benchmark_uy_A_mm = -66.1

Derived: youngs_modulus_Pa = 1.4e+06, load_parameter_qL3_over_EI = 1.543, linear_uy_A_mm = -67.53, elastica_ux_A_mm = -7.109, elastica_uy_A_mm = -65.62, beam_frequency_Hz = 1.077, height_over_length = 0.05714

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-S1 | 0.1828 % | <= 1 | 0.817 | **PASS** | [point.json](points/p00_element_size_mm-5/point.json) |
| REQ-S2 | 0.3182 % | <= 2 | 1.68 | **PASS** | [point.json](points/p00_element_size_mm-5/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| increments_complete | static step reached the full load (1 = not) | 0.00e+00 | 5e-01 | PASS |
| equilibrium | |clamp reaction - weight carried through the elements| / weight (the weight lumped on the clamp nodes is excluded from CalculiX's reaction total) | 2.39e-07 | 1e-06 | PASS |
| elastica_uy | |uy(A) - elastica| / |elastica| (model form: inextensible beam, root on a straight line) | 5.55e-03 | 2e-02 | PASS |
| elastica_ux | |ux(A) - elastica| / |elastica| (model form) | 7.87e-03 | 3e-02 | PASS |
| load_path | max over increments of |uy(A) - elastica at that load| / |elastica uy at full load| (model form) | 5.55e-03 | 2e-02 | PASS |
| deflected_shape | max |centreline y - elastica y| at the same x / |elastica uy(A)| (model form) | 5.77e-03 | 2e-02 | PASS |
| frequency_reference | |f1 FE - Euler-Bernoulli cantilever| / beam value (model form) | 3.54e-03 | 2e-02 | PASS |
| slender (validity) | height / length (beam references) | 5.71e-02 | 1e-01 | PASS |

![p00_element_size_mm-5 response](points/p00_element_size_mm-5/response.png)

### p01_element_size_mm-2.5

Parameters: shear_modulus_Pa = 5e+05, density_kg_per_m3 = 1000, poisson_ratio = 0.4, gravity_m_per_s2 = 2, flag_length_m = 0.35, flag_height_m = 0.02, cylinder_radius_m = 0.05, element_size_mm = 2.5, benchmark_ux_A_mm = -7.188, benchmark_uy_A_mm = -66.1

Derived: youngs_modulus_Pa = 1.4e+06, load_parameter_qL3_over_EI = 1.543, linear_uy_A_mm = -67.53, elastica_ux_A_mm = -7.109, elastica_uy_A_mm = -65.62, beam_frequency_Hz = 1.077, height_over_length = 0.05714

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-S1 | 0.07966 % | <= 1 | 0.92 | **PASS** | [point.json](points/p01_element_size_mm-2.5/point.json) |
| REQ-S2 | 0.139 % | <= 2 | 1.86 | **PASS** | [point.json](points/p01_element_size_mm-2.5/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| increments_complete | static step reached the full load (1 = not) | 0.00e+00 | 5e-01 | PASS |
| equilibrium | |clamp reaction - weight carried through the elements| / weight (the weight lumped on the clamp nodes is excluded from CalculiX's reaction total) | 1.94e-08 | 1e-06 | PASS |
| elastica_uy | |uy(A) - elastica| / |elastica| (model form: inextensible beam, root on a straight line) | 6.59e-03 | 2e-02 | PASS |
| elastica_ux | |ux(A) - elastica| / |elastica| (model form) | 9.68e-03 | 3e-02 | PASS |
| load_path | max over increments of |uy(A) - elastica at that load| / |elastica uy at full load| (model form) | 6.59e-03 | 2e-02 | PASS |
| deflected_shape | max |centreline y - elastica y| at the same x / |elastica uy(A)| (model form) | 6.86e-03 | 2e-02 | PASS |
| frequency_reference | |f1 FE - Euler-Bernoulli cantilever| / beam value (model form) | 4.13e-03 | 2e-02 | PASS |
| slender (validity) | height / length (beam references) | 5.71e-02 | 1e-01 | PASS |

![p01_element_size_mm-2.5 response](points/p01_element_size_mm-2.5/response.png)

### p02_element_size_mm-1.25

Parameters: shear_modulus_Pa = 5e+05, density_kg_per_m3 = 1000, poisson_ratio = 0.4, gravity_m_per_s2 = 2, flag_length_m = 0.35, flag_height_m = 0.02, cylinder_radius_m = 0.05, element_size_mm = 1.25, benchmark_ux_A_mm = -7.188, benchmark_uy_A_mm = -66.1

Derived: youngs_modulus_Pa = 1.4e+06, load_parameter_qL3_over_EI = 1.543, linear_uy_A_mm = -67.53, elastica_ux_A_mm = -7.109, elastica_uy_A_mm = -65.62, beam_frequency_Hz = 1.077, height_over_length = 0.05714

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-S1 | 0.03228 % | <= 1 | 0.968 | **PASS** | [point.json](points/p02_element_size_mm-1.25/point.json) |
| REQ-S2 | 0.05643 % | <= 2 | 1.94 | **PASS** | [point.json](points/p02_element_size_mm-1.25/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| increments_complete | static step reached the full load (1 = not) | 0.00e+00 | 5e-01 | PASS |
| equilibrium | |clamp reaction - weight carried through the elements| / weight (the weight lumped on the clamp nodes is excluded from CalculiX's reaction total) | 2.38e-07 | 1e-06 | PASS |
| elastica_uy | |uy(A) - elastica| / |elastica| (model form: inextensible beam, root on a straight line) | 7.06e-03 | 2e-02 | PASS |
| elastica_ux | |ux(A) - elastica| / |elastica| (model form) | 1.05e-02 | 3e-02 | PASS |
| load_path | max over increments of |uy(A) - elastica at that load| / |elastica uy at full load| (model form) | 7.06e-03 | 2e-02 | PASS |
| deflected_shape | max |centreline y - elastica y| at the same x / |elastica uy(A)| (model form) | 7.36e-03 | 2e-02 | PASS |
| frequency_reference | |f1 FE - Euler-Bernoulli cantilever| / beam value (model form) | 4.39e-03 | 2e-02 | PASS |
| slender (validity) | height / length (beam references) | 5.71e-02 | 1e-01 | PASS |

![p02_element_size_mm-1.25 response](points/p02_element_size_mm-1.25/response.png)

## Limitations

- A solver-qualification case: it shows that the solid participant reproduces the published solid-only results, not that the coupled FSI result is right.
- The elastica is a beam model (no shear, straight root, inextensible), so it bounds the FE to about 1 %, not to the benchmark's digits.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

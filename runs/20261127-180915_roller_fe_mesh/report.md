# Engineering review report: roller_fe_mesh

- **Run:** `20261127-180915_roller_fe_mesh`
- **Generated:** 2026-11-28T13:45:09+00:00
- **Case file SHA-256:** `5126f72f9928278b2364d3fe9215e216fce4e1f04a32b2cfee625531c97396b5`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Tools:** gmsh 4.15.0; CalculiX This is Version 2.22
- **Code version:** git `4651b3ee07fabacfc0961754ac5b28c360caed9b` (uncommitted changes present)
- **Simulation status:** completed
- **Verification status:** FAIL

> **Warning:** verification did not pass for every point. Requirement verdicts marked *(unverified)* are not supported by evidence and must not be used for acceptance.

## Scope

Study 10's track roller (100 mm diameter, 30 mm long [synthetic], 500 N/mm) with the chosen logarithmic crown (A = 1.793 um, z_m 30 um) on a 60 mm plate, 3D CalculiX penalty contact; contact elements 0.08 / 0.06 / 0.045 mm; four approach steps bracketing the load.

**Assumptions**

- Linear elastic steel (E 210 GPa, nu 0.3), frictionless penalty contact as study 10 (50 E / h).
- Quarter model: symmetric about the plane through the roller's axis and about its mid-length; the plate 60 mm wide, 50 mm deep, 120 mm long (study 10's section).
- The crown applied as a micron drop of the roller's nodes (each slice shifted), capped at 60 um.
- The results interpolated linearly in load between the two steps that bracket 500 N/mm.

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-C1-3D | The peak contact pressure anywhere along the crowned roller shall not exceed 650 MPa (study 10's REQ on the peak pressure), on the 3D finite-element model. | `peak_contact_pressure_MPa` | <= 650 MPa |

## Summary across points

| Point | contact_element_size_mm | REQ-C1-3D | Checks |
|---|---|---|---|
| p00_contact_element_size_mm-0.08 | 0.08 | 647.1 MPa: **PASS (unverified)** | 3/5 FAIL |
| p01_contact_element_size_mm-0.06 | 0.06 | 724.1 MPa: **FAIL (unverified)** | 4/5 FAIL |
| p02_contact_element_size_mm-0.045 | 0.045 | 715.7 MPa: **FAIL (unverified)** | 4/5 FAIL |

## Run-level checks

Checks that use several points together (for example mesh convergence).

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| discretization_peak_contact_pressure_MPa | relative discretization uncertainty of peak_contact_pressure_MPa, oscillatory (R = -0.109): 1.25 x half-range of the 3 finest solutions | 0.0673 | 0.03 | FAIL |

A failed run-level check withholds the verdicts of requirements on `peak_contact_pressure_MPa` at every point: they are marked *(unverified)* in the table above.

![Requirement metrics across the sweep](sweep.png)

## Point details

### p00_contact_element_size_mm-0.08

Parameters: roller_radius_mm = 50, roller_length_mm = 30, plate_width_mm = 60, block_half_width_mm = 60, block_depth_mm = 50, youngs_modulus_MPa = 2.1e+05, poisson_ratio = 0.3, yield_strength_MPa = 1200, contact_element_size_mm = 0.08, far_element_size_mm = 4, refined_zone_mm = 1.6, end_layer_mm = 0.2, layer_growth = 1.3, max_layer_mm = 1, penalty_stiffness_factor = 50, line_load_N_per_mm = 500, profile = log, crown_A_um = 1.793, crown_zm_um = 30, cap_um = 60, approach_mm = 0.0155, approach_factors = [0.92, 0.97, 1.02, 1.07]

Derived: hertz_long_roller = {'E_star_MPa': 115384.61538461539, 'half_width_mm': 0.5252319183236601, 'peak_pressure_MPa': 606.0368288349923, 'max_shear_MPa': 181.98262131343319, 'max_shear_depth_mm': 0.4129117977874304}, lundberg_A_um = 1.379, total_load_N = 1.5e+04

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-C1-3D | 647.1 MPa | <= 650 | 2.91 | **PASS (unverified)** | [point.json](points/p00_contact_element_size_mm-0.08/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| load_bracketed (validity) | the target load lies between two completed steps (0 = yes) | 0.00e+00 | 0 | PASS |
| equilibrium | max over the steps of \|roller reaction + plate reaction\| / roller reaction | 0.00e+00 | 1e-05 | PASS |
| contact_integral | \|contact pressure integrated over the patch / roller reaction - 1\| at the target load (the nodal pressures' smearing of the contact edge) | 1.08e-01 | 0.03 | FAIL |
| hertz_mid_pressure | \|peak pressure at mid-length - Hertz p0 for the local line load there\| / p0 (long-roller limit) | 3.20e-02 | 0.03 | FAIL |
| elastic (validity) | max subsurface shear / shear yield (Tresca, yield / 2) | 3.23e-01 | 1 | PASS |

![p00_contact_element_size_mm-0.08 response](points/p00_contact_element_size_mm-0.08/response.png)

### p01_contact_element_size_mm-0.06

Parameters: roller_radius_mm = 50, roller_length_mm = 30, plate_width_mm = 60, block_half_width_mm = 60, block_depth_mm = 50, youngs_modulus_MPa = 2.1e+05, poisson_ratio = 0.3, yield_strength_MPa = 1200, contact_element_size_mm = 0.06, far_element_size_mm = 4, refined_zone_mm = 1.6, end_layer_mm = 0.2, layer_growth = 1.3, max_layer_mm = 1, penalty_stiffness_factor = 50, line_load_N_per_mm = 500, profile = log, crown_A_um = 1.793, crown_zm_um = 30, cap_um = 60, approach_mm = 0.0155, approach_factors = [0.92, 0.97, 1.02, 1.07]

Derived: hertz_long_roller = {'E_star_MPa': 115384.61538461539, 'half_width_mm': 0.5252319183236601, 'peak_pressure_MPa': 606.0368288349923, 'max_shear_MPa': 181.98262131343319, 'max_shear_depth_mm': 0.4129117977874304}, lundberg_A_um = 1.379, total_load_N = 1.5e+04

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-C1-3D | 724.1 MPa | <= 650 | -74.1 | **FAIL (unverified)** | [point.json](points/p01_contact_element_size_mm-0.06/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| load_bracketed (validity) | the target load lies between two completed steps (0 = yes) | 0.00e+00 | 0 | PASS |
| equilibrium | max over the steps of \|roller reaction + plate reaction\| / roller reaction | 0.00e+00 | 1e-05 | PASS |
| contact_integral | \|contact pressure integrated over the patch / roller reaction - 1\| at the target load (the nodal pressures' smearing of the contact edge) | 1.12e-01 | 0.03 | FAIL |
| hertz_mid_pressure | \|peak pressure at mid-length - Hertz p0 for the local line load there\| / p0 (long-roller limit) | 3.30e-04 | 0.03 | PASS |
| elastic (validity) | max subsurface shear / shear yield (Tresca, yield / 2) | 3.23e-01 | 1 | PASS |

![p01_contact_element_size_mm-0.06 response](points/p01_contact_element_size_mm-0.06/response.png)

### p02_contact_element_size_mm-0.045

Parameters: roller_radius_mm = 50, roller_length_mm = 30, plate_width_mm = 60, block_half_width_mm = 60, block_depth_mm = 50, youngs_modulus_MPa = 2.1e+05, poisson_ratio = 0.3, yield_strength_MPa = 1200, contact_element_size_mm = 0.045, far_element_size_mm = 4, refined_zone_mm = 1.6, end_layer_mm = 0.2, layer_growth = 1.3, max_layer_mm = 1, penalty_stiffness_factor = 50, line_load_N_per_mm = 500, profile = log, crown_A_um = 1.793, crown_zm_um = 30, cap_um = 60, approach_mm = 0.0155, approach_factors = [0.92, 0.97, 1.02, 1.07]

Derived: hertz_long_roller = {'E_star_MPa': 115384.61538461539, 'half_width_mm': 0.5252319183236601, 'peak_pressure_MPa': 606.0368288349923, 'max_shear_MPa': 181.98262131343319, 'max_shear_depth_mm': 0.4129117977874304}, lundberg_A_um = 1.379, total_load_N = 1.5e+04

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-C1-3D | 715.7 MPa | <= 650 | -65.7 | **FAIL (unverified)** | [point.json](points/p02_contact_element_size_mm-0.045/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| load_bracketed (validity) | the target load lies between two completed steps (0 = yes) | 0.00e+00 | 0 | PASS |
| equilibrium | max over the steps of \|roller reaction + plate reaction\| / roller reaction | 0.00e+00 | 1e-05 | PASS |
| contact_integral | \|contact pressure integrated over the patch / roller reaction - 1\| at the target load (the nodal pressures' smearing of the contact edge) | 5.92e-02 | 0.03 | FAIL |
| hertz_mid_pressure | \|peak pressure at mid-length - Hertz p0 for the local line load there\| / p0 (long-roller limit) | 2.03e-02 | 0.03 | PASS |
| elastic (validity) | max subsurface shear / shear yield (Tresca, yield / 2) | 3.23e-01 | 1 | PASS |

![p02_contact_element_size_mm-0.045 response](points/p02_contact_element_size_mm-0.045/response.png)

## Limitations

- Layers along the roller are not refined with the contact mesh (end 0.2 mm, at most 1.0 mm): the mid-length value is what this case measures; the end region is resolved by the end layers only.
- No misalignment; contact pressure and the shear below it only.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

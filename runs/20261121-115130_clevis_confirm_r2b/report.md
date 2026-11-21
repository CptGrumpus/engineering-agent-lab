# Engineering review report: clevis_confirm_r2b

- **Run:** `20261121-115130_clevis_confirm_r2b`
- **Generated:** 2026-11-21T17:22:38+00:00
- **Case file SHA-256:** `1ebb4e58c91cd43592734469eca6287e29d895d1e936fbb48eb95213aa227efa`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Tools:** cadquery 2.8.0; gmsh 4.15.0; CalculiX This is Version 2.22
- **Code version:** git `6e284df9a6dafeff85f0f748867344118bca9ad0` (uncommitted changes present)
- **Simulation status:** completed
- **Verification status:** PASS

## Scope

Confirmation of design D, chosen by a local linear response surface over the converged candidates of run 20261121-091836_clevis_opt_r2: 4 mm quadratic tetrahedra globally, fillet element size 1.0 / 0.85 / 0.75 mm. Original problem: lightest 6061-T6 machined clevis bracket (base 100 x 100 x 10 mm, lug 40 mm wide with a 16 mm pin at 70 mm, two gussets, 3 mm fillets) under a (1.5, 1.0, 4.5) kN pin load, with peak von Mises at most 100 MPa and pin deflection at most 0.10 mm.

**Assumptions**

- Base bottom face fixed (bolted and dowelled to a rigid machine frame); the bottom half of the base is not assessed (the edge of a fixed face is singular, and the real joint is not modelled).
- Pin load through a rigid pin tied to the hole surface; a ring of one pin diameter around the hole is not assessed (pin bearing and lug net section are sized by the standard lug method).
- Linear elastic 6061-T6 (E 68.9 GPa, nu 0.33); checked: peak stress below yield.
- Small deflection; checked: pin deflection / pin height below 1 %.
- Stress allowable 100 MPa (fatigue-rated) and pin deflection limit 0.10 mm: synthetic.

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-C1 | Peak von Mises stress (outside the fixed base layer and the pin ring) shall not exceed 100 MPa (fatigue-rated allowable). | `peak_von_mises_MPa` | <= 100 MPa |
| REQ-C2 | Pin deflection under the load shall not exceed 0.10 mm. | `pin_deflection_mm` | <= 0.1 mm |

## Summary across points

| Point | fillet_element_size_mm | REQ-C1 | REQ-C2 | Checks |
|---|---|---|---|---|
| p00_fillet_element_size_mm-1 | 1 | 97.36 MPa: **PASS** | 0.0794 mm: **PASS** | 6/6 PASS |
| p01_fillet_element_size_mm-0.85 | 0.85 | 97.54 MPa: **PASS** | 0.07941 mm: **PASS** | 6/6 PASS |
| p02_fillet_element_size_mm-0.75 | 0.75 | 98.33 MPa: **PASS** | 0.07942 mm: **PASS** | 6/6 PASS |

## Run-level checks

Checks that use several points together (for example mesh convergence).

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| discretization_peak_von_mises_MPa | relative discretization uncertainty of peak_von_mises_MPa, converged to within the noise floor (spread 9.9e-03 <= 0.015) | 0.0062 | 0.01 | PASS |
| requirement_margin_peak_von_mises_MPa | (finest peak_von_mises_MPa x (1 + uncertainty) - limit) / limit, must be <= 0 | -0.0106 | 0 | PASS |

![Requirement metrics across the sweep](sweep.png)

## Point details

### p00_fillet_element_size_mm-1

Parameters: base_length_mm = 100, base_width_mm = 100, base_thickness_mm = 10, lug_radius_mm = 20, pin_height_mm = 70, pin_diameter_mm = 16, lug_thickness_mm = 10.17, gusset_thickness_mm = 9.069, gusset_height_mm = 36.36, gusset_aspect = 0.7, fillet_radius_mm = 3, youngs_modulus_MPa = 6.89e+04, poisson_ratio = 0.33, density_t_per_mm3 = 2.7e-09, yield_strength_MPa = 276, load_x_N = 1500, load_y_N = 1000, load_z_N = 4500, element_size_mm = 4, fillet_element_size_mm = 1

Derived: gusset_reach_mm = 33.54, load_magnitude_N = 4848

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-C1 | 97.36 MPa | <= 100 | 2.64 | **PASS** | [point.json](points/p00_fillet_element_size_mm-1/point.json) |
| REQ-C2 | 0.0794 mm | <= 0.1 | 0.0206 | **PASS** | [point.json](points/p00_fillet_element_size_mm-1/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| cad_valid | CadQuery B-rep is a valid solid (1 = no) | 0.00e+00 | 5e-01 | PASS |
| mesh_volume | |meshed volume (straight-sided tets) - CAD volume| / CAD volume | 1.61e-04 | 2e-03 | PASS |
| force_balance | |sum of base reactions + pin load| / |pin load| | 4.48e-09 | 1e-06 | PASS |
| moment_balance | |moment of the base reactions + moment of the pin load| about the origin / (|F| x pin height) (the load acts where intended) | 2.25e-08 | 1e-06 | PASS |
| linear_material (validity) | peak von Mises / yield strength | 3.53e-01 | 1e+00 | PASS |
| small_deflection (validity) | pin deflection / pin height | 1.13e-03 | 1e-02 | PASS |

![p00_fillet_element_size_mm-1 response](points/p00_fillet_element_size_mm-1/response.png)

### p01_fillet_element_size_mm-0.85

Parameters: base_length_mm = 100, base_width_mm = 100, base_thickness_mm = 10, lug_radius_mm = 20, pin_height_mm = 70, pin_diameter_mm = 16, lug_thickness_mm = 10.17, gusset_thickness_mm = 9.069, gusset_height_mm = 36.36, gusset_aspect = 0.7, fillet_radius_mm = 3, youngs_modulus_MPa = 6.89e+04, poisson_ratio = 0.33, density_t_per_mm3 = 2.7e-09, yield_strength_MPa = 276, load_x_N = 1500, load_y_N = 1000, load_z_N = 4500, element_size_mm = 4, fillet_element_size_mm = 0.85

Derived: gusset_reach_mm = 33.54, load_magnitude_N = 4848

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-C1 | 97.54 MPa | <= 100 | 2.46 | **PASS** | [point.json](points/p01_fillet_element_size_mm-0.85/point.json) |
| REQ-C2 | 0.07941 mm | <= 0.1 | 0.0206 | **PASS** | [point.json](points/p01_fillet_element_size_mm-0.85/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| cad_valid | CadQuery B-rep is a valid solid (1 = no) | 0.00e+00 | 5e-01 | PASS |
| mesh_volume | |meshed volume (straight-sided tets) - CAD volume| / CAD volume | 5.98e-05 | 2e-03 | PASS |
| force_balance | |sum of base reactions + pin load| / |pin load| | 1.55e-09 | 1e-06 | PASS |
| moment_balance | |moment of the base reactions + moment of the pin load| about the origin / (|F| x pin height) (the load acts where intended) | 3.16e-08 | 1e-06 | PASS |
| linear_material (validity) | peak von Mises / yield strength | 3.53e-01 | 1e+00 | PASS |
| small_deflection (validity) | pin deflection / pin height | 1.13e-03 | 1e-02 | PASS |

![p01_fillet_element_size_mm-0.85 response](points/p01_fillet_element_size_mm-0.85/response.png)

### p02_fillet_element_size_mm-0.75

Parameters: base_length_mm = 100, base_width_mm = 100, base_thickness_mm = 10, lug_radius_mm = 20, pin_height_mm = 70, pin_diameter_mm = 16, lug_thickness_mm = 10.17, gusset_thickness_mm = 9.069, gusset_height_mm = 36.36, gusset_aspect = 0.7, fillet_radius_mm = 3, youngs_modulus_MPa = 6.89e+04, poisson_ratio = 0.33, density_t_per_mm3 = 2.7e-09, yield_strength_MPa = 276, load_x_N = 1500, load_y_N = 1000, load_z_N = 4500, element_size_mm = 4, fillet_element_size_mm = 0.75

Derived: gusset_reach_mm = 33.54, load_magnitude_N = 4848

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-C1 | 98.33 MPa | <= 100 | 1.67 | **PASS** | [point.json](points/p02_fillet_element_size_mm-0.75/point.json) |
| REQ-C2 | 0.07942 mm | <= 0.1 | 0.0206 | **PASS** | [point.json](points/p02_fillet_element_size_mm-0.75/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| cad_valid | CadQuery B-rep is a valid solid (1 = no) | 0.00e+00 | 5e-01 | PASS |
| mesh_volume | |meshed volume (straight-sided tets) - CAD volume| / CAD volume | 7.23e-06 | 2e-03 | PASS |
| force_balance | |sum of base reactions + pin load| / |pin load| | 7.59e-09 | 1e-06 | PASS |
| moment_balance | |moment of the base reactions + moment of the pin load| about the origin / (|F| x pin height) (the load acts where intended) | 2.36e-08 | 1e-06 | PASS |
| linear_material (validity) | peak von Mises / yield strength | 3.56e-01 | 1e+00 | PASS |
| small_deflection (validity) | pin deflection / pin height | 1.13e-03 | 1e-02 | PASS |

![p02_fillet_element_size_mm-0.75 response](points/p02_fillet_element_size_mm-0.75/response.png)

## Limitations

- Static load only; the fatigue rating is folded into the allowable.
- No closed-form reference for the whole part: the evidence is exact equilibrium, geometry fidelity, a model-form check of the lug section and this mesh study.
- Fixed outline and fillet radius; only three dimensions vary.
- No physical test data.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

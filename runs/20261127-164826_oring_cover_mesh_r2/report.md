# Engineering review report: oring_cover_mesh_r2

- **Run:** `20261127-164826_oring_cover_mesh_r2`
- **Generated:** 2026-11-27T21:55:56+00:00
- **Case file SHA-256:** `c99795a3fd307782fdd05d0711634d15ae61ab03d0dc3d648995805589c384c6`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Tools:** cadquery 2.8.0; gmsh 4.15.0; CalculiX This is Version 2.22
- **Code version:** git `49b4a9e2529287f6ded359c91a931aa361a3edac` (uncommitted changes present)
- **Simulation status:** completed
- **Verification status:** PASS

## Scope

Study 25's pump cover (synthetic: 6061-T6, 96 mm across, 4 mm thick, 4 x M6 on a 76 mm circle) lifted by 3 bar and the O-ring's reaction at the loosest corner; element size 2.0 / 1.333 / 0.889 / 0.593 mm, curvature sizing off.

**Assumptions**

- The cover [synthetic, part 1 never drew it]: 6061-T6 aluminium, 96 mm across, held by 4 M6 bolts on a 76 mm circle with 12 mm washers; the groove is in the pump, the cover's underside flat.
- Loads: 3 bar out to the groove's outer radius (conservative) and the O-ring's reaction from part 1 at the loosest corner, 1.887 N/mm over its 1.68 mm contact; both push the cover up.
- The washer footprints held against lifting only (free to slide and pivot: the softer support); the pump flange rigid; the rim beyond the bolts unsupported (a real flange pushes back on it, which lowers the lift).
- The O-ring's reaction held at its part 1 value as the cover lifts (it falls as the squeeze falls: conservative).
- Linear elastic, small displacement.

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-E1L | With the cover's lift between the bolts, the squeeze at the loosest corner of the stack stays at or above 15 % (REQ-E1 of part 1, at the worst point around the seal). | `loosest_squeeze_with_lift_pct` | >= 15 % |

## Summary across points

| Point | element_size_mm | REQ-E1L | Checks |
|---|---|---|---|
| p00_element_size_mm-2 | 2 | 16.78 %: **PASS** | 4/4 PASS |
| p01_element_size_mm-1.333 | 1.333 | 16.78 %: **PASS** | 4/4 PASS |
| p02_element_size_mm-0.889 | 0.889 | 16.77 %: **PASS** | 4/4 PASS |
| p03_element_size_mm-0.593 | 0.593 | 16.77 %: **PASS** | 4/4 PASS |

## Run-level checks

Checks that use several points together (for example mesh convergence).

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| discretization_loosest_squeeze_with_lift_pct | relative discretization uncertainty of loosest_squeeze_with_lift_pct, converged to within the noise floor (spread 5.6e-04 <= 0.001) | 0.000352 | 0.03 | PASS |
| discretization_max_seal_lift_um | relative discretization uncertainty of max_seal_lift_um, monotone (R = 0.551): GCI_fine, observed order 1.47, extrapolated 15.0627 | 0.0119 | 0.03 | PASS |

![Requirement metrics across the sweep](sweep.png)

## Point details

### p00_element_size_mm-2

Parameters: cover_diameter_mm = 96, cover_thickness_mm = 4, bolt_count = 4, bolt_circle_diameter_mm = 76, bolt_hole_diameter_mm = 6.6, washer_diameter_mm = 12, pressure_MPa = 0.3, pressure_radius_mm = 28.53, oring_line_load_N_per_mm = 1.887, oring_radius_mm = 26.8, oring_contact_width_mm = 1.68, youngs_modulus_MPa = 6.89e+04, poisson_ratio = 0.33, element_size_mm = 2, support = bolts, curvature_elements_per_circle = 0, loosest_cross_section_mm = 3.43, loosest_groove_depth_mm = 2.84

Derived: loosest_squeeze_flat_pct = 17.2, allowed_lift_for_15pct_mm = 0.0755, mindlin_centre_deflection_mm = 0.2438

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-E1L | 16.78 % | >= 15 | 1.78 | **PASS** | [point.json](points/p00_element_size_mm-2/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| cad_valid | CadQuery B-rep valid, one solid (0 = yes) | 0.00e+00 | 0 | PASS |
| equilibrium | \|reaction at the washer footprints + applied load\| / applied load (the footprints carry no load, so RF is the reaction) | 8.49e-09 | 1e-06 | PASS |
| seal_line_inside_mesh (validity) | max barycentric violation of the points sampled on the seal circle (0 = inside an element; the underside is flat) | 3.85e-13 | 1e-06 | PASS |
| lifts_everywhere (validity) | the cover lifts (does not press down) all along the seal line (min lift / max lift >= 0; 0 = yes) | 0.00e+00 | 0 | PASS |

![p00_element_size_mm-2 response](points/p00_element_size_mm-2/response.png)

### p01_element_size_mm-1.333

Parameters: cover_diameter_mm = 96, cover_thickness_mm = 4, bolt_count = 4, bolt_circle_diameter_mm = 76, bolt_hole_diameter_mm = 6.6, washer_diameter_mm = 12, pressure_MPa = 0.3, pressure_radius_mm = 28.53, oring_line_load_N_per_mm = 1.887, oring_radius_mm = 26.8, oring_contact_width_mm = 1.68, youngs_modulus_MPa = 6.89e+04, poisson_ratio = 0.33, element_size_mm = 1.333, support = bolts, curvature_elements_per_circle = 0, loosest_cross_section_mm = 3.43, loosest_groove_depth_mm = 2.84

Derived: loosest_squeeze_flat_pct = 17.2, allowed_lift_for_15pct_mm = 0.0755, mindlin_centre_deflection_mm = 0.2438

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-E1L | 16.78 % | >= 15 | 1.78 | **PASS** | [point.json](points/p01_element_size_mm-1.333/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| cad_valid | CadQuery B-rep valid, one solid (0 = yes) | 0.00e+00 | 0 | PASS |
| equilibrium | \|reaction at the washer footprints + applied load\| / applied load (the footprints carry no load, so RF is the reaction) | 8.49e-09 | 1e-06 | PASS |
| seal_line_inside_mesh (validity) | max barycentric violation of the points sampled on the seal circle (0 = inside an element; the underside is flat) | 1.15e-15 | 1e-06 | PASS |
| lifts_everywhere (validity) | the cover lifts (does not press down) all along the seal line (min lift / max lift >= 0; 0 = yes) | 0.00e+00 | 0 | PASS |

![p01_element_size_mm-1.333 response](points/p01_element_size_mm-1.333/response.png)

### p02_element_size_mm-0.889

Parameters: cover_diameter_mm = 96, cover_thickness_mm = 4, bolt_count = 4, bolt_circle_diameter_mm = 76, bolt_hole_diameter_mm = 6.6, washer_diameter_mm = 12, pressure_MPa = 0.3, pressure_radius_mm = 28.53, oring_line_load_N_per_mm = 1.887, oring_radius_mm = 26.8, oring_contact_width_mm = 1.68, youngs_modulus_MPa = 6.89e+04, poisson_ratio = 0.33, element_size_mm = 0.889, support = bolts, curvature_elements_per_circle = 0, loosest_cross_section_mm = 3.43, loosest_groove_depth_mm = 2.84

Derived: loosest_squeeze_flat_pct = 17.2, allowed_lift_for_15pct_mm = 0.0755, mindlin_centre_deflection_mm = 0.2438

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-E1L | 16.77 % | >= 15 | 1.77 | **PASS** | [point.json](points/p02_element_size_mm-0.889/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| cad_valid | CadQuery B-rep valid, one solid (0 = yes) | 0.00e+00 | 0 | PASS |
| equilibrium | \|reaction at the washer footprints + applied load\| / applied load (the footprints carry no load, so RF is the reaction) | 8.49e-09 | 1e-06 | PASS |
| seal_line_inside_mesh (validity) | max barycentric violation of the points sampled on the seal circle (0 = inside an element; the underside is flat) | 7.63e-16 | 1e-06 | PASS |
| lifts_everywhere (validity) | the cover lifts (does not press down) all along the seal line (min lift / max lift >= 0; 0 = yes) | 0.00e+00 | 0 | PASS |

![p02_element_size_mm-0.889 response](points/p02_element_size_mm-0.889/response.png)

### p03_element_size_mm-0.593

Parameters: cover_diameter_mm = 96, cover_thickness_mm = 4, bolt_count = 4, bolt_circle_diameter_mm = 76, bolt_hole_diameter_mm = 6.6, washer_diameter_mm = 12, pressure_MPa = 0.3, pressure_radius_mm = 28.53, oring_line_load_N_per_mm = 1.887, oring_radius_mm = 26.8, oring_contact_width_mm = 1.68, youngs_modulus_MPa = 6.89e+04, poisson_ratio = 0.33, element_size_mm = 0.593, support = bolts, curvature_elements_per_circle = 0, loosest_cross_section_mm = 3.43, loosest_groove_depth_mm = 2.84

Derived: loosest_squeeze_flat_pct = 17.2, allowed_lift_for_15pct_mm = 0.0755, mindlin_centre_deflection_mm = 0.2438

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-E1L | 16.77 % | >= 15 | 1.77 | **PASS** | [point.json](points/p03_element_size_mm-0.593/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| cad_valid | CadQuery B-rep valid, one solid (0 = yes) | 0.00e+00 | 0 | PASS |
| equilibrium | \|reaction at the washer footprints + applied load\| / applied load (the footprints carry no load, so RF is the reaction) | 8.49e-09 | 1e-06 | PASS |
| seal_line_inside_mesh (validity) | max barycentric violation of the points sampled on the seal circle (0 = inside an element; the underside is flat) | 0.00e+00 | 1e-06 | PASS |
| lifts_everywhere (validity) | the cover lifts (does not press down) all along the seal line (min lift / max lift >= 0; 0 = yes) | 0.00e+00 | 0 | PASS |

![p03_element_size_mm-0.593 response](points/p03_element_size_mm-0.593/response.png)

## Limitations

- No bolt stretch or flange flexibility, no flatness tolerance on the machined faces (a flatness callout adds to the lift directly).
- The cover geometry is synthetic: the answer is the lift per thickness, read against the 75.5 um the loosest corner can give up.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

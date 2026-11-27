# Engineering review report: duct_section_mesh

- **Run:** `20261127-170402_duct_section_mesh`
- **Generated:** 2026-11-27T22:04:04+00:00
- **Case file SHA-256:** `a2f8617a28ebf6a31bfd811a8044ecade9aa5554ce4071862b56e30f81516048`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Tools:** scipy 1.18.1; numpy 2.5.5
- **Code version:** git `5d6aa1b53b70e1166ea3b379f24dcf696d4aa862` (uncommitted changes present)
- **Simulation status:** completed
- **Verification status:** FAIL

> **Warning:** verification did not pass for every point. Requirement verdicts marked *(unverified)* are not supported by evidence and must not be used for acceptance.

## Scope

Study 11's cold-plate passage (1 x 20 mm, water at 0.1 m/s, 30 kW/m2 on both broad walls) with its side walls, fully developed, the broad wall a 2 mm 6061-T6 sheet; 20 / 40 / 80 cells across the half gap.

**Assumptions**

- Fully developed flow and heat transfer in the cross-section; the 3D correction (peak excess over the bulk, 3D minus parallel plates) is added to study 11's verified 2D wall temperature, which includes the thermal entry (98 % developed at the outlet in 2D).
- The passage 1 x 20 mm [width synthetic], heated on both broad walls at 30 kW/m2 over its width; the side walls adiabatic (conservative: metal side walls carry heat away).
- The broad wall a conducting sheet of 6061-T6 (k 167 W/m K), its temperature uniform through its thickness; the heat applied uniformly over the passage's width.
- Water properties as study 11 (k 0.607 W/m K); laminar (Re 224).

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-T1-3D | With the side walls, the passage's wall stays at or under 45 C (study 11's REQ on the wall temperature, at its hottest point across the width): the 3D peak excess corrected onto study 11's verified 2D value. | `wall_peak_temperature_C` | <= 45 C |

## Summary across points

| Point | cells_across_half_gap | REQ-T1-3D | Checks |
|---|---|---|---|
| p00_cells_across_half_gap-20 | 20 | 44.24 C: **PASS (unverified)** | 3/4 FAIL |
| p01_cells_across_half_gap-40 | 40 | 44.25 C: **PASS** | 4/4 PASS |
| p02_cells_across_half_gap-80 | 80 | 44.25 C: **PASS** | 4/4 PASS |

## Run-level checks

Checks that use several points together (for example mesh convergence).

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| discretization_wall_peak_excess_K | relative discretization uncertainty of wall_peak_excess_K, monotone (R = 0.254): GCI_fine, observed order 1.97, extrapolated 12.2212 | 3.94e-05 | 0.01 | PASS |
| discretization_wall_peak_temperature_C | relative discretization uncertainty of wall_peak_temperature_C, monotone (R = 0.254): GCI_fine, observed order 1.97, extrapolated 44.2474 | 1.09e-05 | 0.01 | PASS |

![Requirement metrics across the sweep](sweep.png)

## Point details

### p00_cells_across_half_gap-20

Parameters: gap_mm = 1, width_mm = 20, cells_across_half_gap = 20, side_growth = 1.08, dz_max_over_dy = 8, bc = plate, plate_conductivity_W_per_mK = 167, plate_thickness_mm = 2, fluid_conductivity_W_per_mK = 0.607, wall_heat_flux_W_per_m2 = 3e+04, wall_temperature_2D_C = 44.03, wall_limit_C = 45

Derived: parallel_plate_excess_K = 12, plate_conductance_rel_mm = 550.2, study11_margin_K = 0.971

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-T1-3D | 44.24 C | <= 45 | 0.759 | **PASS (unverified)** | [point.json](points/p00_cells_across_half_gap-20/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| parallel_plate_limit | \|wall excess with the side wall replaced by symmetry - 17/70 q H / k\| / (17/70 q H / k) (exact) | 4.39e-04 | 0.001 | PASS |
| fRe_exact | \|Fanning fRe - the exact rectangular-duct series\| / exact | 1.31e-03 | 0.001 | FAIL |
| incropera_Nu_ar4 | \|Nu, four walls at one temperature, b/a = 4 - Incropera Table 8.1 (5.33)\| / 5.33 (printed to 3 figures) | 1.02e-03 | 0.0015 | PASS |
| incropera_Nu_ar8 | \|Nu, four walls at one temperature, b/a = 8 - Incropera Table 8.1 (6.49)\| / 6.49 (printed to 3 figures) | 6.81e-04 | 0.0015 | PASS |

![p00_cells_across_half_gap-20 response](points/p00_cells_across_half_gap-20/response.png)

### p01_cells_across_half_gap-40

Parameters: gap_mm = 1, width_mm = 20, cells_across_half_gap = 40, side_growth = 1.08, dz_max_over_dy = 8, bc = plate, plate_conductivity_W_per_mK = 167, plate_thickness_mm = 2, fluid_conductivity_W_per_mK = 0.607, wall_heat_flux_W_per_m2 = 3e+04, wall_temperature_2D_C = 44.03, wall_limit_C = 45

Derived: parallel_plate_excess_K = 12, plate_conductance_rel_mm = 550.2, study11_margin_K = 0.971

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-T1-3D | 44.25 C | <= 45 | 0.754 | **PASS** | [point.json](points/p01_cells_across_half_gap-40/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| parallel_plate_limit | \|wall excess with the side wall replaced by symmetry - 17/70 q H / k\| / (17/70 q H / k) (exact) | 1.10e-04 | 0.001 | PASS |
| fRe_exact | \|Fanning fRe - the exact rectangular-duct series\| / exact | 3.42e-04 | 0.001 | PASS |
| incropera_Nu_ar4 | \|Nu, four walls at one temperature, b/a = 4 - Incropera Table 8.1 (5.33)\| / 5.33 (printed to 3 figures) | 4.25e-04 | 0.0015 | PASS |
| incropera_Nu_ar8 | \|Nu, four walls at one temperature, b/a = 8 - Incropera Table 8.1 (6.49)\| / 6.49 (printed to 3 figures) | 2.27e-04 | 0.0015 | PASS |

![p01_cells_across_half_gap-40 response](points/p01_cells_across_half_gap-40/response.png)

### p02_cells_across_half_gap-80

Parameters: gap_mm = 1, width_mm = 20, cells_across_half_gap = 80, side_growth = 1.08, dz_max_over_dy = 8, bc = plate, plate_conductivity_W_per_mK = 167, plate_thickness_mm = 2, fluid_conductivity_W_per_mK = 0.607, wall_heat_flux_W_per_m2 = 3e+04, wall_temperature_2D_C = 44.03, wall_limit_C = 45

Derived: parallel_plate_excess_K = 12, plate_conductance_rel_mm = 550.2, study11_margin_K = 0.971

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-T1-3D | 44.25 C | <= 45 | 0.753 | **PASS** | [point.json](points/p02_cells_across_half_gap-80/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| parallel_plate_limit | \|wall excess with the side wall replaced by symmetry - 17/70 q H / k\| / (17/70 q H / k) (exact) | 2.76e-05 | 0.001 | PASS |
| fRe_exact | \|Fanning fRe - the exact rectangular-duct series\| / exact | 9.58e-05 | 0.001 | PASS |
| incropera_Nu_ar4 | \|Nu, four walls at one temperature, b/a = 4 - Incropera Table 8.1 (5.33)\| / 5.33 (printed to 3 figures) | 2.96e-04 | 0.0015 | PASS |
| incropera_Nu_ar8 | \|Nu, four walls at one temperature, b/a = 8 - Incropera Table 8.1 (6.49)\| / 6.49 (printed to 3 figures) | 1.19e-04 | 0.0015 | PASS |

![p02_cells_across_half_gap-80 response](points/p02_cells_across_half_gap-80/response.png)

## Limitations

- No axial development in 3D: the side-wall correction is the fully developed one.
- The plate's own temperature rise through its thickness (q t / k, 0.36 K for 2 mm) is not in the fluid-side wall temperature this requirement is about; a component on the plate sees it on top.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

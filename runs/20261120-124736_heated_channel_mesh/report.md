# Engineering review report: heated_channel_mesh

- **Run:** `20261120-124736_heated_channel_mesh`
- **Generated:** 2026-11-20T18:20:56+00:00
- **Case file SHA-256:** `e7160033efd653b24d92befaf7af5ae8c1784daee454377d18be21dcfe649bd1`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Tools:** openfoam_bashrc /opt/openfoam14/etc/bashrc; openfoam_version 14; openfoam_package openfoam14 20261008; linux Ubuntu 22.04.5 LTS
- **Code version:** git `c16b216a2d5b9801ad8130364859bfac45eca338` (uncommitted changes present)
- **Simulation status:** completed
- **Verification status:** FAIL

> **Warning:** verification did not pass for every point. Requirement verdicts marked *(unverified)* are not supported by evidence and must not be used for acceptance.

## Scope

2D laminar water channel (1 mm gap, 0.1 m/s) with both walls heated at 30 kW/m2 over 50 mm; OpenFOAM incompressibleFluid + scalarTransport; cells across the gap 20 / 40 / 80, verified against the Graetz thermal-entry solution.

**Assumptions**

- Constant water properties at 25 C (temperature rise under 20 K), so temperature is a passive scalar.
- Hydrodynamically developed inflow: parabolic profile at an exact flow rate, 5 mm unheated entry.
- Uniform heat flux into the water on both walls; the plate's conduction is not modelled (no conjugate heat transfer).
- 2D: the passage is much wider than the gap (side walls neglected; the 3D duct study shows a 3 % effect on flow).

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-T1 | Peak wall temperature over the heated length shall not exceed 45 C. | `max_wall_temperature_C` | <= 45 C |
| REQ-T2 | Coolant temperature rise from inlet to outlet shall not exceed 10 K. | `outlet_bulk_rise_K` | <= 10 K |

## Summary across points

| Point | cells_across_gap | REQ-T1 | REQ-T2 | Checks |
|---|---|---|---|---|
| p00_cells_across_gap-20 | 20 | 44.05 C: **PASS (unverified)** | 7.199 K: **PASS (unverified)** | 8/9 FAIL |
| p01_cells_across_gap-40 | 40 | 44.01 C: **PASS (unverified)** | 7.199 K: **PASS (unverified)** | 8/9 FAIL |
| p02_cells_across_gap-80 | 80 | 44.02 C: **PASS (unverified)** | 7.199 K: **PASS (unverified)** | 8/9 FAIL |

## Run-level checks

Checks that use several points together (for example mesh convergence).

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| discretization_max_wall_temperature_C | relative discretization uncertainty of max_wall_temperature_C (rise above inlet), oscillatory (R = -0.241): 1.25 x half-range of the 3 finest solutions | 0.000998 | 0.01 | PASS |
| discretization_outlet_bulk_rise_K | relative discretization uncertainty of outlet_bulk_rise_K (rise above inlet), converged to within the noise floor (spread 1.1e-12 <= 1e-05) | 7.09e-13 | 0.01 | PASS |

![Requirement metrics across the sweep](sweep.png)

## Point details

### p00_cells_across_gap-20

Parameters: gap_mm = 1, heated_length_mm = 50, entry_length_mm = 5, exit_length_mm = 5, mean_velocity_m_per_s = 0.1, density_kg_per_m3 = 997, dynamic_viscosity_Pa_s = 0.00089, specific_heat_J_per_kgK = 4180, conductivity_W_per_mK = 0.607, inlet_temperature_C = 25, wall_heat_flux_W_per_m2 = 3e+04, cells_across_gap = 20, cell_aspect_ratio = 5

Derived: reynolds_Dh = 224, prandtl = 6.129, peclet_Dh = 1373, graetz_x_star_end = 0.01821, bulk_rise_exact_K = 7.199, wall_minus_bulk_fully_developed_K = 12

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-T1 | 44.05 C | <= 45 | 0.955 | **PASS (unverified)** | [point.json](points/p00_cells_across_gap-20/point.json) |
| REQ-T2 | 7.199 K | <= 10 | 2.8 | **PASS (unverified)** | [point.json](points/p00_cells_across_gap-20/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| mesh | checkMesh reports Mesh OK (1 = failed) | 0.00e+00 | 5e-01 | PASS |
| temperature_converged | final initial residual of the temperature equation | 2.09e-01 | 1e-08 | FAIL |
| flow_rate | |inlet flow - U H| / (U H) | 1.99e-14 | 1e-06 | PASS |
| developed_inflow | |peak velocity at the start of heating - 1.5 U| / 1.5 U (parabolic) | 5.73e-03 | 1e-02 | PASS |
| energy_balance | |outlet bulk rise - 2 q L / (rho cp U H)| / exact rise | 1.06e-12 | 1e-06 | PASS |
| wall_temperature_reference | max |T_wall CFD - Graetz| / (T_wall - T_in) at 0.2, 0.5, 0.9 of the heated length | 1.51e-03 | 1e-02 | PASS |
| peak_vs_reference | |peak wall temperature - Graetz at the end of heating| / rise (model form: the reference has no axial conduction) | 9.42e-04 | 1e-02 | PASS |
| laminar (validity) | Reynolds number (Dh) / 2000 | 1.12e-01 | 1e+00 | PASS |
| reference_assumption (validity) | 100 / Peclet (the reference neglects axial conduction) | 7.28e-02 | 1e+00 | PASS |

![p00_cells_across_gap-20 response](points/p00_cells_across_gap-20/response.png)

### p01_cells_across_gap-40

Parameters: gap_mm = 1, heated_length_mm = 50, entry_length_mm = 5, exit_length_mm = 5, mean_velocity_m_per_s = 0.1, density_kg_per_m3 = 997, dynamic_viscosity_Pa_s = 0.00089, specific_heat_J_per_kgK = 4180, conductivity_W_per_mK = 0.607, inlet_temperature_C = 25, wall_heat_flux_W_per_m2 = 3e+04, cells_across_gap = 40, cell_aspect_ratio = 5

Derived: reynolds_Dh = 224, prandtl = 6.129, peclet_Dh = 1373, graetz_x_star_end = 0.01821, bulk_rise_exact_K = 7.199, wall_minus_bulk_fully_developed_K = 12

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-T1 | 44.01 C | <= 45 | 0.985 | **PASS (unverified)** | [point.json](points/p01_cells_across_gap-40/point.json) |
| REQ-T2 | 7.199 K | <= 10 | 2.8 | **PASS (unverified)** | [point.json](points/p01_cells_across_gap-40/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| mesh | checkMesh reports Mesh OK (1 = failed) | 0.00e+00 | 5e-01 | PASS |
| temperature_converged | final initial residual of the temperature equation | 2.25e-01 | 1e-08 | FAIL |
| flow_rate | |inlet flow - U H| / (U H) | 2.60e-13 | 1e-06 | PASS |
| developed_inflow | |peak velocity at the start of heating - 1.5 U| / 1.5 U (parabolic) | 1.60e-03 | 1e-02 | PASS |
| energy_balance | |outlet bulk rise - 2 q L / (rho cp U H)| / exact rise | 6.06e-13 | 1e-06 | PASS |
| wall_temperature_reference | max |T_wall CFD - Graetz| / (T_wall - T_in) at 0.2, 0.5, 0.9 of the heated length | 1.34e-03 | 1e-02 | PASS |
| peak_vs_reference | |peak wall temperature - Graetz at the end of heating| / rise (model form: the reference has no axial conduction) | 1.16e-03 | 1e-02 | PASS |
| laminar (validity) | Reynolds number (Dh) / 2000 | 1.12e-01 | 1e+00 | PASS |
| reference_assumption (validity) | 100 / Peclet (the reference neglects axial conduction) | 7.28e-02 | 1e+00 | PASS |

![p01_cells_across_gap-40 response](points/p01_cells_across_gap-40/response.png)

### p02_cells_across_gap-80

Parameters: gap_mm = 1, heated_length_mm = 50, entry_length_mm = 5, exit_length_mm = 5, mean_velocity_m_per_s = 0.1, density_kg_per_m3 = 997, dynamic_viscosity_Pa_s = 0.00089, specific_heat_J_per_kgK = 4180, conductivity_W_per_mK = 0.607, inlet_temperature_C = 25, wall_heat_flux_W_per_m2 = 3e+04, cells_across_gap = 80, cell_aspect_ratio = 5

Derived: reynolds_Dh = 224, prandtl = 6.129, peclet_Dh = 1373, graetz_x_star_end = 0.01821, bulk_rise_exact_K = 7.199, wall_minus_bulk_fully_developed_K = 12

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-T1 | 44.02 C | <= 45 | 0.978 | **PASS (unverified)** | [point.json](points/p02_cells_across_gap-80/point.json) |
| REQ-T2 | 7.199 K | <= 10 | 2.8 | **PASS (unverified)** | [point.json](points/p02_cells_across_gap-80/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| mesh | checkMesh reports Mesh OK (1 = failed) | 0.00e+00 | 5e-01 | PASS |
| temperature_converged | final initial residual of the temperature equation | 2.02e-01 | 1e-08 | FAIL |
| flow_rate | |inlet flow - U H| / (U H) | 2.98e-13 | 1e-06 | PASS |
| developed_inflow | |peak velocity at the start of heating - 1.5 U| / 1.5 U (parabolic) | 4.85e-04 | 1e-02 | PASS |
| energy_balance | |outlet bulk rise - 2 q L / (rho cp U H)| / exact rise | 7.34e-14 | 1e-06 | PASS |
| wall_temperature_reference | max |T_wall CFD - Graetz| / (T_wall - T_in) at 0.2, 0.5, 0.9 of the heated length | 2.98e-04 | 1e-02 | PASS |
| peak_vs_reference | |peak wall temperature - Graetz at the end of heating| / rise (model form: the reference has no axial conduction) | 1.03e-03 | 1e-02 | PASS |
| laminar (validity) | Reynolds number (Dh) / 2000 | 1.12e-01 | 1e+00 | PASS |
| reference_assumption (validity) | 100 / Peclet (the reference neglects axial conduction) | 7.28e-02 | 1e+00 | PASS |

![p02_cells_across_gap-80 response](points/p02_cells_across_gap-80/response.png)

## Limitations

- Synthetic geometry and loads; not calibrated to a product.
- No conjugate conduction in the plate, so real wall temperatures would be smoothed along the length.
- Checks establish numerical verification against the Graetz solution and the energy balance only; no test data.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

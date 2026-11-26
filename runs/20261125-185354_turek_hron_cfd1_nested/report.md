# Engineering review report: turek_hron_cfd1_nested

- **Run:** `20261125-185354_turek_hron_cfd1_nested`
- **Generated:** 2026-11-26T00:45:16+00:00
- **Case file SHA-256:** `fe0e03510b6ec592264d7447ba8bd8c99a9ed605a8e7c0810b638ce0af8168ab`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Tools:** openfoam_bashrc /opt/openfoam14/etc/bashrc; gmsh 4.15.0; openfoam_version 14; openfoam_package openfoam14 20261008; linux Ubuntu 22.04.5 LTS
- **Code version:** git `a8aafa1af2d4dcc56bb2b50938e3a3a2fc2552e6` (uncommitted changes present)
- **Simulation status:** completed
- **Verification status:** PASS

## Scope

Turek-Hron CFD1: steady laminar flow (Re 20) in a 2.5 x 0.41 m channel round a cylinder (r 0.05 m) with a rigid 0.35 x 0.02 m flag; OpenFOAM 14 on NESTED Gmsh quad meshes (one 2.5 mm base split uniformly), body cell size 2.5 / 1.25 / 0.625 mm; drag and lift against the published benchmark.

**Assumptions**

- 2D (one cell deep, empty front and back), as the benchmark defines it.
- Steady flow: at Re 20 the wake is steady; the SIMPLE residual targets and the settled force history check it.
- The flag is rigid and fixed (the CFD tests make it so by a huge stiffness and density).
- Inflow: the benchmark's parabolic profile at the full mean velocity (the steady tests have no time ramp).

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-F1 | Before it is coupled to the solid, the fluid model shall reproduce the Turek-Hron CFD1 drag within 1 %. | `drag_deviation_pct` | <= 1 % |
| REQ-F2 | It shall reproduce the CFD1 lift within 2 % (lift is a small difference of large pressure forces, about 8 % of the drag). | `lift_deviation_pct` | <= 2 % |

## Summary across points

| Point | cell_size_m | REQ-F1 | REQ-F2 | Checks |
|---|---|---|---|---|
| p00_cell_size_m-0.0025 | 0.0025 | 0.007328 %: **PASS** | 0.3317 %: **PASS** | 8/8 PASS |
| p01_cell_size_m-0.00125 | 0.00125 | 0.2613 %: **PASS** | 0.6059 %: **PASS** | 8/8 PASS |
| p02_cell_size_m-0.000625 | 0.000625 | 0.2179 %: **PASS** | 0.5257 %: **PASS** | 8/8 PASS |

## Run-level checks

Checks that use several points together (for example mesh convergence).

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| discretization_drag_N_per_m | relative discretization uncertainty of drag_N_per_m, oscillatory (R = -0.171): 1.25 x half-range of the 3 finest solutions | 0.00158 | 0.01 | PASS |
| discretization_lift_N_per_m | relative discretization uncertainty of lift_N_per_m, oscillatory (R = -0.085): 1.25 x half-range of the 3 finest solutions | 0.00583 | 0.01 | PASS |

![Requirement metrics across the sweep](sweep.png)

## Point details

### p00_cell_size_m-0.0025

Parameters: mean_velocity_m_per_s = 0.2, kinematic_viscosity_m2_per_s = 0.001, density_kg_per_m3 = 1000, flag_length_m = 0.35, cell_size_m = 0.0025, benchmark_drag_N_per_m = 14.29, benchmark_lift_N_per_m = 1.119

Derived: reynolds_D = 20, dynamic_pressure_times_D_N_per_m = 2

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-F1 | 0.007328 % | <= 1 | 0.993 | **PASS** | [point.json](points/p00_cell_size_m-0.0025/point.json) |
| REQ-F2 | 0.3317 % | <= 2 | 1.67 | **PASS** | [point.json](points/p00_cell_size_m-0.0025/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| mesh | checkMesh reports Mesh OK (1 = failed) | 0.00e+00 | 0.5 | PASS |
| flag_cells | largest interior angle (deg) of the fluid cells touching the flag, at (0.3455, 0.2110) m (a cell wrapped around a tip corner reads near 180) | 1.23e+02 | 140 | PASS |
| converged | SIMPLE met its residual targets (1 = stopped at the iteration limit) | 0.00e+00 | 0.5 | PASS |
| forces_settled | max over drag and lift of the spread over the last 10 % of iterations / final value | 6.24e-08 | 1e-06 | PASS |
| inflow_profile | max over inlet faces \|U - benchmark parabola at the face centre\| / (1.5 U_mean) | 6.20e-08 | 1e-06 | PASS |
| flow_rate | \|inlet flow - U_mean H depth\| / (U_mean H depth) (midpoint sampling of the parabola on the inlet faces; shrinks with the mesh) | 2.93e-04 | 0.005 | PASS |
| mass_conservation | \|outlet flow - inlet flow\| / inlet flow | 8.53e-14 | 1e-06 | PASS |
| laminar (validity) | Reynolds number (D) / 200 (the benchmark's steady laminar range) | 1.00e-01 | 1 | PASS |

![p00_cell_size_m-0.0025 response](points/p00_cell_size_m-0.0025/response.png)

### p01_cell_size_m-0.00125

Parameters: mean_velocity_m_per_s = 0.2, kinematic_viscosity_m2_per_s = 0.001, density_kg_per_m3 = 1000, flag_length_m = 0.35, cell_size_m = 0.00125, benchmark_drag_N_per_m = 14.29, benchmark_lift_N_per_m = 1.119

Derived: reynolds_D = 20, dynamic_pressure_times_D_N_per_m = 2

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-F1 | 0.2613 % | <= 1 | 0.739 | **PASS** | [point.json](points/p01_cell_size_m-0.00125/point.json) |
| REQ-F2 | 0.6059 % | <= 2 | 1.39 | **PASS** | [point.json](points/p01_cell_size_m-0.00125/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| mesh | checkMesh reports Mesh OK (1 = failed) | 0.00e+00 | 0.5 | PASS |
| flag_cells | largest interior angle (deg) of the fluid cells touching the flag, at (0.3497, 0.2106) m (a cell wrapped around a tip corner reads near 180) | 1.16e+02 | 140 | PASS |
| converged | SIMPLE met its residual targets (1 = stopped at the iteration limit) | 0.00e+00 | 0.5 | PASS |
| forces_settled | max over drag and lift of the spread over the last 10 % of iterations / final value | 2.30e-07 | 1e-06 | PASS |
| inflow_profile | max over inlet faces \|U - benchmark parabola at the face centre\| / (1.5 U_mean) | 6.25e-08 | 1e-06 | PASS |
| flow_rate | \|inlet flow - U_mean H depth\| / (U_mean H depth) (midpoint sampling of the parabola on the inlet faces; shrinks with the mesh) | 7.33e-05 | 0.005 | PASS |
| mass_conservation | \|outlet flow - inlet flow\| / inlet flow | 3.70e-15 | 1e-06 | PASS |
| laminar (validity) | Reynolds number (D) / 200 (the benchmark's steady laminar range) | 1.00e-01 | 1 | PASS |

![p01_cell_size_m-0.00125 response](points/p01_cell_size_m-0.00125/response.png)

### p02_cell_size_m-0.000625

Parameters: mean_velocity_m_per_s = 0.2, kinematic_viscosity_m2_per_s = 0.001, density_kg_per_m3 = 1000, flag_length_m = 0.35, cell_size_m = 0.000625, benchmark_drag_N_per_m = 14.29, benchmark_lift_N_per_m = 1.119

Derived: reynolds_D = 20, dynamic_pressure_times_D_N_per_m = 2

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-F1 | 0.2179 % | <= 1 | 0.782 | **PASS** | [point.json](points/p02_cell_size_m-0.000625/point.json) |
| REQ-F2 | 0.5257 % | <= 2 | 1.47 | **PASS** | [point.json](points/p02_cell_size_m-0.000625/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| mesh | checkMesh reports Mesh OK (1 = failed) | 0.00e+00 | 0.5 | PASS |
| flag_cells | largest interior angle (deg) of the fluid cells touching the flag, at (0.3495, 0.2103) m (a cell wrapped around a tip corner reads near 180) | 1.16e+02 | 140 | PASS |
| converged | SIMPLE met its residual targets (1 = stopped at the iteration limit) | 0.00e+00 | 0.5 | PASS |
| forces_settled | max over drag and lift of the spread over the last 10 % of iterations / final value | 7.73e-07 | 1e-06 | PASS |
| inflow_profile | max over inlet faces \|U - benchmark parabola at the face centre\| / (1.5 U_mean) | 6.25e-08 | 1e-06 | PASS |
| flow_rate | \|inlet flow - U_mean H depth\| / (U_mean H depth) (midpoint sampling of the parabola on the inlet faces; shrinks with the mesh) | 1.83e-05 | 0.005 | PASS |
| mass_conservation | \|outlet flow - inlet flow\| / inlet flow | 2.67e-13 | 1e-06 | PASS |
| laminar (validity) | Reynolds number (D) / 200 (the benchmark's steady laminar range) | 1.00e-01 | 1 | PASS |

![p02_cell_size_m-0.000625 response](points/p02_cell_size_m-0.000625/response.png)

## Limitations

- A solver-qualification case: it shows that the fluid participant reproduces the published fluid-only forces, not that the coupled result is right.
- Pressure outlet at 2.5 m as in the benchmark; no separate domain-length study.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

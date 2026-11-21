# Engineering review report: turek_hron_cfd1_mesh

- **Run:** `20261121-140245_turek_hron_cfd1_mesh`
- **Generated:** 2026-11-21T19:06:18+00:00
- **Case file SHA-256:** `43061bc2f590970766eeaa1c20b7a72b7ae73601eefc41ec42c284e2ee172184`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Tools:** openfoam_bashrc /opt/openfoam14/etc/bashrc; gmsh 4.15.0; openfoam_version 14; openfoam_package openfoam14 20261008; linux Ubuntu 22.04.5 LTS
- **Code version:** git `fea8e67765680000672273b44ac416863a8bbcdd` (uncommitted changes present)
- **Simulation status:** completed
- **Verification status:** FAIL

> **Warning:** verification did not pass for every point. Requirement verdicts marked *(unverified)* are not supported by evidence and must not be used for acceptance.

## Scope

Turek-Hron CFD1: steady laminar flow (Re 20) in a 2.5 x 0.41 m channel round a cylinder (r 0.05 m) with a rigid 0.35 x 0.02 m flag; OpenFOAM 14 on a Gmsh quad-dominant mesh, body cell size 5 / 2.5 / 1.25 mm; drag and lift against the published benchmark.

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
| p00_cell_size_m-0.005 | 0.005 | 0.2337 %: **PASS (unverified)** | 0.9045 %: **PASS** | 7/7 PASS |
| p01_cell_size_m-0.0025 | 0.0025 | 0.007328 %: **PASS (unverified)** | 0.3317 %: **PASS** | 7/7 PASS |
| p02_cell_size_m-0.00125 | 0.00125 | 0.0355 %: **PASS (unverified)** | 0.563 %: **PASS** | 7/7 PASS |

## Run-level checks

Checks that use several points together (for example mesh convergence).

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| discretization_drag_N_per_m | relative discretization uncertainty of drag_N_per_m, anomalous: observed order 3.15 is far above the design order 2, so the solutions are not in the asymptotic range (singularity or coincidence); no estimate | inf | 0.01 | FAIL |
| discretization_lift_N_per_m | relative discretization uncertainty of lift_N_per_m, oscillatory (R = -0.404): 1.25 x half-range of the 3 finest solutions | 0.0036 | 0.01 | PASS |

A failed run-level check withholds the verdicts of requirements on `drag_deviation_pct` at every point: they are marked *(unverified)* in the table above.

![Requirement metrics across the sweep](sweep.png)

## Point details

### p00_cell_size_m-0.005

Parameters: mean_velocity_m_per_s = 0.2, kinematic_viscosity_m2_per_s = 0.001, density_kg_per_m3 = 1000, flag_length_m = 0.35, cell_size_m = 0.005, benchmark_drag_N_per_m = 14.29, benchmark_lift_N_per_m = 1.119

Derived: reynolds_D = 20, dynamic_pressure_times_D_N_per_m = 2

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-F1 | 0.2337 % | <= 1 | 0.766 | **PASS (unverified)** | [point.json](points/p00_cell_size_m-0.005/point.json) |
| REQ-F2 | 0.9045 % | <= 2 | 1.1 | **PASS** | [point.json](points/p00_cell_size_m-0.005/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| mesh | checkMesh reports Mesh OK (1 = failed) | 0.00e+00 | 5e-01 | PASS |
| converged | SIMPLE met its residual targets (1 = stopped at the iteration limit) | 0.00e+00 | 5e-01 | PASS |
| forces_settled | max over drag and lift of the spread over the last 10 % of iterations / final value | 9.39e-11 | 1e-06 | PASS |
| inflow_profile | max over inlet faces |U - benchmark parabola at the face centre| / (1.5 U_mean) | 6.18e-08 | 1e-06 | PASS |
| flow_rate | |inlet flow - U_mean H depth| / (U_mean H depth) (midpoint sampling of the parabola on the inlet faces; shrinks with the mesh) | 1.07e-03 | 5e-03 | PASS |
| mass_conservation | |outlet flow - inlet flow| / inlet flow | 3.29e-13 | 1e-06 | PASS |
| laminar (validity) | Reynolds number (D) / 200 (the benchmark's steady laminar range) | 1.00e-01 | 1e+00 | PASS |

![p00_cell_size_m-0.005 response](points/p00_cell_size_m-0.005/response.png)

### p01_cell_size_m-0.0025

Parameters: mean_velocity_m_per_s = 0.2, kinematic_viscosity_m2_per_s = 0.001, density_kg_per_m3 = 1000, flag_length_m = 0.35, cell_size_m = 0.0025, benchmark_drag_N_per_m = 14.29, benchmark_lift_N_per_m = 1.119

Derived: reynolds_D = 20, dynamic_pressure_times_D_N_per_m = 2

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-F1 | 0.007328 % | <= 1 | 0.993 | **PASS (unverified)** | [point.json](points/p01_cell_size_m-0.0025/point.json) |
| REQ-F2 | 0.3317 % | <= 2 | 1.67 | **PASS** | [point.json](points/p01_cell_size_m-0.0025/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| mesh | checkMesh reports Mesh OK (1 = failed) | 0.00e+00 | 5e-01 | PASS |
| converged | SIMPLE met its residual targets (1 = stopped at the iteration limit) | 0.00e+00 | 5e-01 | PASS |
| forces_settled | max over drag and lift of the spread over the last 10 % of iterations / final value | 6.24e-08 | 1e-06 | PASS |
| inflow_profile | max over inlet faces |U - benchmark parabola at the face centre| / (1.5 U_mean) | 6.20e-08 | 1e-06 | PASS |
| flow_rate | |inlet flow - U_mean H depth| / (U_mean H depth) (midpoint sampling of the parabola on the inlet faces; shrinks with the mesh) | 2.93e-04 | 5e-03 | PASS |
| mass_conservation | |outlet flow - inlet flow| / inlet flow | 8.53e-14 | 1e-06 | PASS |
| laminar (validity) | Reynolds number (D) / 200 (the benchmark's steady laminar range) | 1.00e-01 | 1e+00 | PASS |

![p01_cell_size_m-0.0025 response](points/p01_cell_size_m-0.0025/response.png)

### p02_cell_size_m-0.00125

Parameters: mean_velocity_m_per_s = 0.2, kinematic_viscosity_m2_per_s = 0.001, density_kg_per_m3 = 1000, flag_length_m = 0.35, cell_size_m = 0.00125, benchmark_drag_N_per_m = 14.29, benchmark_lift_N_per_m = 1.119

Derived: reynolds_D = 20, dynamic_pressure_times_D_N_per_m = 2

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-F1 | 0.0355 % | <= 1 | 0.964 | **PASS (unverified)** | [point.json](points/p02_cell_size_m-0.00125/point.json) |
| REQ-F2 | 0.563 % | <= 2 | 1.44 | **PASS** | [point.json](points/p02_cell_size_m-0.00125/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| mesh | checkMesh reports Mesh OK (1 = failed) | 0.00e+00 | 5e-01 | PASS |
| converged | SIMPLE met its residual targets (1 = stopped at the iteration limit) | 0.00e+00 | 5e-01 | PASS |
| forces_settled | max over drag and lift of the spread over the last 10 % of iterations / final value | 2.16e-07 | 1e-06 | PASS |
| inflow_profile | max over inlet faces |U - benchmark parabola at the face centre| / (1.5 U_mean) | 6.25e-08 | 1e-06 | PASS |
| flow_rate | |inlet flow - U_mean H depth| / (U_mean H depth) (midpoint sampling of the parabola on the inlet faces; shrinks with the mesh) | 7.33e-05 | 5e-03 | PASS |
| mass_conservation | |outlet flow - inlet flow| / inlet flow | 2.30e-13 | 1e-06 | PASS |
| laminar (validity) | Reynolds number (D) / 200 (the benchmark's steady laminar range) | 1.00e-01 | 1e+00 | PASS |

![p02_cell_size_m-0.00125 response](points/p02_cell_size_m-0.00125/response.png)

## Limitations

- A solver-qualification case: it shows that the fluid participant reproduces the published fluid-only forces, not that the coupled result is right.
- Pressure outlet at 2.5 m as in the benchmark; no separate domain-length study.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

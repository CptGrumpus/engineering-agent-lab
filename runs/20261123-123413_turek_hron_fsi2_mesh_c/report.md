# Engineering review report: turek_hron_fsi2_mesh_c

- **Run:** `20261123-123413_turek_hron_fsi2_mesh_c`
- **Generated:** 2026-11-23T23:05:02+00:00
- **Case file SHA-256:** `ae0c88a09eb918cb20298215458b74ede3d6729f65d1d8c15c85d3c7b996952f`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Tools:** openfoam_bashrc /usr/lib/openfoam/openfoam2512/etc/bashrc; gmsh 4.15.0
- **Code version:** git `8306afb11b72c345a31e8a44e2ac60d69fe35df2`
- **Simulation status:** failed
- **Verification status:** FAIL

> **Warning:** verification did not pass for every point. Requirement verdicts marked *(unverified)* are not supported by evidence and must not be used for acceptance.

## Scope

Turek-Hron FSI2: self-excited periodic oscillation of the elastic flag behind the cylinder (Re 100, density ratio 10); OpenFOAM v2512 (moving mesh) coupled to CalculiX through preCICE; fluid 1.77 mm at the body (mesh study level c), solid 2.5 mm, dt 0.001 s to 15 s; mean, amplitude and frequency of the tip displacements, drag and lift over the last periods against the published benchmark.

**Assumptions**

- 2D: one cell deep in the fluid, plane strain in the solid (one element layer, as deep as the fluid).
- St. Venant-Kirchhoff solid (CalculiX *ELASTIC under NLGEOM), no gravity, as the FSI tests define it.
- No numerical damping in the solid (HHT alpha 0).
- Inflow: the benchmark's parabola with its (1 - cos) ramp over 2 s.
- Statistics from the last whole periods (benchmark definition); the oscillation is periodic (checked: last two periods).

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-FSI2-1 | The coupled model shall reproduce the FSI2 amplitude of the tip's vertical displacement within 5 %. | `uy_A_amp_deviation_pct` | <= 5 % |
| REQ-FSI2-2 | It shall reproduce the FSI2 oscillation frequency (uy of point A) within 3 %. | `uy_A_freq_Hz_deviation_pct` | <= 3 % |
| REQ-FSI2-3 | It shall reproduce the FSI2 mean drag within 5 %. | `drag_mean_deviation_pct` | <= 5 % |
| REQ-FSI2-4 | It shall reproduce the FSI2 drag amplitude within 15 % (the benchmark's own levels spread 15 %). | `drag_amp_deviation_pct` | <= 15 % |
| REQ-FSI2-5 | It shall reproduce the FSI2 lift amplitude within 10 %. | `lift_amp_deviation_pct` | <= 10 % |
| REQ-FSI2-6 | It shall reproduce the FSI2 mean horizontal tip displacement within 10 % (second order, as in FSI1). | `ux_A_mean_deviation_pct` | <= 10 % |

## Summary across points

| Point | REQ-FSI2-1 | REQ-FSI2-2 | REQ-FSI2-3 | REQ-FSI2-4 | REQ-FSI2-5 | REQ-FSI2-6 | Checks |
|---|---|---|---|---|---|---|---|
| p00_baseline | - %: **NO RESULT** | - %: **NO RESULT** | - %: **NO RESULT** | - %: **NO RESULT** | - %: **NO RESULT** | - %: **NO RESULT** | 0/0 NOT_RUN |

## Point details

### p00_baseline

Parameters: solid_density_kg_per_m3 = 1e+04, shear_modulus_Pa = 5e+05, poisson_ratio = 0.4, fluid_density_kg_per_m3 = 1000, kinematic_viscosity_m2_per_s = 0.001, mean_velocity_m_per_s = 1, fluid_cell_size_m = 0.001768, solid_element_size_mm = 2.5, time_step_s = 0.001, end_time_s = 15, benchmark_ux_A_m = -0.01485, benchmark_uy_A_m = 0.0013, benchmark_drag_N_per_m = 215.1, benchmark_lift_N_per_m = 0.61, benchmark_ux_A_mean = -0.01485, benchmark_ux_A_amp = 0.0127, benchmark_ux_A_freq_Hz = 3.86, benchmark_uy_A_mean = 0.0013, benchmark_uy_A_amp = 0.0816, benchmark_uy_A_freq_Hz = 1.93, benchmark_drag_mean = 215.1, benchmark_drag_amp = 77.65, benchmark_drag_freq_Hz = 3.86, benchmark_lift_mean = 0.61, benchmark_lift_amp = 237.8, benchmark_lift_freq_Hz = 1.93

Derived: reynolds_D = 100, mass_ratio = 10

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-FSI2-1 | - % | <= 5 | - | **NO RESULT** | [point.json](points/p00_baseline/point.json) |
| REQ-FSI2-2 | - % | <= 3 | - | **NO RESULT** | [point.json](points/p00_baseline/point.json) |
| REQ-FSI2-3 | - % | <= 5 | - | **NO RESULT** | [point.json](points/p00_baseline/point.json) |
| REQ-FSI2-4 | - % | <= 15 | - | **NO RESULT** | [point.json](points/p00_baseline/point.json) |
| REQ-FSI2-5 | - % | <= 10 | - | **NO RESULT** | [point.json](points/p00_baseline/point.json) |
| REQ-FSI2-6 | - % | <= 10 | - | **NO RESULT** | [point.json](points/p00_baseline/point.json) |

No verification checks recorded (status: NOT_RUN).

## Limitations

- One level of a three-level mesh study run as separate cases side by side (scripts/combine_mesh_levels.py applies the study's run-level check to the three runs).
- The fluid mesh is regenerated per size (FSI1: about +-0.5 % mesh-to-mesh scatter on the tip displacement).
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

# Engineering review report: enclosure_k20_eps0p9

- **Run:** `20261124-144021_enclosure_k20_eps0p9`
- **Generated:** 2026-11-24T21:15:52+00:00
- **Case file SHA-256:** `3604eebc3da9ae19e5cc968884cde7625555e4bcd4c62d4bfd3fcec1bf22a441`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Code version:** git `89cc692d6a858a58b7246a72d88fbb4a095887f7` (uncommitted changes present)
- **Simulation status:** completed
- **Verification status:** PASS

## Scope

Sealed enclosure, 2D section: 15 W board (5 W component), board conductivity 20 W/mK, internal emissivity 0.9, 40 C ambient; hottest component and mean air against the limits.

**Assumptions**

- 2D section (per unit depth of the 200 mm box); the box's end walls are left out (conservative).
- Laminar natural convection (Rayleigh number about 1e5-1e6 on the box height), air as a perfect gas.
- Grey diffuse internal surfaces (emissivity the corner's value), transparent air.
- Walls: thin aluminium, no conduction resistance and no lateral spreading in the wall (each face loses heat locally: conservative for hot spots); outside h 5 W/m2K and emissivity 0.85 to 40 C (synthetic).
- Board: isotropic effective conductivity (the corner's value; synthetic bracket for FR4 with copper planes); the component a solid block of the board's material.

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-D1 | The hottest component shall stay at or below 85 C at 40 C ambient. | `component_max_C` | <= 85 C |
| REQ-D2 | The mean internal air temperature shall stay at or below 60 C at 40 C ambient. | `air_mean_C` | <= 60 C |

## Summary across points

| Point | REQ-D1 | REQ-D2 | Checks |
|---|---|---|---|
| p00_baseline | 94.25 C: **FAIL** | 67 C: **FAIL** | 2/2 PASS |

## Point details

### p00_baseline

Parameters: width_mm = 150, height_mm = 60, box_depth_mm = 200, board_length_mm = 100, board_thickness_mm = 2, component_length_mm = 20, power_component_W = 5, power_board_W = 10, board_k_W_mK = 20, ambient_C = 40, h_ext_W_m2K = 5, eps_ext = 0.85, eps_int = 0.9, cell_mm = 2, n_phi = 4, max_iterations = 1

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-D1 | 94.25 C | <= 85 | -9.25 | **FAIL** | [point.json](points/p00_baseline/point.json) |
| REQ-D2 | 67 C | <= 60 | -7 | **FAIL** | [point.json](points/p00_baseline/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| heat_balance | \|heat leaving the walls to the ambient - input power\| / input, at the end | 4.57e-03 | 0.01 | PASS |
| settled | change of the component's maximum over the last tenth of the run (K) | 1.97e-03 | 0.3 | PASS |

## Limitations

- 2D: no heat path through the box's end walls and no 3D flow.
- Steady operation only (a transient run to a settled state).
- No physical test data.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

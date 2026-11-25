# Engineering review report: enclosure_fix_k5_eps0p1_br5

- **Run:** `20261124-171511_enclosure_fix_k5_eps0p1_br5`
- **Generated:** 2026-11-25T02:07:48+00:00
- **Case file SHA-256:** `911cba0206a40808028ed170284b179179980cb5d6f92b844eaffdb90b1d8bfb`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Code version:** git `b9472e5e38dc84788f33e23c16fec409d82d26cd` (uncommitted changes present)
- **Simulation status:** completed
- **Verification status:** PASS

## Scope

Sealed enclosure redesign: board 5 W/mK, emissivity 0.1, shell and a bridge of 5 W/mK; aluminium shell 2 mm, 200 W/mK; hottest component and mean air against the limits.

**Assumptions**

- 2D section (per unit depth of the 200 mm box); the box's end walls are left out (conservative).
- Laminar natural convection (Rayleigh number about 1e5-1e6 on the box height), air as a perfect gas.
- Grey diffuse internal surfaces (emissivity the corner's value), transparent air.
- Walls: a 2 mm aluminium shell (200 W/mK) conducting along the walls; outside h 5 W/m2K and emissivity 0.85 to 40 C (synthetic).
- Bridge: a solid block the component's width from its top to the lid, one effective conductivity for a pillar and its gap pad; perfect contact at both ends.
- Board: isotropic effective conductivity (the corner's value; synthetic bracket for FR4 with copper planes); the component a solid block of the board's material.

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-D1 | The hottest component shall stay at or below 85 C at 40 C ambient. | `component_max_C` | <= 85 C |
| REQ-D2 | The mean internal air temperature shall stay at or below 60 C at 40 C ambient. | `air_mean_C` | <= 60 C |

## Summary across points

| Point | REQ-D1 | REQ-D2 | Checks |
|---|---|---|---|
| p00_baseline | 76.12 C: **PASS** | 66.16 C: **FAIL** | 2/2 PASS |

## Point details

### p00_baseline

Parameters: width_mm = 150, height_mm = 60, box_depth_mm = 200, board_length_mm = 100, board_thickness_mm = 2, component_length_mm = 20, power_component_W = 5, power_board_W = 10, board_k_W_mK = 5, ambient_C = 40, h_ext_W_m2K = 5, eps_ext = 0.85, eps_int = 0.1, cell_mm = 2, n_phi = 4, max_iterations = 1, shell_thickness_mm = 2, shell_k_W_mK = 200, bridge_k_W_mK = 5

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-D1 | 76.12 C | <= 85 | 8.88 | **PASS** | [point.json](points/p00_baseline/point.json) |
| REQ-D2 | 66.16 C | <= 60 | -6.16 | **FAIL** | [point.json](points/p00_baseline/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| heat_balance | \|heat leaving the walls to the ambient - input power\| / input, at the end | 4.80e-03 | 0.01 | PASS |
| settled | change of the component's maximum over the last tenth of the run (K) | 1.73e-01 | 0.3 | PASS |

## Limitations

- 2D: no heat path through the box's end walls and no 3D flow.
- Steady operation only (a transient run to a settled state).
- No physical test data.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

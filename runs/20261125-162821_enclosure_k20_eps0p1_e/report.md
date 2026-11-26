# Engineering review report: enclosure_k20_eps0p1_e

- **Run:** `20261125-162821_enclosure_k20_eps0p1_e`
- **Generated:** 2026-11-26T03:51:07+00:00
- **Case file SHA-256:** `282c1c2b76bbbdbe5946a19a9d57f55f37b7171ed48a9612b9eb25ca96fd8991`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Code version:** git `5a4d5898ad52f8ad8dd6d504da83f774cd3367fd` (uncommitted changes present)
- **Simulation status:** completed
- **Verification status:** PASS

## Scope

Sealed enclosure, 2D section: 15 W board (5 W component), board conductivity 20 W/mK, internal emissivity 0.1, 40 C ambient; hottest component and mean air against the limits.

**Assumptions**

- 2D section (per unit depth of the 200 mm box); the box's end walls are left out (conservative).
- Laminar natural convection (Rayleigh number about 1e5-1e6 on the box height), air as a perfect gas.
- Grey diffuse internal surfaces (emissivity the corner's value), transparent air.
- Walls: thin aluminium, no conduction resistance and no lateral spreading in the wall (each face loses heat locally: conservative for hot spots); outside h 5 W/m2K and emissivity 0.85 to 40 C (synthetic).
- Board: isotropic effective conductivity (the corner's value; synthetic bracket for FR4 with copper planes); the component a solid block of the board's material.

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-E1 | U1's junction shall stay at or below 125 C (Tj max 150 C less the client's 25 K derating): its case at or below 115 C with 2.0 K/W junction to case at 5 W; the U1 block's hottest point stands for the case. | `component_max_C` | <= 115 C |
| REQ-E2 | The FR-4 board shall stay at or below 105 C anywhere (UL 796 MOT 130 C less the client's 25 K). | `board_max_C` | <= 105 C |
| REQ-E3 | C1 (105 C / 5,000 h electrolytic, 5-15 mm from the board's left end) shall stay at or below 70 C, for 50,000 h of life; the board under its footprint stands for C1. | `C1_board_max_C` | <= 70 C |
| REQ-E4 | The internal air shall stay at or below 70 C (the commercial-grade parts' 0-70 C ambient rating; the mean air stands for the local air in 2D). | `air_mean_C` | <= 70 C |

## Summary across points

| Point | REQ-E1 | REQ-E2 | REQ-E3 | REQ-E4 | Checks |
|---|---|---|---|---|---|
| p00_baseline | 157.4 C: **FAIL** | 156.4 C: **FAIL** | 152.7 C: **FAIL** | 84.55 C: **FAIL** | 2/2 PASS |

## Point details

### p00_baseline

Parameters: width_mm = 150, height_mm = 60, box_depth_mm = 200, board_length_mm = 100, board_thickness_mm = 2, component_length_mm = 20, power_component_W = 5, power_board_W = 10, board_k_W_mK = 20, ambient_C = 40, h_ext_W_m2K = 5, eps_ext = 0.85, eps_int = 0.1, cell_mm = 2, n_phi = 4, max_iterations = 1

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-E1 | 157.4 C | <= 115 | -42.4 | **FAIL** | [point.json](points/p00_baseline/point.json) |
| REQ-E2 | 156.4 C | <= 105 | -51.4 | **FAIL** | [point.json](points/p00_baseline/point.json) |
| REQ-E3 | 152.7 C | <= 70 | -82.7 | **FAIL** | [point.json](points/p00_baseline/point.json) |
| REQ-E4 | 84.55 C | <= 70 | -14.5 | **FAIL** | [point.json](points/p00_baseline/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| heat_balance | \|heat leaving the walls to the ambient - input power\| / input, at the end | 3.65e-06 | 0.01 | PASS |
| settled | change of the component's maximum over the last tenth of the run (K) | 9.10e-06 | 0.3 | PASS |

## Limitations

- 2D: no heat path through the box's end walls and no 3D flow.
- Steady operation only (a transient run to a settled state).
- No physical test data.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

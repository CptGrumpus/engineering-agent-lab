# Engineering review report: enclosure_k5_eps0p9_e

- **Run:** `20261125-162808_enclosure_k5_eps0p9_e`
- **Generated:** 2026-11-25T22:59:16+00:00
- **Case file SHA-256:** `1de594069341145444132264ccc8fd94044bdffbccab2e0ee94e1bcd48c3355c`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Code version:** git `7abeedea829d2a90d1f370baeffdf32cad39ab1a` (uncommitted changes present)
- **Simulation status:** completed
- **Verification status:** PASS

## Scope

Sealed enclosure, 2D section: 15 W board (5 W component), board conductivity 5 W/mK, internal emissivity 0.9, 40 C ambient; hottest component and mean air against the limits.

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
| p00_baseline | 98.45 C: **PASS** | 95.84 C: **PASS** | 89.16 C: **FAIL** | 66.93 C: **PASS** | 2/2 PASS |

## Point details

### p00_baseline

Parameters: width_mm = 150, height_mm = 60, box_depth_mm = 200, board_length_mm = 100, board_thickness_mm = 2, component_length_mm = 20, power_component_W = 5, power_board_W = 10, board_k_W_mK = 5, ambient_C = 40, h_ext_W_m2K = 5, eps_ext = 0.85, eps_int = 0.9, cell_mm = 2, n_phi = 4, max_iterations = 1

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-E1 | 98.45 C | <= 115 | 16.6 | **PASS** | [point.json](points/p00_baseline/point.json) |
| REQ-E2 | 95.84 C | <= 105 | 9.16 | **PASS** | [point.json](points/p00_baseline/point.json) |
| REQ-E3 | 89.16 C | <= 70 | -19.2 | **FAIL** | [point.json](points/p00_baseline/point.json) |
| REQ-E4 | 66.93 C | <= 70 | 3.07 | **PASS** | [point.json](points/p00_baseline/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| heat_balance | \|heat leaving the walls to the ambient - input power\| / input, at the end | 3.07e-05 | 0.01 | PASS |
| settled | change of the component's maximum over the last tenth of the run (K) | 2.06e-03 | 0.3 | PASS |

## Limitations

- 2D: no heat path through the box's end walls and no 3D flow.
- Steady operation only (a transient run to a settled state).
- No physical test data.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

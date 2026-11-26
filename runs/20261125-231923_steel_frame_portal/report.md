# Engineering review report: steel_frame_portal

- **Run:** `20261125-231923_steel_frame_portal`
- **Generated:** 2026-11-26T04:19:23+00:00
- **Case file SHA-256:** `339eb6f37611895f263840cc75b4c57e906110399ead0b27fe14341ab06a47c1`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Code version:** git `2bc42b4426bbf0b786e28d172ca3e6cfa089e6e7` (uncommitted changes present)
- **Simulation status:** completed
- **Verification status:** PASS

## Scope

Single-bay steel portal for an equipment platform (W10x33 columns 4.0 m, W14x30 beam 6.0 m, fixed bases), AISC 360-22 LRFD by the Direct Analysis Method: member interaction H1-1, beam live-load deflection and service drift against the client's limits.

**Assumptions**

- Plane frame; rigid knees (no joint flexibility); fixed bases.
- Direct Analysis Method (C2): second-order analysis with P-Delta and P-delta (exact stability functions), all stiffnesses x 0.8, tau_b = 1 (checked: alpha Pr / Pns under 0.5), notional loads 0.002 Y in the lateral direction.
- Effective length = unbraced length (C3). Columns braced out of plane at base and beam only (4.0 m); beam laterally unbraced over its 6.0 m span (conservative; the client has not specified the bracing).
- Cb from each member's own second-order moment diagram (Eq. F1-1).
- Factored loads as given by the client (LRFD); serviceability with nominal stiffness: live-load deflection first order, drift second order with the service live load on the beam.
- Section properties from the AISC Shapes Database v16.0; ASTM A992 Fy 345 MPa, E 200,000 MPa.

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-A1 | Every member's combined axial and flexural ratio by AISC 360-22 Eq. H1-1 (LRFD, Direct Analysis Method) shall be at most 1.0. | `max_interaction_ratio` | <= 1 - |
| REQ-A2 | The beam's live-load deflection shall be at most L/360 (6,000 / 360 = 16.7 mm). | `live_deflection_mm` | <= 16.67 mm |
| REQ-A3 | The frame's drift under the service lateral load shall be at most H/400 (4,000 / 400 = 10.0 mm). | `service_drift_mm` | <= 10 mm |

## Summary across points

| Point | REQ-A1 | REQ-A2 | REQ-A3 | Checks |
|---|---|---|---|---|
| p00_baseline | 0.8006 -: **PASS** | 4.1 mm: **PASS** | 2.613 mm: **PASS** | 7/7 PASS |

## Point details

### p00_baseline

Parameters: frame_height_m = 4, bay_span_m = 6, column_shape = W10X33, beam_shape = W14X30, youngs_modulus_MPa = 2e+05, yield_strength_MPa = 345, base = fixed, factored_gravity_kN_per_m = 35, factored_lateral_kN = 15, service_live_kN_per_m = 12, service_lateral_kN = 10, beam_unbraced_length_m = 6, column_unbraced_length_weak_m = 4

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-A1 | 0.8006 - | <= 1 | 0.199 | **PASS** | [point.json](points/p00_baseline/point.json) |
| REQ-A2 | 4.1 mm | <= 16.67 | 12.6 | **PASS** | [point.json](points/p00_baseline/point.json) |
| REQ-A3 | 2.613 mm | <= 10 | 7.39 | **PASS** | [point.json](points/p00_baseline/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| benchmarks_aisc | largest relative miss against the AISC Design Examples: C.1A drift (scaled to its 2 % tolerance) and moments, E.1D, F.1-3B, H.1B | 9.11e-03 | 0.01 | PASS |
| closed_form_portal | first-order knee moment (UDL) and base moment (lateral) against Kleinlogel's closed forms, axially rigid | 3.59e-09 | 1e-06 | PASS |
| equilibrium | largest \|sum of reactions + applied loads\| / total gravity, both load cases | 3.31e-14 | 1e-09 | PASS |
| b1b2_vs_exact | \|Appendix 8 B1-B2 amplified moment - exact second-order moment\| / exact, right column top, gravity + lateral | 4.75e-04 | 0.02 | PASS |
| segments | right column top moment with 2 against 8 members per span (exact at nodes: should agree to round-off) | 2.92e-10 | 1e-06 | PASS |
| tau_b (validity) | largest alpha Pr / Pns (C2.3: tau_b = 1 and the 0.8 reduction alone apply up to 0.5) | 5.06e-02 | 0.5 | PASS |
| drift_ratio (validity) | second- to first-order drift ratio (Commentary C1 recommends at most 2.5; above 1.7 notional loads go into every load case) | 1.02e+00 | 2.5 | PASS |

## Limitations

- Connections, base plates and anchorage not designed (the knees and bases are assumed rigid and adequate).
- Out-of-plane stability of the frame (bracing members) not checked.
- No dynamic or fatigue assessment of the equipment loads.
- Synthetic client and loads.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

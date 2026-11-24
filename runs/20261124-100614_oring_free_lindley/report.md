# Engineering review report: oring_free_lindley

- **Run:** `20261124-100614_oring_free_lindley`
- **Generated:** 2026-11-24T15:15:04+00:00
- **Case file SHA-256:** `877e9b574b9905c51018b40da58206fd96e511cf09ba40355ec12700de31cfd7`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Tools:** CalculiX This is Version 2.22; gmsh 4.15.0
- **Code version:** git `19cd5f58820a6b7f9759e6ef56fdf30949314bbf`
- **Simulation status:** failed
- **Verification status:** FAIL

> **Warning:** verification did not pass for every point. Requirement verdicts marked *(unverified)* are not supported by evidence and must not be used for acceptance.

## Scope

O-ring 3.53 mm, 70 Shore A, laterally unrestrained (no groove walls) between flat plates to 30 % squeeze; force against squeeze over the run against Lindley's relation and Parker's measured band (reference case).

**Assumptions**

- Axisymmetric; the mid-plane is a symmetry plane (flat groove bottom and cover, frictionless contact, quasi-static), so the upper half of the cross-section is modelled.
- Neo-Hookean rubber, E from Shore A by Gent's relation (synthetic compound; the hardness tolerance carries the material uncertainty), near-incompressible (K = 1000 G; checked: volume conservation).
- Steel cover and groove walls (E 200 GPa, effectively rigid against the rubber).
- Installed against the groove's outer wall (internal pressure); the ring's ID follows the cross-section so its OD equals the groove OD at every corner.
- Unpressurised installation: the 0.3 MPa sealed pressure enters only through REQ-E2's 2 x rule, not as a load.

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-R1a | Validation: the closing force at 30 % squeeze shall be at least the lower end of Parker's measured 70 Shore A band for the 0.139 in cross-section (ORD 5700 Fig. 2-6; 1.891 N/mm). | `force_per_length_N_per_mm` | >= 1.891 N/mm |
| REQ-R1b | Validation: the closing force at 30 % squeeze shall not exceed the upper end of that band (12.999 N/mm). | `force_per_length_N_per_mm` | <= 12.999 N/mm |

## Summary across points

| Point | REQ-R1a | REQ-R1b | Checks |
|---|---|---|---|
| p00_baseline | - N/mm: **NO RESULT** | - N/mm: **NO RESULT** | 0/0 NOT_RUN |

## Point details

### p00_baseline

Parameters: cross_section_mm = 3.53, ring_inner_diameter_mm = 50, groove_depth_mm = 2.471, groove_width_mm = 4.8, groove_outer_diameter_mm = 57.06, groove_walls = 0, shore_a = 70, bulk_to_shear = 1000, contact_element_size_mm = 0.05, far_element_size_mm = 0.2, penalty_factor = 10

Derived: squeeze = 0.3, youngs_modulus_MPa = 5.521, groove_fill_hand = 0.8251

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-R1a | - N/mm | >= 1.891 | - | **NO RESULT** | [point.json](points/p00_baseline/point.json) |
| REQ-R1b | - N/mm | <= 12.999 | - | **NO RESULT** | [point.json](points/p00_baseline/point.json) |

No verification checks recorded (status: NOT_RUN).

## Limitations

- No friction, no compression set or stress relaxation over time, no temperature effects on the compound.
- Lindley's relation is empirical and its exponents are not yet confirmed from a second source; Parker's band is wide (a factor of about 6.6).
- No physical test data.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

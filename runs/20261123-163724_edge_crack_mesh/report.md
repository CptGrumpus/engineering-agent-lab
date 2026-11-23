# Engineering review report: edge_crack_mesh

- **Run:** `20261123-163724_edge_crack_mesh`
- **Generated:** 2026-11-23T21:40:54+00:00
- **Case file SHA-256:** `0f8fbac7da57bf139eeedb04b22573905331e371bf43883800fa9379670e7091`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Tools:** gmsh 4.15.0; calculix This is Version 2.22
- **Code version:** git `a57591330ff71c8537fb3617b3c5a10dc8b4cd62`
- **Simulation status:** completed
- **Verification status:** FAIL

> **Warning:** verification did not pass for every point. Requirement verdicts marked *(unverified)* are not supported by evidence and must not be used for acceptance.

## Scope

Edge-cracked S355 plate (100 mm wide, 10 mm thick) in cyclic tension, 150 MPa maximum, R = 0.1: K(a) by FE at 11 crack lengths 2-45 mm (energy release rate and crack opening, CalculiX plane strain on a Gmsh half model refined at the tip), critical crack against Kmat 100 MPa sqrt m and net-section yield, BS 7910 crack growth life from 2 mm; tip element sizes 0.1 / 0.05 / 0.025 mm.

**Assumptions**

- Linear elastic fracture mechanics, plane strain (K from G with E / (1 - nu^2)); the plastic zone at Kmax 13-100 MPa sqrt m in S355 (r_p = (K / sigma_y)^2 / 6 pi up to 4 mm at the critical crack) is small against the ligament until the last few millimetres. [model form]
- Uniform remote tension with the plate's ends free to rotate (Tada's case); the half model's height (200 mm, 2 W) makes the end conditions irrelevant at the crack.
- Crack growth by the BS 7910 / IIW simplified law for steels in air (R < 0.5): da/dN = 5.21e-13 dK^3 mm/cycle, dK in N/mm^1.5, threshold 63 N/mm^1.5. [published design law]
- Fracture toughness Kmat 100 MPa sqrt m [synthetic: a client would give CTOD or Charpy results]; net-section yield at 355 MPa (S355) [standard].
- Constant-amplitude loading, 150 MPa maximum at R = 0.1 [synthetic]; detectable crack 2 mm (magnetic particle inspection) [synthetic].

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-F1 | At the detectable crack (2 mm) the maximum stress intensity shall not exceed half the fracture toughness (Kmat / 2 = 50 MPa sqrt m). | `K_a0_MPa_sqrt_m` | <= 50 MPa sqrt m |
| REQ-F2 | The crack growth life from the detectable crack to the critical crack shall be at least twice the planned inspection interval of 40,000 cycles. | `growth_life_cycles` | >= 80000 cycles |

## Summary across points

| Point | tip_element_size_mm | REQ-F1 | REQ-F2 | Checks |
|---|---|---|---|---|
| p00_tip_element_size_mm-0.1 | 0.1 | 13.39 MPa sqrt m: **PASS** | 9.203e+04 cycles: **PASS (unverified)** | 6/6 PASS |
| p01_tip_element_size_mm-0.05 | 0.05 | 13.35 MPa sqrt m: **PASS** | 9.222e+04 cycles: **PASS (unverified)** | 6/6 PASS |
| p02_tip_element_size_mm-0.025 | 0.025 | 13.36 MPa sqrt m: **PASS** | 9.198e+04 cycles: **PASS (unverified)** | 6/6 PASS |

## Run-level checks

Checks that use several points together (for example mesh convergence).

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| discretization_K_a0_MPa_sqrt_m | relative discretization uncertainty of K_a0_MPa_sqrt_m, oscillatory (R = -0.138): 1.25 x half-range of the 3 finest solutions | 0.00183 | 0.01 | PASS |
| discretization_crit_crack_mm | relative discretization uncertainty of crit_crack_mm, monotone (R = 0.145): GCI_fine, observed order 2.78, extrapolated 37.0057 | 7.21e-06 | 0.01 | PASS |
| discretization_growth_life_cycles | relative discretization uncertainty of growth_life_cycles, divergent (oscillating, growing) (R = -1.253): no estimate | inf | 0.01 | FAIL |

A failed run-level check withholds the verdicts of requirements on `growth_life_cycles` at every point: they are marked *(unverified)* in the table above.

![Requirement metrics across the sweep](sweep.png)

## Point details

### p00_tip_element_size_mm-0.1

Parameters: width_mm = 100, half_height_mm = 200, thickness_mm = 10, sigma_max_MPa = 150, stress_ratio = 0.1, youngs_modulus_MPa = 2.1e+05, poisson_ratio = 0.3, yield_strength_MPa = 355, k_mat_MPa_sqrt_m = 100, paris_C = 5.21e-13, paris_m = 3, dK_threshold = 63, initial_crack_mm = 2, tip_element_size_mm = 0.1, far_element_size_mm = 5

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-F1 | 13.39 MPa sqrt m | <= 50 | 36.6 | **PASS** | [point.json](points/p00_tip_element_size_mm-0.1/point.json) |
| REQ-F2 | 9.203e+04 cycles | >= 80000 | 1.2e+04 | **PASS (unverified)** | [point.json](points/p00_tip_element_size_mm-0.1/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| tada | max |K (energy route) / Tada - 1| for a/W <= 0.6 (Tada's own accuracy 0.5 %) | 6.28e-03 | 1e-02 | PASS |
| k_routes | max |K (crack opening) / K (energy) - 1| over the crack lengths | 2.54e-02 | 3e-02 | PASS |
| equilibrium | max |ligament reaction + applied load| / applied load | 1.21e-16 | 1e-06 | PASS |
| energy_step | |K (energy, step eps) / K (step eps / 2) - 1| at a = 10 mm (the central difference's step and the mesh noise in U together) | 6.13e-05 | 1e-03 | PASS |
| life_integral | |life by adaptive quadrature - by Simpson on 4000 steps| / quadrature | 2.40e-10 | 1e-04 | PASS |
| crack_range (validity) | critical crack / largest sampled crack (below 1: K(a) is sampled past the critical crack) | 8.23e-01 | 1e+00 | PASS |

![p00_tip_element_size_mm-0.1 response](points/p00_tip_element_size_mm-0.1/response.png)

### p01_tip_element_size_mm-0.05

Parameters: width_mm = 100, half_height_mm = 200, thickness_mm = 10, sigma_max_MPa = 150, stress_ratio = 0.1, youngs_modulus_MPa = 2.1e+05, poisson_ratio = 0.3, yield_strength_MPa = 355, k_mat_MPa_sqrt_m = 100, paris_C = 5.21e-13, paris_m = 3, dK_threshold = 63, initial_crack_mm = 2, tip_element_size_mm = 0.05, far_element_size_mm = 5

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-F1 | 13.35 MPa sqrt m | <= 50 | 36.6 | **PASS** | [point.json](points/p01_tip_element_size_mm-0.05/point.json) |
| REQ-F2 | 9.222e+04 cycles | >= 80000 | 1.22e+04 | **PASS (unverified)** | [point.json](points/p01_tip_element_size_mm-0.05/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| tada | max |K (energy route) / Tada - 1| for a/W <= 0.6 (Tada's own accuracy 0.5 %) | 6.03e-03 | 1e-02 | PASS |
| k_routes | max |K (crack opening) / K (energy) - 1| over the crack lengths | 2.18e-02 | 3e-02 | PASS |
| equilibrium | max |ligament reaction + applied load| / applied load | 1.21e-16 | 1e-06 | PASS |
| energy_step | |K (energy, step eps) / K (step eps / 2) - 1| at a = 10 mm (the central difference's step and the mesh noise in U together) | 6.97e-04 | 1e-03 | PASS |
| life_integral | |life by adaptive quadrature - by Simpson on 4000 steps| / quadrature | 7.23e-10 | 1e-04 | PASS |
| crack_range (validity) | critical crack / largest sampled crack (below 1: K(a) is sampled past the critical crack) | 8.22e-01 | 1e+00 | PASS |

![p01_tip_element_size_mm-0.05 response](points/p01_tip_element_size_mm-0.05/response.png)

### p02_tip_element_size_mm-0.025

Parameters: width_mm = 100, half_height_mm = 200, thickness_mm = 10, sigma_max_MPa = 150, stress_ratio = 0.1, youngs_modulus_MPa = 2.1e+05, poisson_ratio = 0.3, yield_strength_MPa = 355, k_mat_MPa_sqrt_m = 100, paris_C = 5.21e-13, paris_m = 3, dK_threshold = 63, initial_crack_mm = 2, tip_element_size_mm = 0.025, far_element_size_mm = 5

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-F1 | 13.36 MPa sqrt m | <= 50 | 36.6 | **PASS** | [point.json](points/p02_tip_element_size_mm-0.025/point.json) |
| REQ-F2 | 9.198e+04 cycles | >= 80000 | 1.2e+04 | **PASS (unverified)** | [point.json](points/p02_tip_element_size_mm-0.025/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| tada | max |K (energy route) / Tada - 1| for a/W <= 0.6 (Tada's own accuracy 0.5 %) | 6.29e-03 | 1e-02 | PASS |
| k_routes | max |K (crack opening) / K (energy) - 1| over the crack lengths | 1.86e-02 | 3e-02 | PASS |
| equilibrium | max |ligament reaction + applied load| / applied load | 1.21e-16 | 1e-06 | PASS |
| energy_step | |K (energy, step eps) / K (step eps / 2) - 1| at a = 10 mm (the central difference's step and the mesh noise in U together) | 7.94e-05 | 1e-03 | PASS |
| life_integral | |life by adaptive quadrature - by Simpson on 4000 steps| / quadrature | 4.69e-10 | 1e-04 | PASS |
| crack_range (validity) | critical crack / largest sampled crack (below 1: K(a) is sampled past the critical crack) | 8.22e-01 | 1e+00 | PASS |

![p02_tip_element_size_mm-0.025 response](points/p02_tip_element_size_mm-0.025/response.png)

## Limitations

- Through-thickness straight crack front; a real surface crack starts semi-elliptical (BS 7910 Annex M would give its K).
- No crack closure, no load sequence effects, no environment (air).
- Net-section yield by the simple uniform-stress formula; the eccentric ligament also bends.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

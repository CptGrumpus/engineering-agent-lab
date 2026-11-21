# Engineering review report: flag_csm3_dt

- **Run:** `20261121-132448_flag_csm3_dt`
- **Generated:** 2026-11-21T19:25:04+00:00
- **Case file SHA-256:** `848b1066c503a55e6241705e042284bc29d760d6443d3bea138af7b58a16639a`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Tools:** CalculiX This is Version 2.22
- **Code version:** git `fea8e67765680000672273b44ac416863a8bbcdd` (uncommitted changes present)
- **Simulation status:** completed
- **Verification status:** FAIL

> **Warning:** verification did not pass for every point. Requirement verdicts marked *(unverified)* are not supported by evidence and must not be used for acceptance.

## Scope

Turek-Hron CSM3: the elastic flag (plane strain, St. Venant-Kirchhoff, mu_s 0.5 MPa, nu 0.4, rho 1000 kg/m3) released from rest under gravity (2 m/s2) and left to swing undamped; CalculiX NLGEOM *DYNAMIC (trapezoidal rule), 2.5 mm C3D8I, time step 0.01 / 0.005 / 0.0025 / 0.00125 s, 6 s; checked against the published band, a small-amplitude companion run, the modal frequency and beam theory.

**Assumptions**

- Plane strain, per unit depth (established in flag_csm1_mesh).
- St. Venant-Kirchhoff material (CalculiX *ELASTIC under NLGEOM), as the benchmark defines it.
- No damping, physical or numerical (ALPHA = 0), so the oscillation should repeat exactly.
- 2.5 mm elements: the static mesh study (flag_csm1_mesh) puts uy(A) at this size 0.09 % from its extrapolated value.

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-S3 | The solid model shall reproduce the CSM3 mean vertical displacement of point A inside the band of the published rows, or within 1 % of its nearest edge. | `uy_mean_band_dev_pct` | <= 1 % |
| REQ-S4 | It shall reproduce the CSM3 vertical amplitude of point A inside the published band, or within 1 % of its nearest edge. | `uy_amplitude_band_dev_pct` | <= 1 % |
| REQ-S5 | It shall reproduce the CSM3 mean horizontal displacement of point A inside the published band, or within 2 % of its nearest edge. | `ux_mean_band_dev_pct` | <= 2 % |
| REQ-S6 | It shall reproduce the CSM3 oscillation frequency inside the published band, or within 1 % of its nearest edge. | `frequency_band_dev_pct` | <= 1 % |

## Summary across points

| Point | time_step_s | REQ-S3 | REQ-S4 | REQ-S5 | REQ-S6 | Checks |
|---|---|---|---|---|---|---|
| p00_time_step_s-0.01 | 0.01 | 0.6195 %: **PASS (unverified)** | 0 %: **PASS (unverified)** | 1.324 %: **PASS (unverified)** | 0.644 %: **PASS (unverified)** | 4/7 FAIL |
| p01_time_step_s-0.005 | 0.005 | 0 %: **PASS (unverified)** | 0 %: **PASS (unverified)** | 0 %: **PASS (unverified)** | 0.4489 %: **PASS (unverified)** | 5/7 FAIL |
| p02_time_step_s-0.0025 | 0.0025 | 0 %: **PASS** | 0 %: **PASS** | 0 %: **PASS** | 0.1576 %: **PASS (unverified)** | 7/7 PASS |
| p03_time_step_s-0.00125 | 0.00125 | 0.05096 %: **PASS (unverified)** | 0 %: **PASS (unverified)** | 0 %: **PASS (unverified)** | 0.1422 %: **PASS (unverified)** | 6/7 FAIL |

## Run-level checks

Checks that use several points together (for example mesh convergence).

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| time_step_uy_mean_mm | relative time-step uncertainty of uy_mean_mm, monotone (R = 0.578): GCI_fine, observed order 0.79, extrapolated -65.0539 | 0.00492 | 0.01 | PASS |
| time_step_uy_amplitude_mm | relative time-step uncertainty of uy_amplitude_mm, monotone (R = 0.272): GCI_fine, observed order 1.88, extrapolated 64.8252 | 0.000421 | 0.01 | PASS |
| time_step_ux_mean_mm | relative time-step uncertainty of ux_mean_mm, monotone (R = 0.354): GCI_fine, observed order 1.50, extrapolated -14.642 | 0.00106 | 0.01 | PASS |
| time_step_frequency_Hz | relative time-step uncertainty of frequency_Hz, anomalous: observed order 4.24 is far above the design order 2, so the solutions are not in the asymptotic range (singularity or coincidence); no estimate | inf | 0.01 | FAIL |

A failed run-level check withholds the verdicts of requirements on `frequency_band_dev_pct` at every point: they are marked *(unverified)* in the table above.

![Requirement metrics across the sweep](sweep.png)

## Point details

### p00_time_step_s-0.01

Parameters: density_kg_per_m3 = 1000, shear_modulus_Pa = 5e+05, poisson_ratio = 0.4, gravity_m_per_s2 = 2, flag_length_m = 0.35, flag_height_m = 0.02, cylinder_radius_m = 0.05, element_size_mm = 2.5, time_step_s = 0.01

Derived: beam_frequency_Hz = 1.077, steps_per_linear_period = 92.88, height_over_length = 0.05714

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-S3 | 0.6195 % | <= 1 | 0.38 | **PASS (unverified)** | [point.json](points/p00_time_step_s-0.01/point.json) |
| REQ-S4 | 0 % | <= 1 | 1 | **PASS (unverified)** | [point.json](points/p00_time_step_s-0.01/point.json) |
| REQ-S5 | 1.324 % | <= 2 | 0.676 | **PASS (unverified)** | [point.json](points/p00_time_step_s-0.01/point.json) |
| REQ-S6 | 0.644 % | <= 1 | 0.356 | **PASS (unverified)** | [point.json](points/p00_time_step_s-0.01/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| integrator_small_amplitude | |frequency of a gravity/1000 run - linear modal f1| / f1 (the time integrator alone) | 6.43e-04 | 2e-03 | PASS |
| returns_to_start | max uy(A) over the last period / amplitude (undamped: the flag swings back to its undeformed height) | 2.89e-02 | 1e-02 | FAIL |
| periodic_troughs | spread of the trough depths of uy(A) over all periods / mean depth | 1.31e-02 | 1e-02 | FAIL |
| periodic_periods | spread of the periods / mean period | 1.59e-02 | 1e-02 | FAIL |
| frequency_reference | |f1 modal - Euler-Bernoulli cantilever| / beam value (model form) | 4.13e-03 | 2e-02 | PASS |
| periods_seen | shortfall of full periods before the last one (needs >= 3) | 0.00e+00 | 5e-01 | PASS |
| steps_per_period (validity) | 50 / time steps per linear period (below 1: at least 50 steps a period, period error of the trapezoidal rule about (2 pi / 50)^2 / 12 = 0.13 %) | 5.38e-01 | 1e+00 | PASS |

![p00_time_step_s-0.01 response](points/p00_time_step_s-0.01/response.png)

### p01_time_step_s-0.005

Parameters: density_kg_per_m3 = 1000, shear_modulus_Pa = 5e+05, poisson_ratio = 0.4, gravity_m_per_s2 = 2, flag_length_m = 0.35, flag_height_m = 0.02, cylinder_radius_m = 0.05, element_size_mm = 2.5, time_step_s = 0.005

Derived: beam_frequency_Hz = 1.077, steps_per_linear_period = 185.8, height_over_length = 0.05714

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-S3 | 0 % | <= 1 | 1 | **PASS (unverified)** | [point.json](points/p01_time_step_s-0.005/point.json) |
| REQ-S4 | 0 % | <= 1 | 1 | **PASS (unverified)** | [point.json](points/p01_time_step_s-0.005/point.json) |
| REQ-S5 | 0 % | <= 2 | 2 | **PASS (unverified)** | [point.json](points/p01_time_step_s-0.005/point.json) |
| REQ-S6 | 0.4489 % | <= 1 | 0.551 | **PASS (unverified)** | [point.json](points/p01_time_step_s-0.005/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| integrator_small_amplitude | |frequency of a gravity/1000 run - linear modal f1| / f1 (the time integrator alone) | 7.51e-03 | 2e-03 | FAIL |
| returns_to_start | max uy(A) over the last period / amplitude (undamped: the flag swings back to its undeformed height) | 1.27e-02 | 1e-02 | FAIL |
| periodic_troughs | spread of the trough depths of uy(A) over all periods / mean depth | 2.63e-03 | 1e-02 | PASS |
| periodic_periods | spread of the periods / mean period | 6.22e-03 | 1e-02 | PASS |
| frequency_reference | |f1 modal - Euler-Bernoulli cantilever| / beam value (model form) | 4.13e-03 | 2e-02 | PASS |
| periods_seen | shortfall of full periods before the last one (needs >= 3) | 0.00e+00 | 5e-01 | PASS |
| steps_per_period (validity) | 50 / time steps per linear period (below 1: at least 50 steps a period, period error of the trapezoidal rule about (2 pi / 50)^2 / 12 = 0.13 %) | 2.69e-01 | 1e+00 | PASS |

![p01_time_step_s-0.005 response](points/p01_time_step_s-0.005/response.png)

### p02_time_step_s-0.0025

Parameters: density_kg_per_m3 = 1000, shear_modulus_Pa = 5e+05, poisson_ratio = 0.4, gravity_m_per_s2 = 2, flag_length_m = 0.35, flag_height_m = 0.02, cylinder_radius_m = 0.05, element_size_mm = 2.5, time_step_s = 0.0025

Derived: beam_frequency_Hz = 1.077, steps_per_linear_period = 371.5, height_over_length = 0.05714

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-S3 | 0 % | <= 1 | 1 | **PASS** | [point.json](points/p02_time_step_s-0.0025/point.json) |
| REQ-S4 | 0 % | <= 1 | 1 | **PASS** | [point.json](points/p02_time_step_s-0.0025/point.json) |
| REQ-S5 | 0 % | <= 2 | 2 | **PASS** | [point.json](points/p02_time_step_s-0.0025/point.json) |
| REQ-S6 | 0.1576 % | <= 1 | 0.842 | **PASS (unverified)** | [point.json](points/p02_time_step_s-0.0025/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| integrator_small_amplitude | |frequency of a gravity/1000 run - linear modal f1| / f1 (the time integrator alone) | 9.39e-04 | 2e-03 | PASS |
| returns_to_start | max uy(A) over the last period / amplitude (undamped: the flag swings back to its undeformed height) | 4.50e-03 | 1e-02 | PASS |
| periodic_troughs | spread of the trough depths of uy(A) over all periods / mean depth | 2.19e-04 | 1e-02 | PASS |
| periodic_periods | spread of the periods / mean period | 9.45e-04 | 1e-02 | PASS |
| frequency_reference | |f1 modal - Euler-Bernoulli cantilever| / beam value (model form) | 4.13e-03 | 2e-02 | PASS |
| periods_seen | shortfall of full periods before the last one (needs >= 3) | 0.00e+00 | 5e-01 | PASS |
| steps_per_period (validity) | 50 / time steps per linear period (below 1: at least 50 steps a period, period error of the trapezoidal rule about (2 pi / 50)^2 / 12 = 0.13 %) | 1.35e-01 | 1e+00 | PASS |

![p02_time_step_s-0.0025 response](points/p02_time_step_s-0.0025/response.png)

### p03_time_step_s-0.00125

Parameters: density_kg_per_m3 = 1000, shear_modulus_Pa = 5e+05, poisson_ratio = 0.4, gravity_m_per_s2 = 2, flag_length_m = 0.35, flag_height_m = 0.02, cylinder_radius_m = 0.05, element_size_mm = 2.5, time_step_s = 0.00125

Derived: beam_frequency_Hz = 1.077, steps_per_linear_period = 743, height_over_length = 0.05714

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-S3 | 0.05096 % | <= 1 | 0.949 | **PASS (unverified)** | [point.json](points/p03_time_step_s-0.00125/point.json) |
| REQ-S4 | 0 % | <= 1 | 1 | **PASS (unverified)** | [point.json](points/p03_time_step_s-0.00125/point.json) |
| REQ-S5 | 0 % | <= 2 | 2 | **PASS (unverified)** | [point.json](points/p03_time_step_s-0.00125/point.json) |
| REQ-S6 | 0.1422 % | <= 1 | 0.858 | **PASS (unverified)** | [point.json](points/p03_time_step_s-0.00125/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| integrator_small_amplitude | |frequency of a gravity/1000 run - linear modal f1| / f1 (the time integrator alone) | 3.39e-03 | 2e-03 | FAIL |
| returns_to_start | max uy(A) over the last period / amplitude (undamped: the flag swings back to its undeformed height) | 7.41e-04 | 1e-02 | PASS |
| periodic_troughs | spread of the trough depths of uy(A) over all periods / mean depth | 9.63e-04 | 1e-02 | PASS |
| periodic_periods | spread of the periods / mean period | 3.75e-03 | 1e-02 | PASS |
| frequency_reference | |f1 modal - Euler-Bernoulli cantilever| / beam value (model form) | 4.13e-03 | 2e-02 | PASS |
| periods_seen | shortfall of full periods before the last one (needs >= 3) | 0.00e+00 | 5e-01 | PASS |
| steps_per_period (validity) | 50 / time steps per linear period (below 1: at least 50 steps a period, period error of the trapezoidal rule about (2 pi / 50)^2 / 12 = 0.13 %) | 6.73e-02 | 1e+00 | PASS |

![p03_time_step_s-0.00125 response](points/p03_time_step_s-0.00125/response.png)

## Limitations

- Time-step convergence only; the spatial error is taken from the static mesh study at the same size.
- The published rows are not labelled with their time step, so the reference is a band, not a value.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

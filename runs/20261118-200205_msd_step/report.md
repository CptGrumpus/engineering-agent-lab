# Engineering review report: msd_step

- **Run:** `20261118-200205_msd_step`
- **Generated:** 2026-11-19T14:00:58+00:00
- **Case file SHA-256:** `01e4ff45c2d7b40e058a6106890a8d7ede89937a129b0bf3d94c4835431804fd`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2; Windows-11-10.0.26100-SP0
- **Code version:** git `none`
- **Simulation status:** completed
- **Verification status:** PASS

## Scope

1-DOF mass-spring-damper subjected to a 10 N step force; damping-ratio sweep against overshoot, settling-time, and deflection requirements.

**Assumptions**

- Single translational degree of freedom; no gravity or preload.
- Linear spring and viscous damper, constant over the full stroke.
- Ideal step force applied at t = 0 from rest (x = 0, v = 0).
- Rigid mass; no compliance or friction elsewhere in the load path.

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-001 | Peak overshoot of the step response shall not exceed 20 %. | `overshoot_pct` | <= 20 % |
| REQ-002 | The response shall settle within +/-2 % of its final value in 0.5 s or less. | `settling_time_s` | <= 0.5 s |
| REQ-003 | Static deflection under the 10 N load shall not exceed 12 mm. | `static_deflection_mm` | <= 12 mm |

## Summary across points

| Point | damping_ratio | REQ-001 | REQ-002 | REQ-003 | Checks |
|---|---|---|---|---|---|
| p00_damping_ratio-0.1 | 0.1 | 72.94 %: **FAIL** | 1.214 s: **FAIL** | 9.999 mm: **PASS** | 6/6 PASS |
| p01_damping_ratio-0.3 | 0.3 | 37.23 %: **FAIL** | 0.3552 s: **PASS** | 10 mm: **PASS** | 6/6 PASS |
| p02_damping_ratio-0.5 | 0.5 | 16.3 %: **PASS** | 0.2554 s: **PASS** | 10 mm: **PASS** | 6/6 PASS |
| p03_damping_ratio-0.7 | 0.7 | 4.599 %: **PASS** | 0.1891 s: **PASS** | 10 mm: **PASS** | 6/6 PASS |
| p04_damping_ratio-1 | 1 | 1.915e-08 %: **PASS** | 0.1845 s: **PASS** | 10 mm: **PASS** | 6/6 PASS |
| p05_damping_ratio-2 | 2 | 2.301e-09 %: **PASS** | 0.4705 s: **PASS** | 10 mm: **PASS** | 6/6 PASS |

![Requirement metrics across the sweep](sweep.png)

## Point details

### p00_damping_ratio-0.1

Parameters: mass_kg = 1, stiffness_N_per_m = 1000, damping_ratio = 0.1, step_force_N = 10

Derived: damping_N_s_per_m = 6.325, natural_frequency_rad_per_s = 31.62, natural_frequency_Hz = 5.033

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-001 | 72.94 % | <= 20 | -52.9 | **FAIL** | [point.json](points/p00_damping_ratio-0.1/point.json) |
| REQ-002 | 1.214 s | <= 0.5 | -0.714 | **FAIL** | [point.json](points/p00_damping_ratio-0.1/point.json) |
| REQ-003 | 9.999 mm | <= 12 | 2 | **PASS** | [point.json](points/p00_damping_ratio-0.1/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| reference_agreement | max |x_num - x_ref| / (F/k) over the full time history | 2.17e-09 | 1e-06 | PASS |
| overshoot_reference | |overshoot_num - overshoot_closed_form| in percentage points | 1.31e-02 | 5e-02 | PASS |
| settling_reference | |settling_num - settling of analytical curve| in s | 0.00e+00 | 1e-03 | PASS |
| steady_state | |x(t_end) - F/k| / (F/k) | 7.61e-05 | 1e-03 | PASS |
| energy_balance | |W_in - (KE + PE + E_dissipated)| / W_in | 2.03e-10 | 1e-04 | PASS |
| solver_convergence | max |x(rtol, atol) - x(rtol/100, atol/100)| / (F/k) | 2.17e-09 | 1e-06 | PASS |

![p00_damping_ratio-0.1 response](points/p00_damping_ratio-0.1/response.png)

### p01_damping_ratio-0.3

Parameters: mass_kg = 1, stiffness_N_per_m = 1000, damping_ratio = 0.3, step_force_N = 10

Derived: damping_N_s_per_m = 18.97, natural_frequency_rad_per_s = 31.62, natural_frequency_Hz = 5.033

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-001 | 37.23 % | <= 20 | -17.2 | **FAIL** | [point.json](points/p01_damping_ratio-0.3/point.json) |
| REQ-002 | 0.3552 s | <= 0.5 | 0.145 | **PASS** | [point.json](points/p01_damping_ratio-0.3/point.json) |
| REQ-003 | 10 mm | <= 12 | 2 | **PASS** | [point.json](points/p01_damping_ratio-0.3/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| reference_agreement | max |x_num - x_ref| / (F/k) over the full time history | 1.12e-09 | 1e-06 | PASS |
| overshoot_reference | |overshoot_num - overshoot_closed_form| in percentage points | 3.41e-05 | 5e-02 | PASS |
| settling_reference | |settling_num - settling of analytical curve| in s | 0.00e+00 | 1e-03 | PASS |
| steady_state | |x(t_end) - F/k| / (F/k) | 2.77e-13 | 1e-03 | PASS |
| energy_balance | |W_in - (KE + PE + E_dissipated)| / W_in | 8.21e-11 | 1e-04 | PASS |
| solver_convergence | max |x(rtol, atol) - x(rtol/100, atol/100)| / (F/k) | 1.12e-09 | 1e-06 | PASS |

![p01_damping_ratio-0.3 response](points/p01_damping_ratio-0.3/response.png)

### p02_damping_ratio-0.5

Parameters: mass_kg = 1, stiffness_N_per_m = 1000, damping_ratio = 0.5, step_force_N = 10

Derived: damping_N_s_per_m = 31.62, natural_frequency_rad_per_s = 31.62, natural_frequency_Hz = 5.033

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-001 | 16.3 % | <= 20 | 3.7 | **PASS** | [point.json](points/p02_damping_ratio-0.5/point.json) |
| REQ-002 | 0.2554 s | <= 0.5 | 0.245 | **PASS** | [point.json](points/p02_damping_ratio-0.5/point.json) |
| REQ-003 | 10 mm | <= 12 | 2 | **PASS** | [point.json](points/p02_damping_ratio-0.5/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| reference_agreement | max |x_num - x_ref| / (F/k) over the full time history | 5.07e-10 | 1e-06 | PASS |
| overshoot_reference | |overshoot_num - overshoot_closed_form| in percentage points | 1.78e-06 | 5e-02 | PASS |
| settling_reference | |settling_num - settling of analytical curve| in s | 0.00e+00 | 1e-03 | PASS |
| steady_state | |x(t_end) - F/k| / (F/k) | 1.62e-13 | 1e-03 | PASS |
| energy_balance | |W_in - (KE + PE + E_dissipated)| / W_in | 5.96e-12 | 1e-04 | PASS |
| solver_convergence | max |x(rtol, atol) - x(rtol/100, atol/100)| / (F/k) | 5.08e-10 | 1e-06 | PASS |

![p02_damping_ratio-0.5 response](points/p02_damping_ratio-0.5/response.png)

### p03_damping_ratio-0.7

Parameters: mass_kg = 1, stiffness_N_per_m = 1000, damping_ratio = 0.7, step_force_N = 10

Derived: damping_N_s_per_m = 44.27, natural_frequency_rad_per_s = 31.62, natural_frequency_Hz = 5.033

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-001 | 4.599 % | <= 20 | 15.4 | **PASS** | [point.json](points/p03_damping_ratio-0.7/point.json) |
| REQ-002 | 0.1891 s | <= 0.5 | 0.311 | **PASS** | [point.json](points/p03_damping_ratio-0.7/point.json) |
| REQ-003 | 10 mm | <= 12 | 2 | **PASS** | [point.json](points/p03_damping_ratio-0.7/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| reference_agreement | max |x_num - x_ref| / (F/k) over the full time history | 1.60e-09 | 1e-06 | PASS |
| overshoot_reference | |overshoot_num - overshoot_closed_form| in percentage points | 3.35e-07 | 5e-02 | PASS |
| settling_reference | |settling_num - settling of analytical curve| in s | 2.78e-17 | 1e-03 | PASS |
| steady_state | |x(t_end) - F/k| / (F/k) | 9.02e-15 | 1e-03 | PASS |
| energy_balance | |W_in - (KE + PE + E_dissipated)| / W_in | 1.60e-11 | 1e-04 | PASS |
| solver_convergence | max |x(rtol, atol) - x(rtol/100, atol/100)| / (F/k) | 1.60e-09 | 1e-06 | PASS |

![p03_damping_ratio-0.7 response](points/p03_damping_ratio-0.7/response.png)

### p04_damping_ratio-1

Parameters: mass_kg = 1, stiffness_N_per_m = 1000, damping_ratio = 1, step_force_N = 10

Derived: damping_N_s_per_m = 63.25, natural_frequency_rad_per_s = 31.62, natural_frequency_Hz = 5.033

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-001 | 1.915e-08 % | <= 20 | 20 | **PASS** | [point.json](points/p04_damping_ratio-1/point.json) |
| REQ-002 | 0.1845 s | <= 0.5 | 0.316 | **PASS** | [point.json](points/p04_damping_ratio-1/point.json) |
| REQ-003 | 10 mm | <= 12 | 2 | **PASS** | [point.json](points/p04_damping_ratio-1/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| reference_agreement | max |x_num - x_ref| / (F/k) over the full time history | 2.24e-10 | 1e-06 | PASS |
| overshoot_reference | |overshoot_num - overshoot_closed_form| in percentage points | 1.91e-08 | 5e-02 | PASS |
| settling_reference | |settling_num - settling of analytical curve| in s | 0.00e+00 | 1e-03 | PASS |
| steady_state | |x(t_end) - F/k| / (F/k) | 6.42e-15 | 1e-03 | PASS |
| energy_balance | |W_in - (KE + PE + E_dissipated)| / W_in | 1.71e-12 | 1e-04 | PASS |
| solver_convergence | max |x(rtol, atol) - x(rtol/100, atol/100)| / (F/k) | 2.24e-10 | 1e-06 | PASS |

![p04_damping_ratio-1 response](points/p04_damping_ratio-1/response.png)

### p05_damping_ratio-2

Parameters: mass_kg = 1, stiffness_N_per_m = 1000, damping_ratio = 2, step_force_N = 10

Derived: damping_N_s_per_m = 126.5, natural_frequency_rad_per_s = 31.62, natural_frequency_Hz = 5.033

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-001 | 2.301e-09 % | <= 20 | 20 | **PASS** | [point.json](points/p05_damping_ratio-2/point.json) |
| REQ-002 | 0.4705 s | <= 0.5 | 0.0295 | **PASS** | [point.json](points/p05_damping_ratio-2/point.json) |
| REQ-003 | 10 mm | <= 12 | 2 | **PASS** | [point.json](points/p05_damping_ratio-2/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| reference_agreement | max |x_num - x_ref| / (F/k) over the full time history | 6.85e-10 | 1e-06 | PASS |
| overshoot_reference | |overshoot_num - overshoot_closed_form| in percentage points | 2.30e-09 | 5e-02 | PASS |
| settling_reference | |settling_num - settling of analytical curve| in s | 5.55e-17 | 1e-03 | PASS |
| steady_state | |x(t_end) - F/k| / (F/k) | 9.01e-12 | 1e-03 | PASS |
| energy_balance | |W_in - (KE + PE + E_dissipated)| / W_in | 5.16e-11 | 1e-04 | PASS |
| solver_convergence | max |x(rtol, atol) - x(rtol/100, atol/100)| / (F/k) | 6.85e-10 | 1e-06 | PASS |

![p05_damping_ratio-2 response](points/p05_damping_ratio-2/response.png)

## Limitations

- Synthetic parameters; not calibrated to any physical part.
- Checks establish numerical verification only. No physical validation data exists for this case.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

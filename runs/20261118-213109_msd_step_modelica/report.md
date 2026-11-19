# Engineering review report: msd_step_modelica

- **Run:** `20261118-213109_msd_step_modelica`
- **Generated:** 2026-11-19T14:01:00+00:00
- **Case file SHA-256:** `73ed4ffbf0aab71ed5c59e87a6db90c0692bb018a4665405aef2429694edee1d`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2; Windows-11-10.0.26100-SP0
- **Tools:** omc OpenModelica v1.26.3 (64-bit); Modelica Standard Library 4.1.0
- **Code version:** git `none`
- **Simulation status:** failed
- **Verification status:** FAIL

> **Warning:** verification did not pass for every point. Requirement verdicts marked *(unverified)* are not supported by evidence and must not be used for acceptance.

## Scope

1-DOF mass-spring-damper subjected to a 10 N step force, modelled with Modelica Standard Library translational components and solved by OpenModelica (DASSL); damping-ratio sweep against the same requirements as the SciPy case, plus a cross-tool comparison.

**Assumptions**

- Single translational degree of freedom; no gravity or preload.
- Linear spring and viscous damper, constant over the full stroke.
- Constant force applied at t = 0 from rest (x = 0, v = 0).
- Rigid mass (MSL Mass with L = 0); no compliance or friction elsewhere in the load path.

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-001 | Peak overshoot of the step response shall not exceed 20 %. | `overshoot_pct` | <= 20 % |
| REQ-002 | The response shall settle within +/-2 % of its final value in 0.5 s or less. | `settling_time_s` | <= 0.5 s |
| REQ-003 | Static deflection under the 10 N load shall not exceed 12 mm. | `static_deflection_mm` | <= 12 mm |

## Summary across points

| Point | damping_ratio | REQ-001 | REQ-002 | REQ-003 | Checks |
|---|---|---|---|---|---|
| p00_damping_ratio-0.1 | 0.1 | - %: **NO RESULT** | - s: **NO RESULT** | - mm: **NO RESULT** | 0/0 NOT_RUN |
| p01_damping_ratio-0.3 | 0.3 | - %: **NO RESULT** | - s: **NO RESULT** | - mm: **NO RESULT** | 0/0 NOT_RUN |
| p02_damping_ratio-0.5 | 0.5 | - %: **NO RESULT** | - s: **NO RESULT** | - mm: **NO RESULT** | 0/0 NOT_RUN |
| p03_damping_ratio-0.7 | 0.7 | - %: **NO RESULT** | - s: **NO RESULT** | - mm: **NO RESULT** | 0/0 NOT_RUN |
| p04_damping_ratio-1 | 1 | - %: **NO RESULT** | - s: **NO RESULT** | - mm: **NO RESULT** | 0/0 NOT_RUN |
| p05_damping_ratio-2 | 2 | - %: **NO RESULT** | - s: **NO RESULT** | - mm: **NO RESULT** | 0/0 NOT_RUN |

## Point details

### p00_damping_ratio-0.1

Parameters: mass_kg = 1, stiffness_N_per_m = 1000, damping_ratio = 0.1, step_force_N = 10

Derived: damping_N_s_per_m = 6.325, natural_frequency_rad_per_s = 31.62, natural_frequency_Hz = 5.033

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-001 | - % | <= 20 | - | **NO RESULT** | [point.json](points/p00_damping_ratio-0.1/point.json) |
| REQ-002 | - s | <= 0.5 | - | **NO RESULT** | [point.json](points/p00_damping_ratio-0.1/point.json) |
| REQ-003 | - mm | <= 12 | - | **NO RESULT** | [point.json](points/p00_damping_ratio-0.1/point.json) |

No verification checks recorded (status: NOT_RUN).

### p01_damping_ratio-0.3

Parameters: mass_kg = 1, stiffness_N_per_m = 1000, damping_ratio = 0.3, step_force_N = 10

Derived: damping_N_s_per_m = 18.97, natural_frequency_rad_per_s = 31.62, natural_frequency_Hz = 5.033

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-001 | - % | <= 20 | - | **NO RESULT** | [point.json](points/p01_damping_ratio-0.3/point.json) |
| REQ-002 | - s | <= 0.5 | - | **NO RESULT** | [point.json](points/p01_damping_ratio-0.3/point.json) |
| REQ-003 | - mm | <= 12 | - | **NO RESULT** | [point.json](points/p01_damping_ratio-0.3/point.json) |

No verification checks recorded (status: NOT_RUN).

### p02_damping_ratio-0.5

Parameters: mass_kg = 1, stiffness_N_per_m = 1000, damping_ratio = 0.5, step_force_N = 10

Derived: damping_N_s_per_m = 31.62, natural_frequency_rad_per_s = 31.62, natural_frequency_Hz = 5.033

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-001 | - % | <= 20 | - | **NO RESULT** | [point.json](points/p02_damping_ratio-0.5/point.json) |
| REQ-002 | - s | <= 0.5 | - | **NO RESULT** | [point.json](points/p02_damping_ratio-0.5/point.json) |
| REQ-003 | - mm | <= 12 | - | **NO RESULT** | [point.json](points/p02_damping_ratio-0.5/point.json) |

No verification checks recorded (status: NOT_RUN).

### p03_damping_ratio-0.7

Parameters: mass_kg = 1, stiffness_N_per_m = 1000, damping_ratio = 0.7, step_force_N = 10

Derived: damping_N_s_per_m = 44.27, natural_frequency_rad_per_s = 31.62, natural_frequency_Hz = 5.033

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-001 | - % | <= 20 | - | **NO RESULT** | [point.json](points/p03_damping_ratio-0.7/point.json) |
| REQ-002 | - s | <= 0.5 | - | **NO RESULT** | [point.json](points/p03_damping_ratio-0.7/point.json) |
| REQ-003 | - mm | <= 12 | - | **NO RESULT** | [point.json](points/p03_damping_ratio-0.7/point.json) |

No verification checks recorded (status: NOT_RUN).

### p04_damping_ratio-1

Parameters: mass_kg = 1, stiffness_N_per_m = 1000, damping_ratio = 1, step_force_N = 10

Derived: damping_N_s_per_m = 63.25, natural_frequency_rad_per_s = 31.62, natural_frequency_Hz = 5.033

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-001 | - % | <= 20 | - | **NO RESULT** | [point.json](points/p04_damping_ratio-1/point.json) |
| REQ-002 | - s | <= 0.5 | - | **NO RESULT** | [point.json](points/p04_damping_ratio-1/point.json) |
| REQ-003 | - mm | <= 12 | - | **NO RESULT** | [point.json](points/p04_damping_ratio-1/point.json) |

No verification checks recorded (status: NOT_RUN).

### p05_damping_ratio-2

Parameters: mass_kg = 1, stiffness_N_per_m = 1000, damping_ratio = 2, step_force_N = 10

Derived: damping_N_s_per_m = 126.5, natural_frequency_rad_per_s = 31.62, natural_frequency_Hz = 5.033

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-001 | - % | <= 20 | - | **NO RESULT** | [point.json](points/p05_damping_ratio-2/point.json) |
| REQ-002 | - s | <= 0.5 | - | **NO RESULT** | [point.json](points/p05_damping_ratio-2/point.json) |
| REQ-003 | - mm | <= 12 | - | **NO RESULT** | [point.json](points/p05_damping_ratio-2/point.json) |

No verification checks recorded (status: NOT_RUN).

## Limitations

- Synthetic parameters; not calibrated to any physical part.
- Checks establish numerical verification only. No physical validation data exists for this case.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

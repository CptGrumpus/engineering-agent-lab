# Engineering review report: motor_prius_ornl_oc_mesh_r3

- **Run:** `20261122-014658_motor_prius_ornl_oc_mesh_r3`
- **Generated:** 2026-11-22T06:56:15+00:00
- **Case file SHA-256:** `04d36e4a90129692ed7cfd944af8cf4a0efaffb87cb5628a37657d423b8b8e00`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Tools:** pyleecan 1.5.2; SciDataTool 2.5.0; numpy_pyleecan_env 2.5.5
- **Code version:** git `cbbbac46454d96c28a08c4b8db37d3f4cd414b3d` (uncommitted changes present)
- **Simulation status:** completed
- **Verification status:** FAIL

> **Warning:** verification did not pass for every point. Requirement verdicts marked *(unverified)* are not supported by evidence and must not be used for acceptance.

## Scope

2004 Toyota Prius traction motor rebuilt from ORNL/TM-2005/33 Fig. 21 (radii, air gap 0.775 mm, slot, pocket thickness and position), ORNL/TM-2004/120 (bridge) and ORNL/TM-2004/137 Fig. 14 (magnet B-H line), laminations M330-35A (stand-in grade), at open circuit, 1000 rpm; Pyleecan + FEMM 4.2 magnetostatics over one electrical period (48 steps), mesh fineness 2 / 4 / 8; back-EMF and the uncontrolled-generator voltage at top speed.

**Assumptions**

- 2D magnetostatics (FEMM), no end effects: the stack (83.8 mm) is long against the air gap (0.775 mm), but end-winding leakage and axial fringing are not modelled.
- Stator, rotor, slot and pocket thickness from ORNL/TM-2005/33 Fig. 21; bridge 1.45 mm from ORNL/TM-2004/120; magnet Br 1.243 T and recoil permeability 1.129 from ORNL/TM-2004/137 Fig. 14 (temperature not stated, taken as 20 C); magnet width and winding still Pyleecan's.
- Laminations M330-35A, a stand-in: ORNL gives the thickness (0.36 mm) but not the grade. B-H curve from Tata Steel's typical data (50 Hz) up to 1.8 T, extrapolated above (saturation polarization 2.0 T).
- Magnet temperature 20 C; Br falls about 0.1 %/K, so a hot motor has a lower back-EMF (stated, not modelled here).
- Maximum speed 6000 rpm, the commonly published rating for this motor; ORNL's design report tabulates ratings only up to base speed.

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-M1 | With the inverter not switching (a fault at top speed), the line-to-line back-EMF peak at 6000 rpm shall not exceed the 500 V maximum bus voltage. | `back_emf_LL_peak_at_max_speed_V` | <= 500 V |

## Summary across points

| Point | mesh_fineness | REQ-M1 | Checks |
|---|---|---|---|
| p00_mesh_fineness-2 | 2 | 1039 V: **FAIL (unverified)** | 5/5 PASS |
| p01_mesh_fineness-4 | 4 | 1040 V: **FAIL (unverified)** | 5/5 PASS |
| p02_mesh_fineness-8 | 8 | 1040 V: **FAIL (unverified)** | 5/5 PASS |

## Run-level checks

Checks that use several points together (for example mesh convergence).

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| discretization_back_emf_LL_peak_at_max_speed_V | relative discretization uncertainty of back_emf_LL_peak_at_max_speed_V, anomalous: observed order 3.79 is far above the design order 2, so the solutions are not in the asymptotic range (singularity or coincidence); no estimate | inf | 0.01 | FAIL |
| discretization_lambda1_Wb | relative discretization uncertainty of lambda1_Wb, monotone (R = 0.737): GCI_fine, observed order 0.44, extrapolated 0.215856 | 0.00164 | 0.01 | PASS |

A failed run-level check withholds the verdicts of requirements on `back_emf_LL_peak_at_max_speed_V` at every point: they are marked *(unverified)* in the table above.

![Requirement metrics across the sweep](sweep.png)

## Point details

### p00_mesh_fineness-2

Parameters: machine = Toyota_Prius_ORNL.json, speed_rpm = 1000, id_A = 0, iq_A = 0, mesh_fineness = 2, steps_per_period = 48, angle_points = 2048, max_speed_rpm = 6000, bus_voltage_V = 500, rated_torque_Nm = 400

Derived: speed_ratio_to_max = 6

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-M1 | 1039 V | <= 500 | -539 | **FAIL (unverified)** | [point.json](points/p00_mesh_fineness-2/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| phase_symmetry | spread of the three phases' fundamental flux linkage / mean | 1.90e-04 | 1e-03 | PASS |
| phase_shift | max |phase shift between phases - 120 deg| (deg) | 2.43e-02 | 5e-01 | PASS |
| winding_theory | |2 N k_w1 B_1 R L / p from the air-gap field - FEMM coil flux linkage| / FEMM (model form: mid-gap sampling, slot openings, leakage) | 2.10e-03 | 2e-02 | PASS |
| open_circuit_torque | |mean torque at zero current| / rated torque (no net torque without current) | 2.06e-05 | 1e-03 | PASS |
| time_resolution (validity) | 48 / steps per electrical period (below 1: at least 48) | 1.00e+00 | 1e+00 | PASS |

![p00_mesh_fineness-2 response](points/p00_mesh_fineness-2/response.png)

### p01_mesh_fineness-4

Parameters: machine = Toyota_Prius_ORNL.json, speed_rpm = 1000, id_A = 0, iq_A = 0, mesh_fineness = 4, steps_per_period = 48, angle_points = 2048, max_speed_rpm = 6000, bus_voltage_V = 500, rated_torque_Nm = 400

Derived: speed_ratio_to_max = 6

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-M1 | 1040 V | <= 500 | -540 | **FAIL (unverified)** | [point.json](points/p01_mesh_fineness-4/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| phase_symmetry | spread of the three phases' fundamental flux linkage / mean | 5.68e-05 | 1e-03 | PASS |
| phase_shift | max |phase shift between phases - 120 deg| (deg) | 7.77e-03 | 5e-01 | PASS |
| winding_theory | |2 N k_w1 B_1 R L / p from the air-gap field - FEMM coil flux linkage| / FEMM (model form: mid-gap sampling, slot openings, leakage) | 2.09e-03 | 2e-02 | PASS |
| open_circuit_torque | |mean torque at zero current| / rated torque (no net torque without current) | 3.55e-06 | 1e-03 | PASS |
| time_resolution (validity) | 48 / steps per electrical period (below 1: at least 48) | 1.00e+00 | 1e+00 | PASS |

![p01_mesh_fineness-4 response](points/p01_mesh_fineness-4/response.png)

### p02_mesh_fineness-8

Parameters: machine = Toyota_Prius_ORNL.json, speed_rpm = 1000, id_A = 0, iq_A = 0, mesh_fineness = 8, steps_per_period = 48, angle_points = 2048, max_speed_rpm = 6000, bus_voltage_V = 500, rated_torque_Nm = 400

Derived: speed_ratio_to_max = 6

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-M1 | 1040 V | <= 500 | -540 | **FAIL (unverified)** | [point.json](points/p02_mesh_fineness-8/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| phase_symmetry | spread of the three phases' fundamental flux linkage / mean | 1.04e-04 | 1e-03 | PASS |
| phase_shift | max |phase shift between phases - 120 deg| (deg) | 1.51e-02 | 5e-01 | PASS |
| winding_theory | |2 N k_w1 B_1 R L / p from the air-gap field - FEMM coil flux linkage| / FEMM (model form: mid-gap sampling, slot openings, leakage) | 2.01e-03 | 2e-02 | PASS |
| open_circuit_torque | |mean torque at zero current| / rated torque (no net torque without current) | 3.93e-06 | 1e-03 | PASS |
| time_resolution (validity) | 48 / steps per electrical period (below 1: at least 48) | 1.00e+00 | 1e+00 | PASS |

![p02_mesh_fineness-8 response](points/p02_mesh_fineness-8/response.png)

## Limitations

- No test data in this case: the ORNL comparison is a separate, blind step.
- The magnet fills the pocket thickness (HoleM50); TM-2004/120 gives a thinner magnet (5.31 mm), not modelled.
- Line-to-line peak from the phase flux linkages with their harmonics; the inverter's own clamping is not modelled.
- The real lamination grade is unknown; the bracketing grades (M250-35A, a high-strength rotor grade) are separate cases.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

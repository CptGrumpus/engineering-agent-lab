# Engineering review report: motor_prius_torque_current

- **Run:** `20261122-000853_motor_prius_torque_current`
- **Generated:** 2026-11-22T06:36:52+00:00
- **Case file SHA-256:** `17cacbbe95cf5734026bf4bea5a39904227bccd649499e05d602dda93fb7afc9`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Tools:** pyleecan 1.5.2; SciDataTool 2.5.0; numpy_pyleecan_env 2.5.5
- **Code version:** git `bceac0d6e02eec7096c2413bcd10c0b2b6b576a1` (uncommitted changes present)
- **Simulation status:** completed
- **Verification status:** PASS

## Scope

2004 Toyota Prius traction motor (our machine from ORNL Fig. 21), MTPA torque at 50-350 A rms, 1000 rpm; Pyleecan + FEMM 4.2 magnetostatics, current angle 0-70 deg from the q axis, mesh fineness 4.

**Assumptions**

- 2D magnetostatics (FEMM), no end effects; torque is the mean of FEMM's stress-tensor torque over one electrical period.
- Magnets, magnet pockets and materials as in models/motor/Toyota_Prius_ORNL.json.
- Magnet temperature 20 C.
- Current-density limit 25 A/mm^2 rms on 0.84 x 143.0 mm^2 of copper per slot (stated assumption).

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-M3 | Each operating point of the torque curve shall stay within the 25 A/mm^2 rms copper current-density limit (marks which points of the curve the motor can sustain for a short time). | `current_density_rms_A_per_mm2` | <= 25 A/mm^2 |

## Summary across points

| Point | current_rms_A | REQ-M3 | Checks |
|---|---|---|---|
| p00_current_rms_A-50 | 50 | 3.746 A/mm^2: **PASS** | 5/5 PASS |
| p01_current_rms_A-100 | 100 | 7.493 A/mm^2: **PASS** | 5/5 PASS |
| p02_current_rms_A-150 | 150 | 11.24 A/mm^2: **PASS** | 5/5 PASS |
| p03_current_rms_A-200 | 200 | 14.99 A/mm^2: **PASS** | 5/5 PASS |
| p04_current_rms_A-250 | 250 | 18.73 A/mm^2: **PASS** | 5/5 PASS |
| p05_current_rms_A-300 | 300 | 22.48 A/mm^2: **PASS** | 5/5 PASS |
| p06_current_rms_A-350 | 350 | 26.22 A/mm^2: **FAIL** | 5/5 PASS |

![Requirement metrics across the sweep](sweep.png)

## Point details

### p00_current_rms_A-50

Parameters: machine = Toyota_Prius_ORNL.json, speed_rpm = 1000, current_rms_A = 50, angle_min_deg = 0, angle_max_deg = 70, angle_steps = 8, mesh_fineness = 4, steps_per_period = 48, angle_points = 2048, rated_torque_Nm = 400, slot_fill = 0.84, slot_area_mm2 = 143, turns_per_slot = 9

Derived: current_density_rms_A_per_mm2 = 3.746

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-M3 | 3.746 A/mm^2 | <= 25 | 21.3 | **PASS** | [point.json](points/p00_current_rms_A-50/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| power_balance | max over current angles of |mean(sum i dphi/dt) - mean torque x omega_m| / (mean torque x omega_m): energy conservation, an independent route to FEMM's stress-tensor torque | 1.28e-03 | 2e-02 | PASS |
| current_amplitude | max |imposed phase current fundamental - sqrt(2) x requested rms| / peak (Pyleecan's dq currents are rms) | 2.01e-16 | 1e-03 | PASS |
| phase_symmetry_load | max over angles of the spread of the three phases' fundamental flux linkage / mean, under load | 4.66e-05 | 2e-03 | PASS |
| mtpa_bracketed (validity) | maximum torque inside the angle sweep (0 = yes) | 0.00e+00 | 0e+00 | PASS |
| time_resolution (validity) | 48 / steps per electrical period (below 1: at least 48) | 1.00e+00 | 1e+00 | PASS |

![p00_current_rms_A-50 response](points/p00_current_rms_A-50/response.png)

### p01_current_rms_A-100

Parameters: machine = Toyota_Prius_ORNL.json, speed_rpm = 1000, current_rms_A = 100, angle_min_deg = 0, angle_max_deg = 70, angle_steps = 8, mesh_fineness = 4, steps_per_period = 48, angle_points = 2048, rated_torque_Nm = 400, slot_fill = 0.84, slot_area_mm2 = 143, turns_per_slot = 9

Derived: current_density_rms_A_per_mm2 = 7.493

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-M3 | 7.493 A/mm^2 | <= 25 | 17.5 | **PASS** | [point.json](points/p01_current_rms_A-100/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| power_balance | max over current angles of |mean(sum i dphi/dt) - mean torque x omega_m| / (mean torque x omega_m): energy conservation, an independent route to FEMM's stress-tensor torque | 6.29e-04 | 2e-02 | PASS |
| current_amplitude | max |imposed phase current fundamental - sqrt(2) x requested rms| / peak (Pyleecan's dq currents are rms) | 2.01e-16 | 1e-03 | PASS |
| phase_symmetry_load | max over angles of the spread of the three phases' fundamental flux linkage / mean, under load | 1.36e-04 | 2e-03 | PASS |
| mtpa_bracketed (validity) | maximum torque inside the angle sweep (0 = yes) | 0.00e+00 | 0e+00 | PASS |
| time_resolution (validity) | 48 / steps per electrical period (below 1: at least 48) | 1.00e+00 | 1e+00 | PASS |

![p01_current_rms_A-100 response](points/p01_current_rms_A-100/response.png)

### p02_current_rms_A-150

Parameters: machine = Toyota_Prius_ORNL.json, speed_rpm = 1000, current_rms_A = 150, angle_min_deg = 0, angle_max_deg = 70, angle_steps = 8, mesh_fineness = 4, steps_per_period = 48, angle_points = 2048, rated_torque_Nm = 400, slot_fill = 0.84, slot_area_mm2 = 143, turns_per_slot = 9

Derived: current_density_rms_A_per_mm2 = 11.24

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-M3 | 11.24 A/mm^2 | <= 25 | 13.8 | **PASS** | [point.json](points/p02_current_rms_A-150/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| power_balance | max over current angles of |mean(sum i dphi/dt) - mean torque x omega_m| / (mean torque x omega_m): energy conservation, an independent route to FEMM's stress-tensor torque | 3.58e-04 | 2e-02 | PASS |
| current_amplitude | max |imposed phase current fundamental - sqrt(2) x requested rms| / peak (Pyleecan's dq currents are rms) | 4.02e-16 | 1e-03 | PASS |
| phase_symmetry_load | max over angles of the spread of the three phases' fundamental flux linkage / mean, under load | 1.89e-04 | 2e-03 | PASS |
| mtpa_bracketed (validity) | maximum torque inside the angle sweep (0 = yes) | 0.00e+00 | 0e+00 | PASS |
| time_resolution (validity) | 48 / steps per electrical period (below 1: at least 48) | 1.00e+00 | 1e+00 | PASS |

![p02_current_rms_A-150 response](points/p02_current_rms_A-150/response.png)

### p03_current_rms_A-200

Parameters: machine = Toyota_Prius_ORNL.json, speed_rpm = 1000, current_rms_A = 200, angle_min_deg = 0, angle_max_deg = 70, angle_steps = 8, mesh_fineness = 4, steps_per_period = 48, angle_points = 2048, rated_torque_Nm = 400, slot_fill = 0.84, slot_area_mm2 = 143, turns_per_slot = 9

Derived: current_density_rms_A_per_mm2 = 14.99

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-M3 | 14.99 A/mm^2 | <= 25 | 10 | **PASS** | [point.json](points/p03_current_rms_A-200/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| power_balance | max over current angles of |mean(sum i dphi/dt) - mean torque x omega_m| / (mean torque x omega_m): energy conservation, an independent route to FEMM's stress-tensor torque | 3.30e-04 | 2e-02 | PASS |
| current_amplitude | max |imposed phase current fundamental - sqrt(2) x requested rms| / peak (Pyleecan's dq currents are rms) | 2.01e-16 | 1e-03 | PASS |
| phase_symmetry_load | max over angles of the spread of the three phases' fundamental flux linkage / mean, under load | 1.56e-04 | 2e-03 | PASS |
| mtpa_bracketed (validity) | maximum torque inside the angle sweep (0 = yes) | 0.00e+00 | 0e+00 | PASS |
| time_resolution (validity) | 48 / steps per electrical period (below 1: at least 48) | 1.00e+00 | 1e+00 | PASS |

![p03_current_rms_A-200 response](points/p03_current_rms_A-200/response.png)

### p04_current_rms_A-250

Parameters: machine = Toyota_Prius_ORNL.json, speed_rpm = 1000, current_rms_A = 250, angle_min_deg = 0, angle_max_deg = 70, angle_steps = 8, mesh_fineness = 4, steps_per_period = 48, angle_points = 2048, rated_torque_Nm = 400, slot_fill = 0.84, slot_area_mm2 = 143, turns_per_slot = 9

Derived: current_density_rms_A_per_mm2 = 18.73

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-M3 | 18.73 A/mm^2 | <= 25 | 6.27 | **PASS** | [point.json](points/p04_current_rms_A-250/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| power_balance | max over current angles of |mean(sum i dphi/dt) - mean torque x omega_m| / (mean torque x omega_m): energy conservation, an independent route to FEMM's stress-tensor torque | 4.10e-04 | 2e-02 | PASS |
| current_amplitude | max |imposed phase current fundamental - sqrt(2) x requested rms| / peak (Pyleecan's dq currents are rms) | 1.61e-16 | 1e-03 | PASS |
| phase_symmetry_load | max over angles of the spread of the three phases' fundamental flux linkage / mean, under load | 1.19e-04 | 2e-03 | PASS |
| mtpa_bracketed (validity) | maximum torque inside the angle sweep (0 = yes) | 0.00e+00 | 0e+00 | PASS |
| time_resolution (validity) | 48 / steps per electrical period (below 1: at least 48) | 1.00e+00 | 1e+00 | PASS |

![p04_current_rms_A-250 response](points/p04_current_rms_A-250/response.png)

### p05_current_rms_A-300

Parameters: machine = Toyota_Prius_ORNL.json, speed_rpm = 1000, current_rms_A = 300, angle_min_deg = 0, angle_max_deg = 70, angle_steps = 8, mesh_fineness = 4, steps_per_period = 48, angle_points = 2048, rated_torque_Nm = 400, slot_fill = 0.84, slot_area_mm2 = 143, turns_per_slot = 9

Derived: current_density_rms_A_per_mm2 = 22.48

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-M3 | 22.48 A/mm^2 | <= 25 | 2.52 | **PASS** | [point.json](points/p05_current_rms_A-300/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| power_balance | max over current angles of |mean(sum i dphi/dt) - mean torque x omega_m| / (mean torque x omega_m): energy conservation, an independent route to FEMM's stress-tensor torque | 8.91e-04 | 2e-02 | PASS |
| current_amplitude | max |imposed phase current fundamental - sqrt(2) x requested rms| / peak (Pyleecan's dq currents are rms) | 4.02e-16 | 1e-03 | PASS |
| phase_symmetry_load | max over angles of the spread of the three phases' fundamental flux linkage / mean, under load | 9.41e-05 | 2e-03 | PASS |
| mtpa_bracketed (validity) | maximum torque inside the angle sweep (0 = yes) | 0.00e+00 | 0e+00 | PASS |
| time_resolution (validity) | 48 / steps per electrical period (below 1: at least 48) | 1.00e+00 | 1e+00 | PASS |

![p05_current_rms_A-300 response](points/p05_current_rms_A-300/response.png)

### p06_current_rms_A-350

Parameters: machine = Toyota_Prius_ORNL.json, speed_rpm = 1000, current_rms_A = 350, angle_min_deg = 0, angle_max_deg = 70, angle_steps = 8, mesh_fineness = 4, steps_per_period = 48, angle_points = 2048, rated_torque_Nm = 400, slot_fill = 0.84, slot_area_mm2 = 143, turns_per_slot = 9

Derived: current_density_rms_A_per_mm2 = 26.22

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-M3 | 26.22 A/mm^2 | <= 25 | -1.22 | **FAIL** | [point.json](points/p06_current_rms_A-350/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| power_balance | max over current angles of |mean(sum i dphi/dt) - mean torque x omega_m| / (mean torque x omega_m): energy conservation, an independent route to FEMM's stress-tensor torque | 1.24e-03 | 2e-02 | PASS |
| current_amplitude | max |imposed phase current fundamental - sqrt(2) x requested rms| / peak (Pyleecan's dq currents are rms) | 2.30e-16 | 1e-03 | PASS |
| phase_symmetry_load | max over angles of the spread of the three phases' fundamental flux linkage / mean, under load | 9.53e-05 | 2e-03 | PASS |
| mtpa_bracketed (validity) | maximum torque inside the angle sweep (0 = yes) | 0.00e+00 | 0e+00 | PASS |
| time_resolution (validity) | 48 / steps per electrical period (below 1: at least 48) | 1.00e+00 | 1e+00 | PASS |

![p06_current_rms_A-350 response](points/p06_current_rms_A-350/response.png)

## Limitations

- No test data in this case: the ORNL comparison is a separate, blind step at the end of the study.
- Sinusoidal currents; no inverter harmonics, no voltage limit (1000 rpm is below base speed).
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

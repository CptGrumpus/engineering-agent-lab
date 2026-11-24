# Engineering review report: motor_prius_efficiency_rev5_refined

- **Run:** `20261124-091110_motor_prius_efficiency_rev5_refined`
- **Generated:** 2026-11-24T14:11:12+00:00
- **Case file SHA-256:** `9ccce707ecc72a2270d46cf03d31af46ae44046dae17ea781200d6266c2aef2b`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Tools:** numpy 2.5.5; scipy 1.18.1
- **Code version:** git `43c8c160d548248786e5c57bfe2c49178f73a4b9` (uncommitted changes present)
- **Simulation status:** completed
- **Verification status:** PASS

## Scope

2004 Toyota Prius traction motor, REVISION 5 (client data: magnet 83.1 x 18.9 x 6.5 mm, 1.255 T at 20 C, air gap 0.775 mm; measured phase resistance 69 mOhm at 21 C), motor-only efficiency map from the verified dq look-up tables (25 A tables merged with low-q-current tables at 6.25 A): 500-6000 rpm, 10-400 N m, least copper + iron loss under the 500 V bus voltage limit and the current limit; cold (all 20 C) and hot (windings 100 C, magnets 80 C) scenarios.

**Assumptions**

- Motor-only efficiency: copper (DC resistance, end connections included) and iron loss; no mechanical, magnet eddy-current, AC copper or inverter loss (user's framing, 2026-11-22).
- Voltage limit Vdc / sqrt 6 phase rms (linear modulation of a 500 V bus); the resistive drop is included, inductive coupling to the inverter is not.
- Current limit 212 A rms for the design (25 A/mm^2 on 76.4 mm^2 of bare copper per slot, a stated assumption) and 300 A for the map's edge.
- Iron loss from the table's coefficients, P = A f + B f^2 + C f^1.5 with f the electrical frequency, at each grid point.
- Phase resistance: the client's measured 69 mOhm at 21 C (ORNL/TM-2010/253 Table 2.7), referred to temperature with alpha 0.00393 /K [client: routine test]; the geometric parameters stay in the case for reference only.

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-M5 | The motor shall deliver its rated 50 kW from the rated base speed (50 kW at 400 N m: 1194 rpm) to 6000 rpm within the 500 V bus voltage limit and the 212 A rms design current limit. | `min_power_rated_speed_range_kW` | >= 50 kW |

## Summary across points

| Point | scenario | REQ-M5 | Checks |
|---|---|---|---|
| p00_cold | cold | 55.85 kW: **PASS** | 8/8 PASS |
| p01_hot | hot | 51.65 kW: **PASS** | 5/5 PASS |

![Requirement metrics across the sweep](sweep.png)

## Point details

### p00_cold

Parameters: lut_run = 20261123-230647_motor_prius_lut_cold_rev5,20261124-004731_motor_prius_lut_cold_lowiq_rev5,20261124-075333_motor_prius_lut_cold_refine_rev5, magnet_temperature_C = 20, winding_temperature_C = 20, series_turns_per_phase = 72, turn_copper_area_mm2 = 8.492, stack_length_m = 0.08382, end_connection_length_m = 0.1206, copper_resistivity_20C_ohm_m = 1.72e-08, copper_alpha_per_K = 0.00393, phase_resistance_measured_ohm = 0.069, phase_resistance_measured_at_C = 21, bus_voltage_V = 500, current_limit_design_A = 212, current_limit_map_A = 300, speed_min_rpm = 500, speed_max_rpm = 6000, speed_step_rpm = 250, torque_min_Nm = 10, torque_max_Nm = 400, torque_step_Nm = 10, rated_power_kW = 50, rated_torque_Nm = 400, ref_back_emf_V = 105.8, ref_mtpa_100A_Nm = 247.7, ref_mtpa_200A_Nm = 449.1, scenario = cold

Derived: phase_resistance_20C_ohm = 0.06873, voltage_limit_rms_V = 204.1

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-M5 | 55.85 kW | >= 50 | 5.85 | **PASS** | [point.json](points/p00_cold/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| lut_back_emf | |table open-circuit back-EMF (sqrt 3 w phi_d at id = iq = 0) - open-circuit study| / open-circuit study (same mesh fineness) | 3.21e-05 | 1e-03 | PASS |
| lut_mtpa_100A | |table MTPA torque at 100 A rms - torque-curve study| / torque-curve study (cubic interpolation against an angle sweep with a parabola) | 4.97e-04 | 1e-02 | PASS |
| lut_mtpa_200A | |table MTPA torque at 200 A rms - torque-curve study| / torque-curve study (cubic interpolation against an angle sweep with a parabola) | 2.27e-03 | 1e-02 | PASS |
| interp_torque | max over the left-out nodes (|T| >= 20 N m) of the torque error of the table on every second node: bounds the full table's interpolation error (cubic: about 1/16 of this) | 4.86e-03 | 5e-02 | PASS |
| interp_iron_loss | the same for the iron loss at 6000 rpm | 2.57e-02 | 5e-02 | PASS |
| magnet_temperature (validity) | |table's magnet temperature - this scenario's| (K) | 0.00e+00 | 0e+00 | PASS |
| lut_merge | max relative difference over the nodes two merged table runs both computed (same model, mesh and rotor positions: it must reproduce itself) | 0.00e+00 | 1e-04 | PASS |
| interp_map | max |efficiency from the half table - from the full table| over the map (efficiency points): bounds the full table's interpolation error on the output itself | 6.02e-01 | 2e+00 | PASS |

![p00_cold response](points/p00_cold/response.png)

### p01_hot

Parameters: lut_run = 20261124-014553_motor_prius_lut_hot_rev5,20261124-031723_motor_prius_lut_hot_lowiq_rev5,20261124-082355_motor_prius_lut_hot_refine_rev5, magnet_temperature_C = 80, winding_temperature_C = 100, series_turns_per_phase = 72, turn_copper_area_mm2 = 8.492, stack_length_m = 0.08382, end_connection_length_m = 0.1206, copper_resistivity_20C_ohm_m = 1.72e-08, copper_alpha_per_K = 0.00393, phase_resistance_measured_ohm = 0.069, phase_resistance_measured_at_C = 21, bus_voltage_V = 500, current_limit_design_A = 212, current_limit_map_A = 300, speed_min_rpm = 500, speed_max_rpm = 6000, speed_step_rpm = 250, torque_min_Nm = 10, torque_max_Nm = 400, torque_step_Nm = 10, rated_power_kW = 50, rated_torque_Nm = 400, ref_back_emf_V = 0, ref_mtpa_100A_Nm = 0, ref_mtpa_200A_Nm = 0, scenario = hot

Derived: phase_resistance_20C_ohm = 0.06873, voltage_limit_rms_V = 204.1

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-M5 | 51.65 kW | >= 50 | 1.65 | **PASS** | [point.json](points/p01_hot/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| interp_torque | max over the left-out nodes (|T| >= 20 N m) of the torque error of the table on every second node: bounds the full table's interpolation error (cubic: about 1/16 of this) | 5.37e-03 | 5e-02 | PASS |
| interp_iron_loss | the same for the iron loss at 6000 rpm | 2.48e-02 | 5e-02 | PASS |
| magnet_temperature (validity) | |table's magnet temperature - this scenario's| (K) | 0.00e+00 | 0e+00 | PASS |
| lut_merge | max relative difference over the nodes two merged table runs both computed (same model, mesh and rotor positions: it must reproduce itself) | 0.00e+00 | 1e-04 | PASS |
| interp_map | max |efficiency from the half table - from the full table| over the map (efficiency points): bounds the full table's interpolation error on the output itself | 3.11e-01 | 2e+00 | PASS |

![p01_hot response](points/p01_hot/response.png)

## Limitations

- Revision 5 carries about 18 % more magnet flux than ORNL's back-EMF test shows (unexplained; CALIBRATION_PLAN step 4); not calibrated. ORNL's efficiency is not used here and is scored separately.
- The tables are 2D magnetostatic at 1000 rpm; the iron loss is scaled to speed by the fitted coefficients, not recomputed per speed.
- Steady thermal corners only (cold and hot); no thermal model links temperature to the operating point yet.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

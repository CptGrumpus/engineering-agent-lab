# Engineering review report: motor_prius_thermal_rev5

- **Run:** `20261124-063338_motor_prius_thermal_rev5`
- **Generated:** 2026-11-24T11:38:02+00:00
- **Case file SHA-256:** `5f127812b9c3a51bc88aeca9670d178919f5d81efbe9fe63156464ee6e208417`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Tools:** numpy 2.5.5; scipy 1.18.1; gmsh 4.15.0; ccx This is Version 2.22
- **Code version:** git `a9427c2485bf78539afae66ced2196481e5007de` (uncommitted changes present)
- **Simulation status:** completed
- **Verification status:** FAIL

> **Warning:** verification did not pass for every point. Requirement verdicts marked *(unverified)* are not supported by evidence and must not be used for acceptance.

## Scope

2004 Toyota Prius traction motor, REVISION 5 (client data: magnets 83.1 x 18.9 x 6.5 mm at 1.255 T, measured phase resistance 69 mOhm at 21 C): steady lumped thermal network from the geometry, coupled to the verified dq tables (losses at the network's temperatures); continuous torque-speed envelope 500-6000 rpm within a 180 C winding hotspot and 150 C magnets under a synthetic 65 C water jacket, and the magnet temperature where the winding mean reaches the efficiency map's 100 C; nominal and nine sensitivity scenarios; CalculiX slot-pitch conduction check.

**Assumptions**

- Steady state; continuous duty. Losses: copper (DC resistance at each winding part's temperature) and iron (the tables' stator and rotor coefficients); no AC copper, magnet eddy-current or mechanical loss (as in the efficiency study). Magnets carry no loss, so they sit at the rotor's mean temperature.
- Tables blended linearly in magnet temperature between the cold (20 C) and hot (80 C) runs; above 80 C this is an extrapolation (linear reversible Br loss), reported as magnet_extrapolation_above_hot_table_K.
- Cooling synthetic (user, 2026-11-22): water-glycol jacket 65 C, h 3000 W/m^2 K on the housing over the stack and end-winding extensions; the result scales with it through the jacket scenarios.
- Limits synthetic (user, 2026-11-22): winding hotspot 180 C (class H), magnets 150 C.
- Stator-housing interface: an equivalent air gap of 0.037 mm (Staton et al. 2005 Table III average of measured machines); swept 0.01 / 0.08 mm.
- End-space convection from correlations measured on TEFC induction motors (Boglietti and Cavagnino 2007 form; Micallef constants), v = rotor peripheral speed; scenario 0.5x.
- Air gap: conduction only (Nu = 2), the lower bound; scenario 3x. Shaft adiabatic: no heat path through the shaft and bearings (conservative for the rotor).
- Slot hotspot: the larger of the slab value (winding surface + 1.5 (mean - surface)) and the top-of-slot value (tooth-tip temperature + liner drop + local slab rise across the top width; revision 1); checked against the CalculiX section's peak. End-turn hotspot: slot exit + 1.5 (mean - slot exit), not checked by FE.
- Stator iron loss split 0.57 teeth / 0.43 yoke (area x B^2 estimate); scenarios 0.4 and 0.75.

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-TH1 | The motor shall deliver at least 25 kW continuously (steady state, winding hotspot <= 180 C, magnets <= 150 C) at every speed from 1250 rpm (just above the 1194 rpm rated base speed) to 6000 rpm, under the stated jacket. | `min_continuous_power_kW` | >= 25 kW |

## Summary across points

| Point | scenario | REQ-TH1 | Checks |
|---|---|---|---|
| p00_nominal | nominal | 27.7 kW: **PASS (unverified)** | 8/9 FAIL |
| p01_jacket_h1000 | jacket_h1000 | 25.6 kW: **PASS (unverified)** | 8/9 FAIL |
| p02_jacket_h6000 | jacket_h6000 | 28.25 kW: **PASS (unverified)** | 8/9 FAIL |
| p03_interface_0p01 | interface_0p01 | 31.47 kW: **PASS (unverified)** | 6/9 FAIL |
| p04_interface_0p08 | interface_0p08 | 23.99 kW: **FAIL** | 9/9 PASS |
| p05_end_space_half | end_space_half | 25.21 kW: **PASS** | 9/9 PASS |
| p06_air_gap_x3 | air_gap_x3 | 27.14 kW: **PASS** | 9/9 PASS |
| p07_winding_k_half | winding_k_half | 27.38 kW: **PASS (unverified)** | 8/9 FAIL |
| p08_teeth_0p40 | teeth_0p40 | 27.77 kW: **PASS (unverified)** | 8/9 FAIL |
| p09_teeth_0p75 | teeth_0p75 | 27.6 kW: **PASS (unverified)** | 8/9 FAIL |

![Requirement metrics across the sweep](sweep.png)

## Point details

### p00_nominal

Parameters: n_slots = 48, stack_length_mm = 83.82, stator_outer_radius_mm = 134.6, stator_bore_radius_mm = 80.96, slot_shoulder_x_mm = 81.97, slot_width_shoulder_mm = 3.15, slot_width_round_mm = 5.639, slot_round_centre_x_mm = 111.7, slot_opening_mm = 1.93, liner_thickness_mm = 0.25, copper_area_per_slot_mm2 = 76.4, rotor_outer_radius_mm = 80.19, rotor_inner_radius_mm = 55.32, end_connection_length_mm = 120.6, end_extension_mm = 38.4, impregnant_conductivity_W_mK = 0.25, copper_conductivity_W_mK = 390, liner_conductivity_W_mK = 0.2, lamination_conductivity_W_mK = 28, housing_conductivity_W_mK = 160, housing_wall_mm = 6, interface_gap_mm = 0.037, jacket_htc_W_m2K = 3000, coolant_temperature_C = 65, air_gap_h_factor = 1, end_space_h_scale = 1, winding_k_scale = 1, teeth_iron_fraction = 0.57, h_winding_end_space_k1 = 15, h_winding_end_space_k2 = 6, h_winding_end_space_k3 = 0.9, h_housing_end_space_k1 = 20, h_housing_end_space_k2 = 8.7, h_housing_end_space_k3 = 0.7, h_rotor_end_space_k1 = 41.4, h_rotor_end_space_k2 = 6.22, h_rotor_end_space_k3 = 1, lut_run_cold = 20261123-230647_motor_prius_lut_cold_rev5,20261124-004731_motor_prius_lut_cold_lowiq_rev5, lut_run_hot = 20261124-014553_motor_prius_lut_hot_rev5,20261124-031723_motor_prius_lut_hot_lowiq_rev5, efficiency_run = 20261124-062847_motor_prius_efficiency_rev5, series_turns_per_phase = 72, turn_copper_area_mm2 = 8.492, stack_length_m = 0.08382, end_connection_length_m = 0.1206, copper_resistivity_20C_ohm_m = 1.72e-08, copper_alpha_per_K = 0.00393, phase_resistance_measured_ohm = 0.069, phase_resistance_measured_at_C = 21, bus_voltage_V = 500, current_limit_design_A = 212, winding_hotspot_limit_C = 180, magnet_limit_C = 150, speed_min_rpm = 500, speed_max_rpm = 6000, speed_step_rpm = 250, hot_corner_winding_C = 100, fe_reference_speed_rpm = 3000, scenario = nominal

Derived: phase_resistance_20C_ohm = 0.06873

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-TH1 | 27.7 kW | >= 25 | 2.7 | **PASS (unverified)** | [point.json](points/p00_nominal/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| energy_balance | max over every network solve of |losses in - heat to the coolant| / losses | 1.73e-12 | 1e-09 | PASS |
| coupling_convergence | max over the envelope and hot-corner searches of the last temperature change of the loss-temperature iteration (K) | 7.08e-04 | 1e-01 | PASS |
| efficiency_consistency | max relative difference of the total loss at fixed hot temperatures (windings 100 C, magnets 80 C) against the efficiency run's hot map at five points | 3.43e-16 | 1e-06 | PASS |
| fe_balance | CalculiX section: |generation - film heat out| / generation, worst mesh | 6.49e-05 | 1e-03 | PASS |
| fe_mesh | CalculiX section: discretization uncertainty (GCI or spread) of the winding peak rise | 0.00e+00 | 1e-02 | PASS |
| section_wind_mean | |network - CalculiX| / CalculiX, winding mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 4.48e-02 | 5e-02 | PASS |
| section_wind_peak | |network - CalculiX| / CalculiX, winding peak (network: slab factor 1.5) rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 5.33e-02 | 5e-02 | FAIL |
| section_teeth_mean | |network - CalculiX| / CalculiX, teeth mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 3.28e-02 | 5e-02 | PASS |
| section_yoke_mean | |network - CalculiX| / CalculiX, yoke mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 6.66e-03 | 5e-02 | PASS |

![p00_nominal response](points/p00_nominal/response.png)

### p01_jacket_h1000

Parameters: n_slots = 48, stack_length_mm = 83.82, stator_outer_radius_mm = 134.6, stator_bore_radius_mm = 80.96, slot_shoulder_x_mm = 81.97, slot_width_shoulder_mm = 3.15, slot_width_round_mm = 5.639, slot_round_centre_x_mm = 111.7, slot_opening_mm = 1.93, liner_thickness_mm = 0.25, copper_area_per_slot_mm2 = 76.4, rotor_outer_radius_mm = 80.19, rotor_inner_radius_mm = 55.32, end_connection_length_mm = 120.6, end_extension_mm = 38.4, impregnant_conductivity_W_mK = 0.25, copper_conductivity_W_mK = 390, liner_conductivity_W_mK = 0.2, lamination_conductivity_W_mK = 28, housing_conductivity_W_mK = 160, housing_wall_mm = 6, interface_gap_mm = 0.037, jacket_htc_W_m2K = 1000, coolant_temperature_C = 65, air_gap_h_factor = 1, end_space_h_scale = 1, winding_k_scale = 1, teeth_iron_fraction = 0.57, h_winding_end_space_k1 = 15, h_winding_end_space_k2 = 6, h_winding_end_space_k3 = 0.9, h_housing_end_space_k1 = 20, h_housing_end_space_k2 = 8.7, h_housing_end_space_k3 = 0.7, h_rotor_end_space_k1 = 41.4, h_rotor_end_space_k2 = 6.22, h_rotor_end_space_k3 = 1, lut_run_cold = 20261123-230647_motor_prius_lut_cold_rev5,20261124-004731_motor_prius_lut_cold_lowiq_rev5, lut_run_hot = 20261124-014553_motor_prius_lut_hot_rev5,20261124-031723_motor_prius_lut_hot_lowiq_rev5, efficiency_run = 20261124-062847_motor_prius_efficiency_rev5, series_turns_per_phase = 72, turn_copper_area_mm2 = 8.492, stack_length_m = 0.08382, end_connection_length_m = 0.1206, copper_resistivity_20C_ohm_m = 1.72e-08, copper_alpha_per_K = 0.00393, phase_resistance_measured_ohm = 0.069, phase_resistance_measured_at_C = 21, bus_voltage_V = 500, current_limit_design_A = 212, winding_hotspot_limit_C = 180, magnet_limit_C = 150, speed_min_rpm = 500, speed_max_rpm = 6000, speed_step_rpm = 250, hot_corner_winding_C = 100, fe_reference_speed_rpm = 3000, scenario = jacket_h1000

Derived: phase_resistance_20C_ohm = 0.06873

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-TH1 | 25.6 kW | >= 25 | 0.597 | **PASS (unverified)** | [point.json](points/p01_jacket_h1000/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| energy_balance | max over every network solve of |losses in - heat to the coolant| / losses | 1.79e-12 | 1e-09 | PASS |
| coupling_convergence | max over the envelope and hot-corner searches of the last temperature change of the loss-temperature iteration (K) | 8.79e+00 | 1e-01 | FAIL |
| efficiency_consistency | max relative difference of the total loss at fixed hot temperatures (windings 100 C, magnets 80 C) against the efficiency run's hot map at five points | 3.43e-16 | 1e-06 | PASS |
| fe_balance | CalculiX section: |generation - film heat out| / generation, worst mesh | 6.06e-05 | 1e-03 | PASS |
| fe_mesh | CalculiX section: discretization uncertainty (GCI or spread) of the winding peak rise | 0.00e+00 | 1e-02 | PASS |
| section_wind_mean | |network - CalculiX| / CalculiX, winding mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 3.60e-02 | 5e-02 | PASS |
| section_wind_peak | |network - CalculiX| / CalculiX, winding peak (network: slab factor 1.5) rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 4.34e-02 | 5e-02 | PASS |
| section_teeth_mean | |network - CalculiX| / CalculiX, teeth mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 2.55e-02 | 5e-02 | PASS |
| section_yoke_mean | |network - CalculiX| / CalculiX, yoke mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 6.33e-03 | 5e-02 | PASS |

![p01_jacket_h1000 response](points/p01_jacket_h1000/response.png)

### p02_jacket_h6000

Parameters: n_slots = 48, stack_length_mm = 83.82, stator_outer_radius_mm = 134.6, stator_bore_radius_mm = 80.96, slot_shoulder_x_mm = 81.97, slot_width_shoulder_mm = 3.15, slot_width_round_mm = 5.639, slot_round_centre_x_mm = 111.7, slot_opening_mm = 1.93, liner_thickness_mm = 0.25, copper_area_per_slot_mm2 = 76.4, rotor_outer_radius_mm = 80.19, rotor_inner_radius_mm = 55.32, end_connection_length_mm = 120.6, end_extension_mm = 38.4, impregnant_conductivity_W_mK = 0.25, copper_conductivity_W_mK = 390, liner_conductivity_W_mK = 0.2, lamination_conductivity_W_mK = 28, housing_conductivity_W_mK = 160, housing_wall_mm = 6, interface_gap_mm = 0.037, jacket_htc_W_m2K = 6000, coolant_temperature_C = 65, air_gap_h_factor = 1, end_space_h_scale = 1, winding_k_scale = 1, teeth_iron_fraction = 0.57, h_winding_end_space_k1 = 15, h_winding_end_space_k2 = 6, h_winding_end_space_k3 = 0.9, h_housing_end_space_k1 = 20, h_housing_end_space_k2 = 8.7, h_housing_end_space_k3 = 0.7, h_rotor_end_space_k1 = 41.4, h_rotor_end_space_k2 = 6.22, h_rotor_end_space_k3 = 1, lut_run_cold = 20261123-230647_motor_prius_lut_cold_rev5,20261124-004731_motor_prius_lut_cold_lowiq_rev5, lut_run_hot = 20261124-014553_motor_prius_lut_hot_rev5,20261124-031723_motor_prius_lut_hot_lowiq_rev5, efficiency_run = 20261124-062847_motor_prius_efficiency_rev5, series_turns_per_phase = 72, turn_copper_area_mm2 = 8.492, stack_length_m = 0.08382, end_connection_length_m = 0.1206, copper_resistivity_20C_ohm_m = 1.72e-08, copper_alpha_per_K = 0.00393, phase_resistance_measured_ohm = 0.069, phase_resistance_measured_at_C = 21, bus_voltage_V = 500, current_limit_design_A = 212, winding_hotspot_limit_C = 180, magnet_limit_C = 150, speed_min_rpm = 500, speed_max_rpm = 6000, speed_step_rpm = 250, hot_corner_winding_C = 100, fe_reference_speed_rpm = 3000, scenario = jacket_h6000

Derived: phase_resistance_20C_ohm = 0.06873

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-TH1 | 28.25 kW | >= 25 | 3.25 | **PASS (unverified)** | [point.json](points/p02_jacket_h6000/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| energy_balance | max over every network solve of |losses in - heat to the coolant| / losses | 1.60e-12 | 1e-09 | PASS |
| coupling_convergence | max over the envelope and hot-corner searches of the last temperature change of the loss-temperature iteration (K) | 5.16e-04 | 1e-01 | PASS |
| efficiency_consistency | max relative difference of the total loss at fixed hot temperatures (windings 100 C, magnets 80 C) against the efficiency run's hot map at five points | 3.43e-16 | 1e-06 | PASS |
| fe_balance | CalculiX section: |generation - film heat out| / generation, worst mesh | 6.57e-05 | 1e-03 | PASS |
| fe_mesh | CalculiX section: discretization uncertainty (GCI or spread) of the winding peak rise | 0.00e+00 | 1e-02 | PASS |
| section_wind_mean | |network - CalculiX| / CalculiX, winding mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 4.76e-02 | 5e-02 | PASS |
| section_wind_peak | |network - CalculiX| / CalculiX, winding peak (network: slab factor 1.5) rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 5.63e-02 | 5e-02 | FAIL |
| section_teeth_mean | |network - CalculiX| / CalculiX, teeth mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 3.52e-02 | 5e-02 | PASS |
| section_yoke_mean | |network - CalculiX| / CalculiX, yoke mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 6.72e-03 | 5e-02 | PASS |

![p02_jacket_h6000 response](points/p02_jacket_h6000/response.png)

### p03_interface_0p01

Parameters: n_slots = 48, stack_length_mm = 83.82, stator_outer_radius_mm = 134.6, stator_bore_radius_mm = 80.96, slot_shoulder_x_mm = 81.97, slot_width_shoulder_mm = 3.15, slot_width_round_mm = 5.639, slot_round_centre_x_mm = 111.7, slot_opening_mm = 1.93, liner_thickness_mm = 0.25, copper_area_per_slot_mm2 = 76.4, rotor_outer_radius_mm = 80.19, rotor_inner_radius_mm = 55.32, end_connection_length_mm = 120.6, end_extension_mm = 38.4, impregnant_conductivity_W_mK = 0.25, copper_conductivity_W_mK = 390, liner_conductivity_W_mK = 0.2, lamination_conductivity_W_mK = 28, housing_conductivity_W_mK = 160, housing_wall_mm = 6, interface_gap_mm = 0.01, jacket_htc_W_m2K = 3000, coolant_temperature_C = 65, air_gap_h_factor = 1, end_space_h_scale = 1, winding_k_scale = 1, teeth_iron_fraction = 0.57, h_winding_end_space_k1 = 15, h_winding_end_space_k2 = 6, h_winding_end_space_k3 = 0.9, h_housing_end_space_k1 = 20, h_housing_end_space_k2 = 8.7, h_housing_end_space_k3 = 0.7, h_rotor_end_space_k1 = 41.4, h_rotor_end_space_k2 = 6.22, h_rotor_end_space_k3 = 1, lut_run_cold = 20261123-230647_motor_prius_lut_cold_rev5,20261124-004731_motor_prius_lut_cold_lowiq_rev5, lut_run_hot = 20261124-014553_motor_prius_lut_hot_rev5,20261124-031723_motor_prius_lut_hot_lowiq_rev5, efficiency_run = 20261124-062847_motor_prius_efficiency_rev5, series_turns_per_phase = 72, turn_copper_area_mm2 = 8.492, stack_length_m = 0.08382, end_connection_length_m = 0.1206, copper_resistivity_20C_ohm_m = 1.72e-08, copper_alpha_per_K = 0.00393, phase_resistance_measured_ohm = 0.069, phase_resistance_measured_at_C = 21, bus_voltage_V = 500, current_limit_design_A = 212, winding_hotspot_limit_C = 180, magnet_limit_C = 150, speed_min_rpm = 500, speed_max_rpm = 6000, speed_step_rpm = 250, hot_corner_winding_C = 100, fe_reference_speed_rpm = 3000, scenario = interface_0p01

Derived: phase_resistance_20C_ohm = 0.06873

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-TH1 | 31.47 kW | >= 25 | 6.47 | **PASS (unverified)** | [point.json](points/p03_interface_0p01/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| energy_balance | max over every network solve of |losses in - heat to the coolant| / losses | 1.60e-12 | 1e-09 | PASS |
| coupling_convergence | max over the envelope and hot-corner searches of the last temperature change of the loss-temperature iteration (K) | 7.57e-04 | 1e-01 | PASS |
| efficiency_consistency | max relative difference of the total loss at fixed hot temperatures (windings 100 C, magnets 80 C) against the efficiency run's hot map at five points | 3.43e-16 | 1e-06 | PASS |
| fe_balance | CalculiX section: |generation - film heat out| / generation, worst mesh | 6.86e-05 | 1e-03 | PASS |
| fe_mesh | CalculiX section: discretization uncertainty (GCI or spread) of the winding peak rise | 0.00e+00 | 1e-02 | PASS |
| section_wind_mean | |network - CalculiX| / CalculiX, winding mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 6.43e-02 | 5e-02 | FAIL |
| section_wind_peak | |network - CalculiX| / CalculiX, winding peak (network: slab factor 1.5) rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 7.31e-02 | 5e-02 | FAIL |
| section_teeth_mean | |network - CalculiX| / CalculiX, teeth mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 5.00e-02 | 5e-02 | FAIL |
| section_yoke_mean | |network - CalculiX| / CalculiX, yoke mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 7.87e-03 | 5e-02 | PASS |

![p03_interface_0p01 response](points/p03_interface_0p01/response.png)

### p04_interface_0p08

Parameters: n_slots = 48, stack_length_mm = 83.82, stator_outer_radius_mm = 134.6, stator_bore_radius_mm = 80.96, slot_shoulder_x_mm = 81.97, slot_width_shoulder_mm = 3.15, slot_width_round_mm = 5.639, slot_round_centre_x_mm = 111.7, slot_opening_mm = 1.93, liner_thickness_mm = 0.25, copper_area_per_slot_mm2 = 76.4, rotor_outer_radius_mm = 80.19, rotor_inner_radius_mm = 55.32, end_connection_length_mm = 120.6, end_extension_mm = 38.4, impregnant_conductivity_W_mK = 0.25, copper_conductivity_W_mK = 390, liner_conductivity_W_mK = 0.2, lamination_conductivity_W_mK = 28, housing_conductivity_W_mK = 160, housing_wall_mm = 6, interface_gap_mm = 0.08, jacket_htc_W_m2K = 3000, coolant_temperature_C = 65, air_gap_h_factor = 1, end_space_h_scale = 1, winding_k_scale = 1, teeth_iron_fraction = 0.57, h_winding_end_space_k1 = 15, h_winding_end_space_k2 = 6, h_winding_end_space_k3 = 0.9, h_housing_end_space_k1 = 20, h_housing_end_space_k2 = 8.7, h_housing_end_space_k3 = 0.7, h_rotor_end_space_k1 = 41.4, h_rotor_end_space_k2 = 6.22, h_rotor_end_space_k3 = 1, lut_run_cold = 20261123-230647_motor_prius_lut_cold_rev5,20261124-004731_motor_prius_lut_cold_lowiq_rev5, lut_run_hot = 20261124-014553_motor_prius_lut_hot_rev5,20261124-031723_motor_prius_lut_hot_lowiq_rev5, efficiency_run = 20261124-062847_motor_prius_efficiency_rev5, series_turns_per_phase = 72, turn_copper_area_mm2 = 8.492, stack_length_m = 0.08382, end_connection_length_m = 0.1206, copper_resistivity_20C_ohm_m = 1.72e-08, copper_alpha_per_K = 0.00393, phase_resistance_measured_ohm = 0.069, phase_resistance_measured_at_C = 21, bus_voltage_V = 500, current_limit_design_A = 212, winding_hotspot_limit_C = 180, magnet_limit_C = 150, speed_min_rpm = 500, speed_max_rpm = 6000, speed_step_rpm = 250, hot_corner_winding_C = 100, fe_reference_speed_rpm = 3000, scenario = interface_0p08

Derived: phase_resistance_20C_ohm = 0.06873

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-TH1 | 23.99 kW | >= 25 | -1.01 | **FAIL** | [point.json](points/p04_interface_0p08/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| energy_balance | max over every network solve of |losses in - heat to the coolant| / losses | 1.69e-12 | 1e-09 | PASS |
| coupling_convergence | max over the envelope and hot-corner searches of the last temperature change of the loss-temperature iteration (K) | 9.82e-05 | 1e-01 | PASS |
| efficiency_consistency | max relative difference of the total loss at fixed hot temperatures (windings 100 C, magnets 80 C) against the efficiency run's hot map at five points | 3.43e-16 | 1e-06 | PASS |
| fe_balance | CalculiX section: |generation - film heat out| / generation, worst mesh | 6.06e-05 | 1e-03 | PASS |
| fe_mesh | CalculiX section: discretization uncertainty (GCI or spread) of the winding peak rise | 0.00e+00 | 1e-02 | PASS |
| section_wind_mean | |network - CalculiX| / CalculiX, winding mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 3.06e-02 | 5e-02 | PASS |
| section_wind_peak | |network - CalculiX| / CalculiX, winding peak (network: slab factor 1.5) rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 3.85e-02 | 5e-02 | PASS |
| section_teeth_mean | |network - CalculiX| / CalculiX, teeth mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 2.18e-02 | 5e-02 | PASS |
| section_yoke_mean | |network - CalculiX| / CalculiX, yoke mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 4.15e-03 | 5e-02 | PASS |

![p04_interface_0p08 response](points/p04_interface_0p08/response.png)

### p05_end_space_half

Parameters: n_slots = 48, stack_length_mm = 83.82, stator_outer_radius_mm = 134.6, stator_bore_radius_mm = 80.96, slot_shoulder_x_mm = 81.97, slot_width_shoulder_mm = 3.15, slot_width_round_mm = 5.639, slot_round_centre_x_mm = 111.7, slot_opening_mm = 1.93, liner_thickness_mm = 0.25, copper_area_per_slot_mm2 = 76.4, rotor_outer_radius_mm = 80.19, rotor_inner_radius_mm = 55.32, end_connection_length_mm = 120.6, end_extension_mm = 38.4, impregnant_conductivity_W_mK = 0.25, copper_conductivity_W_mK = 390, liner_conductivity_W_mK = 0.2, lamination_conductivity_W_mK = 28, housing_conductivity_W_mK = 160, housing_wall_mm = 6, interface_gap_mm = 0.037, jacket_htc_W_m2K = 3000, coolant_temperature_C = 65, air_gap_h_factor = 1, end_space_h_scale = 0.5, winding_k_scale = 1, teeth_iron_fraction = 0.57, h_winding_end_space_k1 = 15, h_winding_end_space_k2 = 6, h_winding_end_space_k3 = 0.9, h_housing_end_space_k1 = 20, h_housing_end_space_k2 = 8.7, h_housing_end_space_k3 = 0.7, h_rotor_end_space_k1 = 41.4, h_rotor_end_space_k2 = 6.22, h_rotor_end_space_k3 = 1, lut_run_cold = 20261123-230647_motor_prius_lut_cold_rev5,20261124-004731_motor_prius_lut_cold_lowiq_rev5, lut_run_hot = 20261124-014553_motor_prius_lut_hot_rev5,20261124-031723_motor_prius_lut_hot_lowiq_rev5, efficiency_run = 20261124-062847_motor_prius_efficiency_rev5, series_turns_per_phase = 72, turn_copper_area_mm2 = 8.492, stack_length_m = 0.08382, end_connection_length_m = 0.1206, copper_resistivity_20C_ohm_m = 1.72e-08, copper_alpha_per_K = 0.00393, phase_resistance_measured_ohm = 0.069, phase_resistance_measured_at_C = 21, bus_voltage_V = 500, current_limit_design_A = 212, winding_hotspot_limit_C = 180, magnet_limit_C = 150, speed_min_rpm = 500, speed_max_rpm = 6000, speed_step_rpm = 250, hot_corner_winding_C = 100, fe_reference_speed_rpm = 3000, scenario = end_space_half

Derived: phase_resistance_20C_ohm = 0.06873

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-TH1 | 25.21 kW | >= 25 | 0.215 | **PASS** | [point.json](points/p05_end_space_half/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| energy_balance | max over every network solve of |losses in - heat to the coolant| / losses | 1.73e-12 | 1e-09 | PASS |
| coupling_convergence | max over the envelope and hot-corner searches of the last temperature change of the loss-temperature iteration (K) | 3.85e-04 | 1e-01 | PASS |
| efficiency_consistency | max relative difference of the total loss at fixed hot temperatures (windings 100 C, magnets 80 C) against the efficiency run's hot map at five points | 3.43e-16 | 1e-06 | PASS |
| fe_balance | CalculiX section: |generation - film heat out| / generation, worst mesh | 5.72e-05 | 1e-03 | PASS |
| fe_mesh | CalculiX section: discretization uncertainty (GCI or spread) of the winding peak rise | 0.00e+00 | 1e-02 | PASS |
| section_wind_mean | |network - CalculiX| / CalculiX, winding mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 4.05e-02 | 5e-02 | PASS |
| section_wind_peak | |network - CalculiX| / CalculiX, winding peak (network: slab factor 1.5) rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 4.54e-02 | 5e-02 | PASS |
| section_teeth_mean | |network - CalculiX| / CalculiX, teeth mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 2.81e-02 | 5e-02 | PASS |
| section_yoke_mean | |network - CalculiX| / CalculiX, yoke mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 1.01e-02 | 5e-02 | PASS |

![p05_end_space_half response](points/p05_end_space_half/response.png)

### p06_air_gap_x3

Parameters: n_slots = 48, stack_length_mm = 83.82, stator_outer_radius_mm = 134.6, stator_bore_radius_mm = 80.96, slot_shoulder_x_mm = 81.97, slot_width_shoulder_mm = 3.15, slot_width_round_mm = 5.639, slot_round_centre_x_mm = 111.7, slot_opening_mm = 1.93, liner_thickness_mm = 0.25, copper_area_per_slot_mm2 = 76.4, rotor_outer_radius_mm = 80.19, rotor_inner_radius_mm = 55.32, end_connection_length_mm = 120.6, end_extension_mm = 38.4, impregnant_conductivity_W_mK = 0.25, copper_conductivity_W_mK = 390, liner_conductivity_W_mK = 0.2, lamination_conductivity_W_mK = 28, housing_conductivity_W_mK = 160, housing_wall_mm = 6, interface_gap_mm = 0.037, jacket_htc_W_m2K = 3000, coolant_temperature_C = 65, air_gap_h_factor = 3, end_space_h_scale = 1, winding_k_scale = 1, teeth_iron_fraction = 0.57, h_winding_end_space_k1 = 15, h_winding_end_space_k2 = 6, h_winding_end_space_k3 = 0.9, h_housing_end_space_k1 = 20, h_housing_end_space_k2 = 8.7, h_housing_end_space_k3 = 0.7, h_rotor_end_space_k1 = 41.4, h_rotor_end_space_k2 = 6.22, h_rotor_end_space_k3 = 1, lut_run_cold = 20261123-230647_motor_prius_lut_cold_rev5,20261124-004731_motor_prius_lut_cold_lowiq_rev5, lut_run_hot = 20261124-014553_motor_prius_lut_hot_rev5,20261124-031723_motor_prius_lut_hot_lowiq_rev5, efficiency_run = 20261124-062847_motor_prius_efficiency_rev5, series_turns_per_phase = 72, turn_copper_area_mm2 = 8.492, stack_length_m = 0.08382, end_connection_length_m = 0.1206, copper_resistivity_20C_ohm_m = 1.72e-08, copper_alpha_per_K = 0.00393, phase_resistance_measured_ohm = 0.069, phase_resistance_measured_at_C = 21, bus_voltage_V = 500, current_limit_design_A = 212, winding_hotspot_limit_C = 180, magnet_limit_C = 150, speed_min_rpm = 500, speed_max_rpm = 6000, speed_step_rpm = 250, hot_corner_winding_C = 100, fe_reference_speed_rpm = 3000, scenario = air_gap_x3

Derived: phase_resistance_20C_ohm = 0.06873

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-TH1 | 27.14 kW | >= 25 | 2.14 | **PASS** | [point.json](points/p06_air_gap_x3/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| energy_balance | max over every network solve of |losses in - heat to the coolant| / losses | 1.98e-12 | 1e-09 | PASS |
| coupling_convergence | max over the envelope and hot-corner searches of the last temperature change of the loss-temperature iteration (K) | 7.06e-04 | 1e-01 | PASS |
| efficiency_consistency | max relative difference of the total loss at fixed hot temperatures (windings 100 C, magnets 80 C) against the efficiency run's hot map at five points | 3.43e-16 | 1e-06 | PASS |
| fe_balance | CalculiX section: |generation - film heat out| / generation, worst mesh | 6.48e-05 | 1e-03 | PASS |
| fe_mesh | CalculiX section: discretization uncertainty (GCI or spread) of the winding peak rise | 0.00e+00 | 1e-02 | PASS |
| section_wind_mean | |network - CalculiX| / CalculiX, winding mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 3.58e-02 | 5e-02 | PASS |
| section_wind_peak | |network - CalculiX| / CalculiX, winding peak (network: slab factor 1.5) rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 3.95e-02 | 5e-02 | PASS |
| section_teeth_mean | |network - CalculiX| / CalculiX, teeth mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 2.25e-02 | 5e-02 | PASS |
| section_yoke_mean | |network - CalculiX| / CalculiX, yoke mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 1.62e-02 | 5e-02 | PASS |

![p06_air_gap_x3 response](points/p06_air_gap_x3/response.png)

### p07_winding_k_half

Parameters: n_slots = 48, stack_length_mm = 83.82, stator_outer_radius_mm = 134.6, stator_bore_radius_mm = 80.96, slot_shoulder_x_mm = 81.97, slot_width_shoulder_mm = 3.15, slot_width_round_mm = 5.639, slot_round_centre_x_mm = 111.7, slot_opening_mm = 1.93, liner_thickness_mm = 0.25, copper_area_per_slot_mm2 = 76.4, rotor_outer_radius_mm = 80.19, rotor_inner_radius_mm = 55.32, end_connection_length_mm = 120.6, end_extension_mm = 38.4, impregnant_conductivity_W_mK = 0.25, copper_conductivity_W_mK = 390, liner_conductivity_W_mK = 0.2, lamination_conductivity_W_mK = 28, housing_conductivity_W_mK = 160, housing_wall_mm = 6, interface_gap_mm = 0.037, jacket_htc_W_m2K = 3000, coolant_temperature_C = 65, air_gap_h_factor = 1, end_space_h_scale = 1, winding_k_scale = 0.5, teeth_iron_fraction = 0.57, h_winding_end_space_k1 = 15, h_winding_end_space_k2 = 6, h_winding_end_space_k3 = 0.9, h_housing_end_space_k1 = 20, h_housing_end_space_k2 = 8.7, h_housing_end_space_k3 = 0.7, h_rotor_end_space_k1 = 41.4, h_rotor_end_space_k2 = 6.22, h_rotor_end_space_k3 = 1, lut_run_cold = 20261123-230647_motor_prius_lut_cold_rev5,20261124-004731_motor_prius_lut_cold_lowiq_rev5, lut_run_hot = 20261124-014553_motor_prius_lut_hot_rev5,20261124-031723_motor_prius_lut_hot_lowiq_rev5, efficiency_run = 20261124-062847_motor_prius_efficiency_rev5, series_turns_per_phase = 72, turn_copper_area_mm2 = 8.492, stack_length_m = 0.08382, end_connection_length_m = 0.1206, copper_resistivity_20C_ohm_m = 1.72e-08, copper_alpha_per_K = 0.00393, phase_resistance_measured_ohm = 0.069, phase_resistance_measured_at_C = 21, bus_voltage_V = 500, current_limit_design_A = 212, winding_hotspot_limit_C = 180, magnet_limit_C = 150, speed_min_rpm = 500, speed_max_rpm = 6000, speed_step_rpm = 250, hot_corner_winding_C = 100, fe_reference_speed_rpm = 3000, scenario = winding_k_half

Derived: phase_resistance_20C_ohm = 0.06873

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-TH1 | 27.38 kW | >= 25 | 2.38 | **PASS (unverified)** | [point.json](points/p07_winding_k_half/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| energy_balance | max over every network solve of |losses in - heat to the coolant| / losses | 1.89e-12 | 1e-09 | PASS |
| coupling_convergence | max over the envelope and hot-corner searches of the last temperature change of the loss-temperature iteration (K) | 5.32e-04 | 1e-01 | PASS |
| efficiency_consistency | max relative difference of the total loss at fixed hot temperatures (windings 100 C, magnets 80 C) against the efficiency run's hot map at five points | 3.43e-16 | 1e-06 | PASS |
| fe_balance | CalculiX section: |generation - film heat out| / generation, worst mesh | 6.51e-05 | 1e-03 | PASS |
| fe_mesh | CalculiX section: discretization uncertainty (GCI or spread) of the winding peak rise | 0.00e+00 | 1e-02 | PASS |
| section_wind_mean | |network - CalculiX| / CalculiX, winding mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 4.65e-02 | 5e-02 | PASS |
| section_wind_peak | |network - CalculiX| / CalculiX, winding peak (network: slab factor 1.5) rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 6.53e-02 | 5e-02 | FAIL |
| section_teeth_mean | |network - CalculiX| / CalculiX, teeth mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 3.46e-02 | 5e-02 | PASS |
| section_yoke_mean | |network - CalculiX| / CalculiX, yoke mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 6.92e-03 | 5e-02 | PASS |

![p07_winding_k_half response](points/p07_winding_k_half/response.png)

### p08_teeth_0p40

Parameters: n_slots = 48, stack_length_mm = 83.82, stator_outer_radius_mm = 134.6, stator_bore_radius_mm = 80.96, slot_shoulder_x_mm = 81.97, slot_width_shoulder_mm = 3.15, slot_width_round_mm = 5.639, slot_round_centre_x_mm = 111.7, slot_opening_mm = 1.93, liner_thickness_mm = 0.25, copper_area_per_slot_mm2 = 76.4, rotor_outer_radius_mm = 80.19, rotor_inner_radius_mm = 55.32, end_connection_length_mm = 120.6, end_extension_mm = 38.4, impregnant_conductivity_W_mK = 0.25, copper_conductivity_W_mK = 390, liner_conductivity_W_mK = 0.2, lamination_conductivity_W_mK = 28, housing_conductivity_W_mK = 160, housing_wall_mm = 6, interface_gap_mm = 0.037, jacket_htc_W_m2K = 3000, coolant_temperature_C = 65, air_gap_h_factor = 1, end_space_h_scale = 1, winding_k_scale = 1, teeth_iron_fraction = 0.4, h_winding_end_space_k1 = 15, h_winding_end_space_k2 = 6, h_winding_end_space_k3 = 0.9, h_housing_end_space_k1 = 20, h_housing_end_space_k2 = 8.7, h_housing_end_space_k3 = 0.7, h_rotor_end_space_k1 = 41.4, h_rotor_end_space_k2 = 6.22, h_rotor_end_space_k3 = 1, lut_run_cold = 20261123-230647_motor_prius_lut_cold_rev5,20261124-004731_motor_prius_lut_cold_lowiq_rev5, lut_run_hot = 20261124-014553_motor_prius_lut_hot_rev5,20261124-031723_motor_prius_lut_hot_lowiq_rev5, efficiency_run = 20261124-062847_motor_prius_efficiency_rev5, series_turns_per_phase = 72, turn_copper_area_mm2 = 8.492, stack_length_m = 0.08382, end_connection_length_m = 0.1206, copper_resistivity_20C_ohm_m = 1.72e-08, copper_alpha_per_K = 0.00393, phase_resistance_measured_ohm = 0.069, phase_resistance_measured_at_C = 21, bus_voltage_V = 500, current_limit_design_A = 212, winding_hotspot_limit_C = 180, magnet_limit_C = 150, speed_min_rpm = 500, speed_max_rpm = 6000, speed_step_rpm = 250, hot_corner_winding_C = 100, fe_reference_speed_rpm = 3000, scenario = teeth_0p40

Derived: phase_resistance_20C_ohm = 0.06873

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-TH1 | 27.77 kW | >= 25 | 2.77 | **PASS (unverified)** | [point.json](points/p08_teeth_0p40/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| energy_balance | max over every network solve of |losses in - heat to the coolant| / losses | 1.73e-12 | 1e-09 | PASS |
| coupling_convergence | max over the envelope and hot-corner searches of the last temperature change of the loss-temperature iteration (K) | 8.39e-04 | 1e-01 | PASS |
| efficiency_consistency | max relative difference of the total loss at fixed hot temperatures (windings 100 C, magnets 80 C) against the efficiency run's hot map at five points | 3.43e-16 | 1e-06 | PASS |
| fe_balance | CalculiX section: |generation - film heat out| / generation, worst mesh | 7.11e-05 | 1e-03 | PASS |
| fe_mesh | CalculiX section: discretization uncertainty (GCI or spread) of the winding peak rise | 0.00e+00 | 1e-02 | PASS |
| section_wind_mean | |network - CalculiX| / CalculiX, winding mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 4.32e-02 | 5e-02 | PASS |
| section_wind_peak | |network - CalculiX| / CalculiX, winding peak (network: slab factor 1.5) rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 5.23e-02 | 5e-02 | FAIL |
| section_teeth_mean | |network - CalculiX| / CalculiX, teeth mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 3.17e-02 | 5e-02 | PASS |
| section_yoke_mean | |network - CalculiX| / CalculiX, yoke mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 6.66e-03 | 5e-02 | PASS |

![p08_teeth_0p40 response](points/p08_teeth_0p40/response.png)

### p09_teeth_0p75

Parameters: n_slots = 48, stack_length_mm = 83.82, stator_outer_radius_mm = 134.6, stator_bore_radius_mm = 80.96, slot_shoulder_x_mm = 81.97, slot_width_shoulder_mm = 3.15, slot_width_round_mm = 5.639, slot_round_centre_x_mm = 111.7, slot_opening_mm = 1.93, liner_thickness_mm = 0.25, copper_area_per_slot_mm2 = 76.4, rotor_outer_radius_mm = 80.19, rotor_inner_radius_mm = 55.32, end_connection_length_mm = 120.6, end_extension_mm = 38.4, impregnant_conductivity_W_mK = 0.25, copper_conductivity_W_mK = 390, liner_conductivity_W_mK = 0.2, lamination_conductivity_W_mK = 28, housing_conductivity_W_mK = 160, housing_wall_mm = 6, interface_gap_mm = 0.037, jacket_htc_W_m2K = 3000, coolant_temperature_C = 65, air_gap_h_factor = 1, end_space_h_scale = 1, winding_k_scale = 1, teeth_iron_fraction = 0.75, h_winding_end_space_k1 = 15, h_winding_end_space_k2 = 6, h_winding_end_space_k3 = 0.9, h_housing_end_space_k1 = 20, h_housing_end_space_k2 = 8.7, h_housing_end_space_k3 = 0.7, h_rotor_end_space_k1 = 41.4, h_rotor_end_space_k2 = 6.22, h_rotor_end_space_k3 = 1, lut_run_cold = 20261123-230647_motor_prius_lut_cold_rev5,20261124-004731_motor_prius_lut_cold_lowiq_rev5, lut_run_hot = 20261124-014553_motor_prius_lut_hot_rev5,20261124-031723_motor_prius_lut_hot_lowiq_rev5, efficiency_run = 20261124-062847_motor_prius_efficiency_rev5, series_turns_per_phase = 72, turn_copper_area_mm2 = 8.492, stack_length_m = 0.08382, end_connection_length_m = 0.1206, copper_resistivity_20C_ohm_m = 1.72e-08, copper_alpha_per_K = 0.00393, phase_resistance_measured_ohm = 0.069, phase_resistance_measured_at_C = 21, bus_voltage_V = 500, current_limit_design_A = 212, winding_hotspot_limit_C = 180, magnet_limit_C = 150, speed_min_rpm = 500, speed_max_rpm = 6000, speed_step_rpm = 250, hot_corner_winding_C = 100, fe_reference_speed_rpm = 3000, scenario = teeth_0p75

Derived: phase_resistance_20C_ohm = 0.06873

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-TH1 | 27.6 kW | >= 25 | 2.6 | **PASS (unverified)** | [point.json](points/p09_teeth_0p75/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| energy_balance | max over every network solve of |losses in - heat to the coolant| / losses | 1.86e-12 | 1e-09 | PASS |
| coupling_convergence | max over the envelope and hot-corner searches of the last temperature change of the loss-temperature iteration (K) | 4.32e-04 | 1e-01 | PASS |
| efficiency_consistency | max relative difference of the total loss at fixed hot temperatures (windings 100 C, magnets 80 C) against the efficiency run's hot map at five points | 2.98e-16 | 1e-06 | PASS |
| fe_balance | CalculiX section: |generation - film heat out| / generation, worst mesh | 5.95e-05 | 1e-03 | PASS |
| fe_mesh | CalculiX section: discretization uncertainty (GCI or spread) of the winding peak rise | 0.00e+00 | 1e-02 | PASS |
| section_wind_mean | |network - CalculiX| / CalculiX, winding mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 4.66e-02 | 5e-02 | PASS |
| section_wind_peak | |network - CalculiX| / CalculiX, winding peak (network: slab factor 1.5) rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 5.45e-02 | 5e-02 | FAIL |
| section_teeth_mean | |network - CalculiX| / CalculiX, teeth mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 3.41e-02 | 5e-02 | PASS |
| section_yoke_mean | |network - CalculiX| / CalculiX, yoke mean rise above the coolant, cross-section with the same losses and boundary conditions (model form) | 6.69e-03 | 5e-02 | PASS |

![p09_teeth_0p75 response](points/p09_teeth_0p75/response.png)

## Limitations

- No test data: thermal is not in the agreed ORNL validation set.
- The CalculiX check covers the stator cross-section only; the axial copper paths, end windings, end space and rotor are network-only (their T-equivalents are exact for 1D conduction, tests/test_motor_thermal.py).
- Steady state only: no transient (peak) ratings.
- Material conductivities and the slot liner are typical values, not measured on this machine.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

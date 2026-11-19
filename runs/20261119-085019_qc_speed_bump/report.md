# Engineering review report: qc_speed_bump

- **Run:** `20261119-085019_qc_speed_bump`
- **Generated:** 2026-11-19T14:01:08+00:00
- **Case file SHA-256:** `4661d902782460db0de949cd873a16da81a533c9ee5bb05aa86dbf04ea0d56ec`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2; Windows-11-10.0.26100-SP0
- **Tools:** scipy 1.18.1
- **Code version:** git `833aecbcf507cb002cdf90362e408dcdafe22ed0` (uncommitted changes present)
- **Simulation status:** completed
- **Verification status:** PASS

## Scope

Linear 2-DOF quarter car crossing a 40 mm x 1.0 m (1 - cos) speed bump at 5 m/s (18 km/h); wheel-rate damping swept from 600 to 3500 N.s/m against peak body acceleration, suspension travel, and dynamic tire load requirements.

**Assumptions**

- Linear spring, damper, and tire; parameters are wheel rates (motion ratio already applied).
- Point-contact tire with no tire damping; the tire never leaves the road (checked: no_wheel_lift).
- Coordinates from static equilibrium; gravity cancels in the linear model.
- Rigid body above one corner (no pitch/roll coupling, no seat or occupant dynamics).
- Suspension travel stays inside the linear range (no bump-stop contact); REQ-QB2 bounds it.

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-QB1 | Peak vertical body acceleration over the bump shall not exceed 4.0 m/s^2 (comfort). | `peak_body_accel_m_per_s2` | <= 4 m/s^2 |
| REQ-QB2 | Suspension travel shall stay within +/-40 mm of static (no bump-stop contact). | `max_suspension_travel_mm` | <= 40 mm |
| REQ-QB3 | Dynamic tire load shall stay within +/-70 % of static load (road holding). | `max_tire_load_ratio` | <= 0.7 - |

## Summary across points

| Point | damping_N_s_per_m | REQ-QB1 | REQ-QB2 | REQ-QB3 | Checks |
|---|---|---|---|---|---|
| p00_damping_N_s_per_m-600 | 600 | 3.04 m/s^2: **PASS** | 37.88 mm: **PASS** | 0.4102 -: **PASS** | 6/6 PASS |
| p01_damping_N_s_per_m-1000 | 1000 | 3.56 m/s^2: **PASS** | 35.95 mm: **PASS** | 0.439 -: **PASS** | 6/6 PASS |
| p02_damping_N_s_per_m-1500 | 1500 | 4.176 m/s^2: **FAIL** | 33.87 mm: **PASS** | 0.4768 -: **PASS** | 6/6 PASS |
| p03_damping_N_s_per_m-2200 | 2200 | 5.413 m/s^2: **FAIL** | 31.38 mm: **PASS** | 0.5309 -: **PASS** | 6/6 PASS |
| p04_damping_N_s_per_m-3500 | 3500 | 8.16 m/s^2: **FAIL** | 27.6 mm: **PASS** | 0.8204 -: **FAIL** | 6/6 PASS |

![Requirement metrics across the sweep](sweep.png)

## Point details

### p00_damping_N_s_per_m-600

Parameters: sprung_mass_kg = 350, unsprung_mass_kg = 45, suspension_stiffness_N_per_m = 2.2e+04, damping_N_s_per_m = 600, tire_stiffness_N_per_m = 2.2e+05, road = bump, speed_m_per_s = 5, bump_height_m = 0.04, bump_length_m = 1

Derived: ride_rate_N_per_m = 2e+04, body_frequency_Hz_approx = 1.203, wheel_hop_frequency_Hz_approx = 11.67, body_damping_ratio_approx = 0.1134, static_tire_load_N = 3874, slowest_decay_rate_per_s = 0.7084

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-QB1 | 3.04 m/s^2 | <= 4 | 0.96 | **PASS** | [point.json](points/p00_damping_N_s_per_m-600/point.json) |
| REQ-QB2 | 37.88 mm | <= 40 | 2.12 | **PASS** | [point.json](points/p00_damping_N_s_per_m-600/point.json) |
| REQ-QB3 | 0.4102 - | <= 0.7 | 0.29 | **PASS** | [point.json](points/p00_damping_N_s_per_m-600/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| energy_balance | |W_road - (dE + E_dissipated)| / integral |P_road| dt | 2.26e-09 | 1e-04 | PASS |
| solver_convergence | max |z(tol) - z(tol/100)| / max |z| (body and wheel) | 2.25e-09 | 1e-06 | PASS |
| no_wheel_lift (validity) | max dynamic tire load / static load (linear tire valid only < 1) | 3.28e-01 | 1e+00 | PASS |
| reference_agreement | max |z_num - z_ref| / bump height (body and wheel; matrix-exponential ref) | 1.66e-07 | 1e-05 | PASS |
| peak_accel_reference | |peak accel num - peak accel ref| / peak accel ref | 2.56e-07 | 1e-04 | PASS |
| return_to_rest | max(|zs(t_end)|, |zu(t_end)|) / bump height | 3.84e-04 | 1e-03 | PASS |

![p00_damping_N_s_per_m-600 response](points/p00_damping_N_s_per_m-600/response.png)

### p01_damping_N_s_per_m-1000

Parameters: sprung_mass_kg = 350, unsprung_mass_kg = 45, suspension_stiffness_N_per_m = 2.2e+04, damping_N_s_per_m = 1000, tire_stiffness_N_per_m = 2.2e+05, road = bump, speed_m_per_s = 5, bump_height_m = 0.04, bump_length_m = 1

Derived: ride_rate_N_per_m = 2e+04, body_frequency_Hz_approx = 1.203, wheel_hop_frequency_Hz_approx = 11.67, body_damping_ratio_approx = 0.189, static_tire_load_N = 3874, slowest_decay_rate_per_s = 1.188

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-QB1 | 3.56 m/s^2 | <= 4 | 0.44 | **PASS** | [point.json](points/p01_damping_N_s_per_m-1000/point.json) |
| REQ-QB2 | 35.95 mm | <= 40 | 4.05 | **PASS** | [point.json](points/p01_damping_N_s_per_m-1000/point.json) |
| REQ-QB3 | 0.439 - | <= 0.7 | 0.261 | **PASS** | [point.json](points/p01_damping_N_s_per_m-1000/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| energy_balance | |W_road - (dE + E_dissipated)| / integral |P_road| dt | 2.99e-09 | 1e-04 | PASS |
| solver_convergence | max |z(tol) - z(tol/100)| / max |z| (body and wheel) | 3.93e-08 | 1e-06 | PASS |
| no_wheel_lift (validity) | max dynamic tire load / static load (linear tire valid only < 1) | 2.68e-01 | 1e+00 | PASS |
| reference_agreement | max |z_num - z_ref| / bump height (body and wheel; matrix-exponential ref) | 1.62e-07 | 1e-05 | PASS |
| peak_accel_reference | |peak accel num - peak accel ref| / peak accel ref | 2.71e-07 | 1e-04 | PASS |
| return_to_rest | max(|zs(t_end)|, |zu(t_end)|) / bump height | 4.41e-06 | 1e-03 | PASS |

![p01_damping_N_s_per_m-1000 response](points/p01_damping_N_s_per_m-1000/response.png)

### p02_damping_N_s_per_m-1500

Parameters: sprung_mass_kg = 350, unsprung_mass_kg = 45, suspension_stiffness_N_per_m = 2.2e+04, damping_N_s_per_m = 1500, tire_stiffness_N_per_m = 2.2e+05, road = bump, speed_m_per_s = 5, bump_height_m = 0.04, bump_length_m = 1

Derived: ride_rate_N_per_m = 2e+04, body_frequency_Hz_approx = 1.203, wheel_hop_frequency_Hz_approx = 11.67, body_damping_ratio_approx = 0.2835, static_tire_load_N = 3874, slowest_decay_rate_per_s = 1.803

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-QB1 | 4.176 m/s^2 | <= 4 | -0.176 | **FAIL** | [point.json](points/p02_damping_N_s_per_m-1500/point.json) |
| REQ-QB2 | 33.87 mm | <= 40 | 6.13 | **PASS** | [point.json](points/p02_damping_N_s_per_m-1500/point.json) |
| REQ-QB3 | 0.4768 - | <= 0.7 | 0.223 | **PASS** | [point.json](points/p02_damping_N_s_per_m-1500/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| energy_balance | |W_road - (dE + E_dissipated)| / integral |P_road| dt | 9.12e-10 | 1e-04 | PASS |
| solver_convergence | max |z(tol) - z(tol/100)| / max |z| (body and wheel) | 1.18e-09 | 1e-06 | PASS |
| no_wheel_lift (validity) | max dynamic tire load / static load (linear tire valid only < 1) | 3.45e-01 | 1e+00 | PASS |
| reference_agreement | max |z_num - z_ref| / bump height (body and wheel; matrix-exponential ref) | 1.30e-07 | 1e-05 | PASS |
| peak_accel_reference | |peak accel num - peak accel ref| / peak accel ref | 2.79e-07 | 1e-04 | PASS |
| return_to_rest | max(|zs(t_end)|, |zu(t_end)|) / bump height | 1.37e-08 | 1e-03 | PASS |

![p02_damping_N_s_per_m-1500 response](points/p02_damping_N_s_per_m-1500/response.png)

### p03_damping_N_s_per_m-2200

Parameters: sprung_mass_kg = 350, unsprung_mass_kg = 45, suspension_stiffness_N_per_m = 2.2e+04, damping_N_s_per_m = 2200, tire_stiffness_N_per_m = 2.2e+05, road = bump, speed_m_per_s = 5, bump_height_m = 0.04, bump_length_m = 1

Derived: ride_rate_N_per_m = 2e+04, body_frequency_Hz_approx = 1.203, wheel_hop_frequency_Hz_approx = 11.67, body_damping_ratio_approx = 0.4158, static_tire_load_N = 3874, slowest_decay_rate_per_s = 2.714

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-QB1 | 5.413 m/s^2 | <= 4 | -1.41 | **FAIL** | [point.json](points/p03_damping_N_s_per_m-2200/point.json) |
| REQ-QB2 | 31.38 mm | <= 40 | 8.62 | **PASS** | [point.json](points/p03_damping_N_s_per_m-2200/point.json) |
| REQ-QB3 | 0.5309 - | <= 0.7 | 0.169 | **PASS** | [point.json](points/p03_damping_N_s_per_m-2200/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| energy_balance | |W_road - (dE + E_dissipated)| / integral |P_road| dt | 5.04e-10 | 1e-04 | PASS |
| solver_convergence | max |z(tol) - z(tol/100)| / max |z| (body and wheel) | 8.17e-10 | 1e-06 | PASS |
| no_wheel_lift (validity) | max dynamic tire load / static load (linear tire valid only < 1) | 5.29e-01 | 1e+00 | PASS |
| reference_agreement | max |z_num - z_ref| / bump height (body and wheel; matrix-exponential ref) | 1.21e-07 | 1e-05 | PASS |
| peak_accel_reference | |peak accel num - peak accel ref| / peak accel ref | 1.78e-07 | 1e-04 | PASS |
| return_to_rest | max(|zs(t_end)|, |zu(t_end)|) / bump height | 6.39e-13 | 1e-03 | PASS |

![p03_damping_N_s_per_m-2200 response](points/p03_damping_N_s_per_m-2200/response.png)

### p04_damping_N_s_per_m-3500

Parameters: sprung_mass_kg = 350, unsprung_mass_kg = 45, suspension_stiffness_N_per_m = 2.2e+04, damping_N_s_per_m = 3500, tire_stiffness_N_per_m = 2.2e+05, road = bump, speed_m_per_s = 5, bump_height_m = 0.04, bump_length_m = 1

Derived: ride_rate_N_per_m = 2e+04, body_frequency_Hz_approx = 1.203, wheel_hop_frequency_Hz_approx = 11.67, body_damping_ratio_approx = 0.6614, static_tire_load_N = 3874, slowest_decay_rate_per_s = 4.713

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-QB1 | 8.16 m/s^2 | <= 4 | -4.16 | **FAIL** | [point.json](points/p04_damping_N_s_per_m-3500/point.json) |
| REQ-QB2 | 27.6 mm | <= 40 | 12.4 | **PASS** | [point.json](points/p04_damping_N_s_per_m-3500/point.json) |
| REQ-QB3 | 0.8204 - | <= 0.7 | -0.12 | **FAIL** | [point.json](points/p04_damping_N_s_per_m-3500/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| energy_balance | |W_road - (dE + E_dissipated)| / integral |P_road| dt | 8.46e-11 | 1e-04 | PASS |
| solver_convergence | max |z(tol) - z(tol/100)| / max |z| (body and wheel) | 5.50e-10 | 1e-06 | PASS |
| no_wheel_lift (validity) | max dynamic tire load / static load (linear tire valid only < 1) | 8.20e-01 | 1e+00 | PASS |
| reference_agreement | max |z_num - z_ref| / bump height (body and wheel; matrix-exponential ref) | 1.17e-07 | 1e-05 | PASS |
| peak_accel_reference | |peak accel num - peak accel ref| / peak accel ref | 1.84e-07 | 1e-04 | PASS |
| return_to_rest | max(|zs(t_end)|, |zu(t_end)|) / bump height | 1.20e-13 | 1e-03 | PASS |

![p04_damping_N_s_per_m-3500 response](points/p04_damping_N_s_per_m-3500/response.png)

## Limitations

- Synthetic parameters; not calibrated to any vehicle.
- Peak acceleration is unweighted; ISO 2631 frequency weighting is not applied.
- Checks establish numerical verification and model-validity limits only; no test data.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

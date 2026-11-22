# Engineering review report: pipe_rans_wf_yplus

- **Run:** `20261122-140211_pipe_rans_wf_yplus`
- **Generated:** 2026-11-22T19:23:13+00:00
- **Case file SHA-256:** `f922fc7f89a4f8ee4447b1a5c29e1663f061b3b06ad3917a3f50ce7cf6ca976f`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Tools:** openfoam_bashrc /opt/openfoam14/etc/bashrc; openfoam_version 14; openfoam_package openfoam14 20261008; linux Ubuntu 22.04.5 LTS
- **Code version:** git `b6c7ccca0ae55207c07dd5fb5a217b36fad0f5a5`
- **Simulation status:** completed
- **Verification status:** FAIL

> **Warning:** verification did not pass for every point. Requirement verdicts marked *(unverified)* are not supported by evidence and must not be used for acceptance.

## Scope

Fully developed turbulent pipe flow at Re 2e6 (D 0.1 m, nu 1e-6 m^2/s), axisymmetric periodic wedge, RANS k-omega SST with wall functions; first-cell placement (first-face y+ 60 / 100 / 160 / 250 / 400) on 80 radial cells; friction factor against Prandtl's smooth-pipe law.

**Assumptions**

- Fully developed, steady, incompressible, axisymmetric mean flow in a hydraulically smooth pipe.
- RANS with the k-omega SST model (openfoam.org v14 coefficients); its form error is what this study measures.
- Hydraulic diameter of the wedge 2 R cos(2.5 deg) (its wall is a flat face): 0.1 % below D, used consistently.

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-T1 | The predicted friction factor shall be within 5 % of Prandtl's smooth-pipe law (the Moody chart's smooth curve), a usable accuracy for pressure-drop budgets. | `friction_abs_dev_prandtl_pct` | <= 5 % |

## Summary across points

| Point | scenario | REQ-T1 | Checks |
|---|---|---|---|
| p00_yp60 | yp60 | 5.226 %: **FAIL (unverified)** | 5/7 FAIL |
| p01_yp100 | yp100 | 5.166 %: **FAIL (unverified)** | 6/7 FAIL |
| p02_yp160 | yp160 | 5.068 %: **FAIL (unverified)** | 6/7 FAIL |
| p03_yp250 | yp250 | 4.935 %: **PASS** | 7/7 PASS |
| p04_yp400 | yp400 | 4.754 %: **PASS** | 7/7 PASS |

![Requirement metrics across the sweep](sweep.png)

## Point details

### p00_yp60

Parameters: diameter_m = 0.1, reynolds_number = 2e+06, kinematic_viscosity_m2_per_s = 1e-06, n_radial = 80, first_cell_yplus = 60, wall_treatment = wall_function, turbulence_model = kOmegaSST, scenario = yp60

Derived: friction_prandtl = 0.01037, friction_petukhov = 0.01037, friction_blasius = 0.008414

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-T1 | 5.226 % | <= 5 | -0.226 | **FAIL (unverified)** | [point.json](points/p00_yp60/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| mesh | checkMesh reports Mesh OK (1 = failed) | 0.00e+00 | 5e-01 | PASS |
| force_balance | |f from the wall shear - f from the applied pressure gradient| / f (periodic flow: dp/dx A = tau_w P exactly) | 5.62e-11 | 1e-04 | PASS |
| bulk_velocity | |bulk velocity of the cell field - target| / target | 1.63e-13 | 1e-06 | PASS |
| iterative_convergence | max change of the pressure gradient over the last 10 % of iterations / final | 2.65e-09 | 1e-06 | PASS |
| wall_uniform | spread of the wall shear along the wall / mean (fully developed: 0) | 0.00e+00 | 1e-04 | PASS |
| yplus_range (validity) | first-cell y+ against the wall treatment's range (below 1 = inside) | 1.02e+00 | 1e+00 | FAIL |
| log_law | max |u+ - (ln y+ / 0.41 + 5.2)| / u+ for 50 <= y+ <= 0.15 Re_tau (model form: the log law's constants scatter by a few per cent between experiments) | 5.15e-02 | 5e-02 | FAIL |

![p00_yp60 response](points/p00_yp60/response.png)

### p01_yp100

Parameters: diameter_m = 0.1, reynolds_number = 2e+06, kinematic_viscosity_m2_per_s = 1e-06, n_radial = 80, first_cell_yplus = 100, wall_treatment = wall_function, turbulence_model = kOmegaSST, scenario = yp100

Derived: friction_prandtl = 0.01037, friction_petukhov = 0.01037, friction_blasius = 0.008414

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-T1 | 5.166 % | <= 5 | -0.166 | **FAIL (unverified)** | [point.json](points/p01_yp100/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| mesh | checkMesh reports Mesh OK (1 = failed) | 0.00e+00 | 5e-01 | PASS |
| force_balance | |f from the wall shear - f from the applied pressure gradient| / f (periodic flow: dp/dx A = tau_w P exactly) | 3.38e-11 | 1e-04 | PASS |
| bulk_velocity | |bulk velocity of the cell field - target| / target | 6.04e-14 | 1e-06 | PASS |
| iterative_convergence | max change of the pressure gradient over the last 10 % of iterations / final | 1.06e-09 | 1e-06 | PASS |
| wall_uniform | spread of the wall shear along the wall / mean (fully developed: 0) | 0.00e+00 | 1e-04 | PASS |
| yplus_range (validity) | first-cell y+ against the wall treatment's range (below 1 = inside) | 6.12e-01 | 1e+00 | PASS |
| log_law | max |u+ - (ln y+ / 0.41 + 5.2)| / u+ for 50 <= y+ <= 0.15 Re_tau (model form: the log law's constants scatter by a few per cent between experiments) | 5.12e-02 | 5e-02 | FAIL |

![p01_yp100 response](points/p01_yp100/response.png)

### p02_yp160

Parameters: diameter_m = 0.1, reynolds_number = 2e+06, kinematic_viscosity_m2_per_s = 1e-06, n_radial = 80, first_cell_yplus = 160, wall_treatment = wall_function, turbulence_model = kOmegaSST, scenario = yp160

Derived: friction_prandtl = 0.01037, friction_petukhov = 0.01037, friction_blasius = 0.008414

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-T1 | 5.068 % | <= 5 | -0.0675 | **FAIL (unverified)** | [point.json](points/p02_yp160/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| mesh | checkMesh reports Mesh OK (1 = failed) | 0.00e+00 | 5e-01 | PASS |
| force_balance | |f from the wall shear - f from the applied pressure gradient| / f (periodic flow: dp/dx A = tau_w P exactly) | 8.70e-12 | 1e-04 | PASS |
| bulk_velocity | |bulk velocity of the cell field - target| / target | 2.32e-13 | 1e-06 | PASS |
| iterative_convergence | max change of the pressure gradient over the last 10 % of iterations / final | 7.91e-10 | 1e-06 | PASS |
| wall_uniform | spread of the wall shear along the wall / mean (fully developed: 0) | 0.00e+00 | 1e-04 | PASS |
| yplus_range (validity) | first-cell y+ against the wall treatment's range (below 1 = inside) | 3.82e-01 | 1e+00 | PASS |
| log_law | max |u+ - (ln y+ / 0.41 + 5.2)| / u+ for 50 <= y+ <= 0.15 Re_tau (model form: the log law's constants scatter by a few per cent between experiments) | 5.05e-02 | 5e-02 | FAIL |

![p02_yp160 response](points/p02_yp160/response.png)

### p03_yp250

Parameters: diameter_m = 0.1, reynolds_number = 2e+06, kinematic_viscosity_m2_per_s = 1e-06, n_radial = 80, first_cell_yplus = 250, wall_treatment = wall_function, turbulence_model = kOmegaSST, scenario = yp250

Derived: friction_prandtl = 0.01037, friction_petukhov = 0.01037, friction_blasius = 0.008414

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-T1 | 4.935 % | <= 5 | 0.0647 | **PASS** | [point.json](points/p03_yp250/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| mesh | checkMesh reports Mesh OK (1 = failed) | 0.00e+00 | 5e-01 | PASS |
| force_balance | |f from the wall shear - f from the applied pressure gradient| / f (periodic flow: dp/dx A = tau_w P exactly) | 4.80e-12 | 1e-04 | PASS |
| bulk_velocity | |bulk velocity of the cell field - target| / target | 1.08e-14 | 1e-06 | PASS |
| iterative_convergence | max change of the pressure gradient over the last 10 % of iterations / final | 6.43e-10 | 1e-06 | PASS |
| wall_uniform | spread of the wall shear along the wall / mean (fully developed: 0) | 0.00e+00 | 1e-04 | PASS |
| yplus_range (validity) | first-cell y+ against the wall treatment's range (below 1 = inside) | 4.09e-01 | 1e+00 | PASS |
| log_law | max |u+ - (ln y+ / 0.41 + 5.2)| / u+ for 50 <= y+ <= 0.15 Re_tau (model form: the log law's constants scatter by a few per cent between experiments) | 4.96e-02 | 5e-02 | PASS |

![p03_yp250 response](points/p03_yp250/response.png)

### p04_yp400

Parameters: diameter_m = 0.1, reynolds_number = 2e+06, kinematic_viscosity_m2_per_s = 1e-06, n_radial = 80, first_cell_yplus = 400, wall_treatment = wall_function, turbulence_model = kOmegaSST, scenario = yp400

Derived: friction_prandtl = 0.01037, friction_petukhov = 0.01037, friction_blasius = 0.008414

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-T1 | 4.754 % | <= 5 | 0.246 | **PASS** | [point.json](points/p04_yp400/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| mesh | checkMesh reports Mesh OK (1 = failed) | 0.00e+00 | 5e-01 | PASS |
| force_balance | |f from the wall shear - f from the applied pressure gradient| / f (periodic flow: dp/dx A = tau_w P exactly) | 6.17e-12 | 1e-04 | PASS |
| bulk_velocity | |bulk velocity of the cell field - target| / target | 4.32e-14 | 1e-06 | PASS |
| iterative_convergence | max change of the pressure gradient over the last 10 % of iterations / final | 6.47e-10 | 1e-06 | PASS |
| wall_uniform | spread of the wall shear along the wall / mean (fully developed: 0) | 0.00e+00 | 1e-04 | PASS |
| yplus_range (validity) | first-cell y+ against the wall treatment's range (below 1 = inside) | 6.54e-01 | 1e+00 | PASS |
| log_law | max |u+ - (ln y+ / 0.41 + 5.2)| / u+ for 50 <= y+ <= 0.15 Re_tau (model form: the log law's constants scatter by a few per cent between experiments) | 4.82e-02 | 5e-02 | PASS |

![p04_yp400 response](points/p04_yp400/response.png)

## Limitations

- Smooth walls only; roughness (the Colebrook range) not modelled.
- The reference is a correlation of measurements (about +-2 % scatter in Nikuradse's smooth-pipe data), not the measurements themselves.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

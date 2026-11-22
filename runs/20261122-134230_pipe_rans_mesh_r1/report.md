# Engineering review report: pipe_rans_mesh_r1

- **Run:** `20261122-134230_pipe_rans_mesh_r1`
- **Generated:** 2026-11-22T20:37:12+00:00
- **Case file SHA-256:** `889d685e5a45d4a753bbe25518743eccf2d29b895bde3394a2a44cde6f3d9c74`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Tools:** openfoam_bashrc /opt/openfoam14/etc/bashrc; openfoam_version 14; openfoam_package openfoam14 20261008; linux Ubuntu 22.04.5 LTS
- **Code version:** git `a441f36c118d28d971b16bcce55b0c0d553dc564`
- **Simulation status:** completed
- **Verification status:** FAIL

> **Warning:** verification did not pass for every point. Requirement verdicts marked *(unverified)* are not supported by evidence and must not be used for acceptance.

## Scope

Fully developed turbulent pipe flow, Re 1e5 (D 0.1 m, nu 1e-6 m^2/s), axisymmetric periodic wedge, RANS k-omega SST, low-Reynolds wall treatment; mesh study on the radial cells (80 / 160 / 320, wall cell halved with them); friction factor against Prandtl's smooth-pipe law.

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
| p00_n80 | n80 | 0.9037 %: **PASS** | 7/7 PASS |
| p01_n160 | n160 | 0.7372 %: **PASS (unverified)** | 6/7 FAIL |
| p02_n320 | n320 | 0.7013 %: **PASS (unverified)** | 5/7 FAIL |

## Run-level checks

Checks that use several points together (for example mesh convergence).

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| discretization_friction_factor | relative discretization uncertainty of the friction factor, oscillatory (R = -0.022): 1.25 x half-range of the 3 finest solutions | 0.0102 | 0.01 | FAIL |

A failed run-level check withholds the verdicts of requirements on `friction_factor` at every point: they are marked *(unverified)* in the table above.

![Requirement metrics across the sweep](sweep.png)

## Point details

### p00_n80

Parameters: diameter_m = 0.1, reynolds_number = 1e+05, kinematic_viscosity_m2_per_s = 1e-06, n_radial = 80, first_cell_yplus = 0.5, wall_treatment = low_re, turbulence_model = kOmegaSST, scenario = n80

Derived: friction_prandtl = 0.01799, friction_petukhov = 0.01799, friction_blasius = 0.01779

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-T1 | 0.9037 % | <= 5 | 4.1 | **PASS** | [point.json](points/p00_n80/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| mesh | checkMesh reports Mesh OK (1 = failed) | 0.00e+00 | 5e-01 | PASS |
| force_balance | |f from the wall shear - f from the applied pressure gradient| / f (periodic flow: dp/dx A = tau_w P exactly) | 2.34e-11 | 1e-04 | PASS |
| bulk_velocity | |bulk velocity of the cell field - target| / target | 3.70e-13 | 1e-06 | PASS |
| iterative_convergence | max change of the pressure gradient over the last 10 % of iterations / final | 1.47e-09 | 1e-06 | PASS |
| wall_uniform | spread of the wall shear along the wall / mean (fully developed: 0) | 0.00e+00 | 1e-04 | PASS |
| yplus_range (validity) | first-cell y+ against the wall treatment's range (below 1 = inside) | 2.49e-01 | 1e+00 | PASS |
| log_law | max |u+ - (ln y+ / 0.41 + 5.2)| / u+ for 50 <= y+ <= 0.15 Re_tau (model form: the log law's constants scatter by a few per cent between experiments) | 3.41e-02 | 5e-02 | PASS |

![p00_n80 response](points/p00_n80/response.png)

### p01_n160

Parameters: diameter_m = 0.1, reynolds_number = 1e+05, kinematic_viscosity_m2_per_s = 1e-06, n_radial = 160, first_cell_yplus = 0.25, wall_treatment = low_re, turbulence_model = kOmegaSST, scenario = n160

Derived: friction_prandtl = 0.01799, friction_petukhov = 0.01799, friction_blasius = 0.01779

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-T1 | 0.7372 % | <= 5 | 4.26 | **PASS (unverified)** | [point.json](points/p01_n160/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| mesh | checkMesh reports Mesh OK (1 = failed) | 0.00e+00 | 5e-01 | PASS |
| force_balance | |f from the wall shear - f from the applied pressure gradient| / f (periodic flow: dp/dx A = tau_w P exactly) | 4.97e-05 | 1e-04 | PASS |
| bulk_velocity | |bulk velocity of the cell field - target| / target | 3.33e-16 | 1e-06 | PASS |
| iterative_convergence | max change of the pressure gradient over the last 10 % of iterations / final | 8.99e-05 | 1e-06 | FAIL |
| wall_uniform | spread of the wall shear along the wall / mean (fully developed: 0) | 0.00e+00 | 1e-04 | PASS |
| yplus_range (validity) | first-cell y+ against the wall treatment's range (below 1 = inside) | 1.25e-01 | 1e+00 | PASS |
| log_law | max |u+ - (ln y+ / 0.41 + 5.2)| / u+ for 50 <= y+ <= 0.15 Re_tau (model form: the log law's constants scatter by a few per cent between experiments) | 2.54e-02 | 5e-02 | PASS |

![p01_n160 response](points/p01_n160/response.png)

### p02_n320

Parameters: diameter_m = 0.1, reynolds_number = 1e+05, kinematic_viscosity_m2_per_s = 1e-06, n_radial = 320, first_cell_yplus = 0.125, wall_treatment = low_re, turbulence_model = kOmegaSST, scenario = n320

Derived: friction_prandtl = 0.01799, friction_petukhov = 0.01799, friction_blasius = 0.01779

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-T1 | 0.7013 % | <= 5 | 4.3 | **PASS (unverified)** | [point.json](points/p02_n320/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| mesh | checkMesh reports Mesh OK (1 = failed) | 0.00e+00 | 5e-01 | PASS |
| force_balance | |f from the wall shear - f from the applied pressure gradient| / f (periodic flow: dp/dx A = tau_w P exactly) | 7.16e-03 | 1e-04 | FAIL |
| bulk_velocity | |bulk velocity of the cell field - target| / target | 6.99e-15 | 1e-06 | PASS |
| iterative_convergence | max change of the pressure gradient over the last 10 % of iterations / final | 4.23e-03 | 1e-06 | FAIL |
| wall_uniform | spread of the wall shear along the wall / mean (fully developed: 0) | 0.00e+00 | 1e-04 | PASS |
| yplus_range (validity) | first-cell y+ against the wall treatment's range (below 1 = inside) | 6.27e-02 | 1e+00 | PASS |
| log_law | max |u+ - (ln y+ / 0.41 + 5.2)| / u+ for 50 <= y+ <= 0.15 Re_tau (model form: the log law's constants scatter by a few per cent between experiments) | 2.78e-02 | 5e-02 | PASS |

![p02_n320 response](points/p02_n320/response.png)

## Limitations

- Smooth walls only; roughness (the Colebrook range) not modelled.
- The reference is a correlation of measurements (about +-2 % scatter in Nikuradse's smooth-pipe data), not the measurements themselves.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

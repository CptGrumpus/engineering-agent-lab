# Engineering review report: strut_mesh

- **Run:** `20261120-233637_strut_mesh`
- **Generated:** 2026-11-21T04:48:35+00:00
- **Case file SHA-256:** `2a9ad4033d7b06fc809a967c6752b43652b76e8032652ee502d475f889acd079`
- **Environment:** Python 3.14.10, numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, cadquery 2.8.0; Windows-11-10.0.26100-SP0
- **Tools:** CalculiX This is Version 2.22
- **Code version:** git `356901c82d9a18b1bef3dcca4aad4413874a0b7d` (uncommitted changes present)
- **Simulation status:** completed
- **Verification status:** PASS

## Scope

Mesh study at L = 600 mm (next to the acceptance boundary), 4 / 3 / 2 mm C3D8I. Pinned-pinned 6061-T6 strut, 25 x 16 mm solid section, in compression: CalculiX linear buckling and a geometrically nonlinear analysis with an L/1000 initial bow to first yield, at L = 400 / 500 / 600 / 700 mm; checked against Euler-Engesser, the amplification law, the Southwell plot and Perry-Robertson.

**Assumptions**

- Pins on the centroidal axis at both ends (knife-edge line supports across the width at mid-thickness).
- Initial bow e0 = L/1000 in the weak direction, half-sine shaped (the first buckling mode): synthetic tolerance.
- Load axial and concentric at the ends, uniform over the end face (dead load).
- Linear elastic material up to first yield (6061-T6, E = 68.9 GPa, yield 276 MPa); the analysis stops just past first yield.
- Elastic buckling governs; checked: Euler stress at most half the yield stress (Johnson range otherwise).
- Moderate deflection at first yield; checked: below 5 % of the length.

## Requirements

| ID | Requirement | Metric | Limit |
|---|---|---|---|
| REQ-K1 | The strut, with an L/1000 initial bow, shall reach 16 kN (twice the 8 kN service load) before first yield. | `first_yield_load_N` | >= 16000 N |

## Summary across points

| Point | element_size_mm | REQ-K1 | Checks |
|---|---|---|---|
| p00_element_size_mm-4 | 4 | 1.531e+04 N: **FAIL** | 11/11 PASS |
| p01_element_size_mm-3 | 3 | 1.531e+04 N: **FAIL** | 11/11 PASS |
| p02_element_size_mm-2 | 2 | 1.531e+04 N: **FAIL** | 11/11 PASS |

## Run-level checks

Checks that use several points together (for example mesh convergence).

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| discretization_critical_load_N | relative discretization uncertainty of critical_load_N, monotone (R = 0.495): GCI_fine, observed order 2.37, extrapolated 16081.8 | 2.75e-05 | 0.01 | PASS |
| discretization_first_yield_load_N | relative discretization uncertainty of first_yield_load_N, monotone (R = 0.522): GCI_fine, observed order 2.22, extrapolated 15308.6 | 2.85e-05 | 0.01 | PASS |

![Requirement metrics across the sweep](sweep.png)

## Point details

### p00_element_size_mm-4

Parameters: length_mm = 600, width_mm = 25, thickness_mm = 16, youngs_modulus_MPa = 6.89e+04, poisson_ratio = 0.33, yield_strength_MPa = 276, element_size_mm = 4, imperfection_over_length = 0.001

Derived: slenderness_L_over_r = 129.9, euler_load_N = 1.612e+04, critical_load_engesser_N = 1.609e+04, euler_stress_MPa = 40.3, johnson_stress_MPa = -196.6, perry_robertson_load_N = 1.55e+04, squash_load_N = 1.104e+05, thickness_over_length = 0.02667

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-K1 | 1.531e+04 N | >= 16000 | -690 | **FAIL** | [point.json](points/p00_element_size_mm-4/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| buckling_reference | |P_cr FE - Euler with Engesser shear correction| / reference (model form) | 3.64e-04 | 1e-02 | PASS |
| mode_shape | 1 - MAC(first mode on the axis, half sine) (weak-axis buckling) | 6.26e-12 | 1e-03 | PASS |
| southwell_vs_eigenvalue | |P_cr from the Southwell plot of the nonlinear run - eigenvalue| / eigenvalue (two independent FE routes) | 1.11e-04 | 1e-02 | PASS |
| southwell_imperfection | |initial bow recovered by the Southwell fit - imposed| / imposed | 2.14e-03 | 3e-02 | PASS |
| amplification_reference | max over P <= 0.8 P_cr of |midspan deflection - e0 / (1 - P/P_cr)| / deflection (model form: small-deflection theory) | 1.20e-03 | 2e-02 | PASS |
| first_yield_bracketed | first yield reached inside the load range (1 = not reached) | 0.00e+00 | 5e-01 | PASS |
| first_yield_reference | |first-yield load FE - Perry-Robertson (FE P_cr)| / Perry-Robertson (model form: beam stresses) | 1.18e-02 | 2e-02 | PASS |
| equilibrium | |axial reaction at the midspan restraint| / end load, last increment (the two end loads balance) | 1.48e-14 | 1e-06 | PASS |
| euler_range (validity) | Euler stress / (yield / 2): elastic buckling governs at or below 1 (Johnson range otherwise) | 2.92e-01 | 1e+00 | PASS |
| moderate_deflection (validity) | midspan deflection at first yield / length | 2.74e-02 | 5e-02 | PASS |
| slender (validity) | thickness / length (beam-column references) | 2.67e-02 | 1e-01 | PASS |

![p00_element_size_mm-4 response](points/p00_element_size_mm-4/response.png)

### p01_element_size_mm-3

Parameters: length_mm = 600, width_mm = 25, thickness_mm = 16, youngs_modulus_MPa = 6.89e+04, poisson_ratio = 0.33, yield_strength_MPa = 276, element_size_mm = 3, imperfection_over_length = 0.001

Derived: slenderness_L_over_r = 129.9, euler_load_N = 1.612e+04, critical_load_engesser_N = 1.609e+04, euler_stress_MPa = 40.3, johnson_stress_MPa = -196.6, perry_robertson_load_N = 1.55e+04, squash_load_N = 1.104e+05, thickness_over_length = 0.02667

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-K1 | 1.531e+04 N | >= 16000 | -691 | **FAIL** | [point.json](points/p01_element_size_mm-3/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| buckling_reference | |P_cr FE - Euler with Engesser shear correction| / reference (model form) | 4.25e-04 | 1e-02 | PASS |
| mode_shape | 1 - MAC(first mode on the axis, half sine) (weak-axis buckling) | 7.93e-12 | 1e-03 | PASS |
| southwell_vs_eigenvalue | |P_cr from the Southwell plot of the nonlinear run - eigenvalue| / eigenvalue (two independent FE routes) | 1.11e-04 | 1e-02 | PASS |
| southwell_imperfection | |initial bow recovered by the Southwell fit - imposed| / imposed | 2.13e-03 | 3e-02 | PASS |
| amplification_reference | max over P <= 0.8 P_cr of |midspan deflection - e0 / (1 - P/P_cr)| / deflection (model form: small-deflection theory) | 1.19e-03 | 2e-02 | PASS |
| first_yield_bracketed | first yield reached inside the load range (1 = not reached) | 0.00e+00 | 5e-01 | PASS |
| first_yield_reference | |first-yield load FE - Perry-Robertson (FE P_cr)| / Perry-Robertson (model form: beam stresses) | 1.18e-02 | 2e-02 | PASS |
| equilibrium | |axial reaction at the midspan restraint| / end load, last increment (the two end loads balance) | 3.24e-15 | 1e-06 | PASS |
| euler_range (validity) | Euler stress / (yield / 2): elastic buckling governs at or below 1 (Johnson range otherwise) | 2.92e-01 | 1e+00 | PASS |
| moderate_deflection (validity) | midspan deflection at first yield / length | 2.74e-02 | 5e-02 | PASS |
| slender (validity) | thickness / length (beam-column references) | 2.67e-02 | 1e-01 | PASS |

![p01_element_size_mm-3 response](points/p01_element_size_mm-3/response.png)

### p02_element_size_mm-2

Parameters: length_mm = 600, width_mm = 25, thickness_mm = 16, youngs_modulus_MPa = 6.89e+04, poisson_ratio = 0.33, yield_strength_MPa = 276, element_size_mm = 2, imperfection_over_length = 0.001

Derived: slenderness_L_over_r = 129.9, euler_load_N = 1.612e+04, critical_load_engesser_N = 1.609e+04, euler_stress_MPa = 40.3, johnson_stress_MPa = -196.6, perry_robertson_load_N = 1.55e+04, squash_load_N = 1.104e+05, thickness_over_length = 0.02667

| Requirement | Result | Limit | Margin | Verdict | Evidence |
|---|---|---|---|---|---|
| REQ-K1 | 1.531e+04 N | >= 16000 | -691 | **FAIL** | [point.json](points/p02_element_size_mm-2/point.json) |

| Check | Description | Value | Tolerance | Status |
|---|---|---|---|---|
| buckling_reference | |P_cr FE - Euler with Engesser shear correction| / reference (model form) | 4.56e-04 | 1e-02 | PASS |
| mode_shape | 1 - MAC(first mode on the axis, half sine) (weak-axis buckling) | 9.23e-12 | 1e-03 | PASS |
| southwell_vs_eigenvalue | |P_cr from the Southwell plot of the nonlinear run - eigenvalue| / eigenvalue (two independent FE routes) | 1.11e-04 | 1e-02 | PASS |
| southwell_imperfection | |initial bow recovered by the Southwell fit - imposed| / imposed | 2.12e-03 | 3e-02 | PASS |
| amplification_reference | max over P <= 0.8 P_cr of |midspan deflection - e0 / (1 - P/P_cr)| / deflection (model form: small-deflection theory) | 1.18e-03 | 2e-02 | PASS |
| first_yield_bracketed | first yield reached inside the load range (1 = not reached) | 0.00e+00 | 5e-01 | PASS |
| first_yield_reference | |first-yield load FE - Perry-Robertson (FE P_cr)| / Perry-Robertson (model form: beam stresses) | 1.18e-02 | 2e-02 | PASS |
| equilibrium | |axial reaction at the midspan restraint| / end load, last increment (the two end loads balance) | 3.13e-15 | 1e-06 | PASS |
| euler_range (validity) | Euler stress / (yield / 2): elastic buckling governs at or below 1 (Johnson range otherwise) | 2.92e-01 | 1e+00 | PASS |
| moderate_deflection (validity) | midspan deflection at first yield / length | 2.74e-02 | 5e-02 | PASS |
| slender (validity) | thickness / length (beam-column references) | 2.67e-02 | 1e-01 | PASS |

![p02_element_size_mm-2 response](points/p02_element_size_mm-2/response.png)

## Limitations

- No residual stresses, end eccentricity or load misalignment beyond the bow.
- Capacity defined as first yield, not collapse (the plastic reserve beyond first yield is not used).
- References are model form (beam-column theory) except the Southwell plot, which uses the FE response itself.
- No physical test data.
- A converged solver run that matches an analytical reference shows that the equations were solved correctly. It does not show that the equations represent real hardware.

## Engineering acceptance

Pending human review. This report does not accept or reject the design.

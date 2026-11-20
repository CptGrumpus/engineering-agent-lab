# Reference solution: track roller contact stress

**Method.** Hertz line contact (a cylinder on a half-space, plane strain), K. L. Johnson,
*Contact Mechanics*, chapter 4.

- Combined modulus: 1/E* = 2 (1 - 0.3²) / 210 000, so E* = 115 385 MPa
- Half-width: a = sqrt(4 P' R / (pi E*)) = sqrt(4 x 500 x 50 / (pi x 115 385)) = **0.525 mm**
- Peak pressure: p0 = 2 P' / (pi a) = **606 MPa** (limit 650: met)
- Maximum subsurface shear: 0.300 p0 = **182 MPa** at z = 0.786 a = **0.413 mm** (limit 200: met)

**Independent evidence.** A CalculiX surface-to-surface contact model of the same roller
and plate (portfolio study 10) matches: half-width to 0.005 %, peak pressure 0.4 %, shear
1.2 %, depth within 2 % of one element.

**Grading tolerances.** Half-width and peak pressure ±2 %, shear ±3 %, depth ±5 %
(finite-element answers on an adequate mesh land inside these); both verdicts must be right.

## Traps this task is designed to expose

| Trap | What it produces | Criterion that fails |
|---|---|---|
| Using E instead of the combined E* | a 0.389 mm (26 % small), p0 817 MPa (35 % high): the pressure verdict flips | half-width, pressure, verdict |
| Point (sphere) contact formulas for a long roller | wrong scaling with load and radius | half-width, pressure |
| Taking the maximum shear at the surface instead of below it | depth 0 | shear depth |
| Reading peak pressure from element stresses extrapolated to the surface on a linear-element mesh | 3.5 to 6.5 % high | pressure (beyond ±2 %) |

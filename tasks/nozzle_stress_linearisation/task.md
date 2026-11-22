# Task: nozzle junction stresses, design by analysis

A cylindrical pressure vessel shell (inside radius 500 mm, wall 16 mm) has a radial nozzle
(bore 200 mm, wall 12 mm, 10 mm outer weld fillet). At 3.5 MPa internal pressure a linear
elastic finite element model gives the stresses below along a **stress classification line**
through the shell wall at the toe of the weld fillet, in the plane through the nozzle axis
and the vessel axis. The line runs straight through the 16 mm wall from the inner surface
(s = 0) to the outer surface (s = 16 mm).

Stresses are in MPa, in local axes: r radial (along the line, through the wall), a axial
(along the vessel), h hoop. τ are the shear components between those axes.

The line is at a gross structural discontinuity (the nozzle junction), so its membrane stress
is local primary membrane, PL, and its membrane-plus-bending stress is primary plus secondary,
P + Q. Use the von Mises equivalent stress. The allowable is S = 138 MPa:

- PL ≤ 1.5 S = 207 MPa
- P + Q ≤ 3 S = 414 MPa

Linearise the stresses along the line, give PL and P + Q (the larger of the two surfaces), say
which surface governs P + Q, and whether each limit is met. State your method.

| s (mm) | σ_r radial | σ_a axial | σ_h hoop | τ_ra | τ_ah | τ_hr |
|---:|---:|---:|---:|---:|---:|---:|
| 0.0 | -3.66 | -29.96 | 221.49 | -0.22 | 0.00 | -0.02 |
| 0.8 | -2.72 | -20.00 | 223.20 | -1.45 | 0.07 | -0.03 |
| 1.6 | -1.94 | -10.33 | 224.64 | -2.65 | 0.07 | -0.04 |
| 2.4 | -0.99 | -1.05 | 225.82 | -3.63 | 0.01 | -0.03 |
| 3.2 | 0.53 | 7.60 | 226.92 | -4.61 | -0.01 | 0.02 |
| 4.0 | 1.86 | 16.06 | 228.06 | -5.70 | -0.02 | 0.06 |
| 4.8 | 3.61 | 24.35 | 229.20 | -6.85 | -0.01 | 0.03 |
| 5.6 | 5.44 | 32.51 | 230.27 | -8.08 | -0.00 | 0.00 |
| 6.4 | 7.14 | 40.50 | 231.21 | -9.33 | 0.03 | -0.01 |
| 7.2 | 8.98 | 48.71 | 232.25 | -10.62 | 0.05 | -0.03 |
| 8.0 | 11.02 | 57.11 | 233.40 | -12.01 | 0.04 | -0.08 |
| 8.8 | 12.29 | 65.77 | 234.35 | -13.38 | 0.00 | -0.08 |
| 9.6 | 13.46 | 74.91 | 235.39 | -14.93 | -0.04 | -0.01 |
| 10.4 | 15.53 | 84.82 | 236.89 | -17.03 | -0.17 | 0.08 |
| 11.2 | 15.75 | 95.38 | 237.86 | -18.36 | -0.16 | 0.09 |
| 12.0 | 16.30 | 106.43 | 239.20 | -20.06 | 0.06 | 0.03 |
| 12.8 | 15.97 | 119.62 | 240.95 | -21.14 | 0.12 | -0.01 |
| 13.6 | 15.34 | 134.81 | 243.22 | -22.48 | 0.33 | -0.07 |
| 14.4 | 11.51 | 151.64 | 245.23 | -19.72 | 0.64 | -0.26 |
| 15.2 | 5.76 | 171.73 | 247.78 | -14.17 | 0.54 | -0.38 |
| 16.0 | -0.39 | 195.37 | 251.30 | -7.88 | -0.04 | -0.34 |

Answer as JSON:

```json
{
  "pl_MPa": 0.0,
  "pq_MPa": 0.0,
  "pq_governing_surface": "inner or outer",
  "pl_limit_met": true,
  "pq_limit_met": true,
  "method": "one or two sentences"
}
```

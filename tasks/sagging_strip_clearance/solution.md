# Reference solution: sagging strip clearance

## Answer

| Quantity | Reference | Grader tolerance |
|---|---|---|
| Tip drop | 86.5 mm | ±1.5 % |
| Tip pull-in towards the wall | 10.85 mm | ±3 % |
| Bending modulus | 12.54 MPa (plane strain, E / (1 − ν²)) | ±1 % |
| Clearance met (drop ≤ 89 mm) | **yes**, by about 2.5 mm | exact |

## Method

The strip is 15 times wider than it is thick, so it bends in **plane strain**: the width can't contract
sideways, which stiffens it by 1 / (1 − ν²). Per metre of width:

- Bending modulus E' = E / (1 − ν²) = 10 / (1 − 0.45²) = 12.54 MPa.
- Bending stiffness EI = E' h³ / 12 = 8.36 N·m.
- Weight per unit length q = ρ g h = 1200 × 9.81 × 0.020 = 235.4 N/m.

The load parameter q L³ / EI = 1.80 is far from small. The free edge drops by more than a fifth of the
length, so the **small-deflection formula overestimates the drop**: the strip's weight moves inwards as it
sags, shortening the moment arm. The large-deflection elastica (inextensible beam, dead load) solves

    EI θ''(s) = q (L − s) cos θ(s),   θ(0) = 0,   θ'(L) = 0

and integrates the slope for the tip position. That gives a drop of 86.71 mm and a pull-in of 10.90 mm.

## Evidence

- **Elastica** (`validation/elastica.py`, solved with SciPy's boundary-value solver; its small-load limit
  matches q L⁴ / 8 EI to 10⁻⁷): drop 86.71 mm, pull-in 10.90 mm.
- **Finite elements**, as an independent continuum check. The verified flag model of study 6
  (`models/fea/flag_ccx.py`: CalculiX, geometrically nonlinear, plane strain through one C3D8I layer held in z)
  reproduced the Turek-Hron CSM1/CSM2 benchmark to 0.015 %. Run here with a straight clamped root:
  - drop 86.09 / 86.30 / 86.40 mm and pull-in 10.750 / 10.796 / 10.817 mm at elements of 5 / 2.5 / 1.25 mm;
  - extrapolated about 86.5 and 10.83 mm.

  The two methods agree within 0.3 % on the drop and 0.7 % on the pull-in. The reference takes the FE values,
  and the tolerances accept either method.

## Traps this task exposes

| Trap | Bending modulus | Drop | Verdict | Fails on |
|---|---|---|---|---|
| Small-deflection formula q L⁴ / 8 EI (plane strain right) | 12.54 | 90.13 mm | **fails** (wrong) | drop, pull-in (0), verdict |
| Plane stress, E instead of E / (1 − ν²) (large deflection right) | 10.0 | 106.5 mm | **fails** (wrong) | modulus, drop, pull-in, verdict |
| Both: plane stress and the small-deflection formula | 10.0 | 113.0 mm | **fails** (wrong) | all |
| Linear FE (no geometric nonlinearity) | 12.54 | about 90 mm | **fails** (wrong) | drop, verdict |

Each trap is a real habit: the cantilever formula is the reflex, and "a strip is a beam" hides the plane-strain
stiffening. Either one alone turns a pass into a fail. The limit was placed between the right answer and the
nearest trap on purpose.

## Assumptions to state

Plane strain across the width; elastic; dead load (gravity stays vertical); rigid clamp; strip mass uniform. No
material damping or creep (a real polyurethane would creep over time, so the margin matters).

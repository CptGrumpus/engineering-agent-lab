# Reference solution: cantilever bracket stress and deflection

**Bending stress.** M = 1000 N x 200 mm = 2e5 N·mm; I = 20 x 20³ / 12 = 13 333 mm⁴;
sigma = M c / I = 2e5 x 10 / 13 333 = **150 MPa** (limit 213: met).

**Deflection.** Euler-Bernoulli: P L³ / (3 E I) = 0.952 mm. Adding Timoshenko shear
deflection gives 0.960 mm. A fully clamped 3D solid lands between the two: the 3D FE
model (portfolio study 1) gives **0.953 mm** (limit 1.0: met).

**The peak stress in the FE model is an artifact.** At the clamped corners the stress
keeps rising with mesh refinement (150, then 217 MPa and still growing): a sharp corner
against a fully fixed boundary is a stress singularity. The design stress comes from the
smooth part of the beam, extrapolated to the root, and matches beam theory.

**Grading tolerances.** Deflection 0.955 ± 0.010 mm (covers both beam theories and the
3D result), stress 150 ±3 %, all three booleans exact.

## Traps this task is designed to expose

| Trap | What it produces | Criterion that fails |
|---|---|---|
| Reporting the FE peak at the clamped corner as the design stress | 217 MPa and growing: the stress verdict flips | stress, verdict, singularity flag |
| Linear tetrahedra on a coarse mesh | 4 to 33 % too stiff, stress 7 to 45 % low | deflection, stress |
| Using the full depth (20 mm) instead of half (10 mm) as c | 300 MPa: the verdict flips | stress, verdict |

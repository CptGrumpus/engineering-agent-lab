# Task: cantilever bracket stress and deflection

A steel bracket is a solid bar, 200 mm long with a 20 x 20 mm square section, fully
clamped at one end. A 1 kN load acts downwards at the free end. Steel: E = 210 GPa,
Poisson's ratio 0.3, yield strength 355 MPa.

The bracket must deflect no more than 1.0 mm at the tip, and the bending stress must not
exceed 213 MPa (yield / 1.67). Build a 3D finite-element model (or justify another
method) and report the tip deflection, the root bending stress you would use for the
design check, whether each limit is met, and whether the peak stress in your model is a
real stress or a modelling artifact.

Answer as JSON:

```json
{
  "tip_deflection_mm": 0.0,
  "root_bending_stress_MPa": 0.0,
  "deflection_limit_met": true,
  "stress_limit_met": true,
  "peak_fe_stress_is_singular": true,
  "method": "one or two sentences"
}
```

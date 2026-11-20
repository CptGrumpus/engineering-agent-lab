# Task: track roller contact stress

A hardened steel track roller, 100 mm in diameter and long compared with its contact
width, runs on a flat steel rail plate. It carries a line load of 500 N per mm of roller
length. Both parts: E = 210 GPa, Poisson's ratio 0.3. Treat the contact as frictionless
and elastic.

The design limits are a peak contact pressure of 650 MPa and a maximum shear stress
below the surface (where rolling-contact fatigue cracks start) of 200 MPa.

Determine the contact half-width, the peak contact pressure, the maximum subsurface
shear stress and its depth below the surface, and whether each limit is met. You may
use analytical theory, finite elements, or both; state your method.

Answer as JSON:

```json
{
  "contact_half_width_mm": 0.0,
  "peak_contact_pressure_MPa": 0.0,
  "max_subsurface_shear_MPa": 0.0,
  "max_shear_depth_mm": 0.0,
  "pressure_limit_met": true,
  "shear_limit_met": true,
  "method": "one or two sentences"
}
```

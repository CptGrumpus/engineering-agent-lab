# Task: sagging strip clearance

A flexible polyurethane strip is clamped horizontally along one edge to a rigid wall bracket and hangs out
over a conveyor under its own weight. The strip is 400 mm long (from the clamp to its free edge), 20 mm thick
and 300 mm wide. Material: E = 10 MPa, Poisson's ratio 0.45, density 1200 kg/m³. Take g = 9.81 m/s². The
clamp holds the whole clamped edge rigidly; nothing else touches the strip.

The conveyor belt runs 89 mm below the strip's clamped mid-plane. The strip's free edge must stay clear of
the belt: the vertical drop of the free edge's mid-plane must not exceed 89 mm.

Determine the vertical drop of the free edge, how far the free edge moves back towards the wall, the bending
modulus you used for the strip, and whether the clearance requirement is met. You may use analytical
methods, finite elements, or both; state your method and its main assumptions.

Answer as JSON:

```json
{
  "tip_drop_mm": 0.0,
  "tip_pull_in_mm": 0.0,
  "bending_modulus_MPa": 0.0,
  "clearance_met": true,
  "method": "one or two sentences"
}
```

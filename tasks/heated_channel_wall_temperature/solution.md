# Reference solution: cold-plate channel wall temperature

**Coolant rise (energy balance, exact).** Heat in = 2 q L per unit width; mass flow per
unit width = rho U H. Rise = 2 x 30 000 x 0.05 / (997 x 4180 x 0.1 x 0.001) = **7.20 K**,
so the bulk leaves at 32.20 °C.

**Is the flow thermally developed? No.** Re (on Dh = 2H) = 224, Pr = 6.13, Pe = 1373.
The thermal entry length is about 0.05 Dh Pe = 137 mm, longer than the 50 mm heated
length. The local Nusselt number must come from the thermal-entry (Graetz) solution,
not the fully developed value.

**Thermal entry.** Solving u(y) dT/dx = alpha d2T/dy2 with the parabolic profile and flux
walls (validation/graetz.py: exact along x, converged across the gap) gives at x = 50 mm:
Nu = **8.34** (fully developed: 140/17 = 8.235), and wall minus bulk = q Dh / (k Nu) =
11.85 K, so the peak wall temperature is **44.05 °C** (limit 45: met, by about 0.95 K).

**Independent evidence.** OpenFOAM with temperature transport (portfolio study 11) gives
44.03 to 44.14 °C on three meshes and closes the energy balance to 1e-12.

**Grading tolerances.** Coolant rise ±0.5 %, peak wall ±0.10 K, Nusselt ±0.05, verdict
exact. The wall tolerance is tight on purpose: the fully developed shortcut is only 0.15 K
off here, and the task exists to see whether the solver checks that assumption.

## Traps this task is designed to expose

| Trap | Peak wall | Criterion that fails |
|---|---|---|
| Fully developed Nu = 8.235 at the end of heating (entry length not checked) | 44.20 °C | wall, Nusselt |
| Constant-wall-temperature Nu = 7.54 instead of the uniform-flux value | 45.31 °C: the verdict flips | wall, Nusselt, verdict |
| Only one wall heated (Nu = 5.385) | 50.55 °C: the verdict flips | wall, Nusselt, verdict |
| Counting only one wall in the energy balance | rise 3.60 K | coolant rise |

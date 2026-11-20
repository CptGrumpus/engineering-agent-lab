# Cold-plate channel heat transfer

[Portfolio index](../PORTFOLIO.md) · Thermal and fluids

| | |
|---|---|
| **Answer** | The coolant warms by 7.2 K, within its 10 K budget (verified). The wall peaks at 44.0 to 44.1 °C against a 45 °C limit on every mesh, but its mesh uncertainty can't be estimated yet, so that verdict is formally withheld. Rated heat flux about 31 kW/m². |
| **Discipline** | Thermal and fluids |
| **Tools** | OpenFOAM 14 (in WSL), scalar temperature transport, Python |
| **Methods** | Laminar CFD with heat transfer, the Graetz thermal-entry solution as an independent reference, energy balance, mesh refinement, a heat-flux sweep |

![Wall and bulk temperature along the heated channel, OpenFOAM against the Graetz reference](../runs/20261120-150722_heated_channel_mesh/points/p01_cells_across_gap-40/response.png)

## The question

A cold-plate passage, 1 mm deep, carries water at 25 °C and 0.1 m/s. Electronics heat both walls at 30 kW/m² over 50 mm. Does the wall stay at or under 45 °C, does the coolant warm by no more than 10 K, and how much heat flux could the passage take?

## The answer

- **The coolant warms by 7.2 K**, inside its 10 K budget. That result is verified: the energy balance closes to a part in a trillion on every mesh.
- **The wall peaks at 44.0 to 44.1 °C** on all three meshes, 0.86 to 0.97 K under the limit, and matches the independent reference within 0.6 %. But the peak isn't yet settling smoothly as the mesh is refined, so the formal mesh-convergence check can't put a number on its uncertainty. Under the rules this portfolio works to, that verdict stays withheld until a finer mesh shows it converging.
- **The rating:** at 40 cells the wall reaches 45 °C at about 31 kW/m². Up to 30 kW/m² passes, and 35 fails.

## How I know it's right

- **Against an independent solution.** The thermal-entry (Graetz) problem is solved separately: exact along the flow, and checked first against the textbook fully developed Nusselt number (140/17) and the energy balance. The CFD wall temperature matches it to within 0.03 to 0.6 % of the temperature rise, closer on finer meshes.
- **Energy balance.** The heat put into the walls comes out in the coolant to a part in a trillion.
- **Converged.** Temperature is solved on the converged flow until the field stops changing, which it does to 10⁻¹¹ of the rise.
- **Validity.** The flow is laminar (Reynolds number 224), and the reference's no-axial-conduction assumption holds (Péclet number 1373).

## Why the reference matters

The heated length is shorter than the thermal entry length (about 137 mm here), so the heat transfer is still developing at the end of the heating: the Nusselt number is 8.34, not the textbook fully developed 8.24. A hand calculation that assumed developed flow would get the wall temperature wrong.

## What the checks caught

- **An overshoot exactly where the answer is.** The standard second-order scheme overshoots by 0.06 to 0.11 K at the last heated cell, where the heated wall meets an unheated one, which is where the peak sits. It errs on the safe side, raising the peak, but it's also why the peak doesn't converge smoothly with the mesh.
- **Fixes that only hid the problem.** I tried four bounded schemes to remove the overshoot. All of them dithered from one iteration to the next near the end of the heating and never closed the energy balance. Under-relaxation only masked it. I went back to the scheme that converges exactly and let the checks bound its bias, and kept every failed run as evidence. The tolerances never changed.

## Limits

- 2D: the passage is much wider than it is deep, so the side walls are neglected (the 3D duct check showed a 3 % effect on the flow).
- No conduction in the plate itself (no conjugate heat transfer), which would smooth the wall temperature along the length.
- Constant water properties, reasonable for a rise under 20 K.

## Evidence

- [mesh study](../runs/20261120-150722_heated_channel_mesh/report.md) and [heat-flux sweep](../runs/20261120-150722_heated_channel_flux/report.md)
- earlier runs kept as evidence: [first mesh study](../runs/20261120-124736_heated_channel_mesh/report.md), [first heat-flux sweep](../runs/20261120-130606_heated_channel_flux/report.md), [relaxed run](../runs/20261120-131818_heated_channel_mesh/report.md)
- case files: `cases/heated_channel_mesh.toml`, `cases/heated_channel_flux.toml` (predictions, two revision notes, results)

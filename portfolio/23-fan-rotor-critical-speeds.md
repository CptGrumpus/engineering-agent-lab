# Fan rotor: critical speeds and unbalance response

[Portfolio index](../PORTFOLIO.md) · Structures and vibration

| | |
|---|---|
| **Answer** | The 50 mm shaft does not work: its first critical speed (2710-2911 rpm) sits inside the 1000-3000 rpm operating range, and the impeller swings 335-345 µm through it. A 60 mm shaft clears the range only on stiff bearings (14.3 % margin against 15 % on soft ones). **Use 65 mm**: at least 23.8 % margin over the whole bearing-stiffness band, response under 5 µm. Geometry, speed range, bearing band and damping are synthetic. |
| **Discipline** | Rotordynamics |
| **Tools** | ROSS 3.1 (open-source rotordynamics, Python) |
| **Methods** | Timoshenko rotor finite elements with gyroscopic terms, Campbell diagram, critical speeds as 1× crossings, API 684 unbalance response, Jeffcott and Euler-Bernoulli closed forms |

![Campbell diagram and unbalance response, 65 mm shaft on soft bearings](../runs/20261123-162721_rotor_fan_design/points/p04_d65_kb1e7/response.png)

## The question

A fan's impeller (400 mm steel disc, 25 mm thick) sits mid-span on a steel shaft between two rolling bearings 1 m
apart. It runs at 1000-3000 rpm on a variable-speed drive. A rotor that runs near a critical speed vibrates hard, so
the requirement, simplified from API 684, is that every forward critical speed sits at least 15 % outside the
operating range: none between 850 and 3450 rpm. The bearing pedestals' stiffness is not known well, so it is a band,
1e7 to 1e8 N/m, and the requirement must hold across it. A second requirement limits the impeller's response to the
standard API unbalance to 50 µm. The drawing's shaft is 50 mm; is it enough, and if not, what is?

## The answer

| Shaft | Bearings (N/m) | First forward critical | Margin (at least 15 %) | Response (at most 50 µm) |
|---|---|---|---|---|
| 50 mm | 1e7 / 1e8 | 2710 / 2911 rpm | -9.7 / -3.0 % **FAIL** | 335 / 345 µm **FAIL** |
| 60 mm | 1e7 / 1e8 | 3429 / 3957 rpm | **14.3 % FAIL** / 31.9 % | 8.7 / 3.8 µm |
| 65 mm | 1e7 / 1e8 | 3714 / 4494 rpm | 23.8 / 49.8 % | 5.0 / 2.3 µm |

The soft-bearing end of the band governs: a softer support lowers every critical speed. The 60 mm shaft would pass
on stiff pedestals and fail on soft ones, which is exactly the uncertainty the band was meant to cover.

## How it works

ROSS builds the rotor from 20 Timoshenko beam elements (shear deformation, rotary inertia, gyroscopic coupling), a
rigid disc and two linear bearings. Its Campbell diagram tracks each mode's frequency against running speed, split
into forward and backward whirl. A critical speed is where a forward-whirl mode crosses the 1× running-speed line. The
unbalance response applies API 684's standard unbalance (6350 W / N g·mm, here 84-106 g·mm) at the disc.

## How I know it's right

- **Jeffcott rotor** (massless shaft, rigid supports, central disc) against sqrt(48 EI / m L³): within 0.27-0.46 %,
  the difference being shear deformation and the disc's width.
- **The same rotor on the case's bearings** against the closed form with shaft and bearings as springs in series:
  within 0.24-0.44 %.
- **The bare shaft** on rigid supports against Euler-Bernoulli pinned-pinned: within 0.30-0.50 %.
- **The Campbell crossings** against ROSS's own critical-speed search: agree to 6e-6 or better.
- **Element convergence:** 10, 20 and 40 elements give the same critical speed and response (GCI 2e-7).

## What the checks caught

- **ROSS's own critical-speed search failed to converge** over the full 0-9000 rpm range (its Newton iteration). The
  study takes the critical speeds from the Campbell diagram's 1× crossings instead and keeps ROSS's search, over its
  default range, as a cross-check.
- **My hand estimate ran 2 % high on soft bearings.** Rayleigh's method, with 17/35 of the shaft's mass at mid-span,
  matched within 0.2 % on stiff bearings, but that factor assumes a simply supported mode shape; on soft bearings the
  whole shaft also translates, so more of its mass takes part. That 2 % put the 60 mm shaft just under the limit,
  outside the band I had predicted for it.

## Limits

- Linear bearings: a rolling bearing's stiffness rises with load and speed; the band is meant to cover that.
- No aerodynamic cross-coupling, foundation mass or seal forces; the blades are lumped into the disc.
- API 684's separation margin depends on each mode's amplification factor; a fixed 15 % is a simplification.

## Evidence

- [design run](../runs/20261123-162721_rotor_fan_design/report.md) (verification PASS),
  [element convergence](../runs/20261123-163104_rotor_fan_mesh/report.md) (PASS)
- case files: `cases/rotor_fan_design.toml`, `cases/rotor_fan_mesh.toml` (hand estimate, predictions, results)
- code: `models/rotor/fan_rotor.py` (runs in its own ROSS environment), `studies/rotor_critical.py`;
  tests `tests/test_rotor_critical.py`

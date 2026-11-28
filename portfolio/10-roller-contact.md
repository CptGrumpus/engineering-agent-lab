# Roller-on-plate contact

[Portfolio index](../PORTFOLIO.md) · Structures and vibration

| | |
|---|---|
| **Answer** | Yes. Peak contact pressure 609 MPa against a 650 MPa limit, and maximum shear below the surface 184 MPa against 200 MPa. **Part 2, with the roller's ends:** a straight roller fails. Square ends, or a 1 mm edge break, load the ends at 2,700-3,000 MPa and more, against 650. **With a logarithmic crown it passes at 617 MPa** on the half-space model (A = 1.8 µm, crown drop 3.7 µm at 1 mm from the end). The 3D FE model also puts the peak at mid-length, at 635-647 MPa over six meshes: under the limit by only 0.4-2.4 %, and unverified. The crown works from about 3 to 7 µm of drop, so it needs a grinding tolerance of about ±2 µm. |
| **Discipline** | Structures and vibration |
| **Tools** | Gmsh 4.15, CalculiX 2.22 (surface-to-surface contact) |
| **Methods** | Nonlinear contact FEA (penalty, frictionless), plane strain, displacement control, Hertz line contact as the exact reference, mesh refinement; part 2: 3D contact along the roller by half-space influence coefficients (Boussinesq, Love), checked against Hertz line and elliptical contact, with crowning profiles; a 3D CalculiX contact model of the crowned roller as a cross-check |

![Von Mises stress at the contact, whole roller and a section through the contact, rendered in Blender](img/render_contact.png)

![Contact pressure and the shear stress below the contact, CalculiX against the exact Hertz solution](../runs/20261120-120243_contact_roller_mesh/points/p02_contact_element_size_mm-0.02/response.png)

## The question

A hardened steel track roller, 100 mm in diameter, runs on a steel rail plate and carries 500 N per mm of its width. Does the peak contact pressure stay at or under 650 MPa? And does the maximum shear stress below the surface, which is where rolling-contact fatigue cracks start, stay at or under 200 MPa?

## The answer

**Yes, on both.** The peak contact pressure is 609 MPa and the maximum shear below the surface is 184 MPa, about 0.4 mm down. That leaves margins of 6 % and 8 %. The contact patch is 1.05 mm wide.

## How I know it's right

- **The model.** The roller and the plate are separate bodies that only touch. CalculiX finds where they're in contact as part of the solution, which makes it a nonlinear analysis. I push the roller down by a set distance and read the force it takes from the reactions. That's more robust than pushing with a force before the bodies have engaged.
- **Against the exact solution.** Hertz's theory gives the exact contact pressure and the stress field underneath for a cylinder on a flat. I compare at the load the model actually carries, 501.1 N/mm. On the finest mesh, the contact half-width matches to 0.005 %, the peak pressure to 0.4 %, and the depth of the maximum shear to within 2 % of one element.
- **Equilibrium.** The force on the roller and the reaction under the plate balance exactly. The contact pressure integrated across the patch accounts for the load to within 2.2 %.
- **The contact itself.** The penalty method lets the surfaces overlap very slightly. The largest overlap is less than a ten-thousandth of the imposed approach.
- **Mesh refinement.** Three meshes, with contact elements of 0.08, 0.04 and 0.02 mm. The two coarser meshes fail some checks against Hertz, as they should, so only the finest mesh gives the verdict. Mesh uncertainty is 1.2 % on the pressure and 0.15 % on the shear.

## What the checks caught

- **Reading the wrong output overstates the pressure.** Taking the pressure from the element stresses at the surface gave a peak 3.5 to 6.5 % too high, and that pressure added up to more than the load. CalculiX's own contact pressure output was within 0.2 % of Hertz on the same mesh. The study reads the contact output.
- **A converged answer the convergence check called divergent.** The maximum shear agreed across the three meshes to 0.06 %, but the convergence check failed it. The metric was the largest value at any node, and which node sits nearest the true peak changes with the mesh. I didn't loosen the tolerance. I changed the metric to locate the peak between nodes, wrote down the expected result first, and kept the failed run as evidence. The check now passes at 0.15 %.
- **A mesh nearly eight times bigger than it needed to be.** My first refinement zone spread across the whole model: 70,820 nodes and 3.5 minutes per solve. Keeping it close to the contact gave 9,334 nodes, 20 seconds, and the same answer to 0.2 %.

## Limits

- Frictionless, linear elastic contact. Friction, roughness, residual stress and plasticity are not modelled, and fatigue life is not assessed.
- Plane strain: a long roller, with no end effects or edge loading. Part 2 adds the ends, below.
- The shear below the surface sits 1.2 % above Hertz on every mesh. Because it doesn't change with refinement, it comes from the model (finite bodies rather than Hertz's infinite ones), not the mesh.

## Part 2: the roller's ends

![Peak contact pressure along the roller for square ends, a 1 mm edge radius and a logarithmic crown, and the peak against the crown's size](img/roller_halfspace.png)

### The question

Part 1 modelled a long roller: a section in plane strain, far from any end. Its 609 MPa against 650 left 6 %. A real
track roller is short, here 30 mm long for the 500 N/mm (15 kN), and a straight roller on a wider plate presses
hardest at its ends: the classic edge loading. Under the portfolio's standing rule (a fuller model wherever the margin
is as small as the simplification's likely error), the roller was modelled along its length. Does it pass, and what
profile does it need?

### The answer

**A straight roller fails; a crowned one passes.**

| Roller profile | Peak contact pressure (limit 650 MPa) | Verdict |
|---|---|---|
| straight, square ends | 2,018 → 2,443 → 2,969 MPa as the grid refines (the end is singular) | fails |
| straight, 1 mm edge radius | 1,497 → 2,010 → 2,708 MPa, 1 mm from the end (still growing) | fails |
| logarithmic crown, A = 1.38 µm (Lundberg's value) | 693 MPa, near the end | fails |
| **logarithmic crown, A = 1.79 µm (1.3 x Lundberg's)** | **617 MPa, at mid-length** | **passes, 5 % margin** |
| logarithmic crown, A = 3.45 µm (2.5 x) | 649 MPa, at mid-length | passes, only just |

The crown is the logarithmic profile of the Fujiwara-Kawase form, its drop capped at 30 µm at the ends. Too gentle
a crown leaves the ends loaded; too strong a crown piles the load into the middle. The window runs from about 1.1 to
2.5 times Lundberg's parameter, a drop at 1 mm from the end of about 3.1 to 7.1 µm. The drawing should call for about
3.7 µm there, with a tolerance of about ±2 µm. With it, the roller keeps part 1's verdict at 617 MPa, 1.8 % above the
long roller.

### How it works

- **Half-space contact.** The contact plane is divided into small rectangles. The surface displacement a uniform
  pressure on a rectangle causes in an elastic half-space is known in closed form (Love, 1929), and the two bodies'
  displacements add. The pressures are found so that the gap closes where they push and stays open where they do not
  (an active-set solution), and the approach is adjusted until the total force is 15 kN.
- **The profile** is the same function the 3D finite-element model uses: the roller's surface drops by d(y) along its
  length.
- **Why not the 3D finite-element model?** It is built (study 10's section extruded along the roller, the profile as a
  micron drop), but one solve takes about an hour; the half-space method is the standard tool for roller profiles and
  solves a design in seconds. The FE model was run as a cross-check, on seven meshes in all (below).

### How I know it's right

- **Two exact solutions, inside every run.** On each run's own grid: the middle of a long straight roller matches
  Hertz line contact for the line load it carries (within 6 × 10⁻⁴), and a roller with a circular crown matches
  Hertz's elliptical contact (within 2.4 × 10⁻⁴ on the finest grid).
- **Grid refinement**: the crowned design gives 616.3, 616.6 and 616.8 MPa on three grids: uncertainty 0.03 %.
- **The failures behave as theory says**: the square end's peak grows as the end cells shrink, roughly as their size
  to the power -0.47, the signature of a singular edge, so its runs fail their convergence check by design.

### The cross-check against the 3D finite-element model

**A first coarse check.** One 3D FE solve (scratch, 2026-11-27, a single coarse mesh: 0.08 mm contact elements, the
crown at Lundberg's own A, three approach steps) was compared with the half-space model at the loads the FE steps
reached:

| Load | FE mid-length | Half-space mid-length | FE peak (where) | Half-space peak (where) |
|---|---|---|---|---|
| 451 N/mm | 610 MPa | 580 MPa (FE +5.2 %) | 610 MPa (mid-length) | 612 MPa (0.2 mm from the end) |
| 528 N/mm | 655 MPa | 622 MPa (FE +5.3 %) | 902 MPa (0.2 mm from the end) | 736 MPa (0.2 mm from the end) |
| 605 N/mm | 698 MPa | 662 MPa (FE +5.4 %) | 1,229 MPa (0.2 mm from the end) | 901 MPa (0.1 mm from the end) |

Both models say the gentle crown fails at the ends. But the FE reads 5 % higher at mid-length at every load. A
closer look at the FE explains most of it: its nodal contact pressures integrate to 10-12 % more than the reaction
(the coarse mesh smears the contact's edge), and corrected for that, its mid-length section carries about 514 N/mm
at the 451 N/mm mean load, against the half-space's 458, with a mid-length pressure that matches Hertz for 514 within
1 %. The FE puts more of the load in the middle. That is what the half-space's known limit predicts: it continues past
the roller's end face, so it makes the ends too stiff and draws load to them. For the crowned design, whose peak is
at mid-length, the effect raises the pressure, and its size (2-5 %) is comparable to the design's 5.1 % margin. Under
the portfolio's standing rule that is too close to call, so the FE model was run properly at the chosen crown.

**Six meshes at the chosen crown.** Two FE runs at A = 1.79 µm, their predictions committed first: three contact
meshes with the layers along the roller 0.2 mm at the end (case `roller_fe_mesh`), then three end-layer sizes at the
coarsest contact mesh (case `roller_fe_end`):

| Contact elements | End layer | Mid-length | End region, against mid-length | Peak as first reported |
|---|---|---|---|---|
| 0.08 mm | 0.2 mm | 647.1 MPa | 0.98, settled | 647.1 MPa (pass) |
| 0.06 mm | 0.2 mm | 634.5 MPa | not settled | 724.1 MPa (fail) |
| 0.045 mm | 0.2 mm | 640.5 MPa | not settled | 715.7 MPa (fail) |
| 0.08 mm | 0.1 mm | 647.0 MPa | 0.93-0.94, settled | 647.0 MPa (pass) |
| 0.08 mm | 0.05 mm | 647.0 MPa | not settled | 668.1 MPa (fail) |
| 0.08 mm | 0.025 mm | 647.0 MPa | 0.93-0.94, settled | 647.0 MPa (pass) |

Three of the six meshes first read over 650 MPa near the roller's end. Looking at every load step showed that those
readings are not results. Each point solves two to four approach steps and interpolates to 500 N/mm between the two
that bracket it. On a settled mesh the end follows the load as mid-length does: its pressure against mid-length's
moves 0.004-0.005 between the two steps. On the other three, one layer near the end jumps:
- 751, 771, 697, then 816 MPa over four evenly rising loads on the 0.06 mm mesh;
- 466 to 692 MPa for 4.9 % more load at the 0.05 mm end layer, while mid-length rose 2 %.

That pattern rules out both physical causes I had in line. A coarsely drawn crown (my first diagnosis, made with the
half-space model fed the FE's piecewise crown) and the roller's free end face would each act at every load. Each would
also change steadily as the end layers refine. This end peak comes and goes: at one end-layer size of three, and at
one load step of two.

One reading was also a scoring error of mine. At the 0.05 mm end layer the study blended the two steps' maximum
pressures, which sat at different places along the roller, into 668.1 MPa: a pressure the model computed nowhere.
The interpolated profile reads 589 MPa at that spot and peaks at 647.0 at mid-length. Two changes followed:
- the study now reads the peak from the interpolated profile;
- a new check makes the end region's pressure, against mid-length's, agree within 0.03 between the two steps (the
  criterion I wrote down before the run). It fails exactly the three readings over 650 and passes the other three.

**Where the FE's ends are settled, its peak is at mid-length, as on the half-space model.** Mid-length reads
634.5-647.1 MPa across all six meshes: under the 650 limit by 0.4-2.4 %. That is 3-5 % above the half-space's 617,
the end effect the coarse check found. The FE's own checks are not all met: its nodal contact pressures add up to
6-11 % more than the load, because the contact mesh smears the edge of the patch. So every FE verdict stays
unverified.

**So the crowned design passes on both models, but the FE's margin is too thin to count as independent
confirmation.** The design number is the half-space's 617 MPa, which meets all of that model's exact checks. The 3D FE
model confirms where the peak sits and that it stays under the limit, but only by 0.4-2.4 %. The recommendation stands:
crown it, about 3.7 µm at 1 mm from the end. Before relying on the FE's thin margin, the next FE run would refine the
contact mesh and the end layers together, with enough load steps to show the end is settled.

### What the checks caught

- **My own formula error, caught by a limit.** The Hertz elliptical reference first came out 2.4 times too far from
  the solver. Checking it against its own long-ellipse limit (the minor semi-axis must tend to 2 p₀ R / E*) showed an
  extra factor I had "fixed" in; the original was right. A first test case also used the wrong load (15 kN for a 40 mm
  roller at 500 N/mm). Both were found before any run; the reference now carries the limit as a test.
- **A number CalculiX could not read.** The 3D FE model's crowned trial stopped on inverted elements. The cause was
  not the mesh: node coordinates written at full precision (21 characters) were cut at CalculiX's 20-character field,
  so `8.73e-05` became `8.73e-0` and a node jumped. The deck now writes 12 significant digits.
- **A trial lost to a timeout.** The first 3D FE trial was killed at 30 minutes by a time limit inside the command,
  at 47 % of its load; long solves now run in the background with none.
- **A failing peak the model never computed.** The 0.05 mm end-layer run reported 668 MPa at the roller's end.
  The study had blended two load steps' maxima that sat 14.6 mm apart. The fix reads the peak from the interpolated
  profile, and a new check rejects an end pressure that doesn't follow the load.
- **A diagnosis that didn't survive its test.** I traced the first end peaks to the coarsely drawn crown and set up a
  run to confirm it, with the result predicted first. The run showed the peaks come and go between meshes and load
  steps, which no drawing effect does, and the page says so.

### The roller as built

The crowned roller is delivered as a detailed CadQuery assembly ([`models/cad/track_roller.py`](../models/cad/track_roller.py),
[STEP](cad/track_roller_crowned.step)): the outer ring with the logarithmic crown in its profile (3.7 µm of drop
1 mm from each end: invisible in a render, exact in the STEP), a full complement of 26 needle rollers, the inner ring,
two side washers and a length of the rail. Every part matches a hand volume (the crowned ring by integrating the
same drop function, to 10⁻⁶) and no two parts overlap. Everything but the outer diameter, the width and the crown is
synthetic.

### Limits (part 2)

- Both bodies are half-spaces: the roller's end face and the plate's edges are left out. That overstates a sharp end's
  peak somewhat, but the failing profiles fail by 3 to 4 times, and the crowned design's peak is at mid-length.
- The 3D FE cross-check is unverified. Its nodal contact pressures add up to 6-11 % more than the load, and on three
  meshes of six the end region's pressure was not settled between load steps. Its mid-length margin (0.4-2.4 %) is
  thinner than that uncertainty.
- No misalignment. A tilted roller loads one end; a crown's tolerance to tilt is a separate check.
- Contact pressure only; the subsurface shear (part 1's second requirement) is not computed along the roller.
- The roller's length (30 mm) and the crown are a design input, marked synthetic.

## Evidence

- [mesh study](../runs/20261120-120243_contact_roller_mesh/report.md)
- [first run, with the shear metric that couldn't converge](../runs/20261120-120004_contact_roller_mesh/report.md)
- case file: `cases/contact_roller_mesh.toml` (predictions, revision note)
- Part 2: [crown size](../runs/20261127-172125_roller_hs_crown/report.md) (PASS), [the crowned design at three
  grids](../runs/20261127-172428_roller_hs_mesh/report.md) (PASS), [1 mm edge radius](../runs/20261127-172625_roller_hs_plain/report.md)
  and [square ends](../runs/20261127-172828_roller_hs_square/report.md) (both FAIL their convergence check, as
  predicted: the peak has no converged value); cases `cases/roller_hs_*.toml`; code `models/contact/roller_halfspace.py`,
  `studies/roller_halfspace.py` (tests `tests/test_roller_halfspace.py`), the 3D FE model `models/fea/roller_3d.py`;
  figure `scripts/make_roller_halfspace_figure.py`
- Part 2, the 3D FE cross-check: [three contact meshes](../runs/20261127-180915_roller_fe_mesh/report.md) and
  [three end layers](../runs/20261128-014852_roller_fe_end/report.md) (both VERIFICATION FAIL on the contact integral;
  scored in `cases/roller_fe_mesh.toml` and `cases/roller_fe_end.toml`); the load-step check
  `scripts/roller_step_consistency.py`; study `studies/roller_3d.py` (tests `tests/test_roller_3d.py`)

# Cracked steel plate: critical crack and fatigue crack growth

[Portfolio index](../PORTFOLIO.md) · Structures and vibration

| | |
|---|---|
| **Answer** | A 2 mm edge crack (the smallest magnetic-particle inspection reliably finds) in the 100 mm S355 plate grows to the critical size, **37.0 mm**, in about **92,000 cycles** at 150 MPa maximum stress (R = 0.1). Inspect at least every **46,000 cycles**; the planned 40,000 has margin. At the detectable crack, K is 13.4 MPa√m against the 50 allowed. Loads, toughness and the detectable size are synthetic; the crack growth law is the published BS 7910 / IIW one. |
| **Discipline** | Fracture mechanics, damage tolerance |
| **Tools** | Gmsh, CalculiX, Python (SciPy) |
| **Methods** | Linear elastic fracture mechanics, stress intensity by energy release rate and by crack opening, Paris-law crack growth (BS 7910 simplified law for steels in air), handbook K (Tada), mesh noise measurement |

![K against crack length, and the FE against Tada's handbook solution](../runs/20261123-164649_edge_crack_mesh_r2/points/p02_tip_element_size_mm-0.025/response.png)

## The question

A steel plate (S355, 100 mm wide, 10 mm thick) carries cyclic tension, 150 MPa at peak, 15 MPa at the bottom of each
cycle. Inspections can find an edge crack once it is 2 mm deep. How long does such a crack take to grow to failure,
and how often must the plate be inspected? Requirements: at the detectable crack, the stress intensity stays below
half the fracture toughness (100 MPa√m, synthetic: a client would supply CTOD or Charpy data); and the growth life is
at least twice the planned inspection interval of 40,000 cycles.

## The answer

- **Critical crack 37.0 mm**, set by the toughness; the ligament would yield only at 57.7 mm.
- **Life from 2 mm to 37.0 mm: about 92,000 cycles**, so an inspection interval of at most 46,000 cycles. 81 % of
  that life is spent growing from 2 to 10 mm: the early crack is slow, which is what gives inspection its chance.
- **K at the 2 mm crack: 13.4 MPa√m**, a quarter of the toughness.

## How it works

CalculiX solves half the plate (the crack plane is a plane of symmetry) in plane strain, meshed by Gmsh with
quadratic triangles that shrink towards the crack tip. At each of eleven crack lengths from 2 to 45 mm the stress
intensity K comes two ways, neither needing special crack-tip elements:

- **Energy release rate:** the strain energy at the crack length and 0.2 mm either side; G = dU/da, K = √(E′G).
- **Crack opening:** near the tip the crack faces open as √r, in proportion to K; fitting the opening along the face
  and extrapolating to the tip gives K.

K(a) then gives the critical crack (where K reaches the toughness) and, integrated through the BS 7910 crack growth
law (da/dN = 5.21×10⁻¹³ ΔK³), the life.

## How I know it's right

- **Tada's handbook solution** for an edge crack in a finite strip: the energy route agrees within 0.66 % at every
  crack length, against Tada's own stated accuracy of 0.5 %. The wave in the difference against crack length (right
  plot) is the same on every mesh, so it is the handbook's polynomial fit, not the model.
- **Two routes to K** agree within 1.9-2.2 %; the crack-opening route is the weaker one (few points to fit at small
  cracks) and converges towards the energy route as the tip mesh refines.
- **Equilibrium** to 1e-16; the life integral by two quadratures to 3e-9.
- **Tip mesh study** (0.1, 0.05, 0.025 mm): the critical crack converges (GCI 2e-4).
- **Measured mesh noise:** five meshes at one tip size, perturbed in the far field, scatter the life by 0.11 %.

## What the checks caught

- **The life would not converge cleanly, and fixing it took three revisions.** The first energy step (2 % of the crack
  length) was 0.04 mm at a 2 mm crack, about one tip element, so the energy difference picked up the mesh's own noise.
  A 10 % step cured that but added 1.2 % of truncation error at long cracks, where K rises steeply. A fixed 0.2 mm
  step, a few tip elements long and small against long cracks, satisfies both.
- **I had declared a noise floor I had not measured.** The first case's floor (1e-4) was a guess written beside a
  measured-sounding source. Measured afterwards, the life's scatter is 1.1e-3, and the finest tip still sits 0.05 %
  below that band. So the life is known to about ±0.2 %, but the harness's mesh check stays formally unverified for it.
  Against a 15 % margin to the requirement, no further revision can change the answer, so I stopped there.

## Limits

- Through-thickness straight crack; a real crack usually starts as a semi-ellipse at a surface (BS 7910 gives its K).
- Constant-amplitude loading; no crack closure, sequence effects or environment.
- Linear elastic: valid while the plastic zone (up to about 4 mm near the critical crack) is small against the
  ligament.

## Evidence

- [tip mesh study, revision 2](../runs/20261123-164649_edge_crack_mesh_r2/report.md),
  [noise measurement](../runs/20261123-165115_edge_crack_noise/report.md); revisions 0 and 1 in `runs/` with their
  reasons in the case files
- case files: `cases/edge_crack_mesh.toml`, `cases/edge_crack_mesh_r1.toml`, `cases/edge_crack_mesh_r2.toml`,
  `cases/edge_crack_noise.toml`
- code: `models/fea/edge_crack.py`, `studies/edge_crack.py`; tests `tests/test_edge_crack.py`

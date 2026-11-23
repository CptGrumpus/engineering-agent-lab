# Technical Memo: Cold-Plate Coolant Passage, Pressure Budget and Wall Shear

| | |
|---|---|
| **To** | Thermal design lead (example client; synthetic problem) |
| **From** | Engineering modeling consultant |
| **Date** | 20 November 2026 |
| **Subject** | Does the 1 mm coolant passage meet its pressure budget and minimum wall shear across tolerance and temperature? |
| **Status** | Analysis complete; recommendation pending your decision on the requirements |

*This is a sample deliverable built from case study 3 of my [portfolio](../../PORTFOLIO.md). Every number traces to a saved, reproducible evidence run listed in section 9.*

---

## 1. Summary and recommendation

**The passage as specified does not meet its requirements, and no choice of gap alone can fix it.**

- At nominal conditions (1.00 mm gap, 20 °C) the passage needs **33.4 Pa** of supply pressure against a **30 Pa** budget, 11 % over.
- Across the gap tolerance (±0.05 mm) and coolant range (15–40 °C) it needs **28–42 Pa** at the four verified corners, and warm coolant drops the wall shear to **0.43 Pa** against a **0.5 Pa** minimum (0.36 Pa at the warm, wide-gap corner, which is unverified; see below).
- The two requirements pull in opposite directions. The pressure budget at 15 °C needs a gap of at least **1.078 mm**; the shear minimum at 40 °C allows at most **0.885 mm**. Both limits were predicted before running and confirmed by simulation (30.02 Pa and 0.500 Pa).

**Recommendation.** Decide which requirement can move, then I will confirm the chosen design with one more run:

- **Option A, keep the shear minimum:** tighten the gap to **0.835 ± 0.05 mm** and either shorten the channel to about **6 mm** or raise the pressure budget to about **70 Pa**.
- **Option B, keep the 20 mm channel and 1.0 mm gap:** relax the shear minimum to about **0.35 Pa at the hot end** of the coolant range and raise the pressure budget to about **44 Pa**.

The option figures are scaling estimates from the verified results (section 8), not yet confirmed by simulation.

## 2. Question and requirements

| ID | Requirement | Limit | Source |
|---|---|---|---|
| REQ-F1 | Supply pressure needed to drive the flow from the supply header through the passage, including the exit loss | ≤ 30 Pa | Share of the pump budget (synthetic) |
| REQ-F2 | Fully developed wall shear stress | ≥ 0.5 Pa | Fouling guideline (synthetic) |

Conditions: water flow fixed by the pump at 1.0 × 10⁻⁴ m²/s per unit width (about 0.1 m/s), gap 1.00 ± 0.05 mm, coolant 15–40 °C.

## 3. Inputs and assumptions

| Item | Value | Note |
|---|---|---|
| Passage | 1.00 mm gap, 20 mm long; side walls 20 mm apart (assumed) | Width only affects the 3D check |
| Supply header | 3 mm high, 3 mm long, smooth 3 mm contraction | Represents the real header; see section 6 |
| Water properties | IAPWS: 15 °C 999.10 kg/m³, 1.1375 mPa·s; 20 °C 998.21, 1.0016; 40 °C 992.22, 0.6527 | |
| Flow | Steady, laminar, isothermal | Reynolds number about 200–300 (laminar below 2000) |
| Exit loss | The jet's dynamic head is lost in the outlet header | Conservative; 7.7 Pa of the 33.4 Pa |

## 4. Method

- **Model:** steady two-dimensional laminar flow in OpenFOAM 14, covering the supply header, contraction and passage. The model is generated from parameters by a Python case writer, and results are read straight from OpenFOAM's field files.
- **Required pressure:** flux-weighted total pressure at the supply inlet minus static pressure at the outlet.
- **Fully developed quantities:** pressure gradient and wall shear, measured 10–18 mm into the passage, after the entrance length.
- **Studies run:** a mesh refinement (10 to 80 cells across the gap), a tolerance study (four gap and temperature corners plus nominal), two confirmation runs at the predicted gap limits, and a 3D duct model to check the two-dimensional assumption.

## 5. Verification

| Check | Result | Acceptance |
|---|---|---|
| Velocity profile, pressure gradient, wall shear vs exact solution (plane Poiseuille) | within 0.02 % | 1 % |
| Mass conservation | 1 × 10⁻⁸ | 1 × 10⁻⁶ |
| Wall shear vs pressure gradient (force balance) | 2 × 10⁻⁵ | 1 × 10⁻³ |
| Supply-to-outlet loss vs independent estimate (lubrication theory + Shah & London) | within 0.3 % at every corner | 10 % (model form) |
| Mesh convergence of the required pressure (Grid Convergence Index) | 0.04 %, observed order 1.95 | 2 % |
| Laminar flow, and fully developed where measured | yes, except one corner (see section 7) | validity |
| 3D side walls vs exact rectangular-duct solution | 3.22 % vs 3.25 % | 1 % |

## 6. Results

| Case | Required pressure (≤ 30 Pa) | Wall shear (≥ 0.5 Pa) |
|---|---|---|
| Nominal: 1.00 mm, 20 °C | **33.4 Pa: fails** | 0.601 Pa: passes |
| 0.95 mm, 15 °C | **42.5 Pa: fails** | 0.756 Pa: passes |
| 0.95 mm, 40 °C | 28.2 Pa: passes | **0.434 Pa: fails** |
| 1.05 mm, 15 °C | **32.3 Pa: fails** | 0.619 Pa: passes |
| 1.05 mm, 40 °C | 21.6 Pa (unverified) | 0.355 Pa (unverified) |
| 1.078 mm, 15 °C (predicted pressure limit) | 30.02 Pa | 0.587 Pa |
| 0.885 mm, 40 °C (predicted shear limit) | 34.0 Pa | 0.500 Pa |

**The idealized model would have given the wrong answer.** A simpler model with a uniform inflow straight into the passage said it passed (28.6 Pa). That model never converged at the inlet corner, and it left out the supply header and the exit loss.

## 7. Uncertainty

| Source | Effect on the nominal 33.4 Pa |
|---|---|
| Mesh | ±0.04 % |
| Iteration and conservation | negligible |
| Model simplifications (vs independent estimate) | ≤ 0.3 % |
| Two-dimensional assumption (20 mm wide passage) | about +0.8 Pa (+2.4 %): the 3D answer is about 34.2 Pa |
| **Gap tolerance and coolant temperature** | **−16 % to +27 %: dominates** |

The warm, wide-gap corner (1.05 mm, 40 °C) is marked unverified: the flow there is still developing slightly (0.13 % against a 0.1 % limit) where the fully developed values are measured. The conclusions rest on the four verified cases.

## 8. Options

Two scaling relations from the verified results drive every option. The wall shear depends only on gap and viscosity (τ = 6μq/H²). The passage's friction loss also grows with its length.

| Option | What changes | Pressure (worst case) | Shear (worst case) | Confidence |
|---|---|---|---|---|
| A1 | Gap 0.835 ± 0.05 mm, passage shortened to about 6 mm | about 30 Pa | 0.50 Pa | Estimate; confirm with one run |
| A2 | Gap 0.835 ± 0.05 mm, budget raised to about 70 Pa | about 69 Pa | 0.50 Pa | Estimate; confirm with one run |
| B | Keep 1.00 mm and 20 mm; shear minimum relaxed to 0.35 Pa at 40 °C; budget about 44 Pa | 42.5 Pa (+ about 1 Pa for side walls) | 0.355 Pa | Pressure verified; shear at the hot, wide corner is unverified |

Changing the flow rate does not help: pressure loss and wall shear both scale with it, so the conflict stays.

## 9. Limits, next steps, and evidence

**Limits.**
- Flow and pressure only: no heat transfer.
- The passage width (20 mm) is assumed.
- Water properties are for pure water.
- Requirements and geometry are synthetic.
- No test data.

**Next steps.**
1. Confirm which requirement can move (the 0.5 Pa shear guideline or the 30 Pa budget) and whether shear must hold at 40 °C.
2. Run the chosen option as a confirmation case (about 1 hour including verification).
3. If heat transfer matters for the decision, add the solid plates and a heat load (conjugate model).

**Evidence** (each report traces every requirement to its result, the checks behind it, and reproducible inputs):
- [Mesh study](../../runs/20261119-200042_channel_header_mesh/report.md)
- [Tolerance corners](../../runs/20261119-200202_channel_header_tolerance/report.md)
- [Gap-limit confirmation](../../runs/20261119-201615_channel_header_gap_limits/report.md)
- [3D side-wall check](../../runs/20261119-204111_duct_side_walls/report.md)
- [First model with an idealized inlet, kept as evidence](../../runs/20261119-191916_channel_mesh/report.md)

*Engineering acceptance of these results is the client's decision.*

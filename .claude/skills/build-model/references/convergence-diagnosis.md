# Convergence diagnosis

Read the observed order and the location of the largest error before deciding
anything. Each row below happened in this repo.

| Symptom | Likely cause | What to do | Seen in |
|---|---|---|---|
| Observed order close to the method's design order (about 2 for second-order FV or quadratic FE) | Healthy, in the asymptotic range | Report GCI and the extrapolated value | channel header (1.95), duct (1.99), cantilever TET10 (2.04) |
| Observed order near 0.5 or lower, metric keeps drifting with refinement | A singularity inside the metric's footprint: velocity jump at a wall corner, re-entrant corner, clamp corner | Move the measurement away from it, model the real geometry (header, fillet), or define the metric on the smooth region. Do not loosen the GCI limit | uniform-inlet channel (0.49) |
| Peak value grows without bound with refinement | Point singularity (stress at a sharp corner) | The peak is not a valid requirement metric; use an extrapolated or linearized value | cantilever von Mises at the clamp corner (150 → 217 MPa) |
| Differences change sign between meshes at a tiny level | Converged to round-off or iterative noise; GCI not applicable | Oscillatory regime: uncertainty = 1.25 × half-range (Stern 2001) | cantilever root stress (~1e-4) |
| Three values agree to a few parts per million but the check says "divergent" | Noise below any meaningful convergence signal; the sign of the ratio is random | The harness now classes a relative spread under 1e-5 as converged (`noise_floor`) | cantilever root stress in the peak-stress test (4e-6) |
| Sign changes with growing amplitude (convergence ratio ≤ −1) | Not converging at all | Classed divergent, no estimate. Refine further or look for a bug | peak stress on a coarse smoke test |
| GCI passes, but the observed order is far above the design order (3.7 for second-order elements) | The three values only look converged: a singularity or a coincidence | No estimate ("anomalous order"); pass `design_order` to `discretization_uncertainty`. Never treat such a pass as evidence | peak von Mises at the clamp corner |
| A requirement metric passes in a mesh study but nothing checks its convergence | The harness only judged the metrics the study author thought of | Give every requirement metric a convergence check (the cantilever study now does this automatically) | "max von Mises anywhere" requirement |
| Convergence ratio R ≥ 1 | Coarse meshes outside the asymptotic range, or a bug | Refine further; if it persists, look for a bug | - |
| Large error that does not shrink steadily and sits in one region | Mesh distribution bug (inverted grading), boundary condition on the wrong face | Print the location of the maximum error; inspect the mesh there | duct with inverted side-wall grading (error always in the first cell from the wall) |
| Integral metric passes but a field check fails | A local error that averages out | Trust the field check; find the region | duct (pressure gradient passed at 40 and 80 cells) |
| Normalised residuals stall around 1e-3 while the result is constant to 10 digits | The field is exactly zero or uniform (cross-flow, cross-section pressure), so the normalisation divides by almost nothing | Judge convergence on the quantity of interest and on the meaningful field's residual; record why in the case | duct p, Uy, Uz |
| Quantity of interest converges slowly and geometrically over thousands of SIMPLE iterations | Pseudo-time diffusion: under-relaxation acts like a time step limited by the smallest cells, and the slow mode spans the largest dimension | Run more iterations; check the change over the last 10 %. Relaxation near 1 diverged; a multigrid velocity solver did not help | duct across a 10 mm half-width with 12 µm cells |
| Coarse elements too stiff, error 4-33 % | Locking / low-order elements (linear tets in bending) | Use quadratic elements; keep the linear-element run as evidence | cantilever TET4 |
| Output not on the requested grid | Tool silently ignored the requested settings | Fix how settings are passed; never relax the grid check | OpenModelica `-override` |
| Every numerical check passes but a validity check fails | The model is the wrong tool for this point | Revise the scenario or the model; withhold verdicts | quarter car at 36 km/h (wheel lift) |

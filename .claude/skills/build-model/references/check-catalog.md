# Check catalog

Independent checks used in this repo, by problem type. Pick at least one
reference per requirement metric, plus conservation, convergence, a field-level
comparison, and one validity check per assumption that can fail.

## Time-domain dynamics (ODEs)

| Check | Kind | Example |
|---|---|---|
| Closed-form solution | numerical | MSD step response vs analytical |
| Matrix exponential / `lsim` on a 10x finer grid | numerical | quarter-car bump (linear system with arbitrary input) |
| Closed-form spectral RMS from transfer functions | numerical | quarter car on an ISO 8608 road |
| Energy balance (input work = stored + dissipated, Simpson rule) | numerical | MSD, quarter car |
| Solver convergence: rerun with tightened tolerances | numerical | `tolerance_scale` in the backend |
| Steady state / return to rest / transient decayed before the window | numerical | MSD steady state, quarter-car `transient_decayed` |
| Second tool (same model in Modelica vs SciPy) | numerical | `[cross_check]` in the case |
| Wheel stays on the road (dynamic / static tire load < 1) | validity | `no_wheel_lift` |

## Structural FEA

| Check | Kind | Example |
|---|---|---|
| Beam theory (Euler-Bernoulli, Timoshenko with Cowper shear coefficient) | model form | cantilever tip deflection |
| Bending stress extrapolated from the smooth region, not the singular corner | numerical | root stress fit over 0.25L-0.75L |
| Reaction equilibrium (sum of reactions = applied load) | numerical | from the CalculiX `.dat` totals |
| Applied load recomputed from the solver deck; reactions balance the load on the non-fixed nodes | numerical | needed when a loaded face touches the clamp (uniform load on a cantilever's top face) |
| Deflection field along a free fibre vs beam theory, not only the tip value | numerical | catches a wrong load distribution that a single tip value can hide |
| GCI over the 3 finest meshes, regime-aware (monotone / oscillatory / divergent) | numerical | `discretization_<metric>` |
| Stress / yield < 1 | validity | `linear_material` |
| Deflection / length below a limit | validity | `small_deflection` |
| Large-deflection elastica (inextensible beam, dead load) for tip displacement, load path and deflected shape | model form | Turek-Hron flag `elastica_uy`, `load_path`, `deflected_shape` |
| Reaction + body load lumped on the constrained nodes (computed from the mesh) = total weight | numerical | flag `equilibrium` |
| Dynamics: a small-amplitude companion run at the linear modal frequency (the integrator alone) | numerical | flag CSM3 `integrator_small_amplitude` |
| Dynamics, undamped: returns to its start height; trough depths and periods repeat (energy drift) | numerical | flag CSM3 `returns_to_start`, `periodic_troughs`, `periodic_periods` |
| Published benchmark values as the requirement, or a band of published rows when they disagree | requirement | flag CSM1-3, Turek-Hron CFD1-2 |

## Stress concentration (CAD to FEA)

| Check | Kind | Example |
|---|---|---|
| Exact limiting case through the whole pipeline (a hole in a very wide plate: Kirsch, Kt = 3) | numerical | strap `test_pipeline_reproduces_kirsch_in_a_wide_plate`; caught the plane-stress expansion error that a clean GCI hid |
| Peterson (or Roark) stress concentration factor, labelled model form | model form | strap `kt_reference` |
| Force across the net section (integral of stress over the ligament = load) | numerical | strap `ligament_force` |
| Far field equals the nominal stress (load introduction far enough away) | numerical | strap `far_field_uniform` |
| CAD area or volume vs closed form | numerical | strap `cad_area` |
| GCI on the peak with the design-order test (a smooth peak converges; a sharp-corner peak does not) | numerical | strap mesh study |

## Vibration (modal analysis)

| Check | Kind | Example |
|---|---|---|
| 1D Timoshenko beam model (shear and rotary inertia), solved independently, for each bending family | numerical / model form | bracket `flapwise_reference`, `inplane_reference` |
| Saint-Venant torsion frequency, labelled model form (warping restraint stiffens short bars) | model form | bracket `torsion_reference` |
| Every expected mode found, and mode 1 is the type the requirement assumes | numerical | bracket `modes_identified` |
| First-mode effective mass fraction (0.613 for a uniform cantilever) | numerical | bracket `first_mode_effective_mass` |
| Mode shape along the part vs the reference, by modal assurance criterion (MAC) | numerical | bracket `first_mode_shape` |
| GCI on the frequency with the design order (4 for quadratic elements) | numerical | bracket mesh study |

## Contact (CalculiX surface-to-surface)

| Check | Kind | Example |
|---|---|---|
| Reactions balance across the two bodies | numerical | contact `equilibrium` |
| Contact pressure integrated over the patch equals the load | numerical | contact `contact_force_balance` |
| Hertz peak pressure, half-width, subsurface max shear and its depth, at the load the model carries | numerical | contact `hertz_*` |
| Penalty penetration small against the approach | numerical | contact `penalty_penetration` |
| Elements across the contact half-width (resolution) | validity | contact `resolution` |
| Stresses elastic (subsurface shear below Tresca yield) | validity | contact `elastic` |
| GCI on peak pressure and subsurface shear | numerical | contact mesh study |

## Fatigue (chained from a verified stress model)

| Check | Kind | Example |
|---|---|---|
| Upstream stress model's own checks carried into the chain (equilibrium, Kt vs handbook) | numerical | strap fatigue `equilibrium`, `kt_reference` |
| S-N curve fitted to cited test data, with its scatter reported | numerical | strap fatigue `sn_fit_scatter` |
| Extrapolated S-N curve vs an independent long-life value from a different source | model form | strap fatigue `sn_hcf_crosscheck` (ASM 96.5 MPa at 5e8) |
| Life inverted back to the stress amplitude (exact round trip) | numerical | strap fatigue `life_round_trip` |
| Notch stays elastic, or a plasticity correction (Neuber) is needed | validity | strap fatigue `elastic_notch` |
| Life by each data set separately, reported as the material-data spread | sensitivity | strap fatigue `life_by_data_set` |

Fatigue life is extremely sensitive to stress (here a 10 % stress change moves life about 3.4x), so report the spread from the material data and the notch model, not one number.

## Heat conduction (CalculiX)

| Check | Kind | Example |
|---|---|---|
| Energy balance: base reaction heat flow vs convective loss integrated from nodal temperatures | numerical | fin `energy_balance` |
| 1D fin theory with convective tip (tip temperature, heat rate), labelled model form | model form | fin `tip_reference`, `heat_flow_reference` |
| Cross-section-mean temperature profile vs 1D theory | numerical | fin `profile_reference` |
| The requirement metric finds the coldest / hottest point of the whole part | numerical | fin `tip_is_coldest` |
| GCI on the requirement metric | numerical | fin mesh study |
| Biot number below 0.1 for the 1D reference | validity | `one_d_reference_valid` |

## Geometry automation (CAD)

| Check | Kind | Example |
|---|---|---|
| Closed-form area / volume | numerical | plate with corner radii and holes |
| Geometry measured back from the B-rep (bounding box, hole centres, diameters) | numerical | `measure()` in the mounting-plate study |
| Exchange-file round trip (STEP re-import: volume, hole count) | numerical | `step_roundtrip_*` |
| Valid solid | numerical | `shape.isValid()` |

## Electric machines (Pyleecan + FEMM magnetostatics)

| Check | Kind | Example |
|---|---|---|
| Three phases' flux-linkage fundamentals equal and 120 deg apart | numerical | `motor_em` `phase_symmetry`, `phase_shift`; `motor_torque` `phase_symmetry_load` |
| Flux linkage from winding theory and the air-gap field's fundamental (2 N k_w1 B_1 R L / p) vs FEMM's coil integration | model form | `motor_em` `winding_theory` (0.3-0.6 %) |
| Zero mean torque at zero current | numerical | `motor_em` `open_circuit_torque` |
| Power balance over a whole period: mean(sum i d(phi)/dt) = mean torque x omega_m, an independent route to the stress-tensor torque | numerical | `motor_torque` `power_balance` (1e-3) |
| Imposed current amplitude vs the requested value (catches rms/peak mix-ups) | numerical | `motor_torque` `current_amplitude` |
| Maximum torque per amp found inside the current-angle sweep | validity | `motor_torque` `mtpa_bracketed` |
| dq torque equation 3 p (phi_d iq - phi_q id) (rms dq) against the stress-tensor torque: checks the mean dq flux linkages a look-up table interpolates | numerical (model form: harmonics) | `motor_lut` `dq_torque` |
| Exact pressure resultant on each symmetry plane (p x projected wetted area + end thrusts) and zero reaction at a single support of a closed vessel | numerical (exact) | `pressure_vessel` `equilibrium_y`, `equilibrium_z`, `self_balance_x` |
| Linearised membrane of the Lame cylinder (mean hoop = p Ri / t exactly) on a classification line far from discontinuities | analytical (exact) | `pressure_vessel` `lame_membrane` |
| Enough time steps per electrical period for the metric (48 for flux linkage and mean torque; more for ripple) | validity | `time_resolution` |
| GCI on the flux linkage, the back-EMF peak and the MTPA torque (mesh fineness) | numerical | motor mesh studies |
| Design inputs overlaid on the published drawing they came from | numerical | study 7 slot and pocket overlays |
| Rotor stress pipeline on a plain annulus vs the exact rotating disk | numerical | `rotor_stress` `rotating_disk` (4e-4) |
| Sector equilibrium: centrifugal + magnet load + constrained reaction components = 0 | numerical | `rotor_stress` `equilibrium` (1e-5) |
| Fixed-guided beam estimate of a rotor bridge (tension F/(tL) + end bending 3Fl/(t^2 L)) | model form | `rotor_stress` `beam_estimate` |
| Bridge membrane stress below yield (so a linear-elastic model applies through the section) | validity | `rotor_stress` `membrane_elastic` |
| Merged dq tables: the row both runs computed agrees (same model, mesh and rotor positions) | numerical | `motor_efficiency` `lut_merge` (bit-identical in practice) |
| Efficiency map from the half table against the map from the full table, in efficiency points: the interpolation error on the output itself | numerical | `motor_efficiency` `interp_map` |
| The table's own back-EMF and MTPA torque against the open-circuit and torque-curve studies | numerical | `motor_efficiency` `lut_back_emf`, `lut_mtpa_100A` |

## Turbulent CFD (RANS, fully developed pipe flow)

| Check | Kind | Example |
|---|---|---|
| Force balance of periodic flow: wall shear x perimeter = applied pressure gradient x area, two routes to the friction factor | numerical (exact) | `pipe_flow` `force_balance` (1e-12) |
| Bulk velocity held at the target by meanVelocityForce | numerical | `pipe_flow` `bulk_velocity` |
| Iterative convergence on the pressure gradient's history (the pressure residual never falls in a periodic domain) | numerical | `pipe_flow` `iterative_convergence` |
| Wall shear uniform along the wall (fully developed) | numerical | `pipe_flow` `wall_uniform` |
| First-cell y+ inside the wall treatment's range (below 1 resolved; 30-300 wall functions) | validity | `pipe_flow` `yplus_range` |
| Mean velocity against the log law, labelled model form (its constants scatter by a few per cent) | model form | `pipe_flow` `log_law` |
| Friction factor against Prandtl's smooth-pipe law (measured data through a correlation), Blasius and Petukhov beside it | validation | REQ-T1 |
| checkMesh passes, with the wedge's axial length tied to the cells so the aspect ratio stays low | numerical | `pipe_flow` `mesh` |
| GCI on the friction factor over a systematic refinement (wall cell halved with the cells); for wall functions, the wall cell held and the core refined | numerical | `pipe_rans_mesh_r1`, `pipe_rans_wf_mesh` |

## Heat transfer in a flow (CFD + scalar temperature)

| Check | Kind | Example |
|---|---|---|
| Energy balance: outlet bulk rise = 2 q L / (rho cp U H) | numerical | heated channel `energy_balance` |
| Wall temperature vs the Graetz thermal-entry solution at stations away from the heating ends | numerical | heated channel `wall_temperature_reference` |
| Peak vs the reference, labelled model form (the reference has no axial conduction) | model form | heated channel `peak_vs_reference` |
| Temperature field converged: max change over the last write interval / rise | numerical | heated channel `temperature_converged` |
| Laminar (Re), and Pe >> 1 for a reference that neglects axial conduction | validity | heated channel `laminar`, `reference_assumption` |

## CFD (incompressible, laminar)

| Check | Kind | Example |
|---|---|---|
| Exact solution (plane Poiseuille; rectangular-duct series) for profile, gradient, wall shear | numerical | channel, duct |
| Full-field comparison against the exact field (max error / u_max) | numerical | duct `velocity_field_reference` |
| Mass conservation (outlet vs inlet face flux) and imposed flow rate | numerical | `mass_conservation`, `inlet_flow` |
| Force balance (wall shear vs pressure gradient x H/2) | numerical | `momentum_balance` |
| Correlation for developing flow (Shah & London), labelled model form | model form | `pressure_drop_correlation` |
| Lubrication theory through slowly varying sections | model form | header + contraction estimate |
| Iterative convergence on the quantity of interest (history over the last 10 % of iterations) | numerical | duct `pressure_gradient_converged` |
| No cross-flow where the exact cross-flow is zero | numerical | duct `no_cross_flow` |
| GCI on every requirement metric | numerical | channel, duct |
| Re below transition | validity | `laminar` |
| Entrance length ends before the measurement window; centreline constant across it | validity | `entrance_before_window`, `fully_developed` |
| checkMesh passes | numerical | `mesh_quality` |
| Prescribed inflow profile checked face by face against the formula; flow rate carries the face-sampling error | numerical | Turek-Hron `inflow_profile`, `flow_rate` |
| Force history settled over the last 10 % of iterations; SIMPLE met its residual targets | numerical | Turek-Hron `forces_settled`, `converged` |

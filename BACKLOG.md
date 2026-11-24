# Backlog: harder studies

Planned studies, not started. Each one follows the usual loop (frame requirements, build the model, run, verify, report), and its independent check is fixed before any modelling starts. When a study starts, change its status here; when it is verified, it gets its own case files, a study module, tests and a page section, and moves off this list.

| # | Study | Why it's harder | Independent check | Tools | Effort | Status |
|---|-------|-----------------|-------------------|-------|--------|--------|
| 1 | Bolted joint: preload plus a side load, with friction contact | Contact with friction and preload: when does the joint slip or open? | VDI 2230 hand method; slip load = μ × clamp force | CalculiX | Medium | **Verified** (run 20261121-110554_bolted_joint_mesh_r1, 1.0 / 0.75 / 0.5 mm): the joint FAILS the slip requirement after settling, 2.39 kN against 2.5 kN (4.4 % short; needs about 15.5 kN preload); opening 13.1 kN passes; GCI 1e-4. The FE slip load sits 0.13 % under mu F_V because the interface tilts with the strain (shortfall linear in 1/E); a rigid-limit companion solve recovers mu F_V to 1e-7; [portfolio/16](portfolio/16-bolted-joint-slip.md) |
| 2 | Cold plate, full thermal chain: coolant CFD → conduction through the aluminium plate → thermal stress | Three physics chained, each verified before passing results to the next | Fin and slab conduction theory, closed-form thermal stress, energy balance at every handoff | OpenFOAM → CalculiX | Medium-high | **Verified** (run 20261121-094235_cold_plate_mesh_r1, 40 / 60 / 80 cells): component face 40.99 C (limit 45), coolant rise 7.20 K (limit 10), thermal stress 46.8 MPa (limit 60); all requirements pass, GCI <= 3.5e-4; [portfolio/15](portfolio/15-cold-plate-thermal-chain.md) |
| 3 | Bracket optimisation loop: the agent changes geometry, meshes, solves and checks, repeating to minimise mass under stress and stiffness limits | The agent drives a design, not just one case | Every candidate passes the existing checks; optimum spot-checked against beam theory | CadQuery · Gmsh · CalculiX | Medium | **Verified** (3D machined clevis bracket; confirmation run 20261121-115130_clevis_confirm_r2b): lightest design found 371.9 g (lug 10.17 mm, gussets 9.07 x 36.36 mm), 4.1 % under the start, peak 98.3 MPa (98.9 with mesh uncertainty) against 100. Took three optimisation runs: a 1 % margin too small for a fillet peak, a global mesh study that never refined the fillet, and an optimiser stalled in mesh noise (resolved with local fillet refinement and a local response surface); [portfolio/12](portfolio/12-bracket-optimisation.md). First version (tapered cantilever) kept as superseded evidence |
| 4 | Notched bar with plasticity | Nonlinear material: stress beyond yield, residual stress after unloading | Neuber's rule, Glinka's method | CalculiX | Medium | **Done**: proof test at 15 kN strains the hole edge 0.58 % (limit 1 %), leaves -77 MPa residual; [portfolio/14](portfolio/14-strap-proof-plasticity.md) |
| 5 | Buckling: column or thin panel, linear eigenvalue, then with a small imperfection | Stability: a load-path problem, not just stress | Euler and Johnson formulas, Southwell plot | CalculiX | Low-medium | **Done**: longest acceptable strut about 587 mm; [portfolio/13](portfolio/13-strut-buckling.md) |
| 6 | Fluid-structure interaction: flexible flap in a channel | Coupled multiphysics | A published benchmark | OpenFOAM · CalculiX · preCICE | High (a weekend or more) | **In progress** (study 6): CSM1-3, CFD1-2 verified; FSI1 verified in part (drag, lift; tip within 1 %); FSI3 mesh study done 2026-11-24 (3 levels, every requirement passes on the finest; frequency and drag mean verified, uy amplitude extrapolates to 0.02 %); FSI2 two levels (0.7 %), the finest crashes at 8.8 s (diagnosis run `turek_hron_fsi2_mesh_c_diag`); open: FSI2 level-c fix on all three levels, a time-step study; [portfolio/17](portfolio/17-fsi-flag-turek-hron.md) (draft) |
| 7 | Electric motor, an open-source Motor-CAD alternative: the Toyota Prius IPM motor (2004, ORNL) | Three physics on one machine. Electromagnetics: torque, back-EMF, flux-linkage and efficiency maps. Thermal: a lumped network from the geometry. Mechanical: rotor stress at overspeed | The published Prius data (Oak Ridge National Laboratory); an analytic air-gap field; the thermal network against CalculiX heat transfer on a stator section; power balance at every map point | Pyleecan + FEMM (pyFEMM), Python or OpenModelica, CalculiX. Options considered 2026-11-20: SyR-e (needs MATLAB), SWAT-EM (windings), Elmer and GetDP (3D) | High | **In progress** (study 7), run as a client project since 2026-11-23: blind comparison FAIL 3/3 (kept on record); calibration withdrawn as a model; revision 5 (client data, uncalibrated): flux about 18 % high in back-EMF and torque alike (solver, steel, end effects ruled out; magnetisation level leading, client questions); every design check recomputed 2026-11-24 (efficiency 4.4 points high against ORNL; REQ-M5 pass; REQ-TH1 27.7 kW; REQ-M4 415 MPa fail); open: table refinement at low iq (running), `reports/motor/` refresh, client answers; [portfolio/20](portfolio/20-prius-traction-motor.md), `validation/motor_ornl/STATUS.md` |
| 8 | Pressure vessel with a nozzle, ASME VIII-2 Part 5 elastic stress analysis (study 18) | Design-code verdict from linearised stresses on classification lines; rule vs analysis | Lame cylinder, exact pressure resultants, simplified pressure-area rule | CadQuery · Gmsh · CalculiX | Medium | **Done**: [portfolio/18](portfolio/18-pressure-vessel-nozzle.md). Placement decides: toe lines PL 205.1 against 207 (about 11.7 mm), crotch line 256.7 (about 20 mm), rule 16 mm; hemispherical head about 6.5 mm (axisymmetric model, checked against shell theory) |
| 9 | Turbulent CFD: pipe friction, then the backward-facing step against measurements (study 19) | Turbulence modelling; validation against measured data | Prandtl's smooth-pipe law; Driver & Seegmiller's step data | OpenFOAM | Medium | **Done**: part 1 (pipe friction) verified, +2.4 % on Prandtl (GCI 0.48 %); part 2 (step) scored once against Driver & Seegmiller 2026-11-23: REQ-S1 PASS (+2.3 %), REQ-S2 PASS (7.0 % rms), REQ-S3 FAIL (recovery +0.0227, limit 0.02; 2D, no side walls); finest step mesh unconverged at its cap (verification FAIL, reported); [portfolio/19](portfolio/19-turbulent-pipe-friction.md) |
| 10 | Random vibration of the study-4 bracket (C) | Forced response to a PSD; 3-sigma stress; vibration fatigue | Miles' equation; effective mass | CalculiX · Python | Medium | **Verified** (run 20261123-100907_bracket_random_mesh, 3.1 / 1.95 / 1.22 mm): PASS on all three: 3-sigma root stress 38.6 MPa (limit 236.7, GCI 1.3 %), damage 2.4e-3 (limit 0.5), tip 0.345 mm (limit 1.0, GCI 0.1 %); harmonic check 1e-6 after finding CalculiX's absolute-damping base motion; a 16.5 GB .frd from carried-over output requests, fixed; [portfolio/21](portfolio/21-bracket-random-vibration.md) |
| 11 | Natural convection and radiation (D) | Buoyant flow; view-factor radiation | de Vahl Davis cavity benchmark; two-surface exchange | OpenFOAM · CalculiX | Medium | Documented, not started |
| 12 | O-ring compression (E) | Hyperelastic large strain with self-contact | Published force-squeeze correlation; J about 1 | CalculiX | High | **In progress** (framing approved 2026-11-24; building) |
| 13 | Cracked plate, K and crack growth (F) | Fracture mechanics; damage tolerance | Handbook K solutions; G-K consistency | CalculiX · Python | Medium | **Done** (runs edge_crack_mesh r0-r2 and edge_crack_noise, 2026-11-23): K within 0.66 % of Tada, critical crack 37.0 mm (verified), life about 92,000 cycles from 2 mm (+-0.2 %, formally unverified: mesh noise), inspection interval about 46,000 cycles; REQ-F1, F2 PASS; [portfolio/24](portfolio/24-cracked-plate-growth.md) |
| 14 | Rotor critical speeds (G) | Rotordynamics, Campbell diagram | Jeffcott rotor closed form | ROSS (Python) | Low-medium | **Verified** (runs 20261123-162721 and -163104): 50 mm shaft FAILS (critical in range), 60 mm FAILS on soft bearings (14.3 %), 65 mm PASSES (margin 23.8 % or more, under 5 um); [portfolio/23](portfolio/23-fan-rotor-critical-speeds.md) |
| 15 | Probabilistic uncertainty on an existing study (H) | Sobol indices, failure probability | Monte Carlo convergence; analytic linear case | Python | Low-medium | **Verified** (run 20261123-104847_bracket_random_uq, on study C): pf_any 2.2e-6 against 1e-3, tip governs (beta 4.55), damping 71 % of the damage variance; [portfolio/22](portfolio/22-bracket-random-uncertainty.md) |

Notes
- Study 2 can start from the verified heated-channel flow (`studies/heated_channel.py`).
- Study 6 needs preCICE and its OpenFOAM and CalculiX adapters installed in WSL, which needs sudo.

### Study 6: what the install needs (checked 2026-11-21)

- **The preCICE OpenFOAM adapter does not support our OpenFOAM 14 (openfoam.org).** Adapter v1.4.0
  targets the openfoam.com line, v1812 to v2606; its newest openfoam.org branch is OpenFOAM 10
  (last updated 2024). So the coupled stage needs openfoam.com **v2512** installed alongside ours.
  It installs to `/usr/lib/openfoam/openfoam2512`, and the harness only looks in `/opt/openfoam*`,
  so the existing studies are unaffected. v2606 for Ubuntu 22.04 is only a release candidate
  (2606.0~rc2) in that repository.
- **preCICE 3.5 dropped Ubuntu 22.04**, so use 3.4.1, the newest release with a jammy package.
  CalculiX adapter 2.20.2 has a jammy package and needs libprecice3 >= 3.0.
- Already downloaded to `~/precice-debs` in WSL. Both SHA-256 values match the release's `.sha256`
  file and GitHub's asset digest:
  `libprecice3_3.4.1_jammy.deb` 56253637...a854d895b,
  `calculix-precice3_2.20.2-1_amd64_jammy.deb` 9942fa30...fe49d9cc4.
  A simulated install resolves from Ubuntu's own repositories: 137 new packages (Boost, PETSc) and
  7 routine upgrades.
- `~/openfoam-esi/add-debian-repo.sh` (SHA-256 f7fa2883...3310b5b) has been read. It only adds
  `/etc/apt/sources.list.d/openfoam.list` and the repository's signing key, then runs `apt-get update`.

The sudo steps (in WSL, about 15 minutes, roughly 1.5 GB):

```bash
sudo bash ~/openfoam-esi/add-debian-repo.sh
sudo apt-get install -y openfoam2512-dev
cd ~/precice-debs && sudo apt-get install -y ./libprecice3_3.4.1_jammy.deb ./calculix-precice3_2.20.2-1_amd64_jammy.deb
```

The OpenFOAM adapter itself is then built without sudo (`./Allwmake` against v2512).

Plan: Turek and Hron (2006), the flexible flag behind a cylinder, whose paper publishes values for
each part on its own: CSM1 to CSM3 (solid only, CalculiX, nothing new needed), CFD1 to CFD3 (fluid
only, OpenFOAM 14, nothing new needed), then FSI1 to FSI3 coupled through preCICE. Each part is
verified before the coupled run, as in study 2.

## Session handoff (2026-11-23, 20:52; first written 2026-11-21, 23:10)

Read this first. Files under site/, docs/, DASHBOARD.md, `scripts/make_study_renders.py`, `scripts/make_figures.py`,
`scripts/make_drawings.py`, `scripts/figkit.py` and `.claude/skills/publication-figures/` belong to the dashboard
session (it commits in this clone: add and commit only your own paths, in one command; never leave files staged; a
gitignored run dir needs `git add -f`, and a failed add can leave files staged: check `git status` after every
commit). Rules that bind:
- **Study 7 runs as a regular client project since about 13:50 (user):** use everything a client would hand over
  (drawings, bill of materials and masses, material data, routine tests) as input, look up anything missing before
  assuming it, never calibrate to hide a gap; test results the job must predict stay targets. Short version of the
  study: `validation/motor_ornl/STATUS.md`; inputs: `CLIENT_DATA.md`.
- **Isolate one effect per revision; predictions in the case header committed BEFORE the run; Results after.**
- **Take every clock time from `date` in the same command** (memory `clock-times-from-date`: guessed times were wrong
  five times today and each needed a correction commit).
- **Measure a noise floor before declaring it** (study F); **compare the statistic the test reports** (study 7's
  locked-rotor maximum against the model's mean, withdrawn the same hour).
- Every lesson into the matching skill the same session; `scripts/scrub_paths.py <run dir>`, `git add -f` without
  `*.inp`, `*.dat`, `__pycache__`, files > 600 kB, then `tests/test_privacy.py`; never two FEMM cases at once; check
  free RAM on long runs.

### Running at 08:25, 2026-11-24 (scratchpads under `%LOCALAPPDATA%/Temp/claude/cb67dd1e648f8970/<session>/scratchpad/`)

| Job | Run dir (log) | Done about | When it finishes |
|---|---|---|---|
| Study 6: FSI2 mesh study revision 1, levels a / b / c side by side (`cases/turek_hron_fsi2_mesh_{a,b,c}_r1.toml`: frozen 1 / d mesh motion, the fix chosen from the level-c diagnosis, done 08:12, and an offline moveMesh test), started 08:24 | `runs/*_turek_hron_fsi2_mesh_*_r1` (`fsi2_r1_{a,b,c}.log`, session 8f53debf) | about 15:30-18:30 | Score P1-P5 (headers); `scripts/combine_mesh_levels.py` over the three r1 runs; page 17 (drop 'draft' if c passes); run-case / tool-notes skill lines. |
| Study 7: revision-5 table refinement (`motor_prius_lut_{cold,hot}_refine_rev5`), cold done 08:23 (dq-torque FAIL on the new low rows at id -100 to -300 A, wider than P1's -175 to -300), hot running | `refine_chain.log` (session 8f53debf) | about 08:55 | Score P1-P4; rerun the revision-5 efficiency and thermal cases on the merged tables (new cases, predictions first): does the 5500 rpm hot corner converge? |

### Next (in order)
0. **Done 2026-11-24 00:47-06:42 (this session):** FSI3 mesh study (all three levels, combined check, page 17);
   study 7 revision-5 chain finished and scored: four dq tables (cold / hot PASS; both low-iq FAIL the dq-torque check
   at iq 6.25 A, as predicted), the efficiency map (ORNL gap 4.37 points; REQ-M2, M5 pass), the field export for the
   site (gate passed; the dashboard session published it), thermal (27.7 kW; a hot-corner state without a fixed point
   diagnosed) and rotor overspeed (415 MPa, fail; the rotor study now loads the case's machine and reads drawn
   pockets); page 20 and STATUS updated, dashboard session told. User's choices: FSI2 option A now, B running;
   parallel work = motor rotor + thermal on revision 5 only (not FSI3 dt, not new studies 11/12).
1. **Study 7, the 18 % flux excess: step 4** (`validation/motor_ornl/CALIBRATION_PLAN.md`, "step 4"; questions for the
   client in `CLIENT_QUESTIONS.md`). Ruled out: the solver (independent ElmerFEM model, +0.10 %), the steel (at most
   0.35 %), the measurement side; bounded: end effects 1.3-3.7 %. Done 21:23: the drawing's magnet stops measured (`scripts/motor_drawing_stops.py`): revision 5 already puts
   every magnet on its stop (pockets within 0.075 mm; at most 0.4 mm of play), no revision needed. So the magnetisation
   level is reported as the leading
   hypothesis (effective remanence 1.10-1.12 T, 88-90 %) with the fluxmeter test that settles it, never fitted. ORNL's measured air-gap flux (TM-2004/137 Fig. 13) would separate the two
   directly; the user decided to leave it for now (item 4). The inductance mismatch is framed (21:51,
   `scripts/motor_inductance_frame.py`): mean +4.3 %, saliency term +22.7 %, decided by how ORNL's static test was
   made (client question 6); no run until then. The MDPI Machines 2019 7(4) 75 PDF can be read only if the user saves it (its server blocks fetches).
2. **FSI3 mesh study done 03:12** (a / b / c 02:05 / 01:31 / 03:12, all PASS; c passes every requirement; combined: frequency 0.13 %, drag mean GCI 0.90 %, uy amplitude GCI 1.45 % extrapolating to +0.02 % from the benchmark; drag/lift amplitude anomalous order; ux mean order 0.89; `validation/turek_hron/fsi3_mesh_study.json`, headers, page 17 updated, 38da0b6). FSI3 c ran 8 s at Courant 2.36 under PISO with half FSI2's swing. FSI2 levels a and b done 21:18 / 21:28 and scored (case
   headers: P1 held on both, P2 held, b repeats turek_hron_fsi2 exactly, P3 held on a, P5 missed; a vs b 0.1-0.7 %);
   FSI2 level c's rerun FAILED again at t = 8.836 s (00:02; max Courant 2.2 -> 5.8 -> 17.9 in two steps, then a
   floating point exception in GAMG): a mesh-motion cell collapse or a local PISO instability; the tail cannot
   separate them (case header). Options put to the user (01:30, no answer yet): A) accept two levels (a vs b
   0.1-0.7 %), no three-level GCI, no compute; B) rerun c unchanged but write fields from 8.80 s, to see which
   mechanism (~6 h), then one fix applied to all three levels (~9 h more); C) all three levels with
   nOuterCorrectors 3 (~15-20 h, fixes only the instability). Recommended: A now, B when the CPU is free. A
   settings change must go to all three levels, or the levels are no longer comparable. FSI3 c (1.77 mm, Courant
   2.36) is the same risk: read its result first.
3. Motor field render for the site: re-export from a revision-5 solution (`scripts/export_femm_field.py`; copy the
   evidence run's .ans to build/ first, Pyleecan overwrites it); the revision-4 export in `build/render/motor_rev4_centre`
   has the wrong magnet. Refresh `reports/motor/` after the 18 % is explained.
4. Future, to consider (user, 2026-11-23: leave for now): ORNL's measured air-gap flux map (TM-2004/137 Fig. 13) as a
   direct check of the magnetisation hypothesis; teardown-only data, so it needs the user's go-ahead under the
   realistic-information rule. (Settled: the site shows the user's name, memory `public-contact`; the stale temp dirs
   and the Elmer zip were deleted 2026-11-23 on the user's OK.)

### Done 17:48-20:52
- **Study 7, 18 % diagnosis:** step 3 end effects, hand estimate -1.3 to -2.4 % (`scripts/motor_end_effects.py`;
  end clamping piece non-magnetic from TM-2004/137 Fig. 9's photo); step 2 steels scored (-0.35 to +0.14 %, not the
  cause); **step 3b: an independent 2D model in ElmerFEM** (`models/motor/elmer_em.py`, `scripts/export_motor_elmer.py`,
  `scripts/motor_elmer_check.py`; Elmer 26.1 in `~/tools/elmer-26.1/`, gmsh 4.15 as optional dependency `em`): closed-
  form magnet check -0.07 %; attempt 1 stopped (ring surfaces meshed as outer + inner area, 10x low; Newton limit cycle
  on a linear B-H table), fixed with an area-balance check; attempt 2 within **0.10 %** of FEMM (P1-P4 held, P5
  missed as written); step 4 written; `CLIENT_QUESTIONS.md`.
- **Study 6:** FSI2 c's first run failed at 8.835 s with its log lost; rerun started; Courant numbers measured per
  level from the live logs.
- **Harness:** a failed point keeps the last 400 lines of every log its study did not copy
  (`points/<label>/solver/failure_tails/`, all studies; tests).
- **Skills and memory:** run-case (read failure tails first; Courant per level before a fixed-dt mesh study; live
  logs on long runs; run time as the sum over points), verify-against-reference (what a second solver settles),
  frame-requirements (read the photos before calling a fact unknown), tool notes (ElmerFEM), skill-table rows for
  studies F and G; memory: edit files with Edit or Python with asserts, never shell chains.

### Done 12:40-17:48
- **Study 7 turned into a client project.** Revision 4 at 1.12 T scored (P5 held; 1.12 T is ORNL's hot design value,
  TM-2004/120 "BrT"); drawing audit (`DRAWING_AUDIT.md`); **client data pack** from ORNL/TM-2010/253 Table 2.7 and
  Fig. 2.72, TM-2004/185, the test and thermal reports (`CLIENT_DATA.md`): magnet 83.1 x 18.9 x 6.5 mm, 77 g (**revision
  4's 5.31 mm overturned**), Br 1.255 T at 20 C, phase resistance 69 mOhm at 21 C, back-EMF test line to line at 25 C.
  **Revision 5** (client data, nothing fitted; all predictions held): back-EMF 105.2 / 106.1 V (+17.7 / +18.7 %),
  Ld / Lq 1.72 / 5.50 mH, torque run (mean +3.9 to +21.8 %) and the **locked-rotor emulation** (+17.5 % at 50 A, mostly
  17-19 %). A "tests disagree" diagnosis was withdrawn (mean against maximum). Pages 20 and STATUS rewritten; dashboard
  given a presentation note (results split into "model against test" and "design findings").
- **FSI1 mesh r2 scored** (P1-P5 held: uy, drag, lift verified; ux unverified as predicted). **FSI3 mesh study started.**
- **Study H scored** (pf_any 2.2e-6, PASS; damping 71 % of the variance); page 22.
- **Study G (rotor critical speeds) built and verified:** ROSS 3.1 in `~/.venvs/ross`; 50 mm FAILS, 60 mm FAILS on soft
  bearings (14.3 %), 65 mm PASSES (23.8 % or more); page 23.
- **Study F (crack growth) built:** K within 0.66 % of Tada, critical crack 37.0 mm (verified), life about 92,000
  cycles (+-0.2 %, formally unverified: mesh noise measured at 1.1e-3), inspection interval about 46,000; three
  revisions and a noise case; page 24.
- **Skills:** frame-requirements (read a source's own definition; assemble the client data pack first and cross-check
  dimensions by mass; compare the test's statistic; hand-estimate simplifications across the band), build-model step 3
  (complete audits), convergence-diagnosis (measured noise floors; finite-difference steps). Memories: client-project
  mode, clock times.

### Done 07:40-12:40
- **Study C (random vibration) verified:** run 20261123-100907, 38.6 MPa / 2.4e-3 / 0.345 mm, all PASS (GCI 1.3 % /
  0.1 %); page 21. A first attempt was stopped: CalculiX output requests carried into the harmonic steps (16.5 GB .frd,
  38 GB RAM); fixed, tool note, run-case resources section.
- **Study 19 part 2 scored once:** REQ-S1 PASS (+2.3 %), REQ-S2 PASS (7.0 % rms), REQ-S3 FAIL (+0.0227; 2D, no side
  walls); finest mesh unconverged at its cap (reported); outlet and inlet-turbulence cases PASS; page 19 part 2.
- **Study 7:** REQ-M1 on the calibrated machine 856.5 V verified FAIL (ORNL 850 V); revision 2 (ORNL's no-load spin
  loss = the model's, gap unchanged); revision 3 (measured winding temperature: gap 4.50 -> 4.05 points); diagnostic
  (ORNL drew 6-30 % more current: 43 % of the missing loss); Table B-1 transcription repaired (unscored columns);
  revision 4 above. Page 20 and PORTFOLIO updated.
- **Study H built:** `harness/uncertainty.py` (Sobol, FORM with SLSQP fallback, importance sampling; closed-form tests),
  `studies/bracket_random_uq.py`; framing approved; evidence run started.
- **Skills:** build-model step 3 (drawing audit), frame-requirements 6a (opening vs using data, column audits, clock
  times, calibration as a model-form alarm, isolate effects), run-case resources, tool notes (CalculiX output carry-over
  and 20-character fields, Pyleecan HoleUD and MACHINES).

### Done 03:30-07:40
- **FSI1 noise (study 6):** four meshes at 1.72-1.83 mm. b, c, d (with r1's 1.77 mm mesh) scatter uy(A) 1.94 %, ux(A)
  0.20 %, drag 0.075 %, lift 1.12 % peak to peak: r1's uy, drag and lift differences are within the noise, ux's are
  not. **Mesh a gave uy(A) 28 % low with every check passing**: one quad wrapped around the flag's upper tip corner
  (165 deg), found by rebuilding its mesh from the kept mesh.geo; 24 Turek-Hron meshes scanned, only a is affected
  (FSI2 / FSI3 / r1 / CFD clean, 128 deg at most). New point check `flag_cells` (140 deg), `mesh_noise_rel` per metric in
  the FSI run level, tests (7c4038f); runs committed (6b074fd); skills (bafc496). Optional: the same check in
  `studies/turek_hron_cfd.py` (its meshes are clean; future runs only).

### Done 22:25-03:30
- **Study 7 post-test calibration finished** (c6d39dc, 7189003, 652c7b6; report artifact version 7): A's efficiency
  is 4.5 points high at the median over ORNL's 393 points (blind 5.2, B 5.3): the 2-point limit is still missed, the
  rest being losses the model leaves out. **REQ-M5 flips to FAIL** with A (48.0 kW cold, 44.5 kW hot at 6000 rpm, from
  58.6 / 53.7): weaker magnets, less field-weakening torque per ampere; I predicted the opposite. The efficiency case's
  verification failed on three checks that do not touch the comparison (my back-EMF reference from a fineness-8 run;
  half-table iron loss 7 %; the 10 N m row). Open: the thermal rating is not recomputed with A; a fineness-2
  open-circuit point at 1.036 T would clear the back-EMF check; the d-axis saliency (2.6 against 3.2).
- **FSI2 and FSI3 scored** (3b5c533, 8720c51, page bf16065): every benchmark quantity within 2.1 % (FSI2) and 9 %
  (FSI3) on one mesh; every requirement passes but is UNVERIFIED: the force-transfer check was defective. Under the
  preCICE adapter CalculiX writes the `.dat` (clamp reaction) only at the last increment (FSI3's stayed empty 8 h,
  then held one block), so whole-period means never existed and the check fell back to the end-of-run balance, which
  includes the swinging flag's inertia. The FAILs stand. Fixes: the fallback now reports not-evaluable; NEW
  per-window check from preCICE watch-integrals (sum of Force the solid receives against the sum the fluid writes,
  and that against OpenFOAM's forcesFlag), no inertia involved; smoke test in scratch. FSI1 r1's check description
  corrected (its value stands: steady). Next for FSI2/3: a mesh / time-step study with the working check (each
  ~8 h on 2 cores; schedule after the FSI1 noise runs).
- **Study 7 dq tables at 1.036 T:** cold and hot PASS, MTPA 233.5 N m at 100 A (predicted 233); cold_lowiq FAILs the
  known dq-torque check in six columns (the original failed it in three; my P1 overlooked that). Efficiency case for A
  committed with predictions (b2d7092): I predict the median gap to ORNL GROWS (5.5-7 points), A does not close it.

### Done 20:30-22:25
- **Study 18 reviewed** (147170e): the inner corner is not singular (peak converges, 351 MPa); a Kirsch hand check
  explains the crotch value (2.56 x nominal hoop against 2.50 at an unreinforced hole edge); recommendation: judge the
  opening by the crotch line (about 21 mm or a pad).
- **Study 7 calibration:** A selected first on torque (f097624), then, after the user asked whether a client would
  have torque data, re-decided on ORNL's static inductances (TM-2006/423 p. 51, opened with the user's OK; predictions
  first, 9082d9f): Ld 1.92 / Lq 5 mH against A 1.70 / 5.38 and B 1.11 / 3.50 (per phase): **A** (3b6a5eb). Torque
  stays 12-14 % high at 150-250 A. dq tables at 1.036 T running for the efficiency test. Page 20 has a revision
  section (06274d9). Skill frame-requirements: choose between hypotheses with the cheapest routine test (44f187e).
- **Study 19 part 2:** limits agreed (REQ-S1 10 %, REQ-S2 15 % rms, REQ-S3 0.02); model, study, tests committed
  (9374d60). SST start-up fix: first-order k, omega for 500 iterations, then limitedLinear 1 (linearUpwind diverged).
- Process: a `| tail` pipe masked two test failures (a home path in BACKLOG, since fixed; missing skill-table rows,
  since added). Use `set -o pipefail` or no pipe before committing. The home path remains in commits bee3774..3167966
  (matters only if the repo goes public).

### Done 19:45-20:30 (work order below)
- **Study 7:** open-circuit calibration scored (d6ddf02): back-EMF linear in Br, **calibrated remanence 1.036 T**
  (full waveform to 89.78 V; fundamental route 1.037); prediction missed by about 1.5 %. Machine built and set in the
  torque case (10ce915); torque run going.
- **Study 18, item 1 DONE, and the answer changed.** Crotch classification lines (82b3c74 .. 7d1b7a0): PL through the
  crotch **256.7 MPa against 207, verified FAIL** (r1 with the measured mesh noise 3e-3; noise case: five regenerated
  meshes at 4 mm scatter 8e-4 to 2.9e-3). Wall where crotch PL = 207: about 20.1 mm (toe 11.7, rule 16). Toe line
  moved a weld size out: -10 %. The 14 mm recommendation is withdrawn. **Head-to-shell junction:** new axisymmetric
  model (`ccx_vessel_head_axi`), equal thickness against thin-shell theory (bending -1.5 %, hoop -0.04 %, verified);
  head thickness sweep: the head's own membrane governs, about 6.5 mm (rule 6.34); junction P + Q 210 MPa at 6.5 mm.
  One stated limit: the 8 mm head's P + Q spreads 1.5 % (unverified, margin 58 %). Page 18 rewritten (03fc4a9).
- **Item 5 DONE:** coolant page and memo say the 28-42 Pa range is the four verified corners (54f8001); quarter car
  already plain.
- **Item 6 (skills audit) DONE:** every "What the checks caught" lesson on pages 02-20 is in a skill or enforced by
  code, except study 13's *BUCKLE output (tool note added); pressure-vessel checks moved out of the electric-machines
  table; new notes: CAX8 reactions per 2 degrees, the 21-character number limit on any card, the sampled-maximum
  pattern, study 18's mesh noise, placement sensitivity (check catalog and frame-requirements).
- **Item 7:** scan done; only FSI2/FSI3 (page 17) and the calibration (page 20) remain in progress. `reports/motor/`
  does carry the copper correction (the note further down saying otherwise is stale).
- **Item 2:** n640 probe converges at 1 mm axial length (slowly: f about 0.01835 at 80000 iterations); r3 running.
- **Study 19 part 2 UNBLOCKED (20:31):** the ERCOFTAC classic database answers again (case 030, Driver & Seegmiller);
  all seven data files fetched to `~/data/ercoftac_case030/` (Windows home) (outside the repo: redistribution terms
  not checked; `SOURCE.txt` has the URL and sha256; turbmodels.larc.nasa.gov still has the certificate mismatch).
  **Prior knowledge to declare in part 2's case headers:** printing the head of `bkst-reattach.dat` showed the
  measured reattachment length, Xr/H 6.26 +- 0.10 at 0 deg (5.82 at -2, 6.72 at +2); nothing else was opened. Part 2
  is new work: start it after the clean-up, with the user's go-ahead, as for study C.
- **Item 3 (FSI1 noise), prepared, not started:** at 1.77 mm each coupled run takes about 1.7 h alone and the harness
  runs points in sequence, so run one case per perturbation (fluid_cell_size_m 0.00172 / 0.00175 / 0.00180 / 0.00183;
  r1's 0.0017678 is the fifth) concurrently once FSI2/FSI3 are done; then r2 of FSI1 declares the measured
  `mesh_noise_rel` (a 5 h rerun).

**For the dashboard session:** study 18's answer changed (placement-dependent; nozzle needs about 20 mm with the crotch
line; head about 6.5 mm; a new axisymmetric head model). The site's study-18 page and any "passes narrowly" line are
stale. README model table has a new row.

### Study 7: post-test revision in progress (plan `validation/motor_ornl/CALIBRATION_PLAN.md`, committed 31449ff before computing)

- Blind result (stays the record): back-EMF +23.5 %, torque +7 to +24 %, efficiency +5.2 points: FAIL 3/3
  (`validation/motor_ornl/RESULTS.md`; log `reports/motor/blind_comparison_log.md`).
- User's decisions (~19:10-19:20): calibrate on back-EMF (the routine test), predict the rest; **do NOT open ORNL
  TM-2004/137 Fig. 13** (teardown-only data, against the new rule). Torque chooses between the hypotheses (so it becomes
  calibration data); efficiency is the out-of-sample test.
- Hypothesis B (series turns x 0.807) scored: torque rms error 10.7 % (peak reading; -17 % at 50 A to +4 % at 250 A),
  31 % (rms reading); efficiency unchanged, 5.3 points high (turns don't change copper loss at a given torque).
  `scripts/motor_calibration.py` (writes `validation/motor_ornl/calibration.json`).
- Hypothesis A (remanence): running (above). After the torque run: `scripts/motor_calibration.py --torque-run <run id>`;
  select by the smaller rms torque error; score efficiency for the selected hypothesis (the script does B's; add A's from
  a dq table at the calibrated remanence only if A wins: that needs the LUT runs, several hours of FEMM); write the
  outcome into CALIBRATION_PLAN.md (Results), portfolio page 20, the reports (`reports/motor/build_report.py`, republish
  artifact https://claude.ai/artifact/C6dNdzjs1FdP8vVb6MLaRy).

### NEXT WORK ORDER (user, 2026-11-22 ~19:35): clean up every study already run, then study C

"First focus on all the studies we already ran, and clean them up as needed. Anything we need to improve in that
modelling that would translate to a skill? No loose ends: people are looking at these. Once that is complete we can
move to study C." Study C defaults APPROVED: flat 0.04 g^2/Hz 20-2000 Hz (8.9 g rms), 1 h per axis, 2 % modal damping,
S355-type steel (yield 355 MPa, a published S-N curve), all marked synthetic (framing under "Open for the user" (a)).

Already done (19:35): stale status lines fixed (8b78f7e); every relative link in portfolio/, PORTFOLIO.md, README.md
resolves. Loose ends found by a keyword scan (draft / pending / unverified / withheld / not yet), to close or to state
plainly as final:
1. **DONE 20:30** **Study 18:** classification-line placement sensitivity "not yet quantified" (portfolio/18 line ~54) and the
   head-to-shell junction against shell discontinuity theory: run both (CalculiX), predictions first.
2. **Study 19:** REQ-T1 unverified by 0.05 point of GCI (1.05 % vs 1 %): an n640 level with a 1 mm axial length would
   settle it (stall risk: probe convergence first, BACKLOG study 19 notes); part 2 still blocked (retry the NASA host).
3. **Study 6 FSI1:** tip displacement's mesh uncertainty not estimable (+-0.5 % regenerated-mesh scatter): measure the
   scatter at one nominal size (small perturbations of the 1.77 mm mesh) and declare `verification.mesh_noise_rel`, then
   re-verify r1 (CFD1/CFD2 carry the same issue: "the fix (nested meshes ...)" on page 17).
4. **Study 7:** hot REQ-M5 unverified (one map cell); the 10 N m row above 4000 rpm unresolved; the calibrated revision
   (running). Decide which stay as stated limits.
5. **DONE** **Study 5 (coolant channel)** one case unverified (settling); **quarter car** wheel lift (a validity flag, correct as
   is). Check each page states these plainly.
6. **DONE** **Skills audit:** for every study page's "What the checks caught", confirm the lesson is in a skill (tool-notes,
   convergence-diagnosis, check-catalog, frame-requirements) or is enforced by code; add what is missing; prune what is
   duplicated (CLAUDE.md "Keep the skills current").
7. **Every page:** numbers match the latest run reports; no "running" / "pending" left except FSI2/FSI3 until they land.
Then study C.

### Open for the user
(e) **Study G framing: APPROVED by the user 2026-11-23 ~16:05 (with F and the FSI3 mesh study; building since 16:13).**
*Decision:* does a fan rotor (steel shaft 50 mm, bearing span 1.0 m, central impeller 400 x 25 mm steel, 24.7 kg)
running 1000-3000 rpm on a variable-speed drive keep every critical speed at least 15 % outside its range (no forward
critical speed in 850-3450 rpm), for any bearing stiffness 1e7-1e8 N/m (rolling bearings on pedestals; unknown, so a
band)? If not, what shaft diameter does? *Requirements:* REQ-G1 the separation margin above, over the whole bearing
band; REQ-G2 disc unbalance response at most 50 um (0-peak) over 1000-3000 rpm with API 684's unbalance
(U = 6350 W / N g mm) and bearing damping 500 N s/m (synthetic). *Model:* ROSS 3.1 (open source), Timoshenko shaft
elements, rigid disc, linear bearings; Campbell diagram, unbalance response. *Verification:* Jeffcott closed form
(massless shaft, rigid supports, central disc: sqrt(48 EI / (m L^3))); uniform pinned-pinned shaft against Euler-
Bernoulli (pi / L)^2 sqrt(EI / rho A); series bearing spring closed form; element-count convergence; gyroscopic
split of the second mode reported. *Hand estimate (before any run):* 50 mm: n1 2730-2930 rpm, inside the band: FAIL;
60 mm 3500-4010 rpm (passes only with stiff bearings); 65 mm 3840-4590 rpm. *Synthetic:* geometry, speed range, bearing
band, damping. Environment: ~/.venvs/ross (ROSS 3.1.0 from PyPI), outside the project lock, like Pyleecan.
(f) **Study F framing: APPROVED by the user 2026-11-23 ~16:05.** *Decision:* an S355 steel plate (100 mm wide, 10 mm
thick) with an edge crack, cyclic remote tension 150 MPa maximum at R = 0.1 (synthetic): how many cycles from a
detectable crack (2 mm, magnetic particle) to failure, and what inspection interval follows? *Material (published):*
crack growth by the BS 7910 / IIW simplified law for steels in air, da/dN = 5.21e-13 dK^3 (mm/cycle, N/mm^1.5),
threshold 63 N/mm^1.5; fracture toughness Kmat 100 MPa sqrt(m) (synthetic; a client would give CTOD or Charpy);
net-section yield 355 MPa. *Requirements:* REQ-F1 at the detectable crack, Kmax at most Kmat / 2 and the net section
below yield; REQ-F2 growth life from 2 mm to critical at least twice the inspection interval, interval recommended from
it. *Model:* CalculiX 2D plane strain, half model on the crack plane, collapsed quarter-point elements at the tip; K by
displacement extrapolation and by energy release (compliance at two crack lengths, K = sqrt(E' G)); Paris integration in
Python over the K(a) curve. *Verification:* Tada's finite-width edge-crack K (handbook, 0.5 % for a/W up to 0.6); the
two K routes agree; tip-mesh refinement; integration step convergence.
(0) **Study 19 part 2 framing: LIMITS AGREED by the user 2026-11-22 ~20:50 (REQ-S1 10 %, REQ-S2 15 % rms, REQ-S3 0.02; nothing built yet; next: the build plan below, in a fresh session).**
*Decision:* can the setup part 1 verified (k-omega SST, sublayer resolved, OpenFOAM 14) predict a separated,
reattaching flow well enough for design use: where the flow reattaches behind a sudden step, how much pressure it
recovers, and the wall shear downstream (e.g. placing a heat-transfer surface or a sensor in a duct with a step)?
*Case:* Driver & Seegmiller, ERCOFTAC 030, parallel walls (alpha 0): step H 12.7 mm, inlet duct height 8H (expansion
1.125), U 44.2 m/s, air (nu about 1.5e-5), Re_H about 37500, M 0.128 (incompressible). *Inflow (boundary condition,
from the case description, not the answer key):* step-side boundary layer delta 19 mm, Re_theta 5000 (theta about 1.7
mm) at x/H = -4. *Requirements (proposed; to be agreed BEFORE any measured data beyond the inflow is opened):*
REQ-S1 reattachment length Xr/H within 10 % of measured; REQ-S2 skin friction on the step-side wall over 10 <= x/H
<= 30 within 15 % of measured (rms); REQ-S3 pressure recovery, Cp on the step-side wall at x/H = 30 minus its value at
x/H = -4, within 0.02 absolute. Velocity and Reynolds-stress profiles reported, not required. *Prior knowledge
(declare):* measured Xr/H 6.26 +- 0.10 seen at download (above); SST's tendency on this case is also widely discussed;
the prediction band must come from our own mesh and inflow sensitivity, not from these. *Verification (before the
comparison):* inflow matched (theta and delta at x/H = -4 within 5 % of the stated values, by choosing the inlet's
upstream distance); mass balance; y+ under 1; mesh study (3 levels, GCI on Xr and Cf at x/H = 20); outlet length
(Xr unchanged within 0.5 % when the outlet moves from x/H 30 to 50); inlet turbulence intensity sensitivity; 2D
(span / H = 12, stated). *Build plan (fresh session; part 1's machinery):* `models/cfd/step_openfoam.py` (blockMesh,
graded blocks: inlet duct and step region, one cell thick, empty sides; low-Re walls; slip or wall on the top per the
experiment's tunnel wall), `models/cfd/run_step.sh` modelled on `run_pipe.sh`, `studies/step_flow.py` (Xr from the
Cf zero crossing located by interpolation, Cf and Cp along the wall, theta / delta at x/H = -4, profiles at the data
stations), tests, cases with predictions first. Run one solver process at a time under `nice -n 19` in WSL (the user's
machine is in use: avoid contention with FSI2/FSI3 and the user's own programs). Open `bkst-tauw.dat`, `bkst-cp.dat`,
`bkst-ldv-00.dat` only after the user agrees the limits and the predictions are committed.
(a) Study C framing, drafted for approval (nothing run): *Decision:* does the study-4 steel bracket arm (150 x 25 x 7
mm cantilever, first mode about 262 Hz, portfolio 04) survive a random-vibration qualification: 1 h per axis of a base
PSD, flat 0.04 g^2/Hz from 20 to 2000 Hz (about 8.9 g rms; synthetic), 2 % modal damping (synthetic)? *Requirements
(proposed):* REQ-RV1 3-sigma von Mises at the clamp (smooth-region extrapolated, not the corner singularity) below
yield / 1.5; REQ-RV2 fatigue damage (Steinberg three-band with Miner; Dirlik as a second estimate) below 0.5 for the
test; REQ-RV3 tip relative displacement 3-sigma under a stated clearance. *Model:* CalculiX *FREQUENCY, then base
excitation (*MODAL DYNAMIC or *STEADY STATE DYNAMICS); response PSD and moments in Python. *Checks:* Miles' equation for
the first mode, modal effective mass above 90 %, response rms by two integrations, mesh study on the 3-sigma stress.
*Questions:* PSD level (or a standard profile such as ISO 16750-3), damping, steel grade (yield, S-N curve), clearance.
(b) Proposed eval case for frame-requirements: "brackets the inputs that don't matter, leaves out the one that does"
(study 7's remanence); ask before adding. (c) The skill eval's no-skills baseline (not run).
(d) **Study H framing: APPROVED by the user 2026-11-23 ~10:00 ("ok yes please run these"); build in progress.**
*Decision:* study C passes on nominal inputs, its damage by a factor of about 200. Is that PASS robust to what a
project would not know exactly, and which input would be worth measuring first? *Uncertain inputs (all synthetic,
independent):* modal damping lognormal, median 2 %, 90 % between 1 % and 4 %; test level within a control tolerance,
uniform +-1.5 dB on the PSD; fatigue strength a factor on the EN 1993-1-9 detail category, lognormal, median 1.0 (the
design curve itself: conservative), CoV 10 %; plate thickness normal 7.0 mm, sd 0.1 mm (a +-0.3 mm drawing tolerance
read as 3 sd). *Outputs:* the probability of failing each of REQ-RV1-3 (Monte Carlo, Wilson interval; FORM with
importance sampling when no sample fails), Sobol first-order and total indices on log damage, 3 sigma stress and tip
displacement, and the damping at which each requirement would fail alone. *Requirement (proposed, synthetic):*
REQ-H1 probability of failing any of REQ-RV1-3 below 1e-3. *Method:* CalculiX modes at five thicknesses (the
study C mesh chosen from its mesh study); the spectral moments at each hot-spot point on a grid of damping and
thickness, interpolated (the surrogate); the test level scales the moments exactly; the S-N factor enters the damage
integral. *Checks:* `harness/uncertainty.py` against closed forms (committed f797064, 8 tests); the nominal sample
reproduces study C's evidence value on the same mesh; surrogate error at off-grid points under 1 %; FORM against
importance sampling; Sobol intervals under +-0.03. *Expected (declare):* a robust PASS; damping and the S-N factor
dominate the damage, because the stress sits near the S-N cut-off.

### Done this evening (17:15-19:25)
Thermal network (r1 final, cb6920c reports); FSI1 r1 scored (29e6655, page 9c41e8d); skill eval single-mesh-agreement-trap
8/8 (9031316); efficiency figure fixed (d69953b); blind comparison (0f58d8c, ebb75f7, artifact v6); frame-requirements
lessons from the miss (a180027); the realistic-information rule (95daee6); FSI2/FSI3 periodic statistics and cases
(f56581d, ea28835); calibration plan, hypothesis B, hypothesis A cases (31449ff .. 7664a06). Uncommitted: none of this
session's (docs/ and DASHBOARD.md changes belong to the dashboard session).
**For the dashboard session:** study 7 is no longer "blind, sealed": the comparison ran and failed 3/3 (flux 24 % high),
a calibrated revision is in progress; thermal page added; study 6 FSI1 within 1 % (drag and lift verified), FSI2/FSI3
running. Pages under `site/` / `docs/` showing study 7 or 6 status are stale.

### Work order (user, 2026-11-22 ~17:05: "keep working through all of this")

1. **Study 7 thermal network: DONE 2026-11-22 ~18:00** (state below, "Study 7"). Original plan, kept for reference:
   a lumped network built from the machine geometry (`models/motor/`, our ORNL machine): winding in slot, end winding,
   teeth, yoke, housing/jacket, air gap, rotor, magnets; losses per region from the efficiency study (copper from the
   phase resistance; stator and rotor iron from the dq tables' separate coefficients). Independent check: CalculiX 2D
   steady conduction on one slot-pitch stator section with the same losses and boundary conditions (the plan in the
   table at the top). Cooling is not in the design data we may read: state a synthetic jacket coolant temperature and
   h, mark them synthetic, and show how the answer scales with them. Decision to frame (propose to the user, don't
   assume): e.g. the continuous torque-speed envelope that keeps the winding under its insulation class limit, and
   whether the efficiency map's hot corner (windings 100 C, magnets 80 C) is a consistent operating state. Thermal
   is NOT in the agreed validation set; ORNL's thermal report pages 20-30 stay sealed (design text only, whitelist).
2. **FSI1 r1: DONE** (Results in the case; drift was scatter). Was: score, Results block, update `portfolio/17-...` draft (CLAUDE.md "Update the record").
   Early: 2.5 mm uy(A) -0.41 %, 1.77 mm +0.04 % (the drift may not be real). Then FSI2 / FSI3 (periodic; set up cases,
   predictions first; likely overnight runs).
3. **Study 7 blind comparison: DONE, FAIL 3/3** (above). Next: the Fig. 13 diagnostic, on the user's call.
4. **Next new study:** C, random vibration of the study-4 bracket (documented below).
5. **Small items:** (figure fix and eval DONE) the efficiency-map figure's contour-fill artefact at the map edge (`studies/motor_efficiency.py`
   `efficiency_figure`: use pcolormesh or mask, the data is fine); optionally run the new eval
   (`.claude/skills/verify-against-reference/evals/single-mesh-agreement-trap`) with the skill-eval-runner agent (ask:
   it costs a session); study 18 extras (classification-line placement, head-to-shell junction).
6. **Blocked:** study 19 part 2 (step data host certificate; the user may supply the files).

### Study 7 (motor): state and next steps

- **Blind predictions (cases, committed):** back-EMF **110.9 V rms line-to-line per 1000 rpm** at 20 C
  (`motor_prius_ornl_oc_mesh_r3`); MTPA torque **118.8 / 251.6 / 366.6 / 456.9 / 522.3 / 569.4 / 606.4 N m at 50-350 A
  rms** (`motor_prius_torque_current_r1`), 400 N m at about 168 A. Stand-in steel M330-35A.
- **Lamination bracket (done):** across M330-35A / M250-35A / 190Y390 the back-EMF spans 0.13 %, torque 1.8 % at 100 A
  and 1.0 % at 300 A: the unknown grade does not limit the comparison. REQ-M4 (overspeed, 424 MPa) by comparison: M250-35A
  passes on its typical yield, the other two fail.
- **B-H tail sensitivity (done, user's request):** saturation polarization 2.05 instead of 2.0 T: torque +1.75 / +1.96 %
  at 300 / 350 A, back-EMF -0.35 % (`*_js205` cases). The prediction stays on 2.0 T; this is its stated uncertainty.
- **Copper correction (2026-11-22 ~09:30, 5714743):** ORNL's 0.84 fill is on the squares of insulated wires; bare
  copper is 76.4 mm^2 per slot (13 x 0.912 mm strands per turn), not 120. **25 A/mm^2 = 212 A rms, not 333.** REQ-M2
  still PASS (400 N m at 168 A, 19.8 A/mm^2); REQ-M3 now fails from 250 A. Notes in the five torque case headers.
  (In `reports/motor/` since the 15:12 rebuild.)
- **User decisions today:** the 25 A/mm^2 limit stays as a stated assumption; efficiency = motor only, a cold/hot band
  (cold: all 20 C; hot: windings 100 C, magnets 80 C), mechanical losses left out and stated; bus 500 V.
- **Efficiency map, built:** `studies/motor_lut.py` (dq table per (id, iq): torque, dq flux, iron-loss coefficients A,
  B, C with P = A f + B f^2 + C f^1.5), `models/motor/efficiency_map.py` + `studies/motor_efficiency.py` (lowest-loss
  feasible current per speed and torque under the voltage limit Vdc / sqrt 6 and a current limit). Mesh study
  `motor_prius_lut_mesh` done: fineness 2 within 0.4 % of 8 (grids revised to 2, reason in the case).
- **Both 25 A tables done** (cold 2bf53fc, hot 590f42e, both PASS): hot open-circuit flux -7.0 % against Br -6 %;
  torque -5.1 to -5.4 % at id 0. **Efficiency map run** (`motor_prius_efficiency`, cfe0f58): cold peak 97.4 % at
  2500 rpm / 80 N m, hot 97.0 %; REQ-M5 PASS but unverified (58.6 / 53.7 kW, lowest at 6000 rpm). Verification FAIL
  on the half-grid checks, all on the iq 25 A row; diagnostic: below 30 N m at 4000-6000 rpm the optimum sits at iq
  2-5 A, inside the first 25 A cell, and the map moves up to 10 points; above 60 N m within about 1 point.
- **Efficiency r1 done (c9a8637):** low-iq tables merged (25 A rows bit-identical; their dq check fails at iq 6.25 A deep
  in field weakening, up to 1.1 %, model form). Cold verified, all 8 checks: REQ-M5 58.6 kW verified PASS, map resolved
  to 0.9 point; hot fails the map check in one cell (4500 rpm, 10 N m), REQ-M5 53.7 kW PASS unverified. Peaks 97.41 /
  97.05 %. The 10 N m row above 4000 rpm stays unresolved (stated; not worth a revision before the blind comparison).
- **Reports rebuilt and republished** (b770fee, artifact version 4: https://claude.ai/artifact/C6dNdzjs1FdP8vVb6MLaRy).
- **Thermal network done** (user's framing 2026-11-22 ~17:20: envelope + hot-corner check; class H 180 C hotspot and
  150 C magnets, synthetic; water jacket 65 C, h 3000, synthetic). Cases `motor_prius_thermal` (run 174048, Results)
  and `motor_prius_thermal_r1` (run 174925, final; commits 1040954 .. f48f01f). Answer: about 230 N m continuous to 2000
  rpm, 42-48 kW from 2500 to 6000 rpm; the **magnets bind at every speed** (rotor floats at the tooth-tip temperature:
  no shaft path, gap conduction only); REQ-TH1 (>= 25 kW from 1250 rpm, our synthetic limit) 30.2 kW, 26.2-34.3 kW over
  ten scenarios. Hot corner: at winding mean 100 C the magnets are 93-105 C (the map's 80 C is optimistic by 13-25 K).
  Verification: CalculiX slot-pitch check passes mean / teeth / yoke (bar interface 0.01 mm: mean -6.4 %); the slot
  hotspot is 4-7 % low on its rise after r1's top-of-slot estimate (FAIL in six scenarios by 0.1-2.2 points); a bound in
  r1's header shows it cannot move the envelope from 1250 rpm. Not revised further (needs a 2D slot model). Portfolio
  page 20, PORTFOLIO, README and skills updated; `reports/motor/` has a thermal page (cb6920c).
- **Blind comparison done (19:00): FAIL 3/3**; see the top of this handoff. Next: the Fig. 13 diagnostic (ask first).

### Study 6 (FSI): FSI2 / FSI3 set-up (started 2026-11-22 ~19:20)

Benchmark source (featflow.de fails TLS at the server; TU Dortmund's mirror works with normal certificate checks):
https://wwwold.mathematik.tu-dortmund.de/~featflow/en/benchmarks/cfdbenchmarking/fsi_benchmark/fsi_tests/fsi_fsi_tests.html
(tables), `.../fsi_quantities.html` (definitions), `.../fsi_reference.html` (time series `media/fsi/data/fsi2/0p0005/
ref_fsi2.point`, `fsi3/0p00025/ref_fsi3.point`; columns 1 time, 5+7 drag, 6+8 lift, 11 ux(A), 12 uy(A)). The FSI1 row
there matches our case's values exactly.
- Parameters: FSI2 rho_s 10e3 kg/m^3, nu_s 0.4, mu_s 0.5e6 Pa, U 1 m/s (Re 100); FSI3 rho_s 1e3, mu_s 2.0e6, U 2 (Re 200);
  fluid 1e3 kg/m^3, nu 1e-3 m^2/s.
- Reference (level 4+0, finest dt): FSI2 (dt 0.0005) ux -1.485e-2 +- 1.270e-2 m [3.86 Hz], uy 1.30e-3 +- 8.16e-2 m
  [1.93], drag 2.1506e2 +- 7.765e1 N/m [3.86], lift 6.1e-1 +- 2.378e2 [1.93]. FSI3 (dt 0.00025) ux -2.88e-3 +- 2.72e-3
  [10.93], uy 1.47e-3 +- 3.499e-2 [5.46], drag 4.605e2 +- 2.774e1 [10.93], lift 2.50 +- 1.5391e2 [5.46]. Across the
  page's levels 2-4 and time steps the FSI2 uy amplitude spans 7.9-8.2e-2 and drag 201-215 N/m: a few % of scatter.
- Definition (fsi_quantities): over the last period, mean = (max + min) / 2, amplitude = (max - min) / 2; frequency =
  1 / period or the lowest significant FFT peak. Forces on cylinder + flag (as FSI1).
- Plan: opt-in periodic metrics in `studies/turek_hron_fsi.py` (mean, amplitude, frequency over the last whole periods
  of uy; a periodic-steadiness check comparing the last two periods' amplitudes); case `turek_hron_fsi2` (2.5 mm fluid,
  dt 0.001, about 15-20 s) with predictions first; then FSI3 (dt 0.0005 or finer; added mass is hardest at beta 1).

### Study 6 (FSI): FSI1 revision 1

- Code (f61cc9f): opt-in `numerics.metric_average_s` (window-mean metrics and force transfer) and
  `verification.steady_measure = "drift"`.
- Prototype A (5 mm fluid, coupling tolerance 1e-6): lift jitter 72 x smaller, means unchanged to 5 digits, iterations
  +19 %, every point check passes. The jitter was zero-mean coupling noise.
- Prototype B (solid 1.25 mm at the 2.5 mm fluid mesh): uy(A) +0.035 % against the 2.5 mm solid, about 1/16 of the
  drift; cost 3 h 45 min against 51 min. The solid mesh does not explain the drift; it stays at 2.5 mm.
- **FSI1 r1 running** (8ddf816): fluid 2.5 / 1.77 / 1.25 mm (the 5 mm mesh was outside the asymptotic range). Still
  unexplained: uy(A) moving away from the benchmark; candidates the fluid mesh motion near the tip and the RBF force
  mapping (bending moment not checked). Then FSI2 and FSI3 (periodic).
  The portfolio page `portfolio/17-fsi-flag-turek-hron.md` stays a draft until study 6 is complete.

### Study 18 (pressure vessel with a nozzle): two cases done

- `pv_nozzle_mesh` (5feb663): PL 205.1 MPa, GCI 0.03 %, REQ-PV2 verified PASS by 0.9 %; Pm exact to 0.03 %; equilibrium
  exact. `pv_nozzle_thickness` (17fc040): by analysis the nozzle needs about 11.7 mm, by the simplified pressure-area
  rule about 16 mm; recommendation for review 14 mm.
- Placement sensitivity and the head-to-shell junction: done 20:30 (see the top of the handoff).

### Study 19 (turbulent flow)

- Part 1, pipe friction (2f076cf). Mesh study done (b18fada), verification FAIL: f 0.01730 / 0.01783 / 0.01813 on
  n 40 / 80 / 160, observed order 0.84, GCI 2.6 % (tolerance 1 %), extrapolated +2.8 % on Prandtl. REQ-T1 PASS but
  unverified. The smoke test's -0.9 % was the n80 mesh's error. Reynolds sweep done (587dadd): low_re within 2 % of
  Prandtl at Re 2e4-2e6 (on those under-resolved meshes); wall functions -5.2 % at every Re (REQ-T1 FAIL); Re 2e6
  flagged by checkMesh on aspect ratio (the axial length floor D/50 in `grading()`). `pipe_rans_mesh_r1` (3b5c91b): n320 never converged; cause the
  geometric-mean axial length (it stalls SIMPLE; the n640 probe used it too). r2 (dd29fbb): all converged, f 0.017834 / 0.018130 / 0.018280,
  first order, extrapolated +2.4 % on Prandtl, GCI 1.05 % (run-level fails by 0.05 point). **Part 1 done; page
  `portfolio/19-turbulent-pipe-friction.md` (6454d5e).** Optional: n640 with a 1 mm axial length (aspect ratio 760). Axial-length option d5e385a. Wall functions done (877b7b3): at Re 2e6 the core
  mesh does not matter (GCI 0.024 %) and the first-cell placement moves f only from -5.23 to -4.75 % (y+ 29-196): the
  -5 % is the wall treatment; REQ-T1 fails or passes by under 0.25 point. Low-Re is the usable setup.
- Part 2, the backward-facing step against Driver & Seegmiller's measurements: **waiting on data.** On 2026-11-22
  ~10:20 turbmodels.larc.nasa.gov had a TLS certificate fault and the ERCOFTAC classic database
  (cfd.mace.manchester.ac.uk) refused connections; the KB wiki (UFR 3-15) gives only secondary values (Re_H 37500,
  expansion 1.125, inflow BL at x/H = -4: delta 19 mm, theta 1.9 mm). Retried 2026-11-22 ~16:05:
  turbmodels.larc.nasa.gov still serves a certificate for other larc.nasa.gov names (hostname mismatch). Retry the
  hosts, or ask the user for the data files; never fill values from memory; never bypass a certificate error.

### Documented, not started (user, 2026-11-22: "work on the agreed ones, document the rest")

From the portfolio gap review (gaps not covered anywhere: design codes beyond VDI 2230, turbulence and measured-data
validation, forced and transient dynamics, natural convection and radiation, hyperelastic large strain, fracture, machine
elements, probabilistic uncertainty). Each with its tools and independent references:

- **C. Random vibration of the study-4 bracket.** Base-excitation PSD (synthetic, e.g. a flat 0.04 g^2/Hz from 20 to
  2000 Hz) through modal superposition (CalculiX *FREQUENCY + *STEADY STATE DYNAMICS for the transfer functions, or
  Python from the modes); response PSD, 1-sigma and 3-sigma stress, fatigue by Steinberg's three-band method or Dirlik.
  References: Miles' equation (exact for a single mode), modal effective mass sum above 90 %, an RMS-integration check.
- **D. Natural convection and radiation.** Differentially heated square cavity against the de Vahl Davis (1983)
  benchmark (Nusselt numbers at Ra 1e3-1e6; fetch the values, do not quote from memory), OpenFOAM buoyant solver;
  enclosure radiation with view factors in CalculiX (*RADIATE, cavity radiation) against two-surface exchange (parallel
  plates, concentric cylinders); then the combination on an electronics enclosure.
- **E. O-ring compression.** Hyperelastic (Neo-Hookean / Mooney-Rivlin, CalculiX *HYPERELASTIC), axisymmetric ring
  squeezed between plates with contact and self-contact; force against squeeze from a published correlation (source to
  fetch); checks: near-incompressibility (J about 1), contact pressure integral against the reaction, mesh convergence.
  **Framing DRAFT for study 12 (2026-11-24 07:59; started on the user's word "start study 12"; APPROVED by the user
  2026-11-24, after 08:25 ("this study 12 framework sounds good to me, please proceed"), as drafted):**
  - Decision: a static face-seal O-ring in a cover's groove (synthetic client: an aluminium coolant-pump cover, water-
    glycol at up to 3 bar, NBR 70 Shore A, cross-section 3.53 mm, a 50 mm class ring). Across the stack of tolerances
    (cross-section +-0.10 mm, groove depth +-0.05 mm, hardness +-5 Shore A), does the seal (a) keep enough contact
    pressure at the loosest stack to seal, (b) need no more closing force at the tightest stack than the cover's bolts
    supply, (c) fit its groove (fill), (d) stay within the squeeze the elastomer tolerates?
  - Requirements (all synthetic, to approve): REQ-E1 squeeze 15-30 % over the stack (hand calculation, checked by FE
    geometry); REQ-E2 peak contact pressure at the loosest stack >= 2 x the 0.3 MPa sealed pressure; REQ-E3 closing
    force at the tightest stack (hardest compound) <= 12 N per mm of seal length (bolt budget); REQ-E4 groove fill
    <= 85 % (deformed area / groove area).
  - Model: CalculiX, axisymmetric (CAX), Mooney-Rivlin or neo-Hookean, near-incompressible, rigid plates and groove
    walls by penalty contact, squeeze applied by displacement; a plane-strain twin as a cross-check.
  - Independent checks: Lindley's force-compression relation (J. Inst. Rubber Ind. 1967; seen via El Bahloul et al.
    2022, Int. J. Fluid Power 23(2), whose text extraction garbles it: F = pi D d E (1.25 c^1.5 + 50 c^6); confirm the
    exponents from a second source before use); Hertz line contact (incompressible, E* = 4E/3) as the exact small-
    squeeze limit (2-5 %); volume ratio J about 1; the contact-pressure integral against the reaction; GCI on force
    and peak pressure. Material: E from Shore A by a published relation (Gent; fetch, do not quote) and its
    tolerance; a published NBR Mooney-Rivlin pair as a second material form.
  - Effort: about half a day to build and verify; runs are minutes each.
  - Sources found 2026-11-24 08:30 (no values used yet): Parker O-Ring Handbook ORD 5700 sec. 2.4.6 publishes
    measured compression-load charts per inch of seal by cross-section (0.139 in = 3.53 mm among them), squeeze and
    hardness (70 / 90 Shore A; 50 / 60 / 80 in the full handbook): a measured force-squeeze reference for exactly
    this ring (read off the chart with its reading uncertainty). Gent, "On the Relation between Indentation Hardness
    and Young's Modulus", Rubber Chem. Technol. 31(4) 896-906, 1958 (doi 10.5254/1.3542351): the Shore A to E relation;
    the versions in circulation differ in their coefficients (7.62336 / 0.137505 with a kgf/cm^2 factor, or 7.66 /
    0.1375 in MPa), so take it from the original. Lindley's exponents still need a second source.
- **F. Fracture.** Edge- or centre-cracked plate, stress intensity factor from the energy release rate (two runs with
  a small crack extension, G = -dPi/da, K = sqrt(E' G)) and from crack-opening displacement near the tip; against the
  handbook solutions (Tada, Paris and Irwin); then Paris-law crack-growth life by integration.
- **G. Rotordynamics with ROSS** (open-source Python package `ross-rotordynamics`): critical speeds, Campbell diagram,
  unbalance response; verified on the Jeffcott rotor's closed form; applied to the Prius rotor on its shaft (first
  critical speed against the 6000 rpm maximum).
- **H. Probabilistic uncertainty.** Latin hypercube or Monte Carlo with a surrogate and Sobol indices on an existing
  study (the coolant channel or the cantilever); reliability index and failure probability against a requirement.
- Also noted: transient conduction (exact series for a slab or cylinder), machine elements (a gear tooth by ISO 6336 or
  AGMA against FE contact; shaft fatigue by DIN 743).

### For the dashboard session (from the study session)

- 2026-11-23 12:40, ready to show (all committed):
  - **New page** `portfolio/21-bracket-random-vibration.md` (study C, random vibration of the study-4 bracket: PASS on
    stress, fatigue and tip clearance, verified); figure in its run. PORTFOLIO.md has its row and two capability rows
    (vibration, fatigue) now cite it.
  - **Page 19 part 2** (the backward-facing step against Driver and Seegmiller): two of three limits pass; comparison
    figure `validation/step_driver_seegmiller/comparison.png`. PORTFOLIO row 19 extended. Study 19 is complete.
  - **Page 20** (Prius motor): REQ-M1 recomputed on the calibrated machine (856 V, ORNL 850 V), efficiency revisions 2-3,
    the current diagnostic, and revision 4 in progress (the magnet as drawn explains most of the blind miss without
    calibration). PORTFOLIO row 20 updated. The motor report artifact (`reports/motor/`) is NOT yet refreshed; wait.
  - Not ready yet: study H (uncertainty, ~16:30), page 17 (FSI1 r2 ~13:30, FSI2 mesh study tomorrow).
- 2026-11-23 ~10:10: the pipe-friction figure's mesh panel labels the extrapolated value "converged: +2.4 %"; the
  user read it as a claim that the meshes had stopped changing (they still move linearly in 1/N). Suggest "extrapolated
  to zero cell size: +2.4 % +- 0.5 %". Page 19 now says so (study session).
- 2026-11-22 ~16:00: new portfolio pages `portfolio/18-pressure-vessel-nozzle.md` (complete), `portfolio/20-prius-traction-motor.md`
  and `portfolio/17-fsi-flag-turek-hron.md` (drafts, now in PORTFOLIO.md); `portfolio/19-turbulent-pipe-friction.md` (part 1
  complete, with `portfolio/img/pipe_friction.png`); new task `tasks/nozzle_stress_linearisation`.
  PORTFOLIO.md no longer states a study count. The site's study list and counts may be stale.

### Waiting on the user

Nothing blocking. For review when convenient: study 18's answer (placement-dependent: about 20 mm with the crotch line; 14 mm withdrawn). (User, 2026-11-22 ~15:00: "keep working
on our studies, updating docs and skills and building out the portfolio": study 18's page is published (0feac56); study
19's page is published (6454d5e). New evaluation task
`tasks/nozzle_stress_linearisation` (ea159d0). Skills updated (6eadf71). README study table (4d484d3). Next ideas: a
skill eval on quoting one mesh's agreement with a correlation (after pipe r1), FSI page when r1 is in.)

### Earlier notes (history: the summary above supersedes anything here that disagrees)

**Study 6 (FSI) status.**
- **CSM1, CSM2:** verified and committed (e72d395).
- **CFD1:**
  - drag verified on run `20261121-140657_turek_hron_cfd1_mesh_r1`;
  - lift verified on run `20261121-140245_turek_hron_cfd1_mesh` but "divergent" on r1, because Gmsh's
    regenerated meshes carry about ±0.6 % mesh-to-mesh noise.
  - **CFD2 is done** (run `20261121-151947_turek_hron_cfd2_mesh`): drag verified (extrapolated 136.719,
    0.014 % from the benchmark); lift withheld on the same mesh noise (uncertainty 1.65 %).
  - Next revision, for CFD1 and CFD2 both: nested structured meshes round the body, or measure that
    noise at a fixed size and declare it before the rerun.
  - Hold it until the CPU is free.
- **CSM3: closed** (run `20261121-184353_flag_csm3_dt_r3`: frequency and ux verified; uy mean and amplitude inside the band but formally withheld at the 0.05 % level). The first run is kept as evidence of the trapezoidal-rule energy drift and of the mode-2
  measurement flaw (fixed: mid-level crossings).
- **Coupled stage, toolchain ready (2026-11-21).** The user installed OpenFOAM v2512, preCICE 3.4.1 and
  `ccx_preCICE`. The OpenFOAM adapter v1.4.0 is built (`~/precice-adapters`). preCICE's `perpendicular-flap`
  tutorial (OpenFOAM + CalculiX, tutorials develop branch in `~/precice-tutorials`) matched its reference
  flap-tip history: peak equal to 5 digits, largest difference 0.7 % of the peak. Next:
  - FSI1 (steady), then FSI2 and FSI3 (periodic, need a transient fluid solver: pimpleFoam).
- **FSI1 revision 1 under way (2026-11-22).** Code: opt-in window-mean metrics and drift-based steadiness (f61cc9f).
  Scratch prototype A (5 mm fluid mesh, coupling tolerance 1e-6, run `20261122-091120_scratch_fsi1_tol1e6`, not
  committed): lift jitter 1.70e-2 -> 2.36e-4 peak to peak (72 x less), means unchanged to 5 digits (lift 0.74231,
  uy(A) 0.868557 mm, drag 14.2656), coupling iterations 2.94 -> 3.49, every point check passes (steady by drift 1.1e-4,
  force transfer 5.6e-5 averaged). So the jitter was zero-mean coupling noise from the 1e-4 tolerance. Prototype B
  (solid 1.25 mm at the 2.5 mm fluid mesh, tolerance 1e-4) still running (about 4 h, slower than expected): tests the
  uy(A) drift. Then write `turek_hron_fsi1_mesh_r1` (tolerance 1e-6, means, drift; solid mesh as B decides) with
  predictions, and run it.
- The portfolio page is a draft, not linked from PORTFOLIO.md until study 6 is complete.

**Study 7 (motor), feasibility.** See its row in the table above. The Pyleecan environment is at
`~/.venvs/pyleecan`, pinned in `models/motor/pyleecan-env.txt` (recreate steps in its header).

FEMM 4.2 is installed and scriptable (see the study 7 row).

**Study 7 (motor) plan, agreed 2026-11-21, not started.** Build and verify everything ourselves;
the ORNL report is the last step, opened blind.
1. **Design inputs.** Use Pyleecan's Prius model (geometry, winding, magnet and lamination data).
   Spot-check a few key dimensions against a published source, so that the model is really the 2004
   Prius.
2. **Our model and internal checks.** These are independent of ORNL:
   - FEMM electromagnetics: torque, back-EMF, flux-linkage and efficiency maps;
   - a thermal network checked against CalculiX on a stator section;
   - rotor stress at overspeed;
   - checks: an analytic air-gap field, the power balance at every operating point, mesh convergence,
     and FEMM against a second calculation route.
3. **Blind validation.** Write predictions into the case file first: the back-EMF constant, torque at a
   few currents, efficiency at some operating points. Only then fetch ORNL's measured values and
   compare. This is the portfolio's first comparison with test data. Expect 5 to 10 % from material
   and temperature uncertainty, and explain the gap rather than tune it away.

**Study 7 framing, agreed with the user 2026-11-21 (started that evening).**
- **Decision:** can an open-source toolchain (Pyleecan + FEMM electromagnetics, CalculiX rotor stress, and later a
  thermal network checked against CalculiX) predict a production traction motor's key characteristics well enough
  for early design screening? Tested on the 2004 Prius against ORNL's measured data.
- **Design checks**, answered by our models with internal verification only: rated peak torque within the current
  limit; rotor bridge stress at overspeed under the lamination's yield.
- **Validation limits**, agreed with the user:
  - back-EMF constant within 5 %;
  - peak torque at several currents within 10 %;
  - efficiency at sample points within 2 percentage points.

  The user wants to keep an eye on these and may tune them later. They may change only **before** the ORNL data is
  opened, with a written reason. After that, any change is a documented revision with the earlier verdict kept,
  or the blind comparison means nothing.
- **Scope:** electromagnetics and rotor stress first; the thermal network second (the biggest build, with no
  open-source tool to lean on).
- The Pyleecan environment is durable now, at `~/.venvs/pyleecan` (in the user home folder) (master, pyFEMM, pywin32).

**Study 7 progress (2026-11-21 evening).**
- **Design-input spot check against ORNL's design report** (ORNL/TM-2004/137, Hsu, Ayers, Coomer, July 2004;
  https://info.ornl.gov/sites/publications/Files/Pub57348.pdf). Design content only; no performance data was opened.
  - Confirmed: the 3.3 in (83.82 mm) stack, an exact match with Pyleecan's L1; the series winding on the 2004
    model (200 to 500 V boosted bus); ratings 50 kW and 400 N m up to base speed.
  - Also from the report: 0.014 in (0.36 mm) laminations, slot fill 0.84, end winding 1.5 in per side.
  - Not yet confirmed: the diameters and the air gap, which are in the report's figures, not its text.
  - The two ORNL test reports (ORNL/TM-2006/423, ORNL/TM-2004/247 rev.) contain no dimensions in their text; only
    filtered design-term searches were run on them, so the blind comparison is intact.
- **Assumptions to state:**
  - Pyleecan's lamination grade is M400-50A, a 0.5 mm grade, not the actual 0.36 mm steel. That matters for
    iron loss and efficiency.
  - Its magnet is a generic NdFeB (Br 1.24 T at 20 C, recoil permeability 1.05).
- **Toolchain:** SciDataTool 2.5.0 (PyPI) uses numpy.string_, which numpy 2 removed. Install SciDataTool from GitHub
  master (2.5.1, Feb 2026, commit c6f2497) in the Pyleecan environment. Pyleecan is pinned at master 1e940df.
- **First FEMM solve through Pyleecan** (open circuit, 1000 rpm, 24 rotor positions, default mesh, 2.3 s): phase
  flux-linkage peak 0.2087 Wb, the same in all three phases; cogging torque mean 0.07 N m.
- **Blind prediction, written before any ORNL performance data was opened:** back-EMF of about 107 V line-to-line
  rms per 1000 rpm, from lambda_peak x omega_e at 4 pole pairs. This comes from the smoke solve; mesh and
  time-resolution checks are still to come.

**Study 7: geometry rebuild, agreed with the user 2026-11-21.** Build the Prius machine definition ourselves from
published dimensions, and compare it with Pyleecan's Toyota_Prius.json before trusting it as the design input. That
covers stator OD and bore, slot shape, rotor OD and ID, V-magnet pockets and magnet size, air gap, stack, winding.
- Compare dimension by dimension.
- Then run both machines through the same open-circuit case: the back-EMF difference shows how much any mismatch
  matters.
- If they disagree, the published source wins and the deviation is recorded.
- Source the dimensions from published design data only (ORNL design and teardown reports, papers), never from
  measured performance.
- The user wants the inputs, not only the solve, to be ours, with the case study used only to check the results.

**Study 7 geometry rebuild: first source found (2026-11-21).** ORNL/TM-2005/33, *Report on Toyota Prius Motor Thermal
Management* (FY 2005), https://info.ornl.gov/sites/publications/Files/Pub57487.pdf. Fig. 21 on page 32 is a dimensioned
stator and rotor schematic. Its labels are vector text: render the page with PyMuPDF and read them with
`page.get_text()`. Pages 20-30 hold test data, so stay out of them to keep the comparison blind.

| Feature | Drawing | mm | Pyleecan's file |
|---|---|---|---|
| Stator OD | 10.600 in | 269.24 | 269.24 |
| Stator bore | 6.375 in | 161.93 | 161.90 |
| Rotor OD | 6.314 in | 160.38 | 160.40 |
| Rotor ID | 4.356 in | 110.64 | 110.64 |
| Air gap | | 0.775 | **0.750 (3 % narrower)** |
| Slot opening | 0.076 in | 1.93 | 1.93 |
| Tooth tip height | 0.040 in | 1.02 | 1.00 |
| Slot depth | 1.320 in | 33.53 | H0 + H2 = 34.3? (check SlotW11's convention) |

Also on the drawing: slot-bottom feature 0.222 in, a width of 0.124 in, red 0.060 in and 0.056 in (likely the rotor
bridges), and the stator's bolt ears. The magnet pockets are simplified in that model, so they still need a source.
The thermal report's text gives 9 conductor bundles per slot (matches 9 turns per coil). Next: build our machine with
the drawing's values (air gap 0.775 mm) and run both through the open-circuit case to measure what the differences
change.

**Study 7: air-gap sensitivity and updated blind prediction (2026-11-21, 21:45, before any ORNL performance data is
opened).** (Superseded the same evening: see "Study 7: our machine definition" below.) Open circuit, 1000 rpm, mesh fineness 4, 48 steps per electrical period, scratch run:
| Machine | Air gap | Back-EMF |
|---|---|---|
| Pyleecan file | 0.750 mm | 107.035 V rms LL per 1000 rpm |
| Same machine with the ORNL Fig. 21 radii (stator bore 6.375 in, rotor OD 6.314 in, rotor ID 4.356 in, stator OD 10.600 in), slot opening 0.076 in, tooth tip 0.040 in | 0.7747 mm | 106.591 V (-0.41 %) |

**Updated blind prediction:** 106.6 V rms line-to-line per 1000 rpm at 20 C, from the rebuilt radii. Mesh uncertainty
about 0.02 % (from the fineness 2/4/8 study on Pyleecan's machine). The magnet pockets are still Pyleecan's: ORNL's
Fig. 21 simplifies them, so they need another published source before the rebuild is complete. Next session: turn the
rebuild into a committed machine definition (a script that applies the ORNL dimensions to Pyleecan's file, with
provenance), run it through `motor_prius_oc_mesh`, then do the torque-vs-current case.

**Study 7: our machine definition, verified (2026-11-21, 22:03).** Fig. 21 read in full: Pyleecan's stator SLOT is
wrong, not only the air gap. Drawing: 3.15 mm wide at the shoulder, round end 5.64 mm diameter, depth 33.53 mm, slot
area 145 mm^2; Pyleecan's file: 5.0 / 8.0 / 34.29 mm, 218 mm^2 (teeth at the bore 7.4 against 5.6 mm). The inset and the
main view's vector outline agree; the mapping onto SlotW11 (W1 at the shoulder, R1 = W2/2, H2 = 1.320 - 0.040 in) is
in `models/motor/build_prius_ornl.py`, which writes `models/motor/Toyota_Prius_ORNL.json`. The backend copies that file
into each run's inputs (hashed); a case selects it with `machine = "Toyota_Prius_ORNL.json"`. Overlay figure:
`portfolio/img/motor_slot_vs_ornl_fig21.png`. Run `20261121-215053_motor_prius_ornl_oc_mesh`: verification PASS,
back-EMF 108.04 V per 1000 rpm (+1.4 % on the radii-only machine, under the predicted 2-6 %), peak at 6000 rpm 1004 V
(down: narrower slots cut the harmonics), REQ-M1 verified fail. **Blind prediction now 108.0 V rms LL per 1000 rpm at
20 C, mesh uncertainty 0.12 %.** Details and the scored predictions are in the case header.
- **HTML reports for study 7**, apart from the dashboard: `reports/motor/` (index, geometry, open-circuit), generated by
  `reports/motor/build_report.py` from the cases and runs; rerun it after each new motor run. Published privately as an
  artifact: https://claude.ai/artifact/C6dNdzjs1FdP8vVb6MLaRy (republish from a session with the generator's
  `[artifact-index-path]` argument, which writes the main page without a document skeleton).
- **Decision (user, 2026-11-21 22:15): the ORNL data stays sealed until study 7 is complete**, then every quantity is
  compared at once. No one-quantity-at-a-time unsealing.

**Study 7: magnet pockets and magnets, sources found (2026-11-21, late evening).**
- **Fig. 21 (ORNL/TM-2005/33) draws the V pockets as vector outlines**: each of the 8 bent pockets is one pole's V (two
  magnet seats separated by stop notches, no steel at the apex; elbows at 22.5 + n x 45 deg). Measured on all 8 poles
  with the bore-fit scale: arm angle to tangential 17.4 deg (sd 0.3; Pyleecan HoleM50 17.46), outer apex 10.83 mm
  below the rotor OD (Pyleecan H0 10.96), pocket thickness 6.78 mm (sd 0.05; Pyleecan H3 6.50). So the V geometry
  matches; the pocket is 4 % thicker.
- **ORNL/TM-2004/120** (*PM Motor Parametric Design Analyses*, July 2004, https://info.ornl.gov/sites/publications/Files/Pub57320.pdf),
  Table 5.3 and Fig. 5.2 (PDF page 41), "baseline IPM machine" (the Prius; rotor radius 80.19 mm matches Fig. 21):
  magnet width MagWid 38.48 mm for the PAIR (the sketch labels one magnet MagWid/2, so 19.24 mm each; Pyleecan
  18.9), magnet thickness LM 5.31 mm (Pyleecan 6.5), bridge 1.45 mm (Fig. 21's red 0.056 in = 1.42 mm; Pyleecan
  H1 1.5), stack 83.57 mm, Br 1.12 T in its Table 5.4 (Pyleecan 1.24). It also gives Rad2 (radial distance to the end
  of the slot) 116.5 mm, which DISAGREES with Fig. 21 (bore + 1.320 in = 114.5 mm) and Pyleecan (115.2 mm): kept
  Fig. 21 (a dimensioned drawing whose inset and outline agree); recorded as a conflict.
- **Blind-protocol incident, recorded in full:** reading TM-2004/120 locally, a line filter that withheld lines with
  performance words still let through some table values from its Tables 5.4-5.5, whose labels are abbreviations
  (e.g. RelTorq, Pmech, Eff, IWpk, IWrms) or sit on separate lines. These are ORNL's lumped-parameter MODEL results
  for their baseline, not measured data; the validation compares against ORNL's measured data (TM-2004/247,
  TM-2006/423), which remains unopened. They do not change any prediction already written (back-EMF). For the
  torque and efficiency predictions still to come, this is a possible anchor: state it in those cases' headers.
  Lesson: extract by whitelist (geometry words, numbers masked unless wanted), never by blacklist.
- **Off limits until the study is complete:** ORNL/TM-2004/137 (the design report) Fig. 13 is the MEASURED no-load
  air-gap flux density (2003 against 2004), a back-EMF proxy. Its Fig. 14 is ORNL's measured comparison of a Prius
  magnet sample with other magnets: a material property (would give Br), not motor performance, but ORNL-measured.
- **Scratch sensitivity** (open circuit, fineness 4, one change at a time on the stator-rebuilt machine, 108.09 V):
  pocket/magnet 6.78 mm +0.42 %; magnet 5.31 mm -2.38 %; magnet 19.24 mm wide +2.01 %; **Br 1.12 T -11.3 %**.
- **Decision (user, 2026-11-21 ~22:30): open Fig. 14 only, as the source of the magnet material.** Rendered alone
  (page 12, image block y 447-679; Fig. 13 sits above y 367 and stayed out of the crop). Digitized from 906 pixels of
  ORNL's fitted line for the "Toyota/Prius Perm. Magnet": Br 1.243 T (extrapolated to H = 0; the measured points span
  -7.2 to -4.7 kOe), recoil permeability 1.129, Hcb -876 kA/m. Pyleecan's generic 1.24 T was right; its 1.05 was not.
  TM-2004/120's 1.12 T matches 1.24 T at about 120 C with alpha_Br -0.1 %/K, so it is probably a hot value.
- **Fig. 21 is stretched 1.1 % in x in the PDF** (the rotor OD outline is an ellipse, x/y 1.0114). Corrected, the
  pocket is 6.80 mm thick (sd 0.03), its inner edge matches Pyleecan's and its outer apex is 0.31 mm nearer the air
  gap (10.65 against 10.96 mm). Machine: H0 10.65, H3 6.80, W0 41.21 mm (keeps the 17.4 deg arm), bridge 1.45 mm,
  Br 1.243 T, mu_r 1.129. Overlay: `portfolio/img/motor_pocket_vs_ornl_fig21.png`. The stator measurements used the
  isotropic bore fit; their adopted values come from the drawing's labels, so the stretch does not change them.
- **Privacy:** the committed machine file (e060598) and its run input carried absolute material paths from Pyleecan's authors' computer
  material paths (upstream metadata, not ours); the build script now keeps file names only. Scrub
  `runs/20261121-215053_motor_prius_ornl_oc_mesh/inputs/Toyota_Prius_ORNL.json` before the next commit.
- **Torque against current (new study `motor_torque`, model `pyleecan_femm_load`):** the runner sweeps the current
  angle per point; checks are power balance (mean sum i dphi/dt = mean torque x omega_m, with Pyleecan's flux-linkage
  sign, which is opposite to the motor convention), current amplitude (Pyleecan's dq currents are RMS), phase symmetry,
  MTPA bracketed. Design limit assumed: 25 A/mm^2 rms copper current density = 333 A rms (stated in the cases; the
  user may change it). Prototype: 242 / 453 / 605 N m at 100 / 200 / 333 A rms.
- **Runs queued tonight, in order:** `motor_prius_ornl_oc_mesh_r1` (the intermediate machine, H3 grown inward),
  `motor_prius_torque_mesh` (333 A, fineness 2/4/8), `motor_prius_torque_current` (50-350 A), then
  `motor_prius_ornl_oc_mesh_r2` (final machine; its back-EMF becomes the blind prediction). Each case header holds
  predictions written before its run; fill in the Results blocks, update `reports/motor/` and commit.

**Study 7 status (2026-11-22, 04:45), one place.**

| Piece | State | Result / next |
|---|---|---|
| Design inputs: stator, rotor, slot, pocket | done | ORNL Fig. 21 (stretch corrected); bridge from TM-2004/120; magnet B-H from TM-2004/137 Fig. 14 |
| Open circuit (back-EMF, REQ-M1) | done on the final machine (r3, M330-35A) | **110.88 V per 1000 rpm, the blind prediction** (r2 on M400-50A: 109.70 V); REQ-M1 fails at 1040 V against the 500 V bus (verified on earlier runs; withheld on r2/r3 on the peak's GCI only) |
| Torque mesh study, 333 A (REQ-M2) | run, GCI withheld | 608 N m at 46.7 deg, spread 0.055 %, divergent classification: REQ-M2 pass (unverified), margin 52 %. Revision: measure the mesh noise, declare it, rerun |
| Torque curve 50-350 A | done on both steels | **M330-35A (r1): 118.8-606.4 N m, the blind prediction**, 400 N m at about 168 A; M400-50A: 115.4-621.8 N m. REQ-M3 fails at 350 A only |
| Rotor overspeed (REQ-M4) | verified | 424 MPa linearized vs 335 at 7200 rpm: FAIL (295 MPa at 6000 rpm: elastic in service) |
| Lamination steel | M330-35A in the machine file (2bc520b); bracket done: back-EMF spread 0.13 %, torque 1.8 % at 100 A | `build_prius_ornl.py --steel` (default M330-35A; M400-50A rebuilds the old file exactly). Tata B-H to 1.8 T; above it our extrapolation (saturation polarization 2.0 T, slope-continuous). It matters more than first thought: it sets the torque above about 200 A (torque r1). The overspeed verdict stands: same density (7650), and the stress there does not depend on E |
| Efficiency map | not started | M330-35A loss data in hand (`models/motor/materials/`) |
| Thermal network | not started | |
| Blind comparison with ORNL | sealed until all of the above | |

**Decision (user, 2026-11-22 ~00:40): one stand-in lamination steel, M330-35A, for every property.**
- Why: ORNL gives the thickness (0.014 in = 0.36 mm) but not the grade; Toyota likely used a supplier's proprietary
  0.35 mm grade. The aim is the closest guess to what Toyota used (reverse engineering for a blind validation), not
  the best steel. M330-35A is a standard 0.35 mm EN 10106 grade with full public data, mid-range in its class.
- Until now the study mixed two steels: the electromagnetics used Pyleecan's inherited M400-50A B-H curve (0.5 mm,
  never chosen), the overspeed check used M330-35A's yield (335 MPa, Waelzholz; Tata's sheet says 315), and the loss
  data is M330-35A (Tata 2009). The two B-H curves differ a lot: M400-50A needs 2-4 x more field at 1.0-1.5 T
  (e.g. 950 against 242 A/m at 1.3 T), where the Prius teeth run.
- To do after tonight's runs: put M330-35A's B-H curve (Tata, typical, 50 Hz) and density into the machine file
  through `build_prius_ornl.py` (sourced like the other changes), rerun open circuit and torque, and keep the
  M400-50A runs as the "inherited steel" side of the sensitivity. This is a design-input correction made before the
  ORNL data is opened, so it is allowed with this written reason.

**Decision (user, same time): bracket the unknown grade.** Rerun the key cases (open circuit, torque at two currents,
overspeed) with a lower-loss 0.35 mm grade (M250-35A) and a high-strength rotor grade (a Y390 type, Rp0.2 about 412
MPa). The blind predictions become ranges. Needs published B-H, loss and yield data for both (material searches only;
never search for Prius performance).

**Next step recorded (user, same time): a material trade study after validation.** Once the model is validated
against ORNL, swap lamination grades and report what each changes in efficiency, torque and overspeed margin, with
rough public cost indices (relative, labelled as such). That is the cost-versus-performance question a client would
ask; it belongs after validation, not inside it.

**Uncommitted at handoff (04:45):** nothing of study 7's. `scripts/make_study_renders.py`, site/ and docs/ belong to the
dashboard session.

**Next, in order (04:45):** (1) the user's calls listed under "Waiting on the user" in the handoff; (2) the efficiency
map: design the case (loss model from the M330-35A fit, copper loss, voltage limit and flux weakening above base speed,
which operating points) and write its predictions before any run; (3) the thermal network.

## Action items

- **Local model (Inkling 2 Mini): optimisation under way 2026-11-21.** The action list and experiment log
  are in [local_llm/PLAN.md](local_llm/PLAN.md). The first finding: the GPU had never been used (missing
  CUDA runtime DLLs), so the numbers below are CPU-only and out of date.
  - **Status:** it runs through Unsloth's llama.cpp build at about 4.4 tokens/s on the RTX 3070, with
    the experts in RAM. On a six-task trial it got the calculation, extraction, report reading and tool
    call right, and was only partly right on diagnosis and planning.
  - **Decision:** not for planning. A possible use is overnight batch extraction and triage
    through a small `harness/local_llm.py`.
  - **Revisit when:** Ollama ships PC support for Inkling, or an official llama.cpp build includes
    PR #32704 (merged 2026-11-21) together with Unsloth's `Mainline_Support` files.
  - The setup and the results are in the session memory note `local-llm-hardware`.
  - **Speed it up later** with [sybil-solutions/inference-optimisation-skill](https://github.com/sybil-solutions/inference-optimisation-skill)
    (MIT license; one skill, `skills/inference-optimisation`, plus a `PROMPT.md` any agent can follow).
    It hill-climbs local LLM serving speed: decode, speculative decoding, prefill, KV cache, startup.
    Its method:
    - compute the theoretical ceiling first;
    - change one thing at a time against interleaved controls;
    - log every result, failures included;
    - gate on long-context retrieval.

    Its published results include a 3090 and Arc GPUs, but nothing at 8 GB of VRAM. Our baseline to
    beat: 4.4 tokens/s generating and 22 tokens/s reading prompts, experts in RAM. Installing it as a
    project skill is a config change: show it first. Its ceiling step would tell us early how much is
    reachable on the RTX 3070's memory bandwidth.
- **Study 6 install:** done by the user 2026-11-21.

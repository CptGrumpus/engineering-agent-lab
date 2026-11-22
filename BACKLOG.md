# Backlog: harder studies

Planned studies, not started. Each one follows the usual loop (frame requirements, build the model, run, verify, report), and its independent check is fixed before any modelling starts. When a study starts, change its status here; when it is verified, it gets its own case files, a study module, tests and a page section, and moves off this list.

| # | Study | Why it's harder | Independent check | Tools | Effort | Status |
|---|-------|-----------------|-------------------|-------|--------|--------|
| 1 | Bolted joint: preload plus a side load, with friction contact | Contact with friction and preload: when does the joint slip or open? | VDI 2230 hand method; slip load = μ × clamp force | CalculiX | Medium | **Verified** (run 20261121-110554_bolted_joint_mesh_r1, 1.0 / 0.75 / 0.5 mm): the joint FAILS the slip requirement after settling, 2.39 kN against 2.5 kN (4.4 % short; needs about 15.5 kN preload); opening 13.1 kN passes; GCI 1e-4. The FE slip load sits 0.13 % under mu F_V because the interface tilts with the strain (shortfall linear in 1/E); a rigid-limit companion solve recovers mu F_V to 1e-7; [portfolio/16](portfolio/16-bolted-joint-slip.md) |
| 2 | Cold plate, full thermal chain: coolant CFD → conduction through the aluminium plate → thermal stress | Three physics chained, each verified before passing results to the next | Fin and slab conduction theory, closed-form thermal stress, energy balance at every handoff | OpenFOAM → CalculiX | Medium-high | **Verified** (run 20261121-094235_cold_plate_mesh_r1, 40 / 60 / 80 cells): component face 40.99 C (limit 45), coolant rise 7.20 K (limit 10), thermal stress 46.8 MPa (limit 60); all requirements pass, GCI <= 3.5e-4; [portfolio/15](portfolio/15-cold-plate-thermal-chain.md) |
| 3 | Bracket optimisation loop: the agent changes geometry, meshes, solves and checks, repeating to minimise mass under stress and stiffness limits | The agent drives a design, not just one case | Every candidate passes the existing checks; optimum spot-checked against beam theory | CadQuery · Gmsh · CalculiX | Medium | **Verified** (3D machined clevis bracket; confirmation run 20261121-115130_clevis_confirm_r2b): lightest design found 371.9 g (lug 10.17 mm, gussets 9.07 x 36.36 mm), 4.1 % under the start, peak 98.3 MPa (98.9 with mesh uncertainty) against 100. Took three optimisation runs: a 1 % margin too small for a fillet peak, a global mesh study that never refined the fillet, and an optimiser stalled in mesh noise (resolved with local fillet refinement and a local response surface); [portfolio/12](portfolio/12-bracket-optimisation.md). First version (tapered cantilever) kept as superseded evidence |
| 4 | Notched bar with plasticity | Nonlinear material: stress beyond yield, residual stress after unloading | Neuber's rule, Glinka's method | CalculiX | Medium | **Done**: proof test at 15 kN strains the hole edge 0.58 % (limit 1 %), leaves -77 MPa residual; [portfolio/14](portfolio/14-strap-proof-plasticity.md) |
| 5 | Buckling: column or thin panel, linear eigenvalue, then with a small imperfection | Stability: a load-path problem, not just stress | Euler and Johnson formulas, Southwell plot | CalculiX | Low-medium | **Done**: longest acceptable strut about 587 mm; [portfolio/13](portfolio/13-strut-buckling.md) |
| 6 | Fluid-structure interaction: flexible flap in a channel | Coupled multiphysics | A published benchmark | OpenFOAM · CalculiX · preCICE | High (a weekend or more) | **In progress** (study 6): CSM1-3, CFD1-2 done; FSI1 revision 1 under way; FSI2, FSI3 to come (handoff) |
| 7 | Electric motor, an open-source Motor-CAD alternative: the Toyota Prius IPM motor (2004, ORNL) | Three physics on one machine. Electromagnetics: torque, back-EMF, flux-linkage and efficiency maps. Thermal: a lumped network from the geometry. Mechanical: rotor stress at overspeed | The published Prius data (Oak Ridge National Laboratory); an analytic air-gap field; the thermal network against CalculiX heat transfer on a stator section; power balance at every map point | Pyleecan + FEMM (pyFEMM), Python or OpenModelica, CalculiX. Options considered 2026-11-20: SyR-e (needs MATLAB), SWAT-EM (windings), Elmer and GetDP (3D) | High | Not started. Feasibility checked 2026-11-21: Pyleecan's PyPI release (1.5.2, 2024) needs Python < 3.11, but its GitHub master installs and imports on Python 3.14 (numpy 2.5, VTK 9.7, PySide6). Install with `PYTHONUTF8=1`, or setup.py fails on Windows' default encoding. It ships a Toyota Prius IPM model (48 slots, 8 poles, 0.75 mm air gap, 83.8 mm stack), which is the 2004 Prius documented by ORNL, so benchmark against the 2004 report rather than the 2010 one. FEMM 4.2 (x64, 22Oct2023 build) installed by the user at C:emm42 on 2026-11-21 and registered for scripting (femm.ActiveFEMM). A pyFEMM smoke test from Python 3.14 (a 100 A wire, where B = mu0 I / (2 pi r) exactly) agreed within 0.1-0.5 % on FEMM's default mesh. pyFEMM needs pywin32. Keep Pyleecan in its own environment, apart from the repo's pinned .venv |
| 8 | Pressure vessel with a nozzle, ASME VIII-2 Part 5 elastic stress analysis (study 18) | Design-code verdict from linearised stresses on classification lines; rule vs analysis | Lame cylinder, exact pressure resultants, simplified pressure-area rule | CadQuery · Gmsh · CalculiX | Medium | **Done** (optional extras in the handoff): [portfolio/18](portfolio/18-pressure-vessel-nozzle.md), PL 205.1 against 207 MPa, nozzle needs about 11.7 mm (rule: 16) |
| 9 | Turbulent CFD: pipe friction, then the backward-facing step against measurements (study 19) | Turbulence modelling; validation against measured data | Prandtl's smooth-pipe law; Driver & Seegmiller's step data | OpenFOAM | Medium | **In progress**: part 1 (pipe friction) done, [portfolio/19](portfolio/19-turbulent-pipe-friction.md): +2.4 % on Prandtl converged, wall functions -5 %; part 2 (step) waits on data hosts (handoff) |
| 10 | Random vibration of the study-4 bracket (C) | Forced response to a PSD; 3-sigma stress; vibration fatigue | Miles' equation; effective mass | CalculiX · Python | Medium | Documented, not started (handoff) |
| 11 | Natural convection and radiation (D) | Buoyant flow; view-factor radiation | de Vahl Davis cavity benchmark; two-surface exchange | OpenFOAM · CalculiX | Medium | Documented, not started |
| 12 | O-ring compression (E) | Hyperelastic large strain with self-contact | Published force-squeeze correlation; J about 1 | CalculiX | High | Documented, not started |
| 13 | Cracked plate, K and crack growth (F) | Fracture mechanics; damage tolerance | Handbook K solutions; G-K consistency | CalculiX · Python | Medium | Documented, not started |
| 14 | Rotor critical speeds (G) | Rotordynamics, Campbell diagram | Jeffcott rotor closed form | ROSS (Python) | Low-medium | Documented, not started |
| 15 | Probabilistic uncertainty on an existing study (H) | Sobol indices, failure probability | Monte Carlo convergence; analytic linear case | Python | Low-medium | Documented, not started |

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

## Session handoff (2026-11-22, 19:10; first written 2026-11-21, 23:10)

**Done this evening (17:15-19:10 session; user, ~18:10: "do as much of this list as you can before I go to bed"; user
said yes to the blind comparison and to the skill eval):** study 7 thermal network (r1 final); FSI1 r1 scored (29e6655,
page 9c41e8d); skill eval single-mesh-agreement-trap 8/8 (9031316, `evals/.../results.md`); efficiency figure fixed
(d69953b); motor reports gained a thermal page; **study 7 blind comparison run: all three limits FAIL** (0f58d8c,
ebb75f7; `validation/motor_ornl/RESULTS.md`, log `reports/motor/blind_comparison_log.md`): back-EMF +23.5 %, torque +7 to
+24 %, efficiency +5.2 points; the model's magnet flux is about 24 % high. Artifact version 6.
**For the dashboard session:** study 7 is no longer "blind, sealed": the comparison ran and failed (see above); thermal
added; study 6 FSI1 reproduces the benchmark within 1 % (drag and lift verified). Pages under `site/` that show study 7
or study 6 status are stale.
**Open for the user:** (a) study 7 diagnostic: may I open ORNL/TM-2004/137 Fig. 13 (measured air-gap flux density) to
split the 24 % between magnets and winding? Then a documented revision with predictions first, the blind verdicts kept.
(b) the skill eval's no-skills baseline (not run).

Read this first in a new session. Files under site/, docs/, DASHBOARD.md and `scripts/make_study_renders.py` belong
to the dashboard session (it commits in this clone: add and commit only your own paths, in one command; never leave
files staged). Study 7's HTML reports live in `reports/motor/`. Rules that still bind: the ORNL measured data stays
SEALED until study 7 is complete (ask before opening any; whitelist extraction only; material searches only, never
search for Prius performance); never run two FEMM cases at once (OpenFOAM/CalculiX may run beside FEMM: 24 cores);
predictions go into a case header and get committed BEFORE its evidence run; Results blocks after; `scripts/scrub_paths.py
<run dir>`, commit with `git add -f` leaving out `*.inp`, `*.dat`, `__pycache__` and logs over about 600 KB, then
`tests/test_privacy.py`.

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

### Running at 17:10 (background shells: they should keep running after a /clear; confirm with the commands below)

Check with `ps -ef | grep "[h]arness pipeline"` (WSL jobs: `wsl.exe -e bash -lc "ps -eo etime,cmd | grep -E 'Foam|ccx' | grep -v grep"`).
A run is finished when its `runs/<timestamp>_<case>/report.md` exists. Logs are in the 13:50-17:10 session's scratchpad,
`$TEMP/claude/cb67dd1e648f8970/2466259e-97df-49dc-993b-d474fed5635d/scratchpad/` ($TEMP = the user's AppData/Local/Temp).

Logs of the 17:15 session (thermal runs): `$TEMP/claude/cb67dd1e648f8970/4abd5a92-1872-493d-b389-7a0cff188b91/scratchpad/`.

| Job | Run dir (log) | Done about | When it finishes |
|---|---|---|---|
| (none at 19:10: FSI1 r1 finished 18:09 and is scored) | | | |

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
  **Not yet in `reports/motor/`** (they still show the old J values).
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
- **Next (optional):** a classification-line placement sensitivity (a line through the crotch corner), the head-to-shell
  junction against shell discontinuity theory; then the portfolio page (`portfolio/18-...`) and a PORTFOLIO.md row.

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

- 2026-11-22 ~16:00: new portfolio pages `portfolio/18-pressure-vessel-nozzle.md` (complete), `portfolio/20-prius-traction-motor.md`
  and `portfolio/17-fsi-flag-turek-hron.md` (drafts, now in PORTFOLIO.md); `portfolio/19-turbulent-pipe-friction.md` (part 1
  complete, with `portfolio/img/pipe_friction.png`); new task `tasks/nozzle_stress_linearisation`.
  PORTFOLIO.md no longer states a study count. The site's study list and counts may be stale.

### Waiting on the user

Nothing blocking. For review when convenient: study 18's 14 mm recommendation. (User, 2026-11-22 ~15:00: "keep working
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

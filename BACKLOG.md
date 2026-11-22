# Backlog: harder studies

Planned studies, not started. Each one follows the usual loop (frame requirements, build the model, run, verify, report), and its independent check is fixed before any modelling starts. When a study starts, change its status here; when it is verified, it gets its own case files, a study module, tests and a page section, and moves off this list.

| # | Study | Why it's harder | Independent check | Tools | Effort | Status |
|---|-------|-----------------|-------------------|-------|--------|--------|
| 1 | Bolted joint: preload plus a side load, with friction contact | Contact with friction and preload: when does the joint slip or open? | VDI 2230 hand method; slip load = μ × clamp force | CalculiX | Medium | **Verified** (run 20261121-110554_bolted_joint_mesh_r1, 1.0 / 0.75 / 0.5 mm): the joint FAILS the slip requirement after settling, 2.39 kN against 2.5 kN (4.4 % short; needs about 15.5 kN preload); opening 13.1 kN passes; GCI 1e-4. The FE slip load sits 0.13 % under mu F_V because the interface tilts with the strain (shortfall linear in 1/E); a rigid-limit companion solve recovers mu F_V to 1e-7; [portfolio/16](portfolio/16-bolted-joint-slip.md) |
| 2 | Cold plate, full thermal chain: coolant CFD → conduction through the aluminium plate → thermal stress | Three physics chained, each verified before passing results to the next | Fin and slab conduction theory, closed-form thermal stress, energy balance at every handoff | OpenFOAM → CalculiX | Medium-high | **Verified** (run 20261121-094235_cold_plate_mesh_r1, 40 / 60 / 80 cells): component face 40.99 C (limit 45), coolant rise 7.20 K (limit 10), thermal stress 46.8 MPa (limit 60); all requirements pass, GCI <= 3.5e-4; [portfolio/15](portfolio/15-cold-plate-thermal-chain.md) |
| 3 | Bracket optimisation loop: the agent changes geometry, meshes, solves and checks, repeating to minimise mass under stress and stiffness limits | The agent drives a design, not just one case | Every candidate passes the existing checks; optimum spot-checked against beam theory | CadQuery · Gmsh · CalculiX | Medium | **Verified** (3D machined clevis bracket; confirmation run 20261121-115130_clevis_confirm_r2b): lightest design found 371.9 g (lug 10.17 mm, gussets 9.07 x 36.36 mm), 4.1 % under the start, peak 98.3 MPa (98.9 with mesh uncertainty) against 100. Took three optimisation runs: a 1 % margin too small for a fillet peak, a global mesh study that never refined the fillet, and an optimiser stalled in mesh noise (resolved with local fillet refinement and a local response surface); [portfolio/12](portfolio/12-bracket-optimisation.md). First version (tapered cantilever) kept as superseded evidence |
| 4 | Notched bar with plasticity | Nonlinear material: stress beyond yield, residual stress after unloading | Neuber's rule, Glinka's method | CalculiX | Medium | **Done**: proof test at 15 kN strains the hole edge 0.58 % (limit 1 %), leaves -77 MPa residual; [portfolio/14](portfolio/14-strap-proof-plasticity.md) |
| 5 | Buckling: column or thin panel, linear eigenvalue, then with a small imperfection | Stability: a load-path problem, not just stress | Euler and Johnson formulas, Southwell plot | CalculiX | Low-medium | **Done**: longest acceptable strut about 587 mm; [portfolio/13](portfolio/13-strut-buckling.md) |
| 6 | Fluid-structure interaction: flexible flap in a channel | Coupled multiphysics | A published benchmark | OpenFOAM · CalculiX · preCICE | High (a weekend or more) | Not started: needs preCICE and its OpenFOAM and CalculiX adapters installed in WSL (sudo) |
| 7 | Electric motor, an open-source Motor-CAD alternative: the Toyota Prius IPM motor (2004, ORNL) | Three physics on one machine. Electromagnetics: torque, back-EMF, flux-linkage and efficiency maps. Thermal: a lumped network from the geometry. Mechanical: rotor stress at overspeed | The published Prius data (Oak Ridge National Laboratory); an analytic air-gap field; the thermal network against CalculiX heat transfer on a stator section; power balance at every map point | Pyleecan + FEMM (pyFEMM), Python or OpenModelica, CalculiX. Options considered 2026-11-20: SyR-e (needs MATLAB), SWAT-EM (windings), Elmer and GetDP (3D) | High | Not started. Feasibility checked 2026-11-21: Pyleecan's PyPI release (1.5.2, 2024) needs Python < 3.11, but its GitHub master installs and imports on Python 3.14 (numpy 2.5, VTK 9.7, PySide6). Install with `PYTHONUTF8=1`, or setup.py fails on Windows' default encoding. It ships a Toyota Prius IPM model (48 slots, 8 poles, 0.75 mm air gap, 83.8 mm stack), which is the 2004 Prius documented by ORNL, so benchmark against the 2004 report rather than the 2010 one. FEMM 4.2 (x64, 22Oct2023 build) installed by the user at C:emm42 on 2026-11-21 and registered for scripting (femm.ActiveFEMM). A pyFEMM smoke test from Python 3.14 (a 100 A wire, where B = mu0 I / (2 pi r) exactly) agreed within 0.1-0.5 % on FEMM's default mesh. pyFEMM needs pywin32. Keep Pyleecan in its own environment, apart from the repo's pinned .venv |

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

## Session handoff (2026-11-21, late evening, before /clear)

Read this first in a new session. The dashboard is maintained by another session; files under site/
and docs/ belong to it.

**Runs that were still going at handoff.** They write to `runs/` whether or not this session is
alive. Check with `ls -td runs/*` and, if one is still solving, `wsl -e pgrep -a foamRun` or
`tasklist | grep ccx`. When each finishes, follow these steps:
1. Read its report.
2. Compare it with the predictions in its case header.
3. Append a "Results" block to the header.
4. Fill in the *pending* items in `portfolio/17-fsi-flag-turek-hron.md`.
5. Run `scripts/scrub_paths.py <run dir>`, then commit the case and the curated run with `git add -f`. Leave out `*.inp`, `*.dat`, `__pycache__`, and solver logs over about 600 KB (the CSM3 `dynamic.log` files run to 10 MB).

| Case | Run directory prefix | Expected |
|---|---|---|
| `cases/turek_hron_fsi1_mesh.toml` (FSI1, coupled, three fluid meshes), RERUN started about 20:35 | the newest `*_turek_hron_fsi1_mesh` (not `20261121-184241_...`, which is the stopped run with the force-parser bug) | About 5.5 h, so about 2:00. The prototype gave uy(A) 0.818 mm (-0.34 %), drag 14.293 (-0.006 %), lift 0.764 (+0.03 %); predictions P1-P5 are in the case header. Check that drag reads about 14.29, not 21.7: if it is 21.7, the parser fix did not take. If verified, study 6's coupled stage is done (FSI2 and FSI3 are periodic and need ALPHA 0 in the solid and a longer run) |

If a run stopped with the session (no report.md, no solver processes running), rerun it from its case file with `.venv/Scripts/python.exe -m harness pipeline cases/<case>.toml`. It takes about 1 h for CSM3 r3's last point and 5.5 h for FSI1.


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
- The portfolio page is a draft, not linked from PORTFOLIO.md until study 6 is complete.

**Study 7 (motor), feasibility.** See its row in the table above. The Pyleecan test environment was in
a session scratchpad and is gone. To recreate it:
1. `py -3.14 -m venv <dir>`
2. `set PYTHONUTF8=1`
3. `<dir>/Scripts/python -m pip install git+https://github.com/Eomys/pyleecan.git`

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
- **Privacy:** the committed machine file (e060598) and its run input carried Pyleecan's own `C:/Users/LAP10/...`
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

**Uncommitted at handoff:** nothing settled. Running cases and their runs are committed once they finish.

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

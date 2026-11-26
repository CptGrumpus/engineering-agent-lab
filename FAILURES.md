# Failure ledger

Every run with a failed point gets a row here in the same session, with the software and version, what happened,
the cause (or "not diagnosed") and the status. `tests/test_failures_ledger.py` fails when a committed run with a
failed point is missing; `python scripts/list_failures.py` lists every failed point and marks the unlisted ones.
A failed run is evidence, not noise: keep it, record it, and put the lesson into the matching skill.

## By software (2026-11-25: 24 failed points in 21 runs, of 951 points)

| Software | Failed runs | Fixed | Open |
|---|---|---|---|
| CalculiX 2.20 through the preCICE adapter (`ccx_preCICE` 2.20.2, preCICE 3.4.1, Open MPI 4.1.2), the FSI solid | 8 | the hang (Open MPI's crash handler, 57d5d01) | the crash itself: Newton creep under an undamped integrator; fix under test (`turek_hron_fsi3_dt_a_alpha`) |
| OpenFOAM v2512 `pimpleFoam` (FSI fluid) | 3 | yes (frozen mesh-motion diffusivity) | |
| CalculiX 2.22 (FreeCAD 1.1 build), standalone | 7 | yes (each below) | |
| OpenFOAM 14 (`foamRun`) | 1 | yes (timeout) | |
| Pyleecan / FEMM 4.2 | 1 | yes (our setup) | |
| Our own Python (post-processing) | 1 | yes (our bug) | |

The one that keeps crashing is the FSI solid, `ccx_preCICE`. Its chain, as established on 2026-11-25:
1. **Precursor:** the solid's Newton iterations per step creep (2 for most of the run, then 3, 4, 5-7, 14-18) under
   HHT alpha 0, the undamped trapezoidal rule: energy builds in the flag's stiff in-plane modes (CalculiX's .sta,
   column ITRS; the same signature as CSM3 r1/r2, which alpha -0.05 cured). Runs that finished show no creep.
2. **Crash:** in `*DYNAMIC, DIRECT` CalculiX stops when a step does not converge; under the adapter that stop ends
   in a heap corruption ("corrupted double-linked list", SIGABRT or SIGSEGV). Reproducible in 20 s with
   `solid_iteration_limit = 1`, `ramp_time_s = 0`.
3. **Hang:** Open MPI's crash handler (`opal_signal` 6,7,8,11) tries to print a backtrace from the corrupted heap and
   spins forever. Fixed: `OMPI_MCA_opal_signal=""` in `models/fsi/run_turek_hron_fsi.sh` (the solid now exits with
   134 in seconds).
4. **Misattribution:** the runner reported "solid failed (exit 30)" whatever happened, because it tests the solid's
   exit code first. Fixed: `participants_exit.txt` records each participant's exit code (signals decoded) and end
   time. The order does not name the culprit (a stopping solid closes its socket before it aborts); the logs do.

## Ledger

| Date | Run(s) | Software | What happened | Cause | Status |
|---|---|---|---|---|---|
| 2026-11-20 | 20261120-235041_bolted_joint_mesh (0.7 mm) | CalculiX 2.22 | Hit the 4 h timeout (friction contact, finest mesh) | Cost, not a fault | Superseded by bolted_joint_mesh_r1 (1.0 / 0.75 / 0.5 mm), verified |
| 2026-11-21 | 20261121-000013_clevis_opt (c019), 20261121-002416_clevis_confirm (4 mm) | CalculiX 2.22 | Exit 201 | Gmsh's second-order curving inverted one quadratic tet | Fixed: the loop rejects the candidate; CAD build corrected; element-quality check |
| 2026-11-21 | 20261121-125924_heated_channel_mesh_r1 (160 cells) | OpenFOAM 14 | Backend's fixed 7200 s timeout at flow iteration 960 of 2000 | Iterations and timeout not sized from the residuals | Fixed: heated_channel_mesh_r2 (1200 iterations, timeout in the case) |
| 2026-11-21 | 20261121-142836_flag_csm3_dt_r1, 20261121-164522_flag_csm3_dt_r2 (dt 0.000625 s) | CalculiX 2.22 (NLGEOM dynamic) | Diverged at t = 5.84 s after Newton iterations crept from 2 to 12 per step | HHT alpha 0 (no numerical damping): energy in stiff modes | Fixed: flag_csm3_dt_r3 (alpha -0.05) |
| 2026-11-23 | 20261123-105948_motor_prius_rev4_oc (3 points) | Pyleecan / FEMM 4.2 | LoadMissingFileError in load_json, all points in a minute | Our setup: the new machine files were not registered | Fixed and rerun |
| 2026-11-23 | 20261123-123413_turek_hron_fsi2_mesh_c, 20261123-180658_turek_hron_fsi2_mesh_c, 20261124-035322_turek_hron_fsi2_mesh_c_diag | OpenFOAM v2512 `pimpleFoam` (reported as "solid, exit 30") | Floating point exception in GAMG at 8.836 s after the Courant number jumped 2.2 -> 5.8 -> 17.9 | A cell under the flag tip collapsed: the mesh-motion diffusivity was ill-posed (a period-2 oscillation in the motion solve) | Fixed: frozen 1/d diffusivity; all three FSI2 levels rerun |
| 2026-11-24 | 20261124-082453_turek_hron_fsi2_mesh_a_r1, 20261124-175940_turek_hron_fsi2_mesh_a_r1, 20261124-082500_turek_hron_fsi2_mesh_c_r1 | `ccx_preCICE` | Heap corruption at 14.009 s (twice, deterministic) and 14.047 s; the solid hung | Newton creep from about 12 s (to 9-13 iterations), then the DIRECT stop (chain above) | Scored to 14.0 s (the user's decision); hang fixed; damping fix under test |
| 2026-11-24 | 20261124-091009_motor_prius_efficiency_rev5_refined (cold, hot) | Our Python (SciPy interpolation) | "One of the requested xi is out of bounds" | Half-table interpolation stepped off the grid edge | Fixed: half-table checks keep both grid ends (7a7412f) |
| 2026-11-24 | 20261124-100614_oring_free_lindley | CalculiX 2.22 | "Matrix found to be singular" at 26.5 % squeeze | A free ring is held radially only by its hoop stiffness; load steps too large | Fixed: load increments 0.005 |
| 2026-11-24 | 20261124-103347_turek_hron_fsi3_dt_a, 20261124-175934_turek_hron_fsi3_dt_a | `ccx_preCICE` | Heap corruption at 6.902 s (twice, deterministic); the solid hung | Newton creep from about 5 s (chain above) | Scored to 6.9 s; hang fixed; damping fix under test |
| 2026-11-24 | 20261124-103350_turek_hron_fsi3_dt_c | `ccx_preCICE` | Segmentation fault on the very last step (7.99975 of 8 s); the solid hung | Not diagnosed (creep had just begun: 2.85 iterations at 7.9 s); forces also lost to the old force-file size limit (fixed separately) | Tip record complete; force time-step check open (needs a 20 h rerun) |
| 2026-11-24 | 20261124-152828_shaft_fillet_radius (3.9 mm) | CalculiX 2.22 | Exit 201 | A 0.1 mm sliver face: 14 curved tets inverted | Fixed: Gmsh high-order optimisation plus an element-quality check |
| 2026-11-25 | 20261125-113046_turek_hron_fsi3_dt_a_r1 | `ccx_preCICE` | With solid iteration limit 40: passed 6.902 s, then the coupling stalled at 6.911 s and the solid crashed | Same creep (14-18 iterations by 6.9 s); raising the limit moved the failure to the coupling | Superseded by the damping test |
| 2026-11-25 | 20261125-162526_turek_hron_fsi3_dt_a_r2 | `ccx_preCICE` | With preCICE's own FSI3 acceleration: solid Newton failure at 6.895 s (first coupling iteration) | Same creep | Superseded by the damping test |

## Local-only runs (not committed; listed by `scripts/list_failures.py --all`)

| Date | Run(s) | Software | What happened | Cause | Status |
|---|---|---|---|---|---|
| 2026-11-18 | 20261118-213050_msd_step_modelica | OpenModelica 1.26 (harness backend) | Backend preparation failed on every point | First set-up of the OpenModelica backend | Fixed in set-up; later runs pass |
| 2026-11-18 | 20261118-213109_msd_step_modelica | OpenModelica 1.26 | Output grid mismatch: 501 points against the expected 30,001 | The simulation's output interval was not set from the case | Fixed in the backend; later runs pass |
| 2026-11-22 | 20261122-122935_scratch_pipe_r1_probe (n640) | OpenFOAM 14 | Stopped ("Terminated", exit 22) | The probe used the geometric-mean axial cell length, which stalls SIMPLE (found with pipe_rans_mesh_r1) | Fixed: a 1 mm axial length; the 160 / 320 / 640 study (pipe_rans_mesh_r3) verified REQ-T1 |

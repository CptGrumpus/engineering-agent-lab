# Study 19 part 2: protocol log (what measured data was opened, when, why)

Data: ERCOFTAC classic database, case 030 (Driver and Seegmiller), fetched 2026-11-22 20:31 to `~/data/ercoftac_case030/`
(outside the repo; `SOURCE.txt` there has the URL and the archive's sha256). Limits agreed with the user before any
comparison data was opened (BACKLOG, 2026-11-22 ~20:50): REQ-S1 Xr/H within 10 %, REQ-S2 Cf over 10 <= x/H <= 30
within 15 % rms, REQ-S3 Cp(30 H) - Cp(-4 H) within 0.02.

| Time (2026-11-22) | What | Why |
|---|---|---|
| 20:31 | Printed the head of `bkst-reattach.dat` while checking the download: measured Xr/H 6.26 +- 0.10 at alpha 0 (5.82 at -2, 6.72 at +2). | Unintended; declared in every case header since. |
| 20:31-23:35 | Inflow from the case description only (U_ref 44.2 m/s, delta 19 mm, Re_theta 5000 at x/H = -4, geometry). Model built, smoke-tested twice (our own Xr/H 6.41-6.42), inflow matched on theta. | Boundary conditions, not answer key. |
| 23:35 | Cases `step_mesh`, `step_outlet`, `step_inlet_tu` committed with predictions (75b4fbf) and started; their inputs are fixed. | Protocol: predictions before the data. |
| 23:40 | **Opened** the headers and the alpha-0 rows of `bkst-tauw.dat` (Table 3, Cf along the step-side wall, with uncertainties) and the first rows of `bkst-cp.dat` (Table 2, Cp on the step-side wall, four wall angles). | To write the comparison script's parser. No model input changed after this. |
| 2026-11-23 10:13 | **Scored once**: `compare.py 20261122-233146_step_mesh p02_mesh_level-1.4142` (finest level, as planned in the handoff). Opened the rest of `bkst-tauw.dat` and `bkst-cp.dat` (alpha 0) through the script. Result (RESULTS.md): REQ-S1 PASS (Xr/H 6.404 against 6.26, +2.3 %), REQ-S2 PASS (Cf rms 7.0 %, ours low at every station, -1 to -10 %), REQ-S3 **FAIL** (recovery 0.1534 against 0.1307, +0.0227, limit 0.02). | The finest level stopped at its 80000-iteration cap with U residuals 3.6e-7 / 4.7e-7 against 2e-7 (p and k, omega met): a verification FAIL, reported. Its effect on the recovery is bounded by the level-to-level spread (0.0011), well under the 0.0027 by which REQ-S3 fails; the coarser, converged levels give 0.1545 and 0.1541, further from the measurement. Not re-scored. |

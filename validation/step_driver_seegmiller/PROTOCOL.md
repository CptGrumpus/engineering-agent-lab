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

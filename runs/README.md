# runs/

Each execution writes `runs/<YYYYmmdd-HHMMSS>_<case>/`:

| Path | Contents |
|---|---|
| `inputs/case.toml` | Exact copy of the case file used (hash recorded in the manifest) |
| `manifest.json` | Run status, environment (Python, packages, platform, git commit), per-point parameters, solver diagnostics, metrics |
| `run.log` | Log from run, verify, and rerun steps |
| `points/<label>/timeseries.csv` | Numerical time history (`t_s,x_m,v_m_per_s`) |
| `points/<label>/point.json` | Parameters, derived values, solver status, metrics |
| `points/<label>/reference.csv` | Analytical reference time history (after verify) |
| `points/<label>/checks.json` | Independent check results (after verify) |
| `points/<label>/response.png` | Numerical vs reference overlay and error plot (after verify) |
| `verification.json` | Check summary across points |
| `report.md`, `report.json` | Requirement -> result -> check -> evidence traceability |
| `reproducibility.json` | Only in rerun directories: comparison against the original run |

Run directories are git-ignored. Commit a curated example with `git add -f`.

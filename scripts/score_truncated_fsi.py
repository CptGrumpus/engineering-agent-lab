"""Score periodic FSI runs on their records cut at a common end time, and apply the study's run-level mesh check.

Why: a CalculiX solid that dies late in a run (ccx_preCICE heap corruption, FSI2 r1 levels a and c at 14.01 and
14.05 s of 15 s) leaves the harness point 'failed' although the logs up to the crash are complete. Scoring every level
on the same window (records cut at --t-end) keeps the levels comparable: a run that finished is cut too.

usage: .venv/Scripts/python.exe scripts/score_truncated_fsi.py OUT.json --t-end 14.0 RUN_DIR RUN_DIR RUN_DIR
       [--parameter fluid_cell_size_m]

Per run, from points/p00_baseline/solver (the files the harness keeps, failed or not): the series exactly as
studies/turek_hron_fsi.py's backend builds them, cut at t <= t_end; the study's compute_metrics; the point checks
that the kept files allow, with the study's own functions and the case's tolerances:
  mesh (log.checkMesh), coupling_converged (iterations log, windows up to t_end), periodic (last two periods),
  force_transfer (window by window over the last N whole periods, preCICE watch-integrals);
not evaluated (the work dir's time directories and the Gmsh mesh are deleted after a run): inflow_profile and
flag_cells; they depend only on the boundary condition and the mesh generator, and are reported from the run itself
when it finished, else as not evaluated. Requirements from the case. Then the study's verify_run_level over the runs.
The records end where the runs ended; nothing is extrapolated or filled in.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from harness.checks import check  # noqa: E402
from harness.registry import study_for  # noqa: E402
from studies import turek_hron_fsi as F  # noqa: E402

OPS = {"<=": lambda v, lim: v <= lim, ">=": lambda v, lim: v >= lim}


def score(run: Path, t_end: float) -> dict:
    case = tomllib.loads((run / "inputs" / "case.toml").read_text(encoding="utf-8"))
    man = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    pt = man["points"][0]
    sd = run / "points" / pt["label"] / "solver"
    fl, so = sd / "fluid", sd / "solid"
    params, numerics, tol = case["parameters"], case["numerics"], case["verification"]
    n = int(numerics["periodic_periods"])
    d = float(F._W.DEPTH)          # the 2D mesh's thickness (m), as the backend's depth_m
    wp = F.read_watchpoint(so / "precice-Solid-watchpoint-A.log")
    # the harness keeps files under 20 MB; at small time steps the force files (a row per coupling sub-iteration) pass
    # it and are lost with the work dir (FSI3 dt_c): then only the displacement metrics can be scored
    forces_kept = (fl / "postProcessing/forces/0/force.dat").is_file()
    if forces_kept:
        Fo = F.read_forces(fl / "postProcessing/forces/0/force.dat")
        Ff = F.read_forces(fl / "postProcessing/forcesFlag/0/force.dat")
    else:
        Fo = Ff = np.column_stack([wp[:, 0], np.ones((len(wp), 4))])   # placeholder; force metrics set to NaN below
    it = F.read_iterations(fl / "precice-Fluid-iterations.log")
    t_last = float(wp[-1, 0])
    if t_last < t_end - 1e-9:
        raise SystemExit(f"{run.name}: record ends at {t_last:g} s, before t_end {t_end:g} s")
    wp, Fo, Ff = wp[wp[:, 0] <= t_end + 1e-9], Fo[Fo[:, 0] <= t_end + 1e-9], Ff[Ff[:, 0] <= t_end + 1e-9]
    dt = float(params["time_step_s"])
    it = it[it[:, 0] * dt <= t_end + 1e-9]
    series = {"t_s": wp[:, 0], "ux_A_m": wp[:, 3], "uy_A_m": wp[:, 4],
              "drag_N_per_m": np.interp(wp[:, 0], Fo[:, 0], (Fo[:, 1] + Fo[:, 3]) / d),
              "lift_N_per_m": np.interp(wp[:, 0], Fo[:, 0], (Fo[:, 2] + Fo[:, 4]) / d)}
    study = study_for(case["case"]["model"])
    metrics = study.compute_metrics(series, params, case)
    if not forces_kept:
        for k in list(metrics):
            if k.startswith(("drag", "lift")):
                metrics[k] = float("nan")
    st = F.periodic_stats(series, n)
    steady = max(abs(st["uy_A_amp"] - st["uy_A_prev_amp"]) / abs(st["uy_A_amp"]),
                 abs(st["drag_mean"] - st["drag_prev_mean"]) / abs(st["drag_mean"]) if forces_kept else 0.0)
    t0, _, t2 = F.last_periods(series["t_s"], series["uy_A_m"], n)
    chk = (fl / "log.checkMesh").read_text(encoding="utf-8")
    checks = [
        check("mesh", "checkMesh reports Mesh OK (1 = failed)", 0.0 if "Mesh OK." in chk else 1.0, 0.5),
        check("coupling_converged", f"coupling windows up to {t_end:g} s that hit the iteration limit without "
              "converging", float(np.sum(it[:, 3] < 0.5)), 0.5),
        check("periodic", "periodic state: max of |uy(A) amplitude, last period - the one before| / amplitude and the "
              "same for the drag mean" + ("" if forces_kept else " (forces not kept: uy(A) only)"), float(steady),
              tol["periodic_rel_tol"]),
    ]
    tr = {}
    if forces_kept:
        tr = F.transfer_per_window(F.read_watchintegral(fl / "precice-Fluid-watchintegral-Wet.log"),
                                   F.read_watchintegral(so / "precice-Solid-watchintegral-Wet.log"), Ff, t0, t2)
        checks.append(check("force_transfer", f"force transfer per coupling window over {t0:g}-{t2:g} s (preCICE "
                            "watch-integrals)", max(tr["transfer_mapping_max_rel"], tr["transfer_fluid_max_rel"]),
                            tol["force_transfer_rel_tol"]))
    done = pt["status"] == "completed"
    from_run = {}
    if done:
        for c in json.loads((run / "points" / pt["label"] / "checks.json").read_text(encoding="utf-8"))["checks"]:
            if c["id"] in ("inflow_profile", "flag_cells"):
                from_run[c["id"]] = {"status": c["status"], "value": c["value"], "tolerance": c["tolerance"]}
    reqs = []
    for r in case.get("requirements", []):
        v = float(metrics[r["metric"]])
        reqs.append({"id": r["id"], "metric": r["metric"], "value": v, "limit": r["limit"],
                     "status": "NOT EVALUATED" if np.isnan(v) else
                     ("PASS" if OPS[r["operator"]](v, r["limit"]) else "FAIL")})
    return {"run": run.name, "point_status_in_harness": pt["status"], "record_end_s": t_last, "t_end_s": t_end,
            "windows": int(len(it)), "coupling_iterations_mean": float(np.mean(it[:, 2])),
            "period_window_s": [t0, t2], "parameters": params, "metrics": metrics, "checks": checks,
            "checks_from_the_finished_run": from_run,
            "not_evaluated": ([] if done else ["inflow_profile", "flag_cells"])
            + ([] if forces_kept else ["force_transfer", "drag and lift metrics (force files not kept)"]),
            "requirements": reqs,
            "transfer": tr, "case": case}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--t-end", type=float, required=True)
    ap.add_argument("--parameter", default="fluid_cell_size_m")
    a = ap.parse_args()
    scored = [score(Path(r), a.t_end) for r in a.runs]
    ref = scored[0]["case"]
    wall_clock_only = {"solver_timeout_s"}   # a time limit, not a setting that changes the answer

    def same(sec, c):
        return ({k: v for k, v in c.get(sec, {}).items() if k not in wall_clock_only}
                == {k: v for k, v in ref.get(sec, {}).items() if k not in wall_clock_only})
    for s in scored[1:]:
        for sec in ("numerics", "verification"):
            if not same(sec, s["case"]):
                raise SystemExit(f"cases differ in [{sec}]")
        pa, pr = dict(s["parameters"]), dict(ref["parameters"])
        pa.pop(a.parameter, None), pr.pop(a.parameter, None)
        if pa != pr:
            raise SystemExit(f"cases differ in parameters other than {a.parameter}")
    points = [{"label": s["run"], "status": "completed", "parameters": s["parameters"], "metrics": s["metrics"]}
              for s in scored]
    case = dict(ref) | {"sweep": {"parameter": a.parameter}}
    study = study_for(ref["case"]["model"])
    run_checks, detail = study.verify_run_level(case, {"points": points}, points)
    for s in scored:
        s.pop("case")
    out = {"t_end_s": a.t_end, "parameter": a.parameter, "runs": scored, "run_checks": run_checks,
           "run_detail": detail}
    Path(a.out).write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    for s in scored:
        m = s["metrics"]
        print(f"{s['run']}: record to {s['record_end_s']:.3f} s, cut {a.t_end:g} s, {s['windows']} windows; "
              f"uy amp {m['uy_A_amp'] * 1e3:.3f} mm ({m['uy_A_amp_deviation_pct']:.2f} %), "
              f"f {m['uy_A_freq_Hz']:.4f} Hz ({m['uy_A_freq_Hz_deviation_pct']:.2f} %), "
              f"drag {m['drag_mean']:.2f}+-{m['drag_amp']:.2f}, lift amp {m['lift_amp']:.1f}, "
              f"ux mean {m['ux_A_mean'] * 1e3:.3f} mm")
        for c in s["checks"]:
            print(f"   {c['id']:22s} {c['status']}  {c['value']:.3e} (tol {c['tolerance']:.1e})")
        print("   " + "; ".join(f"{r['id']} {r['value']:.2f} {r['status']}" for r in s["requirements"]))
    for c in run_checks:
        print(f"{c['id']:40s} {c['status']}  value {c['value']:.3e}  tol {c['tolerance']:.1e}")


if __name__ == "__main__":
    main()

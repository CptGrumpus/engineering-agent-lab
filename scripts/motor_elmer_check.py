"""Study 7, step 3b: the independent Elmer model against the FEMM model on the revision-5 geometry.

    .venv/Scripts/python.exe scripts/motor_elmer_check.py <geometry.json> <femm point dir> <out dir> [--workers 4]

1. Closed-form magnet check (models/motor/elmer_em.cylinder_check).
2. Mesh study at the FEMM run's first rotor position: refinement 1.0 / 0.7 / 0.5.
3. 48 rotor positions over one electrical period on the finest mesh the study supports; lambda1 per phase, phase
   balance, anti-periodicity, the waveform against FEMM's (aligned by the fundamental's phase) and the gap's radial
   flux density fundamental against FEMM's.
Writes <out>/elmer_check.json (every number) and <out>/elmer_check.csv (the flux linkages); predictions and the
verdict are in validation/motor_ornl/CALIBRATION_PLAN.md (step 3b).
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models.motor.elmer_em import cylinder_check, elmer_version, solve_position  # noqa: E402


def _one(args):
    geo_path, theta, refine, work = args
    geo = json.loads(Path(geo_path).read_text(encoding="utf-8"))
    t0 = time.time()
    r = solve_position(geo, theta, Path(work), refine=refine)
    r["wall_s"] = time.time() - t0
    r.pop("nonlinear_changes", None)
    return r


def fund(x):
    x = np.asarray(x, float)
    return 2 * np.fft.rfft(x, axis=0)[1] / len(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("geometry")
    ap.add_argument("femm_point")
    ap.add_argument("out")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--positions", type=int, default=48)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="elmer_motor_"))
    geo = json.loads(Path(a.geometry).read_text(encoding="utf-8"))
    pp = geo["dims"]["pole_pairs"]
    res = {"elmer": elmer_version(), "geometry": a.geometry, "femm_point": a.femm_point}

    t0 = time.time()
    cyl = cylinder_check(work / "cylinder")
    cyl.pop("nonlinear_changes", None)
    res["cylinder_check"] = cyl
    print(f"cylinder: {cyl['Bx_T']:.5f} T against {cyl['expected_T']:.5f} ({cyl['rel_error']:+.2e})", flush=True)

    # FEMM reference
    fp = Path(a.femm_point)
    femm = np.loadtxt(fp / "flux_linkage.csv", delimiter=",", skiprows=1)
    femm_pt = json.loads((fp / "point.json").read_text(encoding="utf-8"))
    f_lam = femm[:, 1:4]
    f1 = fund(f_lam)
    res["femm"] = {"lambda1_Wb": float(np.mean(np.abs(f1))), "lambda1_phase_Wb": np.abs(f1).tolist(),
                   "metrics": femm_pt.get("metrics")}

    # 2. mesh study at theta = 0
    levels = [1.0, 0.7, 0.5]
    with ProcessPoolExecutor(max_workers=min(a.workers, 3)) as ex:
        mesh = list(ex.map(_one, [(a.geometry, 0.0, r, str(work / f"mesh_{r}")) for r in levels]))
    res["mesh_study"] = [{k: m[k] for k in ("lambda_Wb", "nodes", "elements", "sizes_mm", "nonlinear_iterations",
                                            "final_change", "wall_s")} | {"refine": r} for m, r in zip(mesh, levels)]
    la = [m["lambda_Wb"][0] for m in mesh]
    ref_amp = max(abs(x) for x in mesh[-1]["lambda_Wb"])
    print("mesh:", [f"{x:.6f}" for x in la], "nodes", [m["nodes"] for m in mesh], flush=True)
    d12, d23 = abs(la[1] - la[0]) / ref_amp, abs(la[2] - la[1]) / ref_amp
    res["mesh_change_rel"] = [d12, d23]
    refine = levels[-1]

    # 3. positions over one electrical period (rotor counter-clockwise, as Pyleecan's time axis turns it)
    n = a.positions
    thetas = [360.0 / pp * k / n for k in range(n)]
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        sweep = list(ex.map(_one, [(a.geometry, th, refine, str(work / f"pos_{k:02d}")) for k, th in
                                   enumerate(thetas)]))
    lam = np.array([s["lambda_Wb"] for s in sweep])
    e1 = fund(lam)
    lam1 = float(np.mean(np.abs(e1)))
    res["positions"] = {"theta_deg": thetas, "lambda_Wb": lam.tolist(), "refine": refine,
                        "nodes": [s["nodes"] for s in sweep], "wall_s": [s["wall_s"] for s in sweep],
                        "nonlinear_iterations": [s["nonlinear_iterations"] for s in sweep],
                        "final_change": [s["final_change"] for s in sweep]}
    res["elmer_lambda1_Wb"] = lam1
    res["elmer_lambda1_phase_Wb"] = np.abs(e1).tolist()
    res["lambda1_rel_diff"] = lam1 / res["femm"]["lambda1_Wb"] - 1
    res["phase_balance_rel"] = float(np.ptp(np.abs(e1)) / lam1)
    half = n // 2                                   # 45 deg mechanical = half an electrical period
    res["antiperiodicity_rel"] = float(np.max(np.abs(lam[half:, 0] + lam[:half, 0])) / lam1)
    # waveform: shift Elmer's phase a to FEMM's fundamental phase (sampled on the same grid; FFT shift)
    shift = np.angle(f1[0]) - np.angle(e1[0])
    k = np.arange(n // 2 + 1)
    ea = np.fft.irfft(np.fft.rfft(lam[:, 0]) * np.exp(1j * k * shift), n)
    res["waveform_max_diff_rel"] = float(np.max(np.abs(ea - f_lam[:, 0])) / res["femm"]["lambda1_Wb"])
    res["phase_offset_elec_deg"] = float(np.degrees(shift))
    # gap radial flux density at theta = 0 against FEMM's first-step sample
    br = np.asarray(sweep[0]["gap_Br_T"])
    b_p = np.abs(2 * np.fft.rfft(br)[pp] / len(br))
    res["elmer_gap_Br1_T"] = float(b_p)
    femm_br = (femm_pt.get("solver_outputs") or {}).get("gap_Br_T")
    if femm_br is not None:
        # FEMM's samples span one pole (0-45 deg, the anti-periodic model): extend to a full electrical period
        fb = np.asarray(femm_br, float)
        fb = fb[0] if fb.ndim > 1 else fb
        full = np.concatenate([fb, -fb])
        res["femm_gap_Br1_T"] = float(np.abs(2 * np.fft.rfft(full)[1] / len(full)))
        res["gap_Br1_rel_diff"] = res["elmer_gap_Br1_T"] / res["femm_gap_Br1_T"] - 1
    res["elapsed_s"] = time.time() - t0
    (out / "elmer_check.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    with (out / "elmer_check.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["theta_mech_deg", "elmer_a_Wb", "elmer_b_Wb", "elmer_c_Wb", "femm_a_Wb", "femm_b_Wb", "femm_c_Wb"])
        for th, le, lf in zip(thetas, lam, f_lam):
            w.writerow([f"{th:.6f}", *[f"{x:.8e}" for x in le], *[f"{x:.8e}" for x in lf]])
    print(f"lambda1 Elmer {lam1:.6f} Wb, FEMM {res['femm']['lambda1_Wb']:.6f} ({res['lambda1_rel_diff']:+.3%}); "
          f"balance {res['phase_balance_rel']:.2e}, antiperiodic {res['antiperiodicity_rel']:.2e}, "
          f"waveform {res['waveform_max_diff_rel']:.2e}, gap Br1 {res['elmer_gap_Br1_T']:.4f} T "
          f"(FEMM {res.get('femm_gap_Br1_T')}), {res['elapsed_s']:.0f} s", flush=True)
    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()

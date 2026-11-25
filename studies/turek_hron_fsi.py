"""Study: Turek-Hron fluid-structure interaction (FSI1), OpenFOAM v2512 + CalculiX through preCICE.

Model:     openfoam_ccx_precice_fsi (models/fsi/turek_hron_fsi.py, run_turek_hron_fsi.sh): the verified flag of
           studies/flag_csm.py and the fluid of studies/turek_hron_cfd.py, coupled (parallel implicit, IQN-ILS)
Reference: the published FSI1 values (the requirement); internal checks: every coupling window converged, the
           steady state reached, the force the fluid puts on the flag equal to the clamp reaction in the solid
           (the coupling conserves force), the inflow equal to the benchmark parabola at every inlet face
Run-level: GCI on the requirement metrics when the sweep is fluid_cell_size_m (single-mesh runs: none)

Opt-in (FSI1 revision 1): numerics.metric_average_s takes the metrics and the force-transfer check as means over the
last that many seconds instead of the final values, and verification.steady_measure = "drift" judges steadiness by
the change of the mean between the two halves of the steady window instead of the peak-to-peak spread. The first FSI1
run showed why: at Re 20 the lift jitters at every time step (coupling noise, about +-2 % of the lift) with no drift, so
a final value and a spread both report the noise. Cases without these keys behave as before.

Opt-in (FSI2 / FSI3, periodic): numerics.periodic_periods = N. The benchmark's definition (featflow FSI benchmark,
"Quantities for comparison"): over the last period, mean = (max + min) / 2 and amplitude = (max - min) / 2; frequency =
1 / period or the lowest significant FFT peak. Here the period is found from the upward crossings of uy(A) through its
mean; mean and amplitude come from the last whole period; each quantity's frequency is its dominant FFT peak over the
last N whole periods (drag and ux oscillate at twice the lift's and uy's frequency, as in the benchmark). Metrics
<q>_mean, <q>_amp, <q>_freq_Hz for q in ux_A, uy_A, drag, lift, and their deviations from the benchmark parameters
benchmark_<q>_mean / _amp / _freq_Hz: amplitudes and frequencies relative to the benchmark value, means relative to
max(|benchmark mean|, benchmark amplitude) (uy(A) and lift swing about zero). Checks: the periodic state (the last two
periods' uy(A) amplitudes and drag means agree), and force transfer averaged over exactly the last N whole periods (the
flag's inertia force averages out only over whole periods: in FSI2 it is several times the fluid force).
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness import openfoam as of
from harness.backend_base import Backend, failed
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study
from studies.strut_buckling import read_dat_blocks

WRITER = "models/fsi/turek_hron_fsi.py"
RUNNER = "models/fsi/run_turek_hron_fsi.sh"
FLAG_WRITER = "models/fea/flag_ccx.py"
FROZEN_DIFFUSIVITY = "models/fsi/frozen_motion_diffusivity.py"   # run by the runner, next to it
BENCH = ("benchmark_ux_A_m", "benchmark_uy_A_m", "benchmark_drag_N_per_m", "benchmark_lift_N_per_m")
METRICS = ("ux_A_m", "uy_A_m", "drag_N_per_m", "lift_N_per_m")
PERIODIC_Q = {"ux_A": "ux_A_m", "uy_A": "uy_A_m", "drag": "drag_N_per_m", "lift": "lift_N_per_m"}
PERIODIC_METRICS = tuple(f"{q}_{k}" for q in PERIODIC_Q for k in ("mean", "amp", "freq_Hz"))
# the periodic metrics a mesh study converges (the requirement metrics; the means of uy and lift swing about zero, so
# their relative uncertainty means nothing)
PERIODIC_GCI_METRICS = ("uy_A_amp", "uy_A_freq_Hz", "drag_mean", "drag_amp", "lift_amp", "ux_A_mean")
V2512_BASHRC = "/usr/lib/openfoam/openfoam2512/etc/bashrc"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_W = _load(Path(__file__).resolve().parent.parent / WRITER, "turek_hron_fsi_saved")


def _p(params, k):
    return float(params[k])


def read_forces(path: Path) -> np.ndarray:
    """OpenFOAM v2512 force.dat rows: (time, Fx_pressure, Fy_pressure, Fx_viscous, Fy_viscous).

    v2512 writes `time total_xyz pressure_xyz viscous_xyz` as plain columns. The openfoam.org v14 parser in
    studies/turek_hron_cfd.py reads `((pressure) (viscous))` instead: applied to a v2512 file it summed total +
    pressure and reported 21.6 N/m for a 14.3 N/m drag (FSI1, first evidence run)."""
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        v = [float(x) for x in line.split()]
        if len(v) != 10:
            raise ValueError(f"{path}: expected 10 columns (time, total, pressure, viscous), got {len(v)}")
        rows.append([v[0], v[4], v[5], v[7], v[8]])
    return np.array(rows)


def read_watchpoint(path: Path) -> np.ndarray:
    """preCICE watch-point log: (time, x, y, ux, uy, Fx, Fy)."""
    return np.loadtxt(path, skiprows=1, ndmin=2)


def read_watchintegral(path: Path) -> dict:
    """preCICE watch-integral log (scale-with-connectivity false: plain sums over the mesh's vertices), by column."""
    lines = [ln for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln.strip()]
    head = lines[0].split()
    v = np.loadtxt(lines[1:], ndmin=2)
    if v.shape[1] != len(head):
        raise ValueError(f"{path}: {len(head)} header names, {v.shape[1]} columns")
    return {h: v[:, k] for k, h in enumerate(head)}


def transfer_per_window(wi_fluid: dict, wi_solid: dict, Ff: np.ndarray, t0: float, t2: float) -> dict:
    """Force transfer, window by window over (t0, t2], with no inertia involved:
    mapping: |sum of Force the solid receives - sum the fluid writes| / max |sum the fluid writes|;
    fluid:   |sum the fluid writes - OpenFOAM's own force on the flag (forcesFlag, at the same time)| / max |that|."""
    t = wi_solid["Time"]
    sel = (t > t0) & (t <= t2)
    fs = np.column_stack([wi_solid["Force0"], wi_solid["Force1"]])[sel]
    tf = wi_fluid["Time"]
    fw = np.column_stack([np.interp(t[sel], tf, wi_fluid["Force0"]), np.interp(t[sel], tf, wi_fluid["Force1"])])
    ff = np.column_stack([np.interp(t[sel], Ff[:, 0], Ff[:, 1] + Ff[:, 3]),
                          np.interp(t[sel], Ff[:, 0], Ff[:, 2] + Ff[:, 4])])
    scale_w = float(np.max(np.linalg.norm(fw, axis=1)))
    scale_f = float(np.max(np.linalg.norm(ff, axis=1)))
    return {"transfer_mapping_max_rel": float(np.max(np.linalg.norm(fs - fw, axis=1)) / scale_w),
            "transfer_fluid_max_rel": float(np.max(np.linalg.norm(fw - ff, axis=1)) / scale_f),
            "transfer_windows": int(sel.sum()), "transfer_from_s": float(t0), "transfer_to_s": float(t2)}


def read_msh22_base(path: Path) -> tuple[dict, list]:
    """Gmsh 2.2 ASCII mesh of the extruded 2D domain: node xy, and the z = 0 face of each hexahedron (or the
    quads / triangles themselves in a 2D mesh)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    i = lines.index("$Nodes")
    xyz = {}
    for ln in lines[i + 2:i + 2 + int(lines[i + 1])]:
        a = ln.split()
        xyz[int(a[0])] = (float(a[1]), float(a[2]), float(a[3]))
    i = lines.index("$Elements")
    cells3, cells2 = [], []
    for ln in lines[i + 2:i + 2 + int(lines[i + 1])]:
        a = [int(v) for v in ln.split()]
        nodes = a[3 + a[2]:]
        if a[1] in (5, 6):                     # hexahedron / prism: base = the nodes at z = 0, in element order
            cells3.append([k for k in nodes if abs(xyz[k][2]) < 1e-12])
        elif a[1] in (2, 3):
            cells2.append(nodes)
    return {k: v[:2] for k, v in xyz.items()}, (cells3 or cells2)


def flag_cell_quality(xy: dict, cells: list, x_root: float, x_end: float, y_lo: float, y_hi: float) -> dict:
    """Largest interior angle of the fluid cells that touch the flag, and where. A quad wrapped around a tip
    corner (one cell spanning the 270 deg fluid corner, its angle there near 180 deg) puts a force error at the
    flag tip, where the moment arm is largest: turek_hron_fsi1_noise_a (2026-11-23), angle 165 deg, uy(A) 28 %
    low while every other check passed. The 22 other Turek-Hron meshes reach 128 deg at most."""
    def on_flag(p):
        x, y = p
        return ((x_root - 1e-6 <= x <= x_end + 1e-9 and (abs(y - y_lo) < 1e-9 or abs(y - y_hi) < 1e-9))
                or (abs(x - x_end) < 1e-9 and y_lo - 1e-9 <= y <= y_hi + 1e-9))
    worst, at = 0.0, [float("nan"), float("nan")]
    for c in cells:
        if len(c) < 3 or not any(on_flag(xy[k]) for k in c):
            continue
        pts = np.array([xy[k] for k in c])
        cen = pts.mean(axis=0)
        order = np.argsort(np.arctan2(pts[:, 1] - cen[1], pts[:, 0] - cen[0]))   # robust to node ordering
        pts = pts[order]
        for j in range(len(pts)):
            u, v = pts[j - 1] - pts[j], pts[(j + 1) % len(pts)] - pts[j]
            ang = float(np.degrees(np.arccos(np.clip(u @ v / np.linalg.norm(u) / np.linalg.norm(v), -1, 1))))
            if ang > worst:
                worst, at = ang, [float(cen[0]), float(cen[1])]
    return {"flag_cell_max_angle_deg": worst, "flag_cell_max_angle_at_m": at}


def _window_means(numerics, Ff, rf_blocks) -> dict:
    """Means of the flag's fluid force and the clamp reaction over the last numerics.metric_average_s (opt-in).
    Caution: under the preCICE adapter CalculiX prints the reaction only at the last increment, so its 'mean' is the
    end value; valid for a steady state (no inertia), which is the only case this is used for."""
    w = numerics.get("metric_average_s")
    if not w or not rf_blocks:
        return {}
    t_end = float(Ff[-1, 0])
    f = Ff[Ff[:, 0] >= t_end - float(w)]
    r = np.array([b["rows"][0][:2] for b in rf_blocks if b["time"] >= t_end - float(w)])
    return {"flag_fluid_force_mean_N": [float(np.mean(f[:, 1] + f[:, 3])), float(np.mean(f[:, 2] + f[:, 4]))],
            "clamp_reaction_mean_N": [float(np.mean(r[:, 0])), float(np.mean(r[:, 1]))],
            "metric_average_s": float(w)}


def _period_means(numerics, wp, Ff, rf_blocks) -> dict:
    """Means of the flag's fluid force and the clamp reaction over exactly the last N whole periods of uy(A)."""
    n = int(numerics["periodic_periods"])
    try:
        t0, _, t2 = last_periods(wp[:, 0], wp[:, 4], n)
    except ValueError:
        return {}
    f = Ff[(Ff[:, 0] > t0) & (Ff[:, 0] <= t2)]
    r = np.array([b["rows"][0][:2] for b in rf_blocks if t0 < b["time"] <= t2])
    if not len(f) or not len(r):
        return {}
    return {"flag_fluid_force_mean_N": [float(np.mean(f[:, 1] + f[:, 3])), float(np.mean(f[:, 2] + f[:, 4]))],
            "clamp_reaction_mean_N": [float(np.mean(r[:, 0])), float(np.mean(r[:, 1]))],
            "metric_average_s": float(t2 - t0), "metric_average_periods": n}


def last_periods(t: np.ndarray, uy: np.ndarray, n: int) -> tuple[float, float, float]:
    """(start of the last n whole periods, start of the last period, end) from the upward crossings of uy through
    the mean of the record's last 40 %; linear interpolation between samples. Raises if fewer than n + 1 periods."""
    tail = t >= t[0] + 0.6 * (t[-1] - t[0])
    y = uy - np.mean(uy[tail])
    k = np.flatnonzero((y[:-1] < 0) & (y[1:] >= 0) & tail[1:])
    tc = t[k] - y[k] * (t[k + 1] - t[k]) / (y[k + 1] - y[k])
    if len(tc) < n + 2:
        raise ValueError(f"only {max(len(tc) - 1, 0)} whole periods of uy(A) in the record's last 40 %; need {n + 1}")
    return float(tc[-1 - n]), float(tc[-2]), float(tc[-1])


def periodic_stats(series: dict, n: int) -> dict:
    """Benchmark statistics over the last whole period(s), plus the previous period's for the steadiness check."""
    t = np.asarray(series["t_s"])
    t0, t1, t2 = last_periods(t, np.asarray(series["uy_A_m"]), n)
    t_prev0 = t1 - (t2 - t1)
    out = {"period_window_s": [t0, t2], "periods_used": n}
    for q, col in PERIODIC_Q.items():
        x = np.asarray(series[col])
        last = (t >= t1) & (t <= t2)
        prev = (t >= t_prev0) & (t < t1)
        hi, lo = float(np.max(x[last])), float(np.min(x[last]))
        out[f"{q}_mean"], out[f"{q}_amp"] = 0.5 * (hi + lo), 0.5 * (hi - lo)
        out[f"{q}_prev_mean"] = 0.5 * (float(np.max(x[prev])) + float(np.min(x[prev])))
        out[f"{q}_prev_amp"] = 0.5 * (float(np.max(x[prev])) - float(np.min(x[prev])))
        # dominant frequency over the last n whole periods: uniform resample, zero-padded FFT, parabolic peak
        w = (t >= t0) & (t <= t2)
        tu = np.linspace(t0, t2, 4096, endpoint=False)
        xu = np.interp(tu, t[w], x[w]) - np.mean(x[w])
        nfft = 16 * len(tu)
        S = np.abs(np.fft.rfft(xu * np.hanning(len(tu)), nfft))
        fr = np.fft.rfftfreq(nfft, d=tu[1] - tu[0])
        j = int(np.argmax(S[1:])) + 1
        a, b, c = S[j - 1], S[j], S[j + 1] if j + 1 < len(S) else S[j]
        dj = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) != 0 else 0.0
        out[f"{q}_freq_Hz"] = float(fr[j] + dj * (fr[1] - fr[0]))
    out["uy_period_freq_Hz"] = 1.0 / (t2 - t1)
    return out


def read_iterations(path: Path) -> np.ndarray:
    """preCICE iterations log: (window, total iterations, iterations, converged, ...)."""
    return np.loadtxt(path, skiprows=1, ndmin=2)


class PreciceFSI(Backend):
    sources = (WRITER, RUNNER, FLAG_WRITER, FROZEN_DIFFUSIVITY)

    def __init__(self):
        from studies.cantilever import find_freecadcmd

        self.gmsh = find_freecadcmd().parent / "gmsh.exe"
        self.bashrc = os.environ.get("OPENFOAM_V2512_BASHRC", V2512_BASHRC)
        self._versions: dict = {"openfoam_bashrc": self.bashrc}

    def prepare(self, source_dir=None, log_dir=None):
        self.writer = _load(self.source_path(WRITER, source_dir), "turek_hron_fsi_run")
        self.runner = self.source_path(RUNNER, source_dir)
        r = subprocess.run([str(self.gmsh), "--version"], capture_output=True, text=True, timeout=60)
        self._versions["gmsh"] = ((r.stdout + r.stderr).strip().splitlines() or ["?"])[-1]

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="fsi_"))
        case = work / "case"
        info = self.writer.write_case(params, numerics, case)
        fl, so = case / "fluid", case / "solid"

        def files():
            # a long run's fluid log passes the size limit below and the work dir is deleted after the run, so a
            # crash would leave no message (FSI2 mesh c, 2026-11-23: floating point exception at 8.8 s, 53 MB log
            # lost): keep the last 400 lines of every oversized log as <name>.tail
            for big in list(fl.glob("log.*")) + list(so.glob("log.*")):
                if big.suffix != ".tail" and big.is_file() and big.stat().st_size >= 20e6:
                    with big.open("rb") as fh:
                        fh.seek(max(0, big.stat().st_size - 200_000))
                        tail = fh.read().decode("utf-8", "replace").splitlines()[-400:]
                    big.with_name(big.name + ".tail").write_text("\n".join(tail) + "\n", encoding="utf-8")
            # force files get a row per coupling sub-iteration and pass the size limit at small time steps (FSI3 dt_c,
            # 0.00025 s: drag and lift lost with the work dir, 2026-11-25): keep one row per time, the last (the
            # converged iteration), which is all the metrics use; small files are kept whole
            for big in fl.glob("postProcessing/*/0/*.dat"):
                if big.is_file() and big.stat().st_size >= 20e6:
                    rows, head = {}, []
                    for line in big.read_text(encoding="utf-8").splitlines():
                        if line.startswith("#") or not line.strip():
                            head.append(line)
                        else:
                            rows[line.split(None, 1)[0]] = line
                    big.write_text("\n".join(head + list(rows.values())) + "\n", encoding="utf-8")
            keep = (sorted(fl.glob("system/*")) + sorted(fl.glob("constant/*")) + sorted(fl.glob("0/*"))
                    + sorted(fl.glob("log.*")) + sorted(fl.glob("*.log")) + sorted(so.glob("log.*"))
                    + [fl / "mesh.geo"]
                    + sorted(fl.glob("postProcessing/*/0/*.dat"))
                    + [so / "flag.inp", so / "config.yml", so / "flag.sta"] + sorted(so.glob("*.log"))
                    + [case / "precice-config.xml", case / "versions.txt"])
            out = {str(f.relative_to(case)).replace("\\", "/"): f for f in keep
                   if f.is_file() and f.stat().st_size < 20e6}
            # dense writing (crash diagnosis): the last time directories written and the base mesh, whole, so
            # the state before the crash can be read offline (checkMesh -time, the fields); not for committing
            if (fl / "dense_write_from_s").is_file():
                t0 = float((fl / "dense_write_from_s").read_text().strip())
                times = []
                for p in fl.iterdir():
                    try:
                        times.append((float(p.name), p))
                    except ValueError:
                        pass
                dense = [p for t, p in sorted(times) if t >= t0][-int(numerics.get("dense_write_keep", 12)):]
                for f in [fl / "log.denseWrite", fl / "dense_write_from_s"] + sorted(
                        (fl / "constant/polyMesh").glob("*")) + [x for p in dense for x in sorted(p.rglob("*"))]:
                    if f.is_file():
                        out[str(f.relative_to(case)).replace("\\", "/")] = f
            return out

        g = subprocess.run([str(self.gmsh), "mesh.geo", "-3", "-format", "msh22", "-o", "mesh.msh"], cwd=fl,
                           capture_output=True, text=True, timeout=3600)
        (fl / "log.gmsh").write_text(g.stdout + g.stderr, encoding="utf-8")
        if g.returncode != 0 or not (fl / "mesh.msh").exists():
            return failed("Gmsh failed") | {"files": files(), "cleanup": work}
        W = self.writer
        quality = flag_cell_quality(*read_msh22_base(fl / "mesh.msh"), W.XC + (W.R ** 2 - (W.FLAG_H / 2) ** 2) ** 0.5,
                                    W.XC + W.R + W.FLAG_L, W.YC - W.FLAG_H / 2, W.YC + W.FLAG_H / 2)
        r = subprocess.run(of.wsl_command("bash", of.to_wsl_path(self.runner), of.to_wsl_path(case), self.bashrc),
                           capture_output=True, text=True, timeout=float(numerics.get("solver_timeout_s", 21600)))
        (fl / "mesh.msh").unlink(missing_ok=True)
        if r.returncode != 0:
            return failed(f"FSI run failed (exit {r.returncode}) {r.stderr.strip()[:300]}") | {
                "files": files(), "cleanup": work}
        for line in (case / "versions.txt").read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition("=")
            self._versions[k] = v
        d = info["depth_m"]
        wp = read_watchpoint(so / "precice-Solid-watchpoint-A.log")
        F = read_forces(fl / "postProcessing/forces/0/force.dat")
        Ff = read_forces(fl / "postProcessing/forcesFlag/0/force.dat")
        it = read_iterations(fl / "precice-Fluid-iterations.log")
        rfb = [b for b in read_dat_blocks(so / "flag.dat") if b["kind"] == "total" and b["set"] == "NFIX"]
        rf = [b["rows"][0] for b in rfb]
        chk = (fl / "log.checkMesh").read_text(encoding="utf-8")
        tdir = of.latest_time_dir(fl)
        u_in = np.asarray(of.read_patch_value(tdir / "U", "inlet"))
        y_in = np.asarray(of.read_patch_value(tdir / "C", "inlet"))[:, 1]
        U, H = _p(params, "mean_velocity_m_per_s"), self.writer.CH_H
        parabola = 1.5 * U * 4 * y_in * (H - y_in) / H**2
        series = {"t_s": wp[:, 0], "ux_A_m": wp[:, 3], "uy_A_m": wp[:, 4],
                  "drag_N_per_m": np.interp(wp[:, 0], F[:, 0], (F[:, 1] + F[:, 3]) / d),
                  "lift_N_per_m": np.interp(wp[:, 0], F[:, 0], (F[:, 2] + F[:, 4]) / d)}
        outputs = info | quality | {"cells": int(chk.split("cells:")[1].split()[0]), "mesh_ok": "Mesh OK." in chk,
                          "windows": int(len(it)), "windows_not_converged": int(np.sum(it[:, 3] < 0.5)),
                          "coupling_iterations_mean": float(np.mean(it[:, 2])),
                          "coupling_iterations_max": int(np.max(it[:, 2])),
                          "flag_fluid_force_N": [float(Ff[-1, 1] + Ff[-1, 3]), float(Ff[-1, 2] + Ff[-1, 4])],
                          "clamp_reaction_N": [float(rf[-1][0]), float(rf[-1][1])] if rf else [float("nan")] * 2,
                          **(_period_means(numerics, wp, Ff, rfb) if numerics.get("periodic_periods")
                             else _window_means(numerics, Ff, rfb)),
                          "inlet_profile_error_max": float(np.max(np.abs(u_in[:, 0] - parabola)) / (1.5 * U))}
        wif, wis = fl / "precice-Fluid-watchintegral-Wet.log", so / "precice-Solid-watchintegral-Wet.log"
        if wif.is_file() and wis.is_file():
            if numerics.get("periodic_periods"):
                try:
                    t0, _, t2 = last_periods(wp[:, 0], wp[:, 4], int(numerics["periodic_periods"]))
                except ValueError:
                    t0, t2 = float("nan"), float("nan")
            else:
                t2 = float(wp[-1, 0])
                t0 = t2 - float(numerics.get("metric_average_s", 2.0))
            if np.isfinite(t0):
                outputs |= transfer_per_window(read_watchintegral(wif), read_watchintegral(wis), Ff, t0, t2)
        return {"success": True, "message": f"uy(A) {wp[-1, 4] * 1e3:.4f} mm, drag {series['drag_N_per_m'][-1]:.3f} "
                f"N/m ({len(it)} windows, {outputs['coupling_iterations_mean']:.1f} iterations each)",
                "nfev": int(np.sum(it[:, 2])), "series": series, "outputs": outputs, "files": files(),
                "cleanup": work}

    def tool_versions(self):
        return self._versions


class TurekHronFSIStudy(Study):
    name = "turek_hron_fsi"
    models = {"openfoam_ccx_precice_fsi": PreciceFSI}
    metrics = frozenset(set(METRICS) | {m.replace("_m", "").replace("_N_per", "") + "_deviation_pct" for m in METRICS}
                        | set(PERIODIC_METRICS) | {f"{m}_deviation_pct" for m in PERIODIC_METRICS})
    param_names = _W.PARAMS + BENCH
    series_file = "history.csv"
    compare_description = "max relative difference of uy(A) over time"

    @staticmethod
    def _dev_name(metric):
        return metric.replace("_m", "").replace("_N_per", "") + "_deviation_pct"

    def derive(self, params):
        U, nu = _p(params, "mean_velocity_m_per_s"), _p(params, "kinematic_viscosity_m2_per_s")
        return {"reynolds_D": U * 2 * _W.R / nu,
                "mass_ratio": _p(params, "solid_density_kg_per_m3") / _p(params, "fluid_density_kg_per_m3")}

    def compute_metrics(self, series, params, case, outputs=None):
        n = case.get("numerics", {}).get("periodic_periods")
        if n:
            st = periodic_stats(series, int(n))
            out = {m: st[m] for m in PERIODIC_METRICS}
            out |= {m: float(np.asarray(series[m])[-1]) for m in METRICS}
            for q in PERIODIC_Q:
                bm, ba = _p(params, f"benchmark_{q}_mean"), _p(params, f"benchmark_{q}_amp")
                out[f"{q}_mean_deviation_pct"] = 100 * abs(st[f"{q}_mean"] - bm) / max(abs(bm), abs(ba))
                out[f"{q}_amp_deviation_pct"] = 100 * abs(st[f"{q}_amp"] - ba) / abs(ba)
                bf = _p(params, f"benchmark_{q}_freq_Hz")
                out[f"{q}_freq_Hz_deviation_pct"] = 100 * abs(st[f"{q}_freq_Hz"] - bf) / bf
            for m, b in zip(METRICS, BENCH):
                out[self._dev_name(m)] = float("nan")  # steady metrics do not apply to a periodic case
            return out
        w = case.get("numerics", {}).get("metric_average_s")
        if w:
            t = np.asarray(series["t_s"])
            tail = t >= t[-1] - float(w)
            out = {m: float(np.mean(np.asarray(series[m])[tail])) for m in METRICS}
        else:
            out = {m: float(np.asarray(series[m])[-1]) for m in METRICS}
        for m, b in zip(METRICS, BENCH):
            out[self._dev_name(m)] = 100 * abs(out[m] - _p(params, b)) / abs(_p(params, b))
        return out

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        p, d, out = point["parameters"], point["derived"], point["solver_outputs"]
        t = np.asarray(series["t_s"])
        tail = t >= t[-1] - tol.get("steady_window_s", 2.0)
        drift = tol.get("steady_measure") == "drift"
        n_per = case.get("numerics", {}).get("periodic_periods")
        if n_per:
            try:
                st = periodic_stats(series, int(n_per))
                steady = max(abs(st["uy_A_amp"] - st["uy_A_prev_amp"]) / abs(st["uy_A_amp"]),
                             abs(st["drag_mean"] - st["drag_prev_mean"]) / abs(st["drag_mean"]))
            except ValueError:
                steady = float("inf")
            steady_text = ("periodic state: max of |uy(A) amplitude, last period - the one before| / amplitude and the "
                           "same for the drag mean")
        elif drift:
            def change(x):
                h = len(x) // 2
                return abs(np.mean(x[h:]) - np.mean(x[:h])) / max(abs(np.mean(x)), 1e-30)
            steady = max(float(change(np.asarray(series[m])[tail])) for m in ("uy_A_m", "drag_N_per_m", "lift_N_per_m"))
            steady_text = (f"max over uy(A), drag, lift of the change of the mean between the two halves of the last "
                           f"{tol['steady_window_s']:g} s / mean (drift, not jitter)")
        else:
            steady = max(float(np.ptp(np.asarray(series[m])[tail]) / max(abs(np.asarray(series[m])[-1]), 1e-30))
                         for m in ("uy_A_m", "drag_N_per_m", "lift_N_per_m"))
            steady_text = f"max over uy(A), drag, lift of the spread over the last {tol['steady_window_s']:g} s / final value"
        means = "flag_fluid_force_mean_N" in out
        ff = np.array(out["flag_fluid_force_mean_N" if means else "flag_fluid_force_N"])
        rf = np.array(out["clamp_reaction_mean_N" if means else "clamp_reaction_N"])
        transfer = float(np.linalg.norm(ff + rf) / np.linalg.norm(ff))
        when = f"averaged over the last {out['metric_average_s']:g} s" if means else "at the end"
        if "transfer_mapping_max_rel" in out:
            # Window by window (preCICE watch-integrals): no inertia, valid for steady and periodic cases alike.
            transfer = max(out["transfer_mapping_max_rel"], out["transfer_fluid_max_rel"])
            when = (f"per coupling window over {out['transfer_from_s']:g}-{out['transfer_to_s']:g} s: the larger of "
                    "|force the solid receives - force the fluid writes| and |force the fluid writes - OpenFOAM's "
                    "force on the flag|, each over the largest force in the window")
        elif n_per and not means:
            # An accelerating flag's end-of-run balance includes its inertia, so it says nothing about the transfer.
            # Under the preCICE adapter CalculiX prints the clamp reaction only at the last increment (found
            # 2026-11-23, FSI2), so whole-period means cannot be formed: reported as not evaluable, never as a value.
            transfer = float("nan")
            when = ("over whole periods: NOT EVALUABLE, the solid's reaction is printed only at the last increment "
                    "under the preCICE adapter, and the end-of-run balance of an oscillating flag includes its inertia")
        checks = [
            check("mesh", "checkMesh reports Mesh OK (1 = failed)", 0.0 if out["mesh_ok"] else 1.0, 0.5),
            *([check("flag_cells", "largest interior angle (deg) of the fluid cells touching the flag, at "
                     f"({out['flag_cell_max_angle_at_m'][0]:.4f}, {out['flag_cell_max_angle_at_m'][1]:.4f}) m (a "
                     "cell wrapped around a tip corner reads near 180)", out["flag_cell_max_angle_deg"],
                     tol.get("flag_cell_max_angle_deg", 140.0))] if "flag_cell_max_angle_deg" in out else []),
            check("coupling_converged", "coupling windows that hit the iteration limit without converging",
                  float(out["windows_not_converged"]), 0.5),
            check("periodic" if n_per else "steady", steady_text, steady,
                  tol["periodic_rel_tol"] if n_per else tol["steady_rel_tol"]),
            check("force_transfer", (f"force transfer {when}" if "transfer_mapping_max_rel" in out else
                                      "|fluid force on the flag + clamp reaction in the solid| / |fluid force on the "
                                      f"flag| {when} (the coupling conserves force)"),
                  transfer, tol["force_transfer_rel_tol"]),
            check("inflow_profile", "max over inlet faces |U - benchmark parabola| / (1.5 U_mean), after the ramp",
                  out["inlet_profile_error_max"], tol["profile_rel_tol"]),
            check("laminar", "Reynolds number (D) / 200", d["reynolds_D"] / 200, 1.0, kind="validity"),
        ]
        fsi_figure(pdir / "response.png", series, p, title=f"{point['label']}  ({out['cells']} fluid cells, "
                   f"{out['windows']} windows, {out['coupling_iterations_mean']:.1f} coupling iterations each)",
                   periodic=bool(n_per))
        return checks

    def verify_run_level(self, case, manifest, points):
        # the refined parameter: the fluid cell size (mesh study) or the time step (time-step study; the same mesh on
        # every level, the fluid's backward and the solid's HHT alpha 0 both second order)
        par = case.get("sweep", {}).get("parameter")
        if par not in ("fluid_cell_size_m", "time_step_s"):
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: float(pt["parameters"][par]))
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(float(pt["parameters"][par]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
        # verification.mesh_noise_rel: the mesh-to-mesh scatter at one nominal size, measured independently
        # (regenerated, unstructured meshes; turek_hron_fsi1_noise_a-d), as one number or a table by metric. Three
        # levels spreading less than it are converged within the noise (uncertainty 1.25 x half the spread).
        noise = tol.get("mesh_noise_rel", 1e-5) if par == "fluid_cell_size_m" else tol.get("dt_noise_rel", 1e-5)
        periodic = bool(case.get("numerics", {}).get("periodic_periods"))
        for m in (PERIODIC_GCI_METRICS if periodic else METRICS):
            floor = float(noise.get(m, 1e-5) if isinstance(noise, dict) else noise)
            u = discretization_uncertainty(hs, tuple(pt["metrics"][m] for pt in fine), design_order=2,
                                           noise_floor=floor)
            detail[m] = u
            checks.append(check(f"discretization_{m}", f"relative discretization uncertainty of {m}, {describe(u)}",
                                u["uncertainty"], tol["gci_max"]) | {"metric": f"{m}_deviation_pct" if periodic
                                                                      else self._dev_name(m)})
        return checks, detail


def fsi_figure(path, series, p, *, title, periodic=False):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, _style, plt

    t = np.asarray(series["t_s"])
    fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=True)
    fig.patch.set_facecolor(SURFACE)
    rows = ((axes[0], "uy_A_m", "benchmark_uy_A_m", "uy(A) (mm)", 1e3), (axes[1], "drag_N_per_m",
            "benchmark_drag_N_per_m", "drag (N/m)", 1.0), (axes[2], "lift_N_per_m", "benchmark_lift_N_per_m",
            "lift (N/m)", 1.0))
    for ax, key, bkey, lab, s in rows:
        ax.plot(t, np.asarray(series[key]) * s, color=SERIES_1, lw=1.2, label="OpenFOAM + CalculiX (preCICE)")
        q = {"uy_A_m": "uy_A", "drag_N_per_m": "drag", "lift_N_per_m": "lift"}[key]
        if f"benchmark_{q}_amp" in p and periodic:
            m, a = _p(p, f"benchmark_{q}_mean"), _p(p, f"benchmark_{q}_amp")
            ax.axhline((m + a) * s, color=SERIES_2, lw=1.5, ls="--", label="Turek-Hron: mean +- amplitude")
            ax.axhline((m - a) * s, color=SERIES_2, lw=1.5, ls="--")
        else:
            ax.axhline(_p(p, bkey) * s, color=SERIES_2, lw=2, ls="--", label="Turek-Hron (steady)")
        ax.set_ylabel(lab)
        _style(ax)
    axes[0].legend(frameon=False, fontsize=8)
    axes[2].set_xlabel("time (s)")
    fig.suptitle(title, fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = TurekHronFSIStudy()

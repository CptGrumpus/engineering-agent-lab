"""Study 19, part 1: fully developed turbulent pipe flow with RANS (OpenFOAM, k-omega SST), friction factor.

Model:     openfoam_pipe_rans (models/cfd/pipe_openfoam.py, run_pipe.sh): an axisymmetric wedge, streamwise periodic,
           driven at a fixed bulk velocity (meanVelocityForce); low-Reynolds wall treatment (y+ about 1) or wall
           functions (first cell in the log layer)
Reference: the smooth-pipe friction law of Prandtl, 1/sqrt(f) = 2.0 log10(Re sqrt(f)) - 0.8 (fitted to Nikuradse's
           measurements; the basis of the Moody chart's smooth curve), with Blasius (Re <= 1e5) and Petukhov beside it;
           checks: the exact force balance of periodic flow (wall shear against the applied pressure gradient: two
           routes to the friction factor), the bulk velocity held, iterative convergence of the gradient, the
           first-cell y+ inside the treatment's range (validity), and the mean velocity against the log law (model
           form). No closed form for turbulent flow: this is validation of the model against measured correlations.
Run-level: GCI on the friction factor in a mesh study (verification.mesh_study; scenarios refine n_radial and the
           first-cell y+ together).

Geometry note: the wedge's wall is a flat face at R cos(a) (a = 2.5 deg), so the hydraulic diameter is 2 R cos(a)
(0.1 % below D): the friction factor and Reynolds number use it.
"""

from __future__ import annotations

import importlib.util
import math
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness import openfoam as of
from harness.backend_base import Backend, failed
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study

WRITER = "models/cfd/pipe_openfoam.py"
RUNNER = "models/cfd/run_pipe.sh"
_GRAD = re.compile(r"uncorrected Ubar = ([-+0-9.eE]+), pressure gradient = ([-+0-9.eE]+)")
KAPPA, B_LOG = 0.41, 5.2


def _load(path: Path):
    spec = importlib.util.spec_from_file_location("pipe_openfoam_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_W = _load(Path(__file__).resolve().parent.parent / WRITER)
PARAMS = _W.PARAMS


def f_prandtl(re_):
    return _W.friction_prandtl(re_)


def f_blasius(re_):
    return 0.3164 * re_ ** -0.25


def f_petukhov(re_):
    return (0.790 * math.log(re_) - 1.64) ** -2


class OpenFOAMPipe(Backend):
    sources = (WRITER, RUNNER)

    def __init__(self):
        self.bashrc = of.find_openfoam_bashrc()
        self._versions: dict = {"openfoam_bashrc": self.bashrc}

    def prepare(self, source_dir=None, log_dir=None):
        self.writer = _load(self.source_path(WRITER, source_dir))
        self.runner = self.source_path(RUNNER, source_dir)

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="of_pipe_"))
        case = work / "case"
        info = self.writer.write_case(params, numerics, case)
        r = subprocess.run(of.wsl_command("bash", of.to_wsl_path(self.runner), of.to_wsl_path(case), self.bashrc),
                           capture_output=True, text=True, timeout=float(numerics.get("solver_timeout_s", 7200)))
        files = {str(f.relative_to(case)).replace("\\", "/"): f
                 for f in sorted(case.glob("system/*")) + sorted(case.glob("constant/*")) + sorted(case.glob("0/*"))
                 + sorted(case.glob("log.*")) + sorted(case.glob("versions.txt"))
                 + sorted(case.glob("postProcessing/*/0/*.dat")) if f.is_file() and f.stat().st_size < 5e6}
        if r.returncode != 0:
            return failed(f"OpenFOAM stage failed (exit {r.returncode}) {r.stderr.strip()[:300]}") | {
                "files": files, "cleanup": work}
        for line in (case / "versions.txt").read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition("=")
            self._versions[k] = v
        text = (case / "log.foamRun").read_text(encoding="utf-8", errors="replace")
        grads = np.array([float(g) for _, g in _GRAD.findall(text)])
        if not len(grads):
            return failed("meanVelocityForce reported no pressure gradient") | {"files": files, "cleanup": work}
        tail = grads[-max(2, len(grads) // 10):]
        grad_change = float(np.max(np.abs(tail - grads[-1])) / abs(grads[-1]))
        wss = [ln.split("\t") for ln in (case / "postProcessing/wallShearStress/0/wallShearStress.dat").read_text(
            encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
        tau = abs(float(wss[-1][2].strip().strip("()").split()[0]))  # min over the wall (uniform), x component
        tau_max = abs(float(wss[-1][3].strip().strip("()").split()[0]))
        yp = [ln.split() for ln in (case / "postProcessing/yPlus/0/yPlus.dat").read_text(encoding="utf-8").splitlines()
              if ln.strip() and not ln.startswith("#")]
        yp_min, yp_max, yp_avg = (float(v) for v in yp[-1][2:5])
        log = of.read_solver_log(case / "log.foamRun")
        tdir = of.latest_time_dir(case)
        n = int(params["n_radial"]) * int(numerics.get("axial_cells", 1))
        C = of.read_internal_field(tdir / "C", n)
        U = of.read_internal_field(tdir / "U", n)
        a = math.radians(_W.WEDGE_HALF_ANGLE_DEG)
        R = info["R_m"]
        Rw = R * math.cos(a)  # the wedge wall's distance from the axis
        r = np.hypot(C[:, 1], C[:, 2])
        o = np.argsort(r)
        series = {"r_m": r[o], "u_m_per_s": U[o, 0]}
        # bulk velocity of the cell field, volume-weighted (what meanVelocityForce holds)
        V = of.read_internal_field(tdir / "Vc", n)  # openfoam.org v14 names the cell-volume field Vc
        ub_field = float(np.sum(U[:, 0] * V) / np.sum(V))
        outputs = {**info, "Rw_m": Rw, "D_h_m": 2 * Rw, "iterations": log["iterations"],
                   "final_initial_residuals": log["final_initial_residuals"],
                   "pressure_gradient_kin": float(grads[-1]), "pressure_gradient_change_last_10pct": grad_change,
                   "tau_wall_kin": tau, "tau_wall_spread": abs(tau_max - tau) / tau, "yplus_min": yp_min,
                   "yplus_max": yp_max, "yplus_avg": yp_avg, "bulk_velocity_field_m_per_s": ub_field,
                   "mesh_ok": "Mesh OK." in (case / "log.checkMesh").read_text(encoding="utf-8")}
        return {"success": True, "message": f"foamRun: {log['iterations']} iterations, f from wall shear "
                f"{8 * tau / info['Ub_m_per_s'] ** 2:.5f}, y+ {yp_avg:.2f}", "nfev": log["iterations"],
                "series": series, "outputs": outputs, "files": files, "cleanup": work}

    def tool_versions(self):
        return self._versions


class PipeFlowStudy(Study):
    name = "pipe_flow"
    models = {"openfoam_pipe_rans": OpenFOAMPipe}
    metrics = frozenset({"friction_factor", "friction_dev_prandtl_pct", "friction_abs_dev_prandtl_pct", "friction_dev_petukhov_pct",
                         "friction_dev_blasius_pct", "reynolds_Dh", "yplus_first_cell", "log_law_error_max"})
    param_names = PARAMS
    series_file = "profile.csv"
    compare_description = "max relative difference of the velocity profile"

    def derive(self, params):
        re_ = float(params["reynolds_number"])
        if re_ < 4000 or params["wall_treatment"] not in ("low_re", "wall_function"):
            raise ValueError("turbulent Reynolds number and wall_treatment low_re or wall_function")
        return {"friction_prandtl": f_prandtl(re_), "friction_petukhov": f_petukhov(re_),
                "friction_blasius": f_blasius(re_)}

    def compute_metrics(self, series, params, case, outputs=None):
        Ub, nu, Dh = outputs["Ub_m_per_s"], outputs["nu_m2_per_s"], outputs["D_h_m"]
        re_h = Ub * Dh / nu
        f = 8 * outputs["tau_wall_kin"] / Ub ** 2
        out = {"friction_factor": f, "reynolds_Dh": re_h, "yplus_first_cell": outputs["yplus_avg"],
               "friction_dev_prandtl_pct": 100 * (f / f_prandtl(re_h) - 1),
               "friction_abs_dev_prandtl_pct": 100 * abs(f / f_prandtl(re_h) - 1),
               "friction_dev_petukhov_pct": 100 * (f / f_petukhov(re_h) - 1),
               "friction_dev_blasius_pct": 100 * (f / f_blasius(re_h) - 1) if re_h <= 1.2e5 else float("nan")}
        out["log_law_error_max"] = log_law_error(series, outputs)
        return out

    def verify_point(self, case, point, pdir, series, backend):
        tol = case["verification"]
        p, out, m = point["parameters"], point["solver_outputs"], point["metrics"]
        Ub, Dh = out["Ub_m_per_s"], out["D_h_m"]
        f_dp = 2 * Dh * out["pressure_gradient_kin"] / Ub ** 2
        low = p["wall_treatment"] == "low_re"
        yp_ok = out["yplus_max"] / tol["yplus_max_low_re"] if low else max(
            tol["yplus_min_wall_function"] / out["yplus_min"], out["yplus_max"] / tol["yplus_max_wall_function"])
        checks = [
            check("mesh", "checkMesh reports Mesh OK (1 = failed)", 0.0 if out["mesh_ok"] else 1.0, 0.5),
            check("force_balance", "|f from the wall shear - f from the applied pressure gradient| / f (periodic flow: "
                  "dp/dx A = tau_w P exactly)", abs(m["friction_factor"] - f_dp) / f_dp, tol["force_balance_rel_tol"]),
            check("bulk_velocity", "|bulk velocity of the cell field - target| / target",
                  abs(out["bulk_velocity_field_m_per_s"] - Ub) / Ub, tol["bulk_velocity_rel_tol"]),
            check("iterative_convergence", "max change of the pressure gradient over the last 10 % of iterations / "
                  "final", out["pressure_gradient_change_last_10pct"], tol["iterative_rel_tol"]),
            check("wall_uniform", "spread of the wall shear along the wall / mean (fully developed: 0)",
                  out["tau_wall_spread"], tol["force_balance_rel_tol"]),
            check("yplus_range", "first-cell y+ against the wall treatment's range (below 1 = inside)", yp_ok, 1.0,
                  kind="validity"),
            check("log_law", f"max |u+ - (ln y+ / {KAPPA} + {B_LOG})| / u+ for 50 <= y+ <= 0.15 Re_tau (model form: "
                  "the log law's constants scatter by a few per cent between experiments)", m["log_law_error_max"],
                  tol["log_law_rel_tol"]),
        ]
        pipe_figure(pdir / "response.png", series, out, point)
        return checks

    def verify_run_level(self, case, manifest, points):
        # a mesh study: the sweep varies n_radial, directly or through scenarios (n_radial and first_cell_yplus
        # together, so the whole grid is refined, not only the core), with verification.mesh_study = true
        if not case["verification"].get("mesh_study"):
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: -int(pt["parameters"]["n_radial"]))
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(1.0 / int(pt["parameters"]["n_radial"]) for pt in fine)
        vals = tuple(pt["metrics"]["friction_factor"] for pt in fine)
        u = discretization_uncertainty(hs, vals, design_order=2, noise_floor=tol.get("mesh_noise_rel", 1e-6))
        return [check("discretization_friction_factor", f"relative discretization uncertainty of the friction factor, "
                      f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": "friction_factor"}], {
            "friction_factor": u}


def log_law_error(series, out):
    nu, tau = out["nu_m2_per_s"], out["tau_wall_kin"]
    u_tau = math.sqrt(tau)
    y = out["Rw_m"] - np.asarray(series["r_m"])
    yp = y * u_tau / nu
    re_tau = out["Rw_m"] * u_tau / nu
    sel = (yp >= 50) & (yp <= 0.15 * re_tau)
    if not sel.any():
        return float("nan")
    up = np.asarray(series["u_m_per_s"])[sel] / u_tau
    return float(np.max(np.abs(up - (np.log(yp[sel]) / KAPPA + B_LOG)) / up))


def pipe_figure(path, series, out, point):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, _style, plt

    nu, u_tau = out["nu_m2_per_s"], math.sqrt(out["tau_wall_kin"])
    y = out["Rw_m"] - np.asarray(series["r_m"])
    yp, up = y * u_tau / nu, np.asarray(series["u_m_per_s"]) / u_tau
    fig, ax = plt.subplots(figsize=(7, 4.5))
    fig.patch.set_facecolor(SURFACE)
    ax.semilogx(yp, up, "o", ms=3, color=SERIES_1, label="RANS (cell centres)")
    g = np.logspace(-1, math.log10(max(yp.max(), 10)), 200)
    ax.semilogx(g[g <= 5], g[g <= 5], "-", color=SERIES_2, lw=1, label="u+ = y+")
    ax.semilogx(g[g >= 30], np.log(g[g >= 30]) / KAPPA + B_LOG, "--", color=SERIES_2, lw=1,
                label=f"log law (kappa {KAPPA}, B {B_LOG})")
    ax.set_xlabel("y+")
    ax.set_ylabel("u+")
    ax.legend(frameon=False, fontsize=8)
    _style(ax)
    fig.suptitle(f"{point['label']}: mean velocity in wall units", fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = PipeFlowStudy()

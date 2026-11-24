"""Study 11, stage 1: natural convection in a differentially heated square cavity against de Vahl Davis (1983).

Model:     openfoam_cavity (models/cfd/cavity_openfoam.py, run by models/cfd/run_cavity.sh): OpenFOAM 14 `foamRun
           -solver fluid`, steady, laminar, Boussinesq equation of state with beta dT = 3.3e-4, Ra set through g.
Metrics:   the hot wall's average Nusselt number (from the temperature field: a second-order one-sided gradient at
           the wall, area-weighted with the exact cell heights; OpenFOAM's wallHeatFlux reports a conductivity 1.33 x
           mu Cp / Pr for this thermo setup, so it is not used), u_max on the vertical mid-plane and w_max on the
           horizontal mid-plane (the two central columns / rows averaged, the mesh having an even cell count; a
           parabola through the three points round the peak), all non-dimensional (velocity scale kappa / L).
Reference: de Vahl Davis (1983) Table V (validation/natural_convection.py); energy balance hot wall against cold wall;
           the solver's final residuals; Boussinesq validity (beta dT).
Run-level: GCI on the requirement metrics when the sweep is the cell count (h = 1 / cells).
"""

from __future__ import annotations

import importlib.util
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
from validation import natural_convection as ref

WRITER = "models/cfd/cavity_openfoam.py"
RUNNER = "models/cfd/run_cavity.sh"


def _load_writer(path: Path):
    spec = importlib.util.spec_from_file_location("cavity_openfoam_saved", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_W = _load_writer(Path(__file__).resolve().parent.parent / WRITER)


def _edges(centres: np.ndarray) -> np.ndarray:
    """Cell edges from cell centres of a blockMesh-graded line starting at 0 (each centre is its cell's midpoint)."""
    e = [0.0]
    for c in centres:
        e.append(2 * c - e[-1])
    return np.array(e)


def _peak(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Largest (signed) y and its position, refined by a parabola through the three points round the sampled maximum.
    Signed: the flow is centro-symmetric, so the largest |u| at the bottom ties with de Vahl Davis's at the top."""
    k = int(np.argmax(y))
    if 0 < k < len(y) - 1:
        a, b, c = np.polyfit(x[k - 1:k + 2], y[k - 1:k + 2], 2)
        if a < 0:
            xm = -b / (2 * a)
            if x[k - 1] <= xm <= x[k + 1]:
                return float(np.polyval([a, b, c], xm)), float(xm)
    return float(y[k]), float(x[k])


def postprocess(C: np.ndarray, T: np.ndarray, U: np.ndarray, p: dict) -> dict:
    L, dT, Th, Tc, kap = p["L"], p["dT"], p["Th"], p["Tc"], p["kappa"]
    xs = np.unique(np.round(C[:, 0], 12))
    ys = np.unique(np.round(C[:, 1], 12))
    n = len(xs)
    ix = {v: i for i, v in enumerate(xs)}
    iy = {v: i for i, v in enumerate(ys)}
    Tg = np.zeros((n, len(ys)))
    Ug = np.zeros((n, len(ys), 2))
    for (x, y), t, u in zip(np.round(C[:, :2], 12), T, U):
        Tg[ix[x], iy[y]] = t
        Ug[ix[x], iy[y]] = u[:2]
    hy = np.diff(_edges(ys))

    def wall_nu(T1, T2, x1, x2, Tw, sign):
        a = -(x1 + x2) / (x1 * x2)
        b = x2 / (x1 * (x2 - x1))
        c = -x1 / (x2 * (x2 - x1))
        dTdn = a * Tw + b * T1 + c * T2                               # derivative along the inward normal
        return float(sign * np.sum(dTdn * hy) / L * L / dT)

    nu_hot = wall_nu(Tg[0], Tg[1], xs[0], xs[1], Th, -1.0)
    nu_cold = wall_nu(Tg[-1], Tg[-2], L - xs[-1], L - xs[-2], Tc, 1.0)
    m = n // 2
    u_mid = 0.5 * (Ug[m - 1, :, 0] + Ug[m, :, 0])                     # vertical mid-plane x = L / 2
    w_mid = 0.5 * (Ug[:, m - 1, 1] + Ug[:, m, 1])                     # horizontal mid-plane z = L / 2
    u_max, z_u = _peak(ys / L, u_mid * L / kap)
    w_max, x_w = _peak(xs / L, w_mid * L / kap)
    return {"Nu_hot": nu_hot, "Nu_cold": nu_cold, "u_max": u_max, "u_max_z": z_u, "w_max": w_max, "w_max_x": x_w,
            "profile_z": (ys / L).tolist(), "profile_u": (u_mid * L / kap).tolist(),
            "profile_x": (xs / L).tolist(), "profile_w": (w_mid * L / kap).tolist()}


def final_residuals(log: str) -> dict:
    out = {}
    for f in ("Ux", "Uy", "h", "p_rgh"):
        v = re.findall(rf"Solving for {f}, Initial residual = ([-+0-9.eE]+)", log)
        if v:
            out[f] = float(v[-1])
    out["iterations"] = len(re.findall(r"^Time = ", log, re.M))
    return out


class OpenFOAMCavity(Backend):
    sources = (WRITER, RUNNER)

    def __init__(self):
        self.bashrc = of.find_openfoam_bashrc()
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        self.writer = _load_writer(self.source_path(WRITER, source_dir))
        self.runner = self.source_path(RUNNER, source_dir)

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="cavity_"))
        case = work / "case"

        def files():
            keep = [case / n for n in ("log.blockMesh", "log.checkMesh", "log.foamRun", "log.wallHeatFlux", "versions.txt")]
            keep += sorted((case / "system").glob("*")) + sorted((case / "constant").glob("*"))
            return {str(f.relative_to(case)).replace("\\", "/"): f for f in keep if f.is_file() and f.stat().st_size < 20e6}

        try:
            info = self.writer.write_case(params, numerics, case)
            r = subprocess.run(of.wsl_command("bash", of.to_wsl_path(self.runner), of.to_wsl_path(case), self.bashrc),
                               capture_output=True, text=True, timeout=float(numerics.get("solver_timeout_s", 14400)))
            if r.returncode != 0:
                res = failed(f"cavity run failed (exit {r.returncode}) {r.stderr.strip()[-300:]}")
                res.update(files=files(), cleanup=work)
                return res
            t = of.latest_time_dir(case)
            C = of.read_internal_field(t / "C")
            T = of.read_internal_field(t / "T")
            U = of.read_internal_field(t / "U")
            p = self.writer.properties(params)
            post = postprocess(C, T, U, p)
            res_ = final_residuals((case / "log.foamRun").read_text(encoding="utf-8", errors="replace"))
            for line in (case / "versions.txt").read_text(encoding="utf-8").splitlines():
                k, _, v = line.partition("=")
                self._versions[k] = v
        except Exception as e:  # noqa: BLE001
            res = failed(f"{type(e).__name__}: {e}")
            res.update(files=files(), cleanup=work)
            return res
        series = {"z": np.array(post["profile_z"]), "u_mid": np.array(post["profile_u"])}
        outputs = {**info, **{k: v for k, v in post.items() if not k.startswith("profile_")},
                   "profile_x": post["profile_x"], "profile_w": post["profile_w"], "residuals": res_,
                   "beta_dT": _W.BETA * p["dT"]}
        return {"success": True, "message": f"cavity: {info['cells']} cells, Nu {post['Nu_hot']:.4f}", "nfev": None,
                "series": series, "outputs": outputs, "files": files(), "cleanup": work}

    def tool_versions(self):
        return dict(self._versions)


class CavityConvectionStudy(Study):
    name = "cavity_convection"
    models = {"openfoam_cavity": OpenFOAMCavity}
    metrics = frozenset({"Nu_hot", "u_max", "w_max", "Nu_deviation_pct", "u_max_deviation_pct", "w_max_deviation_pct"})
    param_names = _W.PARAMS
    series_file = "midplane_u.csv"
    compare_description = "max relative difference in the mid-plane velocity profile"

    def derive(self, params):
        ra = float(params["rayleigh"])
        if ra not in ref.DE_VAHL_DAVIS:
            raise ValueError(f"Ra {ra:g} is not a de Vahl Davis bench mark value")
        return {"g_m_per_s2": _W.properties(params)["g"]}

    def compute_metrics(self, series, params, case, outputs=None):
        b = ref.DE_VAHL_DAVIS[float(params["rayleigh"])]
        dev = lambda v, r: 100 * abs(v - r) / r  # noqa: E731
        return {"Nu_hot": outputs["Nu_hot"], "u_max": outputs["u_max"], "w_max": outputs["w_max"],
                "Nu_deviation_pct": dev(outputs["Nu_hot"], b["Nu_0"]),
                "u_max_deviation_pct": dev(outputs["u_max"], b["u_max"]),
                "w_max_deviation_pct": dev(outputs["w_max"], b["w_max"])}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        out = point["solver_outputs"]
        res = out["residuals"]
        worst = max(res.get(k, 1.0) for k in ("Ux", "Uy", "h"))
        checks = [
            check("energy_balance", "|hot-wall Nu - cold-wall Nu| / hot-wall Nu (steady: the heat in leaves)",
                  abs(out["Nu_hot"] - out["Nu_cold"]) / out["Nu_hot"], tol["energy_balance_rel_tol"]),
            check("converged", "largest final initial residual of U and h", worst, tol["residual_max"]),
            check("boussinesq", "beta x temperature difference (OpenFOAM's Boussinesq density enters every term; "
                  "validity)", out["beta_dT"], tol["beta_dT_max"], kind="validity"),
        ]
        cavity_figure(pdir / "response.png", point, out)
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "cells":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: -float(pt["parameters"]["cells"]))
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(1.0 / float(pt["parameters"]["cells"]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
        for m in ("Nu_hot", "u_max", "w_max"):
            u = discretization_uncertainty(hs, tuple(pt["metrics"][m] for pt in fine), design_order=2)
            detail[m] = u
            checks.append(check(f"discretization_{m}", f"relative discretization uncertainty of {m}, {describe(u)}",
                                u["uncertainty"], tol["gci_max"])
                          | {"metric": {"Nu_hot": "Nu_deviation_pct", "u_max": "u_max_deviation_pct",
                                        "w_max": "w_max_deviation_pct"}[m]})
        return checks, detail


def cavity_figure(path, point, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from harness.plotting import GRID, SERIES_1, SERIES_2, SURFACE, TEXT

    b = ref.DE_VAHL_DAVIS[float(point["parameters"]["rayleigh"])]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2), facecolor=SURFACE)
    ax1.plot(np.array(out["profile_x"]), np.array(out["profile_w"]), color=SERIES_1, lw=1.8, label="OpenFOAM")
    ax1.plot([b["w_max_x"]], [b["w_max"]], "o", color=SERIES_2, label="de Vahl Davis w_max")
    ax1.set_xlabel("x / L (horizontal mid-plane)", color=TEXT)
    ax1.set_ylabel("w L / kappa", color=TEXT)
    ax2.bar(["Nu", "u_max", "w_max"], [point["metrics"]["Nu_deviation_pct"], point["metrics"]["u_max_deviation_pct"],
                                       point["metrics"]["w_max_deviation_pct"]], color=SERIES_1)
    ax2.set_ylabel("|deviation| from de Vahl Davis (%)", color=TEXT)
    for ax in (ax1, ax2):
        ax.set_facecolor(SURFACE)
        ax.grid(color=GRID, lw=0.5)
        ax.tick_params(colors=TEXT)
    ax1.legend()
    fig.suptitle(point["label"], color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=110, facecolor=SURFACE)
    plt.close(fig)


STUDY = CavityConvectionStudy()

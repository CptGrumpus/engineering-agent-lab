"""Study G: rotor critical speeds and unbalance response of a fan rotor, ROSS 3.1.

Model:     ross_rotor (models/rotor/fan_rotor.py, run in its own environment ~/.venvs/ross like Pyleecan's): Timoshenko
           shaft elements, a rigid disc at mid-span, two linear bearings; Campbell diagram, critical speeds as the
           1x crossings, unbalance response with API 684's unbalance
Reference: three closed forms on companion models (Jeffcott rotor, Jeffcott on the case's bearings as series springs,
           the bare shaft pinned-pinned against Euler-Bernoulli); ROSS's own critical-speed search against the
           Campbell crossings
Run-level: GCI on the requirement metrics and the first forward critical speed when the sweep is n_elements
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness.backend_base import Backend, failed
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study

RUNNER = "models/rotor/fan_rotor.py"
PARAMS = ("density_kg_per_m3", "youngs_modulus_Pa", "poisson_ratio", "n_elements", "bearing_span_m",
          "shaft_diameter_m", "disc_width_m", "disc_diameter_m", "bearing_stiffness_N_per_m",
          "bearing_damping_Ns_per_m", "speed_min_rpm", "speed_max_rpm", "campbell_max_rpm", "campbell_points", "modes",
          "response_points")


def ross_python() -> Path:
    p = Path(os.environ.get("ROSS_PYTHON", Path.home() / ".venvs" / "ross" / "Scripts" / "python.exe"))
    if not p.exists():
        raise RuntimeError(f"ROSS environment not found at {p} (python -m venv ~/.venvs/ross; pip install "
                           "ross-rotordynamics==3.1.0)")
    return p


class RossRotor(Backend):
    sources = (RUNNER,)

    def __init__(self):
        self.python = ross_python()
        self.runner = None
        self._versions: dict = {}

    def prepare(self, source_dir=None, log_dir=None):
        self.runner = self.source_path(RUNNER, source_dir)
        r = subprocess.run([str(self.python), "-c", "import warnings; warnings.filterwarnings('ignore'); import ross, "
                            "numpy, scipy; print(ross.__version__, numpy.__version__, scipy.__version__)"],
                           capture_output=True, text=True, timeout=300)
        v = (r.stdout.strip().splitlines() or ["? ? ?"])[-1].split() + ["?"] * 3
        self._versions = {"ross": v[0], "numpy_ross_env": v[1], "scipy_ross_env": v[2]}

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="rotor_"))
        # the optional detail (hub, journals; study 23 part 2) goes to ROSS when the case gives it
        opt = {k: params[k] for k in ("hub_diameter_m", "hub_length_m", "journal_diameter_m", "journal_length_m")
               if params.get(k) not in (None, "", 0, 0.0)}
        (work / "params.json").write_text(json.dumps({k: params[k] for k in PARAMS} | opt), encoding="utf-8")
        r = subprocess.run([str(self.python), str(self.runner), "params.json", "out.json"], cwd=work,
                           capture_output=True, text=True, timeout=float(numerics.get("solver_timeout_s", 1800)))
        # ROSS's import prints a warning about an optional fluid-property library (REFPROP); keep only the rest
        log = "\n".join(ln for ln in (r.stdout + r.stderr).splitlines() if "refprop" not in ln.lower())
        (work / "runner.log").write_text(log, encoding="utf-8")
        files = {f.name: f for f in (work / "params.json", work / "runner.log") if f.exists()}
        if r.returncode != 0 or not (work / "out.json").exists():
            return failed(f"ROSS runner failed (exit {r.returncode}): {log.strip()[-300:]}") | {"files": files,
                                                                                               "cleanup": work}
        d = json.loads((work / "out.json").read_text(encoding="utf-8"))
        series = {"speed_rpm": np.array(d["response_rpm"]), "disc_amp_x_m": np.array(d["disc_amp_x_m"]),
                  "disc_amp_y_m": np.array(d["disc_amp_y_m"])}
        outputs = {k: d[k] for k in ("rotor_mass_kg", "disc_mass_kg", "unbalance_g_mm", "campbell_rpm",
                                     "campbell_wd_rpm", "campbell_whirl", "critical_speeds", "ross_critical_speeds",
                                     "ref", "wall_s")}
        return {"success": True, "message": f"{len(d['critical_speeds'])} 1x crossings, {d['wall_s']:.1f} s",
                "nfev": None, "series": series, "outputs": outputs, "files": files, "cleanup": work}

    def tool_versions(self):
        return self._versions


def separation_margin_pct(n_c: float, n_min: float, n_max: float) -> float:
    """API-style separation of one critical speed from the operating range, % (negative inside the range)."""
    if n_c < n_min:
        return 100 * (n_min - n_c) / n_min
    if n_c > n_max:
        return 100 * (n_c - n_max) / n_max
    return -100 * min((n_c - n_min) / n_min, (n_max - n_c) / n_max)


def _forward(crit):
    return [c for c in crit if c["whirl"] != "backward"]


class RotorCriticalStudy(Study):
    name = "rotor_critical"
    models = {"ross_rotor": RossRotor}
    metrics = frozenset({"first_forward_critical_rpm", "separation_margin_pct", "unbalance_amp_max_um",
                         "rotor_mass_kg"})
    param_names = PARAMS
    series_file = "unbalance_response.csv"
    compare_description = "max relative difference of the disc's unbalance response"

    def derive(self, params):
        if int(params["n_elements"]) % 2:
            raise ValueError("n_elements must be even (the disc sits on the mid-span node)")
        if not 0 < float(params["speed_min_rpm"]) < float(params["speed_max_rpm"]) < float(params["campbell_max_rpm"]):
            raise ValueError("need 0 < speed_min < speed_max < campbell_max")
        return {}

    def compute_metrics(self, series, params, case, outputs=None):
        n_min, n_max = float(params["speed_min_rpm"]), float(params["speed_max_rpm"])
        fwd = _forward(outputs["critical_speeds"])
        margins = [separation_margin_pct(c["rpm"], n_min, n_max) for c in fwd]
        amp = np.maximum(np.asarray(series["disc_amp_x_m"]), np.asarray(series["disc_amp_y_m"]))
        return {"first_forward_critical_rpm": fwd[0]["rpm"] if fwd else float("inf"),
                "separation_margin_pct": min(margins) if margins else float("inf"),
                "unbalance_amp_max_um": float(amp.max() * 1e6), "rotor_mass_kg": float(outputs["rotor_mass_kg"])}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        p, out = point["parameters"], point["solver_outputs"]
        ref = out["ref"]
        rel = lambda a, b: abs(a - b) / abs(b)  # noqa: E731
        fwd = _forward(out["critical_speeds"])
        ross_fwd = [c["rpm"] for c in out["ross_critical_speeds"] if c.get("whirl") == "forward"]
        if fwd and ross_fwd:
            cross = min(rel(fwd[0]["rpm"], r) for r in ross_fwd)
        else:
            cross = float("inf")
        speeds = np.asarray(out["campbell_rpm"])
        checks = [
            check("jeffcott", "Jeffcott rotor (massless shaft, rigid supports, central disc): |ROSS - sqrt(48 EI / m "
                  "L^3)| / closed form (model form: shear deformation, the disc's width)",
                  rel(ref["jeffcott_ross_rpm"], ref["jeffcott_cf_rpm"]), tol["closed_form_rel_tol"]),
            check("series_bearings", "Jeffcott rotor on the case's bearings: |ROSS - closed form with the shaft and two "
                  "bearings as springs in series| / closed form", rel(ref["series_ross_rpm"], ref["series_cf_rpm"]),
                  tol["closed_form_rel_tol"]),
            check("bare_shaft", "bare shaft on rigid supports, first bending: |ROSS (Timoshenko) - Euler-Bernoulli "
                  "pinned-pinned| / Euler-Bernoulli", rel(ref["bare_ross_rpm"], ref["bare_cf_rpm"]),
                  tol["closed_form_rel_tol"]),
            check("critical_crosscheck", "|first forward 1x crossing of the Campbell diagram - ROSS's own critical "
                  "speed search| / ROSS's", cross, tol["crossing_rel_tol"]),
            check("campbell_resolution", "Campbell speed step / first forward critical speed (below the tolerance: "
                  "the crossing is resolved)", float(np.diff(speeds).max()) / (fwd[0]["rpm"] if fwd else 1.0),
                  tol["campbell_step_max_rel"], kind="validity"),
        ]
        rotor_figure(pdir / "response.png", series, out, p, title=point["label"])
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "n_elements":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: -int(float(pt["parameters"]["n_elements"])))
        if len(done) < 3:
            return [check("element_convergence_gci", "needs >= 3 completed element counts", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(1.0 / float(pt["parameters"]["n_elements"]) for pt in fine)
        checks, detail = [], {"levels_used": [pt["label"] for pt in fine]}
        for metric in ("first_forward_critical_rpm", "unbalance_amp_max_um"):
            u = discretization_uncertainty(hs, tuple(pt["metrics"][metric] for pt in fine), design_order=2,
                                           noise_floor=tol.get("noise_rel", 1e-6))
            detail[metric] = u
            checks.append(check(f"discretization_{metric}", f"relative discretization uncertainty of {metric}, "
                                f"{describe(u)}", u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


def rotor_figure(path, series, out, p, *, title):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2, _style, plt

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
    fig.patch.set_facecolor(SURFACE)
    sp = np.asarray(out["campbell_rpm"])
    wd = np.asarray(out["campbell_wd_rpm"])
    wh = np.asarray(out["campbell_whirl"])
    for j in range(wd.shape[1]):
        fwd = wh[:, j] < 0.5
        a1.plot(sp[fwd], wd[fwd, j], ".", color=SERIES_1, ms=3, label="forward whirl" if j == 0 else None)
        a1.plot(sp[~fwd], wd[~fwd, j], ".", color=SERIES_2, ms=3, label="backward whirl" if j == 0 else None)
    a1.plot(sp, sp, color=TEXT, lw=0.8, label="1x running speed")
    a1.axvspan(float(p["speed_min_rpm"]), float(p["speed_max_rpm"]), color=TEXT_2, alpha=0.15, label="operating range")
    for c in out["critical_speeds"]:
        a1.plot(c["rpm"], c["rpm"], "o", mfc="none", color=TEXT, ms=7)
    a1.set_ylim(0, sp.max() * 1.5)
    a1.set_xlabel("speed (rpm)")
    a1.set_ylabel("natural frequency (rpm)")
    a1.legend(frameon=False, fontsize=8)
    s = np.asarray(series["speed_rpm"])
    a2.plot(s, np.asarray(series["disc_amp_x_m"]) * 1e6, color=SERIES_1, lw=1.4, label="disc, x")
    a2.plot(s, np.asarray(series["disc_amp_y_m"]) * 1e6, color=SERIES_2, lw=1.0, ls="--", label="disc, y")
    a2.set_xlabel("speed (rpm)")
    a2.set_ylabel("disc response, 0-peak (um)")
    a2.set_title(f"API 684 unbalance {out['unbalance_g_mm']:.0f} g mm", fontsize=9, color=TEXT_2)
    a2.legend(frameon=False, fontsize=8)
    for ax in (a1, a2):
        _style(ax)
    fig.suptitle(f"{title}: shaft {float(p['shaft_diameter_m']) * 1e3:.0f} mm, bearings "
                 f"{float(p['bearing_stiffness_N_per_m']):.0e} N/m", fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = RotorCriticalStudy()

"""Study: efficiency map of our 2004 Prius machine (study 7), from a verified dq look-up table run (motor_lut).

Model:     lut_efficiency (models/motor/efficiency_map.py, numpy/scipy): the table interpolated onto a 1 A grid; at each
           speed and torque the feasible current (voltage limit from the bus, current limit) with the least copper + iron
           loss. Motor-only efficiency; no mechanical, inverter, magnet or AC copper loss (user's framing 2026-11-22).
Reference: the table's own open-circuit point against the open-circuit study (back-EMF), its MTPA torque against the
           torque-curve study at 100 and 200 A, and an interpolation check (the table on every second node predicting
           the nodes left out: an upper bound on the interpolation error of the full table). ORNL test data is NOT used.
Run-level: none.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

from harness.backend_base import REPO, Backend, failed
from harness.checks import check
from harness.study import Study

MODEL = "models/motor/efficiency_map.py"
PARAMS = ("lut_run", "magnet_temperature_C", "winding_temperature_C", "series_turns_per_phase", "turn_copper_area_mm2",
          "stack_length_m", "end_connection_length_m", "copper_resistivity_20C_ohm_m", "copper_alpha_per_K",
          "bus_voltage_V", "current_limit_design_A", "current_limit_map_A", "speed_min_rpm", "speed_max_rpm",
          "speed_step_rpm", "torque_min_Nm", "torque_max_Nm", "torque_step_Nm", "rated_power_kW", "rated_torque_Nm",
          "ref_back_emf_V", "ref_mtpa_100A_Nm", "ref_mtpa_200A_Nm")
#: reference operating points reported as metrics (speed rpm, torque N m): the map is the prediction, these make it
#: concrete in the case file. Chosen to span the plane, not from any ORNL test plan (sealed).
REF_POINTS = ((1000, 50), (1000, 300), (1500, 100), (3000, 50), (3000, 150), (4500, 50), (6000, 30))


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def phase_resistance_20C(p) -> float:
    """DC phase resistance at 20 C: rho N_series (2 L_stack + 2 L_end) / A_turn (one parallel path)."""
    turn = 2 * float(p["stack_length_m"]) + 2 * float(p["end_connection_length_m"])
    return float(p["copper_resistivity_20C_ohm_m"]) * float(p["series_turns_per_phase"]) * turn / (
        float(p["turn_copper_area_mm2"]) * 1e-6)


def _lut_rows(run_dir: Path) -> tuple[list[dict], int, float]:
    rows = []
    for pj in sorted((run_dir / "points").glob("*/point.json")):
        pt = json.loads(pj.read_text(encoding="utf-8"))
        if pt.get("status") != "completed":
            raise ValueError(f"{pj.parent.name}: not completed")
        with open(pj.parent / "lut.csv", newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows.append({k: float(v) for k, v in r.items()})
        pole_pairs = int(pt["solver_outputs"]["pole_pairs"])
        magnet_T = float(pt["parameters"]["magnet_temperature_C"])
    return rows, pole_pairs, magnet_T


#: table columns compared where two merged runs computed the same (id, iq) node
MERGE_FIELDS = ("torque_mean_Nm", "phi_d_Wb", "phi_q_Wb", "stator_iron_A_W", "stator_iron_B_W", "stator_iron_C_W",
                "rotor_iron_A_W", "rotor_iron_B_W", "rotor_iron_C_W")


def run_list(lut_run) -> list[str]:
    """lut_run names one motor_lut run, or several separated by commas (the first is the main table)."""
    return [s.strip() for s in str(lut_run).split(",") if s.strip()]


def load_lut(run_dir: Path | list[Path]) -> dict:
    """The regular (id, iq) grid of one motor_lut run, or the union of several (one point per d-axis current, lut.csv
    per point). Where two runs computed the same node, the first run's values are kept and the largest relative
    difference between them is reported as merge_max_rel_diff (the same model should reproduce itself)."""
    dirs = [run_dir] if isinstance(run_dir, (str, Path)) else list(run_dir)
    idx, merge_diff, temps = {}, 0.0, set()
    for d in dirs:
        rows, pole_pairs, magnet_T = _lut_rows(Path(d))
        temps.add(magnet_T)
        for r in rows:
            key = (r["id_rms_A"], r["iq_rms_A"])
            if key in idx:
                for k in MERGE_FIELDS:
                    a, b = idx[key][k], r[k]
                    scale = max(abs(a), abs(b))
                    if scale > 1e-9:
                        merge_diff = max(merge_diff, abs(a - b) / scale)
            else:
                idx[key] = r
    if len(temps) != 1:
        raise ValueError(f"merged tables disagree on the magnet temperature: {sorted(temps)}")
    ids = np.unique([k[0] for k in idx])
    iqs = np.unique([k[1] for k in idx])
    grid = {"id": ids, "iq": iqs, "pole_pairs": pole_pairs, "magnet_temperature_C": temps.pop(),
            "merge_max_rel_diff": merge_diff}
    missing = [(d, q) for d in ids for q in iqs if (d, q) not in idx]
    if missing:
        raise ValueError(f"table incomplete: {len(missing)} of {len(ids) * len(iqs)} grid points missing")
    get = lambda k: np.array([[idx[(d, q)][k] for q in iqs] for d in ids])  # noqa: E731
    for k in ("torque_mean_Nm", "phi_d_Wb", "phi_q_Wb"):
        grid[k] = get(k)
    for c in "ABC":
        grid[f"iron_{c}_W"] = get(f"stator_iron_{c}_W") + get(f"rotor_iron_{c}_W")
    return grid


class LUTEfficiency(Backend):
    sources = (MODEL,)

    def prepare(self, source_dir=None, log_dir=None):
        self.model = _load(self.source_path(MODEL, source_dir), "efficiency_map_run")

    def solve(self, params, numerics, tolerance_scale=1.0):
        runs = run_list(params["lut_run"])
        run_dirs = [REPO / "runs" / r for r in runs]
        for r, d in zip(runs, run_dirs):
            if not (d / "manifest.json").exists():
                return failed(f"look-up table run {r} not found")
        run_dir = run_dirs[0]
        grid = load_lut(run_dirs)
        m = self.model
        fine = m.fine_grid(grid, step_A=float(numerics.get("fine_step_A", 1.0)))
        r20 = phase_resistance_20C(params)
        r = m.resistance(r20, float(params["winding_temperature_C"]), float(params["copper_alpha_per_K"]))
        v_max = float(params["bus_voltage_V"]) / np.sqrt(6)  # phase rms at the linear-modulation limit Vdc / sqrt(3) peak
        speeds = np.arange(float(params["speed_min_rpm"]), float(params["speed_max_rpm"]) + 1e-9,
                           float(params["speed_step_rpm"]))
        torques = np.arange(float(params["torque_min_Nm"]), float(params["torque_max_Nm"]) + 1e-9,
                            float(params["torque_step_Nm"]))
        common = dict(pole_pairs=grid["pole_pairs"], r_ohm=r, v_max_rms=v_max)
        emap = m.efficiency_map(fine, speeds_rpm=speeds, torques_Nm=torques,
                                i_max_rms=float(params["current_limit_map_A"]), **common)
        t_max_map = emap.pop("t_max_by_speed_Nm")
        design = m.efficiency_map(fine, speeds_rpm=speeds, torques_Nm=[float(params["rated_torque_Nm"])],
                                  i_max_rms=float(params["current_limit_design_A"]), **common)
        t_max_design = design.pop("t_max_by_speed_Nm")
        ref = {}
        for n, t in REF_POINTS:
            o = m.operating_points(fine, speed_rpm=n, torques_Nm=[t], i_max_rms=float(params["current_limit_map_A"]),
                                   **common)
            ref[f"{n}_{t}"] = {k: float(v[0]) if hasattr(v, "__len__") else v for k, v in o.items()}
        # checks on the table itself
        oc = m.interpolants(grid)
        we_krpm = 2 * np.pi * 1000 / 60 * grid["pole_pairs"]
        emf = float(np.sqrt(3) * we_krpm * abs(oc["phi_d_Wb"]([[0.0, 0.0]])[0]))
        mtpa = {}
        for I in (100.0, 200.0):
            g = np.radians(np.linspace(0, 80, 801))
            pts = np.column_stack([-I * np.sin(g), I * np.cos(g)])
            mtpa[I] = float(np.max(oc["torque_mean_Nm"](pts)))
        half = {k: v[::2, ::2] if isinstance(v, np.ndarray) and v.ndim == 2 else v for k, v in grid.items()}
        half["id"], half["iq"] = grid["id"][::2], grid["iq"][::2]
        hi = m.interpolants(half)
        odd = [(d, q) for a, d in enumerate(grid["id"]) for b, q in enumerate(grid["iq"]) if a % 2 or b % 2]
        T_ref = np.array([grid["torque_mean_Nm"][list(grid["id"]).index(d), list(grid["iq"]).index(q)] for d, q in odd])
        T_hal = hi["torque_mean_Nm"](odd)
        sel = np.abs(T_ref) >= 20
        interp_T = float(np.max(np.abs(T_hal[sel] - T_ref[sel]) / np.abs(T_ref[sel]))) if sel.any() else 0.0
        f6 = 6000 / 60 * grid["pole_pairs"]
        P_ref = np.array([sum(grid[f"iron_{c}_W"][list(grid["id"]).index(d), list(grid["iq"]).index(q)] * f6 ** e
                              for c, e in zip("ABC", (1, 2, 1.5))) for d, q in odd])
        P_hal = sum(hi[f"iron_{c}_W"](odd) * f6 ** e for c, e in zip("ABC", (1, 2, 1.5)))
        interp_P = float(np.max(np.abs(P_hal - P_ref) / np.abs(P_ref)))
        extra = {}
        if len(run_dirs) > 1:
            # the main table alone, interpolated at the nodes only the supplementary runs computed: the interpolation
            # error the map would carry without them (|T| >= 5 N m)
            main = load_lut(run_dirs[0])
            mi = m.interpolants(main)
            new = [(d, q) for d in grid["id"] for q in grid["iq"] if q not in set(main["iq"]) or d not in set(main["id"])]
            Tn = np.array([grid["torque_mean_Nm"][list(grid["id"]).index(d), list(grid["iq"]).index(q)] for d, q in new])
            sel_n = np.abs(Tn) >= 5
            err_n = np.abs(mi["torque_mean_Nm"](new) - Tn) / np.maximum(np.abs(Tn), 1e-12)
            k = int(np.argmax(np.where(sel_n, err_n, -1)))
            extra = {"lut_merge_max_rel_diff": grid["merge_max_rel_diff"], "main_table_new_nodes": len(new),
                     "main_table_interp_torque_rel_at_new_nodes": float(err_n[k]) if sel_n.any() else 0.0,
                     "main_table_interp_worst_node_A": [float(new[k][0]), float(new[k][1])]}
        if numerics.get("halfgrid_map_check"):
            # the output itself: the whole map from the half table against the full one, in efficiency points, over
            # the cells both can reach (bounds the full table's interpolation error on the map)
            emap_h = m.efficiency_map(m.fine_grid(half, step_A=float(numerics.get("fine_step_A", 1.0))),
                                      speeds_rpm=speeds, torques_Nm=torques,
                                      i_max_rms=float(params["current_limit_map_A"]), **common)
            emap_h.pop("t_max_by_speed_Nm")
            a, b = np.asarray(emap["efficiency_pct"]), np.asarray(emap_h["efficiency_pct"])
            ok = ~np.isnan(a) & ~np.isnan(b)
            d = np.abs(a - b)[ok]
            tq = np.asarray(emap["target_torque_Nm"])[ok]
            j = int(np.argmax(d))
            extra |= {"halfgrid_map_eff_diff_max_pts": float(d.max()), "halfgrid_map_eff_diff_median_pts":
                      float(np.median(d)), "halfgrid_map_eff_diff_max_pts_above_60Nm": float(d[tq >= 60].max())
                      if (tq >= 60).any() else 0.0, "halfgrid_map_worst_cell": [float(np.asarray(emap["speed_rpm"])[ok][j]),
                                                                               float(tq[j])],
                      "halfgrid_map_cells_compared": int(ok.sum())}
        man = (run_dir / "manifest.json").read_bytes()
        extra["lut_manifests_sha256"] = [hashlib.sha256((d / "manifest.json").read_bytes()).hexdigest() for d in run_dirs]
        outputs = extra | {"lut_run": str(params["lut_run"]), "lut_manifest_sha256": hashlib.sha256(man).hexdigest(),
                   "lut_magnet_temperature_C": grid["magnet_temperature_C"], "pole_pairs": grid["pole_pairs"],
                   "grid_id_A": grid["id"].tolist(), "grid_iq_A": grid["iq"].tolist(),
                   "phase_resistance_20C_ohm": r20, "phase_resistance_ohm": r, "voltage_limit_rms_V": v_max,
                   "speeds_rpm": speeds.tolist(), "t_max_map_Nm": t_max_map.tolist(),
                   "t_max_design_Nm": t_max_design.tolist(), "rated_torque_design_feasible": (~np.isnan(
                       design["efficiency_pct"])).tolist(), "ref_points": ref, "lut_back_emf_V": emf,
                   "lut_mtpa_Nm": {str(int(k)): v for k, v in mtpa.items()},
                   "interp_halfgrid_torque_rel": interp_T, "interp_halfgrid_iron6000_rel": interp_P}
        return {"success": True, "message": f"{len(speeds)} speeds x {len(torques)} torques, R {r * 1e3:.2f} mOhm",
                "nfev": len(speeds) * len(torques), "series": emap, "outputs": outputs}

    def tool_versions(self):
        import scipy

        return {"numpy": np.__version__, "scipy": scipy.__version__}


class MotorEfficiencyStudy(Study):
    name = "motor_efficiency"
    models = {"lut_efficiency": LUTEfficiency}
    metrics = frozenset({"peak_efficiency_pct", "peak_efficiency_speed_rpm", "peak_efficiency_torque_Nm",
                         "min_power_rated_speed_range_kW", "base_speed_rated_torque_rpm"}
                        | {f"efficiency_{n}rpm_{t}Nm_pct" for n, t in REF_POINTS})
    param_names = PARAMS
    series_file = "efficiency_map.csv"
    compare_description = "max difference of the efficiency over the map"

    def derive(self, params):
        return {"phase_resistance_20C_ohm": phase_resistance_20C(params),
                "voltage_limit_rms_V": float(params["bus_voltage_V"]) / np.sqrt(6)}

    def compute_metrics(self, series, params, case, outputs=None):
        eff = np.asarray(series["efficiency_pct"])
        k = int(np.nanargmax(eff))
        speeds = np.asarray(outputs["speeds_rpm"])
        p_rated = float(params["rated_power_kW"])
        n_base = p_rated * 1e3 / float(params["rated_torque_Nm"]) * 60 / (2 * np.pi)
        t_design = np.asarray(outputs["t_max_design_Nm"])
        rng = speeds >= n_base - 1e-9
        power = t_design * speeds * 2 * np.pi / 60 / 1e3
        feas = np.asarray(outputs["rated_torque_design_feasible"], bool)
        out = {"peak_efficiency_pct": float(eff[k]), "peak_efficiency_speed_rpm": float(series["speed_rpm"][k]),
               "peak_efficiency_torque_Nm": float(series["torque_Nm"][k]),
               "min_power_rated_speed_range_kW": float(np.min(power[rng])) if rng.any() else float("nan"),
               "base_speed_rated_torque_rpm": float(np.max(speeds[feas])) if feas.any() else 0.0}
        for n, t in REF_POINTS:
            out[f"efficiency_{n}rpm_{t}Nm_pct"] = float(outputs["ref_points"][f"{n}_{t}"]["efficiency_pct"])
        return out

    def verify_point(self, case, point, pdir, series, backend):
        tol = case["verification"]
        p, out = point["parameters"], point["solver_outputs"]
        checks = []
        if float(p["ref_back_emf_V"]) > 0:
            checks.append(check("lut_back_emf", "|table open-circuit back-EMF (sqrt 3 w phi_d at id = iq = 0) - "
                                "open-circuit study| / open-circuit study (same mesh fineness)",
                                abs(out["lut_back_emf_V"] - float(p["ref_back_emf_V"])) / float(p["ref_back_emf_V"]),
                                tol["back_emf_rel_tol"]))
        for I, key in ((100, "ref_mtpa_100A_Nm"), (200, "ref_mtpa_200A_Nm")):
            if float(p[key]) > 0:
                checks.append(check(f"lut_mtpa_{I}A", f"|table MTPA torque at {I} A rms - torque-curve study| / "
                                    "torque-curve study (cubic interpolation against an angle sweep with a parabola)",
                                    abs(out["lut_mtpa_Nm"][str(I)] - float(p[key])) / float(p[key]),
                                    tol["mtpa_rel_tol"]))
        checks += [
            check("interp_torque", "max over the left-out nodes (|T| >= 20 N m) of the torque error of the table on "
                  "every second node: bounds the full table's interpolation error (cubic: about 1/16 of this)",
                  out["interp_halfgrid_torque_rel"], tol["interp_halfgrid_rel_tol"]),
            check("interp_iron_loss", "the same for the iron loss at 6000 rpm", out["interp_halfgrid_iron6000_rel"],
                  tol["interp_halfgrid_rel_tol"]),
            check("magnet_temperature", "|table's magnet temperature - this scenario's| (K)",
                  abs(out["lut_magnet_temperature_C"] - float(p["magnet_temperature_C"])), 0.0, kind="validity"),
        ]
        if "lut_merge_max_rel_diff" in out and "merge_rel_tol" in tol:
            checks.append(check("lut_merge", "max relative difference over the nodes two merged table runs both "
                                "computed (same model, mesh and rotor positions: it must reproduce itself)",
                                out["lut_merge_max_rel_diff"], tol["merge_rel_tol"]))
        if "halfgrid_map_eff_diff_max_pts" in out and "interp_map_max_pts" in tol:
            checks.append(check("interp_map", "max |efficiency from the half table - from the full table| over the map "
                                "(efficiency points): bounds the full table's interpolation error on the output itself",
                                out["halfgrid_map_eff_diff_max_pts"], tol["interp_map_max_pts"]))
        efficiency_figure(pdir / "response.png", series, out, point)
        return checks


def efficiency_figure(path, series, out, point):
    from harness.plotting import SERIES_1, SURFACE, TEXT, _style, plt

    n = np.asarray(series["speed_rpm"])
    t = np.asarray(series["target_torque_Nm"])
    e = np.asarray(series["efficiency_pct"])
    speeds, torques = np.unique(n), np.unique(t)
    E = e.reshape(len(speeds), len(torques)).T
    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor(SURFACE)
    levels = [70, 80, 85, 88, 90, 92, 93, 94, 95, 96, 97]
    cs = ax.contourf(speeds, torques, E, levels=levels, cmap="viridis", extend="both")
    ax.contour(speeds, torques, E, levels=levels, colors="white", linewidths=0.4)
    fig.colorbar(cs, ax=ax, label="efficiency (%)")
    ax.plot(out["speeds_rpm"], out["t_max_design_Nm"], color=SERIES_1, lw=1.5, label="limit at the design current")
    ax.set_xlabel("speed (rpm)")
    ax.set_ylabel("torque (N m)")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    _style(ax)
    fig.suptitle(f"{point['label']}: motor-only efficiency, R {out['phase_resistance_ohm'] * 1e3:.1f} mOhm, "
                 f"magnets {out['lut_magnet_temperature_C']:g} C", fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = MotorEfficiencyStudy()

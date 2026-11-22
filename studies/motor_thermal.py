"""Study: steady thermal network of our 2004 Prius machine (study 7): continuous torque-speed envelope and the efficiency
map's hot corner.

Model:     lumped_thermal (models/motor/thermal_network.py, numpy) coupled to the verified dq tables: at each speed and
           torque, the lowest-loss feasible current (models/motor/efficiency_map.py, as in the efficiency study) with the
           phase resistance at the network's winding temperatures and the tables blended linearly in magnet temperature
           between the cold (20 C) and hot (80 C) runs; losses placed per region (slot copper, end-winding copper, teeth,
           yoke, rotor iron); network solved; repeated to a self-consistent state. Envelope: the largest torque per speed
           with the winding hotspot and the magnets within their limits and the current and voltage within the design
           limits. Hot corner: per speed, the torque at which the copper-weighted winding mean reaches 100 C, and the
           magnet temperature there.
Reference: CalculiX steady conduction on one half slot pitch (models/motor/stator_section_ccx.py) with the same losses,
           conductivities and boundary conditions as the network's cross-section part (no axial paths), on three meshes;
           the network's energy balance; the coupled losses at fixed hot temperatures against the efficiency run's map.
Run-level: none.
"""

from __future__ import annotations

import csv
import importlib.util
import math
import os
import subprocess
from pathlib import Path

import numpy as np
from scipy.interpolate import RegularGridInterpolator

from harness.backend_base import REPO, Backend, failed
from harness.calculix import read_frd
from harness.checks import check
from harness.convergence import discretization_uncertainty
from harness.study import Study
from studies.motor_efficiency import load_lut, phase_resistance_20C, run_list

NET = "models/motor/thermal_network.py"
FE = "models/motor/stator_section_ccx.py"
EFF = "models/motor/efficiency_map.py"
SPEEDS_REPORTED = (1250, 2000, 3000, 4000, 5000, 6000)
BINDING = {"winding": 0, "magnet": 1, "electrical": 2}
RUNAWAY_C = 400.0  # a probe past this is outside every limit; its iteration stops there

GEOM = ("n_slots", "stack_length_mm", "stator_outer_radius_mm", "stator_bore_radius_mm", "slot_shoulder_x_mm",
        "slot_width_shoulder_mm", "slot_width_round_mm", "slot_round_centre_x_mm", "slot_opening_mm",
        "liner_thickness_mm", "copper_area_per_slot_mm2", "rotor_outer_radius_mm", "rotor_inner_radius_mm",
        "end_connection_length_mm", "end_extension_mm")
PROPS = ("impregnant_conductivity_W_mK", "copper_conductivity_W_mK", "liner_conductivity_W_mK",
         "lamination_conductivity_W_mK", "housing_conductivity_W_mK", "housing_wall_mm", "interface_gap_mm",
         "jacket_htc_W_m2K", "coolant_temperature_C", "air_gap_h_factor", "end_space_h_scale", "winding_k_scale",
         "teeth_iron_fraction")
CORR = tuple(f"h_{s}_k{i}" for s in ("winding_end_space", "housing_end_space", "rotor_end_space") for i in (1, 2, 3))
ELEC = ("lut_run_cold", "lut_run_hot", "series_turns_per_phase", "turn_copper_area_mm2", "end_connection_length_m",
        "stack_length_m", "copper_resistivity_20C_ohm_m", "copper_alpha_per_K", "bus_voltage_V",
        "current_limit_design_A", "winding_hotspot_limit_C", "magnet_limit_C", "speed_min_rpm", "speed_max_rpm",
        "speed_step_rpm", "hot_corner_winding_C", "efficiency_run", "fe_reference_speed_rpm")
PARAMS = GEOM + PROPS + CORR + ELEC


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Coupled:
    """Losses <-> temperatures at one speed and torque."""

    def __init__(self, net, eff, p, fine_cold, fine_hot, t_cold, t_hot, pole_pairs):
        self.net, self.eff, self.p = net, eff, p
        self.g = net.geometry(p)
        self.fc, self.fh, self.tc, self.th = fine_cold, fine_hot, t_cold, t_hot
        self.pp = pole_pairs
        self.r20 = phase_resistance_20C(p)
        Ls, Le = float(p["stack_length_m"]), float(p["end_connection_length_m"])
        self.f_slot, self.f_end = Ls / (Ls + Le), Le / (Ls + Le)
        self.alpha = float(p["copper_alpha_per_K"])
        self.v_max = float(p["bus_voltage_V"]) / math.sqrt(6)
        self.i_max = float(p["current_limit_design_A"])
        self.max_balance = 0.0
        self.n_solves = 0

    def fine(self, t_mag):
        w = (t_mag - self.tc) / (self.th - self.tc)
        if w == 0.0:
            return self.fc
        if w == 1.0:
            return self.fh
        return {k: self.fc[k] + w * (self.fh[k] - self.fc[k]) for k in self.fc}

    def losses(self, n, torque, t_w, t_e, t_m):
        """Operating point and its regional losses at fixed temperatures; None if infeasible."""
        fine = self.fine(t_m)
        r = self.r20 * (self.f_slot * (1 + self.alpha * (t_w - 20)) + self.f_end * (1 + self.alpha * (t_e - 20)))
        op = self.eff.operating_points(fine, speed_rpm=n, torques_Nm=[torque], pole_pairs=self.pp, r_ohm=r,
                                       v_max_rms=self.v_max, i_max_rms=self.i_max)
        if not np.isfinite(op["id_A"][0]):
            return None
        k = int(np.flatnonzero((fine["id"] == op["id_A"][0]) & (fine["iq"] == op["iq_A"][0]))[0])
        f = n / 60 * self.pp
        fe = lambda pre: sum(fine[f"{pre}iron_{c}_W"][k] * f ** e for c, e in zip("ABC", (1, 2, 1.5)))  # noqa: E731
        fe_tot, fe_st = float(fe("")), float(fe("stator_"))
        I2 = op["current_A"][0] ** 2
        ft = float(self.p["teeth_iron_fraction"])
        return {"cu_slot": 3 * I2 * self.r20 * self.f_slot * (1 + self.alpha * (t_w - 20)),
                "cu_end": 3 * I2 * self.r20 * self.f_end * (1 + self.alpha * (t_e - 20)),
                "fe_teeth": ft * fe_st, "fe_yoke": (1 - ft) * fe_st, "fe_rotor": fe_tot - fe_st,
                "p_cu_W": float(op["p_cu_W"][0]), "p_fe_W": float(op["p_fe_W"][0]), "id_A": float(op["id_A"][0]),
                "iq_A": float(op["iq_A"][0]), "current_A": float(op["current_A"][0]), "r_ohm": r,
                "torque_Nm": float(op["torque_Nm"][0])}

    def solve(self, n, torque, start=None, tol=1e-3, max_iter=200):
        t = dict(start or {"W": 100.0, "E": 100.0, "ROT": 80.0})
        change = float("inf")
        for it in range(max_iter):
            L = self.losses(n, torque, t["W"], t["E"], t["ROT"])
            if L is None:
                return None
            st = self.net.steady(self.p, self.g, L, n)
            self.n_solves += 1
            self.max_balance = max(self.max_balance, st["balance_rel"])
            new = {k: st["T"][k] for k in ("W", "E", "ROT")}
            change = max(abs(new[k] - t[k]) for k in t)
            t = new
            if change < tol or max(new.values()) > RUNAWAY_C:
                break  # converged, or far past every limit (thermal runaway: copper loss rising faster than cooling)
        return {"T": st["T"], "losses": L, "last_change_K": change, "iterations": it + 1,
                "winding_hotspot_C": st["winding_hotspot_C"], "slot_hotspot_C": st["slot_hotspot_C"],
                "end_hotspot_C": st["end_hotspot_C"], "winding_mean_C": st["winding_mean_C"],
                "magnet_C": st["T"]["ROT"], "info": st["info"], "start": t}

    def ok(self, s):
        return (s is not None and s["winding_hotspot_C"] <= float(self.p["winding_hotspot_limit_C"])
                and s["magnet_C"] <= float(self.p["magnet_limit_C"]))


def envelope_at(c: Coupled, n: float, max_change: list) -> dict:
    """Largest torque at speed n within the limits (bisection to 0.05 N m)."""
    lo, hi = 0.0, 450.0
    s_lo = None
    start = None
    # the electrical ceiling at the design current (hot tables, R at 100 C: only a bracket for the bisection)
    while hi - lo > 0.05:
        mid = 0.5 * (lo + hi)
        s = c.solve(n, mid, start)
        if c.ok(s):
            lo, s_lo, start = mid, s, s["start"]
        else:
            hi = mid
    if s_lo is None:
        return {"torque": 0.0, "binding": "winding", "s": None}
    max_change[0] = max(max_change[0], s_lo["last_change_K"])  # convergence of the reported state
    s_hi = c.solve(n, hi, start)
    if s_hi is None:
        binding = "electrical"
    elif s_hi["magnet_C"] > float(c.p["magnet_limit_C"]) and s_hi["winding_hotspot_C"] <= float(
            c.p["winding_hotspot_limit_C"]):
        binding = "magnet"
    else:
        binding = "winding"
    return {"torque": s_lo["losses"]["torque_Nm"], "binding": binding, "s": s_lo}


def hot_corner_at(c: Coupled, n: float, target_C: float, max_change: list) -> dict | None:
    """Torque at which the copper-weighted winding mean reaches target_C (bisection), and the state there."""
    s0 = c.solve(n, 10.0)
    if s0 is None or s0["winding_mean_C"] > target_C:
        return None
    lo, hi, s_lo, start = 10.0, 450.0, s0, s0["start"]
    while hi - lo > 0.05:
        mid = 0.5 * (lo + hi)
        s = c.solve(n, mid, start)
        if s is not None and s["winding_mean_C"] <= target_C:
            lo, s_lo, start = mid, s, s["start"]
        else:
            hi = mid
    if hi >= 449.9 or c.solve(n, hi, start) is None:
        return None  # the electrical limit comes first: the winding never reaches the target at this speed
    max_change[0] = max(max_change[0], s_lo["last_change_K"])
    return {"torque": s_lo["losses"]["torque_Nm"], "s": s_lo}


class LumpedThermal(Backend):
    sources = (NET, FE, EFF)

    def __init__(self):
        from studies.fin import find_ccx

        self.ccx = find_ccx()
        self.gmsh = self.ccx.parent / "gmsh.exe"

    def prepare(self, source_dir=None, log_dir=None):
        self.net = _load(self.source_path(NET, source_dir), "thermal_network_run")
        self.fe = _load(self.source_path(FE, source_dir), "stator_section_ccx_run")
        self.eff = _load(self.source_path(EFF, source_dir), "efficiency_map_thermal_run")
        g = subprocess.run([str(self.gmsh), "--version"], capture_output=True, text=True, timeout=60)
        c = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions = {"gmsh": (g.stdout + g.stderr).strip().splitlines()[-1],
                          "ccx": (c.stdout + c.stderr).strip().splitlines()[-1]}

    def _fine(self, run):
        dirs = [REPO / "runs" / r for r in run_list(run)]
        for d in dirs:
            if not (d / "manifest.json").exists():
                raise FileNotFoundError(f"look-up table run {d.name} not found")
        grid = load_lut(dirs)
        fine = self.eff.fine_grid(grid, step_A=1.0)
        pts = np.column_stack([fine["id"], fine["iq"]])
        for c in "ABC":
            k = f"stator_iron_{c}_W"
            fine[k] = RegularGridInterpolator((grid["id"], grid["iq"]), grid[k], method="cubic")(pts)
        return fine, grid

    def section_fe(self, p, g, state, work: Path) -> dict:
        """The CalculiX slot-pitch check at one coupled state (per metre of stack)."""
        net, fe = self.net, self.fe
        L = g["L"]
        Ls = state["losses"]
        per_m = {"q_wind": Ls["cu_slot"] / L, "q_teeth": Ls["fe_teeth"] / L, "q_yoke": Ls["fe_yoke"] / L}
        t_rotor = state["T"]["RO"]
        sec = net.section_check_network(p, g, **per_m, t_rotor_C=t_rotor)
        k_x, _ = net.winding_conductivity(p, g)
        k_fe = float(p["lamination_conductivity_W_mK"])
        Zs = g["Zs"]
        bc = {"k_WIND": k_x, "k_LINER": float(p["liner_conductivity_W_mK"]), "k_TEETH": k_fe, "k_YOKE": k_fe,
              "q_WIND": per_m["q_wind"] / (Zs * g["a_wind"]), "q_LINER": 0.0,
              "q_TEETH": per_m["q_teeth"] / (Zs * g["a_teeth"]), "q_YOKE": per_m["q_yoke"] / (Zs * g["a_yoke"]),
              "h_od": 1 / (net.outer_resistance(p, g, 1.0) * 2 * math.pi * g["r_so"]),
              "t_od": float(p["coolant_temperature_C"]), "h_bore": net.air_gap_h(p, g), "t_bore": t_rotor}
        h0 = float(self.fe_size_mm) * 1e-3
        sizes = (h0 / 2, h0 / math.sqrt(2), h0)  # fine -> coarse
        res = []
        for i, h in enumerate(sizes):
            d = work / f"fe_{i}"
            d.mkdir(parents=True, exist_ok=True)
            fe.write_geo(g, h, d / "mesh.geo")
            r = subprocess.run([str(self.gmsh), "mesh.geo", "-2", "-format", "inp", "-o", "mesh.inp"], cwd=d,
                               capture_output=True, text=True, timeout=600)
            (d / "gmsh.log").write_text(r.stdout + r.stderr, encoding="utf-8")
            if r.returncode != 0:
                raise RuntimeError(f"gmsh failed in {d}")
            info = fe.write_deck(g, bc, d / "mesh.inp", d / "job.inp")
            r = subprocess.run([str(self.ccx), "-i", "job"], cwd=d, capture_output=True, text=True, timeout=1800)
            (d / "ccx.log").write_text(r.stdout + r.stderr, encoding="utf-8")
            if r.returncode != 0 or not (d / "job.frd").exists():
                raise RuntimeError(f"CalculiX failed in {d}; see ccx.log")
            frd = read_frd(d / "job.frd")
            temps = dict(zip([int(v) for v in frd["NDTEMP"]["ids"]], np.asarray(frd["NDTEMP"]["T"], float).tolist()))
            res.append(fe.results(g, bc, d / "mesh.inp", temps) | info | {"h_m": h})
        t0 = float(p["coolant_temperature_C"])
        T = sec["T"]
        net_vals = {"wind_mean": T["W"], "wind_peak": sec["slot_hotspot_C"], "teeth_mean": T["T"], "yoke_mean": T["Y"]}
        fe_keys = {"wind_mean": "WIND_mean_C", "wind_peak": "WIND_max_C", "teeth_mean": "TEETH_mean_C",
                   "yoke_mean": "YOKE_mean_C"}
        out = {"state_speed_rpm": state["speed"], "state_torque_Nm": state["losses"]["torque_Nm"],
               "per_metre_W": per_m, "bc": {k: float(v) for k, v in bc.items()}, "network": net_vals,
               "network_balance_rel": sec["balance_rel"], "fe_levels": res}
        for k, fk in fe_keys.items():
            f = [r[fk] for r in res]
            # noise floor 1e-4: the .frd holds 6 significant digits (0.001 K at 100-200 C, about 1.5e-5 of a 70 K
            # rise), and the peak is a nodal maximum; 1e-5 classed identical values as divergent (run 20261122-174048)
            u = discretization_uncertainty(tuple(sizes), tuple(fi - t0 for fi in f), noise_floor=1e-4,
                                           design_order=2)
            out[f"fe_{k}_C"] = f[0]
            out[f"fe_{k}_gci"] = float(u["uncertainty"])
            out[f"fe_{k}_regime"] = u["regime"]
            out[f"rise_err_{k}"] = ((net_vals[k] - t0) - (f[0] - t0)) / (f[0] - t0)
        out["fe_balance_rel"] = max(r["balance_rel"] for r in res)
        return out

    def solve(self, params, numerics, tolerance_scale=1.0):
        p = params
        self.fe_size_mm = float(numerics.get("fe_element_size_mm", 0.4))
        try:
            fc, gc = self._fine(p["lut_run_cold"])
            fh, gh = self._fine(p["lut_run_hot"])
        except FileNotFoundError as e:
            return failed(str(e))
        if not (np.array_equal(gc["id"], gh["id"]) and np.array_equal(gc["iq"], gh["iq"])):
            return failed("cold and hot tables are on different grids")
        c = Coupled(self.net, self.eff, p, fc, fh, gc["magnet_temperature_C"], gh["magnet_temperature_C"],
                    gc["pole_pairs"])
        speeds = np.arange(float(p["speed_min_rpm"]), float(p["speed_max_rpm"]) + 1e-9, float(p["speed_step_rpm"]))
        max_change = [0.0]
        env = {k: [] for k in ("speed_rpm", "continuous_torque_Nm", "continuous_power_kW", "winding_hotspot_C",
                               "slot_hotspot_C", "end_hotspot_C", "winding_mean_C", "magnet_C", "binding_code",
                               "current_A", "p_cu_W", "p_fe_W", "p_fe_rotor_W", "id_A", "iq_A")}
        states = {}
        for n in speeds:
            e = envelope_at(c, float(n), max_change)
            s = e["s"]
            env["speed_rpm"].append(float(n))
            env["continuous_torque_Nm"].append(e["torque"])
            env["continuous_power_kW"].append(e["torque"] * n * 2 * math.pi / 60 / 1e3)
            env["binding_code"].append(BINDING[e["binding"]])
            for k, sk in (("winding_hotspot_C", "winding_hotspot_C"), ("slot_hotspot_C", "slot_hotspot_C"),
                          ("end_hotspot_C", "end_hotspot_C"), ("winding_mean_C", "winding_mean_C"),
                          ("magnet_C", "magnet_C")):
                env[k].append(s[sk] if s else float("nan"))
            for k in ("current_A", "p_cu_W", "p_fe_W", "id_A", "iq_A"):
                env[k].append(s["losses"][k] if s else float("nan"))
            env["p_fe_rotor_W"].append(s["losses"]["fe_rotor"] if s else float("nan"))
            if s:
                states[float(n)] = s | {"speed": float(n)}
        hot = {"speed_rpm": [], "torque_Nm": [], "magnet_C": [], "winding_hotspot_C": []}
        for n in np.arange(500.0, float(p["speed_max_rpm"]) + 1e-9, 500.0):
            h = hot_corner_at(c, float(n), float(p["hot_corner_winding_C"]), max_change)
            if h:
                hot["speed_rpm"].append(float(n))
                hot["torque_Nm"].append(h["torque"])
                hot["magnet_C"].append(h["s"]["magnet_C"])
                hot["winding_hotspot_C"].append(h["s"]["winding_hotspot_C"])
        # consistency with the efficiency run: losses at fixed hot temperatures (windings 100 C, magnets 80 C)
        eff_rows = []
        with open(REPO / "runs" / str(p["efficiency_run"]) / "points" / "p01_hot" / "efficiency_map.csv",
                  newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                eff_rows.append({k: float(v) for k, v in r.items()})
        cons = 0.0
        n_cons = 0
        for n, t in ((1000, 50), (1500, 100), (3000, 150), (4500, 50), (6000, 30)):
            row = next(r for r in eff_rows if r["speed_rpm"] == n and r["target_torque_Nm"] == t)
            L = c.losses(float(n), float(t), 100.0, 100.0, 80.0)
            if L is None or not np.isfinite(row["p_cu_W"]):
                continue
            ref = row["p_cu_W"] + row["p_fe_W"]
            mine = L["cu_slot"] + L["cu_end"] + L["fe_teeth"] + L["fe_yoke"] + L["fe_rotor"]
            cons = max(cons, abs(mine - ref) / ref)
            n_cons += 1
        # the CalculiX section check at the envelope state at the reference speed
        n_ref = float(p["fe_reference_speed_rpm"])
        import tempfile

        work = Path(tempfile.mkdtemp(prefix="motor_thermal_fe_"))
        try:
            fe_out = self.section_fe(p, c.g, states[n_ref], work)
        except Exception as e:  # noqa: BLE001
            return failed(f"section check: {e}")
        ref_states = {str(int(n)): {"T": {k: float(v) for k, v in states[n]["T"].items()},
                                    "losses": {k: float(v) for k, v in states[n]["losses"].items()},
                                    "info": states[n]["info"], "iterations": states[n]["iterations"]}
                      for n in map(float, SPEEDS_REPORTED) if n in states}
        outputs = {"envelope": {k: [float(v) for v in vals] for k, vals in env.items()}, "hot_corner": hot,
                   "max_balance_rel": c.max_balance, "max_last_change_K": max_change[0],
                   "efficiency_consistency_rel": cons, "efficiency_consistency_points": n_cons,
                   "section_fe": fe_out, "ref_states": ref_states, "network_solves": c.n_solves,
                   "magnet_extrapolation_above_hot_table_K": float(np.nanmax(env["magnet_C"] + hot["magnet_C"])) - c.th,
                   "geometry_mm": {k: (v * 1e3 if isinstance(v, float) else v) for k, v in c.g.items()
                                   if not k.startswith("a_")},
                   "areas_mm2": {k: v * 1e6 for k, v in c.g.items() if k.startswith("a_")},
                   "winding_k_across_W_mK": self.net.winding_conductivity(p, c.g)[0],
                   "phase_resistance_20C_ohm": c.r20, "fe_work_dir": str(work)}
        self._fe_work = work
        return {"success": True, "message": f"{len(speeds)} speeds, {c.n_solves} network solves",
                "nfev": c.n_solves, "series": {k: np.asarray(v, float) for k, v in env.items()},
                "outputs": outputs}

    def tool_versions(self):
        import scipy

        return {"numpy": np.__version__, "scipy": scipy.__version__} | getattr(self, "_versions", {})


class MotorThermalStudy(Study):
    name = "motor_thermal"
    models = {"lumped_thermal": LumpedThermal}
    metrics = frozenset({"min_continuous_power_kW", "magnet_at_winding_100C_min_C", "magnet_at_winding_100C_max_C",
                         "magnet_bound_speeds"} | {f"continuous_torque_{n}rpm_Nm" for n in SPEEDS_REPORTED})
    param_names = PARAMS
    series_file = "envelope.csv"
    compare_description = "max relative difference of the continuous torque over the speeds"

    def derive(self, params):
        return {"phase_resistance_20C_ohm": phase_resistance_20C(params)}

    def compute_metrics(self, series, params, case, outputs=None):
        n = np.asarray(series["speed_rpm"])
        T = np.asarray(series["continuous_torque_Nm"])
        P = np.asarray(series["continuous_power_kW"])
        out = {f"continuous_torque_{s}rpm_Nm": float(T[np.argmin(np.abs(n - s))]) for s in SPEEDS_REPORTED}
        rng = n >= 1250 - 1e-9
        out["min_continuous_power_kW"] = float(np.min(P[rng]))
        hm = outputs["hot_corner"]["magnet_C"] if outputs else []
        out["magnet_at_winding_100C_min_C"] = float(min(hm)) if hm else float("nan")
        out["magnet_at_winding_100C_max_C"] = float(max(hm)) if hm else float("nan")
        out["magnet_bound_speeds"] = float(np.sum(np.asarray(series["binding_code"]) == BINDING["magnet"]))
        return out

    def verify_point(self, case, point, pdir, series, backend):
        tol = case["verification"]
        out = point["solver_outputs"]
        fe = out["section_fe"]
        checks = [
            check("energy_balance", "max over every network solve of |losses in - heat to the coolant| / losses",
                  out["max_balance_rel"], tol["balance_rel_tol"]),
            check("coupling_convergence", "max over the envelope and hot-corner searches of the last temperature "
                  "change of the loss-temperature iteration (K)", out["max_last_change_K"], tol["coupling_tol_K"]),
            check("efficiency_consistency", "max relative difference of the total loss at fixed hot temperatures "
                  "(windings 100 C, magnets 80 C) against the efficiency run's hot map at five points",
                  out["efficiency_consistency_rel"], tol["consistency_rel_tol"]),
            check("fe_balance", "CalculiX section: |generation - film heat out| / generation, worst mesh",
                  fe["fe_balance_rel"], tol["fe_balance_rel_tol"]),
            check("fe_mesh", "CalculiX section: discretization uncertainty (GCI or spread) of the winding peak rise",
                  fe["fe_wind_peak_gci"], tol["fe_gci_tol"]),
        ]
        for k, txt in (("wind_mean", "winding mean"), ("wind_peak", "winding peak (network: slab factor 1.5)"),
                       ("teeth_mean", "teeth mean"), ("yoke_mean", "yoke mean")):
            checks.append(check(f"section_{k}", f"|network - CalculiX| / CalculiX, {txt} rise above the coolant, "
                                "cross-section with the same losses and boundary conditions (model form)",
                                abs(fe[f"rise_err_{k}"]), tol["section_rise_rel_tol"]))
        thermal_figure(pdir / "response.png", series, out, point)
        import shutil

        work = Path(os.path.expanduser(out.get("fe_work_dir", "")))  # the harness writes home as ~
        if work.exists():
            dst = pdir / "solver"
            dst.mkdir(exist_ok=True)
            for f in sorted(work.glob("fe_*/*")):
                if f.suffix in (".geo", ".log", ".sta"):
                    (dst / f.parent.name).mkdir(exist_ok=True)
                    shutil.copy2(f, dst / f.parent.name / f.name)
            shutil.rmtree(work, ignore_errors=True)
        return checks


def thermal_figure(path, series, out, point):
    from harness.plotting import SERIES_1, SERIES_2, SURFACE, TEXT, _style, plt

    n = np.asarray(series["speed_rpm"])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4))
    fig.patch.set_facecolor(SURFACE)
    a1.plot(n, series["continuous_torque_Nm"], color=SERIES_1, lw=1.8, label="continuous torque")
    a1.set_xlabel("speed (rpm)")
    a1.set_ylabel("torque (N m)")
    ax = a1.twinx()
    ax.plot(n, series["continuous_power_kW"], color=SERIES_2, lw=1.2, ls="--", label="power")
    ax.set_ylabel("power (kW)")
    _style(a1)
    a1.legend(frameon=False, fontsize=8, loc="lower left")
    a2.plot(n, series["winding_hotspot_C"], color=SERIES_1, lw=1.5, label="winding hotspot")
    a2.plot(n, series["winding_mean_C"], color=SERIES_1, lw=1.0, ls=":", label="winding mean")
    a2.plot(n, series["magnet_C"], color=SERIES_2, lw=1.5, label="magnets (rotor)")
    hc = out["hot_corner"]
    if hc["speed_rpm"]:
        a2.plot(hc["speed_rpm"], hc["magnet_C"], "o", color=SERIES_2, ms=4, label="magnets at winding mean 100 C")
    a2.set_xlabel("speed (rpm)")
    a2.set_ylabel("temperature (C)")
    a2.legend(frameon=False, fontsize=7)
    _style(a2)
    fig.suptitle(f"{point['label']}: continuous envelope (steady)", fontsize=10, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


STUDY = MotorThermalStudy()

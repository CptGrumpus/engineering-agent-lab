"""Study: cold plate, full thermal chain. Coolant CFD (OpenFOAM) coupled to conduction in the
aluminium plate (CalculiX), then thermal stress in the plate (CalculiX).

Model:     openfoam_ccx_cold_plate
             models/cfd/cold_plate_openfoam.py    coolant channel, wall flux profile
             models/cfd/run_cold_plate.sh         runs it in WSL (full / temperature pass)
             models/thermal/cold_plate_ccx.py     plate heat-transfer and stress decks
Coupling:  partitioned, fixed point (Robin-Neumann). The CFD takes the wall heat flux from the
           plate; the plate takes a film condition from the CFD with a constant coupling
           coefficient h* and sink T_ref = T_wall,CFD - q/h*, so a plate surface at the CFD
           wall temperature returns the same flux. Iterate until the plate's wetted-surface
           temperature equals the CFD wall temperature and the flux stops changing. The wall
           faces of the CFD and the wetted faces of the plate coincide one to one, so heat
           passes across the interface exactly.
References (independent of the model code):
           CFD stage    validation/graetz.thermal_entry_profile: thermal entry with the
                        converged (non-uniform) wall flux, no axial conduction; exact energy
                        balance
           plate stage  validation/plate_conduction: exact 2D Fourier series for the plate
                        with the converged film data and the component flux; 1D slab check
           stress stage validation/thermal_stress: beam theory (plane strain, clamped
                        ends) on the plate temperature field; the exact uniform-temperature
                        case run through the same deck writer and solver
Run-level: GCI on every requirement metric when the sweep is cells_across_gap (the plate
           mesh is refined with the CFD mesh: same cell size along x and through the plate)
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from harness import openfoam as of
from harness.backend_base import Backend, failed
from harness.calculix import hex8_nodal_stress, read_dat_element_stresses, read_dat_total_forces, read_frd
from harness.checks import check
from harness.convergence import describe, discretization_uncertainty
from harness.study import Study
from studies.fin import find_ccx, read_dat_temperatures
from validation import graetz
from validation import plate_conduction as pc
from validation import thermal_stress as ts

CFD_WRITER = "models/cfd/cold_plate_openfoam.py"
RUNNER = "models/cfd/run_cold_plate.sh"
SOLID_WRITER = "models/thermal/cold_plate_ccx.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_ROOT = Path(__file__).resolve().parent.parent
_CW = _load(_ROOT / CFD_WRITER, "cold_plate_cfd_saved")
_SW = _load(_ROOT / SOLID_WRITER, "cold_plate_solid_saved")
PARAMS = _CW.PARAMS + _SW.PARAMS_SOLID + ("component_heat_flux_W_per_m2", "yield_strength_MPa",
                                         "interior_margin_mm", "uniform_check_rise_K")


def _p(params, k):
    return float(params[k])


def exact_rise_K(params):
    """Coolant temperature rise from the energy balance: both plates deliver q_c L_f."""
    H = _p(params, "gap_mm") * 1e-3
    return (2 * _p(params, "component_heat_flux_W_per_m2") * _p(params, "footprint_length_mm") * 1e-3
            / (_p(params, "density_kg_per_m3") * _p(params, "specific_heat_J_per_kgK")
               * _p(params, "mean_velocity_m_per_s") * H))


def footprint_mask(xc_mm, params):
    return (xc_mm > 0.0) & (xc_mm < _p(params, "footprint_length_mm"))


def wall_reference_region(edges_mm, q, gap_mm, tol):
    """Wall faces where the thermal-entry reference is compared, and the band excluded (mm).

    verification.wall_edge_exclusion_gaps (default 0: every face) excludes that many gap heights on
    each side of the plate's two edges. The wall flux steps there from zero to a spike; the wall
    temperature then goes like x^(1/3) (Leveque), which neither the reference (no axial conduction)
    nor a finite mesh resolves at the step itself. Outside the band the CFD converges to the
    reference at second order (cold_plate_mesh: 1.04 / 0.27 / 0.08 % at 20 / 40 / 80 cells, 2 gaps)."""
    edges = np.asarray(edges_mm, dtype=float)
    xc = 0.5 * (edges[1:] + edges[:-1])
    band = float(tol.get("wall_edge_exclusion_gaps", 0.0)) * float(gap_mm)
    on = np.flatnonzero(np.asarray(q) > 0)
    if band <= 0 or on.size == 0:
        return np.ones(xc.size, dtype=bool), 0.0
    x0, x1 = edges[on[0]], edges[on[-1] + 1]
    return (np.abs(xc - x0) >= band) & (np.abs(xc - x1) >= band), band


class ColdPlateChain(Backend):
    sources = (CFD_WRITER, RUNNER, SOLID_WRITER)

    def __init__(self):
        self.bashrc = of.find_openfoam_bashrc()
        self.ccx = find_ccx()
        self._versions: dict = {"openfoam_bashrc": self.bashrc}

    def prepare(self, source_dir=None, log_dir=None):
        self.cw = _load(self.source_path(CFD_WRITER, source_dir), "cold_plate_cfd_run")
        self.sw = _load(self.source_path(SOLID_WRITER, source_dir), "cold_plate_solid_run")
        self.runner = self.source_path(RUNNER, source_dir)
        r = subprocess.run([str(self.ccx), "-v"], capture_output=True, text=True, timeout=60)
        self._versions["CalculiX"] = (r.stdout.strip().splitlines() or ["?"])[-1]

    # ------------------------------------------------------------------ helpers
    def _foam(self, case: Path, mode: str):
        return subprocess.run(of.wsl_command("bash", of.to_wsl_path(self.runner), of.to_wsl_path(case),
                                             self.bashrc, mode),
                              capture_output=True, text=True, timeout=7200)

    def _ccx(self, work: Path, job: str):
        r = subprocess.run([str(self.ccx), "-i", job], cwd=work, capture_output=True, text=True, timeout=3600)
        (work / f"{job}.log").write_text(r.stdout + r.stderr, encoding="utf-8")
        return r.returncode == 0 and "Job finished" in r.stdout

    def solve(self, params, numerics, tolerance_scale=1.0):
        work = Path(tempfile.mkdtemp(prefix="cold_plate_"))
        case, solid = work / "case", work / "solid"
        solid.mkdir()
        cw, sw = self.cw, self.sw
        H = _p(params, "gap_mm")
        kf = _p(params, "conductivity_W_per_mK")
        hstar = _p(params, "coupling_htc_W_per_m2K")
        qc = _p(params, "component_heat_flux_W_per_m2")
        t_p = _p(params, "plate_thickness_mm")
        rise = exact_rise_K(params)

        fe = cw.face_edges_mm(params)            # every CFD wall face, inlet to outlet
        xc = 0.5 * (fe[1:] + fe[:-1])
        pm = cw.plate_faces(params)              # faces under the plate (contiguous)
        i0, npf = int(np.argmax(pm)), int(pm.sum())
        fe_p = fe[i0:i0 + npf + 1]
        fp = footprint_mask(xc[pm], params)
        q_outer = np.where(fp, qc, 0.0)          # per plate face
        q = q_outer.copy()                       # first guess: no spreading in the plate

        def full(v, fill=0.0):
            out = np.full(len(xc), fill)
            out[pm] = v
            return out

        info = cw.write_case(params, numerics, case, full(q))
        ny = int(params["cells_across_gap"])
        dx = fe[1] - fe[0]
        n_t = int(round(t_p / dx))
        grid = sw.Grid(fe_p, H, t_p, n_t)

        def files():
            out = {str(f.relative_to(case)).replace("\\", "/"): f
                   for f in sorted(case.glob("system/*")) + sorted(case.glob("constant/*"))
                   + sorted(case.glob("0/*")) + sorted(case.glob("log.*")) + sorted(case.glob("versions.txt"))
                   if f.is_file()} if case.exists() else {}
            for f in sorted(solid.glob("*")):
                if f.suffix in (".inp", ".dat", ".sta", ".log", ".csv") and f.stat().st_size < 60e6:
                    out[f"solid/{f.name}"] = f
            return out

        r = self._foam(case, "full")
        if r.returncode != 0:
            res = failed(f"OpenFOAM full run failed (exit {r.returncode}) {r.stderr.strip()[:300]}")
            return res | {"files": files(), "cleanup": work}
        for line in (case / "versions.txt").read_text(encoding="utf-8").splitlines():
            k_, _, v_ = line.partition("=")
            self._versions[k_] = v_
        n = info["cells"]
        cdir = next(d for d in sorted(case.iterdir(), key=lambda d: d.name) if (d / "C").exists())
        C = of.read_internal_field(cdir / "C", n) * 1e3                # mm
        fc_top = of.read_patch_value(cdir / "C", "wall_top")[:, 0] * 1e3
        fc_bot = of.read_patch_value(cdir / "C", "wall_bottom")[:, 0] * 1e3
        face_order_error = float(max(np.max(np.abs(fc_top - xc)), np.max(np.abs(fc_bot - xc))))
        if face_order_error > 1e-6:
            res = failed(f"wall faces are not in increasing x (max offset {face_order_error:.3g} mm)")
            return res | {"files": files(), "cleanup": work}
        dy = H / ny
        bot = np.where(np.abs(C[:, 1] - dy / 2) < 1e-6 * H)[0]
        top = np.where(np.abs(C[:, 1] - (H - dy / 2)) < 1e-6 * H)[0]
        bot, top = bot[np.argsort(C[bot, 0])], top[np.argsort(C[top, 0])]
        if len(bot) != len(xc) or len(top) != len(xc):
            res = failed("wall cells do not match the wall faces")
            return res | {"files": files(), "cleanup": work}

        n_flow, end = info["n_flow"], info["n_flow"] + info["n_temp"]
        n_pass = int(numerics["coupling_temperature_iterations"])
        omega = float(numerics.get("coupling_relaxation", 1.0))
        max_it = int(numerics["coupling_max_iterations"])
        tol_T = float(numerics["coupling_temperature_rel_tol"]) * rise
        tol_q = float(numerics["coupling_flux_rel_tol"]) * qc
        conn_wet = [(grid.nid(i, 0, 0), grid.nid(i + 1, 0, 0), grid.nid(i, 0, 1), grid.nid(i + 1, 0, 1))
                    for i in range(grid.nx)]
        accel = str(numerics.get("coupling_acceleration", "none"))
        prev_resid = None
        history = []
        converged = False
        for it in range(max_it):
            tdir = of.latest_time_dir(case)
            T = of.read_internal_field(tdir / "T", n)
            tw_bot = T[bot][pm] + q / kf * dy / 2 * 1e-3
            tw_top = T[top][pm] + q / kf * dy / 2 * 1e-3
            tw = 0.5 * (tw_bot + tw_top)
            t_ref = tw - q / hstar
            (solid / "thermal.inp").write_text(sw.write_thermal_deck(params, grid, q_outer, t_ref), encoding="utf-8")
            if not self._ccx(solid, "thermal"):
                res = failed(f"CalculiX heat transfer failed at coupling iteration {it}")
                return res | {"files": files(), "cleanup": work}
            Tn = read_dat_temperatures(solid / "thermal.dat", "NALL")
            ts_face = np.array([np.mean([Tn[a] for a in c]) for c in conn_wet])
            q_new = hstar * (ts_face - t_ref)
            mismatch = float(np.max(np.abs(ts_face - tw)))
            dq = float(np.max(np.abs(q_new - q)))
            history.append({"iteration": it, "cfd_end_time": end, "max_interface_dT_K": mismatch,
                            "max_flux_change_W_per_m2": dq,
                            "heat_into_coolant_outside_footprint": float(np.sum(q_new[~fp]) / np.sum(q_new))})
            if mismatch <= tol_T and dq <= tol_q:
                converged = True
                break
            if it == max_it - 1:
                break
            # Aitken dynamic relaxation (Irons-Tuck; Kuttler and Wall 2008) on the wall flux.
            # The plain fixed point contracts only by 1 - h*/h_fluid where the coolant's local
            # coefficient is far above h* (start of heating); Aitken removes that slow mode.
            resid = q_new - q
            if accel == "aitken" and prev_resid is not None:
                dr = resid - prev_resid
                omega = float(np.clip(-omega * np.dot(prev_resid, dr) / np.dot(dr, dr), -10.0, 10.0))
            history[-1]["relaxation"] = omega
            prev_resid = resid
            q = q + omega * resid
            # an over-relaxed step (|1 - omega| > 1) amplifies the rounding error of the total heat
            # each pass (1.4e-6 after 20 passes in the smoke test); the plate delivers exactly the
            # component heat, so restore that total
            q *= np.sum(q_outer * np.diff(fe_p)) / np.sum(q * np.diff(fe_p))
            cw.set_wall_flux(tdir / "T", full(q), kf)
            # the temperature stage writes only T; a restart needs the frozen flow fields too
            for f in (case / str(n_flow)).iterdir():
                if f.is_file() and not (tdir / f.name).exists():
                    shutil.copyfile(f, tdir / f.name)
            end += n_pass
            cw.set_end_time(case / "system" / "controlDict", end)
            r = self._foam(case, "temperature")
            if r.returncode != 0:
                res = failed(f"OpenFOAM temperature pass failed at coupling iteration {it} (exit {r.returncode})")
                return res | {"files": files(), "cleanup": work}

        # ------------------------------------------------ CFD results of the final pass
        times = sorted((d for d in case.iterdir() if d.is_dir() and d.name.replace(".", "").isdigit()
                        and float(d.name) > 0), key=lambda d: float(d.name))
        tdir = times[-1]
        T = of.read_internal_field(tdir / "T", n)
        T_prev = of.read_internal_field(times[-2] / "T", n)
        flow_dir = case / str(n_flow)
        Uf = of.read_internal_field(flow_dir / "U", n)
        phi_in = of.read_patch_value(flow_dir / "phi", "inlet")
        cols = np.unique(np.round(C[:, 0], 9))

        def column(x_target):
            xcol = cols[np.argmin(np.abs(cols - x_target))]
            return np.abs(C[:, 0] - xcol) < 1e-6

        out_col = column(fe[-1])
        u_out = Uf[out_col, 0]
        t_bulk_out = float(np.sum(u_out * T[out_col]) / np.sum(u_out))
        in_col = column(0.0)
        qf = full(q)
        tw_bot = T[bot] + qf / kf * dy / 2 * 1e-3       # every wall face
        tw_top = T[top] + qf / kf * dy / 2 * 1e-3

        # ------------------------------------------------ plate temperature field
        dat_T = Tn
        T_grid = np.array([[dat_T[grid.nid(i, j, 0)] for j in range(grid.ny + 1)] for i in range(grid.nx + 1)])
        T_back = np.array([[dat_T[grid.nid(i, j, 1)] for j in range(grid.ny + 1)] for i in range(grid.nx + 1)])

        # ------------------------------------------------ thermal stress, and the exact uniform case
        (solid / "stress.inp").write_text(sw.write_stress_deck(params, grid, dat_T), encoding="utf-8")
        t_uni = _p(params, "assembly_temperature_C") + _p(params, "uniform_check_rise_K")
        (solid / "uniform.inp").write_text(
            sw.write_stress_deck(params, grid, {nid: t_uni for nid in dat_T}), encoding="utf-8")
        for job in ("stress", "uniform"):
            if not self._ccx(solid, job):
                res = failed(f"CalculiX {job} solve failed")
                return res | {"files": files(), "cleanup": work}
        conn = grid.connectivity()

        def nodal(job):
            s = hex8_nodal_stress(read_dat_element_stresses(solid / f"{job}.dat"), conn)
            return np.array([[s[grid.nid(i, j, 0)] for j in range(grid.ny + 1)] for i in range(grid.nx + 1)])

        S = nodal("stress")               # (nx+1, ny+1, 6)
        S_uni = nodal("uniform")
        frd = read_frd(solid / "stress.frd")
        nt_ids, nt_vals = frd["NDTEMP"]["ids"], frd["NDTEMP"]["T"]
        handoff = float(max(abs(v - dat_T[int(i)]) for i, v in zip(nt_ids, nt_vals)))
        forces = read_dat_total_forces(solid / "stress.dat")
        frd_th = read_frd(solid / "thermal.frd")
        th_frd = dict(zip(frd_th["NDTEMP"]["ids"].tolist(), frd_th["NDTEMP"]["T"].tolist()))
        handoff_frd = float(max(abs(v - th_frd[int(i)]) for i, v in zip(nt_ids, nt_vals)))

        X = np.repeat(grid.x[:, None], grid.ny + 1, axis=1)
        Y = np.repeat(grid.y[None, :], grid.nx + 1, axis=0)
        series = {"x_mm": X.ravel(), "y_mm": Y.ravel(), "T_C": T_grid.ravel(),
                  "sxx_MPa": S[..., 0].ravel(), "syy_MPa": S[..., 1].ravel(),
                  "szz_MPa": S[..., 2].ravel(), "sxy_MPa": S[..., 3].ravel()}
        interface = np.column_stack([xc, pm.astype(float), qf, full(q_outer), tw_bot, tw_top,
                                     full(ts_face, np.nan), full(t_ref, np.nan)])
        np.savetxt(solid / "interface.csv", interface, delimiter=",", comments="",
                   header="x_mm,plate,wall_flux_W_per_m2,component_flux_W_per_m2,T_wall_bottom_C,"
                          "T_wall_top_C,T_plate_wetted_C,T_sink_C")
        uni = S_uni.reshape(-1, 6)
        outputs = {
            "cfd_cells": n, "blocks": [list(b) for b in info["blocks"]],
            "plate_divisions": [grid.nx, grid.ny],
            "mesh_ok": "Mesh OK." in (case / "log.checkMesh").read_text(encoding="utf-8"),
            "face_order_error_mm": face_order_error,
            "inlet_flow_m2_per_s": float(-np.sum(phi_in)) / (info["depth_mm"] * 1e-3),
            "peak_velocity_start_of_footprint_m_per_s": float(np.max(Uf[in_col, 0])),
            "T_change_last_write_K": float(np.max(np.abs(T - T_prev))),
            "previous_write": times[-2].name, "result_time": tdir.name,
            "outlet_bulk_C": t_bulk_out,
            "coupling_converged": converged, "coupling_iterations": len(history),
            "coupling_history": history,
            "final_interface_dT_K": history[-1]["max_interface_dT_K"],
            "final_flux_change_W_per_m2": history[-1]["max_flux_change_W_per_m2"],
            "heat_to_cfd_W_per_m": float(np.sum(qf * np.diff(fe)) * 1e-3),
            "heat_from_plate_W_per_m": float(np.sum(q_new * np.diff(fe_p)) * 1e-3),
            "heat_in_W_per_m": float(np.sum(q_outer * np.diff(fe_p)) * 1e-3),
            "wall_symmetry_max_K": float(np.max(np.abs(tw_top - tw_bot))),
            "depth_variation_max_K": float(np.max(np.abs(T_grid - T_back))),
            "temperature_handoff_max_K": handoff, "temperature_handoff_vs_frd_max_K": handoff_frd,
            "reaction_left_N": list(forces.get("NLEFT", (np.nan,) * 3)),
            "reaction_right_N": list(forces.get("NRIGHT", (np.nan,) * 3)),
            "plate_depth_mm": _SW.DEPTH_MM,
            "uniform_case_stress_MPa": {"sxx": [float(uni[:, 0].min()), float(uni[:, 0].max())],
                                        "syy_absmax": float(np.max(np.abs(uni[:, 1]))),
                                        "szz": [float(uni[:, 2].min()), float(uni[:, 2].max())],
                                        "sxy_absmax": float(np.max(np.abs(uni[:, 3])))},
            "frd_vs_extrapolated_sxx_max_MPa": None,
        }
        if "STRESS" in frd:
            sid = dict(zip(frd["STRESS"]["ids"].tolist(), frd["STRESS"]["SXX"].tolist()))
            ext = {grid.nid(i, j, 0): S[i, j, 0] for i in range(grid.nx + 1) for j in range(grid.ny + 1)}
            outputs["frd_vs_extrapolated_sxx_max_MPa"] = float(max(abs(sid[k] - v) for k, v in ext.items()))
        return {"success": True,
                "message": f"coupled in {len(history)} iterations ({'converged' if converged else 'NOT converged'}); "
                           f"{n} CFD cells, plate {grid.nx}x{grid.ny} hex",
                "nfev": len(history), "series": series, "outputs": outputs, "files": files(),
                "cleanup": work}

    def tool_versions(self):
        return self._versions


# ---------------------------------------------------------------------- field helpers

def to_grid(series):
    """Node grid arrays (nx+1, ny+1) from the flat nodal series."""
    xs = np.unique(np.round(series["x_mm"], 9))
    ys = np.unique(np.round(series["y_mm"], 9))
    shape = (len(xs), len(ys))
    order = np.lexsort((series["y_mm"], series["x_mm"]))
    g = {k: np.asarray(v)[order].reshape(shape) for k, v in series.items()}
    return xs, ys, g


def von_mises(sxx, syy, szz, sxy):
    return np.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2) + 3 * sxy**2)


def peak_along_x(xs, values, i):
    """Peak of a row near node i: parabola through i-1, i, i+1 (uniform spacing), else the node."""
    if 0 < i < len(xs) - 1 and np.isfinite(values[i - 1]) and np.isfinite(values[i + 1]):
        f0, f1, f2 = values[i - 1], values[i], values[i + 1]
        den = f0 - 2 * f1 + f2
        if den < 0:
            s = 0.5 * (f0 - f2) / den
            if abs(s) <= 1:
                return float(f1 - 0.25 * (f0 - f2) * s), float(xs[i] + s * (xs[1] - xs[0]))
    return float(values[i]), float(xs[i])


def interior_window(xs, params):
    m = _p(params, "interior_margin_mm")
    return (xs >= xs[0] + m - 1e-9) & (xs <= xs[-1] - m + 1e-9)


def interface_data(pdir: Path):
    a = np.loadtxt(pdir / "solver" / "solid" / "interface.csv", delimiter=",", skiprows=1)
    keys = ("x_mm", "plate", "q", "q_outer", "tw_bot", "tw_top", "ts", "t_ref")
    out = {k: a[:, i] for i, k in enumerate(keys)}
    dx = out["x_mm"][1] - out["x_mm"][0]
    out["edges_mm"] = np.concatenate([[out["x_mm"][0] - dx / 2], out["x_mm"] + dx / 2])
    out["plate"] = out["plate"] > 0.5
    return out


def plate_reference(params, xs, ys, iface):
    """Exact series temperature at every node, from the film data the plate actually had."""
    edges = xs - xs[0]
    L, t = float(xs[-1] - xs[0]), float(ys[-1] - ys[0])
    X, Y = np.meshgrid(xs - xs[0], ys - ys[0], indexing="ij")
    return pc.temperature(X, Y, L=L, t=t, k=_p(params, "plate_conductivity_W_per_mK") * 1e-3,
                          h=_p(params, "coupling_htc_W_per_m2K") * 1e-6,
                          q_edges=edges, q_values=iface["q_outer"][iface["plate"]] * 1e-6,
                          r_edges=edges, r_values=iface["t_ref"][iface["plate"]])


def stress_reference(params, xs, ys, T):
    return ts.clamped_strip(xs, ys, T - _p(params, "assembly_temperature_C"),
                            E=_p(params, "youngs_modulus_MPa"), nu=_p(params, "poisson_ratio"),
                            alpha=_p(params, "expansion_per_K"))


# ---------------------------------------------------------------------- study

class ColdPlateStudy(Study):
    name = "cold_plate"
    models = {"openfoam_ccx_cold_plate": ColdPlateChain}
    metrics = frozenset({"component_face_max_temperature_C", "coolant_rise_K",
                         "interior_von_mises_max_MPa", "wetted_wall_max_temperature_C",
                         "membrane_stress_MPa"})
    param_names = PARAMS
    series_file = "plate_nodes.csv"
    compare_description = "max relative difference over plate nodal columns"

    def derive(self, params):
        H = _p(params, "gap_mm") * 1e-3
        mu = _p(params, "dynamic_viscosity_Pa_s")
        rho, U = _p(params, "density_kg_per_m3"), _p(params, "mean_velocity_m_per_s")
        cp, kf = _p(params, "specific_heat_J_per_kgK"), _p(params, "conductivity_W_per_mK")
        t = _p(params, "plate_thickness_mm") * 1e-3
        ks = _p(params, "plate_conductivity_W_per_mK")
        L = (_p(params, "entry_length_mm") + _p(params, "footprint_length_mm") + _p(params, "exit_length_mm")) * 1e-3
        hfd = graetz.NU_FULLY_DEVELOPED * kf / (2 * H)
        Re = rho * U * 2 * H / mu
        E, nu, a = _p(params, "youngs_modulus_MPa"), _p(params, "poisson_ratio"), _p(params, "expansion_per_K")
        return {"reynolds_Dh": Re, "prandtl": mu * cp / kf, "peclet_Dh": Re * mu * cp / kf,
                "coolant_rise_exact_K": exact_rise_K(params),
                "h_fully_developed_W_per_m2K": hfd,
                "plate_biot": hfd * t / ks,
                "plate_spreading_length_mm": float(np.sqrt(ks * t / hfd)) * 1e3,
                "slab_dT_K": _p(params, "component_heat_flux_W_per_m2") * t / ks,
                "thickness_over_span": t / L,
                "buckling_stress_MPa": float(ts.clamped_strip_buckling_stress(E, nu, t * 1e3, L * 1e3)),
                "uniform_case_exact_MPa": ts.uniform_restrained_stress(E, nu, a, _p(params, "uniform_check_rise_K"))}

    def compute_metrics(self, series, params, case, outputs=None):
        xs, ys, g = to_grid(series)
        top = g["T_C"][:, -1]
        fpn = (xs >= -1e-9) & (xs <= _p(params, "footprint_length_mm") + 1e-9)
        vm = von_mises(g["sxx_MPa"], g["syy_MPa"], g["szz_MPa"], g["sxy_MPa"])
        win = interior_window(xs, params)
        vm_win = np.where(win[:, None], vm, -np.inf)
        i, j = np.unravel_index(np.argmax(vm_win), vm.shape)
        row = np.where(win, vm[:, j], -np.inf)
        vm_peak, _ = peak_along_x(xs, row, i)
        mid = np.argmin(np.abs(xs - 0.5 * (xs[0] + xs[-1])))
        sx_mid = g["sxx_MPa"][mid]
        membrane = float(np.sum(0.5 * (sx_mid[1:] + sx_mid[:-1]) * np.diff(ys)) / (ys[-1] - ys[0]))
        # peak located between nodes (parabola) unless it sits at an end of the footprint
        it = int(np.argmax(np.where(fpn, top, -np.inf)))
        t_peak, _ = peak_along_x(xs, np.where(fpn, top, -np.inf), it)
        return {"component_face_max_temperature_C": t_peak,
                "coolant_rise_K": outputs["outlet_bulk_C"] - _p(params, "inlet_temperature_C"),
                "interior_von_mises_max_MPa": vm_peak,
                "wetted_wall_max_temperature_C": float(np.max(g["T_C"][:, 0])),
                "membrane_stress_MPa": membrane}

    def verify_point(self, case, point, pdir: Path, series, backend):
        tol = case["verification"]
        p, d, m, out = point["parameters"], point["derived"], point["metrics"], point["solver_outputs"]
        rise = d["coolant_rise_exact_K"]
        H = _p(p, "gap_mm")
        U = _p(p, "mean_velocity_m_per_s")
        iface = interface_data(pdir)
        xs, ys, g = to_grid(series)
        T = g["T_C"]
        T_in = _p(p, "inlet_temperature_C")

        # CFD stage: wall temperature against the thermal-entry reference with the same flux
        ref_w = graetz.thermal_entry_profile(
            (iface["edges_mm"] - iface["edges_mm"][0]) * 1e-3, iface["q"], H=H * 1e-3, U=U, rho=_p(p, "density_kg_per_m3"),
            cp=_p(p, "specific_heat_J_per_kgK"), k=_p(p, "conductivity_W_per_mK"), T_in=T_in, n_cells=400)
        tw = 0.5 * (iface["tw_bot"] + iface["tw_top"])
        wall_mask, wall_band = wall_reference_region(iface["edges_mm"], iface["q"], H, tol)
        wall_err = float(np.max(np.abs(tw - ref_w["T_wall"])[wall_mask])) / rise
        heat_cfd = 2 * out["heat_to_cfd_W_per_m"] / (_p(p, "density_kg_per_m3") * _p(p, "specific_heat_J_per_kgK")
                                                     * U * H * 1e-3)

        # plate stage: exact 2D series with the film data the plate actually had
        T_ser = plate_reference(p, xs, ys, iface)
        plate_err = float(np.max(np.abs(T - T_ser))) / rise
        imid = np.argmin(np.abs(xs - 0.5 * _p(p, "footprint_length_mm")))
        slab = T[imid, -1] - T[imid, 0]
        # 1D slab with the mean of the flux entering (component) and leaving (into the coolant)
        q_wet_mid = float(np.interp(xs[imid], iface["x_mm"], iface["q"]))
        slab_ref = (_p(p, "plate_thickness_mm") * 1e-3 * 0.5 * (_p(p, "component_heat_flux_W_per_m2") + q_wet_mid)
                    / _p(p, "plate_conductivity_W_per_mK"))

        # stress stage
        ref = stress_reference(p, xs, ys, T)
        win = interior_window(xs, p)
        vm_ref = np.where(win[:, None], ref["von_mises"], -np.inf)
        iv, jv = np.unravel_index(np.argmax(vm_ref), vm_ref.shape)
        vm_ref_peak, _ = peak_along_x(xs, np.where(win, ref["von_mises"][:, jv], -np.inf), iv)
        sx_err = float(np.max(np.abs(g["sxx_MPa"][win] - ref["sigma_x"][win]))) / float(np.max(np.abs(ref["sigma_x"][win])))
        uni = out["uniform_case_stress_MPa"]
        s_ex = d["uniform_case_exact_MPa"]
        uni_err = max(abs(uni["sxx"][0] - s_ex), abs(uni["sxx"][1] - s_ex), abs(uni["szz"][0] - s_ex),
                      abs(uni["szz"][1] - s_ex), uni["syy_absmax"], uni["sxy_absmax"]) / abs(s_ex)
        rl, rr = np.array(out["reaction_left_N"]), np.array(out["reaction_right_N"])
        area = (ys[-1] - ys[0]) * out["plate_depth_mm"]
        membrane_fe = -rl[0] / area
        checks = [
            # ---- CFD
            check("cfd_mesh", "checkMesh reports Mesh OK (1 = failed)", 0.0 if out["mesh_ok"] else 1.0, 0.5),
            check("cfd_temperature_converged", "max |T change| over the last write interval of the final pass "
                  f"(iterations {out['previous_write']} to {out['result_time']}) / coolant rise",
                  out["T_change_last_write_K"] / rise, tol["temperature_change_rel_max"]),
            check("cfd_flow_rate", "|inlet flow - U H| / (U H)",
                  abs(out["inlet_flow_m2_per_s"] - U * H * 1e-3) / (U * H * 1e-3), tol["flow_rel_tol"]),
            check("cfd_developed_inflow", "|peak velocity at the start of the footprint - 1.5 U| / 1.5 U",
                  abs(out["peak_velocity_start_of_footprint_m_per_s"] - 1.5 * U) / (1.5 * U), tol["profile_rel_tol"]),
            check("cfd_energy_balance", "|outlet bulk rise - 2 (heat given to the CFD) / (rho cp U H)| / exact rise",
                  abs(m["coolant_rise_K"] - heat_cfd) / rise, tol["energy_rel_tol"]),
            check("cfd_wall_reference", "max over the wall of |T_wall CFD - thermal-entry reference with the same "
                  "flux profile| / coolant rise (model form: no axial conduction in the reference)"
                  + (f", outside {wall_band:g} mm of the plate edges (flux steps)" if wall_band else ""),
                  wall_err, tol["wall_rel_tol"]),
            check("cfd_wall_symmetry", "max |T_wall top - T_wall bottom| / coolant rise (symmetric case)",
                  out["wall_symmetry_max_K"] / rise, tol["symmetry_rel_tol"]),
            check("laminar", "Reynolds number (Dh) / 2000", d["reynolds_Dh"] / 2000, 1.0, kind="validity"),
            check("reference_assumption", "100 / Peclet (the CFD reference neglects axial conduction)",
                  100 / d["peclet_Dh"], 1.0, kind="validity"),
            # ---- coupling and handoffs
            check("coupling_converged", "coupling loop met both criteria within the iteration limit (1 = no)",
                  0.0 if out["coupling_converged"] else 1.0, 0.5),
            check("interface_temperature", "max |plate wetted-surface T - CFD wall T| / coolant rise, final iteration",
                  out["final_interface_dT_K"] / rise, tol["interface_temperature_rel_tol"]),
            check("interface_flux", "max |flux the plate returns - flux the CFD used| / component flux, final iteration",
                  out["final_flux_change_W_per_m2"] / _p(p, "component_heat_flux_W_per_m2"), tol["interface_flux_rel_tol"]),
            check("handoff_heat_to_cfd", "|heat the CFD received - component heat| / component heat",
                  abs(out["heat_to_cfd_W_per_m"] - out["heat_in_W_per_m"]) / out["heat_in_W_per_m"], tol["handoff_rel_tol"]),
            check("plate_energy_balance", "|heat the plate passes to the coolant - component heat| / component heat",
                  abs(out["heat_from_plate_W_per_m"] - out["heat_in_W_per_m"]) / out["heat_in_W_per_m"], tol["handoff_rel_tol"]),
            check("handoff_temperature_to_stress", "max |nodal T in the stress solve - thermal result| (K)",
                  out["temperature_handoff_max_K"], tol["temperature_handoff_abs_K"]),
            # ---- plate conduction
            check("plate_reference", "max over every node of |T FE - exact 2D series| / coolant rise",
                  plate_err, tol["plate_reference_rel_tol"]),
            check("plate_slab", "|outer - wetted T at mid-footprint - t (q_component + q_coolant) / 2k| / "
                  "slab estimate (model form: 1D slab, mean of the two face fluxes)",
                  abs(slab - slab_ref) / slab_ref, tol["slab_rel_tol"]),
            check("plate_plane", "max |T front - T back| of the one-element-deep plate (K)",
                  out["depth_variation_max_K"], 1e-9),
            # ---- thermal stress
            check("stress_uniform_exact", "uniform rise through the same deck and solver: max |sigma - "
                  "(-E alpha dT / (1 - nu))| and |sigma_y|, |tau_xy| over all nodes / exact",
                  uni_err, tol["uniform_exact_rel_tol"]),
            check("stress_reaction_balance", "|sum of support reactions (x, y)| / |end reaction|",
                  float(np.hypot(rl[0] + rr[0], rl[1] + rr[1])) / abs(rl[0]), tol["reaction_rel_tol"]),
            check("stress_membrane_reference", "|membrane stress from the end reaction - beam theory N / t| / |N / t|",
                  abs(membrane_fe - ref["membrane_stress"]) / abs(ref["membrane_stress"]), tol["membrane_rel_tol"]),
            check("stress_peak_reference", "|interior peak von Mises FE - beam theory| / beam theory (model form)",
                  abs(m["interior_von_mises_max_MPa"] - vm_ref_peak) / vm_ref_peak, tol["stress_peak_rel_tol"]),
            check("stress_field_reference", "max over the interior of |sigma_x FE - beam theory| / max |sigma_x| "
                  "(model form)", sx_err, tol["stress_field_rel_tol"]),
            check("linear_material", "interior peak von Mises / yield strength", m["interior_von_mises_max_MPa"]
                  / _p(p, "yield_strength_MPa"), 1.0, kind="validity"),
            check("no_buckling", "|membrane stress| / clamped-strip buckling stress (linear analysis)",
                  abs(membrane_fe) / d["buckling_stress_MPa"], tol["buckling_ratio_max"], kind="validity"),
            check("thin_plate", "plate thickness / span (beam-theory reference)", d["thickness_over_span"],
                  tol["thickness_over_span_max"], kind="validity"),
        ]
        cold_plate_figure(pdir / "response.png", p, d, m, out, iface, ref_w, xs, ys, g, T_ser, ref,
                          title=(f"{point['label']}  ({out['cfd_cells']} CFD cells, plate "
                                 f"{out['plate_divisions'][0]}x{out['plate_divisions'][1]} hex, "
                                 f"{out['coupling_iterations']} coupling iterations)"))
        return checks

    def verify_run_level(self, case, manifest, points):
        if case.get("sweep", {}).get("parameter") != "cells_across_gap":
            return [], {}
        tol = case["verification"]
        done = sorted((pt for pt in manifest["points"] if pt["status"] == "completed"),
                      key=lambda pt: -int(pt["parameters"]["cells_across_gap"]))
        if len(done) < 3:
            return [check("mesh_convergence_gci", "needs >= 3 completed mesh levels", float("inf"), 0.0)], {}
        fine = done[:3]
        hs = tuple(1.0 / int(pt["parameters"]["cells_across_gap"]) for pt in fine)
        checks, detail = [], {"meshes_used": [pt["label"] for pt in fine]}
        for metric in sorted({r["metric"] for r in case["requirements"]}):
            offset = (lambda pt: pt["parameters"]["inlet_temperature_C"]) if metric.endswith("_C") else (lambda pt: 0.0)
            vals = tuple(pt["metrics"][metric] - offset(pt) for pt in fine)
            u = discretization_uncertainty(hs, vals, design_order=2)
            detail[metric] = u
            how = "rise above inlet, " if metric.endswith("_C") else ""
            checks.append(check(f"discretization_{metric}",
                                f"relative discretization uncertainty of {metric} ({how}{describe(u)})",
                                u["uncertainty"], tol["gci_max"]) | {"metric": metric})
        return checks, detail


# ---------------------------------------------------------------------- figure

def cold_plate_figure(path, p, d, m, out, iface, ref_w, xs, ys, g, T_ser, ref, *, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from harness.plotting import GRID, SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2

    fig, ax = plt.subplots(2, 2, figsize=(12, 7.6), facecolor=SURFACE)
    a1, a2, a3, a4 = ax.ravel()
    x = iface["x_mm"]
    a1.plot(x, iface["q_outer"] / 1e3, color=TEXT_2, lw=1.2, ls="--", label="component flux on the outer face")
    a1.plot(x, iface["q"] / 1e3, color=SERIES_1, lw=1.8, label="flux into the coolant (converged)")
    a1.set_ylabel("heat flux (kW/m²)")
    a1.set_title("Heat spreads along the plate before it reaches the coolant", color=TEXT, loc="left", fontsize=10)

    tw = 0.5 * (iface["tw_bot"] + iface["tw_top"])
    a2.plot(x, ref_w["T_wall"], color=SERIES_2, lw=2, label="wall, thermal-entry reference (same flux)")
    a2.plot(x, tw, ".", ms=2, color=SERIES_1, label="wall, OpenFOAM")
    a2.plot(xs, g["T_C"][:, -1], color=TEXT, lw=1.4, label="plate outer face (component side), CalculiX")
    a2.plot(xs, T_ser[:, -1], color=SERIES_2, lw=0.8, ls=":", label="outer face, exact series")
    req = 45.0
    a2.set_ylabel("temperature (°C)")
    a2.set_title("Temperatures through the chain", color=TEXT, loc="left", fontsize=10)

    X, Y = np.meshgrid(xs, ys, indexing="ij")
    cs = a3.contourf(X, Y, g["T_C"], levels=14, cmap="turbo")
    a3.set_aspect(4)
    fig.colorbar(cs, ax=a3, label="°C", fraction=0.04)
    a3.set_ylabel("y (mm), plate drawn 4× thicker")
    a3.set_title("Plate temperature (CalculiX)", color=TEXT, loc="left", fontsize=10)

    vm = von_mises(g["sxx_MPa"], g["syy_MPa"], g["szz_MPa"], g["sxy_MPa"])
    a4.plot(xs, vm[:, -1], color=SERIES_1, lw=1.8, label="von Mises, outer face, FE")
    a4.plot(xs, ref["von_mises"][:, -1], color=SERIES_2, lw=1, ls="--", label="outer face, beam theory")
    a4.plot(xs, vm[:, 0], color=TEXT_2, lw=1.2, label="von Mises, wetted face, FE")
    a4.plot(xs, ref["von_mises"][:, 0], color=SERIES_2, lw=1, ls=":", label="wetted face, beam theory")
    win = interior_window(xs, p)
    a4.axvspan(xs[0], xs[win][0], color=GRID, alpha=0.6, lw=0)
    a4.axvspan(xs[win][-1], xs[-1], color=GRID, alpha=0.6, lw=0, label="support regions (not assessed)")
    a4.set_ylim(0, 1.25 * float(np.max(ref["von_mises"])))
    a4.set_ylabel("stress (MPa)")
    a4.set_title("Thermal stress, plate held by its frame", color=TEXT, loc="left", fontsize=10)
    for a in (a1, a2, a3, a4):
        a.set_xlabel("x along the flow (mm)")
        a.grid(color=GRID, lw=0.6)
        a.tick_params(colors=TEXT_2)
        for s in a.spines.values():
            s.set_color(GRID)
    for a in (a1, a2, a4):
        a.legend(frameon=False, fontsize=8, labelcolor=TEXT_2)
    fig.suptitle(title, color=TEXT, fontsize=10, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=130, facecolor=SURFACE)
    plt.close(fig)


STUDY = ColdPlateStudy()

"""Electric-machine electromagnetics through Pyleecan + FEMM (study 7). Runs in the Pyleecan environment.

usage: <pyleecan python> pyleecan_em.py <params.json> <out.json>

Params: machine (a file in Pyleecan's data/Machine, e.g. Toyota_Prius.json, or the absolute path of one of our own
machine files, which the backend resolves from the run's inputs), speed_rpm, mesh_fineness (MagFEMM
Kmesh_fineness), steps_per_period (time steps per ELECTRICAL period; Pyleecan's Nt_tot counts a whole mechanical
revolution, so Nt_tot = steps_per_period x pole pairs: 24 for the Prius gave only 6 samples per electrical period),
angle_points (Na_tot), and the current, either
  - id_A, iq_A: one operating point. These are RMS dq currents: Pyleecan's OPdq documents Id_ref and Iq_ref as rms
    values (an earlier version of this docstring said peak; every case before the torque study had zero current), or
  - current_rms_A with angle_min_deg, angle_max_deg, angle_steps: a sweep of the current angle gamma, measured from the
    q axis towards negative d (Id = -I sin gamma, Iq = I cos gamma), one FEMM simulation per angle.

Writes: for each operating point, one electrical period of the three phase flux linkages, the three phase currents
Pyleecan imposed and the torque (Pyleecan reconstructs the period from the time periodicity); for the first point,
the radial air-gap flux density at t = 0 over the smallest angular period; and the machine data the checks need
(air-gap radius, stack length, pole pairs, series turns per phase, fundamental winding factor). Nothing here is
compared with test data.
"""

from __future__ import annotations

import json
import sys
import time
from os.path import join
from pathlib import Path

import numpy as np


def solve_op(m, p, id_rms, iq_rms, with_gap=False):
    from pyleecan.Classes.InputCurrent import InputCurrent
    from pyleecan.Classes.MagFEMM import MagFEMM
    from pyleecan.Classes.OPdq import OPdq
    from pyleecan.Classes.Simu1 import Simu1

    simu = Simu1(name="em", machine=m)
    nt = int(p["steps_per_period"]) * int(m.get_pole_pair_number())
    simu.input = InputCurrent(OP=OPdq(N0=float(p["speed_rpm"]), Id_ref=float(id_rms), Iq_ref=float(iq_rms)),
                              Na_tot=int(p["angle_points"]), Nt_tot=nt)
    simu.mag = MagFEMM(is_periodicity_a=True, is_periodicity_t=True, nb_worker=1,
                       Kmesh_fineness=float(p["mesh_fineness"]))
    simu.force = None
    simu.struct = None
    t0 = time.time()
    out = simu.run()
    wall = time.time() - t0

    phi = out.mag.Phi_wind_stator.get_along("time[oneperiod]", "phase")
    tq = out.mag.Tem.get_along("time[oneperiod]")
    Is = out.elec.get_Is().get_along("time[oneperiod]", "phase")
    sym_i = [k for k in Is if k not in ("time", "phase")][0]
    # Pyleecan applies no time periodicity to the electrical output: it returns a whole mechanical revolution. Put the
    # currents on the flux linkages' time axis (one electrical period); the samples coincide, so this is a selection.
    tp, ti = np.asarray(phi["time"]).ravel(), np.asarray(Is["time"]).ravel()
    ci = np.asarray(Is[sym_i])
    ci = ci if ci.shape[0] == len(ti) else ci.T
    idx = [int(np.argmin(np.abs(ti - x))) for x in tp]
    if max(abs(ti[idx] - tp)) > 1e-9 * max(tp[-1], 1e-12):
        raise RuntimeError("current and flux-linkage time samples do not coincide")
    Is = {"time": tp, sym_i: ci[idx]}
    r = {
        "id_rms_A": float(id_rms), "iq_rms_A": float(iq_rms),
        "time_s": np.asarray(phi["time"]).ravel().tolist(),
        "phi_Wb": np.asarray(phi[out.mag.Phi_wind_stator.symbol]).tolist(),
        "current_time_s": np.asarray(Is["time"]).ravel().tolist(),
        "current_A": np.asarray(Is[sym_i]).tolist(),
        "torque_time_s": np.asarray(tq["time"]).ravel().tolist(),
        "torque_Nm": np.asarray(tq[out.mag.Tem.symbol]).ravel().tolist(),
        "wall_s": wall,
    }
    if with_gap:
        b = out.mag.B.get_rphiz_along("angle[smallestperiod]", "time[0]")
        r["gap_angle_rad"] = np.asarray(b["angle"]).ravel().tolist()
        r["gap_Br_T"] = np.asarray(b["radial"]).ravel().tolist()
    return r


def main(params_path: str, out_path: str) -> None:
    from pyleecan.definitions import DATA_DIR
    from pyleecan.Functions.load import load
    import pyleecan

    p = json.loads(open(params_path, encoding="utf-8").read())
    mp = Path(p["machine"])
    m = load(str(mp) if mp.is_absolute() else join(DATA_DIR, "Machine", p["machine"]))
    if p.get("current_rms_A") is not None:
        I = float(p["current_rms_A"])
        gammas = np.linspace(float(p["angle_min_deg"]), float(p["angle_max_deg"]), int(p["angle_steps"]))
        ops = [solve_op(m, p, -I * np.sin(np.radians(g)), I * np.cos(np.radians(g)), with_gap=(i == 0)) | {"gamma_deg": g}
               for i, g in enumerate(gammas)]
    else:
        ops = [solve_op(m, p, p["id_A"], p["iq_A"], with_gap=True)]
    w = m.stator.winding
    res = {
        "ops": ops,
        # the first operating point at the top level, as the open-circuit study reads it
        **{k: ops[0][k] for k in ("time_s", "phi_Wb", "torque_time_s", "torque_Nm", "gap_angle_rad", "gap_Br_T")},
        "gap_radius_m": float(m.comp_Rgap_mec()),
        "stack_length_m": float(m.stator.L1),
        "pole_pairs": int(m.get_pole_pair_number()),
        "series_turns_per_phase": float(w.comp_Ntsp(Zs=m.stator.get_Zs())),
        "winding_factor_1": float(np.asarray(w.comp_winding_factor()).ravel()[0]),
        "slots": int(m.stator.get_Zs()),
        "wall_s": float(sum(o["wall_s"] for o in ops)),
        "pyleecan_version": getattr(pyleecan, "__version__", "?"),
    }
    open(out_path, "w", encoding="utf-8").write(json.dumps(res))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

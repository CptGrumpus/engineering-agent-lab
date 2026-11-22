"""Electric-machine electromagnetics through Pyleecan + FEMM (study 7). Runs in the Pyleecan environment.

usage: <pyleecan python> pyleecan_em.py <params.json> <out.json>

Params: machine (a file in Pyleecan's data/Machine, e.g. Toyota_Prius.json, or the absolute path of one of our own
machine files, which the backend resolves from the run's inputs), speed_rpm, id_A and iq_A (peak dq
currents, Pyleecan's convention), mesh_fineness (MagFEMM Kmesh_fineness), steps_per_period (time steps per ELECTRICAL period;
Pyleecan's Nt_tot counts a whole mechanical revolution, so Nt_tot = steps_per_period x pole pairs: 24 for the
Prius gave only 6 samples per electrical period), angle_points (Na_tot).

Writes: one electrical period of the three phase flux linkages and the torque (Pyleecan reconstructs it from the
time periodicity), the radial air-gap flux density at t = 0 over the smallest angular period, and the machine
data the checks need (air-gap radius, stack length, pole pairs, series turns per phase, fundamental winding
factor). Nothing here is compared with test data.
"""

from __future__ import annotations

import json
import sys
import time
from os.path import join
from pathlib import Path

import numpy as np


def main(params_path: str, out_path: str) -> None:
    from pyleecan.Classes.InputCurrent import InputCurrent
    from pyleecan.Classes.MagFEMM import MagFEMM
    from pyleecan.Classes.OPdq import OPdq
    from pyleecan.Classes.Simu1 import Simu1
    from pyleecan.definitions import DATA_DIR
    from pyleecan.Functions.load import load
    import pyleecan

    p = json.loads(open(params_path, encoding="utf-8").read())
    mp = Path(p["machine"])
    m = load(str(mp) if mp.is_absolute() else join(DATA_DIR, "Machine", p["machine"]))
    simu = Simu1(name="em", machine=m)
    nt = int(p["steps_per_period"]) * int(m.get_pole_pair_number())
    simu.input = InputCurrent(OP=OPdq(N0=float(p["speed_rpm"]), Id_ref=float(p["id_A"]), Iq_ref=float(p["iq_A"])),
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
    b = out.mag.B.get_rphiz_along("angle[smallestperiod]", "time[0]")
    w = m.stator.winding
    res = {
        "time_s": np.asarray(phi["time"]).ravel().tolist(),
        "phi_Wb": np.asarray(phi[out.mag.Phi_wind_stator.symbol]).tolist(),
        "torque_time_s": np.asarray(tq["time"]).ravel().tolist(),
        "torque_Nm": np.asarray(tq[out.mag.Tem.symbol]).ravel().tolist(),
        "gap_angle_rad": np.asarray(b["angle"]).ravel().tolist(),
        "gap_Br_T": np.asarray(b["radial"]).ravel().tolist(),
        "gap_radius_m": float(m.comp_Rgap_mec()),
        "stack_length_m": float(m.stator.L1),
        "pole_pairs": int(m.get_pole_pair_number()),
        "series_turns_per_phase": float(w.comp_Ntsp(Zs=m.stator.get_Zs())),
        "winding_factor_1": float(np.asarray(w.comp_winding_factor()).ravel()[0]),
        "slots": int(m.stator.get_Zs()),
        "wall_s": wall,
        "pyleecan_version": getattr(pyleecan, "__version__", "?"),
    }
    open(out_path, "w", encoding="utf-8").write(json.dumps(res))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

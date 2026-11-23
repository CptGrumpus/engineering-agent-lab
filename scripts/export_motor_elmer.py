"""Run in the Pyleecan environment: export a machine's cross-section and materials for the independent Elmer model
(study 7, the 18 % diagnosis: a second 2D solver on the same geometry; models/motor/elmer_em.py reads the result).

    PYTHONUTF8=1 ~/.venvs/pyleecan/Scripts/python.exe scripts/export_motor_elmer.py <machine.json> <out.json> [T_mag_C]

Exact geometry: every boundary as a segment or an arc (begin, end, centre, signed angle), not a polyline (a 24-point
arc across the 0.775 mm gap sags 0.011 mm). Everything FEMM receives is taken from the same Pyleecan calls FEMM's
driver uses (pyleecan/Functions/FEMM): the magnetisation angle per magnet (assign_FEMM_surface: pole centre + the
hole's comp_magnetization_dict, +180 deg on odd poles), the phase and signed turns per winding zone (get_connection_mat,
get_phase_id), the magnet coercivity Hc(T) = Br(T) / (mu0 mu_r) (create_FEMM_magnet) and the laminations' B-H curve
(get_BH, fill factor 1 as in create_FEMM_materials). The rotor is exported at Pyleecan's angle 0; the Elmer model
rotates it.
"""
import json
import sys
from math import floor, pi

import numpy as np
from numpy import angle
from pyleecan.Functions.labels import decode_label
from pyleecan.Functions.Winding.find_wind_phase_color import get_phase_id
from pyleecan.Functions.load import load


def line_dict(ln):
    b, e = complex(ln.get_begin()), complex(ln.get_end())
    d = {"kind": "seg", "b": [b.real, b.imag], "e": [e.real, e.imag]}
    if type(ln).__name__ != "Segment":
        c = complex(ln.get_center())
        d.update(kind="arc", c=[c.real, c.imag], angle=float(ln.get_angle(is_deg=False)))
    return d


def loops_of(surf):
    if type(surf).__name__ == "SurfRing":
        return [[line_dict(l) for l in surf.out_surf.get_lines()], [line_dict(l) for l in surf.in_surf.get_lines()]]
    return [[line_dict(l) for l in surf.get_lines()]]


def main(machine_path, out_path, t_mag=20.0):
    m = load(machine_path)
    out = {"machine": machine_path, "T_mag_C": t_mag, "surfaces": []}
    wind = m.stator.winding
    wm = wind.get_connection_mat(m.stator.get_Zs())
    for s in m.build_geometry(sym=1):
        ld = decode_label(s.label)
        st, lam = ld["surf_type"], ld["lam_type"]
        rec = {"label": s.label, "loops": None, "ref": [complex(s.point_ref).real, complex(s.point_ref).imag]}
        if "Shaft" in s.label:
            continue
        if "Lamination" in st:
            rec["kind"] = "stator_lam" if "Stator" in lam else "rotor_lam"
        elif "HoleMag" in st:
            mag = ld["obj"] if "obj" in ld else None
            hole = m.rotor.hole[ld["R_id"]]
            alpha_p = 360 / hole.Zh
            ref = complex(s.point_ref)
            mag0 = (floor(angle(ref, deg=True) / alpha_p) + 0.5) * alpha_p
            md = hole.comp_magnetization_dict()
            deg = mag0 + md["magnet_" + str(ld["T_id"])] * 180 / pi
            if ld["S_id"] % 2 == 1:
                deg += 180
            magobj = hole.get_magnet_dict()["magnet_" + str(ld["T_id"])]
            if magobj.type_magnetization not in (1, None):
                raise NotImplementedError(f"{s.label}: only parallel magnetisation is exported")
            rec.update(kind="magnet", mag_deg=float(deg))
        elif "HoleVoid" in st:
            rec["kind"] = "void"
        elif "Winding" in st:
            q = get_phase_id(wm, ld["R_id"], ld["T_id"], ld["S_id"])
            rec.update(kind="winding", phase=int(q), turns=float(wm[ld["R_id"], ld["T_id"], ld["S_id"], q]))
        else:
            raise ValueError(f"unexpected surface {s.label}")
        rec["side"] = "stator" if "Stator" in lam else "rotor"
        rec["loops"] = loops_of(s)
        out["surfaces"].append(rec)
    mag = m.rotor.hole[0].get_magnet_dict()["magnet_0"].mat_type.mag
    bh_s = np.asarray(m.stator.mat_type.mag.get_BH(), float)
    bh_r = np.asarray(m.rotor.mat_type.mag.get_BH(), float)
    out["materials"] = {
        "magnet": {"name": m.rotor.hole[0].get_magnet_dict()["magnet_0"].mat_type.name, "Brm20_T": mag.Brm20,
                   "alpha_Br": mag.alpha_Br, "mur": mag.mur_lin, "Br_T": float(mag.get_Brm(T_op=t_mag)),
                   "Hc_A_per_m": float(mag.get_Hc(T_op=t_mag))},
        "stator_steel": {"name": m.stator.mat_type.name, "H_B": bh_s.tolist()},
        "rotor_steel": {"name": m.rotor.mat_type.name, "H_B": bh_r.tolist()},
    }
    out["dims"] = {"stator_Rext": m.stator.Rext, "stator_Rint": m.stator.Rint, "rotor_Rext": m.rotor.Rext,
                   "rotor_Rint": m.rotor.Rint, "L_m": m.stator.L1, "pole_pairs": m.get_pole_pair_number(),
                   "slots": m.stator.get_Zs(), "Npcp": wind.Npcp, "qs": wind.qs}
    json.dump(out, open(out_path, "w"), indent=1)
    kinds = {}
    for r in out["surfaces"]:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    print(kinds, out["materials"]["magnet"], out["dims"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 20.0)

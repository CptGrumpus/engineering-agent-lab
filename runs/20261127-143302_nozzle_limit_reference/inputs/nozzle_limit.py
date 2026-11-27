"""Limit-load analysis of the study-18 nozzle (the method of ASME BPVC VIII-2 Part 5.2.3): the same quarter model as
models/fea/pressure_vessel.py, elastic-perfectly plastic (von Mises, yield = 1.5 S), small displacement theory, the
pressure and its end thrusts ramped together to a load factor lambda_max times the design pressure. The analysis
stops when the equilibrium iterations no longer converge; the last converged load factor is the collapse load factor.
Part 5.2.3 asks that the analysis converge at 1.5 times the design load: collapse factor >= 1.5.

Optional plain_shell = 1 leaves the nozzle out (the same shell, the same mesh sizing, the same loads without the
nozzle's): a closed-end cylinder, whose collapse pressure is known exactly, p_L = (2 / sqrt 3) sigma_y ln(Ro / Ri)
(Hill 1950, von Mises, perfectly plastic; the closed-end axial load is carried with sigma_z the mean of the other two).

Monitored at each increment: the reactions (they must equal lambda times the exact pressure resultants) and the
displacements of three nodes: the shell's outer surface at the weld toe in the plane along the vessel, the crotch
corner, and the far shell's outer surface.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from models.fea import pressure_vessel as pv

PARAMS = pv.PARAMS + ("allowable_stress_MPa", "load_factor_max")
OPTIONAL = {"plain_shell": 0, "initial_increment": 0.1, "min_increment": 1e-4, "max_increment": 0.25,
            "load_step": 0.1}


def opt(p: dict, k: str) -> float:
    return float(p.get(k, OPTIONAL[k]))


def yield_stress(p: dict) -> float:
    return 1.5 * float(p["allowable_stress_MPa"])


def schedule(p: dict) -> list[float]:
    """Load factor at the end of each step: 1, 1.5 (the code's check), then load_step apart up to load_factor_max."""
    lam, dl = float(p["load_factor_max"]), opt(p, "load_step")
    out = [1.0, 1.5]
    while out[-1] + dl < lam - 1e-9:
        out.append(round(out[-1] + dl, 9))
    return out + [lam] if lam > 1.5 + 1e-9 else out


def collapse_pressure_cylinder(p: dict) -> float:
    d = pv.dims(p)
    return 2 / math.sqrt(3) * yield_stress(p) * math.log(d["Ro"] / d["Ri"])


def build_step(p: dict, path: Path) -> dict:
    if not opt(p, "plain_shell"):
        return pv.build_step(p, path)
    import cadquery as cq

    d = pv.dims(p)
    body = (cq.Workplane("XY").circle(d["Ro"]).extrude(d["L"])
            .cut(cq.Workplane("XY").workplane(offset=-1).circle(d["Ri"]).extrude(d["L"] + 2)))
    body = body.intersect(cq.Workplane("XY").box(2 * d["Ro"] + 10, d["Ro"] + 10, d["L"], centered=(True, False, False)))
    cq.exporters.export(body, str(path))
    v = body.val()
    return {"volume_mm3": float(v.Volume()), "volume_hand_mm3": math.pi * (d["Ro"] ** 2 - d["Ri"] ** 2) / 2 * d["L"],
            "faces": len(v.Faces()), "valid": bool(v.isValid())}


def expected_reactions(p: dict) -> dict:
    """Exact resultants at load factor 1 (pressure_vessel.expected_reactions; without the nozzle's terms for the plain
    shell)."""
    if not opt(p, "plain_shell"):
        return pv.expected_reactions(p)
    d = pv.dims(p)
    pr = float(p["pressure_MPa"])
    return {"Ry_N": -pr * 2 * d["Ri"] * d["L"], "Rz_N": -pr * math.pi * d["Ri"] ** 2 / 2, "Rx_back_N": 0.0,
            "nozzle_thrust_scale_N": pr * math.pi * d["rni"] ** 2 / 4}


def write_deck(p: dict, mesh_inp: Path, deck: Path) -> dict:
    d = pv.dims(p)
    ids, xyz, eids, elems = pv.read_mesh(mesh_inp)
    row = {int(n): k for k, n in enumerate(ids)}
    conn = np.vectorize(row.get)(elems)
    tol = 1e-4 * d["Ro"]
    plain = bool(opt(p, "plain_shell"))
    surf = {
        "shell_bore": lambda X: np.abs(np.hypot(X[:, 0], X[:, 1]) - d["Ri"]) < tol,
        "shell_end": lambda X: np.abs(X[:, 2] - d["L"]) < tol,
    }
    if not plain:
        surf["nozzle_bore"] = lambda X: (np.abs(np.hypot(X[:, 1], X[:, 2]) - d["rni"]) < tol) & (X[:, 0] > 0)
        surf["nozzle_end"] = lambda X: np.abs(X[:, 0] - d["Xend"]) < tol
    faces = {k: pv.loaded_faces(xyz, conn, f) for k, f in surf.items()}
    lam = float(p["load_factor_max"])
    pr = float(p["pressure_MPa"]) * lam
    q_shell = pr * d["Ri"] ** 2 / (d["Ro"] ** 2 - d["Ri"] ** 2)
    q_noz = pr * d["rni"] ** 2 / (d["rno"] ** 2 - d["rni"] ** 2)
    near = lambda pt: int(ids[int(np.argmin(np.linalg.norm(xyz - np.asarray(pt, float), axis=1)))])  # noqa: E731
    sym_y, sym_z = ids[np.abs(xyz[:, 1]) < tol], ids[np.abs(xyz[:, 2]) < tol]
    back = near((-d["Ro"], 0.0, 0.0))
    mon = {"NTOE": near((d["Ro"], 0.0, d["rno"] + d["rf"])), "NCROTCH": near((d["Ri"], 0.0, d["rni"])),
           "NFAR": near((-d["Ro"], 0.0, d["L"] / 2))}
    rows = lambda a: [", ".join(str(int(v)) for v in a[s:s + 12]) for s in range(0, len(a), 12)]  # noqa: E731
    E, nu = float(p["youngs_modulus_MPa"]), float(p["poisson_ratio"])
    lines = [f"*INCLUDE, INPUT={Path(mesh_inp).name}", "*NSET, NSET=NSYMY"] + rows(sym_y) + ["*NSET, NSET=NSYMZ"] + \
        rows(sym_z) + ["*NSET, NSET=NBACK", str(back)]
    for k, n in mon.items():
        lines += [f"*NSET, NSET={k}", str(n)]
    lines += ["*MATERIAL, NAME=STEEL", "*ELASTIC", f"{E!r}, {nu!r}", "*PLASTIC", f"{yield_stress(p)!r}, 0.",
              "*SOLID SECTION, ELSET=VESSEL, MATERIAL=STEEL",
              "*BOUNDARY", "NSYMY, 2, 2, 0.", "NSYMZ, 3, 3, 0.", "NBACK, 1, 1, 0."]
    # One step per load factor (each of step time 1, the loads ramped from the previous step's): CalculiX writes
    # neither the .dat prints of a step that stops on non-convergence nor its increments, so the history is kept at
    # the step ends and the collapse is located inside the last step from the .sta file. The stress and plastic strain
    # field is written at 1.5 (the code's load) and at the stop.
    sched = schedule(p)
    lo = [("shell_bore", 1.0), ("shell_end", -q_shell / pr)] + \
        ([] if plain else [("nozzle_bore", 1.0), ("nozzle_end", -q_noz / pr)])
    for k, lk in enumerate(sched):
        pk = float(p["pressure_MPa"]) * lk
        lines += ["*STEP, NLGEOM=NO, INC=2000", "*STATIC",
                  f"{opt(p, 'initial_increment')!r}, 1., {opt(p, 'min_increment')!r}, {opt(p, 'max_increment')!r}",
                  "*DLOAD"]
        for key, f_ in lo:
            lines += [f"{int(eids[e])}, P{f}, {pk * f_!r}" for e, f in faces[key]]
        lines += ["*NODE PRINT, NSET=NSYMY, TOTALS=ONLY", "RF", "*NODE PRINT, NSET=NSYMZ, TOTALS=ONLY", "RF",
                  "*NODE PRINT, NSET=NBACK", "RF"] + sum(([f"*NODE PRINT, NSET={m}", "U"] for m in mon), [])
        if abs(lk - 1.5) < 1e-9:
            lines += ["*NODE FILE, FREQUENCY=1000", "U", "*EL FILE, FREQUENCY=1000", "S, PEEQ"]
        lines.append("*END STEP")
    deck.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"nodes": int(len(ids)), "elements": int(len(eids)), "monitor_nodes": mon, "back_node": back,
            **{f"faces_{k}": len(v) for k, v in faces.items()}}


def last_converged(sta: Path) -> tuple[int, float] | None:
    """(step, step time) of the last converged increment in a CalculiX .sta file (attempts marked U did not converge)."""
    best = None
    for ln in Path(sta).read_text(encoding="latin-1").splitlines():
        v = ln.split()
        if len(v) == 7 and v[0].isdigit() and v[1].isdigit() and not v[2].endswith("U"):
            best = (int(v[0]), float(v[5]))
    return best


def read_history(dat: Path, sta: Path, sched: list[float]) -> dict:
    """At each completed step's end: load factor, reactions, monitored displacements (the .dat blocks; a step's total
    time at its end is its number). The collapse load factor is the last converged increment's, inside its step."""
    from studies.strut_buckling import read_dat_blocks

    blocks = read_dat_blocks(dat)
    by = {(round(b["time"]), b["set"]): b for b in blocks}
    h = {"lambda": [], "Ry_N": [], "Rz_N": [], "Rx_back_N": [], "u_toe_mm": [], "u_crotch_mm": [], "u_far_mm": []}
    for k, lk in enumerate(sched, start=1):
        try:
            ry, rz = by[(k, "NSYMY")]["rows"][0][1], by[(k, "NSYMZ")]["rows"][0][2]
            rb = by[(k, "NBACK")]["rows"][0][1]
            u = {m: float(np.linalg.norm(by[(k, m)]["rows"][0][1:4])) for m in ("NTOE", "NCROTCH", "NFAR")}
        except KeyError:
            break
        h["lambda"].append(lk)
        h["Ry_N"].append(float(ry))
        h["Rz_N"].append(float(rz))
        h["Rx_back_N"].append(float(rb))
        h["u_toe_mm"].append(u["NTOE"])
        h["u_crotch_mm"].append(u["NCROTCH"])
        h["u_far_mm"].append(u["NFAR"])
    text = Path(sta).read_text(encoding="latin-1") if Path(sta).exists() else ""
    lc = last_converged(sta) if text else None
    collapse = None
    completed = len(h["lambda"]) == len(sched)
    if lc and not completed:
        s, tau = lc
        prev = sched[s - 2] if s >= 2 else 0.0
        collapse = prev + tau * (sched[s - 1] - prev)
    return h | {"collapse_load_factor": collapse, "completed_all_steps": completed,
                "stopped_below_min_increment": "smaller than" in text}


def plateau_ratio(lam: list, u: list, n_end: int = 2) -> float:
    """Tangent slope d lambda / d u over the last n_end increments, over the first increment's (elastic) slope: near
    0 when the structure has collapsed (the curve has flattened), near 1 while it is still elastic."""
    lam, u = np.asarray(lam, float), np.asarray(u, float)
    if len(lam) < n_end + 2:
        return float("nan")
    k0 = lam[0] / max(u[0], 1e-30)
    k1 = (lam[-1] - lam[-1 - n_end]) / max(u[-1] - u[-1 - n_end], 1e-30)
    return float(k1 / k0)

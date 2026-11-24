"""Study 6, FSI2 mesh level c: read the dense writes before the crash (cases/turek_hron_fsi2_mesh_c_diag.toml) and
tell the two mechanisms apart by the case header's criteria, decided before the run:
  (1) mesh motion: the peak-Courant cell's volume falls towards zero, or its non-orthogonality rises past about 80 deg,
      over the last steps, while the flow round it is ordinary until then;
  (2) solver: the cells there keep their shape while the velocity grows step to step.

usage: .venv/Scripts/python.exe scripts/fsi_crash_diagnosis.py RUN_DIR [OUT.json]
Reads RUN_DIR/points/p00_baseline/solver/fluid/{constant/polyMesh, <t>/pointDisplacement, <t>/U, <t>/phi} (OpenFOAM
ascii), rebuilds the mesh at each time (base points + pointDisplacement), and reports per time: the smallest cell
volume relative to its own base volume, the largest face non-orthogonality, the largest cell Courant number
(0.5 dt sum |phi_f| / V, the absolute flux) and where it sits, and the same measures for that cell's history.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np

NUM = r"[-+0-9.eE]+"


def _body(path: Path) -> str:
    t = path.read_text(encoding="utf-8", errors="replace")
    return t[t.index("}", t.index("FoamFile")) + 1:]


def read_list(path: Path, key: str | None = None):
    """The first top-level list in an OpenFOAM ascii file (or after `key`): scalars, vectors or face label lists."""
    t = _body(path)
    if key is not None:
        k = t.index(key)
        t = t[k:]
        if "uniform" in t[:t.index(";")] and "nonuniform" not in t[:t.index(";")]:
            return None
    m = re.search(r"(\d+)\s*\(", t)
    n, s = int(m.group(1)), m.end()
    if t[s:s + 200].lstrip().startswith("("):                   # vectors or face lists: "(x y z)" / "4(a b c d)"
        items = re.findall(r"(\d*)\(([^()]*)\)", t[s:])[:n]
        if items and items[0][0]:                               # face lists
            return [list(map(int, v.split())) for _, v in items]
        return np.array([[float(x) for x in v.split()] for _, v in items])
    vals = re.findall(NUM, t[s:t.index(")", s)])
    return np.array([float(v) for v in vals[:n]])


def geometry(points, faces, owner, neighbour, n_cells):
    """Face centres and area vectors, cell volumes and centres (pyramid decomposition about a face-centre estimate)."""
    fc = np.array([points[f].mean(axis=0) for f in faces])
    Sf = np.zeros_like(fc)
    for i, f in enumerate(faces):
        p = points[f]
        for k in range(len(f)):
            Sf[i] += 0.5 * np.cross(p[k] - fc[i], p[(k + 1) % len(f)] - fc[i])
    est = np.zeros((n_cells, 3))
    cnt = np.zeros(n_cells)
    for arr, sign in ((owner, 1), (neighbour, 1)):
        np.add.at(est, arr, fc[: len(arr)])
        np.add.at(cnt, arr, 1)
    est /= cnt[:, None]
    V = np.zeros(n_cells)
    C = np.zeros((n_cells, 3))
    nint = len(neighbour)
    for i in range(len(faces)):
        for c, s in ((owner[i], 1.0), (neighbour[i], -1.0)) if i < nint else ((owner[i], 1.0),):
            pv = s * np.dot(Sf[i], fc[i] - est[c]) / 3.0
            V[c] += pv
            C[c] += pv * (0.75 * fc[i] + 0.25 * est[c])
    C /= V[:, None]
    d = C[neighbour] - C[owner[:nint]]
    cosang = np.einsum("ij,ij->i", d, Sf[:nint]) / (np.linalg.norm(d, axis=1) * np.linalg.norm(Sf[:nint], axis=1))
    nonorth = np.degrees(np.arccos(np.clip(cosang, -1, 1)))
    return V, C, nonorth


def cell_max_nonorth(nonorth, owner, neighbour, n_cells):
    out = np.zeros(n_cells)
    nint = len(neighbour)
    np.maximum.at(out, owner[:nint], nonorth)
    np.maximum.at(out, neighbour, nonorth)
    return out


def main():
    run = Path(sys.argv[1])
    fl = run / "points" / "p00_baseline" / "solver" / "fluid"
    pm = fl / "constant" / "polyMesh"
    p0 = read_list(pm / "points")
    faces = read_list(pm / "faces")
    owner = read_list(pm / "owner").astype(int)
    neighbour = read_list(pm / "neighbour").astype(int)
    n_cells = int(max(owner.max(), neighbour.max()) + 1)
    dt = 0.001
    V0, C0, no0 = geometry(p0, faces, owner, neighbour, n_cells)
    times = sorted((float(d.name), d) for d in fl.iterdir() if d.is_dir() and re.fullmatch(NUM, d.name)
                   and float(d.name) > 0 and (d / "pointDisplacement").exists())
    rows, hist = [], {}
    for t, d in times:
        pd = read_list(d / "pointDisplacement", "internalField")
        V, C, no = geometry(p0 + pd, faces, owner, neighbour, n_cells)
        phi = read_list(d / "phi", "internalField")
        U = read_list(d / "U", "internalField")
        flux = np.zeros(n_cells)
        nint = len(neighbour)
        np.add.at(flux, owner[: len(phi)], np.abs(phi))
        np.add.at(flux, neighbour, np.abs(phi[:nint]))
        Co = 0.5 * dt * flux / V
        cno = cell_max_nonorth(no, owner, neighbour, n_cells)
        k = int(np.argmax(Co))
        hist[t] = {"V": V, "Co": Co, "no": cno, "U": U}
        rows.append({"t": t, "max_Co": float(Co[k]), "max_Co_cell": k, "max_Co_xy_m": C[k, :2].tolist(),
                     "min_rel_volume": float(np.min(V / V0)), "min_rel_volume_cell": int(np.argmin(V / V0)),
                     "max_nonorth_deg": float(no.max()), "negative_volumes": int(np.sum(V <= 0))})
    last = rows[-1]["max_Co_cell"]
    track = [{"t": t, "rel_volume": float(h["V"][last] / V0[last]), "nonorth_deg": float(h["no"][last]),
              "Co": float(h["Co"][last]), "speed_m_s": float(np.linalg.norm(h["U"][last]))} for t, h in hist.items()]
    out = {"run": run.name, "cells": n_cells, "base_max_nonorth_deg": float(no0.max()), "per_time": rows,
           "last_peak_cell": last, "last_peak_cell_history": track}
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"{n_cells} cells; base mesh max non-orthogonality {no0.max():.1f} deg")
    print("t        max Co  at (x, y) mm        min V/V0  max nonorth  V<=0")
    for r in rows:
        x, y = (1e3 * v for v in r["max_Co_xy_m"])
        print(f"{r['t']:.3f}  {r['max_Co']:6.2f}  ({x:6.1f}, {y:6.1f})  {r['min_rel_volume']:8.4f}  "
              f"{r['max_nonorth_deg']:8.1f}  {r['negative_volumes']:4d}")
    print(f"history of the last peak cell {last}:")
    for h in track:
        print(f"  {h['t']:.3f}  V/V0 {h['rel_volume']:.4f}  nonorth {h['nonorth_deg']:.1f}  Co {h['Co']:.2f}  "
              f"|U| {h['speed_m_s']:.3f}")


if __name__ == "__main__":
    main()

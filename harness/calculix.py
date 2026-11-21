"""Readers for CalculiX result files (.frd nodal results, .dat printed totals).

Written against CalculiX 2.22 ASCII output. Parsed directly so results do not
depend on FreeCAD's result-import code.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np


def read_frd(path: str | Path) -> dict:
    """Return {"nodes": ids, "coords": (n,3), "<BLOCK>": {"ids":..., "<COMP>": array},
    "blocks": [(name, block), ...]}.

    "<BLOCK>" holds the last block of that name; "blocks" keeps every block in
    file order (one DISP block per mode in a frequency analysis).

    Fixed-width records: ' -1' + node id (10 chars) + values (12 chars each).
    """
    lines = Path(path).read_text(encoding="latin-1").splitlines()
    out: dict = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("    2C"):
            ids, xyz = [], []
            i += 1
            while not lines[i].startswith(" -3"):
                rec = lines[i]
                ids.append(int(rec[3:13]))
                xyz.append([float(rec[13 + 12 * k: 25 + 12 * k]) for k in range(3)])
                i += 1
            out["nodes"] = np.array(ids)
            out["coords"] = np.array(xyz)
        elif line.startswith(" -4"):
            name = line[5:13].strip()
            n_comp = int(line[13:18])
            comps = []
            i += 1
            while lines[i].startswith(" -5"):
                comps.append(lines[i][5:13].strip())
                i += 1
            comps = [c for c in comps if c != "ALL"][:n_comp]
            ids, vals = [], []
            while not lines[i].startswith(" -3"):
                rec = lines[i]
                if rec.startswith(" -1"):
                    ids.append(int(rec[3:13]))
                    vals.append([float(rec[13 + 12 * k: 25 + 12 * k]) for k in range(len(comps))])
                i += 1
            arr = np.array(vals)
            block = {"ids": np.array(ids), **{c: arr[:, k] for k, c in enumerate(comps)}}
            out[name] = block                                   # last block of this name
            out.setdefault("blocks", []).append((name, block))  # every block, in file order
        i += 1
    return out


_TOTAL = re.compile(r"total force \(fx,fy,fz\) for set (\S+)")


def read_dat_total_forces(path: str | Path) -> dict:
    """{set_name: (fx, fy, fz)} from '*NODE PRINT ... TOTALS=ONLY' output (last step)."""
    lines = Path(path).read_text(encoding="latin-1").splitlines()
    out = {}
    for k, line in enumerate(lines):
        m = _TOTAL.search(line)
        if m:
            for nxt in lines[k + 1:k + 4]:
                parts = nxt.split()
                if len(parts) == 3:
                    out[m.group(1)] = tuple(float(v) for v in parts)
                    break
    return out


def read_dat_element_stresses(path: str | Path) -> dict:
    """{element id: (n_ip, 6) array [sxx, syy, szz, sxy, sxz, syz]} from '*EL PRINT ... S'
    (last block in the file, integration points in CalculiX order)."""
    lines = Path(path).read_text(encoding="latin-1").splitlines()
    start = max((k for k, ln in enumerate(lines) if "stresses (elem, integ.pnt." in ln), default=None)
    if start is None:
        return {}
    out: dict = {}
    for ln in lines[start + 1:]:
        parts = ln.split()
        if not parts:
            if out:
                break
            continue
        if len(parts) != 8 or not parts[0].isdigit():
            break
        out.setdefault(int(parts[0]), []).append([float(v) for v in parts[2:]])
    return {e: np.array(v) for e, v in out.items()}


# C3D8 / C3D8I: 2x2x2 Gauss points at +-1/sqrt(3), xi fastest (CalculiX gauss3d2);
# corner nodes in CalculiX order. Trilinear extrapolation from the Gauss-point cube.
_HEX8_GP = np.array([(sx, sy, sz) for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)], float)
_HEX8_NODES = np.array([(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
                        (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)], float) * np.sqrt(3.0)
HEX8_EXTRAPOLATION = np.prod(1 + _HEX8_NODES[:, None, :] * _HEX8_GP[None, :, :], axis=2) / 8


def hex8_nodal_stress(ip_stress: dict, connectivity: dict) -> dict:
    """Nodal stresses averaged over the elements sharing each node, extrapolated exactly
    from the 8 integration points of C3D8 / C3D8I elements.

    CalculiX's own .frd nodal stresses for these elements are about 4e-5 low even for a
    uniform stress field (uniform thermal expansion, fully restrained: integration points
    exact, .frd 0.99996 of it), so studies that need better than 1e-4 extrapolate here.
    Returns {node id: (6,) [sxx, syy, szz, sxy, sxz, syz]}."""
    acc: dict = {}
    cnt: dict = {}
    for e, s in ip_stress.items():
        if s.shape[0] != 8:
            raise ValueError(f"element {e}: {s.shape[0]} integration points, expected 8")
        vals = HEX8_EXTRAPOLATION @ s
        for n, v in zip(connectivity[e], vals):
            acc[n] = acc.get(n, 0.0) + v
            cnt[n] = cnt.get(n, 0) + 1
    return {n: acc[n] / cnt[n] for n in acc}


def _table_after(lines, title, n_cols):
    """Numeric rows (first column an integer mode number) after a .dat table title."""
    for k, line in enumerate(lines):
        if title in line:
            rows = []
            for nxt in lines[k + 1:]:
                parts = nxt.split()
                if not parts:
                    if rows:
                        break
                    continue
                if parts[0].isdigit() and len(parts) == n_cols + 1:
                    rows.append([float(v) for v in parts[1:]])
                elif rows:
                    break
            return np.array(rows)
    return np.zeros((0, n_cols))


def read_dat_frequency(path: str | Path) -> dict:
    """Frequency-step output of a .dat file.

    Returns {"frequency_Hz": (n,), "effective_mass": (n, 6) [x, y, z, rx, ry, rz],
    "total_effective_mass": (6,)}. Effective masses are in the model's mass
    unit; CalculiX leaves the mass of constrained nodes out of the totals.
    """
    lines = Path(path).read_text(encoding="latin-1").splitlines()
    eig = _table_after(lines, "E I G E N V A L U E   O U T P U T", 4)
    eff = _table_after(lines, "E F F E C T I V E   M O D A L   M A S S", 6)
    total = np.zeros(6)
    for k, line in enumerate(lines):
        if "T O T A L   E F F E C T I V E   M A S S" in line:
            for nxt in lines[k + 1:k + 8]:
                parts = nxt.split()
                if len(parts) == 6:
                    try:
                        total = np.array([float(v) for v in parts])
                        break
                    except ValueError:
                        continue
    return {"frequency_Hz": eig[:, 2] if len(eig) else np.zeros(0),
            "effective_mass": eff, "total_effective_mass": total}

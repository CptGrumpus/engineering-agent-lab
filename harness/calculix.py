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

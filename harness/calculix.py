"""Readers for CalculiX result files (.frd nodal results, .dat printed totals).

Written against CalculiX 2.22 ASCII output. Parsed directly so results do not
depend on FreeCAD's result-import code.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np


def read_frd(path: str | Path) -> dict:
    """Return {"nodes": ids, "coords": (n,3), "<BLOCK>": {"ids":..., "<COMP>": array}}.

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
            out[name] = {"ids": np.array(ids), **{c: arr[:, k] for k, c in enumerate(comps)}}
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

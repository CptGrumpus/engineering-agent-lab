"""Frozen mesh-motion diffusivity for the Turek-Hron FSI cases (study 6): gamma = 1 / d^p on every face of the BASE
mesh, d the exact distance to the cylinder and the flag as drawn (not OpenFOAM's meshWave estimate on the moved mesh),
written once as constant/motionDiffusivity for `diffusivity file motionDiffusivity;`. Runs inside WSL (python3, numpy)
from the runner, in the fluid case directory, after gmshToFoam:  python3 frozen_motion_diffusivity.py <fluid dir>

Why (FSI2 mesh level c, 2026-11-24, cases/turek_hron_fsi2_mesh_c_diag.toml): with `quadratic inverseDistance` the
distance is recomputed on the moved mesh every step and the coefficients span 1/y^2 down to the walls; the one-shot
answer depended on the linear solver (PCG: 572 inverted cells, GAMG: none, both "converged" in one iteration), and the
run's cell below the flag tip collapsed through a growing period-2 oscillation. Frozen and exact, the problem is
linear in the boundary displacement and well posed (PCG and GAMG agree; 1/d kept every cell above 0.46 of its base
volume at 1.2 x the crash step's displacement).

Reads fluid/frozen_diffusivity.json: {"xc", "yc", "r", "flag_x0", "flag_x1", "flag_y0", "flag_y1", "exponent"} (m).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np


def _body(path: Path) -> str:
    t = path.read_text(encoding="utf-8", errors="replace")
    return t[t.index("}", t.index("FoamFile")) + 1:]


def read_list(path: Path):
    t = _body(path)
    m = re.search(r"(\d+)\s*\(", t)
    n, s = int(m.group(1)), m.end()
    head = t[s:s + 200].lstrip()
    if re.match(r"\d+\(", head):
        return [list(map(int, v.split())) for v in re.findall(r"\d+\(([^()]*)\)", t[s:])[:n]]
    if head.startswith("("):
        return np.array([[float(x) for x in v.split()] for v in re.findall(r"\(([^()]*)\)", t[s:])[:n]])
    return np.array([float(v) for v in re.findall(r"[-+0-9.eE]+", t[s:t.index(")", s)])[:n]])


def body_distance(P: np.ndarray, g: dict) -> np.ndarray:
    """Exact distance from points (x, y) to the union of the cylinder and the flag rectangle (0 inside either)."""
    dc = np.hypot(P[:, 0] - g["xc"], P[:, 1] - g["yc"]) - g["r"]
    zero = np.zeros(len(P))
    dx = np.maximum.reduce([g["flag_x0"] - P[:, 0], zero, P[:, 0] - g["flag_x1"]])
    dy = np.maximum.reduce([g["flag_y0"] - P[:, 1], zero, P[:, 1] - g["flag_y1"]])
    return np.minimum(np.maximum(dc, 0.0), np.hypot(dx, dy))


def diffusivity(points, faces, owner, g: dict) -> np.ndarray:
    """1 / d^p per face; a face on the body (d = 0) takes half its owner cell's distance (the cell centre estimated
    as the mean of its face centres), so the coefficients stay finite."""
    fc = np.array([points[f].mean(axis=0) for f in faces])
    n_cells = int(owner.max()) + 1
    cc = np.zeros((n_cells, 3))
    cnt = np.zeros(n_cells)
    np.add.at(cc, owner, fc[: len(owner)])
    np.add.at(cnt, owner, 1)
    cc /= np.maximum(cnt, 1)[:, None]
    d = body_distance(fc, g)
    d = np.maximum(d, 0.5 * body_distance(cc, g)[owner])
    return 1.0 / d ** float(g["exponent"])


def write(fluid: Path) -> dict:
    g = json.loads((fluid / "frozen_diffusivity.json").read_text())
    pm = fluid / "constant" / "polyMesh"
    points, faces = read_list(pm / "points"), read_list(pm / "faces")
    owner, neighbour = read_list(pm / "owner").astype(int), read_list(pm / "neighbour").astype(int)
    gam = diffusivity(points, faces, owner, g)
    bnd = _body(pm / "boundary")
    patches = [(m.group(1), m.group(2), int(m.group(3)), int(m.group(4))) for m in re.finditer(
        r"(\w+)\s*\{\s*type\s+(\w+);[^}]*?nFaces\s+(\d+);\s*startFace\s+(\d+);", bnd)]
    if not patches or sum(n for _, _, n, _ in patches) + len(neighbour) != len(faces):
        raise SystemExit("could not read the boundary patches")

    def lst(v):
        return f"nonuniform List<scalar> {len(v)}\n(\n" + "\n".join(f"{x:.10g}" for x in v) + "\n)"
    bf = [f"    {nm} {{ type empty; }}" if typ == "empty" else
          f"    {nm}\n    {{\n        type calculated;\n        value {lst(gam[s:s + n])};\n    }}"
          for nm, typ, n, s in patches]
    (fluid / "constant" / "motionDiffusivity").write_text(
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n    class surfaceScalarField;\n"
        "    object motionDiffusivity;\n}\ndimensions [0 0 0 0 0 0 0];\n"
        f"internalField {lst(gam[:len(neighbour)])};\nboundaryField\n{{\n" + "\n".join(bf) + "\n}\n")
    return {"faces": len(faces), "min": float(gam.min()), "max": float(gam.max())}


if __name__ == "__main__":
    print(write(Path(sys.argv[1])))

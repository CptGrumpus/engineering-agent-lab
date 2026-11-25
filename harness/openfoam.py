"""OpenFOAM helpers: locate an install inside WSL and read ASCII field files.

OpenFOAM runs in WSL (Linux); the harness runs on Windows and drives it with
`wsl.exe`. Fields are written in ASCII and parsed here with numpy, so results
are read straight from OpenFOAM's own files, not through a post-processor.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path, PureWindowsPath

import numpy as np


def wsl_command(*args: str) -> list[str]:
    distro = os.environ.get("OPENFOAM_WSL_DISTRO")
    return ["wsl", *(["-d", distro] if distro else []), "--", *args]


def to_wsl_path(path: Path) -> str:
    """C:\\a\\b -> /mnt/c/a/b (WSL's default automount)."""
    p = PureWindowsPath(Path(path).resolve())
    if not p.drive or not p.drive.endswith(":"):
        raise ValueError(f"cannot map {path} into WSL")
    return "/mnt/" + p.drive[0].lower() + "/" + "/".join(p.parts[1:])


def find_openfoam_bashrc() -> str:
    """Newest /opt/openfoam*/etc/bashrc in WSL, or $OPENFOAM_BASHRC."""
    if os.environ.get("OPENFOAM_BASHRC"):
        return os.environ["OPENFOAM_BASHRC"]
    try:
        r = subprocess.run(wsl_command("bash", "-c", "ls -d /opt/openfoam*/etc/bashrc"),
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        raise RuntimeError(f"WSL not available: {e}") from e
    found = [ln.strip() for ln in r.stdout.splitlines() if ln.strip().endswith("bashrc")]
    if not found:
        raise RuntimeError("OpenFOAM not found in WSL (/opt/openfoam*): install it or set "
                           "OPENFOAM_BASHRC")

    def version(s):
        m = re.search(r"openfoam(\d+)", s)
        return int(m.group(1)) if m else -1

    return max(found, key=version)


# --------------------------------------------------------------------------- field files

_NONUNIFORM = re.compile(r"nonuniform\s+List<(scalar|vector)>\s*(\d+)\s*\(")
_UNIFORM = re.compile(r"uniform\s+(\([^()]*\)|[-+0-9.eE]+)")


def _parse_value(text: str, pos: int, n_default: int | None = None) -> np.ndarray:
    """Parse 'uniform X' or 'nonuniform List<T> N (...)' starting near pos."""
    m = _NONUNIFORM.match(text, pos)
    if m:
        kind, n, start = m.group(1), int(m.group(2)), m.end()
        if kind == "scalar":
            end = text.index(")", start)
            vals = np.array(text[start:end].split(), dtype=float)
        else:
            items = re.finditer(r"\(([^()]*)\)", text[start:])
            rows = []
            for _, it in zip(range(n), items):
                rows.append(it.group(1).split())
            vals = np.array(rows, dtype=float)
        if len(vals) != n:
            raise ValueError(f"expected {n} values, parsed {len(vals)}")
        return vals
    m = _UNIFORM.match(text, pos)
    if m:
        tok = m.group(1)
        v = np.array(tok.strip("()").split(), dtype=float)
        v = v if tok.startswith("(") else v[0]
        if n_default is None:
            return np.atleast_1d(v)
        return np.tile(v, (n_default, 1)) if np.ndim(v) else np.full(n_default, v)
    raise ValueError(f"cannot parse field value at: {text[pos:pos + 60]!r}")


def read_internal_field(path: Path, n_cells: int | None = None) -> np.ndarray:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    m = re.search(r"\binternalField\s+", text)
    if not m:
        raise ValueError(f"{path}: no internalField")
    return _parse_value(text, m.end(), n_cells)


def read_patch_value(path: Path, patch: str, n_faces: int | None = None) -> np.ndarray | None:
    """The 'value' entry of a boundary patch, or None if the patch writes no value."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    b = text.find("boundaryField")
    m = re.compile(rf"\n\s*{re.escape(patch)}\s*\n\s*\{{").search(text, b)
    if b < 0 or not m:
        raise ValueError(f"{path}: patch {patch!r} not found")
    # scan the patch block; only a 'value' at the block's top level counts (entries
    # such as volumetricFlowRate may be sub-dictionaries with their own 'value')
    depth, i = 1, m.end()
    key = re.compile(r"\bvalue\s+")
    while depth:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif depth == 1 and c == "v" and key.match(text, i) and not text[i - 1].isalnum():
            return _parse_value(text, key.match(text, i).end(), n_faces)
        i += 1
    return None


def _foam_list_body(text: str) -> str:
    """The body of the top-level list in an ascii polyMesh file (after the FoamFile header and the count)."""
    h = text.find("FoamFile")
    if h >= 0:
        text = text[text.index("}", h) + 1:]
    m = re.search(r"\n\s*(\d+)\s*\n\s*\(", text)
    if not m:
        raise ValueError("no top-level list")
    return text[m.end():]


def patch_face_areas(mesh_dir: Path, patch: str) -> np.ndarray:
    """Exact areas (m2) of a patch's faces, in the order of the patch's field values, from an ascii polyMesh
    (mesh_dir = constant/polyMesh, or constant/<region>/polyMesh after splitMeshRegions). A face's area is the
    magnitude of its vector area 1/2 sum(p_k x p_k+1), exact for planar polygons.

    Why: summing a patch's flux as `flux.sum() * one face area` assumes equal faces; blockMesh rounds a block's cell
    count, so blocks whose length is not a whole number of cells get slightly larger cells (enclosure redesign,
    2026-11-24: 25 and 29 mm blocks at 2 mm cells, faces 2.083 and 2.071 mm; the total came out 1.9 % low)."""
    mesh_dir = Path(mesh_dir)
    btxt = (mesh_dir / "boundary").read_text(encoding="utf-8", errors="replace")
    m = re.compile(rf"\n\s*{re.escape(patch)}\s*\n\s*\{{([^}}]*)\}}").search(btxt)
    if not m:
        raise ValueError(f"{mesh_dir}: patch {patch!r} not found in boundary")
    n = int(re.search(r"\bnFaces\s+(\d+)", m.group(1)).group(1))
    start = int(re.search(r"\bstartFace\s+(\d+)", m.group(1)).group(1))
    pts = np.array(re.findall(r"\(\s*([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\)",
                              _foam_list_body((mesh_dir / "points").read_text(encoding="utf-8", errors="replace"))),
                   dtype=float)
    faces = re.findall(r"\d+\s*\(([\d\s]+)\)",
                       _foam_list_body((mesh_dir / "faces").read_text(encoding="utf-8", errors="replace")))
    out = np.empty(n)
    for k in range(n):
        p = pts[np.array(faces[start + k].split(), dtype=int)]
        out[k] = 0.5 * np.linalg.norm(np.cross(p, np.roll(p, -1, axis=0)).sum(axis=0))
    return out


def latest_time_dir(case: Path) -> Path:
    times = []
    for d in Path(case).iterdir():
        try:
            times.append((float(d.name), d))
        except ValueError:
            continue
    times = [t for t in times if t[0] > 0]
    if not times:
        raise ValueError(f"{case}: no result time directories")
    return max(times)[1]


_RESID = re.compile(r"Solving for (\w+), Initial residual = ([-+0-9.eE]+)")


def read_solver_log(path: Path) -> dict:
    """Iteration count, convergence flag, and last initial residual per field."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    last = {}
    for name, val in _RESID.findall(text):
        last[name] = float(val)
    m = re.search(r"SIMPLE solution converged in (\d+) iterations", text)
    times = re.findall(r"^Time = ([-+0-9.eE]+)", text, re.M)
    return {"converged": bool(m),
            "iterations": int(m.group(1)) if m else (int(float(times[-1])) if times else 0),
            "final_initial_residuals": last,
            "ended": "\nEnd" in text}

"""Solid-mesh surface extraction for result rendering.

Reads nodes and solid elements from an Abaqus/CalculiX deck, extracts the outer
surface as outward-oriented triangles, and writes render scenes: a surface mesh
with one scalar per vertex plus the metadata a renderer needs (field name,
units, range, view). Used by the matplotlib figures and the Blender renders, so
both draw exactly the same surface and the same numbers.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

# corner-node faces of each element type, as index tuples into the element's node list
FACES = {
    "C3D10": [(0, 1, 2), (0, 1, 3), (1, 2, 3), (0, 2, 3)],
    "C3D4": [(0, 1, 2), (0, 1, 3), (1, 2, 3), (0, 2, 3)],
    "C3D8": [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)],
}
NODES_PER = {"C3D10": 10, "C3D4": 4, "C3D8": 8}


def read_inp(path: Path) -> tuple[dict, list[tuple[str, list[int]]]]:
    """Nodes {id: (x, y, z)} and solid elements [(type, node ids)] from an Abaqus/CalculiX deck,
    following *INCLUDE files."""
    nodes, elems = {}, []
    mode, etype, buf = None, None, []
    for raw in Path(path).read_text(encoding="latin-1").splitlines():
        line = raw.strip()
        if not line or line.startswith("**"):
            continue
        if line.startswith("*"):
            key = line.upper()
            if key.startswith("*INCLUDE"):
                inc = re.search(r"INPUT\s*=\s*(\S+)", line, re.I).group(1)
                n2, e2 = read_inp(Path(path).parent / inc)
                nodes.update(n2)
                elems += e2
                mode = None
            elif key.startswith("*NODE") and not any(w in key for w in ("PRINT", "FILE", "OUTPUT")):
                mode = "node"
            elif key.startswith("*ELEMENT") and "OUTPUT" not in key:
                t = re.search(r"TYPE\s*=\s*(\w+)", line, re.I).group(1).upper()
                mode, etype, buf = ("elem", t, []) if t in NODES_PER else (None, None, [])
            else:
                mode = None
            continue
        if mode == "node":
            v = line.split(",")
            nodes[int(v[0])] = tuple(float(c) for c in v[1:4])
        elif mode == "elem":
            buf += [int(c) for c in line.rstrip(",").split(",") if c.strip()]
            if len(buf) >= NODES_PER[etype] + 1:
                elems.append((etype, buf[1:NODES_PER[etype] + 1]))
                buf = []
    return nodes, elems


def boundary_triangles(nodes: dict, elems) -> np.ndarray:
    """Outward-oriented boundary triangles (node-id triples) of a solid mesh.

    A face is on the boundary when exactly one element owns it. Each face is
    oriented so its normal points away from its element's centroid; quads are
    split into two triangles."""
    seen: dict = {}
    for etype, conn in elems:
        corners = conn[:4] if etype in ("C3D10", "C3D4") else conn
        for f in FACES[etype]:
            ids = tuple(corners[i] for i in f)
            seen.setdefault(tuple(sorted(ids)), []).append((ids, corners))
    tris = []
    for owners in seen.values():
        if len(owners) != 1:
            continue
        ids, corners = owners[0]
        P = np.array([nodes[i] for i in ids])
        n = np.cross(P[1] - P[0], P[2] - P[0])
        centroid = np.mean([nodes[i] for i in corners], axis=0)
        if np.dot(n, P[0] - centroid) < 0:
            ids = ids[::-1]
        if len(ids) == 3:
            tris.append(ids)
        else:
            tris += [(ids[0], ids[1], ids[2]), (ids[0], ids[2], ids[3])]
    return np.array(tris, dtype=np.int64)


def enclosed_volume(xyz: np.ndarray, tris: np.ndarray) -> float:
    """Volume enclosed by a closed triangle surface (divergence theorem). Positive when the
    triangles face outwards, so it doubles as an orientation and closure check."""
    T = xyz[tris]
    return float(np.einsum("ij,ij->i", T[:, 0], np.cross(T[:, 1], T[:, 2])).sum() / 6.0)


def von_mises(s) -> np.ndarray:
    return np.sqrt(0.5 * ((s["sxx_MPa"] - s["syy_MPa"]) ** 2 + (s["syy_MPa"] - s["szz_MPa"]) ** 2
                          + (s["szz_MPa"] - s["sxx_MPa"]) ** 2)
                   + 3 * (s["sxy_MPa"] ** 2 + s["syz_MPa"] ** 2 + s["szx_MPa"] ** 2))


def compact(xyz: np.ndarray, tris: np.ndarray, *fields: np.ndarray):
    """Drop vertices no triangle uses (interior and mid-side nodes) and renumber."""
    used = np.unique(tris)
    remap = np.full(len(xyz), -1, dtype=np.int64)
    remap[used] = np.arange(len(used))
    return (xyz[used], remap[tris], *[None if f is None else np.asarray(f)[used] for f in fields])


def extrude_planar(xy: np.ndarray, tris: np.ndarray, value: np.ndarray, thickness: float):
    """Turn a planar triangulated field into a closed slab of the given thickness: top and
    bottom faces carry the field, and the side walls are built from the boundary edges."""
    n = len(xy)
    top = np.column_stack([xy, np.full(n, thickness / 2)])
    bot = np.column_stack([xy, np.full(n, -thickness / 2)])
    xyz = np.vstack([top, bot])
    t = np.asarray(tris, dtype=np.int64)
    # make the top triangles counter-clockwise seen from +z
    a = xy[t[:, 1]] - xy[t[:, 0]]
    b = xy[t[:, 2]] - xy[t[:, 0]]
    flip = (a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]) < 0
    t[flip] = t[flip][:, ::-1]
    faces = [t, t[:, ::-1] + n]
    edges = np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]])
    key = np.sort(edges, axis=1)
    _, inv, counts = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    bnd = edges[counts[inv.ravel()] == 1]       # directed with the CCW top face, so walls face out
    i, j = bnd[:, 0], bnd[:, 1]
    faces.append(np.column_stack([j, i, i + n]))
    faces.append(np.column_stack([j, i + n, j + n]))
    return xyz, np.vstack(faces), np.concatenate([value, value])


def write_scene(path: Path, xyz: np.ndarray, tris: np.ndarray, value: np.ndarray | None = None,
                ghost_xyz: np.ndarray | None = None, **meta) -> Path:
    """Write a render scene: <path>.npz (geometry, field) and <path>.json (metadata).

    `value` is the scalar per vertex in physical units; meta carries at least
    `field`, `units`, `vmin`, `vmax` for a contour scene, plus the view
    (`elev`, `azim`) and the caption text. Without `value` the part renders as
    plain material (a CAD hero render)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    arrays = {"xyz": np.asarray(xyz, dtype=np.float64), "tris": np.asarray(tris, dtype=np.int32)}
    if value is not None:
        arrays["value"] = np.asarray(value, dtype=np.float64)
        meta.setdefault("vmin", float(np.min(value)))
        meta.setdefault("vmax", float(np.max(value)))
        meta["data_min"], meta["data_max"] = float(np.min(value)), float(np.max(value))
    if ghost_xyz is not None:
        arrays["ghost_xyz"] = np.asarray(ghost_xyz, dtype=np.float64)
    np.savez_compressed(path.with_suffix(".npz"), **arrays)
    meta["n_vertices"], meta["n_triangles"] = int(len(xyz)), int(len(tris))
    path.with_suffix(".json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return path.with_suffix(".npz")

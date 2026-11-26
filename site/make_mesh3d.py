"""Meshes for the page's interactive 3D view: site/v2/m3d_<id>.bin, one per viewer tab that has one.

Each file is the same surface and field the Blender render was made from (build/render/<scene>.npz),
so the browser view and the still render show the same thing:

    header   uint32[8]   magic "M3D1", vertices, triangles, outline segments, index bytes (2 or 4), 0, 0, 0
    box      float32[6]  bounding box min xyz, max xyz (mm)
    xyz      uint16[3n]  positions quantised over the box (error under box/65535, ~0.003 mm on 200 mm), padded to 4 bytes
    s        float32[n]  the field as the shader bands it: (v - vmin) / (vmax - vmin), clipped to [0, 1)
    tris     uint16 or uint32 [3t], padded to 4 bytes
    outline  float32[6e] undeformed feature edges (mm), for deformed scenes; empty otherwise

The band of a point is floor(s * bands), as in scripts/blender/render_scene.py. Each file is read back
and compared with its source before it is accepted. Run after scripts/make_renders.py; build_v2.py
calls it.
"""
from __future__ import annotations

import json
import math
import struct
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
BUILD = REPO / "build" / "render"
OUT = HERE / "v2"
INDEX = OUT / "m3d.json"
MAGIC = 0x3144334D                                   # "M3D1" little-endian

# viewer entry -> render scene. The contact close-up stays an image (its 1 mm patch is lost in a
# rotatable whole model) and so does the strap proof test (an unstructured 331 000-vertex mesh). The
# cold plate uses a lighter mesh: every fourth node through the thickness (make_study_renders.py)
SCENES = {"bracket_opt": "opt/bracket_opt_hero", "cantilever": "cantilever", "cantilever_opt": "cantilever_opt", "fatigue": "fatigue",
          "fin": "fin", "mode1": "mode1", "strut": "strut", "bolted_joint": "bolted_joint", "duct": "duct",
          "cold_plate": "cold_plate_3d", "steel_frame": "steel_frame", "fan_rotor": "fan_rotor", "enclosure": "enclosure"}


def feature_edges(pts: np.ndarray, tris: np.ndarray, angle_deg: float) -> np.ndarray:
    """Same rule as the render's undeformed outline (render_scene.feature_edges)."""
    T = pts[tris]
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-30
    e = np.sort(np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]]), axis=1)
    owner = np.tile(np.arange(len(tris)), 3)
    order = np.lexsort((e[:, 1], e[:, 0]))
    e, owner = e[order], owner[order]
    same = np.all(e[1:] == e[:-1], axis=1)
    i = np.nonzero(same)[0]
    cosang = np.einsum("ij,ij->i", n[owner[i]], n[owner[i + 1]])
    return e[i][cosang < math.cos(math.radians(angle_deg))]


# mode shapes that can be animated in the 3D view: the scene's deformed surface minus its undeformed
# ghost is the mode's displacement, and the viewer swings the mesh between ghost + d and ghost - d
ANIMATE = {"mode1"}


def encode(scene: str, animate: bool = False) -> tuple[bytes, dict]:
    d = np.load(BUILD / f"{scene}.npz")
    meta = json.loads((BUILD / f"{scene}.json").read_text(encoding="utf-8"))
    xyz, tris = d["xyz"].astype(np.float64), d["tris"].astype(np.int64)
    s = np.clip((d["value"] - meta["vmin"]) / (meta["vmax"] - meta["vmin"]), 0.0, 1.0 - 1e-6).astype(np.float32)
    outline = np.zeros((0, 6), np.float32)
    if "ghost_xyz" in d:
        g = d["ghost_xyz"].astype(np.float64)
        e = feature_edges(g, tris, meta.get("sharp_angle_deg", 32))
        outline = np.hstack([g[e[:, 0]], g[e[:, 1]]]).astype(np.float32)
    disp = None
    if animate:
        disp = xyz - d["ghost_xyz"].astype(np.float64)
    allp = xyz if not len(outline) else np.vstack([xyz, outline.reshape(-1, 3)])
    if disp is not None:                              # the box must hold the opposite swing too
        allp = np.vstack([allp, xyz - 2 * disp])
    lo, hi = allp.min(axis=0), allp.max(axis=0)
    span = np.where(hi > lo, hi - lo, 1.0)
    q = np.round((xyz - lo) / span * 65535).astype(np.uint16)
    ib = 2 if len(xyz) < 65536 else 4
    qb = q.tobytes()
    qb += b"\0" * (-len(qb) % 4)                      # typed arrays in the browser need 4-byte offsets
    idx = tris.astype(np.uint16 if ib == 2 else np.uint32).tobytes()
    idx += b"\0" * (-len(idx) % 4)
    blob = (struct.pack("<8I", MAGIC, len(xyz), len(tris), len(outline), ib, 1 if disp is not None else 0, 0, 0)
            + np.concatenate([lo, hi]).astype(np.float32).tobytes() + qb + s.tobytes() + idx
            + outline.tobytes())
    out = {"xyz": xyz, "tris": tris, "s": s, "outline": outline, "span": span}
    if disp is not None:            # displacement: one float32 scale, then int16 per component, padded
        scale = float(np.abs(disp).max()) or 1.0
        dq = np.round(disp / scale * 32767).astype(np.int16).tobytes()
        dq += b"\0" * (-len(dq) % 4)
        blob += struct.pack("<f", scale) + dq
        out.update(disp=disp, disp_scale=scale)
    return blob, out


def decode(blob: bytes) -> dict:
    magic, nv, nt, ne, ib, anim = struct.unpack_from("<6I", blob)
    assert magic == MAGIC
    o = 32
    box = np.frombuffer(blob, np.float32, 6, o).astype(np.float64); o += 24
    q = np.frombuffer(blob, np.uint16, 3 * nv, o).reshape(nv, 3); o += 6 * nv
    o += -o % 4
    s = np.frombuffer(blob, np.float32, nv, o); o += 4 * nv
    tris = np.frombuffer(blob, np.uint16 if ib == 2 else np.uint32, 3 * nt, o).reshape(nt, 3); o += ib * 3 * nt
    o += -o % 4
    outline = np.frombuffer(blob, np.float32, 6 * ne, o).reshape(ne, 6); o += 24 * ne
    disp = None
    if anim:
        scale = struct.unpack_from("<f", blob, o)[0]; o += 4
        disp = np.frombuffer(blob, np.int16, 3 * nv, o).reshape(nv, 3).astype(np.float64) / 32767 * scale
        o += 6 * nv; o += -o % 4
    assert o == len(blob), (o, len(blob))
    lo, hi = box[:3], box[3:]
    xyz = lo + q.astype(np.float64) / 65535 * np.where(hi > lo, hi - lo, 1.0)
    return {"xyz": xyz, "tris": tris.astype(np.int64), "s": s, "outline": outline, "disp": disp}


def main() -> dict:
    """Encode every scene whose render data is in build/render; a scene without it keeps its committed
    file and index entry (its source script rebuilds the data: make_renders.py, make_clevis_visuals.py,
    make_study_renders.py)."""
    old = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}
    out = {}
    for vid, scene in SCENES.items():
        if not (BUILD / f"{scene}.npz").exists():
            if vid not in old or not (HERE / old[vid]["file"]).exists():
                raise FileNotFoundError(f"{vid}: no render data in build/render and no committed 3D file")
            out[vid] = old[vid]
            continue
        blob, src = encode(scene, animate=vid in ANIMATE)
        back = decode(blob)
        err = np.abs(back["xyz"] - src["xyz"]).max(axis=0)
        assert np.all(err <= src["span"] / 65535 * 0.51 + 1e-4), (vid, err)     # quantisation only
        assert np.array_equal(back["tris"], src["tris"]) and np.array_equal(back["s"], src["s"])
        assert np.array_equal(back["outline"], src["outline"])
        if "disp" in src:            # quantisation of the displacement only
            assert np.abs(back["disp"] - src["disp"]).max() <= src["disp_scale"] / 32767 * 0.51 + 1e-9, vid
        (OUT / f"m3d_{vid}.bin").write_bytes(blob)
        meta = json.loads((BUILD / f"{scene}.json").read_text(encoding="utf-8"))
        out[vid] = {"file": f"v2/m3d_{vid}.bin", "kb": round(len(blob) / 1024), "vertices": len(src["xyz"]),
                    "elev": meta.get("elev", 24), "azim": meta.get("azim", -55),
                    "max_position_error_mm": round(float(err.max()), 5), "animated": "disp" in src}
    INDEX.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def index() -> dict:
    """The meshes for the page: rebuilt from build/render where the data is there, else the committed files."""
    if any((BUILD / f"{s}.npz").exists() for s in SCENES.values()):
        return main()
    return json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}


if __name__ == "__main__":
    for k, v in main().items():
        print(k, v)
    sys.exit(0)

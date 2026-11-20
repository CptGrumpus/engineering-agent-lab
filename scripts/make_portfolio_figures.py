"""Headline figures for the portfolio case studies (portfolio/img/).

Run from the repository root:  .venv\\Scripts\\python.exe scripts\\make_portfolio_figures.py

- Shaded renders of the actual CadQuery geometry (strap, mounting plate,
  bracket arm), tessellated and drawn with matplotlib (no extra renderer).
- The strap's Gmsh mesh around the hole, from the committed solver files.
- The bracket arm's first four mode shapes, from a local evidence run's
  mode_shapes.csv (result CSVs are not committed; rerun bracket_modal_mesh if
  it is missing).
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from harness.plotting import SERIES_1, SURFACE, TEXT, TEXT_2  # noqa: E402

OUT = REPO / "portfolio" / "img"
LIGHT = np.array([0.35, -0.55, 0.75])
BASE = np.array(matplotlib.colors.to_rgb(SERIES_1))


def _view(elev, azim):
    """Rotation to view coordinates (x right, y up, z towards the viewer)."""
    e, a = np.radians(elev), np.radians(azim)
    d = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])   # towards the viewer
    right = np.cross([0, 0, 1], d); right /= np.linalg.norm(right)
    up = np.cross(d, right)
    return np.vstack([right, up, d])


def render(shape, path: Path, title: str, elev=28, azim=-58, tol=0.05):
    """Shaded render of a CadQuery shape: own projection and back-to-front
    painter ordering, so flat faces have no seams."""
    verts, faces = shape.tessellate(tol, 0.2)
    v = np.array([[p.x, p.y, p.z] for p in verts])
    tris = v[np.array(faces)]
    R = _view(elev, azim)
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    light = R.T @ np.array([-0.4, 0.6, 0.7])
    light /= np.linalg.norm(light)
    k = np.abs(n @ light)
    rgb = np.clip(0.30 + 0.70 * k[:, None] * BASE + 0.18 * k[:, None] ** 6, 0, 1)
    pv = tris @ R.T
    facing = (n @ R[2]) > 1e-9           # back-face culling: the part is a closed solid
    pv, rgb = pv[facing], rgb[facing]
    order = np.argsort(pv[:, :, 2].mean(axis=1))              # far to near
    fig, ax = plt.subplots(figsize=(7.5, 3.6), facecolor=SURFACE)
    from matplotlib.collections import PolyCollection
    ax.add_collection(PolyCollection(pv[order][:, :, :2], facecolors=rgb[order],
                                     edgecolors=rgb[order], linewidths=0.4))
    lo, hi = pv[:, :, :2].reshape(-1, 2).min(axis=0), pv[:, :, :2].reshape(-1, 2).max(axis=0)
    pad = 0.04 * (hi - lo).max()
    ax.set_xlim(lo[0] - pad, hi[0] + pad); ax.set_ylim(lo[1] - pad, hi[1] + pad)
    ax.set_aspect("equal"); ax.set_axis_off()
    ax.set_title(title, color=TEXT, fontsize=11, loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def strap_mesh(mesh_inp: Path, path: Path, r: float):
    text = mesh_inp.read_text(encoding="utf-8")
    nodes = {}
    for ln in text.split("*NODE", 1)[1].split("*", 1)[0].strip().splitlines():
        i, x, y, _ = ln.split(",")
        nodes[int(i)] = (float(x), float(y))
    tris = []
    for ln in text.split("*ELEMENT", 1)[1].split("\n", 1)[1].split("*", 1)[0].strip().splitlines():
        parts = [int(p) for p in ln.split(",")]
        tris.append([nodes[k] for k in parts[1:4]])            # corner nodes of the 6-node triangle
    tris = np.array(tris)
    fig, ax = plt.subplots(figsize=(7.5, 3.9), facecolor=SURFACE)
    for t in tris:
        ax.fill(t[:, 0], t[:, 1], facecolor=SURFACE, edgecolor=SERIES_1, linewidth=0.25)
    ax.set_xlim(0, 30); ax.set_ylim(0, 20); ax.set_aspect("equal")
    ax.set_xlabel("x (mm)", color=TEXT_2); ax.set_ylabel("y (mm)", color=TEXT_2)
    ax.tick_params(colors=TEXT_2, labelsize=8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.set_title(f"Gmsh mesh of the quarter model: {len(tris)} quadratic triangles, "
                 "refined at the hole edge", color=TEXT, fontsize=10, loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def mode_shapes(csv: Path, freqs, types, path: Path, L=150.0, b=25.0, h=7.0):
    """Wireframe mode shapes: the four long edges and cross-sections, deformed."""
    from harness.runio import read_series

    s = read_series(csv)
    x, y, z = s["x_mm"], s["y_mm"], s["z_mm"]
    corners = [(sy, sz) for sy in (-1, 1) for sz in (-1, 1)]
    R = _view(24, -60)
    stations = np.linspace(0, L, 11)
    fig, axes = plt.subplots(1, 4, figsize=(11, 3.0), facecolor=SURFACE)
    for k, ax in enumerate(axes):
        u = np.column_stack([s[f"mode{k + 1}_ux"], s[f"mode{k + 1}_uy"], s[f"mode{k + 1}_uz"]])
        scale = 0.15 * L / np.linalg.norm(u, axis=1).max()
        edges = {}
        for sy, sz in corners:
            m = np.isclose(y, sy * b / 2, atol=1e-6) & np.isclose(z, sz * h / 2, atol=1e-6)
            o = np.argsort(x[m])
            p0 = np.column_stack([x[m][o], y[m][o], z[m][o]])
            edges[(sy, sz)] = (p0, p0 + scale * u[m][o])
        for which, colour, lw in ((0, "#d9dde2", 0.8), (1, SERIES_1, 1.4)):
            for p0, p1 in edges.values():
                q = (p1 if which else p0) @ R.T
                ax.plot(q[:, 0], q[:, 1], color=colour, linewidth=lw)
            for xs in stations:
                ring = []
                for sy, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1)):
                    p0, p1 = edges[(sy, sz)]
                    src = p1 if which else p0
                    ring.append([np.interp(xs, p0[:, 0], src[:, c]) for c in range(3)])
                q = np.array(ring) @ R.T
                ax.plot(q[:, 0], q[:, 1], color=colour, linewidth=lw * 0.6)
        ax.set_aspect("equal"); ax.set_axis_off()
        ax.set_title(f"mode {k + 1}: {freqs[k]:.0f} Hz, {types[k]}", color=TEXT, fontsize=9.5)
    fig.suptitle("Bracket arm mode shapes from CalculiX (clamped at the left; undeformed in grey)",
                 color=TEXT, fontsize=10.5, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def main():
    import cadquery as cq

    from harness.runio import read_json
    from models.cad import mounting_plate

    OUT.mkdir(parents=True, exist_ok=True)
    strap = (cq.Workplane("XY").box(160, 40, 4)
             .cut(cq.Workplane("XY").circle(8).extrude(4, both=True)))
    render(strap.val(), OUT / "strap_render.png", "Strap, 160 x 40 x 4 mm, with a 16 mm cable hole")
    plate_params = read_json(REPO / "runs/20261119-090540_mounting_plate/manifest.json")["points"][2]["parameters"]
    render(mounting_plate.build(plate_params).val(), OUT / "plate_render.png",
           f"Mounting plate generated by CadQuery, {plate_params['hole_diameter_mm']:g} mm holes", elev=35)
    arm = cq.Workplane("XY").box(150, 25, 7, centered=(False, True, True))
    render(arm.val(), OUT / "bracket_render.png", "Bracket arm, 150 x 25 x 7 mm, clamped at the left end")
    mesh = REPO / "runs/20261119-235201_strap_hole_mesh/points/p02_hole_element_size_mm-0.25/solver/mesh.inp"
    strap_mesh(mesh, OUT / "strap_mesh.png", r=5.0)
    run = REPO / "runs/20261120-010318_bracket_modal_mesh"
    pt = read_json(run / "manifest.json")["points"][2]
    csv = run / "points" / pt["label"] / "mode_shapes.csv"
    if csv.exists():
        out = pt["solver_outputs"]
        mode_shapes(csv, out["frequency_Hz"], out["mode_types"], OUT / "bracket_modes.png")
    else:
        print(f"skipped mode shapes: {csv} not found (rerun bracket_modal_mesh)")
    print("figures written to", OUT)


if __name__ == "__main__":
    main()

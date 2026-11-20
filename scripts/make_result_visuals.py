"""Result visuals for the portfolio (portfolio/img/): FE contour renders on the
3D parts, an animated mode-shape GIF, and the workflow diagram.

Run from the repository root:  .venv\\Scripts\\python.exe scripts\\make_result_visuals.py

Uses local evidence runs (result CSVs and full meshes are not committed; rerun
the named case if a file is missing). Rendering is plain matplotlib with an
own projection: boundary faces extracted from the solid mesh (harness.femesh),
oriented outwards, back-face culled, and drawn back to front. The Blender
renders (scripts/make_renders.py) use the same surface extraction.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from harness.femesh import boundary_triangles, read_inp, von_mises  # noqa: E402
from harness.plotting import GRID, SERIES_1, SERIES_2, SURFACE, TEXT, TEXT_2  # noqa: E402

OUT = REPO / "portfolio" / "img"
CMAP = matplotlib.colormaps["turbo"]  # FE-style contour map

# --------------------------------------------------------------------------- rendering

def view_matrix(elev, azim):
    e, a = np.radians(elev), np.radians(azim)
    d = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    right = np.cross([0, 0, 1], d); right /= np.linalg.norm(right)
    return np.vstack([right, np.cross(d, right), d])


def draw_field(ax, xyz, tris_idx, value, R, vmin, vmax, ambient=0.55):
    """Contour-shaded surface: colour by the mean nodal value per triangle, lit softly."""
    T = xyz[tris_idx]
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    facing = (n @ R[2]) > 1e-9
    T, n, val = T[facing], n[facing], value[tris_idx][facing].mean(axis=1)
    light = R.T @ np.array([-0.35, 0.55, 0.75]); light /= np.linalg.norm(light)
    shade = ambient + (1 - ambient) * np.abs(n @ light)
    rgb = CMAP(np.clip((val - vmin) / (vmax - vmin + 1e-30), 0, 1))[:, :3] * shade[:, None]
    P = T @ R.T
    order = np.argsort(P[:, :, 2].mean(axis=1))
    ax.add_collection(PolyCollection(P[order][:, :, :2], facecolors=rgb[order],
                                     edgecolors=rgb[order], linewidths=0.3))
    return P


def frame_axes(ax, pts, pad=0.05):
    xy = np.asarray(pts)[..., :2].reshape(-1, 2)      # projected x, y only
    lo, hi = xy.min(axis=0), xy.max(axis=0)
    p = pad * (hi - lo).max()
    ax.set_xlim(lo[0] - p, hi[0] + p); ax.set_ylim(lo[1] - p, hi[1] + p)
    ax.set_aspect("equal"); ax.set_axis_off()


def colorbar(fig, ax, vmin, vmax, label):
    sm = matplotlib.cm.ScalarMappable(cmap=CMAP, norm=matplotlib.colors.Normalize(vmin, vmax))
    cb = fig.colorbar(sm, ax=ax, fraction=0.035, pad=0.02, panchor=False)
    cb.set_label(label, color=TEXT_2)
    cb.ax.tick_params(colors=TEXT_2, labelsize=8)
    cb.outline.set_edgecolor(GRID)


# --------------------------------------------------------------------------- figures

def cantilever_contour():
    from harness.runio import read_series

    pt = REPO / "runs/20261119-085818_cantilever_tet10/points/p03_mesh_size_mm-1.95312"
    nodes, elems = read_inp(pt / "solver" / "Mesh.inp")
    s = read_series(pt / "nodal_results.csv")
    ids = s["node_id"].astype(int)
    index = {nid: k for k, nid in enumerate(ids)}
    tris = np.vectorize(index.get)(boundary_triangles(nodes, elems))
    xyz = np.column_stack([s["x_mm"], s["y_mm"], s["z_mm"]])
    u = np.column_stack([s["ux_mm"], s["uy_mm"], s["uz_mm"]])
    scale = 25.0
    vm = von_mises(s)
    vmax = 150.0                     # beam-theory root stress; the singular clamp corners exceed it
    R = view_matrix(22, -55)
    fig, ax = plt.subplots(figsize=(9, 3.9), facecolor=SURFACE)
    ghost = xyz[tris] @ R.T
    ax.add_collection(PolyCollection(ghost[:, :, :2], facecolors="none", edgecolors="#e2e5e9",
                                     linewidths=0.15))
    P = draw_field(ax, xyz + scale * u, tris, vm, R, 0.0, vmax)
    frame_axes(ax, np.concatenate([P, ghost]))
    colorbar(fig, ax, 0.0, vmax, "von Mises stress (MPa)")
    fig.suptitle("Cantilever bracket under 1 kN: von Mises stress on the deformed shape "
                 f"(deflection x{scale:g}; undeformed outline grey)", color=TEXT, fontsize=10, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(OUT / "cantilever_stress.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def strap_contour():
    import matplotlib.tri as mtri

    from harness.runio import read_series

    pt = REPO / "runs/20261119-235201_strap_hole_mesh/points/p03_hole_element_size_mm-0.125"
    s = read_series(pt / "nodal_results.csv")
    x, y, sxx = s["x_mm"], s["y_mm"], s["sxx_MPa"]
    # mirror the quarter model into the full plate (symmetry about x = 0 and y = 0)
    X = np.concatenate([x, -x, x, -x]); Y = np.concatenate([y, y, -y, -y]); S = np.tile(sxx, 4)
    keep = np.unique(np.round(np.column_stack([X, Y]), 6), axis=0, return_index=True)[1]
    X, Y, S = X[keep], Y[keep], S[keep]
    tri = mtri.Triangulation(X, Y)
    cx, cy = X[tri.triangles].mean(axis=1), Y[tri.triangles].mean(axis=1)
    tri.set_mask(np.hypot(cx, cy) < 5.0)
    fig, ax = plt.subplots(figsize=(10, 3.4), facecolor=SURFACE)
    levels = np.linspace(0, 105, 22)
    cs = ax.tricontourf(tri, S, levels=levels, cmap=CMAP, extend="both")
    th = np.linspace(0, 2 * np.pi, 200)
    ax.plot(5 * np.cos(th), 5 * np.sin(th), color=TEXT, linewidth=0.8)
    ax.plot([-80, 80, 80, -80, -80], [-20, -20, 20, 20, -20], color=TEXT, linewidth=0.8)
    ax.annotate("", (88, 0), (80, 0), arrowprops=dict(arrowstyle="-|>", color=TEXT_2, lw=1.2))
    ax.annotate("", (-88, 0), (-80, 0), arrowprops=dict(arrowstyle="-|>", color=TEXT_2, lw=1.2))
    ax.text(84, 3, "5 kN", color=TEXT_2, fontsize=8.5, ha="center")
    ax.set_xlim(-92, 92); ax.set_ylim(-23, 23); ax.set_aspect("equal"); ax.set_axis_off()
    cb = fig.colorbar(cs, ax=ax, fraction=0.03, pad=0.01)
    cb.set_label("σxx (MPa)", color=TEXT_2); cb.ax.tick_params(colors=TEXT_2, labelsize=8)
    cb.outline.set_edgecolor(GRID)
    ax.set_title("Strap with a 10 mm hole under 5 kN: axial stress, peak 101.5 MPa at the hole edge "
                 "(quarter model mirrored)", color=TEXT, fontsize=10, loc="left")
    fig.tight_layout()
    fig.savefig(OUT / "strap_stress.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def fin_contour():
    from harness.calculix import read_frd

    sol = REPO / "runs/20261119-221454_fin_mesh/points/p03_element_size_mm-0.25/solver"
    nodes, elems = read_inp(sol / "fin.inp")
    frd = read_frd(sol / "fin.frd")
    blk = frd.get("NDTEMP")
    ids = frd["nodes"]
    index = {int(n): k for k, n in enumerate(ids)}
    T = np.empty(len(ids)); T[[index[int(i)] for i in blk["ids"]]] = blk["T"]
    tris = np.vectorize(index.get)(boundary_triangles(nodes, elems))
    xyz = frd["coords"]
    R = view_matrix(20, -125)
    fig, ax = plt.subplots(figsize=(6.2, 4.8), facecolor=SURFACE)
    ax.set_anchor("C")
    P = draw_field(ax, xyz, tris, T, R, float(T.min()), float(T.max()), ambient=0.75)
    frame_axes(ax, P)
    colorbar(fig, ax, float(T.min()), float(T.max()), "temperature (°C)")
    fig.suptitle(f"Heat-sink fin: temperature from {T.max():.1f} °C at the base to "
                 f"{T.min():.1f} °C at the tip", color=TEXT, fontsize=10, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(OUT / "fin_temperature.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def bracket_modes_gif():
    from matplotlib.animation import FuncAnimation, PillowWriter

    from harness.runio import read_json, read_series
    from studies.cantilever import find_freecadcmd

    run = REPO / "runs/20261120-010318_bracket_modal_mesh"
    pt = read_json(run / "manifest.json")["points"][2]           # 1.95 mm elements
    pdir = run / "points" / pt["label"]
    s = read_series(pdir / "mode_shapes.csv")
    work = Path(tempfile.mkdtemp(prefix="modes_gif_"))
    try:
        for f in ("arm.step", "mesh.geo"):
            shutil.copy(pdir / "solver" / f, work / f)
        gmsh = find_freecadcmd().parent / "gmsh.exe"
        subprocess.run([str(gmsh), "mesh.geo", "-3", "-format", "inp", "-o", "mesh.inp"],
                       cwd=work, capture_output=True, check=True, timeout=600)
        nodes, elems = read_inp(work / "mesh.inp")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    ids = s["node_id"].astype(int)
    if len(nodes) != len(ids):
        raise RuntimeError("re-meshed node count differs from the saved results")
    index = {nid: k for k, nid in enumerate(ids)}
    tris = np.vectorize(index.get)(boundary_triangles(nodes, elems))
    xyz = np.column_stack([s["x_mm"], s["y_mm"], s["z_mm"]])
    freqs, types = pt["solver_outputs"]["frequency_Hz"], pt["solver_outputs"]["mode_types"]
    R = view_matrix(24, -60)
    modes = []
    for k in range(4):
        u = np.column_stack([s[f"mode{k + 1}_ux"], s[f"mode{k + 1}_uy"], s[f"mode{k + 1}_uz"]])
        mag = np.linalg.norm(u, axis=1)
        modes.append((u * 0.15 * 150 / mag.max(), mag / mag.max()))
    fig, axes = plt.subplots(1, 4, figsize=(11, 3.0), facecolor=SURFACE)
    lims = []
    for k, ax in enumerate(axes):           # fix the frame from the extreme positions
        pts = np.concatenate([(xyz + sgn * modes[k][0])[tris] @ R.T for sgn in (-1, 1)])
        lims.append(pts)

    def draw(i):
        a = np.sin(2 * np.pi * i / 24)
        for k, ax in enumerate(axes):
            ax.clear()
            draw_field(ax, xyz + a * modes[k][0], tris, abs(a) * modes[k][1], R, 0.0, 1.0)
            frame_axes(ax, lims[k])
            ax.set_title(f"mode {k + 1}: {freqs[k]:.0f} Hz\n{types[k]}", color=TEXT, fontsize=9.5)
        return []

    fig.suptitle("Bracket arm, first four modes from CalculiX (clamped at the left; colour = motion)",
                 color=TEXT, fontsize=10.5, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    anim = FuncAnimation(fig, draw, frames=24, interval=60)
    anim.save(OUT / "bracket_modes.gif", writer=PillowWriter(fps=16), dpi=90,
              savefig_kwargs={"facecolor": SURFACE})
    plt.close(fig)


def workflow_diagram():
    fig, ax = plt.subplots(figsize=(11, 3.1), facecolor=SURFACE)
    ax.set_xlim(0, 110); ax.set_ylim(0, 31); ax.set_axis_off()
    boxes = [
        (2, "1  Frame", "Requirements, units,\ninput ranges, assumptions,\ntolerances and predictions\nwritten before any run"),
        (29, "2  Model", "CAD (CadQuery, FreeCAD)\nmesh (Gmsh)\nsolve (CalculiX, OpenFOAM,\nOpenModelica, SciPy)"),
        (56, "3  Check", "Exact and handbook references\nconservation and equilibrium\nmesh convergence (GCI)\nvalidity of assumptions"),
        (83, "4  Report", "Requirement → result →\ncheck → evidence;\nuncertainty, limits,\none-command rerun"),
    ]
    for x, head, body in boxes:
        ax.add_patch(matplotlib.patches.FancyBboxPatch((x, 9), 24, 18, boxstyle="round,pad=0.4,rounding_size=1.2",
                                                       facecolor="#ffffff", edgecolor=SERIES_1, linewidth=1.4))
        ax.text(x + 1.5, 25, head, color=SERIES_1, fontsize=11, fontweight="bold", va="top")
        ax.text(x + 1.5, 21, body, color=TEXT, fontsize=8.6, va="top", linespacing=1.45)
    for x in (26.5, 53.5, 80.5):
        ax.annotate("", (x + 2.3, 18), (x, 18), arrowprops=dict(arrowstyle="-|>", color=TEXT_2, lw=1.4))
    ax.annotate("", (40, 8.2), (68, 8.2), arrowprops=dict(arrowstyle="-|>", color=SERIES_2, lw=1.4,
                                                          connectionstyle="arc3,rad=-0.35"))
    ax.text(54, 1.2, "A check fails: classify it. Bug → fix and rerun (the failed run is kept). "
            "Model limit → revise the case. Tolerance → never loosened.",
            color=SERIES_2, fontsize=8.6, ha="center")
    fig.tight_layout()
    fig.savefig(OUT / "workflow.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in (workflow_diagram, strap_contour, cantilever_contour, fin_contour, bracket_modes_gif):
        try:
            f()
            print("made", f.__name__)
        except Exception as e:  # keep going; report what was skipped
            print("skipped", f.__name__, f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()

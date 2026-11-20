"""Blender renders of verified results for the portfolio (portfolio/img/render_*.png).

Run from the repository root:

    .venv\\Scripts\\python.exe scripts\\make_renders.py [--only NAME ...] [--samples N]

Pipeline, one command:
  1. Export: each result's outer surface and its nodal field from the saved
     CalculiX evidence run -> build/render/<name>.npz + .json
     (harness.femesh: boundary faces of the solid mesh, oriented outwards).
  2. Render: Blender in background mode (scripts/blender/render_scene.py),
     Cycles, banded contours from a constant colour ramp, Standard view transform.
  3. Check: an unlit, un-anti-aliased pass of the same view; every part pixel
     must be one of the legend's band colours. A render that fails is not written
     to the portfolio, because a beautiful picture whose colours don't match its
     legend is worse than no picture.
  4. Annotate: legend, title and caption composited in matplotlib from the
     same range and band colours the shader used.

Blender is found from $BLENDER or the portable install in %LOCALAPPDATA%\\Programs\\Blender.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import BoundaryNorm, ListedColormap  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from harness.femesh import (boundary_triangles, compact, enclosed_volume,  # noqa: E402
                            extrude_planar, read_inp, von_mises, write_scene)
from harness.plotting import SURFACE, TEXT, TEXT_2  # noqa: E402

BUILD = REPO / "build" / "render"
OUT = REPO / "portfolio" / "img"
CMAP = matplotlib.colormaps["turbo"]
COLOR_TOL = 3            # max 8-bit channel difference from a band colour
COLOR_PASS = 0.995       # fraction of part pixels that must be legend colours
VOLUME_TOL = 0.005       # surface's enclosed volume vs the design volume (faceted circles cost ~0.1 %)
CREDIT = "Rendered in Blender (Cycles) from the CalculiX result; colours checked against the legend"


def find_blender() -> Path:
    if os.environ.get("BLENDER"):
        return Path(os.environ["BLENDER"])
    hits = sorted((Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Blender").glob("*/blender.exe"))
    found = shutil.which("blender")
    if hits:
        return hits[-1]
    if found:
        return Path(found)
    raise FileNotFoundError("Blender not found: set BLENDER or install the portable build")


def bands(n: int) -> list[list[float]]:
    """sRGB colour of each contour band: turbo sampled at the band centres."""
    return [list(map(float, CMAP((k + 0.5) / n)[:3])) for k in range(n)]


def surface(nodes: dict, elems, ids: np.ndarray):
    """Boundary triangles as indices into the result arrays (ordered by `ids`)."""
    index = {int(n): k for k, n in enumerate(ids)}
    return np.vectorize(index.get)(boundary_triangles(nodes, elems))


# --------------------------------------------------------------------------- scene exports

def scene_cantilever():
    from harness.runio import read_series

    pt = REPO / "runs/20261119-085818_cantilever_tet10/points/p03_mesh_size_mm-1.95312"
    nodes, elems = read_inp(pt / "solver" / "Mesh.inp")
    s = read_series(pt / "nodal_results.csv")
    tris = surface(nodes, elems, s["node_id"].astype(int))
    xyz = np.column_stack([s["x_mm"], s["y_mm"], s["z_mm"]])
    u = np.column_stack([s["ux_mm"], s["uy_mm"], s["uz_mm"]])
    vm = von_mises(s)
    k = 25.0
    xyz, tris, vm, u = compact(xyz, tris, vm, u)
    return write_scene(BUILD / "cantilever", xyz + k * u, tris, vm, ghost_xyz=xyz,
                       field="von Mises stress", units="MPa", vmin=0.0, vmax=150.0, bands=12, expected_volume_mm3=200 * 20 * 20,
                       band_colors=bands(12), elev=20, azim=-58,
                       title="Cantilever bracket under 1 kN: von Mises stress",
                       caption=f"Deflection magnified {k:g} times; undeformed shape outlined in black. "
                               "Range capped at the 150 MPa beam-theory root stress (the clamp corners are singular).")


def scene_fin():
    from harness.calculix import read_frd

    sol = REPO / "runs/20261119-221454_fin_mesh/points/p03_element_size_mm-0.25/solver"
    nodes, elems = read_inp(sol / "fin.inp")
    frd = read_frd(sol / "fin.frd")
    ids = frd["nodes"]
    blk = frd.get("NDTEMP")
    index = {int(n): k for k, n in enumerate(ids)}
    T = np.empty(len(ids))
    T[[index[int(i)] for i in blk["ids"]]] = blk["T"]
    xyz, tris, T = compact(frd["coords"] * 1000.0, surface(nodes, elems, ids), T)   # m -> mm
    return write_scene(BUILD / "fin", xyz, tris, T, field="temperature", units="°C",
                       vmin=float(np.floor(T.min())), vmax=float(np.ceil(T.max())),
                       bands=14, band_colors=bands(14), elev=22, azim=-125, distance_factor=4.5,
                       expected_volume_mm3=2 * 20 * 40,
                       title=f"Heat-sink fin: temperature, {T.max():.1f} °C at the base to {T.min():.1f} °C at the tip",
                       caption="Steady conduction with convection from every face (CalculiX heat transfer, 3D mesh).")


def scene_strap():
    import matplotlib.tri as mtri

    from harness.runio import read_series

    pt = REPO / "runs/20261119-235201_strap_hole_mesh/points/p03_hole_element_size_mm-0.125"
    s = read_series(pt / "nodal_results.csv")
    x, y, sxx = s["x_mm"], s["y_mm"], s["sxx_MPa"]
    X = np.concatenate([x, -x, x, -x])
    Y = np.concatenate([y, y, -y, -y])
    S = np.tile(sxx, 4)
    keep = np.unique(np.round(np.column_stack([X, Y]), 6), axis=0, return_index=True)[1]
    X, Y, S = X[keep], Y[keep], S[keep]
    tri = mtri.Triangulation(X, Y)
    c = np.column_stack([X[tri.triangles].mean(axis=1), Y[tri.triangles].mean(axis=1)])
    t = tri.triangles[np.hypot(c[:, 0], c[:, 1]) >= 5.0]
    xyz, faces, val = extrude_planar(np.column_stack([X, Y]), t, S, thickness=4.0)
    # 15 MPa bands placed so the 31.25 MPa nominal stress sits mid-band (a band edge at the
    # nominal stress turns round-off into speckle) and the 101.5 MPa peak falls in the top band
    common = dict(field="axial stress σxx", units="MPa", vmin=-37.5, vmax=112.5, bands=10,
                  band_colors=bands(10), expected_volume_mm3=160 * 40 * 4 - np.pi * 5 ** 2 * 4,
                  sharp_angle_deg=60, resolution=[1400, 900])
    detail = write_scene(BUILD / "strap_detail", xyz, faces, val, elev=42, azim=-70, distance_factor=2.2,
                         frame_box=[[-14, -21, -3], [14, 21, 3]], fill=0.95,
                         title="Close-up: the peak at the sides of the hole", **common)
    return [write_scene(BUILD / "strap", xyz, faces, val, elev=38, azim=-62, distance_factor=3.2,
                        title="Whole strap", **common), detail]


def scene_bracket_modes():
    from harness.runio import read_json, read_series
    from studies.cantilever import find_freecadcmd

    run = REPO / "runs/20261120-010318_bracket_modal_mesh"
    pt = read_json(run / "manifest.json")["points"][2]
    pdir = run / "points" / pt["label"]
    s = read_series(pdir / "mode_shapes.csv")
    work = Path(tempfile.mkdtemp(prefix="modes_render_"))
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
    tris = surface(nodes, elems, ids)
    xyz0 = np.column_stack([s["x_mm"], s["y_mm"], s["z_mm"]])
    out = pt["solver_outputs"]
    paths = []
    for k in range(4):
        u = np.column_stack([s[f"mode{k + 1}_ux"], s[f"mode{k + 1}_uy"], s[f"mode{k + 1}_uz"]])
        mag = np.linalg.norm(u, axis=1)
        amp = 5.0 if "torsion" in out["mode_types"][k] else 24.0     # mm at the point of largest motion
        xyz, t, m, uu = compact(xyz0, tris, mag / mag.max(), u * amp / mag.max())
        paths.append(write_scene(BUILD / f"mode{k + 1}", xyz + uu, t, m, ghost_xyz=xyz,
                                 field="relative displacement", units="", vmin=0.0, vmax=1.0, bands=10,
                                 band_colors=bands(10), elev=24, azim=-60, resolution=[1200, 800],
                                 expected_volume_mm3=150 * 25 * 7,
                                 title=f"Mode {k + 1}: {out['frequency_Hz'][k]:.1f} Hz, {out['mode_types'][k]}"))
    return paths


def scene_cad():
    import cadquery as cq

    from harness.runio import read_json
    from models.cad import mounting_plate

    plate = read_json(REPO / "runs/20261119-090540_mounting_plate/manifest.json")["points"][2]
    parts = {   # name: (solid, view elevation, azimuth, volume from the design dimensions)
        "cad_plate": (mounting_plate.build(plate["parameters"]).val(), 35, -55,
                      plate["solver_outputs"]["volume_mm3"]),
        "cad_strap": ((cq.Workplane("XY").box(160, 40, 4)
                       .cut(cq.Workplane("XY").circle(8).extrude(4, both=True))).val(), 38, -62,
                      160 * 40 * 4 - np.pi * 8 ** 2 * 4),
        "cad_arm": (cq.Workplane("XY").box(150, 25, 7, centered=(False, True, True))
                    .edges("|X").fillet(1.0).val(), 28, -58, 150 * 25 * 7 - 4 * (1 - np.pi / 4) * 150),
    }
    paths = []
    for name, (shape, elev, azim, vol) in parts.items():
        verts, faces = shape.tessellate(0.02, 0.1)
        xyz = np.array([v.toTuple() for v in verts])
        tris = np.array(faces)
        paths.append(write_scene(BUILD / name, xyz, tris, elev=elev, azim=azim, resolution=[1200, 800],
                                 sharp_angle_deg=40, title=name, expected_volume_mm3=float(vol)))
    return paths


SCENES = {"cantilever": scene_cantilever, "fin": scene_fin, "strap": scene_strap,
          "modes": scene_bracket_modes, "cad": scene_cad}


# --------------------------------------------------------------------------- render, check, annotate

def render(blender: Path, scene: Path, samples: int) -> dict:
    t0 = time.time()
    r = subprocess.run([str(blender), "-b", "--factory-startup", "-P", str(REPO / "scripts/blender/render_scene.py"),
                        "--", str(scene), str(scene.with_suffix("")), "--samples", str(samples)],
                       capture_output=True, text=True, timeout=1800)
    info = next((json.loads(l) for l in r.stdout.splitlines() if l.startswith('{"render"')), None)
    if r.returncode != 0 or info is None:
        raise RuntimeError(f"Blender failed on {scene.name}:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    info["seconds"] = round(time.time() - t0, 1)
    return info


def check_colors(scene: Path) -> dict:
    """Every part pixel of the unlit pass must be a legend band colour (within COLOR_TOL)."""
    meta = json.loads(scene.with_suffix(".json").read_text(encoding="utf-8"))
    img = plt.imread(scene.parent / (scene.stem + "_flat.png"))
    part = img[..., 3] > 0.99
    px = np.round(img[..., :3][part] * 255)
    ref = np.round(np.asarray(meta["band_colors"]) * 255)
    dist = np.abs(px[:, None, :] - ref[None, :, :]).max(axis=2)
    nearest = dist.argmin(axis=1)
    ok = dist.min(axis=1) <= COLOR_TOL
    counts = np.bincount(nearest[ok], minlength=len(ref))
    return {"part_pixels": int(part.sum()), "fraction_on_legend": float(ok.mean()),
            "bands_visible": int((counts > 0).sum()), "bands": len(ref),
            "top_band_visible": bool(counts[-1] > 0), "passed": bool(ok.mean() >= COLOR_PASS)}


def legend(fig, rect, meta):
    nb = meta["bands"]
    edges = np.linspace(meta["vmin"], meta["vmax"], nb + 1)
    cax = fig.add_axes(rect)
    sm = matplotlib.cm.ScalarMappable(cmap=ListedColormap(meta["band_colors"]), norm=BoundaryNorm(edges, nb))
    cb = fig.colorbar(sm, cax=cax, ticks=edges[::2] if nb > 10 else edges)
    label = meta["field"] + (f" ({meta['units']})" if meta["units"] else "")
    cb.set_label(label, color=TEXT_2, fontsize=9)
    cb.ax.tick_params(colors=TEXT_2, labelsize=8)
    cb.ax.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%g"))
    cb.outline.set_visible(False)


def beauty(scene: Path) -> np.ndarray:
    """The beauty pass with the shadow layer faded out towards the image border, so the
    shadow catcher's faint haze over the ground plane never shows a hard edge."""
    img = plt.imread(scene.parent / (scene.stem + "_beauty.png")).copy()
    h, w = img.shape[:2]
    def ramp(n, m):
        t = np.clip(np.minimum(np.arange(n), np.arange(n)[::-1]) / m, 0, 1)
        return t * t * (3 - 2 * t)
    fade = np.outer(ramp(h, 0.12 * h), ramp(w, 0.12 * w))
    shadow = img[..., 3] < 0.999                  # ground shadow (the part itself is opaque)
    img[..., 3] = np.where(shadow, img[..., 3] * fade, img[..., 3])
    return img


def annotate_single(scene: Path, out_png: Path):
    meta = json.loads(scene.with_suffix(".json").read_text(encoding="utf-8"))
    img = beauty(scene)
    w, h = meta.get("resolution", [1600, 1000])
    fig = plt.figure(figsize=(11, 11 * h / w * 0.86 + 0.9), facecolor=SURFACE)
    top = 1 - 0.75 / fig.get_figheight()
    ax = fig.add_axes((0.0, 0.05, 0.88, top - 0.06))
    ax.set_facecolor(SURFACE)
    ax.imshow(img)
    ax.set_axis_off()
    legend(fig, (0.9, 0.18, 0.018, 0.6), meta)
    fig.text(0.015, 1 - 0.3 / fig.get_figheight(), meta["title"], color=TEXT, fontsize=12, weight="bold", va="center")
    if meta.get("caption"):
        fig.text(0.015, 1 - 0.58 / fig.get_figheight(), meta["caption"], color=TEXT_2, fontsize=9, va="center")
    fig.text(0.015, 0.015, CREDIT, color=TEXT_2, fontsize=7.5, alpha=0.8)
    fig.savefig(out_png, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def annotate_grid(scenes: list[Path], out_png: Path, title: str, caption: str, ncol: int = 2, legend_on=True):
    metas = [json.loads(p.with_suffix(".json").read_text(encoding="utf-8")) for p in scenes]
    nrow = int(np.ceil(len(scenes) / ncol))
    w, h = metas[0].get("resolution", [1200, 800])
    cell_w = 5.1 if ncol == 2 else 3.6
    fig = plt.figure(figsize=(cell_w * ncol + (0.9 if legend_on else 0.2), cell_w * h / w * nrow + 1.1), facecolor=SURFACE)
    H = fig.get_figheight()
    usable_w = 1 - (0.9 if legend_on else 0.2) / fig.get_figwidth()
    for i, (p, m) in enumerate(zip(scenes, metas)):
        r, c = divmod(i, ncol)
        y0 = 1 - (0.8 + (r + 1) * cell_w * h / w) / H
        ax = fig.add_axes((c * usable_w / ncol, y0, usable_w / ncol, cell_w * h / w / H))
        ax.set_facecolor(SURFACE)
        ax.imshow(beauty(p))
        ax.set_axis_off()
        if legend_on:
            ax.set_title(m["title"], color=TEXT, fontsize=9.5, pad=0)
    if legend_on:
        legend(fig, (usable_w + 0.012, 0.2, 0.016, 0.55), metas[0])
    fig.text(0.012, 1 - 0.28 / H, title, color=TEXT, fontsize=12, weight="bold", va="center")
    fig.text(0.012, 1 - 0.55 / H, caption, color=TEXT_2, fontsize=9, va="center")
    fig.text(0.012, 0.012, CREDIT if legend_on else "Rendered in Blender (Cycles) from the CadQuery geometry",
             color=TEXT_2, fontsize=7.5, alpha=0.8)
    fig.savefig(out_png, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", choices=list(SCENES))
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--skip-render", action="store_true", help="reuse existing renders, redo checks and labels")
    args = ap.parse_args()
    blender = find_blender()
    BUILD.mkdir(parents=True, exist_ok=True)
    report_path = OUT / "renders.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    for name in args.only or SCENES:
        paths = SCENES[name]()
        paths = paths if isinstance(paths, list) else [paths]
        entries = []
        for p in paths:
            meta = json.loads(p.with_suffix(".json").read_text(encoding="utf-8"))
            d = np.load(p)
            # geometry check on the undeformed surface: closed, facing outwards, and enclosing
            # the part's design volume (a missing or flipped face changes the enclosed volume)
            vol = enclosed_volume(d["ghost_xyz"] if "ghost_xyz" in d else d["xyz"], d["tris"].astype(np.int64))
            err = vol / meta["expected_volume_mm3"] - 1
            if abs(err) > VOLUME_TOL:
                raise RuntimeError(f"{p.stem}: enclosed volume {vol:.1f} mm3 vs design "
                                   f"{meta['expected_volume_mm3']:.1f} mm3 ({err:+.2%})")
            info = {} if args.skip_render else render(blender, p, args.samples)
            entry = {"scene": p.stem, **info, "volume_check": {
                "enclosed_mm3": round(vol, 1), "design_mm3": round(meta["expected_volume_mm3"], 1),
                "rel_error": float(f"{err:.2e}"), "passed": True}}
            if "band_colors" in meta:
                chk = check_colors(p)
                entry["color_check"] = chk
                if not chk["passed"]:
                    raise RuntimeError(f"{p.stem}: colour check failed {chk}")
            entries.append(entry)
            print(json.dumps(entry))
        if name == "modes":
            annotate_grid(paths, OUT / "render_bracket_modes.png",
                          "Bracket arm, first four modes (CalculiX, 7 mm arm clamped at the left end)",
                          "Colour shows how far each point moves, relative to the largest motion in that mode; "
                          "undeformed shape outlined.")
        elif name == "strap":
            annotate_grid(paths, OUT / "render_strap.png",
                          "Strap, 160 × 40 × 4 mm with a 10 mm hole, pulled with 5 kN: axial stress",
                          f"Peak 101.5 MPa at the two sides of the hole, at right angles to the load (3.25 times the "
                          "31.25 MPa away from the hole); quarter-model result mirrored to the full plate.")
        elif name == "cad":
            annotate_grid(paths, OUT / "render_cad_parts.png",
                          "Parts generated from parameters by CadQuery", "Mounting plate, strap with cable hole, bracket arm.",
                          ncol=3, legend_on=False)
        else:
            annotate_single(paths[0], OUT / f"render_{name}.png")
        report[name] = entries
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("renders written to", OUT)


if __name__ == "__main__":
    main()

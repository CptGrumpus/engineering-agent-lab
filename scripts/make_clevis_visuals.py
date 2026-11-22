"""Presentation visuals for the clevis bracket optimisation (portfolio study 12).

    .venv\\Scripts\\python.exe scripts\\make_clevis_visuals.py [--samples N] [--skip-render] [--only c000 ...]

Everything is drawn from the saved evidence runs, nothing is re-solved:

  * clevis_opt_r2 (20261121-091836): the 27 candidates the optimiser tried, all at the optimisation mesh
    (4 mm quadratic tets, 1.0 mm on the fillets);
  * clevis_confirm_r2b (20261121-115130): the chosen design D at fillet elements of 1.0 / 0.85 / 0.75 mm.

The runs kept each candidate's STEP file and Gmsh script but not the mesh. The mesh is regenerated and
proved to be the one that was solved (every node id and coordinate matches the saved nodal results, and
the element count matches the solver's). Every render passes the same three gates as the other portfolio
renders: the surface encloses the CAD volume, every part pixel of the unlit pass is a legend colour, and
the lit pass reads as the right band.

Outputs:
  1. portfolio/img/anim_clevis_opt.webp: the search, candidate by candidate, ending on design D.
  2. portfolio/img/render_clevis_compare.png: the starting design against design D, one stress scale.
  3. portfolio/img/clevis_noise.png: why the optimiser stalled, and how the response surface chose D.
  4. site/v2/vp_bracket_opt.webp, th_bracket_opt.webp and the scenes.json entry: design D, deformed,
     for the page's result viewer (and build/render/opt/bracket_opt_hero.npz for its 3D view).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
import make_renders as mr  # noqa: E402
from make_renders import plt, matplotlib  # noqa: E402

from harness.femesh import compact, enclosed_volume, read_inp, write_scene  # noqa: E402
from harness.plotting import GRID, SURFACE, TEXT, TEXT_2  # noqa: E402
from harness.response_surface import design_inside_limit  # noqa: E402
from harness.runio import read_json, read_series  # noqa: E402
from studies.clevis_bracket import assessed, von_mises  # noqa: E402

RUN = REPO / "runs/20261121-091836_clevis_opt_r2"
CONFIRM = REPO / "runs/20261121-115130_clevis_confirm_r2b"
D_COARSE = CONFIRM / "points/p00_fillet_element_size_mm-1"       # same mesh settings as the candidates
D_FINE = CONFIRM / "points/p02_fillet_element_size_mm-0.75"      # the reported values
BUILD = REPO / "build/render/clevis"
OUT = REPO / "portfolio/img"
VMIN, VMAX, NB = 0.0, 110.0, 11            # 10 MPa bands; the top band is at or over the 100 MPa allowable
BOX = [[-50.0, -50.0, 0.0], [50.0, 50.0, 90.0]]    # base 100 x 100, lug top at 90 mm: one frame for all
VIEW = {"elev": 24, "azim": -128}          # from the -x, -y side: the governing fillet faces the camera
LIMIT, MARGIN = 100.0, 0.025               # REQ-C1 and the run's design margin (constraint 97.5 MPa)
ACCENT, FAIL, PASS, WARN = "#2346c4", "#b0381a", "#157447", "#855f00"
DIMS = ("lug_thickness_mm", "gusset_thickness_mm", "gusset_height_mm")


def history():
    m = read_json(RUN / "manifest.json")
    return m, m["optimization"]["history"]


def point(pt: Path) -> dict:
    return read_json(pt / "point.json")


def mesh_for(pt: Path, s) -> tuple[dict, list]:
    """Regenerate the solved mesh from the saved STEP and Gmsh script, and prove it is the same mesh."""
    from studies.cantilever import find_freecadcmd

    d = BUILD / "mesh" / f"{pt.parent.parent.name[:15]}_{pt.name}"
    d.mkdir(parents=True, exist_ok=True)
    for n in ("bracket.step", "mesh.geo"):
        shutil.copyfile(pt / "solver" / n, d / n)
    if not (d / "mesh.inp").exists():
        gmsh = find_freecadcmd().parent / "gmsh.exe"
        subprocess.run([str(gmsh), "mesh.geo", "-3", "-format", "inp", "-o", "mesh.inp"], cwd=d,
                       capture_output=True, text=True, timeout=1800, check=True)
    nodes, elems = read_inp(d / "mesh.inp")
    ids = s["node_id"].astype(int)
    if set(nodes) != set(ids.tolist()):
        raise RuntimeError(f"{pt.name}: regenerated mesh has different nodes from the solved one")
    xyz = np.array([nodes[i] for i in ids])
    # saved coordinates come from the CalculiX .frd at 6 significant figures (about 1e-4 mm here)
    dev = np.abs(xyz - np.column_stack([s["x_mm"], s["y_mm"], s["z_mm"]])).max()
    if dev > 2e-3:
        raise RuntimeError(f"{pt.name}: regenerated mesh differs from the solved one by {dev:.2e} mm")
    solved = point(pt).get("solver_outputs", {}).get("elements")
    if solved is not None and int(solved) != len(elems):
        raise RuntimeError(f"{pt.name}: {len(elems)} elements regenerated, {solved} solved")
    return nodes, elems


def load(pt: Path):
    s = read_series(pt / "nodal_results.csv")
    nodes, elems = mesh_for(pt, s)
    tris = mr.surface(nodes, elems, s["node_id"].astype(int))
    xyz = np.column_stack([s["x_mm"], s["y_mm"], s["z_mm"]])
    u = np.column_stack([s["ux_mm"], s["uy_mm"], s["uz_mm"]])
    return s, xyz, tris, von_mises(s), u


def export(pt: Path, name: str) -> Path:
    """A candidate as designed (undeformed), on the shared camera and stress scale."""
    s, xyz, tris, vm, _ = load(pt)
    xyz, tris, vm = compact(xyz, tris, vm)
    return write_scene(BUILD / name, xyz, tris, vm, field="von Mises stress", units="MPa",
                       vmin=VMIN, vmax=VMAX, bands=NB, band_colors=mr.bands(NB), **VIEW,
                       fixed_box=BOX, resolution=[1100, 900], fill=0.90, distance_factor=4.2,
                       expected_volume_mm3=point(pt)["solver_outputs"]["cad_volume_mm3"],
                       title=name, caption="")


def gate(scene: Path, ghost: bool = False) -> dict:
    meta = json.loads(scene.with_suffix(".json").read_text(encoding="utf-8"))
    d = np.load(scene)
    vol = enclosed_volume(d["ghost_xyz" if ghost else "xyz"], d["tris"].astype(np.int64))
    err = vol / meta["expected_volume_mm3"] - 1
    if abs(err) > mr.VOLUME_TOL:
        raise RuntimeError(f"{scene.stem}: enclosed volume {err:+.2%} off the CAD volume")
    chk = mr.check_colors(scene)
    if not chk["passed"]:
        raise RuntimeError(f"{scene.stem}: colour check failed {chk}")
    leg = mr.check_legibility(scene)
    if not leg["passed"]:
        raise RuntimeError(f"{scene.stem}: the lit render misreads {leg['misread']:.2%} of the part {leg}")
    return {"scene": scene.stem, "volume_rel_error": float(f"{err:.2e}"), "enclosed_mm3": round(float(vol), 1),
            "design_mm3": round(meta["expected_volume_mm3"], 1), "color_check": chk, "legibility_check": leg}


# --------------------------------------------------------------------------- the numbers

def peak(lab_or_pt) -> float:
    pt = lab_or_pt if isinstance(lab_or_pt, Path) else RUN / "points" / lab_or_pt
    return point(pt)["metrics"]["peak_von_mises_MPa"]


def chosen_design(hist) -> dict:
    """Re-derive design D from the run, as cases/clevis_confirm_r2.toml did: a linear fit of the peak
    stress over the converged candidates c012 to c026, moved two residual sd inside the search limit."""
    conv = [h for h in hist if int(h["label"][1:]) >= 12]
    X = np.array([[h["variables"][k] for k in DIMS] for h in conv])
    y = np.array([peak(h["label"]) for h in conv])
    r = design_inside_limit(X, y, LIMIT * (1 - MARGIN), 2.0, order=[1, 2])
    want = [point(D_COARSE)["parameters"][k] for k in DIMS]
    if np.abs(r["x"] - want).max() > 1e-6:
        raise RuntimeError(f"response surface gives {r['x']}, the confirmation run used {want}")
    A = np.c_[np.ones(len(X)), X]
    return {**r, "labels": [h["label"] for h in conv], "y": y, "y_fit": A @ r["fit"]["coef"]}


def status(h):
    s = peak(h["label"])
    if h["feasible"]:
        return "ok", f"{s:.1f} MPa: inside the 97.5 MPa search limit", PASS
    if s <= LIMIT:
        return "edge", f"{s:.1f} MPa: under 100, but inside the margin kept for mesh error", WARN
    return "over", f"{s:.1f} MPa: over the 100 MPa limit", FAIL


def style(ax):
    ax.set_facecolor(SURFACE)
    for sp in ax.spines.values():
        sp.set_color(GRID)
    ax.tick_params(colors=TEXT_2, labelsize=9)
    ax.grid(True, color=GRID, linewidth=0.6)


# --------------------------------------------------------------------------- animation

def frame(fig, k, hist, imgs, final=None):
    """One frame: candidate k (or design D when `final` holds its numbers)."""
    upto = len(hist) - 1 if final else k
    fig.clf()
    fig.patch.set_facecolor(SURFACE)
    fig.text(0.02, 0.955, "Bracket optimisation: the agent's design search, candidate by candidate",
             color=TEXT, fontsize=15, weight="bold", va="center")
    fig.text(0.02, 0.915, "Each candidate is built in CadQuery, meshed in Gmsh, solved in CalculiX and checked before the "
             "optimiser (COBYLA) may use it.\nLimit 100 MPa; the search aims at 97.5 MPa to leave room for mesh error.",
             color=TEXT_2, fontsize=10, va="center", linespacing=1.5)
    ax = fig.add_axes((0.0, 0.23, 0.52, 0.64))
    ax.imshow(imgs[-1] if final else imgs[k])
    ax.set_axis_off()
    if final:
        v, mass = final["variables"], final["mass"]
        fig.text(0.03, 0.215, "Design D, chosen from the search", color=TEXT, fontsize=13, weight="bold", va="center")
        msg, col = final["msg"], PASS
    else:
        h = hist[k]
        v, mass = h["variables"], h["objective"]
        fig.text(0.03, 0.215, f"Candidate {k + 1} of {len(hist)}", color=TEXT, fontsize=13, weight="bold", va="center")
        _, msg, col = status(h)
        msg = "●  " + msg
    fig.text(0.03, 0.172, f"lug {v['lug_thickness_mm']:.2f} mm   gussets {v['gusset_thickness_mm']:.2f} × "
             f"{v['gusset_height_mm']:.1f} mm   mass {mass:.1f} g", color=TEXT, fontsize=11, va="center", family="monospace")
    fig.text(0.03, 0.13, msg, color=col, fontsize=10.5, va="center", weight="bold")
    cax = fig.add_axes((0.03, 0.065, 0.46, 0.022))
    edges = np.linspace(VMIN, VMAX, NB + 1)
    sm = matplotlib.cm.ScalarMappable(cmap=matplotlib.colors.ListedColormap(mr.bands(NB)),
                                      norm=matplotlib.colors.BoundaryNorm(edges, NB))
    cb = fig.colorbar(sm, cax=cax, orientation="horizontal", ticks=edges[::2])
    cb.outline.set_visible(False)
    cb.ax.tick_params(colors=TEXT_2, labelsize=8.5)
    cb.set_label("von Mises stress (MPa), shape as designed; the top band is at or over the 100 MPa limit",
                 color=TEXT_2, fontsize=8.5)

    # peak stress against mass, everything tried so far
    a2 = fig.add_axes((0.585, 0.43, 0.39, 0.44))
    style(a2)
    a2.axhspan(LIMIT * (1 - MARGIN), LIMIT, color="#f9efd6", zorder=0)
    a2.axhline(LIMIT, color=FAIL, lw=1.3)
    a2.axhline(LIMIT * (1 - MARGIN), color=WARN, lw=1, ls=(0, (4, 3)))
    a2.text(406, LIMIT + 0.4, "100 MPa limit", color=FAIL, fontsize=8, ha="right", va="bottom")
    a2.text(406, LIMIT * (1 - MARGIN) - 0.5, "97.5 MPa search limit", color=WARN, fontsize=8, ha="right", va="top")
    top = 108.0
    for i, h in enumerate(hist[:upto + 1]):
        _, _, c = status(h)
        s = peak(h["label"])
        if s > top:                      # off the scale: a marker on the top edge, value in the status line
            a2.plot(h["objective"], top - 0.6, "^", ms=7, color=c, mec="white", mew=0.6, zorder=3, clip_on=False)
        else:
            a2.plot(h["objective"], s, "o", ms=5.5, color=c, mec="white", mew=0.6, zorder=3)
    if any(peak(h["label"]) > top for h in hist[:upto + 1]):
        a2.text(362.5, top - 0.6, "◀ over 108 MPa, off the scale", color=FAIL, fontsize=7.5, va="center")
    if not final:
        a2.plot(hist[k]["objective"], min(peak(hist[k]["label"]), top - 0.6), "o", ms=13, mfc="none", mec=TEXT,
                mew=1.6, zorder=4)
    else:
        a2.plot(final["mass"], final["peak"], "*", ms=17, color="#e9b10c", mec=TEXT, mew=0.6, zorder=5)
        a2.annotate("D", (final["mass"], final["peak"]), xytext=(9, -4), textcoords="offset points", fontsize=10,
                    weight="bold", color=TEXT)
    a2.set_xlim(350, 408)
    a2.set_ylim(80, top)
    a2.set_xlabel("mass (g)", color=TEXT_2, fontsize=9)
    a2.set_ylabel("peak stress (MPa)", color=TEXT_2, fontsize=9)
    a2.set_title("Peak stress against mass, every candidate so far", color=TEXT, fontsize=10, loc="left")

    # the three dimensions
    a3 = fig.add_axes((0.585, 0.09, 0.39, 0.23))
    style(a3)
    n = np.arange(1, upto + 2)
    for key, name, c in ((DIMS[0], "lug thickness", ACCENT), (DIMS[1], "gusset thickness", "#2a9d8f")):
        a3.plot(n, [h["variables"][key] for h in hist[:upto + 1]], "-o", ms=3, lw=1.3, color=c, label=name)
        if final:
            a3.plot(len(hist) + 1.5, final["variables"][key], "*", ms=11, color=c, mec=TEXT, mew=0.5)
    a3.set_xlim(0, len(hist) + 2.5)
    a3.set_ylim(2, 15)
    a3.set_xlabel("candidate", color=TEXT_2, fontsize=9)
    a3.set_ylabel("mm", color=TEXT_2, fontsize=9)
    a3.legend(frameon=False, fontsize=8, loc="upper right", labelcolor=TEXT, ncol=2)
    a3.set_title("The thicknesses it tried (gusset height stays near 36 mm)", color=TEXT, fontsize=10, loc="left")


def make_animation(hist, scenes, d_scene, d_info):
    from PIL import Image

    imgs = [mr.beauty(p) for p in scenes] + [mr.beauty(d_scene)]
    fig = plt.figure(figsize=(14, 7.6), dpi=100)
    frames, durations = [], []
    for k in range(len(hist)):
        frame(fig, k, hist, imgs)
        fig.canvas.draw()
        frames.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()))
        durations.append(1000 if k < 8 else 450)
    frame(fig, None, hist, imgs, final=d_info)
    fig.canvas.draw()
    last = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3].copy())
    frames.append(last)
    durations.append(5000)
    plt.close(fig)
    out = OUT / "anim_clevis_opt.webp"
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=durations, loop=0, lossless=True,
                   quality=100, method=6)
    return out


# --------------------------------------------------------------------------- figures

def make_compare(start_scene, d_scene, d_pt):
    s0, sd = point(RUN / "points/c000"), point(d_pt)
    fig = plt.figure(figsize=(13, 6.6), facecolor=SURFACE)
    for i, (p, pt, title) in enumerate([(start_scene, s0, "Start: lug 12 mm, gussets 8 × 40 mm"),
                                        (d_scene, sd, "Design D: lug 10.17 mm, gussets 9.07 × 36.4 mm")]):
        m = pt["metrics"]
        ax = fig.add_axes((0.01 + i * 0.44, 0.08, 0.43, 0.74))
        ax.imshow(mr.beauty(p))
        ax.set_axis_off()
        fig.text(0.03 + i * 0.44, 0.84, title, color=TEXT, fontsize=12.5, weight="bold")
        fig.text(0.03 + i * 0.44, 0.805, f"{m['mass_g']:.1f} g · peak {m['peak_von_mises_MPa']:.1f} MPa · "
                 f"pin {m['pin_deflection_mm']:.3f} mm", color=TEXT_2, fontsize=10.5, family="monospace")
    mr.legend(fig, (0.915, 0.16, 0.016, 0.6), json.loads(start_scene.with_suffix(".json").read_text(encoding="utf-8")))
    fig.text(0.03, 0.93, "Same load, same limits, 4 % lighter", color=TEXT, fontsize=15, weight="bold")
    fig.text(0.03, 0.02, "Both on the optimisation mesh (1.0 mm fillet elements), one camera and one stress scale, rendered in "
             "Blender from the CalculiX results and checked against the legend.\nThe peak is at the fillet at the lug's "
             "outer end; the tops of the gussets come close behind (94 MPa on design D).", color=TEXT_2, fontsize=8.5,
             linespacing=1.5)
    fig.savefig(OUT / "render_clevis_compare.png", dpi=120, facecolor=SURFACE)
    plt.close(fig)


def make_noise_chart(rs):
    conf = [point(CONFIRM / "points" / n)["metrics"]["peak_von_mises_MPa"]
            for n in ("p00_fillet_element_size_mm-1", "p01_fillet_element_size_mm-0.85", "p02_fillet_element_size_mm-0.75")]
    sd = rs["fit"]["residual_sd"]
    unc = next(c["value"] for c in read_json(CONFIRM / "verification.json")["run_checks"]
               if c["id"] == "discretization_peak_von_mises_MPa")
    fig, ax = plt.subplots(figsize=(11, 5.6), facecolor=SURFACE)
    style(ax)
    lo, hi = 94.0, 101.5
    t = np.linspace(lo, hi, 2)
    ax.fill_between(t, t - 2 * sd, t + 2 * sd, color="#e4e9fb", zorder=0, label=f"fit ± 2 sd ({2 * sd:.1f} MPa)")
    ax.plot(t, t, color=ACCENT, lw=1.2, zorder=1)
    ax.axhline(LIMIT, color=FAIL, lw=1.3)
    ax.text(lo + 0.1, LIMIT + 0.12, "100 MPa limit", color=FAIL, fontsize=9, va="bottom")
    ax.axhline(LIMIT * (1 - MARGIN), color=WARN, lw=1, ls=(0, (4, 3)))
    ax.text(lo + 0.1, LIMIT * (1 - MARGIN) + 0.12, "97.5 MPa search limit", color=WARN, fontsize=9, va="bottom")
    ax.plot(rs["y_fit"], rs["y"], "o", ms=7, color="#7f8c9d", mec="white", mew=0.8, zorder=3,
            label="candidates 13 to 27: the stress the optimiser saw")
    ax.plot([rs["fitted"]] * 3, conf, "-", color=PASS, lw=1.2, zorder=3)
    ax.plot([rs["fitted"]] * 3, conf, "D", ms=7, color=PASS, mec="white", mew=0.8, zorder=4,
            label="design D, mesh study: 1.0 / 0.85 / 0.75 mm fillet elements")
    ax.annotate(f"D: fit {rs['fitted']:.1f} MPa;\nmesh study {conf[0]:.1f} to {conf[-1]:.1f} MPa,\n"
                f"{conf[-1] * (1 + unc):.1f} with its uncertainty", (rs["fitted"], conf[-1]), xytext=(-150, 12),
                textcoords="offset points", fontsize=9, color=PASS, arrowprops=dict(arrowstyle="-", color=PASS, lw=0.8))
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel("peak stress the fit predicts from the three dimensions (MPa)", color=TEXT_2)
    ax.set_ylabel("peak stress CalculiX found (MPa)", color=TEXT_2)
    ax.set_title("Why the optimiser stalled, and how design D was chosen", color=TEXT, fontsize=12, loc="left", weight="bold")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right", labelcolor=TEXT)
    fig.text(0.01, 0.012, f"A linear fit through the last 15 candidates. They scatter ±{sd:.1f} MPa around it for changes under "
             "0.15 mm, because a fillet peak is a maximum over mesh nodes.\nD sits where the fit reads two standard "
             "deviations under the search limit.", color=TEXT_2, fontsize=8, linespacing=1.5)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(OUT / "clevis_noise.png", dpi=140, facecolor=SURFACE)
    plt.close(fig)


def make_hero(blender, samples):
    """Design D on the finest mesh, deformed, for the page's result viewer and its 3D view."""
    from PIL import Image

    s, xyz, tris, vm, u = load(D_FINE)
    xyz, tris, vm, u = compact(xyz, tris, vm, u)
    k = 100.0
    scene = write_scene(REPO / "build/render/opt/bracket_opt_hero", xyz + k * u, tris, vm, ghost_xyz=xyz,
                        field="von Mises stress", units="MPa", vmin=VMIN, vmax=VMAX, bands=NB,
                        band_colors=mr.bands(NB), **VIEW,
                        expected_volume_mm3=point(D_FINE)["solver_outputs"]["cad_volume_mm3"],
                        title="Optimised clevis bracket", caption="")
    if blender is not None:
        mr.render(blender, scene, samples)
    g = gate(scene, ghost=True)
    site = REPO / "site" / "v2"
    a = (np.clip(mr.beauty(scene), 0, 1) * 255).astype(np.uint8)
    im = Image.fromarray(a, "RGBA")
    ys, xs = np.nonzero(np.asarray(im)[..., 3] > 60)
    pad = int(0.10 * max(np.ptp(xs), np.ptp(ys)))
    im = im.crop((max(0, xs.min() - pad), max(0, ys.min() - pad), min(im.width, xs.max() + pad), min(im.height, ys.max() + pad)))
    vp = im.copy()
    vp.thumbnail((1400, 900), Image.LANCZOS)
    vp.save(site / "vp_bracket_opt.webp", quality=90, method=6)
    th = im.copy()
    th.thumbnail((800, 500), Image.LANCZOS)
    canvas = Image.new("RGBA", (800, 500), (0, 0, 0, 0))
    canvas.alpha_composite(th, ((800 - th.width) // 2, (500 - th.height) // 2))
    canvas.save(site / "th_bracket_opt.webp", quality=88, method=6)
    meta = json.loads(scene.with_suffix(".json").read_text(encoding="utf-8"))
    scenes_path = site / "scenes.json"
    scenes = json.loads(scenes_path.read_text(encoding="utf-8"))
    scenes["bracket_opt"] = {kk: meta.get(kk) for kk in ("field", "units", "vmin", "vmax", "bands", "band_colors",
                                                          "title", "caption", "data_min", "data_max")}
    scenes["bracket_opt"]["volume"] = {"enclosed_mm3": g["enclosed_mm3"], "design_mm3": g["design_mm3"],
                                       "rel_error": g["volume_rel_error"], "passed": True}
    scenes["bracket_opt"]["color"] = g["color_check"]
    scenes["bracket_opt"]["legibility"] = g["legibility_check"]
    scenes_path.write_text(json.dumps(scenes, indent=1), encoding="utf-8")
    return g


def make_wipe(blender, samples):
    """The starting design and design D as two images with one camera and one crop, for the page's
    before-and-after wipe (site/v2/wipe_start.webp, wipe_d.webp). Both pass the three render gates."""
    from PIL import Image

    out = {}
    for pt, name in ((RUN / "points/c000", "wipe_start"), (D_COARSE, "wipe_d")):
        sc = export(pt, name)
        if blender is not None:
            mr.render(blender, sc, samples)
        g = gate(sc)
        m = point(pt)["metrics"]
        out[name] = {"scene": sc, "gate": g, "mass_g": round(m["mass_g"], 1), "peak_MPa": round(m["peak_von_mises_MPa"], 1)}
        print(name, g["volume_rel_error"], g["color_check"]["fraction_on_legend"], g["legibility_check"]["misread"])
    ims = {k: Image.fromarray((np.clip(mr.beauty(v["scene"]), 0, 1) * 255).astype(np.uint8), "RGBA") for k, v in out.items()}
    alpha = np.maximum(*[np.asarray(im)[..., 3] for im in ims.values()])
    ys, xs = np.nonzero(alpha > 60)
    pad = int(0.08 * max(np.ptp(xs), np.ptp(ys)))
    crop = (max(0, xs.min() - pad), max(0, ys.min() - pad), xs.max() + pad, ys.max() + pad)
    site = REPO / "site" / "v2"
    for k, im in ims.items():
        im = im.crop(crop)
        im.thumbnail((1200, 1000), Image.LANCZOS)
        im.save(site / f"{k}.webp", quality=90, method=6)
    info = {k: {kk: vv for kk, vv in v.items() if kk != "scene"} for k, v in out.items()}
    (site / "wipe.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--skip-render", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--wipe", action="store_true", help="only the before-and-after pair for the page's wipe")
    args = ap.parse_args()
    if args.wipe:
        make_wipe(None if args.skip_render else mr.find_blender(), 128)
        return
    _, hist = history()
    labels = args.only or [h["label"] for h in hist]
    blender = mr.find_blender()
    report, scenes = [], {}
    jobs = [(RUN / "points" / lab, lab) for lab in labels]
    if not args.only:
        jobs.append((D_COARSE, "design_d"))
    for pt, name in jobs:
        p = export(pt, name)
        if not args.skip_render:
            print(name, mr.render(blender, p, args.samples)["seconds"], "s", flush=True)
        report.append(gate(p))
        scenes[name] = p
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "checks.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    worst_c = min(r["color_check"]["fraction_on_legend"] for r in report)
    worst_l = max(r["legibility_check"]["misread"] for r in report)
    worst_v = max(abs(r["volume_rel_error"]) for r in report)
    print(f"{len(report)} renders gated: colour {worst_c:.4f} on the legend at worst, misread {worst_l:.2%} at worst, "
          f"volume {worst_v:.2e} at worst")
    if args.only:
        return
    rs = chosen_design(hist)
    d = point(D_COARSE)
    d_info = {"variables": d["parameters"], "mass": d["metrics"]["mass_g"], "peak": d["metrics"]["peak_von_mises_MPa"],
              "msg": "✓  Its own mesh study: 98.3 MPa, 98.9 with the uncertainty"}
    hero = make_hero(None if args.skip_render else blender, 160)
    print("hero:", hero["volume_rel_error"], hero["color_check"]["fraction_on_legend"], hero["legibility_check"]["misread"])
    make_compare(scenes["c000"], scenes["design_d"], D_COARSE)
    make_noise_chart(rs)
    out = make_animation(hist, [scenes[h["label"]] for h in hist], scenes["design_d"], d_info)
    print("written", out, out.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()

"""Presentation visuals for the bracket optimisation study (portfolio study 12).

    .venv\\Scripts\\python.exe scripts\\make_opt_visuals.py [--samples N] [--skip-render]

Everything is drawn from the saved evidence run, nothing is re-solved:

  1. Every candidate the optimiser tried (32 CalculiX solutions) is exported and rendered in
     Blender with one fixed camera and stage, von Mises stress on one legend. Each render passes
     the same two gates as the other portfolio renders: the surface encloses the candidate's
     design volume, and every part pixel of the unlit pass is a legend colour.
  2. anim_bracket_opt.webp: the search, frame by frame. The candidate's render, its place in the
     design space (feasible region from independent tapered-beam theory), and the mass so far.
  3. render_bracket_compare.png: the starting prismatic bar against the optimum, same scale.
  4. bracket_stress_span.png: the design stress along the span for the start, the optimum, and
     a candidate a root-only stress check would have accepted.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
import make_renders as mr  # noqa: E402
from make_renders import plt, matplotlib  # noqa: E402

from harness.femesh import compact, enclosed_volume, read_inp, von_mises, write_scene  # noqa: E402
from harness.plotting import GRID, SURFACE, TEXT, TEXT_2  # noqa: E402
from harness.runio import read_json, read_series  # noqa: E402
from validation import tapered_beam as tb  # noqa: E402

RUN = REPO / "runs/20261120-225322_bracket_opt"
BUILD = REPO / "build/render/opt"
OUT = REPO / "portfolio/img"
VMIN, VMAX, NB = 0.0, 110.0, 11            # 10 MPa bands; the top band is at or over the 100 MPa allowable
BOX = [[0.0, -10.0, -20.0], [200.0, 10.0, 20.0]]   # largest candidate height is 27 mm; room to spare
ACCENT, FAIL, PASS, WARN = "#2346c4", "#b0381a", "#157447", "#855f00"


def history():
    m = read_json(RUN / "manifest.json")
    return m, m["optimization"]["history"]


def params_of(label):
    return read_json(RUN / "points" / label / "point.json")["parameters"]


def mesh_for(label, s):
    """The run kept the STEP file and the Gmsh script but not mesh.inp. Regenerate it, and prove it
    is the mesh that was solved: every node id and coordinate must match the saved nodal results."""
    import shutil
    import subprocess

    from studies.cantilever import find_freecadcmd

    src, d = RUN / "points" / label / "solver", BUILD / "mesh" / label
    d.mkdir(parents=True, exist_ok=True)
    for n in ("bracket.step", "mesh.geo"):
        shutil.copyfile(src / n, d / n)
    if not (d / "mesh.inp").exists():
        gmsh = find_freecadcmd().parent / "gmsh.exe"
        subprocess.run([str(gmsh), "mesh.geo", "-3", "-format", "inp", "-o", "mesh.inp"], cwd=d,
                       capture_output=True, text=True, timeout=600, check=True)
    nodes, elems = read_inp(d / "mesh.inp")
    ids = s["node_id"].astype(int)
    if set(nodes) != set(ids.tolist()):
        raise RuntimeError(f"{label}: regenerated mesh has different nodes from the solved one")
    xyz = np.array([nodes[i] for i in ids])
    # the saved coordinates come from the CalculiX .frd, written to 6 significant figures
    # (about 1e-3 mm on a 200 mm part), so that is the resolution of the comparison
    dev = np.abs(xyz - np.column_stack([s["x_mm"], s["y_mm"], s["z_mm"]])).max()
    if dev > 2e-3:
        raise RuntimeError(f"{label}: regenerated mesh differs from the solved one by {dev:.2e} mm")
    solved = read_json(RUN / "points" / label / "point.json").get("solver_outputs", {}).get("elements")
    if solved is not None and int(solved) != len(elems):
        raise RuntimeError(f"{label}: {len(elems)} elements regenerated, {solved} solved")
    return nodes, elems


def export(label) -> Path:
    pt = RUN / "points" / label
    s = read_series(pt / "nodal_results.csv")
    nodes, elems = mesh_for(label, s)
    tris = mr.surface(nodes, elems, s["node_id"].astype(int))
    xyz = np.column_stack([s["x_mm"], s["y_mm"], s["z_mm"]])
    vm = von_mises(s)
    xyz, tris, vm = compact(xyz, tris, vm)
    p = params_of(label)
    return write_scene(BUILD / label, xyz, tris, vm, field="von Mises stress", units="MPa",
                       vmin=VMIN, vmax=VMAX, bands=NB, band_colors=mr.bands(NB), elev=17, azim=-63,
                       fixed_box=BOX, resolution=[1400, 640], fill=0.92, distance_factor=4.2,
                       expected_volume_mm3=tb.volume(p["length_mm"], p["width_mm"],
                                                     p["root_height_mm"], p["tip_height_mm"]),
                       title=label, caption="")


def gate(scene: Path) -> dict:
    meta = json.loads(scene.with_suffix(".json").read_text(encoding="utf-8"))
    d = np.load(scene)
    vol = enclosed_volume(d["xyz"], d["tris"].astype(np.int64))
    err = vol / meta["expected_volume_mm3"] - 1
    if abs(err) > mr.VOLUME_TOL:
        raise RuntimeError(f"{scene.stem}: enclosed volume {err:+.2%} off the design volume")
    chk = mr.check_colors(scene)
    if not chk["passed"]:
        raise RuntimeError(f"{scene.stem}: colour check failed {chk}")
    leg = mr.check_legibility(scene)
    if not leg["passed"]:
        raise RuntimeError(f"{scene.stem}: the lit render misreads {leg['misread']:.2%} of the part {leg}")
    return {"scene": scene.stem, "volume_rel_error": float(f"{err:.2e}"), "color_check": chk, "legibility_check": leg}


# --------------------------------------------------------------------------- design-space background

def design_space(case):
    P = case
    F, L, E, nu, b = P["tip_load_N"], P["length_mm"], P["youngs_modulus_MPa"], P["poisson_ratio"], P["width_mm"]
    hr = np.linspace(16, 32, 161)
    ht = np.linspace(5, 30, 126)
    HR, HT = np.meshgrid(hr, ht)
    S = np.vectorize(lambda a, c: tb.peak_nominal_stress(F, L, b, a, c)[0])(HR, HT)
    D = np.vectorize(lambda a, c: tb.tip_deflection(F, L, E, nu, b, a, c))(HR, HT)
    M = tb.volume(L, b, HR, HT) * P["density_t_per_mm3"] * 1e6
    root = 6 * F * L / (b * hr ** 2)                       # root-only stress, independent of h_t
    return hr, ht, HR, HT, S, D, M, root


def status(h):
    g_d, g_s = h["constraints"]
    if not h["verified"]:
        return "rejected", "Rejected by the checks: outside the small-deflection range", FAIL
    if h["feasible"]:
        return "ok", "Inside both limits", PASS
    worst = min(g_d, g_s)
    if worst > -0.002:
        return "edge", "On the limit (within 0.2 %)", WARN
    which = "stress" if g_s < g_d else "deflection"
    return "over", f"Over the {which} limit by {-worst * 100:.1f} %", FAIL


def style(ax):
    ax.set_facecolor(SURFACE)
    for s in ax.spines.values():
        s.set_color(GRID)
    ax.tick_params(colors=TEXT_2, labelsize=9)
    ax.grid(True, color=GRID, linewidth=0.6)


def frame(fig, k, hist, imgs, bg, best_upto, final=False, upto=None):
    hr, ht, HR, HT, S, D, M, root = bg
    upto = k if upto is None else upto
    h = hist[k]
    key, msg, col = status(h)
    if final:
        msg = msg + ", and 30 % lighter than the 785 g bar it started from"
    fig.clf()
    fig.patch.set_facecolor(SURFACE)
    W, H = fig.get_figwidth(), fig.get_figheight()

    # title row
    fig.text(0.02, 0.955, "Bracket optimisation: the agent's design search, candidate by candidate",
             color=TEXT, fontsize=15, weight="bold", va="center")
    fig.text(0.02, 0.915, "Each candidate is built in CadQuery, meshed in Gmsh, solved in CalculiX and checked "
             "before the optimiser (COBYLA) may use it. Limits: 100 MPa stress, 1.0 mm tip deflection.",
             color=TEXT_2, fontsize=10, va="center")

    # render
    ax = fig.add_axes((0.0, 0.25, 0.60, 0.62))
    ax.imshow(imgs[k])
    ax.set_axis_off()
    lab = f"Candidate {k + 1} of {len(hist)}" if not final else "Optimum"
    v = h["variables"]
    fig.text(0.03, 0.235, lab, color=TEXT, fontsize=13, weight="bold", va="center")
    fig.text(0.03, 0.19, f"root {v['root_height_mm']:.1f} mm   tip {v['tip_height_mm']:.1f} mm   "
             f"mass {h['objective']:.0f} g", color=TEXT, fontsize=11.5, va="center", family="monospace")
    fig.text(0.03, 0.145, ("●  " if key != "rejected" else "✕  ") + msg, color=col, fontsize=11, va="center",
             weight="bold")
    # legend under the render
    cax = fig.add_axes((0.03, 0.055, 0.50, 0.025))
    edges = np.linspace(VMIN, VMAX, NB + 1)
    sm = matplotlib.cm.ScalarMappable(cmap=matplotlib.colors.ListedColormap(mr.bands(NB)),
                                      norm=matplotlib.colors.BoundaryNorm(edges, NB))
    cb = fig.colorbar(sm, cax=cax, orientation="horizontal", ticks=edges[::2])
    cb.outline.set_visible(False)
    cb.ax.tick_params(colors=TEXT_2, labelsize=8.5)
    cb.set_label("von Mises stress (MPa), shape as designed; the top band is at or over the 100 MPa allowable",
                 color=TEXT_2, fontsize=8.5)

    # design space
    a2 = fig.add_axes((0.655, 0.40, 0.32, 0.47))
    style(a2)
    feas = (S <= 100 * 0.995) & (D <= 1.0 * 0.995)
    a2.contourf(HR, HT, feas.astype(float), levels=[0.5, 1.5], colors=["#e0f1e7"])
    cs = a2.contour(HR, HT, M, levels=np.arange(450, 951, 50), colors=[GRID], linewidths=0.8)
    a2.clabel(cs, fmt="%d g", fontsize=7, colors=TEXT_2)
    a2.contour(HR, HT, S, levels=[100 * 0.995], colors=[FAIL], linewidths=1.4)
    a2.contour(HR, HT, D, levels=[0.995], colors=["#2a78d6"], linewidths=1.4)
    a2.axvline(np.sqrt(6 * 1000 * 200 / (20 * 99.5)), color=TEXT_2, lw=1, ls=(0, (4, 3)))
    a2.text(24.75, 29.2, "root-only\nstress limit", fontsize=7.5, color=TEXT_2, va="top", ha="left")
    a2.text(31.6, 6.0, "stress limit", fontsize=8, color=FAIL, ha="right", va="bottom")
    a2.text(18.4, 15.0, "deflection\nlimit", fontsize=8, color="#2a78d6", va="center")
    a2.text(30.5, 24, "feasible", fontsize=9, color=PASS, ha="right", weight="bold")
    xs = [hh["variables"]["root_height_mm"] for hh in hist[:upto + 1]]
    ys = [hh["variables"]["tip_height_mm"] for hh in hist[:upto + 1]]
    a2.plot(xs, ys, "-", color=ACCENT, lw=1.0, alpha=0.55, zorder=3)
    for hh, x, y in zip(hist[:upto + 1], xs, ys):
        kk, _, cc = status(hh)
        a2.plot(x, y, "x" if kk == "rejected" else "o", ms=5 if kk != "rejected" else 7, color=cc,
                mec="white" if kk != "rejected" else cc, mew=0.6 if kk != "rejected" else 2, zorder=4)
    a2.plot(h["variables"]["root_height_mm"], h["variables"]["tip_height_mm"], "o", ms=13, mfc="none", mec=TEXT, mew=1.6, zorder=5)
    if best_upto[upto] is not None:
        b_ = hist[best_upto[upto]]["variables"]
        a2.plot(b_["root_height_mm"], b_["tip_height_mm"], "*", ms=15, color="#e9b10c", mec=TEXT, mew=0.6, zorder=6)
    a2.set_xlim(16, 32)
    a2.set_ylim(5, 30)
    a2.set_xlabel("root height (mm)", color=TEXT_2, fontsize=9)
    a2.set_ylabel("tip height (mm)", color=TEXT_2, fontsize=9)
    a2.set_title("Design space (limits from tapered-beam theory)", color=TEXT, fontsize=10, loc="left")

    # mass history
    a3 = fig.add_axes((0.655, 0.09, 0.32, 0.21))
    style(a3)
    for i, hh in enumerate(hist[:upto + 1]):
        kk, _, cc = status(hh)
        a3.plot(i + 1, hh["objective"], "x" if kk == "rejected" else "o", color=cc, ms=4.5 if kk != "rejected" else 6,
                mew=2 if kk == "rejected" else 0.5, mec="white" if kk != "rejected" else cc)
    bests = [hist[b]["objective"] if b is not None else np.nan for b in best_upto[:upto + 1]]
    a3.step(np.arange(1, upto + 2), bests, where="post", color="#e9b10c", lw=2, zorder=0)
    a3.set_xlim(0, len(hist) + 1)
    a3.set_ylim(360, 840)
    a3.set_xlabel("candidate", color=TEXT_2, fontsize=9)
    a3.set_ylabel("mass (g)", color=TEXT_2, fontsize=9)
    a3.set_title("Mass of each candidate, and the best that passed (gold)", color=TEXT, fontsize=10, loc="left")


def make_animation(hist, scenes, case):
    bg = design_space(case)
    imgs = [mr.beauty(p) for p in scenes]
    best, best_upto = None, []
    for i, h in enumerate(hist):
        if h["feasible"] and h["verified"] and (best is None or h["objective"] < hist[best]["objective"]):
            best = i
        best_upto.append(best)
    fig = plt.figure(figsize=(14, 7.6), dpi=100)
    frames, durations = [], []
    from PIL import Image
    order = list(range(len(hist)))
    opt = next(i for i, h in enumerate(hist) if h["label"] == "c026")
    for k in order:
        frame(fig, k, hist, imgs, bg, best_upto)
        fig.canvas.draw()
        frames.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()))
        durations.append(1100 if k < 8 else 420)       # slow while the shape changes a lot, then quicker
    # finish on the optimum, held
    frame(fig, opt, hist, imgs, bg, best_upto, final=True, upto=len(hist) - 1)
    fig.canvas.draw()
    last = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3].copy())
    frames.append(last)
    durations.append(4500)
    plt.close(fig)
    out = OUT / "anim_bracket_opt.webp"
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=durations, loop=0, quality=82, method=6)
    last.save(OUT / "bracket_opt_final.png")
    return out


def make_compare(scenes_by_label):
    a, b = scenes_by_label["c000"], scenes_by_label["c026"]
    fig = plt.figure(figsize=(12, 8.2), facecolor=SURFACE)
    for i, (p, title, sub) in enumerate([
            (a, "Start: straight bar, 20 × 25 mm", "785 g · peak 96.0 MPa · tip 0.49 mm"),
            (b, "Optimum: linear taper, 26.0 → 8.7 mm", "546 g · peak 99.5 MPa · tip 0.92 mm")]):
        ax = fig.add_axes((0.0, 0.53 - i * 0.43, 0.86, 0.38))
        ax.imshow(mr.beauty(p))
        ax.set_axis_off()
        fig.text(0.03, 0.905 - i * 0.43, title, color=TEXT, fontsize=13, weight="bold")
        fig.text(0.03, 0.875 - i * 0.43, sub, color=TEXT_2, fontsize=10.5, family="monospace")
    mr.legend(fig, (0.89, 0.2, 0.018, 0.6), json.loads(a.with_suffix(".json").read_text(encoding="utf-8")))
    fig.text(0.03, 0.965, "Same load, same limits, 30 % less steel", color=TEXT, fontsize=15, weight="bold")
    fig.text(0.03, 0.025, "Rendered in Blender (Cycles) from the CalculiX results, one camera and one stress scale; "
             "colours checked against the legend. The clamp corners are singular and sit in the top band.",
             color=TEXT_2, fontsize=8.5)
    fig.savefig(OUT / "render_bracket_compare.png", dpi=130, facecolor=SURFACE)
    plt.close(fig)


def make_span_chart():
    from studies import tapered_bracket as st
    fig, ax = plt.subplots(figsize=(11, 5.2), facecolor=SURFACE)
    style(ax)
    for label, name, col in [("c000", "Start, straight 20 × 25 mm bar", "#7f8c9d"),
                             ("c011", "Candidate 12: passes a root-only check, fails mid-span", FAIL),
                             ("c026", "Optimum, 26.0 → 8.7 mm taper", ACCENT)]:
        s = read_series(RUN / "points" / label / "nodal_results.csv")
        p = params_of(label)
        xw, fib, _ = st.surface_ratio(s, p)
        xs, _, sig = st.stress_profile(s, p)
        ax.plot(xw, fib, ".", ms=2.2, color=col, alpha=0.35)
        ax.plot(xs, sig, "-", color=col, lw=2.2, label=name)
        i = int(np.argmax(sig))
        ax.plot(xs[i], sig[i], "o", color=col, ms=7, mec="white", mew=1)
        ax.annotate(f"{sig[i]:.1f} MPa at {xs[i]:.0f} mm", (xs[i], sig[i]), xytext=(8, 8),
                    textcoords="offset points", fontsize=8.5, color=col)
        if i > 0:                                   # the straight bar peaks at the root: one label is enough
            ax.annotate(f"root {sig[0]:.1f}", (0, sig[0]), xytext=(4, -14), textcoords="offset points",
                        fontsize=8, color=col)
    ax.axhline(100, color=FAIL, lw=1.2, ls=(0, (5, 3)))
    ax.text(196, 101.2, "100 MPa allowable", color=FAIL, fontsize=9, ha="right")
    ax.set_xlim(0, 200)
    ax.set_ylim(40, 115)
    ax.set_xlabel("distance from the clamp (mm)", color=TEXT_2)
    ax.set_ylabel("bending stress at the surface (MPa)", color=TEXT_2)
    ax.set_title("Where the stress peaks: at the root for a straight bar, in mid-span for a steep taper",
                 color=TEXT, fontsize=12, loc="left", weight="bold")
    ax.legend(frameon=False, fontsize=9, loc="lower left", labelcolor=TEXT)
    fig.text(0.01, 0.01, "Dots: CalculiX surface stress at the nodes. Lines: the design stress the study uses "
             "(the FE-to-beam-theory ratio fitted in the smooth part of the span, times M/Z).",
             color=TEXT_2, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "bracket_stress_span.png", dpi=140, facecolor=SURFACE)
    plt.close(fig)


def make_hero(blender, samples):
    """The optimum for the page's result viewer: same view and magnification as the cantilever tab."""
    from PIL import Image

    label = "c026"
    pt = RUN / "points" / label
    s = read_series(pt / "nodal_results.csv")
    nodes, elems = mesh_for(label, s)
    tris = mr.surface(nodes, elems, s["node_id"].astype(int))
    xyz = np.column_stack([s["x_mm"], s["y_mm"], s["z_mm"]])
    u = np.column_stack([s["ux_mm"], s["uy_mm"], s["uz_mm"]])
    vm = von_mises(s)
    xyz, tris, vm, u = compact(xyz, tris, vm, u)
    p = params_of(label)
    k = 25.0
    scene = write_scene(BUILD / "bracket_opt_hero", xyz + k * u, tris, vm, ghost_xyz=xyz,
                        field="von Mises stress", units="MPa", vmin=VMIN, vmax=VMAX, bands=NB,
                        band_colors=mr.bands(NB), elev=20, azim=-58,
                        expected_volume_mm3=tb.volume(p["length_mm"], p["width_mm"], p["root_height_mm"], p["tip_height_mm"]),
                        title="Optimised bracket", caption="")
    d = np.load(scene)
    vol = enclosed_volume(d["ghost_xyz"], d["tris"].astype(np.int64))
    meta = json.loads(scene.with_suffix(".json").read_text(encoding="utf-8"))
    err = vol / meta["expected_volume_mm3"] - 1
    assert abs(err) <= mr.VOLUME_TOL, err
    if blender is not None:
        mr.render(blender, scene, samples)
    chk = mr.check_colors(scene)
    assert chk["passed"], chk
    leg = mr.check_legibility(scene)
    assert leg["passed"], leg
    site = REPO / "site" / "v2"
    a = (np.clip(mr.beauty(scene), 0, 1) * 255).astype(np.uint8)
    im = Image.fromarray(a, "RGBA")
    al = np.asarray(im)[..., 3]
    ys, xs = np.nonzero(al > 60)
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
    scenes_path = site / "scenes.json"
    scenes = json.loads(scenes_path.read_text(encoding="utf-8"))
    scenes["bracket_opt"] = {kk: meta.get(kk) for kk in ("field", "units", "vmin", "vmax", "bands", "band_colors",
                                                          "title", "caption", "data_min", "data_max")}
    scenes["bracket_opt"]["volume"] = {"enclosed_mm3": round(vol, 1), "design_mm3": round(meta["expected_volume_mm3"], 1),
                                       "rel_error": float(f"{err:.2e}"), "passed": True}
    scenes["bracket_opt"]["color"] = chk
    scenes_path.write_text(json.dumps(scenes, indent=1), encoding="utf-8")
    print("hero:", chk["fraction_on_legend"], f"{err:.2e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--skip-render", action="store_true")
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()
    manifest, hist = history()
    labels = args.only or [h["label"] for h in hist]
    BUILD.mkdir(parents=True, exist_ok=True)
    blender = mr.find_blender()
    report = []
    scenes = {}
    for lab in labels:
        p = export(lab)
        if not args.skip_render:
            info = mr.render(blender, p, args.samples)
            print(lab, info["seconds"], "s", flush=True)
        report.append(gate(p))
        scenes[lab] = p
    (BUILD / "checks.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    worst = min(r["color_check"]["fraction_on_legend"] for r in report)
    vol = max(abs(r["volume_rel_error"]) for r in report)
    print(f"{len(report)} renders gated: worst colour fraction {worst:.4f}, worst volume error {vol:.2e}")
    if args.only:
        return
    case = {**read_json(RUN / "points/c000/point.json")["parameters"]}
    make_hero(None if args.skip_render else blender, 160)
    make_compare(scenes)
    make_span_chart()
    out = make_animation(hist, [scenes[h["label"]] for h in hist], case)
    print("written", out, out.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()

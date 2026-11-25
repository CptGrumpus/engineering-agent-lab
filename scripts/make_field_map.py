"""The motor's magnetic field for the site: |B| over the whole cross-section and one pole enlarged.

    .venv\\Scripts\\python.exe scripts\\make_field_map.py            the figure and the home page's picture
    .venv\\Scripts\\python.exe scripts\\make_field_map.py --hero     the home page's picture only

Also writes site/v2/hero_motor_field.webp: the whole section alone on a see-through background, for the home page.

Reads the FEMM solution exported by scripts/export_femm_field.py (build/render/motor_rev5_centre/field.npz and
field.json: one pole, 45 degrees, anti-periodic) and writes site/v2/fig_motor_field.webp. The export is revision 5, the
client-data model, open circuit, magnets at the run's temperature (25 C), the drawing's 0.775 mm gap: the last step of run RUN, point POINT. The
full section is the solved pole rotated by k x 45 degrees; |B| doesn't change with the anti-periodic sign flip.

Before drawing, it runs the gate itself rather than trusting a record: the export's circuit fluxes (Wb per metre of
depth, one pole), times -(8 poles x the 83.82 mm stack) (FEMM's sign is opposite), must equal the run's own
flux_linkage.csv last row in all three phases. It also checks the drawn field's peak is the export's.

The bands are the site's render bands (site/v2/scenes.json), 12 of 0.2 T from 0 to 2.4 T, so the saturated bridges
(about 2.3 T) get the top bands. The winding carries no current at open circuit; it's drawn flat, not banded.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import figkit as fk  # noqa: E402

SRC = REPO / "build" / "render" / "motor_rev5_centre"
RUN = REPO / "runs" / "20261123-215502_motor_prius_rev5_oc"
POINT = "p00_gap0775"
POLES, STACK_M = 8, 0.08382
OUT = REPO / "site" / "v2" / "fig_motor_field.webp"
HERO = REPO / "site" / "v2" / "hero_motor_field.webp"
# the export lives in build/, which git ignores, so a worktree has none: name another clone's with FIELD_SRC
import os  # noqa: E402

if os.environ.get("FIELD_SRC"):
    SRC = Path(os.environ["FIELD_SRC"])
VMAX, NB = 2.4, 12
COIL, AIRGAP, STATOR_AIR, ROTOR, VOID, MAG_A, MAG_B, STATOR = 11, 0, 15, 20, 26, 220, 221, 10


def main(hero_only: bool = False):
    meta = json.loads((SRC / "field.json").read_text(encoding="utf-8"))
    man = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
    t_mag = [p for p in man["points"] if p["label"] == POINT][0]["parameters"]["magnet_temperature_C"]
    rows = (RUN / "points" / POINT / "flux_linkage.csv").read_text(encoding="utf-8").strip().splitlines()
    assert rows[0].split(",") == ["time_s", "phi_a_Wb", "phi_b_Wb", "phi_c_Wb"], rows[0]
    run_phi = np.array([float(v) for v in rows[-1].split(",")[1:]])
    exp_phi = -POLES * STACK_M * np.array([meta["circuit_flux_Wb_per_m"][f"Circs{i}"] for i in range(3)])
    gap = np.abs(exp_phi - run_phi).max() / np.abs(run_phi).max()
    assert gap < 1e-6, f"the export is not the run's solution: phase fluxes {exp_phi} against {run_phi}"
    print(f"gate: phase fluxes match {RUN.name}/{POINT} to {gap:.1e}")
    d = np.load(SRC / "field.npz")
    xy, tri, b, grp = d["nodes_m"] * 1000, d["tri"], d["bmag_T"], d["group"]
    assert abs(b.max() - meta["bmag_max_T"]) < 1e-9 and b.max() < VMAX
    bands = json.loads((REPO / "site" / "v2" / "scenes.json").read_text(encoding="utf-8"))["cantilever"]["band_colors"]
    assert len(bands) == NB
    cols = np.array(bands)
    face = cols[np.clip((b / VMAX * NB).astype(int), 0, NB - 1)]
    coil = grp == COIL
    face[coil] = matplotlib.colors.to_rgb("#e9dccb")
    show = grp != STATOR_AIR                        # slot openings: air, left blank like the outside
    rot0 = np.radians(90 - 22.5)                    # the solved pole, centred at the top

    def polys(k):
        a = rot0 + k * np.pi / 4
        R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
        return (xy @ R.T)[tri[show]]

    # outlines of the magnets and the non-magnetic pockets: edges used by only one triangle of the group
    from matplotlib.collections import LineCollection

    def outline(sel):
        e = np.sort(np.concatenate([tri[sel][:, [0, 1]], tri[sel][:, [1, 2]], tri[sel][:, [2, 0]]]), axis=1)
        u, n = np.unique(e, axis=0, return_counts=True)
        return u[n == 1]
    edges = [outline(grp == gid) for gid in (MAG_A, MAG_B, VOID)]

    def draw_outlines(ax, k, lw):
        a = rot0 + k * np.pi / 4
        R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
        q = xy @ R.T
        for e in edges:
            ax.add_collection(LineCollection(q[e], colors=fk.INK, linewidths=lw, zorder=3))

    # the home page's picture: the whole section alone on a see-through background. The same elements, bands and
    # outlines as the figure's left panel, with no labels; drawn large and scaled down so its rim is smooth
    hf = plt.figure(figsize=(6, 6), dpi=440)
    hx = hf.add_axes([0, 0, 1, 1])
    hx.set_aspect("equal")
    hx.axis("off")
    for k in range(8):
        hx.add_collection(PolyCollection(polys(k), facecolors=face[show], edgecolors="face", linewidths=0.05, antialiased=False))
        draw_outlines(hx, k, 0.45)
    hx.set_xlim(-136, 136)
    hx.set_ylim(-136, 136)
    hf.savefig(HERO.with_suffix(".png"), dpi=440, transparent=True)
    plt.close(hf)
    from PIL import Image
    Image.open(HERO.with_suffix(".png")).convert("RGBA").resize((1200, 1200), Image.LANCZOS).save(HERO, "WEBP", quality=92, method=6)
    HERO.with_suffix(".png").unlink()
    print("hero", HERO.name, f"{HERO.stat().st_size // 1024} KB")
    if hero_only:
        return

    fig = plt.figure(figsize=(fk.FULL, 4.9), dpi=220)
    fk.heading(fig, "The magnets' field at open circuit: the thin bridges above the magnets saturate, near 2.3 T",
               f"The client-data model, magnets at {t_mag:g} °C, FEMM 2D magnetostatics, one pole solved and repeated; flux density |B| in tesla")
    axL = fig.add_axes([0.0, 0.08, 0.47, 0.80])
    axR = fig.add_axes([0.45, 0.08, 0.47, 0.80])
    for ax in (axL, axR):
        ax.set_aspect("equal")
        ax.axis("off")
    for k in range(8):
        axL.add_collection(PolyCollection(polys(k), facecolors=face[show], edgecolors="face", linewidths=0.05, antialiased=False))
    axL.set_xlim(-136, 136)
    axL.set_ylim(-136, 136)
    axR.add_collection(PolyCollection(polys(0), facecolors=face[show], edgecolors="face", linewidths=0.05, antialiased=False))
    axR.set_xlim(-38, 38)
    axR.set_ylim(54, 112)
    for k in range(8):
        draw_outlines(axL, k, 0.3)
    draw_outlines(axR, 0, 0.8)
    # where the enlarged view is
    axL.plot([-38, 38, 38, -38, -38], [54, 54, 112, 112, 54], color=fk.INK, lw=0.8)

    def lab(ax, xy_, txt, xytext, ha="left"):
        ax.annotate(txt, xy_, xytext=xytext, textcoords="data", ha=ha, va="center", fontsize=8.5, color=fk.INK,
                    arrowprops=dict(arrowstyle="-", color=fk.INK, lw=0.7, shrinkA=2, shrinkB=1),
                    bbox=dict(fc=fk.SURFACE, ec="none", pad=1.2))

    # labels at the elements that carry each feature, found from the data rather than placed by eye
    P = polys(0)
    cen = P.mean(axis=1)
    g = grp[show]
    bs = b[show]
    left = cen[:, 0] < 0
    hot = cen[left][np.argmax(bs[left])]
    lab(axR, hot, f"bridge, {bs[left].max():.1f} T", (hot[0] - 6, hot[1] + 14), ha="right")
    mag_l, mag_r = (MAG_A, MAG_B) if cen[g == MAG_A][:, 0].mean() < 0 else (MAG_B, MAG_A)
    m = cen[g == mag_l].mean(axis=0)
    lab(axR, m, "magnet", (m[0] - 10, m[1] - 14), ha="right")
    # the flux barrier: the non-magnetic end of the right-hand pocket, past the magnet's outer end
    v = cen[(g == VOID) & (cen[:, 0] > 0)]
    vv = v[np.hypot(*(v - v[np.argmax(v[:, 0])]).T) < 2.5].mean(axis=0)
    lab(axR, vv, "flux barrier", (vv[0] - 3, vv[1] - 18), ha="center")
    fig.text(0.02, 0.035, "Beige: the winding, which carries no current here. Black outlines: the magnets and the "
             "flux barriers at their pockets' ends.", fontsize=8, color=fk.INK2)
    # the key: the 12 bands, 0 to 2.4 T
    kx = fig.add_axes([0.935, 0.16, 0.018, 0.62])
    kx.imshow(cols[:, None, :], origin="lower", aspect="auto", extent=(0, 1, 0, VMAX))
    kx.set_xticks([])
    kx.yaxis.tick_right()
    kx.set_yticks(np.arange(0, VMAX + 1e-9, 0.4))
    kx.tick_params(length=0, labelsize=8, colors=fk.INK2)
    for s in kx.spines.values():
        s.set_visible(False)
    kx.set_title("T", fontsize=8.5, color=fk.INK2, pad=4)
    fig.savefig(OUT.with_suffix(".png"), dpi=220, facecolor=fk.SURFACE)
    plt.close(fig)
    Image.open(OUT.with_suffix(".png")).convert("RGB").save(OUT, "WEBP", quality=90, method=6)
    OUT.with_suffix(".png").unlink()
    print("field map", OUT.name, f"{OUT.stat().st_size // 1024} KB, peak {b.max():.2f} T")


if __name__ == "__main__":
    main(hero_only="--hero" in sys.argv)

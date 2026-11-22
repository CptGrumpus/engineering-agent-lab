"""Result-viewer renders for studies 13 to 16 (strap proof test, cold-plate chain, bolted joint).

    .venv\\Scripts\\python.exe scripts\\make_study_renders.py [--only strap_proof ...] [--samples N] [--skip-render]

The harness keeps solver decks but not CalculiX's full-field .frd files. Where a render needs the full
field, the recorded deck of the evidence run is solved again (output requests are the only thing ever
added) and the re-solve has to reproduce the evidence: the solver's printed results must be identical to
the saved ones, and the headline metric read from the new field must equal the run's recorded value.
Every render then passes the same three gates as the other portfolio renders (make_renders.py): the
surface encloses the part's volume, every part pixel of the unlit pass is a legend colour, and the lit
pass reads as the right band. Outputs go to site/v2 (vp_<id>.webp, th_<id>.webp, scenes.json) and to
build/render/<id>.npz for the page's 3D view.
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

from harness.femesh import enclosed_volume, extrude_planar, write_scene  # noqa: E402
from harness.runio import read_json  # noqa: E402

BUILD = REPO / "build/render"
SITE = REPO / "site/v2"


def ccx():
    from studies.fin import find_ccx
    return find_ccx()


def resolve(src: Path, deck: str, extra: tuple[str, ...], work: Path, printed: str, add_output: str = "") -> Path:
    """Solve a saved deck again in `work` and check that its printed output file matches the saved one.
    `add_output` (field-output request lines) is inserted before the deck's last *END STEP; it changes
    what is written to the .frd, not the solution."""
    work.mkdir(parents=True, exist_ok=True)
    for n in (f"{deck}.inp", *extra):
        shutil.copyfile(src / n, work / n)
    if add_output:
        text = (work / f"{deck}.inp").read_text(encoding="latin-1")
        i = text.upper().rindex("*END STEP")
        (work / f"{deck}.inp").write_text(text[:i] + add_output.strip() + "\n" + text[i:], encoding="latin-1")
    if not (work / f"{deck}.frd").exists():
        subprocess.run([str(ccx()), "-i", deck], cwd=work, capture_output=True, text=True, timeout=7200, check=True)
    if (work / printed).read_text() != (src / printed).read_text():
        raise RuntimeError(f"{work.name}: the re-solve's {printed} differs from the evidence run's")
    return work


def mirror(xy, tris, fields, axis):
    """Mirror a planar triangulation about x = 0 (axis 0) or y = 0 (axis 1); nodes on the plane are shared."""
    off = np.abs(xy[:, axis]) > 1e-9
    idx = np.nonzero(off)[0]
    remap = np.arange(len(xy))
    remap[idx] = len(xy) + np.arange(len(idx))
    flip = np.ones(2)
    flip[axis] = -1
    return (np.vstack([xy, xy[idx] * flip]), np.vstack([tris, remap[tris][:, ::-1]]),
            [np.concatenate([f, f[idx]]) for f in fields])


def read_tri6(mesh_inp: Path):
    """Nodes and 6-node triangles of a Gmsh-written plane mesh; each triangle split into four linear ones
    through its mid-side nodes, so the field is drawn at the resolution the solver computed it."""
    nodes, tris, mode = {}, [], None
    for line in mesh_inp.read_text().splitlines():
        if line.startswith("*"):
            mode = "node" if line.upper().startswith("*NODE") else ("tri" if "CPS6" in line.upper() else None)
            continue
        if mode == "node":
            v = line.split(",")
            nodes[int(v[0])] = (float(v[1]), float(v[2]))
        elif mode == "tri":
            v = [int(a) for a in line.split(",")[1:7]]
            a, b, c, ab, bc, ca = v
            tris += [(a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)]
    return nodes, np.array(tris)


# --------------------------------------------------------------------------- study 14: strap proof test

STRAP = REPO / "runs/20261120-233830_strap_proof_r1/points/p02_hole_element_ratio-0.00625"


def scene_strap_proof():
    from harness.calculix import read_frd

    work = resolve(STRAP / "solver", "plastic", ("mesh.inp",), BUILD / "strap_proof_solve", "plastic.dat")
    rec = read_json(STRAP / "point.json")
    nodes, tris = read_tri6(work / "mesh.inp")
    frd = read_frd(work / "plastic.frd")
    stress = [b for n, b in frd["blocks"] if n == "STRESS"]
    S, R = stress[0], stress[-1]                             # at the 15 kN proof load, and after unloading
    si = {int(n): k for k, n in enumerate(S["ids"])}
    used = np.unique(tris)
    loc = {int(n): k for k, n in enumerate(used)}
    xy = np.array([nodes[int(n)] for n in used])
    sxx = np.array([S["SXX"][si[int(n)]] for n in used])
    res = np.array([R["SXX"][si[int(n)]] for n in used])
    root = loc[int(rec["solver_outputs"]["root_node"])]
    for got, want in ((sxx[root], rec["metrics"]["notch_stress_MPa"]), (res[root], rec["metrics"]["residual_stress_MPa"])):
        if abs(got / want - 1) > 1e-4:
            raise RuntimeError(f"hole-edge stress {got} from the re-solve != recorded {want}")
    zone = rec["metrics"]["plastic_zone_mm"]
    t = np.vectorize(loc.get)(tris)
    xy, t, (sxx,) = mirror(xy, t, [sxx], 0)
    xy, t, (sxx,) = mirror(xy, t, [sxx], 1)
    p = rec["parameters"]
    xyz, faces, val = extrude_planar(xy, t, sxx, thickness=p["thickness_mm"])
    # 25 MPa bands with an edge at 225 MPa, within 0.6 % of the 223.8 MPa initial yield: the top three
    # bands are the material that yielded. The 93.75 MPa nominal stress sits mid-band.
    return write_scene(BUILD / "strap_proof", xyz, faces, val, field="axial stress σxx at the proof load", units="MPa",
                       vmin=0.0, vmax=300.0, bands=12, band_colors=mr.bands(12), elev=40, azim=-66,
                       sharp_angle_deg=60, distance_factor=2.8, frame_box=[[-28, -21, -3], [28, 21, 3]], fill=0.95,
                       resolution=[1400, 900],
                       expected_volume_mm3=p["length_mm"] * p["width_mm"] * p["thickness_mm"]
                       - np.pi * (p["hole_diameter_mm"] / 2) ** 2 * p["thickness_mm"],
                       title="Strap at its 15 kN proof load: where it yields",
                       caption=f"The hole edge yields to {zone:.1f} mm deep and reaches {sxx[root]:.0f} MPa; after "
                               f"unloading it is left at {res[root]:.0f} MPa. Quarter model mirrored to the full strap.")


# --------------------------------------------------------------------------- study 16: bolted joint

JOINT = REPO / "runs/20261121-110554_bolted_joint_mesh_r1/points/p02_element_size_mm-0.5"
OFFSET = 1_000_000                  # bottom plate node and element numbers


def scene_bolted_joint():
    """The bottom plate after clamping, with the contact pressure the top plate puts on its face.

    A first version drew the pressure as a height field so the volume would equal the clamp force; the
    volume check refused it at +2.63 %: the solver's nodal contact pressures, extrapolated from its
    integration points, integrate to 7 697 N on the half model against the 7 500 N actually carried
    (the trap study 10 caught with element stresses). So the field is drawn on the plate itself and the
    volume check is the plate's geometry."""
    import re

    from harness.calculix import read_frd
    from harness.femesh import compact, read_inp

    work = resolve(JOINT / "solver", "job", (), BUILD / "bolted_joint_solve", "job.dat")
    rec = read_json(JOINT / "point.json")
    p = rec["parameters"]
    frd = read_frd(work / "job.frd")
    C = next(b for n, b in frd["blocks"] if n == "CONTACT")    # end of step 1: clamped, before any side load
    coords = dict(zip(frd["nodes"].tolist(), frd["coords"]))
    cid = np.array([int(n) for n in C["ids"]])
    cp = np.asarray(C["CPRESS"], dtype=float)
    slave = np.array([abs(coords[n][2]) < 1e-9 and n < OFFSET for n in cid])
    if cp[~slave].max() > 0:
        raise RuntimeError("contact pressure on nodes off the interface")
    # the bottom plate's face nodes sit at the same (x, y) as the top plate's: match on the result file's
    # own coordinates (6 significant figures), rounded well inside the 0.5 mm element size
    key = lambda q: (round(float(q[0]), 3), round(float(q[1]), 3))
    face = {key(coords[n]): v for n, v in zip(cid[slave], cp[slave])}
    view = work / "view.inp"
    view.write_text(re.sub(r"TYPE=C3D8I", "TYPE=C3D8", (work / "job.inp").read_text(encoding="latin-1")),
                    encoding="latin-1")
    nodes, elems = read_inp(view)
    elems = [e for e in elems if min(e[1]) >= OFFSET]                       # the bottom plate
    ids = np.array(sorted({n for e in elems for n in e[1]}))
    xyz = np.array([nodes[int(n)] for n in ids])
    on_face = np.abs(xyz[:, 2]) < 1e-9
    val = np.array([face[key(coords[int(n)])] if f else 0.0 for n, f in zip(ids, on_face)])
    if on_face.sum() != slave.sum():
        raise RuntimeError(f"{on_face.sum()} bottom face nodes against {slave.sum()} interface nodes")
    tris = mr.surface({int(n): nodes[int(n)] for n in ids}, elems, ids)
    xyz, tris, val = compact(xyz, tris, val)
    tris = tris[~np.all(np.abs(xyz[tris][:, :, 1]) < 1e-9, axis=1)]     # the cut face would end up inside
    # mirror the half model (y >= 0) about the symmetry plane y = 0
    off = np.abs(xyz[:, 1]) > 1e-9
    idx = np.nonzero(off)[0]
    remap = np.arange(len(xyz))
    remap[idx] = len(xyz) + np.arange(len(idx))
    xyz = np.vstack([xyz, xyz[idx] * [1, -1, 1]])
    tris = np.vstack([tris, remap[tris][:, ::-1]])
    val = np.concatenate([val, val[idx]])
    R, rh = p["plate_outer_diameter_mm"] / 2, p["hole_diameter_mm"] / 2
    return write_scene(BUILD / "bolted_joint", xyz, tris, val, field="contact pressure", units="MPa",
                       vmin=0.0, vmax=180.0, bands=12, band_colors=mr.bands(12), elev=38, azim=-58,
                       sharp_angle_deg=50, distance_factor=3.0, resolution=[1400, 900],
                       expected_volume_mm3=np.pi * (R ** 2 - rh ** 2) * p["bottom_thickness_mm"],
                       title="Bolted joint: where the plates press together after clamping",
                       caption=f"Pressure on the bottom plate's face, highest at the hole ({cp[slave].max():.0f} MPa) and "
                               f"gone by {rec['metrics']['contact_diameter_mm']:.1f} mm across; half model mirrored.")


# --------------------------------------------------------------------------- study 15: cold-plate chain

PLATE = REPO / "runs/20261121-094235_cold_plate_mesh_r1/points/p02_cells_across_gap-80"
SLICE_MM = 30.0                     # the plate is a plane-strain section: drawn as a 30 mm wide slice


def scene_cold_plate():
    from harness.runio import read_series

    rec = read_json(PLATE / "point.json")
    s = read_series(PLATE / "plate_nodes.csv")
    x, y, T = s["x_mm"], s["y_mm"], s["T_C"]
    xs, ys = np.unique(x.round(6)), np.unique(y.round(6))
    if len(xs) * len(ys) != len(x):
        raise RuntimeError("plate nodes are not a full structured grid")
    if abs(T.max() / rec["metrics"]["component_face_max_temperature_C"] - 1) > 1e-6:
        raise RuntimeError(f"plate peak {T.max()} != recorded component face peak")
    i, j = np.searchsorted(xs, x.round(6)), np.searchsorted(ys, y.round(6))
    grid = np.empty((len(xs), len(ys)), dtype=np.int64)
    grid[i, j] = np.arange(len(x))
    a, b, c, d = grid[:-1, :-1].ravel(), grid[1:, :-1].ravel(), grid[1:, 1:].ravel(), grid[:-1, 1:].ravel()
    tris = np.vstack([np.column_stack([a, b, c]), np.column_stack([a, c, d])])
    # extrude the x-y section along the width; in the scene the plate's thickness direction is up
    xyz2, faces, val = extrude_planar(np.column_stack([x, y]), tris, T, thickness=SLICE_MM)
    xyz = np.column_stack([xyz2[:, 0] - 25.0, -xyz2[:, 2], xyz2[:, 1] - 2.5])   # a rotation, not a mirror
    t = rec["parameters"]["plate_thickness_mm"]
    return write_scene(BUILD / "cold_plate", xyz, faces, val, field="temperature", units="°C",
                       vmin=30.5, vmax=41.5, bands=11, band_colors=mr.bands(11), elev=30, azim=-62,
                       sharp_angle_deg=60, distance_factor=3.0, resolution=[1400, 900],
                       expected_volume_mm3=(xs[-1] - xs[0]) * t * SLICE_MM,
                       title="Cold plate: temperature with the coolant and the plate's conduction coupled",
                       caption=f"Component face peaks at {T.max():.2f} °C against 45 °C; the coolant runs left to right "
                               "under the plate. A 30 mm slice of the plane-strain section.")


# --------------------------------------------------------------------------- study 13: strut buckling

STRUT = REPO / "runs/20261120-232856_strut_length/points/p01_length_mm-500"
STRUT_SCALE = 5.0


def scene_strut():
    """The bowed 500 mm strut in the last load increment before first yield (time 0.95 of the ramp to
    0.98 P_cr), von Mises stress with the top band starting at yield."""
    import re

    from harness.calculix import read_frd
    from harness.femesh import compact, read_inp

    work = resolve(STRUT / "solver", "nonlinear", (), BUILD / "strut_solve", "nonlinear.dat",
                   add_output="*NODE FILE, FREQUENCY=1\nU\n*EL FILE, FREQUENCY=1\nS")
    rec = read_json(STRUT / "point.json")
    p = rec["parameters"]
    frd = read_frd(work / "nonlinear.frd")
    disp = [b for n, b in frd["blocks"] if n == "DISP"]
    stress = [b for n, b in frd["blocks"] if n == "STRESS"]
    k = 18                                                     # increment 19 of 20: time 0.95
    # the .dat prints the mid-span nodes at every increment: the chosen .frd block must match it
    dat = (work / "nonlinear.dat").read_text()
    blocks = re.split(r"displacements \(vx,vy,vz\) for set NMID and time\s+", dat)[1:]
    time, rows = blocks[k].split("\n", 1)
    if abs(float(time) - 0.95) > 1e-9:
        raise RuntimeError(f"increment {k + 1} is at time {time}")
    nid, *u_dat = rows.split("\n")[1].split()
    D = disp[k]
    j = int(np.nonzero(D["ids"] == int(nid))[0][0])
    u_frd = [D["D1"][j], D["D2"][j], D["D3"][j]]
    if np.abs(np.array(u_frd) - np.array([float(v) for v in u_dat])).max() > 1e-6 * max(1.0, abs(float(u_dat[2]))):
        raise RuntimeError(f"frd displacement {u_frd} != dat {u_dat} at node {nid}")
    load = float(time) * rec["solver_outputs"]["p_max_N"]
    view = work / "view.inp"
    view.write_text(re.sub(r"TYPE=C3D8I", "TYPE=C3D8", (work / "nonlinear.inp").read_text(encoding="latin-1")),
                    encoding="latin-1")
    nodes, elems = read_inp(view)
    ids = np.array(sorted(nodes))
    S = stress[k]
    si = {int(n): i for i, n in enumerate(S["ids"])}
    di = {int(n): i for i, n in enumerate(D["ids"])}
    s = {c: np.array([S[c][si[int(n)]] for n in ids]) for c in ("SXX", "SYY", "SZZ", "SXY", "SYZ", "SZX")}
    vm = np.sqrt(0.5 * ((s["SXX"] - s["SYY"]) ** 2 + (s["SYY"] - s["SZZ"]) ** 2 + (s["SZZ"] - s["SXX"]) ** 2)
                 + 3 * (s["SXY"] ** 2 + s["SYZ"] ** 2 + s["SZX"] ** 2))
    u = np.array([[D[c][di[int(n)]] for c in ("D1", "D2", "D3")] for n in ids])
    xyz = np.array([nodes[int(n)] for n in ids])
    tris = mr.surface(nodes, elems, ids)
    xyz, tris, vm, u = compact(xyz, tris, vm, u)
    mid = np.abs(xyz[:, 0] - p["length_mm"] / 2) < 0.6 * p["element_size_mm"]
    centre = xyz.mean(axis=0)
    return write_scene(BUILD / "strut", xyz - centre + STRUT_SCALE * u, tris, vm, ghost_xyz=xyz - centre,
                       field="von Mises stress", units="MPa", vmin=0.0, vmax=300.0, bands=12, band_colors=mr.bands(12),
                       elev=22, azim=-74, sharp_angle_deg=60, distance_factor=3.4, resolution=[1400, 900],
                       expected_volume_mm3=p["length_mm"] * p["width_mm"] * p["thickness_mm"],
                       title=f"Strut at {load / 1000:.2f} kN, just under first yield",
                       caption=f"Bow drawn {STRUT_SCALE:.0f}x; peak at mid-span {vm[mid].max():.0f} MPa against the "
                               f"{p['yield_strength_MPa']:.0f} MPa yield (top band from 275).")


SCENES = {"strap_proof": scene_strap_proof, "bolted_joint": scene_bolted_joint, "cold_plate": scene_cold_plate,
          "strut": scene_strut}


# --------------------------------------------------------------------------- gates and page assets

def gate(scene: Path) -> dict:
    meta = json.loads(scene.with_suffix(".json").read_text(encoding="utf-8"))
    d = np.load(scene)
    vol = enclosed_volume(d["ghost_xyz"] if "ghost_xyz" in d else d["xyz"], d["tris"].astype(np.int64))
    err = vol / meta["expected_volume_mm3"] - 1
    if abs(err) > mr.VOLUME_TOL:
        raise RuntimeError(f"{scene.stem}: enclosed volume {err:+.2%} off the design volume")
    chk = mr.check_colors(scene)
    if not chk["passed"]:
        raise RuntimeError(f"{scene.stem}: colour check failed {chk}")
    leg = mr.check_legibility(scene)
    if not leg["passed"]:
        raise RuntimeError(f"{scene.stem}: the lit render misreads {leg['misread']:.2%} of the part {leg}")
    return {"volume": {"enclosed_mm3": round(float(vol), 1), "design_mm3": round(meta["expected_volume_mm3"], 1),
                       "rel_error": float(f"{err:.2e}"), "passed": True},
            "color": chk, "legibility": leg}


def publish(name: str, scene: Path, g: dict):
    from PIL import Image

    a = (np.clip(mr.beauty(scene), 0, 1) * 255).astype(np.uint8)
    im = Image.fromarray(a, "RGBA")
    ys, xs = np.nonzero(np.asarray(im)[..., 3] > 60)
    pad = int(0.10 * max(np.ptp(xs), np.ptp(ys)))
    im = im.crop((max(0, xs.min() - pad), max(0, ys.min() - pad), min(im.width, xs.max() + pad), min(im.height, ys.max() + pad)))
    vp = im.copy()
    vp.thumbnail((1400, 900), Image.LANCZOS)
    vp.save(SITE / f"vp_{name}.webp", quality=90, method=6)
    th = im.copy()
    th.thumbnail((800, 500), Image.LANCZOS)
    canvas = Image.new("RGBA", (800, 500), (0, 0, 0, 0))
    canvas.alpha_composite(th, ((800 - th.width) // 2, (500 - th.height) // 2))
    canvas.save(SITE / f"th_{name}.webp", quality=88, method=6)
    meta = json.loads(scene.with_suffix(".json").read_text(encoding="utf-8"))
    path = SITE / "scenes.json"
    scenes = json.loads(path.read_text(encoding="utf-8"))
    scenes[name] = {k: meta.get(k) for k in ("field", "units", "vmin", "vmax", "bands", "band_colors", "title",
                                              "caption", "data_min", "data_max")}
    scenes[name].update(g)
    path.write_text(json.dumps(scenes, indent=1), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--skip-render", action="store_true")
    args = ap.parse_args()
    blender = mr.find_blender()
    for name in args.only or SCENES:
        scene = SCENES[name]()
        meta = json.loads(scene.with_suffix(".json").read_text(encoding="utf-8"))
        print(name, f"data {meta['data_min']:.2f} to {meta['data_max']:.2f} {meta['units']}", flush=True)
        if not args.skip_render:
            print(name, mr.render(blender, scene, args.samples)["seconds"], "s", flush=True)
        g = gate(scene)
        publish(name, scene, g)
        print(name, f"volume {g['volume']['rel_error']:+.1e}, {g['color']['fraction_on_legend']:.2%} on the legend, "
              f"{g['legibility']['misread']:.2%} misread", flush=True)


if __name__ == "__main__":
    main()

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


def resolve(src: Path, deck: str, extra: tuple[str, ...], work: Path, printed: str, add_output: str = "",
            every_increment: bool = False, first_step: bool = False) -> Path:
    """Solve a saved deck again in `work` and check that its printed output file matches the saved one.
    `add_output` (field-output request lines) is inserted before the deck's last *END STEP (the first,
    with first_step); it changes what is written to the .frd, not the solution."""
    work.mkdir(parents=True, exist_ok=True)
    for n in (f"{deck}.inp", *extra):
        shutil.copyfile(src / n, work / n)
    if add_output:
        text = (work / f"{deck}.inp").read_text(encoding="latin-1")
        i = text.upper().index("*END STEP") if first_step else text.upper().rindex("*END STEP")
        (work / f"{deck}.inp").write_text(text[:i] + add_output.strip() + "\n" + text[i:], encoding="latin-1")
    if every_increment:
        # output at every increment. CalculiX shares one frequency between a step's field (.frd) and
        # printed (.dat) requests, the last card winning, so both are set to 1; the new .dat then holds
        # the evidence run's end-of-step prints plus the increments between them
        import re as _re
        text = (work / f"{deck}.inp").read_text(encoding="latin-1")
        text = _re.sub(r"(\*(?:NODE|EL) (?:FILE|PRINT)[^\n]*FREQUENCY=)\d+", r"\g<1>1", text, flags=_re.I)
        (work / f"{deck}.inp").write_text(text, encoding="latin-1")
    if not (work / f"{deck}.frd").exists():
        subprocess.run([str(ccx()), "-i", deck], cwd=work, capture_output=True, text=True, timeout=7200, check=True)
    new, old = (work / printed).read_text(), (src / printed).read_text()
    if every_increment:
        # every line the evidence run printed must appear in the re-solve's output, in the same order: text
        # lines exactly, numbers to round-off. Printing at every increment changes the solver's summation
        # order, so components that are pure noise (1e-8 N beside a 300 N reaction) move in their last
        # digits; the allowance is 1e-9 of the largest printed value.
        def nums(s):
            try:
                return [float(x) for x in s.split()]
            except ValueError:
                return None
        scale = max((abs(v) for ln in old.splitlines() for v in (nums(ln) or [])), default=1.0)
        same = lambda a, b: a == b or (nums(a) is not None and nums(b) is not None and len(nums(a)) == len(nums(b))
                                       and max(abs(x - y) for x, y in zip(nums(a), nums(b))) <= 1e-9 * scale)
        lines, k = new.splitlines(), 0
        for line in old.splitlines():
            if not line.strip():
                continue
            while k < len(lines) and not same(lines[k], line):
                k += 1
            if k == len(lines):
                raise RuntimeError(f"{work.name}: the evidence run's printed line {line!r} is not in the re-solve")
            k += 1
    elif new != old:
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
# 25 MPa bands from -100 to 300 MPa, one scale for the proof load and for the stress left after unloading;
# a band edge at 225 MPa, within 0.6 % of the 223.8 MPa initial yield, so the top three bands are the
# material that yielded; the 93.75 MPa nominal stress sits mid-band
STRAP_SCALE = dict(vmin=-100.0, vmax=300.0, bands=16, band_colors=mr.bands(16))


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
    return write_scene(BUILD / "strap_proof", xyz, faces, val, field="axial stress σxx at the proof load", units="MPa",
                       **STRAP_SCALE, elev=40, azim=-66,
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


def scene_joint_section():
    """Section through the bolt axis after clamping: the axial stress in both plates on the half model's
    symmetry plane, which is where the pressure cone shows. The clamp step is solved again with a stress
    output request added (frequency 1000, the same as the step's other requests, so it writes at the end
    of the step only); the printed output must match the evidence run's exactly."""
    import re

    from harness.calculix import read_frd
    from harness.femesh import compact, read_inp

    work = resolve(JOINT / "solver", "job", (), BUILD / "bolted_joint_section_solve", "job.dat",
                   add_output="*EL FILE, FREQUENCY=1000\nS", first_step=True)
    rec = read_json(JOINT / "point.json")
    p = rec["parameters"]
    frd = read_frd(work / "job.frd")
    S = next(b for n, b in frd["blocks"] if n == "STRESS")          # end of step 1: clamped
    view = work / "view.inp"
    view.write_text(re.sub(r"TYPE=C3D8I", "TYPE=C3D8", (work / "job.inp").read_text(encoding="latin-1")),
                    encoding="latin-1")
    nodes, elems = read_inp(view)
    ids = np.array(sorted({n for e in elems for n in e[1]}))
    si = {int(n): i for i, n in enumerate(S["ids"])}
    szz = np.array([S["SZZ"][si[int(n)]] for n in ids])
    xyz = np.array([nodes[int(n)] for n in ids])
    # the washer pressure the clamp is applied as: the stress under the washer must match it
    washer = 15000 / 2 / (np.pi * ((p["washer_diameter_mm"] / 2) ** 2 - (p["hole_diameter_mm"] / 2) ** 2) / 2)
    top = np.abs(xyz[:, 2] - p["top_thickness_mm"]) < 1e-9
    r = np.hypot(xyz[:, 0], xyz[:, 1])
    under = top & (r > p["hole_diameter_mm"] / 2 + 0.6) & (r < p["washer_diameter_mm"] / 2 - 0.6)
    mean_under = float(-szz[under].mean())
    if abs(mean_under / washer - 1) > 0.10:
        raise RuntimeError(f"stress under the washer {mean_under:.1f} MPa against the applied {washer:.1f} MPa")
    tris = mr.surface({int(n): nodes[int(n)] for n in ids}, elems, ids)
    xyz, tris, szz = compact(xyz, tris, szz)
    R, rh = p["plate_outer_diameter_mm"] / 2, p["hole_diameter_mm"] / 2
    # compression drawn as a positive number; 30 MPa bands with zero in the middle of the lowest, so
    # round-off around an unloaded region can't flicker across a band edge
    return write_scene(BUILD / "bolted_joint_section", xyz, tris, -szz, field="compressive axial stress", units="MPa",
                       vmin=-15.0, vmax=255.0, bands=9, band_colors=mr.bands(9), elev=16, azim=-90,
                       sharp_angle_deg=50, distance_factor=3.0, resolution=[1400, 800],
                       expected_volume_mm3=np.pi * (R ** 2 - rh ** 2) / 2 * (p["top_thickness_mm"] + p["bottom_thickness_mm"]),
                       title="Bolted joint: section through the bolt axis after clamping",
                       caption=f"Axial stress in both plates; the compression spreads from the washers in a cone. "
                               f"Under the washer {mean_under:.0f} MPa against the {washer:.0f} MPa applied.")


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


def scene_cold_plate(thin: int = 1, name: str = "cold_plate"):
    """thin > 1 keeps every thin-th node row through the thickness (and both faces): the lighter mesh
    for the page's 3D view. Temperature changes by about 0.5 K through the 3 mm, so the colour bands,
    which change along the flow, keep their full resolution."""
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
    if thin > 1:
        rows = sorted(set(range(0, len(ys), thin)) | {len(ys) - 1})
        keep = grid[:, rows]
        x, y, T = x[keep.ravel()], y[keep.ravel()], T[keep.ravel()]
        grid = np.arange(keep.size).reshape(keep.shape)
    a, b, c, d = grid[:-1, :-1].ravel(), grid[1:, :-1].ravel(), grid[1:, 1:].ravel(), grid[:-1, 1:].ravel()
    tris = np.vstack([np.column_stack([a, b, c]), np.column_stack([a, c, d])])
    # extrude the x-y section along the width; in the scene the plate's thickness direction is up
    xyz2, faces, val = extrude_planar(np.column_stack([x, y]), tris, T, thickness=SLICE_MM)
    xyz = np.column_stack([xyz2[:, 0] - 25.0, -xyz2[:, 2], xyz2[:, 1] - 2.5])   # a rotation, not a mirror
    t = rec["parameters"]["plate_thickness_mm"]
    return write_scene(BUILD / name, xyz, faces, val, field="temperature", units="°C",
                       vmin=30.5, vmax=41.5, bands=11, band_colors=mr.bands(11), elev=30, azim=-62,
                       sharp_angle_deg=60, distance_factor=3.0, resolution=[1400, 900],
                       expected_volume_mm3=(xs[-1] - xs[0]) * t * SLICE_MM,
                       title="Cold plate: temperature with the coolant and the plate's conduction coupled",
                       caption=f"Component face peaks at {T.max():.2f} °C against 45 °C; the coolant runs left to right "
                               "under the plate. A 30 mm slice of the plane-strain section.")


# --------------------------------------------------------------------------- study 13: strut buckling

STRUT = REPO / "runs/20261120-232856_strut_length/points/p01_length_mm-500"
STRUT_SCALE = 5.0


def strut_data() -> dict:
    """Every load increment of the 500 mm strut's nonlinear run, from the re-solve. Each increment's
    displacement in the .frd must match the mid-span node the solver printed to the .dat at that time."""
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
    blocks = re.split(r"displacements \(vx,vy,vz\) for set NMID and time\s+", (work / "nonlinear.dat").read_text())[1:]
    if not (len(blocks) == len(disp) == len(stress)):
        raise RuntimeError(f"{len(blocks)} printed increments, {len(disp)} displacement and {len(stress)} stress blocks")
    times = []
    for D, blk in zip(disp, blocks):
        time, rows = blk.split("\n", 1)
        nid, *u_dat = rows.split("\n")[1].split()
        j = int(np.nonzero(D["ids"] == int(nid))[0][0])
        u_frd = np.array([D["D1"][j], D["D2"][j], D["D3"][j]])
        # the .frd writes 6 significant figures (half a unit in the last place is 5e-6 relative) and the
        # .dat 7, so they can only agree to the .frd's precision
        if np.abs(u_frd - np.array([float(v) for v in u_dat])).max() > 1e-5 * np.abs(u_frd).max():
            raise RuntimeError(f"time {time}: frd displacement {u_frd} != dat {u_dat} at node {nid}")
        times.append(float(time))
    view = work / "view.inp"
    view.write_text(re.sub(r"TYPE=C3D8I", "TYPE=C3D8", (work / "nonlinear.inp").read_text(encoding="latin-1")),
                    encoding="latin-1")
    nodes, elems = read_inp(view)
    ids = np.array(sorted(nodes))
    xyz = np.array([nodes[int(n)] for n in ids])
    tris = mr.surface(nodes, elems, ids)
    vms, us = [], []
    for S, D in zip(stress, disp):
        si = {int(n): i for i, n in enumerate(S["ids"])}
        di = {int(n): i for i, n in enumerate(D["ids"])}
        s = {c: np.array([S[c][si[int(n)]] for n in ids]) for c in ("SXX", "SYY", "SZZ", "SXY", "SYZ", "SZX")}
        vms.append(np.sqrt(0.5 * ((s["SXX"] - s["SYY"]) ** 2 + (s["SYY"] - s["SZZ"]) ** 2 + (s["SZZ"] - s["SXX"]) ** 2)
                           + 3 * (s["SXY"] ** 2 + s["SYZ"] ** 2 + s["SZX"] ** 2)))
        us.append(np.array([[D[c][di[int(n)]] for c in ("D1", "D2", "D3")] for n in ids]))
    used = np.unique(tris)
    remap = np.full(len(xyz), -1)
    remap[used] = np.arange(len(used))
    xyz, tris = xyz[used], remap[tris]
    vms, us = [v[used] for v in vms], [u[used] for u in us]
    mid = np.abs(xyz[:, 0] - p["length_mm"] / 2) < 0.6 * p["element_size_mm"]
    centre = xyz.mean(axis=0)
    return {"rec": rec, "p": p, "xyz": xyz - centre, "tris": tris, "vm": vms, "u": us, "times": times, "mid": mid,
            "loads_N": [tm * rec["solver_outputs"]["p_max_N"] for tm in times]}


# frames run up to increment 19 (time 0.95): the next one, at 0.98 P_cr, is past first yield
STRUT_FRAMES = 19


def strut_box(d) -> list:
    pts = np.vstack([d["xyz"]] + [d["xyz"] + STRUT_SCALE * d["u"][k] for k in range(STRUT_FRAMES)])
    pad = 0.02 * np.ptp(pts, axis=0).max()
    return [(pts.min(axis=0) - pad).tolist(), (pts.max(axis=0) + pad).tolist()]


def strut_frame(d, k: int, name: str, box) -> Path:
    p, vm = d["p"], d["vm"][k]
    return write_scene(BUILD / name, d["xyz"] + STRUT_SCALE * d["u"][k], d["tris"], vm, ghost_xyz=d["xyz"],
                       field="von Mises stress", units="MPa", vmin=0.0, vmax=300.0, bands=12, band_colors=mr.bands(12),
                       elev=22, azim=-74, sharp_angle_deg=60, distance_factor=3.4, resolution=[1400, 900],
                       fixed_box=box, expected_volume_mm3=p["length_mm"] * p["width_mm"] * p["thickness_mm"],
                       title=f"Strut at {d['loads_N'][k] / 1000:.2f} kN",
                       caption=f"Bow drawn {STRUT_SCALE:.0f}x; peak at mid-span {vm[d['mid']].max():.0f} MPa against the "
                               f"{p['yield_strength_MPa']:.0f} MPa yield (top band from 275).")


def scene_strut():
    """The bowed 500 mm strut in the last load increment before first yield (time 0.95 of the ramp to
    0.98 P_cr), von Mises stress with the top band starting at yield. Same camera as its load-step frames."""
    d = strut_data()
    return strut_frame(d, STRUT_FRAMES - 1, "strut", strut_box(d))


def scene_cold_plate_3d():
    return scene_cold_plate(thin=4, name="cold_plate_3d")


SCENES = {"cold_plate_3d": scene_cold_plate_3d, "strap_proof": scene_strap_proof, "bolted_joint": scene_bolted_joint, "joint_section": scene_joint_section, "cold_plate": scene_cold_plate,
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


def publish_frames(name: str, scenes: list, gates: list, frames: list, main: int, extra: dict) -> dict:
    """Crop every frame with one box (the union of their silhouettes), save them, and make frame `main`
    the viewer's main image, thumbnail and scenes.json entry, so nothing jumps when the slider moves."""
    from PIL import Image

    ims = [Image.fromarray((np.clip(mr.beauty(sc), 0, 1) * 255).astype(np.uint8), "RGBA") for sc in scenes]
    alpha = np.max([np.asarray(im)[..., 3] for im in ims], axis=0)
    ys, xs = np.nonzero(alpha > 60)
    pad = int(0.10 * max(np.ptp(xs), np.ptp(ys)))
    crop = (max(0, xs.min() - pad), max(0, ys.min() - pad), min(ims[0].width, xs.max() + pad), min(ims[0].height, ys.max() + pad))
    for k, (im, f) in enumerate(zip(ims, frames)):
        im = im.crop(crop)
        im.thumbnail((1400, 900), Image.LANCZOS)
        im.save(SITE / f"fr_{name}_{k:02d}.webp", quality=88, method=6)
        f["img"] = f"v2/fr_{name}_{k:02d}.webp"
    shutil.copyfile(SITE / f"fr_{name}_{main:02d}.webp", SITE / f"vp_{name}.webp")
    th = Image.open(SITE / f"vp_{name}.webp").convert("RGBA")
    th.thumbnail((800, 500), Image.LANCZOS)
    canvas = Image.new("RGBA", (800, 500), (0, 0, 0, 0))
    canvas.alpha_composite(th, ((800 - th.width) // 2, (500 - th.height) // 2))
    canvas.save(SITE / f"th_{name}.webp", quality=88, method=6)
    meta = json.loads(scenes[main].with_suffix(".json").read_text(encoding="utf-8"))
    path = SITE / "scenes.json"
    allscenes = json.loads(path.read_text(encoding="utf-8"))
    allscenes[name] = {k: meta.get(k) for k in ("field", "units", "vmin", "vmax", "bands", "band_colors", "title",
                                                 "caption", "data_min", "data_max")}
    allscenes[name].update(gates[main])
    path.write_text(json.dumps(allscenes, indent=1), encoding="utf-8")
    for ext in (".npz", ".json"):        # the 3D view's mesh, where there is one, is the main frame
        shutil.copyfile(scenes[main].with_suffix(ext), BUILD / f"{name}{ext}")
    fpath = SITE / "frames.json"
    allframes = json.loads(fpath.read_text(encoding="utf-8")) if fpath.exists() else {}
    allframes[name] = {**extra, "main": main, "worst_misread": max(g["legibility"]["misread"] for g in gates),
                       "worst_on_legend": min(g["color"]["fraction_on_legend"] for g in gates), "frames": frames}
    fpath.write_text(json.dumps(allframes, indent=1), encoding="utf-8")
    return allframes[name]


def make_strap_frames(blender, samples: int, skip_render: bool) -> dict:
    """The strap through its proof test: every second increment of the load to 15 kN and of the unloading,
    on the main render's camera and colour scale."""
    from harness.calculix import read_frd

    work = resolve(STRAP / "solver", "plastic", ("mesh.inp",), BUILD / "strap_proof_frames_solve", "plastic.dat",
                   every_increment=True)
    rec = read_json(STRAP / "point.json")
    p = rec["parameters"]
    nodes, tris = read_tri6(work / "mesh.inp")
    frd = read_frd(work / "plastic.frd")
    stress = [b for n, b in frd["blocks"] if n == "STRESS"]
    pe = [b for n, b in frd["blocks"] if n == "PE"]
    if len(stress) != 40 or len(pe) != 40:
        raise RuntimeError(f"{len(stress)} stress blocks, {len(pe)} plastic-strain blocks; the run has 40 increments")
    used = np.unique(tris)
    loc = {int(n): k for k, n in enumerate(used)}
    xy0 = np.array([nodes[int(n)] for n in used])
    t0 = np.vectorize(loc.get)(tris)
    root = loc[int(rec["solver_outputs"]["root_node"])]
    rh = p["hole_diameter_mm"] / 2
    lig = (np.abs(xy0[:, 0]) < 1e-9) & (xy0[:, 1] >= rh - 1e-9)          # the ligament, on the x = 0 symmetry line
    picks = list(range(1, 40, 2))                                         # times 0.1, 0.2, ..., 2.0
    scenes, gates, frames = [], [], []
    for n, k in enumerate(picks):
        S, E = stress[k], pe[k]
        si = {int(q): i for i, q in enumerate(S["ids"])}
        ei = {int(q): i for i, q in enumerate(E["ids"])}
        sxx = np.array([S["SXX"][si[int(q)]] for q in used])
        peeq = np.array([E["PE"][ei[int(q)]] for q in used])
        time = 0.05 * (k + 1)
        load = p["axial_load_N"] * (time if time <= 1 else 2 - time)
        if k == 19 and abs(sxx[root] / rec["metrics"]["notch_stress_MPa"] - 1) > 1e-4:
            raise RuntimeError("the proof-load frame doesn't match the recorded hole-edge stress")
        if k == 39 and abs(sxx[root] / rec["metrics"]["residual_stress_MPa"] - 1) > 1e-4:
            raise RuntimeError("the last frame doesn't match the recorded residual stress")
        yielded = peeq[lig] > 1e-9
        depth = float((xy0[lig, 1][yielded] - rh).max()) if yielded.any() else 0.0
        xy, tt, (val,) = mirror(xy0, t0, [sxx], 0)
        xy, tt, (val,) = mirror(xy, tt, [val], 1)
        xyz, faces, vv = extrude_planar(xy, tt, val, thickness=p["thickness_mm"])
        sc = write_scene(BUILD / f"frames/strap_proof_{n:02d}", xyz, faces, vv, field="axial stress σxx", units="MPa",
                         **STRAP_SCALE, elev=40, azim=-66, sharp_angle_deg=60, distance_factor=2.8,
                         frame_box=[[-28, -21, -3], [28, 21, 3]], fill=0.95, resolution=[1400, 900],
                         expected_volume_mm3=p["length_mm"] * p["width_mm"] * p["thickness_mm"]
                         - np.pi * rh ** 2 * p["thickness_mm"],
                         title=f"Strap, {'loading' if time <= 1 else 'unloading'}: {load / 1000:.1f} kN", caption="")
        if not skip_render:
            mr.render(blender, sc, samples)
        gates.append(gate(sc))
        scenes.append(sc)
        phase = "Loading" if time <= 1 + 1e-9 else "Unloading"
        if phase == "Loading":
            state = f"yielded {depth:.1f} mm deep" if depth > 0 else "still elastic"
        elif k == 39:
            state = "the stress left behind, in compression"
        else:
            state = f"unloading elastically, {depth:.1f} mm stays yielded"
        frames.append({"text": f"{phase}: {load / 1000:.1f} kN · hole edge {sxx[root]:.0f} MPa · {state}",
                       "phase": phase, "load_kN": round(load / 1000, 2), "edge_MPa": round(float(sxx[root]), 1),
                       "yield_depth_mm": round(depth, 2)})
        print(f"strap frame {n + 1}: {frames[-1]['text']}, misread {gates[-1]['legibility']['misread']:.2%}", flush=True)
    return publish_frames("strap_proof", scenes, gates, frames, main=picks.index(19),
                          extra={"label": "Proof test", "recorded_zone_mm": rec["metrics"]["plastic_zone_mm"]})


def make_strut_frames(blender, samples: int, skip_render: bool) -> dict:
    """The strut at each load step up to first yield, for the viewer's load slider: one camera, one
    stress scale, one crop for every frame, each frame through the three gates. The last frame is also
    the viewer's main strut image."""
    d = strut_data()
    box = strut_box(d)
    scenes, gates = [], []
    for k in range(STRUT_FRAMES):
        sc = strut_frame(d, k, f"frames/strut_{k:02d}", box)
        if not skip_render:
            mr.render(blender, sc, samples)
        gates.append(gate(sc))
        scenes.append(sc)
        print(f"strut frame {k + 1}: {d['loads_N'][k] / 1000:.2f} kN, misread {gates[-1]['legibility']['misread']:.2%}", flush=True)
    pcr = d["rec"]["metrics"]["critical_load_N"] / 1000
    frames = []
    for k in range(STRUT_FRAMES):
        mid = d["mid"]
        load, defl, peak = d["loads_N"][k] / 1000, float(np.abs(d["u"][k][mid][:, 2]).max()), float(d["vm"][k][mid].max())
        frames.append({"text": f"{load:.2f} kN, {round(100 * load / pcr)} % of buckling · mid-span moves {defl:.2f} mm · "
                               f"peak {peak:.0f} MPa", "load_kN": round(load, 2), "deflection_mm": round(defl, 2),
                       "peak_MPa": round(peak, 1)})
    return publish_frames("strut", scenes, gates, frames, main=STRUT_FRAMES - 1,
                          extra={"label": "Load", "buckling_kN": round(pcr, 2),
                                 "first_yield_kN": round(d["rec"]["metrics"]["first_yield_load_N"] / 1000, 2)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--skip-render", action="store_true")
    ap.add_argument("--frames", nargs="+", choices=["strut", "strap_proof"], help="load-step frames for the viewer slider")
    args = ap.parse_args()
    blender = mr.find_blender()
    if args.frames:
        makers = {"strut": make_strut_frames, "strap_proof": make_strap_frames}
        for name in args.frames:
            f = makers[name](blender, args.samples, args.skip_render)
            print(f"{len(f['frames'])} {name} frames; worst misread {f['worst_misread']:.2%}, "
                  f"worst on legend {f['worst_on_legend']:.2%}")
        return
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

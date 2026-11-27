"""Render scenes for studies 24 (cracked plate; part 2: surface crack), 25 (O-ring face seal) and 26 (shaft
shoulder), written by the study session for the dashboard session's make_study_renders.py (kept in their own module so the two sessions'
edits don't meet in one file). Register them there with lazy imports, e.g.

    "shaft_fillet": lambda: __import__("scenes_24_26").scene_shaft_fillet(),

Each scene solves the evidence run's recorded deck again (or rebuilds it with the run's own saved model code) and
refuses to draw unless the re-solve reproduces the run: the solver's printed output identical to the saved one and
the headline metric, read from the new field the way the study read it, equal to the recorded value. Each returns
write_scene's path, so gate() and publish() apply unchanged. Re-solves run single-threaded when OMP_NUM_THREADS=1.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import make_renders as mr  # noqa: E402
from make_study_renders import BUILD, resolve  # noqa: E402

from harness.femesh import compact, extrude_planar, read_inp, write_scene  # noqa: E402
from harness.runio import read_json  # noqa: E402


def _mirror3(xyz, tris, val, axis):
    """Mirror a half model's surface about the plane x_axis = 0: the faces on the plane become internal and are
    dropped, the nodes on it are shared, and the copy's faces are flipped so they still point outwards."""
    on = np.abs(xyz[:, axis]) < 1e-6
    tris = tris[~on[tris].all(axis=1)]
    idx = np.nonzero(~on)[0]
    remap = np.arange(len(xyz))
    remap[idx] = len(xyz) + np.arange(len(idx))
    flip = np.ones(3)
    flip[axis] = -1
    return (np.vstack([xyz, xyz[idx] * flip]), np.vstack([tris, remap[tris][:, ::-1]]),
            np.concatenate([val, val[idx]]))


def _von_mises(S, rows):
    sxx, syy, szz = S["SXX"][rows], S["SYY"][rows], S["SZZ"][rows]
    sxy, syz, szx = S["SXY"][rows], S["SYZ"][rows], S["SZX"][rows]
    return np.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2) + 3 * (sxy ** 2 + syz ** 2 + szx ** 2))


def _section_triangles(elems):
    """Linear triangles in the section plane from 8-node quads (CAX8R/CPE8/CPS8: four corners, four mid-sides,
    no centre node) and 6-node triangles, through the mid-side nodes, so the field is drawn at the resolution the
    solver computed it. Each element's corner order is kept, so the triangles share its orientation."""
    tris = []
    for c in elems:
        if len(c) == 8:
            a, b, cc, d, ab, bc, cd, da = c
            tris += [(a, ab, da), (ab, b, bc), (bc, cc, cd), (da, cd, d), (ab, bc, cd), (ab, cd, da)]
        elif len(c) == 6:
            a, b, cc, ab, bc, ca = c
            tris += [(a, ab, ca), (ab, b, bc), (ca, bc, cc), (ab, bc, ca)]
        else:
            raise ValueError(f"unexpected {len(c)}-node section element")
    return np.array(tris)


def _boundary_edges(tris):
    """Edges used by exactly one triangle, each in the direction its triangle runs it (so a counter-clockwise
    triangulation gives a counter-clockwise boundary)."""
    count = {}
    for t in tris:
        for i, j in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            key = (min(i, j), max(i, j))
            count[key] = count.get(key, []) + [(i, j)]
    return np.array([v[0] for v in count.values() if len(v) == 1])


def _revolve(rz, tris, val, sweep_deg, steps):
    """A closed solid of revolution from a triangulated section in the (r, z) plane, swept about z from 0 to
    sweep_deg in `steps` facets: the walls from the section's boundary edges, the section itself as the two
    end caps. Returns xyz, triangles, value per vertex; the faces point outwards when the section's triangles
    run counter-clockwise in (r, z) (checked by the caller through the enclosed volume's sign and size)."""
    n = len(rz)
    th = np.radians(np.linspace(0.0, sweep_deg, steps + 1))
    xyz = np.vstack([np.column_stack([rz[:, 0] * np.cos(t), rz[:, 0] * np.sin(t), rz[:, 1]]) for t in th])
    walls = []
    for i, j in _boundary_edges(tris):
        for k in range(steps):
            a, b, c, d = k * n + i, k * n + j, (k + 1) * n + j, (k + 1) * n + i
            walls += [(a, d, c), (a, c, b)]
    caps = np.vstack([tris, steps * n + tris[:, ::-1]])
    return xyz, np.vstack([np.array(walls), caps]), np.tile(val, steps + 1)


# --------------------------------------------------------------------------- study 24: cracked plate

CRACK_RUN = REPO / "runs/20261123-164649_edge_crack_mesh_r2"
CRACK = CRACK_RUN / "points/p02_tip_element_size_mm-0.025"   # the finest tip mesh, the page's evidence point
CRACK_A = 35.0             # mm: the solved crack length nearest below the critical 37.0 mm
CRACK_MAG = 50.0           # displacement magnification, so the crack's opening shows
CRACK_SCALE = dict(vmin=-150.0, vmax=450.0, bands=12, band_colors=mr.bands(12))   # 50 MPa bands; the tip is singular


def scene_cracked_plate():
    """The edge-cracked plate at its peak stress (150 MPa) with a 35 mm crack, just short of the critical 37 mm:
    opening stress sigma_yy on the deformed plate (displacements x50), the half model mirrored about the crack
    plane with the crack faces kept apart, drawn 10 mm thick (the analysis is plane strain per mm).

    The run kept no mesh or deck, so both are made again with the run's own saved model code (inputs/edge_crack.py)
    and the same Gmsh; the only addition is the field-output request. Gates: the node count must equal the run's
    at this crack length, the plate must be in equilibrium as the run's was, and K from the crack opening,
    computed by the run's own k_from_opening with the run's fit range, must equal the recorded K_opening to 1e-9.
    The drawn volume is checked on the undeformed plate (ghost), W x 2H x t: the crack has no width."""
    import importlib.util
    import subprocess

    from harness.calculix import read_frd
    from studies.cantilever import find_freecadcmd

    spec = importlib.util.spec_from_file_location("edge_crack_saved", CRACK_RUN / "inputs/edge_crack.py")
    ec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ec)
    rec = read_json(CRACK / "point.json")
    p = rec["parameters"]
    row = next(r for r in rec["solver_outputs"]["rows"] if abs(r["a_mm"] - CRACK_A) < 1e-9)
    W, H, t = float(p["width_mm"]), float(p["half_height_mm"]), float(p["thickness_mm"])
    E, nu, sig, h = (float(p[k]) for k in ("youngs_modulus_MPa", "poisson_ratio", "sigma_max_MPa", "tip_element_size_mm"))
    bin_dir = find_freecadcmd().parent                     # the Gmsh and CalculiX the study ran (studies/edge_crack.py)
    work = BUILD / "cracked_plate_solve"
    work.mkdir(parents=True, exist_ok=True)
    ec.write_geo(work / "m.geo", a=CRACK_A, W=W, H=H, h_tip=h, h_far=float(p["far_element_size_mm"]))
    subprocess.run([str(bin_dir / "gmsh.exe"), "m.geo", "-2", "-format", "inp", "-o", "mesh.inp"], cwd=work,
                   capture_output=True, text=True, timeout=600, check=True)
    ec.to_plane_strain(work / "mesh.inp")
    info = ec.write_deck(work / "mesh.inp", work / "job.inp", a=CRACK_A, W=W, H=H, sigma=sig, E=E, nu=nu)
    if info["nodes"] != row["nodes"]:
        raise RuntimeError(f"{info['nodes']} nodes; the run had {row['nodes']} at a = {CRACK_A} mm")
    deck = (work / "job.inp").read_text(encoding="utf-8")
    i = deck.rindex("*END STEP")
    (work / "job.inp").write_text(deck[:i] + "*NODE FILE\nU\n*EL FILE\nS\n" + deck[i:], encoding="utf-8")
    subprocess.run([str(bin_dir / "ccx.exe"), "-i", "job"], cwd=work, capture_output=True, text=True, timeout=1800,
                   check=True)
    top, crack, rf = ec.read_node_print(work / "job.dat")
    P = info["applied_load_N_per_mm"]
    if abs(rf + P) / P > 1e-9:
        raise RuntimeError(f"ligament reaction {rf} against the applied {P}")
    k_cod, n_cod = ec.k_from_opening(crack, info, a=CRACK_A, E=E, nu=nu, r_min=2 * h, r_max=max(0.1 * CRACK_A, 6 * h))
    if n_cod != row["opening_points"] or abs(k_cod / row["K_opening"] - 1) > 1e-9:
        raise RuntimeError(f"K from the opening {k_cod} ({n_cod} points) != recorded {row['K_opening']} "
                           f"({row['opening_points']} points)")
    # the 6-node triangles (Gmsh also writes edge elements; only the plate's CPE6 are drawn)
    nodes, elems, mode = {}, [], None
    for line in (work / "mesh.inp").read_text(encoding="utf-8").splitlines():
        if line.startswith("*"):
            u = line.upper()
            mode = "node" if u.startswith("*NODE") else ("tri" if u.startswith("*ELEMENT") and "CPE6" in u else None)
            continue
        if mode == "node":
            v = line.split(",")
            nodes[int(v[0])] = (float(v[1]), float(v[2]))
        elif mode == "tri":
            elems.append([int(q) for q in line.split(",")[1:7]])
    fr = read_frd(work / "job.frd")
    U, S = fr["DISP"], fr["STRESS"]
    ui = {int(n): k for k, n in enumerate(U["ids"])}
    si = {int(n): k for k, n in enumerate(S["ids"])}
    used = sorted({n for c in elems for n in c})
    loc = {n: k for k, n in enumerate(used)}
    xy = np.array([nodes[n] for n in used])
    u = np.array([(U["D1"][ui[n]], U["D2"][ui[n]]) for n in used])
    syy = np.array([S["SYY"][si[n]] for n in used])
    tris = np.vectorize(loc.get)(_section_triangles(elems))
    # mirror about y = 0: the ligament's nodes (x >= a) are shared, the crack face's are not, so the crack opens
    shared = (np.abs(xy[:, 1]) < 1e-7) & (xy[:, 0] >= CRACK_A - 1e-7)
    idx = np.nonzero(~shared)[0]
    remap = np.arange(len(xy))
    remap[idx] = len(xy) + np.arange(len(idx))
    xy2 = np.vstack([xy, xy[idx] * [1, -1]])
    u2 = np.vstack([u, u[idx] * [1, -1]])
    tris2 = np.vstack([tris, remap[tris][:, ::-1]])
    syy2 = np.concatenate([syy, syy[idx]])
    ghost, faces, val = extrude_planar(xy2, tris2, syy2, thickness=t)
    deformed, _, _ = extrude_planar(xy2 + CRACK_MAG * u2, tris2, syy2, thickness=t)
    centre = np.array([W / 2, 0.0, 0.0])
    m = rec["metrics"]
    return write_scene(BUILD / "cracked_plate", deformed - centre, faces, val, ghost_xyz=ghost - centre,
                       field="opening stress σyy", units="MPa", **CRACK_SCALE, elev=24, azim=-72,
                       sharp_angle_deg=60, distance_factor=2.8, resolution=[1400, 900],
                       expected_volume_mm3=W * 2 * H * t,
                       title=f"Cracked plate at 150 MPa with a {CRACK_A:.0f} mm edge crack: opening stress",
                       caption=f"Just short of the critical {m['crit_crack_mm']:.1f} mm crack; K "
                               f"{row['K_energy'] / np.sqrt(1000):.1f} MPa√m against the 100 MPa√m toughness. "
                               f"Displacements x{CRACK_MAG:.0f}; the range stops at 450 MPa (the tip is singular). "
                               f"Half model mirrored about the crack plane.")


# --------------------------------------------------------------------------- study 24 part 2: surface crack

SCRACK_RUN = REPO / "runs/20261126-204858_surface_crack_mesh_r1"
SCRACK = SCRACK_RUN / "points/p02_front_element_rel-0.0125"   # the finest front mesh, the page's evidence point
SCRACK_SHAPE = 3            # the deepest shape solved: a 7.5 mm, c 10.08 mm, three quarters through the 10 mm plate
SCRACK_SCALE = dict(vmin=0.0, vmax=600.0, bands=12, band_colors=mr.bands(12))   # 50 MPa bands; the front is singular


def scene_surface_crack():
    """The semi-elliptical surface crack at its deepest solved shape (a 7.5 mm, c 10.08 mm) under 150 MPa: opening
    stress sigma_yy on the crack plane, seen from the cut. The quarter model is mirrored about x = 0 (the crack's
    centre plane), not about y = 0, so the plane y = 0 is a face of the drawn half plate: the crack face (free,
    sigma_yy near zero) inside the ellipse, the ligament carrying the load around it, highest along the front.
    Undeformed (the opening is microns).

    The run kept no mesh or deck, so both are made again with the run's own saved model code
    (inputs/surface_crack.py) and the same Gmsh, as studies/surface_crack.py made the shape's centre solve; the only
    addition is the field-output request. Gates: the node count must equal the run's at this shape, the ligament's
    reaction must balance the applied load as the run's did, and the K profile from the crack opening, computed by
    the run's own k_profile with the study's fit ranges, must equal the recorded K_fe at all 19 stations to 1e-9.
    The drawn volume is the half plate, 2 (W/2) H t: the crack has no width."""
    import importlib.util
    import subprocess

    from harness.calculix import read_frd
    from studies.cantilever import find_freecadcmd

    spec = importlib.util.spec_from_file_location("surface_crack_saved", SCRACK_RUN / "inputs/surface_crack.py")
    sc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sc)
    rec = read_json(SCRACK / "point.json")
    p = rec["parameters"]
    row = rec["solver_outputs"]["rows"][SCRACK_SHAPE]
    stations = rec["solver_outputs"]["stations_deg"]
    a, c = float(row["a_mm"]), float(row["c_mm"])
    Wh, H, t = float(p["half_width_mm"]), float(p["half_height_mm"]), float(p["thickness_mm"])
    E, nu, sig = (float(p[k]) for k in ("youngs_modulus_MPa", "poisson_ratio", "sigma_max_MPa"))
    h = float(p["front_element_rel"]) * a                 # as studies/surface_crack.py: front size scales with a
    work = BUILD / "surface_crack_solve"
    work.mkdir(parents=True, exist_ok=True)
    sc.mesh(work / "mesh.inp", a=a, c=c, Wh=Wh, H=H, t=t, h_front=h, h_far=float(p["far_element_size_mm"]),
            r_fine=4 * h)
    info = sc.write_deck(work / "mesh.inp", work / "job.inp", a=a, c=c, Wh=Wh, H=H, t=t, sigma=sig, E=E, nu=nu)
    if info["nodes"] != row["nodes"]:
        raise RuntimeError(f"{info['nodes']} nodes; the run had {row['nodes']} at a = {a}, c = {c} mm")
    deck = (work / "job.inp").read_text(encoding="utf-8")
    i = deck.rindex("*END STEP")
    (work / "job.inp").write_text(deck[:i] + "*NODE FILE\nU\n*EL FILE\nS\n" + deck[i:], encoding="utf-8")
    ccx = find_freecadcmd().parent / "ccx.exe"            # the CalculiX the study ran
    subprocess.run([str(ccx), "-i", "job"], cwd=work, capture_output=True, text=True, timeout=3600, check=True)
    top, crack, rf = sc.read_node_print(work / "job.dat")
    P_app = info["applied_load_N"]
    if abs(rf + P_app) / P_app > 1e-9:
        raise RuntimeError(f"ligament reaction {rf} against the applied {P_app}")
    prof = sc.k_profile(crack, info, a=a, c=c, E=E, nu=nu, stations_deg=stations, r_min=3 * h,
                        r_max=max(0.3 * a, 6 * h), band=1.5 * h)
    K = np.array([q["K"] for q in prof])
    K_rec = np.array(row["K_fe"], dtype=float)
    if not np.allclose(K, K_rec, rtol=1e-9, atol=0.0, equal_nan=True):
        raise RuntimeError(f"K profile from the re-solve differs from the run's: max rel "
                           f"{np.nanmax(np.abs(K / K_rec - 1)):.2e}")
    fr = read_frd(work / "job.frd")
    S = fr["STRESS"]
    nodes, elems = read_inp(work / "mesh.inp")
    ids = np.array([int(n) for n in S["ids"]])
    syy = np.asarray(S["SYY"], dtype=float)
    xyz = np.array([nodes[int(n)] for n in ids])
    xyz, tris, syy = compact(xyz, mr.surface(nodes, elems, ids), syy)
    xyz, tris, syy = _mirror3(xyz, tris, syy, 0)
    # (x, y, z) -> (x, z, -y): the crack plane y = 0 on top (Z = 0, the plate below it), the crack's mouth on the
    # face Y = 0; a proper rotation, so the faces keep their winding
    xyz = np.column_stack([xyz[:, 0], xyz[:, 2] - t / 2, -xyz[:, 1]])
    k_deep = K_rec[-1] / 31.6227766
    k_surf = K_rec[0] / 31.6227766
    return write_scene(BUILD / "surface_crack", xyz, tris, syy, field="opening stress σyy", units="MPa",
                       **SCRACK_SCALE, elev=38, azim=-62, sharp_angle_deg=60, distance_factor=1.6,
                       resolution=[1400, 900], expected_volume_mm3=2 * Wh * H * t,
                       title=f"Surface crack {a:.1f} mm deep, {2 * c:.1f} mm long, at 150 MPa: opening stress on "
                             f"the crack plane",
                       caption=f"Seen from the cut through the crack: the free crack face (inside the ellipse) "
                               f"carries no stress, the ligament around it the load, highest along the front "
                               f"(K {k_deep:.1f} MPa√m at the deepest point, {k_surf:.1f} at the surface; the "
                               f"range stops at 600 MPa, the front is singular). Quarter model mirrored about the "
                               f"crack's centre plane.")


# --------------------------------------------------------------------------- study 25: O-ring face seal

ORING_RUN = REPO / "runs/20261124-100619_oring_seal_corners"
ORING = ORING_RUN / "points/p02_tightest"   # the tightest stack: thickest ring, shallowest groove, hardest compound
ORING_SWEEP = 270.0                          # a three-quarter ring, so the squeezed section shows at both cut faces
ORING_SCALE = dict(vmin=0.0, vmax=3.5, bands=14, band_colors=mr.bands(14))       # 0.25 MPa bands; peak 3.06


def scene_oring():
    """The O-ring at the tightest stack, squeezed in its groove: von Mises stress in the rubber on its deformed
    shape (true scale), the axisymmetric half section mirrored about its mid-plane and revolved through 270 deg.

    Gates: the re-solve's job.dat (the cover's reaction at every increment, the symmetry and wall totals) must equal
    the evidence run's byte for byte (resolve), and the cover's reaction converted to N per mm of seal the way
    studies/oring_seal.py converts it must equal the recorded force_per_length (5.939 N/mm) to 1e-9. The drawn
    solid's expected volume is the undeformed ring's (the run's own ring_volume_mm3) times the recorded volume
    ratio, so the volume gate also checks the drawn deformed shape against the run."""
    import importlib.util
    import math
    import re

    from harness.calculix import read_dat_total_forces, read_frd

    spec = importlib.util.spec_from_file_location("oring_saved", ORING_RUN / "inputs/oring_ccx.py")
    W = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(W)
    rec = read_json(ORING / "point.json")
    out = rec["solver_outputs"]
    work = resolve(ORING / "solver", "job", (), BUILD / "oring_solve", "job.dat")
    tot = read_dat_total_forces(work / "job.dat")
    F = abs(tot["CTOP"][1]) / W.SEGMENT / (2 * math.pi * out["model"]["mean_radius_mm"])
    if abs(F / rec["metrics"]["force_per_length_N_per_mm"] - 1) > 1e-9:
        raise RuntimeError(f"force per length {F} from the re-solve != recorded {rec['metrics']['force_per_length_N_per_mm']}")
    # the ring's nodes and elements from the deck (2D: x = radius, y = axial)
    text = (work / "job.inp").read_text(encoding="latin-1")
    nodes, ring, mode = {}, [], None
    for line in text.splitlines():
        if line.startswith("*"):
            u = line.upper()
            mode = "node" if u.startswith("*NODE") and "FILE" not in u and "PRINT" not in u else (
                "ring" if u.startswith("*ELEMENT") and re.search(r"ELSET=RING\b", u) else None)
            continue
        if mode == "node":
            v = line.split(",")
            nodes[int(v[0])] = (float(v[1]), float(v[2]))
        elif mode == "ring":
            ring.append([int(q) for q in line.split(",")[1:] if q.strip()])
    fr = read_frd(work / "job.frd")
    U, S = fr["DISP"], fr["STRESS"]
    ui = {int(n): k for k, n in enumerate(U["ids"])}
    si = {int(n): k for k, n in enumerate(S["ids"])}
    used = sorted({n for c in ring for n in c})
    loc = {n: k for k, n in enumerate(used)}
    rz = np.array([(nodes[n][0] + U["D1"][ui[n]], nodes[n][1] + U["D2"][ui[n]]) for n in used])
    rows = np.array([si[n] for n in used])
    vm = _von_mises(S, rows)                 # SXX radial, SYY axial, SZZ hoop, SXY the r-z shear
    tris = np.vectorize(loc.get)(_section_triangles(ring))

    def area(q):
        return 0.5 * ((q[tris[:, 1], 0] - q[tris[:, 0], 0]) * (q[tris[:, 2], 1] - q[tris[:, 0], 1])
                      - (q[tris[:, 2], 0] - q[tris[:, 0], 0]) * (q[tris[:, 1], 1] - q[tris[:, 0], 1]))

    # orientation from the undeformed section, where every triangle must agree; squeezed flat against the cover,
    # a corner and its two mid-side nodes can fall almost in line, so a drawn sub-triangle may flip as a sliver
    # (one of 10 410 here, -1e-5 mm2) without any element inverting; anything more than slivers is refused
    rz0 = np.array([nodes[n] for n in used])
    a0 = area(rz0)
    if not (np.all(a0 > 0) or np.all(a0 < 0)):
        raise RuntimeError("the undeformed section's triangles don't share one orientation")
    if a0[0] < 0:
        tris = tris[:, ::-1]
    a1 = area(rz)
    if -a1[a1 < 0].sum() > 1e-4 * a1.sum():
        raise RuntimeError(f"{(a1 < 0).sum()} deformed triangles flipped, {-a1[a1 < 0].sum():.3g} mm2: more than slivers")
    # mirror the upper half about the mid-plane z = 0 (the SYM nodes)
    off = np.abs(rz[:, 1]) > 1e-9
    idx = np.nonzero(off)[0]
    remap = np.arange(len(rz))
    remap[idx] = len(rz) + np.arange(len(idx))
    rz = np.vstack([rz, rz[idx] * [1, -1]])
    tris = np.vstack([tris, remap[tris][:, ::-1]])
    vm = np.concatenate([vm, vm[idx]])
    xyz, faces, val = _revolve(rz, tris, vm, ORING_SWEEP, 96)
    xyz, faces, val = compact(xyz, faces, val)
    V0 = W.ring_volume_mm3({n: nodes[n] for n in used}, [(0, "CAX8R" if len(c) == 8 else "CAX6", c) for c in ring])
    expected = 2 * V0 * out["volume_ratio"] * ORING_SWEEP / 360.0
    m = rec["metrics"]
    return write_scene(BUILD / "oring", xyz, faces, val, field="von Mises stress", units="MPa", **ORING_SCALE,
                       elev=28, azim=-50, sharp_angle_deg=50, distance_factor=2.8, resolution=[1400, 900],
                       expected_volume_mm3=expected,
                       title="O-ring at the tightest stack, squeezed in its groove: von Mises stress",
                       caption=f"Squeeze {m['squeeze_pct']:.1f} %, closing force {m['force_per_length_N_per_mm']:.2f} N "
                               f"per mm of seal, peak contact pressure {m['peak_contact_pressure_MPa']:.2f} MPa, groove "
                               f"fill {m['groove_fill_pct']:.0f} %. Deformed shape at true scale; the axisymmetric half "
                               f"section mirrored and revolved through {ORING_SWEEP:.0f} degrees.")


# --------------------------------------------------------------------------- study 26: shaft shoulder

SHAFT_RUN = REPO / "runs/20261124-155125_shaft_fillet_size"
SHAFT = SHAFT_RUN / "points/p03_d36"          # the recommended 36 mm seat with its 45 mm shoulder, fillet 1.6 mm
SHAFT_SCALE = dict(vmin=0.0, vmax=150.0, bands=12, band_colors=mr.bands(12))   # 12.5 MPa bands


def scene_shaft_fillet():
    """The recommended shaft step under its 300 N m bending moment: von Mises stress on the whole shaft (the half
    model mirrored about its symmetry plane y = 0), laid along X with the bending plane vertical, tension on top.

    Gates: the re-solve's bending.dat must equal the evidence run's byte for byte (resolve), and the peak max
    principal stress on the fillet in the plane y = 0 (x > 0), over the nominal 32 M / (pi d^3), must equal the
    recorded kt_bending (2.22462) to 1e-9, read exactly as studies/shaft_fillet.py reads it. Torsion is left out:
    on the half model it is antisymmetric about y = 0, so its mirror needs sign flips this scene doesn't need."""
    import importlib.util

    from harness.calculix import read_frd
    from studies.shaft_fillet import _principal

    spec = importlib.util.spec_from_file_location("shaft_saved", SHAFT_RUN / "inputs/shaft_fillet_ccx.py")
    W = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(W)
    rec = read_json(SHAFT / "point.json")
    p, out = rec["parameters"], rec["solver_outputs"]
    work = resolve(SHAFT / "solver", "bending", (), BUILD / "shaft_fillet_solve", "bending.dat")
    fr = read_frd(work / "bending.frd")
    S = fr["STRESS"]
    row = {int(n): k for k, n in enumerate(fr["nodes"])}
    X = fr["coords"][[row[int(n)] for n in S["ids"]]]
    g = W.dims(p)
    plane = W.fillet_surface_mask(X, p) & (X[:, 0] > 0) & (np.abs(X[:, 1]) < 1e-6 * g["D"])
    s1 = _principal(S, np.arange(len(S["ids"])))[:, 2]
    kt = float(s1[plane].max() / out["sigma_nom_MPa"])
    if abs(kt / rec["metrics"]["kt_bending"] - 1) > 1e-9:
        raise RuntimeError(f"Kt {kt} from the re-solve != recorded {rec['metrics']['kt_bending']}")
    nodes, elems = read_inp(work / "bending.inp")
    ids = np.array([int(n) for n in S["ids"]])
    vm = _von_mises(S, np.arange(len(ids)))
    xyz = np.array([nodes[int(n)] for n in ids])
    xyz, tris, vm = compact(xyz, mr.surface(nodes, elems, ids), vm)
    xyz, tris, vm = _mirror3(xyz, tris, vm, 1)
    # (x, y, z) -> (z - centre, -y, x): the shaft along X, the bending plane vertical with the tension side up;
    # a proper rotation, so the faces keep their winding
    xyz = np.column_stack([xyz[:, 2] - g["z_end"] / 2, -xyz[:, 1], xyz[:, 0]])
    peak = float(vm.max())
    return write_scene(BUILD / "shaft_fillet", xyz, tris, vm, field="von Mises stress", units="MPa", **SHAFT_SCALE,
                       elev=34, azim=-128, sharp_angle_deg=40, distance_factor=2.8, resolution=[1400, 900],
                       expected_volume_mm3=2 * out["volume_mm3"],
                       title="Recommended shaft step under 300 N m bending: von Mises stress",
                       caption=f"36 mm seat, 45 mm shoulder, 1.6 mm fillet. The fillet concentrates the stress "
                               f"(Kt {kt:.2f} on max principal; von Mises peaks at {peak:.0f} MPa against "
                               f"{out['sigma_nom_MPa']:.1f} MPa in the plain shaft). Half model mirrored.")

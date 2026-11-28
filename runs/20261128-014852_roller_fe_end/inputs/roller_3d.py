"""Study 10 part 2: the track roller in 3D, with its ends: a roller of finite length on a wider plate (edge loading),
plain with an edge radius or crowned. CalculiX surface-to-surface penalty contact, as study 10.

Quarter model: symmetric about x = 0 (the plane through the roller axis normal to the rolling direction) and z = 0 (the
roller's mid-length). The 2D section is study 10's (models/fea/hertz_contact.py: the block and the quarter-disc
roller, quads refined at the contact by a distance field), extruded along z in layers graded towards the roller's
end z = L/2: the roller to L/2, the block (the plate, wider) to B/2 with the layers growing again beyond the end.
8-node bricks, as study 10.

The roller's profile along its length is applied as a drop delta(z) of its surface: every roller node at z is moved up
by delta(z) (a slice shift; the drops are microns against element sizes of tens of microns). profile = "none" (a
straight roller, square-ended: a singular edge, its peak grows with the mesh), "edge" (straight, with an end radius
r_e: delta = r_e - sqrt(r_e^2 - (z - z0)^2) over the last r_e), "log" (a logarithmic crown of the Fujiwara-Kawase
form, delta = A ln[1 / (1 - (1 - exp(-z_m / A)) (2z / L)^2)], A and z_m chosen in the case). The drop is capped at
cap_um: beyond it the surface is far out of contact, and a mm-scale slice shift would distort the elements.

Load: displacement control, as study 10. The top face of the roller moves down by the approach, adjusted by the
backend (secant iterations) until the total load is the target line load times the roller length.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

PARAMS = ("roller_radius_mm", "roller_length_mm", "plate_width_mm", "block_half_width_mm", "block_depth_mm",
          "youngs_modulus_MPa", "poisson_ratio", "yield_strength_MPa", "contact_element_size_mm",
          "far_element_size_mm", "refined_zone_mm", "end_layer_mm", "layer_growth", "penalty_stiffness_factor",
          "line_load_N_per_mm", "profile")
OPTIONAL = {"edge_radius_mm": 1.0, "crown_A_um": 0.0, "crown_zm_um": 30.0, "cap_um": 60.0, "approach_mm": 0.016,
            "z_fine_mm": 0.0, "max_layer_mm": 2.0}
HEX_FACES = {"S1": (0, 1, 2, 3), "S2": (4, 7, 6, 5), "S3": (0, 4, 5, 1), "S4": (1, 5, 6, 2), "S5": (2, 6, 7, 3),
             "S6": (3, 7, 4, 0)}


def opt(p: dict, k: str):
    return p.get(k, OPTIONAL[k])


def graded(length: float, h_end: float, growth: float, h_max: float, fine_at_end: bool = True) -> list[float]:
    """Layer thicknesses filling `length`: h_end at one end, growing by `growth` per layer up to h_max, scaled to fit
    exactly. fine_at_end: the thin layers at the far end (z = length), else at the start."""
    hs, tot = [], 0.0
    h = h_end
    while tot + h < length:
        hs.append(h)
        tot += h
        h = min(h * growth, h_max)
    hs.append(length - tot)
    if hs[-1] < 0.5 * hs[-2]:            # merge a sliver into its neighbour
        hs[-2] += hs.pop()
    hs = [float(v) for v in np.asarray(hs) * length / sum(hs)]       # plain floats: no numpy reprs in the .geo
    return hs[::-1] if fine_at_end else hs


def layers(p: dict) -> tuple[list[float], list[float]]:
    """Layer thicknesses along z: the roller (0 to L/2, fine at the end) and the plate beyond it (L/2 to B/2, fine at
    the start); the block uses both, so its z planes match the roller's up to the end."""
    L2, B2 = float(p["roller_length_mm"]) / 2, float(p["plate_width_mm"]) / 2
    h, g = float(p["end_layer_mm"]), float(p["layer_growth"])
    hmax = max(float(p["far_element_size_mm"]), 4 * h)
    zf = min(float(opt(p, "z_fine_mm")) if float(opt(p, "z_fine_mm")) > 0 else L2, L2)
    hr = float(opt(p, "max_layer_mm"))          # the roller's longest layer (a crowned contact starts mid-length)
    roller = graded(zf, h, g, hr, fine_at_end=True)
    if zf < L2 - 1e-9:   # fine layers where the profile changes (the start of an edge radius), growing both ways
        roller += graded(L2 - zf, h, g, hr, fine_at_end=False)
    beyond = graded(B2 - L2, h, g, hmax, fine_at_end=False) if B2 > L2 + 1e-9 else []
    return roller, beyond


def _layers_spec(hs: list[float]) -> str:
    cum = np.cumsum(hs) / sum(hs)
    return "{" + ", ".join("1" for _ in hs) + "}, {" + ", ".join(repr(float(c)) for c in cum) + "}"


def write_geo(p: dict, path: Path) -> None:
    R = float(p["roller_radius_mm"])
    W, H = float(p["block_half_width_mm"]), float(p["block_depth_mm"])
    h0, h1 = float(p["contact_element_size_mm"]), float(p["far_element_size_mm"])
    zone = float(p["refined_zone_mm"])
    roller, beyond = layers(p)
    L2 = float(p["roller_length_mm"]) / 2
    B2 = float(L2 + sum(beyond))
    path.write_text(f"""Geometry.AutoCoherence = 0;
Point(1) = {{0, 0, 0}}; Point(2) = {{{W!r}, 0, 0}}; Point(3) = {{{W!r}, {-H!r}, 0}}; Point(4) = {{0, {-H!r}, 0}};
Line(1) = {{1, 2}}; Line(2) = {{2, 3}}; Line(3) = {{3, 4}}; Line(4) = {{4, 1}};
Curve Loop(1) = {{1, 2, 3, 4}}; Plane Surface(1) = {{1}};
Point(11) = {{0, 0, 0}}; Point(12) = {{0, {R!r}, 0}}; Point(13) = {{{R!r}, {R!r}, 0}};
Circle(11) = {{11, 12, 13}}; Line(12) = {{13, 12}}; Line(13) = {{12, 11}};
Curve Loop(2) = {{11, 12, 13}}; Plane Surface(2) = {{2}};
Field[1] = Distance; Field[1].PointsList = {{1, 11}};
Field[2] = Threshold; Field[2].InField = 1;
Field[2].SizeMin = {h0!r}; Field[2].SizeMax = {h1!r};
Field[2].DistMin = {zone!r}; Field[2].DistMax = {zone + 8 * h1!r};
Background Field = 2;
Mesh.MeshSizeExtendFromBoundary = 0; Mesh.MeshSizeFromPoints = 0; Mesh.MeshSizeFromCurvature = 0;
Mesh.Algorithm = 8; Mesh.RecombineAll = 1; Mesh.SubdivisionAlgorithm = 1;
Mesh.ElementOrder = 1;
b1[] = Extrude {{0, 0, {L2!r}}} {{ Surface{{1}}; Layers{{ {_layers_spec(roller)} }}; Recombine; }};
{"b2[] = Extrude {0, 0, " + repr(B2 - L2) + "} { Surface{b1[0]}; Layers{ " + _layers_spec(beyond) + " }; Recombine; };" if beyond else ""}
r[] = Extrude {{0, 0, {L2!r}}} {{ Surface{{2}}; Layers{{ {_layers_spec(roller)} }}; Recombine; }};
Physical Volume("BLOCK") = {{b1[1]{", b2[1]" if beyond else ""}}};
Physical Volume("ROLLER") = {{r[1]}};
""", encoding="utf-8")


def drop_um(p: dict, z: np.ndarray) -> np.ndarray:
    """The roller's profile drop (microns) at distance z from mid-length, capped at cap_um."""
    z = np.abs(np.asarray(z, float))
    L2 = float(p["roller_length_mm"]) / 2
    prof = str(p["profile"])
    if prof == "none":
        d = np.zeros_like(z)
    elif prof == "edge":
        re = float(opt(p, "edge_radius_mm"))
        z0 = L2 - re
        u = np.clip(z - z0, 0.0, re)
        d = 1e3 * (re - np.sqrt(re * re - u * u))
    elif prof == "log":
        A, zm = float(opt(p, "crown_A_um")), float(opt(p, "crown_zm_um"))
        if A <= 0:
            A = lundberg_A_um(p)
        k = 1 - math.exp(-zm / A)
        s = np.clip(z / L2, 0.0, 1.0)
        d = A * np.log(1 / (1 - k * s * s))
    else:
        raise ValueError(f"unknown profile {prof!r}")
    return np.minimum(d, float(opt(p, "cap_um")))


def lundberg_A_um(p: dict) -> float:
    """Lundberg's crown parameter A = 2 Q / (pi l E') (microns), E' = E / (1 - nu^2) for two steel bodies, Q the
    roller load, l its length: the starting value for the logarithmic profile (Fujiwara-Kawase write A this way, with a
    design factor K1 we leave at 1)."""
    E, nu = float(p["youngs_modulus_MPa"]), float(p["poisson_ratio"])
    l = float(p["roller_length_mm"])
    Q = float(p["line_load_N_per_mm"]) * l
    return 1e3 * 2 * Q / (math.pi * l * E / (1 - nu * nu))


def read_mesh(mesh_inp: Path):
    from models.fea import hertz_contact as hc

    return hc.read_mesh(mesh_inp)


def contact_faces(elements, coord, on_surface):
    out = []
    for row in elements:
        eid, conn = int(row[0]), row[1:9]
        for label, f in HEX_FACES.items():
            if all(on_surface(*coord[int(conn[k])]) for k in f):
                out.append((eid, label))
    return out


def write_deck(p: dict, mesh_inp: Path, deck: Path, approach) -> dict:
    """The contact deck: one step per approach (mm; a number or an increasing list), each step starting from the last
    converged state, with the reactions and the contact field written at every step end, so the backend can
    interpolate to the target load between the two steps that bracket it. Applies the profile to the roller's nodes (writes the shifted node
    coordinates into the deck's own node block, so mesh.inp stays as meshed)."""
    R, H = float(p["roller_radius_mm"]), float(p["block_depth_mm"])
    E, nu = float(p["youngs_modulus_MPa"]), float(p["poisson_ratio"])
    h0 = float(p["contact_element_size_mm"])
    ids, xyz, elems = read_mesh(mesh_inp)
    coord = {int(i): tuple(q) for i, q in zip(ids, xyz)}
    tol = 1e-6 * R
    reach = float(p.get("contact_reach_mm", 0.25 * R))
    on_arc = lambda x, y, z: abs(math.hypot(x, y - R) - R) < 1e-4 * R and x <= reach  # noqa: E731
    on_top = lambda x, y, z: abs(y) < tol and x <= 1.5 * reach  # noqa: E731
    slave = contact_faces(elems["ROLLER"], coord, on_arc)
    master = contact_faces(elems["BLOCK"], coord, on_top)
    roller_nodes = np.unique(elems["ROLLER"][:, 1:])
    is_roller = np.isin(ids, roller_nodes)
    shifted = xyz.copy()
    shifted[is_roller, 1] += 1e-3 * drop_um(p, xyz[is_roller, 2])
    x, y, z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    sets = {"NALL": ids, "XSYM": ids[np.abs(x) < tol], "ZSYM": ids[np.abs(z) < tol],
            "BOTTOM": ids[np.abs(y + H) < tol], "TOP": ids[is_roller & (np.abs(y - R) < tol)]}
    k_pen = float(p["penalty_stiffness_factor"]) * E / h0
    rows = lambda a: [", ".join(str(int(v)) for v in a[s:s + 12]) for s in range(0, len(a), 12)]  # noqa: E731
    text = Path(mesh_inp).read_text(encoding="latin-1")
    head, rest = text.split("*NODE", 1)
    rest = rest.split("\n", 1)[1]
    k = rest.index("*")
    # 12 significant digits: CalculiX cuts input fields at 20 characters, silently at 21 (a repr such as
    # 8.726785618316274e-05 is read as ...e-0 and the node jumps)
    node_block = "*NODE\n" + "\n".join(f"{int(n)}, {float(a):.12g}, {float(b):.12g}, {float(c):.12g}"
                                       for n, (a, b, c) in zip(ids, shifted)) + "\n"
    (deck.parent / "mesh_profiled.inp").write_text(head + node_block + rest[k:], encoding="latin-1")
    lines = ["*INCLUDE, INPUT=mesh_profiled.inp"]
    for name, arr in sets.items():
        lines += [f"*NSET, NSET={name}"] + rows(arr)
    lines += ["*SURFACE, NAME=SROLL"] + [f"{e}, {f}" for e, f in slave]
    lines += ["*SURFACE, NAME=SBLOCK"] + [f"{e}, {f}" for e, f in master]
    lines += ["*MATERIAL, NAME=STEEL", "*ELASTIC", f"{E!r}, {nu!r}",
              "*SOLID SECTION, ELSET=BLOCK, MATERIAL=STEEL", "*SOLID SECTION, ELSET=ROLLER, MATERIAL=STEEL",
              "*CONTACT PAIR, INTERACTION=SI1, TYPE=SURFACE TO SURFACE", "SROLL, SBLOCK",
              "*SURFACE INTERACTION, NAME=SI1", "*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=LINEAR", f"{k_pen!r}, 1.0",
              "*BOUNDARY", "XSYM, 1, 1, 0.", "ZSYM, 3, 3, 0.", "BOTTOM, 2, 2, 0.",
              ]
    approaches = [float(a) for a in (approach if isinstance(approach, (list, tuple)) else [approach])]
    for k, a in enumerate(approaches):
        first = k == 0
        lines += ["*STEP, INC=1000", "*STATIC", "0.1, 1.0, 1e-6, 0.25" if first else "0.5, 1.0, 1e-6, 1.0",
                  "*BOUNDARY", f"TOP, 2, 2, {-a!r}",
                  "*NODE FILE, FREQUENCY=10000", "U", "*EL FILE, FREQUENCY=10000", "S",
                  "*CONTACT FILE, FREQUENCY=10000", "CSTR, CDIS",
                  "*NODE PRINT, NSET=TOP, TOTALS=ONLY", "RF", "*NODE PRINT, NSET=BOTTOM, TOTALS=ONLY", "RF",
                  "*END STEP"]
    deck.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"nodes": int(len(ids)), "roller_elements": int(len(elems["ROLLER"])),
            "block_elements": int(len(elems["BLOCK"])), "slave_faces": len(slave), "master_faces": len(master),
            "penalty_N_per_mm3": k_pen, "max_drop_um": float(drop_um(p, xyz[is_roller, 2]).max()),
            "target_quarter_load_N": float(p["line_load_N_per_mm"]) * float(p["roller_length_mm"]) / 4,
            "approaches_mm": approaches}

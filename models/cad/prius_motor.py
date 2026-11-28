"""The 2004 Prius traction motor (study 20 on the site, study 7 in the repo) as a detailed part set in CadQuery: the
stator core with its mounting ears, edge notches and 48 slots, the slot windings and end windings, the rotor core with
its V pockets and hub keys, and the 16 magnets.

Sources (the client data pack, validation/motor_ornl/CLIENT_DATA.md):
- Cross-section: revision 5, the analysed model (stator and rotor outlines, the 48 slots, the traced V pockets, the
  18.9 x 6.5 mm magnets, the winding zones). Exported from Pyleecan by scripts/export_motor_elmer.py; one slot pitch
  and one pole are kept in models/cad/prius_rev5_section.json (`python -m models.cad.prius_motor section <export>`),
  so this module and its tests need no Pyleecan.
- The features the 2D model leaves out, from the client's lamination drawing (ORNL/TM-2005/33 Fig. 21), measured by
  scripts/motor_drawing_stator.py into validation/motor_ornl/drawing_stator/drawing_stator.json: three mounting ears
  (hole 0.360 in and root relief R0.234 in as dimensioned; hole position, end radius, flank angle and relief depth
  measured), six notches 0.474 x 0.094 in with R0.109 in floor corners and three 0.230 x 0.080 in (as dimensioned,
  positions measured), all on tooth centres every 30 deg; two hub keys on the rotor bore, 4.152 in across (as
  dimensioned; width measured). The audit's "four keys" (teardown) is not what the drawing shows; the drawing is used.
- Stack lengths from the bill of materials (ORNL/TM-2010/253 Table 2.7): stator 84.0 mm, rotor 83.6 mm, magnets
  83.1 mm (the 2D model used 83.82 mm for both cores).
- End windings: the 24 coils' end turns at both ends, wired as the analysed model's single-layer winding (the
  section's slot_phases; 8 coils per phase in series, BOM), each outer coil's crown at the teardown's 1.5 in
  extension (TM-2004/137 p. 7; the machine file's 19.37 mm Lewout, which an earlier ring used, is half that). The
  coils' arrangement (concentric pairs, three radial tiers, rounded-rectangle turns) is [synthetic]: the data does
  not give it. Checked against the BOM's 6.8 kg of copper and the efficiency study's 120.6 mm end connection.
Not drawn: the shaft and hub (no drawing; the BOM rotor mass includes them), the rotor end plates, the transaxle case
the motor bolts into through its ears.

Axes (mm): z along the shaft, the stacks centred on z = 0. Angles in the model's frame (Pyleecan's): the stator's
slot 0 is centred at 3.75 deg, so tooth centres sit at 7.5 k deg; the drawing's slots sit at 7.5 k deg, so its
features at 3.75 + 30 k deg (tooth centres) are placed at 7.5 + 30 k deg here. The rotor's frame is the drawing's
(the pocket outline matched it at 0.0 deg, validation/motor_ornl/drawing_stops/drawing_stops.json).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).resolve().parent
SECTION = HERE / "prius_rev5_section.json"
IN = 25.4
DENSITY = {"lamination": 7650.0, "magnet": 7550.0, "copper": 8960.0}   # kg/m^3: M330-35A stand-in; BOM magnet 77 g / 10.2 cm^3

DESIGNS = {"rev5": {
    "stator_stack": 84.0, "rotor_stack": 83.6, "magnet_length": 83.1,            # BOM
    # stator outer features (drawing): angles of the 12 tooth-centred positions, in the model's frame
    "ears_deg": (97.5, 217.5, 337.5),
    "large_notches_deg": (7.5, 67.5, 127.5, 187.5, 247.5, 307.5),
    "small_notches_deg": (37.5, 157.5, 277.5),
    "ear_hole_d": 0.360 * IN,            # dimensioned (measured 9.10-9.17)
    "ear_hole_r": 138.53,                # measured: 138.39 / 138.59 / 138.60
    "ear_end_r": 8.91,                   # measured: 8.906 / 8.911 / 8.920 about the hole centre
    "ear_flank_deg": 30.0,               # measured 29.1-31.3 from the axis; flanks tangent to the end arc
    "relief_r": 0.234 * IN,              # dimensioned
    "relief_depth": 1.2,                 # measured 1.06-1.29 below the outer edge
    "notch_small": (0.230 * IN, 0.080 * IN),               # width, depth (dimensioned)
    "notch_large": (0.474 * IN, 0.094 * IN, 0.109 * IN),   # width, depth, floor corner radius (dimensioned)
    # rotor hub keys (drawing)
    "keys_deg": (90.0, 270.0),
    "key_top_r": 4.152 / 2 * IN,         # dimensioned
    "key_w": 5.04,                       # measured 5.038 (both keys)
    # end windings
    "end_extension": 1.5 * IN,           # teardown (TM-2004/137 p. 7): "end winding extensions per side is approximately 1.5 in"
    "end_corner": 1.6,                   # [synthetic] the outer coil's corner radius in bundle widths (feasible 1.5-2.06)
    "turns_per_coil": 9, "strands": 13, "strand_d": 0.912,   # BOM: 9 turns, 13 wires of AWG 19 in parallel
}}


# ------------------------------------------------------------------------------------------------ section data

def write_section(export_json: str, out: str | Path = SECTION) -> dict:
    """Keep one slot pitch and one pole of a scripts/export_motor_elmer.py export, in mm."""
    g = json.loads(Path(export_json).read_text(encoding="utf-8"))
    mm = lambda p: [round(p[0] * 1e3, 9), round(p[1] * 1e3, 9)]  # noqa: E731

    def edge(e):
        d = {"kind": e["kind"], "b": mm(e["b"]), "e": mm(e["e"])}
        if e["kind"] == "arc":
            d.update(c=mm(e["c"]), angle=e["angle"])
        return d

    st = next(s for s in g["surfaces"] if s["kind"] == "stator_lam")
    inner = st["loops"][1]
    pitch = [edge(e) for e in inner[1:9]]            # slot 0's seven edges, then the bore arc to slot 1
    wind = next(s for s in g["surfaces"] if s["kind"] == "winding" and s["label"].endswith("T0-S0"))
    pole = [s for s in g["surfaces"] if s["side"] == "rotor" and s["kind"] in ("void", "magnet") and s["label"].endswith("-S0")]
    d = g["dims"]
    sec = {"source": "revision 5 (models/motor/Toyota_Prius_ORNL_rev5centre.json) via scripts/export_motor_elmer.py",
           "stator_Rext": d["stator_Rext"] * 1e3, "stator_Rint": d["stator_Rint"] * 1e3,
           "rotor_Rext": d["rotor_Rext"] * 1e3, "rotor_Rint": d["rotor_Rint"] * 1e3, "slots": d["slots"],
           "poles": 2 * d["pole_pairs"], "stator_pitch_edges": pitch,
           "winding_edges": [edge(e) for e in wind["loops"][0]],
           "pole_voids": [[edge(e) for e in s["loops"][0]] for s in pole if s["kind"] == "void"],
           "pole_magnets": [[edge(e) for e in s["loops"][0]] for s in pole if s["kind"] == "magnet"]}
    # the winding layout: each slot's phase and the sign of its turns (slot k centred at 3.75 + 7.5 k deg)
    zones = {int(s["label"].rsplit("-S", 1)[1]): s for s in g["surfaces"] if s["kind"] == "winding"}
    sec["slot_phases"] = ["ABC"[zones[k]["phase"]] + ("+" if zones[k]["turns"] > 0 else "-") for k in sorted(zones)]
    sec["turns_per_slot"] = sorted({abs(s["turns"]) for s in zones.values()})
    Path(out).write_text(json.dumps(sec, indent=1) + "\n", encoding="utf-8")
    return sec


def section() -> dict:
    return json.loads(SECTION.read_text(encoding="utf-8"))


# ------------------------------------------------------------------------------------------------ 2D geometry
# An edge is ("line", a, b) or ("arc", a, m, b) with points as (x, y) tuples; m is a point on the arc between a and b.

def _rot(p, deg):
    t = math.radians(deg)
    return (p[0] * math.cos(t) - p[1] * math.sin(t), p[0] * math.sin(t) + p[1] * math.cos(t))


def _rot_edge(e, deg):
    return (e[0],) + tuple(_rot(p, deg) for p in e[1:])


def _from_json(e) -> tuple:
    a, b = tuple(e["b"]), tuple(e["e"])
    if e["kind"] == "seg":
        return ("line", a, b)
    c = e["c"]
    m = _rot((a[0] - c[0], a[1] - c[1]), math.degrees(e["angle"]) / 2)
    return ("arc", a, (c[0] + m[0], c[1] + m[1]), b)


def _arc_through(c, r, a0, a1):
    """Arc about c of radius r from angle a0 to a1 (radians, either direction)."""
    p = lambda a: (c[0] + r * math.cos(a), c[1] + r * math.sin(a))  # noqa: E731
    return ("arc", p(a0), p(0.5 * (a0 + a1)), p(a1))


def _circle_centre(a, m, b):
    ax, ay = a
    bx, by = m
    cx, cy = b
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    return ux, uy


def loop_area(edges) -> float:
    """Signed area of a closed loop of lines and arcs (Green's theorem: the chord polygon plus each arc's circular
    segment, signed by the arc's turning direction). Exact, and independent of OpenCASCADE."""
    A = 0.0
    for e in edges:
        a, b = e[1], e[-1]
        A += 0.5 * (a[0] * b[1] - b[0] * a[1])
        if e[0] == "arc":
            m = e[2]
            c = _circle_centre(a, m, b)
            r = math.hypot(a[0] - c[0], a[1] - c[1])
            t0, tm, t1 = (math.atan2(p[1] - c[1], p[0] - c[0]) for p in (a, m, b))
            # sweep from a to b through m
            d1 = (tm - t0) % (2 * math.pi)
            d2 = (t1 - t0) % (2 * math.pi)
            sweep = d2 if d1 < d2 else d2 - 2 * math.pi
            A += 0.5 * r * r * (sweep - math.sin(sweep))
    return A


def _wire(edges) -> cq.Wire:
    out = []
    for e in edges:
        v = [cq.Vector(p[0], p[1], 0) for p in e[1:]]
        out.append(cq.Edge.makeLine(*v) if e[0] == "line" else cq.Edge.makeThreePointArc(*v))
    return cq.Wire.assembleEdges(out)


# ------------------------------------------------------------------------------------------------ stator outline

def _local(p, deg):
    """A point given in a feature's local frame (x along its axis, outward; y counter-clockwise) to global."""
    return _rot(p, deg)


def notch_edges(D, kind, deg, R):
    """Edges of a notch cut into the outer circle, in the counter-clockwise direction, and its OD end angles."""
    if kind == "small":
        w, d = D["notch_small"]
        r = 0.0
    else:
        w, d, r = D["notch_large"]
    x0 = math.sqrt(R * R - w * w / 4)
    xf = R - d
    pts = []
    if r == 0.0:
        loc = [("line", (x0, -w / 2), (xf, -w / 2)), ("line", (xf, -w / 2), (xf, w / 2)), ("line", (xf, w / 2), (x0, w / 2))]
    else:
        s = r / math.sqrt(2)
        loc = [("line", (x0, -w / 2), (xf + r, -w / 2)),
               ("arc", (xf + r, -w / 2), (xf + r - s, -w / 2 + r - s), (xf, -w / 2 + r)),
               ("line", (xf, -w / 2 + r), (xf, w / 2 - r)),
               ("arc", (xf, w / 2 - r), (xf + r - s, w / 2 - r + s), (xf + r, w / 2)),
               ("line", (xf + r, w / 2), (x0, w / 2))]
    pts = [(e[0],) + tuple(_local(p, deg) for p in e[1:]) for e in loc]
    half = math.degrees(math.asin(w / 2 / R))
    return pts, deg - half, deg + half


def ear_geometry(D, R):
    """The ear in its local frame: hole centre, end circle, flank tangent points, relief circle centres and the points
    where each relief meets the outer circle (the +y side; the -y side mirrors it)."""
    rh, Re, Rr = D["ear_hole_r"], D["ear_end_r"], D["relief_r"]
    al = math.radians(D["ear_flank_deg"])
    n = (math.sin(al), math.cos(al))                    # outward normal of the +y flank
    T = (rh + Re * n[0], Re * n[1])                     # flank tangent point on the end circle
    # relief centre C: distance Re + Rr from the hole centre along n (tangent to the flank, outside the tab), and
    # |C| = R - depth + Rr (its innermost point at the relief depth). Solve by bisection along the flank direction.
    rho = R - D["relief_depth"] + Rr
    dvec = (math.cos(al), -math.sin(al))                # along the flank, outward
    base = (rh + (Re + Rr) * n[0], (Re + Rr) * n[1])

    def f(s):
        return math.hypot(base[0] + s * dvec[0], base[1] + s * dvec[1]) - rho

    lo, hi = -40.0, 0.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        lo, hi = (lo, mid) if f(lo) * f(mid) <= 0 else (mid, hi)
    s = 0.5 * (lo + hi)
    C = (base[0] + s * dvec[0], base[1] + s * dvec[1])
    F = (C[0] - Rr * n[0], C[1] - Rr * n[1])            # relief tangent point on the flank
    # relief meets the outer circle (the far side, larger y)
    cr = math.hypot(*C)
    phi = math.atan2(C[1], C[0])
    cosg = (cr * cr + R * R - Rr * Rr) / (2 * cr * R)
    A = (R * math.cos(phi + math.acos(cosg)), R * math.sin(phi + math.acos(cosg)))
    return {"hole": (rh, 0.0), "T": T, "C": C, "F": F, "A": A, "tip_radius": rh + Re,
            "flank_y_at_od": F[1] + (F[0] - R) * math.tan(al) if F[0] > R else None}


def ear_edges(D, deg, R):
    g = ear_geometry(D, R)
    m = lambda p: (p[0], -p[1])  # noqa: E731
    Rr, rh, Re = D["relief_r"], D["ear_hole_r"], D["ear_end_r"]
    C, F, T, A = g["C"], g["F"], g["T"], g["A"]
    Cm, Fm, Tm, Am = m(C), m(F), m(T), m(A)

    def relief(c, p0, p1):
        a0 = math.atan2(p0[1] - c[1], p0[0] - c[0])
        a1 = math.atan2(p1[1] - c[1], p1[0] - c[0])
        low = math.atan2(-c[1], -c[0])                  # the relief's innermost point lies on the arc
        # choose the direction from a0 to a1 that passes through 'low'
        ccw = (a1 - a0) % (2 * math.pi)
        through = (low - a0) % (2 * math.pi) < ccw
        if not through:
            ccw -= 2 * math.pi
        return _arc_through(c, Rr, a0, a0 + ccw)

    loc = [relief(Cm, Am, Fm), ("line", Fm, Tm), ("arc", Tm, (rh + Re, 0.0), T), ("line", T, F), relief(C, F, A)]
    pts = [(e[0],) + tuple(_local(p, deg) for p in e[1:]) for e in loc]
    half = math.degrees(math.atan2(A[1], A[0]))
    return pts, deg - half, deg + half


def stator_outer_edges(D, sec):
    R = sec["stator_Rext"]
    feats = ([("ear", a) for a in D["ears_deg"]] + [("large", a) for a in D["large_notches_deg"]]
             + [("small", a) for a in D["small_notches_deg"]])
    built = []
    for kind, a in sorted(feats, key=lambda t: t[1]):
        e, a0, a1 = ear_edges(D, a, R) if kind == "ear" else notch_edges(D, kind, a, R)
        built.append((a0, a1, e))
    edges = []
    for i, (a0, a1, e) in enumerate(built):
        edges += e
        b0 = built[(i + 1) % len(built)][0] + (360.0 if i == len(built) - 1 else 0.0)
        edges.append(_arc_through((0.0, 0.0), R, math.radians(a1), math.radians(b0)))
    # snap: each edge starts where the previous ended (feature ends lie on the circle by construction)
    return edges


def stator_inner_edges(sec):
    pitch = [_from_json(e) for e in sec["stator_pitch_edges"]]
    return [_rot_edge(e, 360.0 / sec["slots"] * k) for k in range(sec["slots"]) for e in pitch]


def hole_edges(D, deg):
    c = _local((D["ear_hole_r"], 0.0), deg)
    r = D["ear_hole_d"] / 2
    return [_arc_through(c, r, 0.0, math.pi), _arc_through(c, r, math.pi, 2 * math.pi)]


def stator_section_area(D, sec) -> dict:
    """Exact areas (mm^2) of the stator lamination section and its parts, by loop_area()."""
    outer = loop_area(stator_outer_edges(D, sec))
    inner = loop_area(stator_inner_edges(sec))
    holes = sum(loop_area(hole_edges(D, a)) for a in D["ears_deg"])
    R = sec["stator_Rext"]
    return {"outer": outer, "inner": inner, "holes": holes, "lamination": abs(outer) - abs(inner) - abs(holes),
            "plain_outer_circle": math.pi * R * R}


# ------------------------------------------------------------------------------------------------ rotor outline

def rotor_inner_edges(D, sec):
    """The rotor bore with its keys (counter-clockwise)."""
    Rb, Rk, w = sec["rotor_Rint"], D["key_top_r"], D["key_w"]
    xb = math.sqrt(Rb * Rb - w * w / 4)
    half = math.degrees(math.asin(w / 2 / Rb))
    keys = sorted(D["keys_deg"])
    edges = []
    for i, a in enumerate(keys):
        loc = [("line", (xb, -w / 2), (Rk, -w / 2)), ("line", (Rk, -w / 2), (Rk, w / 2)), ("line", (Rk, w / 2), (xb, w / 2))]
        edges += [(e[0],) + tuple(_local(p, a) for p in e[1:]) for e in loc]
        nxt = keys[(i + 1) % len(keys)] + (360.0 if i == len(keys) - 1 else 0.0)
        edges.append(_arc_through((0.0, 0.0), Rb, math.radians(a + half), math.radians(nxt - half)))
    return edges


def key_area(D, sec) -> float:
    """Hand area of one key: the strip from its flat top to the bore circle, |y| <= w / 2 (exact integral)."""
    Rb, Rk, w = sec["rotor_Rint"], D["key_top_r"], D["key_w"]
    h = w / 2
    integral = h * math.sqrt(Rb * Rb - h * h) + Rb * Rb * math.asin(h / Rb)   # integral of sqrt(Rb^2 - y^2), -h..h
    return integral - w * Rk


def pole_loops(sec, k):
    deg = 360.0 / sec["poles"] * k
    rot = lambda loop: [_rot_edge(_from_json(e), deg) for e in loop]  # noqa: E731
    return [rot(l) for l in sec["pole_voids"]], [rot(l) for l in sec["pole_magnets"]]


# ------------------------------------------------------------------------------------------------ solids

def _prism(outer_edges, inner_loops, z0, length) -> cq.Solid:
    face = cq.Face.makeFromWires(_wire(outer_edges), [_wire(l) for l in inner_loops])
    return cq.Solid.extrudeLinear(face.moved(cq.Location(cq.Vector(0, 0, z0))), cq.Vector(0, 0, length))


def build_stator(D, sec) -> cq.Solid:
    L = D["stator_stack"]
    holes = [hole_edges(D, a) for a in D["ears_deg"]]
    return _prism(stator_outer_edges(D, sec), [stator_inner_edges(sec)] + holes, -L / 2, L)


def build_windings(D, sec) -> list[cq.Solid]:
    L = D["stator_stack"]
    w0 = [_from_json(e) for e in sec["winding_edges"]]
    return [_prism([_rot_edge(e, 360.0 / sec["slots"] * k) for e in w0], [], -L / 2, L) for k in range(sec["slots"])]


def winding_radii(sec) -> tuple[float, float]:
    pts = [p for e in sec["winding_edges"] for p in (e["b"], e["e"])]
    r_in = min(math.hypot(*p) for p in pts)
    arc = next(e for e in sec["winding_edges"] if e["kind"] == "arc")
    c = arc["c"]
    r_out = math.hypot(*c) + math.hypot(arc["b"][0] - c[0], arc["b"][1] - c[1])
    return r_in, r_out


# ------------------------------------------------------------------------------------------------ end windings
# The winding is the analysed model's (the section's slot_phases: A+ A+ C- C- B+ B+ A- A- C+ C+ B- B- per pole pair,
# 9 turns per slot): single layer, 24 coils, 8 per phase in series as the BOM gives. Each pole pair holds three
# phase groups, each joining a two-slot belt to the opposite belt six slots on. What the data does not give, and is
# drawn here as a plausible layout [synthetic]: each group as two concentric coils (outer s -> s + 7, inner
# s + 1 -> s + 6; mean span 6), the three groups of a pole pair in three radial tiers (they overlap in angle, so they
# cannot share a radius), the end turn's shape (straight legs, a rounded-rectangle top) and its corner radius.
# From the data: the extension, 1.5 in per side (teardown), reached by every outer coil's crown.

def slot_deg(sec, k: float) -> float:
    """Centre angle of slot k (the model's frame: slot 0 at half a pitch)."""
    return 360.0 / sec["slots"] * (k + 0.5)


def zone_area(sec) -> float:
    return abs(loop_area([_from_json(e) for e in sec["winding_edges"]]))


def coil_layout(sec) -> list[dict]:
    """The 24 coils, from the slot phases: groups start at the first three belts of each pole pair."""
    ph, n = sec["slot_phases"], sec["slots"]
    per = 2 * n // sec["poles"]                         # slots per pole pair (12)
    coils = []
    for s in range(0, n, 2):
        if s % per >= per // 2:
            continue
        back = (s + per // 2) % n
        assert ph[s] == ph[s + 1] and ph[back] == ph[back + 1] and ph[s][0] == ph[back][0] and ph[s] != ph[back]
        for role, a, b in (("outer", s, s + per // 2 + 1), ("inner", s + 1, s + per // 2)):
            coils.append({"phase": ph[s][0], "tier": (s % per) // 2, "sector": s // per, "role": role,
                          "slots": (a, b), "span": b - a})
    return coils


def end_tiers(D, sec) -> list[dict]:
    """The three tiers' radial bands, inner to outer from the slot zone's inner radius. A coil's bundle keeps the
    slot zone's area A [synthetic: the end region's packing is not given]; across the turn it is one slot pitch wide
    at the band's mean radius (w = alpha r_t, so a group's coil sides touch), radially d = A / w."""
    A, alpha = zone_area(sec), 2 * math.pi / sec["slots"]
    r = winding_radii(sec)[0]
    out = []
    for _ in range(3):
        d = (-alpha * r + math.sqrt((alpha * r) ** 2 + 2 * alpha * A)) / alpha     # alpha d (r + d / 2) = A
        out.append({"r_in": r, "r_out": r + d, "r_t": r + d / 2, "d": d, "w": alpha * (r + d / 2)})
        r += d
    return out


def end_turn_shape(D, sec, coil) -> dict:
    """The end turn's centreline in its tier's unrolled surface (s = r_t theta, z from the stack face): legs at the
    two slot centres, corners of radius R, a straight top; the outer coil's outer edge at the extension, the inner
    coil nested one bundle width inside (same corner centres). L is the centreline length."""
    T = end_tiers(D, sec)[coil["tier"]]
    w = T["w"]
    H, R = D["end_extension"] - w / 2, D["end_corner"] * w
    if coil["role"] == "inner":
        H, R = H - w, R - w
    S = coil["span"] * w
    return {"H": H, "R": R, "S": S, "w": w, "L": 2 * (H - R) + (S - 2 * R) + math.pi * R, "tier": T}


def _end_turn_face(r_face, r_t, sL, S, z0, H, R, w) -> cq.Face:
    """The turn's region on the cylinder r_face, its (u, v) = (s / r_t, z): the band of width w about the
    centreline, bounded by lines (axial lines and circles on the cylinder) and the corners, circles of radius
    R +- w / 2 in (s, z) and so ellipses in (u, v) (semi-axes rho along z, rho / r_t along u)."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire
    from OCP.BRepLib import BRepLib
    from OCP.GCE2d import GCE2d_MakeSegment
    from OCP.Geom import Geom_CylindricalSurface
    from OCP.Geom2d import Geom2d_Ellipse, Geom2d_TrimmedCurve
    from OCP.gp import gp_Ax2d, gp_Ax3, gp_Dir, gp_Dir2d, gp_Pnt, gp_Pnt2d

    surf = Geom_CylindricalSurface(gp_Ax3(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1), gp_Dir(1, 0, 0)), r_face)
    sR, zc, h = sL + S, z0 + H - R, w / 2
    edges = []

    def seg(p, q):
        c = GCE2d_MakeSegment(gp_Pnt2d(p[0] / r_t, p[1]), gp_Pnt2d(q[0] / r_t, q[1])).Value()
        edges.append(BRepBuilderAPI_MakeEdge(c, surf).Edge())

    def arc(cs, rho, a0, a1):
        # P(t) = C + rho cos t (0, 1) + (rho / r_t) sin t (-1, 0): s = cs - rho sin t, z = zc + rho cos t, so the
        # (s, z) angle a is t + 90 deg
        e = Geom2d_Ellipse(gp_Ax2d(gp_Pnt2d(cs / r_t, zc), gp_Dir2d(0, 1)), rho, rho / r_t, True)
        t0, t1 = a0 - math.pi / 2, a1 - math.pi / 2
        tc = Geom2d_TrimmedCurve(e, min(t0, t1), max(t0, t1))
        if t0 > t1:
            tc.Reverse()
        edges.append(BRepBuilderAPI_MakeEdge(tc, surf).Edge())

    seg((sL - h, z0), (sL - h, zc))                                  # outer edge: left leg, over the top, down
    arc(sL + R, R + h, math.pi, math.pi / 2)
    seg((sL + R, z0 + H + h), (sR - R, z0 + H + h))
    arc(sR - R, R + h, math.pi / 2, 0.0)
    seg((sR + h, zc), (sR + h, z0))
    seg((sR + h, z0), (sR - h, z0))                                  # the right leg's foot on the stack face
    seg((sR - h, z0), (sR - h, zc))                                  # inner edge back
    arc(sR - R, R - h, 0.0, math.pi / 2)
    seg((sR - R, z0 + H - h), (sL + R, z0 + H - h))
    arc(sL + R, R - h, math.pi / 2, math.pi)
    seg((sL + h, zc), (sL + h, z0))
    seg((sL + h, z0), (sL - h, z0))                                  # the left leg's foot
    mw = BRepBuilderAPI_MakeWire()
    for e in edges:
        BRepLib.BuildCurves3d_s(e)
        mw.Add(e)
    return cq.Face(BRepBuilderAPI_MakeFace(surf, mw.Wire(), True).Face())


def build_end_turn(D, sec, coil) -> cq.Solid:
    """The coil's end turn at the +z end: its (theta, z) region on the tier's inner cylinder, thickened radially by
    the band depth (offset along the cylinder's normal, so the side walls are radial)."""
    sh = end_turn_shape(D, sec, coil)
    T = sh["tier"]
    sL = T["r_t"] * math.radians(slot_deg(sec, coil["slots"][0]))
    face = _end_turn_face(T["r_in"], T["r_t"], sL, sh["S"], D["stator_stack"] / 2, sh["H"], sh["R"], sh["w"])
    return face.thicken(T["d"])


def end_turn_volume_hand(D, sec, coil) -> float:
    """Exact for the radially swept region: (r_out^2 - r_in^2) / 2 times its (theta, z) area, which is (its (s, z)
    area w L) / r_t; with r_t the band's mean radius, d w L. w L: a band of constant width about lines and arcs."""
    sh = end_turn_shape(D, sec, coil)
    return sh["tier"]["d"] * sh["w"] * sh["L"]


def turn_over_axis(sec, coil) -> tuple:
    """The radial line through the turn's middle: the turn is symmetric about it, so turning it over 180 deg about
    that line gives its mirror image at the other end (and a rigid placement the STEP can instance)."""
    a = math.radians(slot_deg(sec, sum(coil["slots"]) / 2))
    return (math.cos(a), math.sin(a), 0.0)


def build_end_turns(D, sec) -> list[dict]:
    """Both ends' 48 end turns: the +z turn of each coil and, at -z, the same turn turned over."""
    out = []
    for c in coil_layout(sec):
        s = build_end_turn(D, sec, c)
        out += [{"coil": c, "end": "a", "solid": s},
                {"coil": c, "end": "b", "solid": s.rotate((0, 0, 0), turn_over_axis(sec, c), 180.0)}]
    return out


def copper(D, sec) -> dict:
    """Copper from the turns (BOM: 9 turns per coil, 13 wires of AWG 19 in parallel): each coil's mean turn is two
    stack lengths plus its two end-turn centrelines. Leads and the jumpers between coils are not drawn."""
    a = math.pi / 4 * D["strand_d"] ** 2
    n = D["turns_per_coil"] * D["strands"]
    coils = coil_layout(sec)
    ends = [end_turn_shape(D, sec, c)["L"] for c in coils]
    vol = sum(n * a * (2 * D["stator_stack"] + 2 * L) for L in ends)
    return {"kg": vol * 1e-9 * DENSITY["copper"], "mean_end_turn_mm": sum(ends) / len(ends),
            "mean_turn_mm": 2 * D["stator_stack"] + 2 * sum(ends) / len(ends), "copper_fill_of_zone": n * a / zone_area(sec),
            "end_turn_mm_by_tier": {t: sum(L for L, c in zip(ends, coils) if c["tier"] == t) / 8 for t in range(3)}}


def build_rotor(D, sec) -> cq.Solid:
    L = D["rotor_stack"]
    R = sec["rotor_Rext"]
    outer = [_arc_through((0.0, 0.0), R, 0.0, math.pi), _arc_through((0.0, 0.0), R, math.pi, 2 * math.pi)]
    core = _prism(outer, [rotor_inner_edges(D, sec)], -L / 2, L)
    pockets = []
    for k in range(sec["poles"]):
        voids, mags = pole_loops(sec, k)
        for loop in voids + mags:
            pockets.append(_prism(loop, [], -L / 2 - 1, L + 2))
    tool = pockets[0].fuse(*pockets[1:]).clean()
    return core.cut(tool).clean()


def build_magnets(D, sec) -> list[cq.Solid]:
    Lm = D["magnet_length"]
    out = []
    for k in range(sec["poles"]):
        _, mags = pole_loops(sec, k)
        out += [_prism(loop, [], -Lm / 2, Lm) for loop in mags]
    return out


def build(design: str = "rev5") -> dict:
    D, sec = DESIGNS[design], section()
    return {"stator": build_stator(D, sec), "windings": build_windings(D, sec), "end_turns": build_end_turns(D, sec),
            "rotor": build_rotor(D, sec), "magnets": build_magnets(D, sec)}


def masses(parts: dict) -> dict:
    """kg from the solids' volumes (mm^3) and the densities; copper is reported from the turns, not the zones."""
    v = lambda s: s.Volume() * 1e-9  # noqa: E731
    return {"stator_core_kg": v(parts["stator"]) * DENSITY["lamination"],
            "rotor_core_kg": v(parts["rotor"]) * DENSITY["lamination"],
            "magnets_kg": sum(v(m) for m in parts["magnets"]) * DENSITY["magnet"]}


def export(design: str, path: str | Path) -> dict:
    """One STEP assembly. The 48 slot windings, the 48 end turns and the 16 magnets are instances (slot 0's
    winding, the first pole pair's end turns at each end, pole 0's two magnets, placed by rotation), which keeps the
    file small. The end turns sit in one sub-assembly per phase (end_windings_A / _B / _C), named
    end_turn_<end a +z | b -z>_<phase><pole pair>_<outer | inner>."""
    D, sec = DESIGNS[design], section()
    parts = build(design)
    asm = cq.Assembly(name=f"prius_motor_{design}")
    asm.add(parts["stator"], name="stator_core", color=cq.Color(0.55, 0.57, 0.6))
    copper, steel, magnet = cq.Color(0.72, 0.45, 0.2), cq.Color(0.45, 0.47, 0.5), cq.Color(0.25, 0.3, 0.45)
    w0 = parts["windings"][0]
    for k in range(sec["slots"]):
        asm.add(w0, name=f"slot_winding_{k:02d}", color=copper,
                loc=cq.Location(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 360.0 / sec["slots"] * k))
    first = {(t["coil"]["tier"], t["coil"]["role"]): t for t in parts["end_turns"]
             if t["coil"]["sector"] == 0 and t["end"] == "a"}
    pair_deg = 360.0 / (sec["poles"] // 2)
    for ph in "ABC":
        sub = cq.Assembly(name=f"end_windings_{ph}")
        for t in parts["end_turns"]:
            c = t["coil"]
            if c["phase"] != ph:
                continue
            f = first[(c["tier"], c["role"])]
            loc = cq.Location(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), pair_deg * c["sector"])
            if t["end"] == "b":
                loc = loc * cq.Location(cq.Vector(0, 0, 0), cq.Vector(*turn_over_axis(sec, f["coil"])), 180.0)
            sub.add(f["solid"], name=f"end_turn_{t['end']}_{ph}{c['sector']}_{c['role']}", color=copper, loc=loc)
        asm.add(sub, name=f"end_windings_{ph}")
    asm.add(parts["rotor"], name="rotor_core", color=steel)
    per_pole = len(sec["pole_magnets"])
    for k in range(sec["poles"]):
        for j in range(per_pole):
            asm.add(parts["magnets"][j], name=f"magnet_p{k}_{j}", color=magnet,
                    loc=cq.Location(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 360.0 / sec["poles"] * k))
    asm.export(str(path), exportType="STEP")
    return parts


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "section":
        write_section(sys.argv[2])
    else:
        out = Path(__file__).resolve().parents[2] / "portfolio" / "cad" / "prius_motor_rev5.step"
        parts = export("rev5", out)
        cu = copper(DESIGNS["rev5"], section())
        print(out, {k: round(v, 4) for k, v in masses(parts).items()},
              {k: (round(v, 4) if isinstance(v, float) else v) for k, v in cu.items()})

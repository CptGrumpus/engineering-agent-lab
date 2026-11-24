"""Export one pole of a Pyleecan IPM rotor for the CalculiX overspeed model (study 7). Runs in the Pyleecan environment.

usage: <pyleecan python> export_rotor_pole.py <machine.json> <out.json>

Writes, in mm, with the pole axis on +x (Pyleecan's own frame for hole 0):
- rotor_bore_radius_mm, rotor_outer_radius_mm, stack_mm, poles;
- pocket_half: the pocket outline on the y >= 0 side, from the inner apex on the pole axis round to the outer apex on
  the pole axis, as a list of segments ("line" [x0, y0, x1, y1] or "arc" [x0, y0, x1, y1, r] about the origin);
- seat_half: the magnet's seat (the pocket's outer edge the magnet bears on), [x0, y0, x1, y1];
- magnet_half: the magnet's area (mm^2) and centroid (mm);
- materials: lamination and magnet density (kg/m^3), Young's modulus (MPa), Poisson's ratio, from the machine file.
Only HoleM50 (one V per pole, no centre rib) is supported; anything else stops with an error.
"""

from __future__ import annotations

import json
import sys

import numpy as np


def _polygon_area_centroid(z):
    x, y = np.real(z), np.imag(z)
    cr = x * np.roll(y, -1) - np.roll(x, -1) * y
    A = 0.5 * cr.sum()
    return A, (np.sum((x + np.roll(x, -1)) * cr) / (6 * A), np.sum((y + np.roll(y, -1)) * cr) / (6 * A))


TOL = 1e-5   # mm: vertex matching and collinearity on Pyleecan's coordinates (they agree to about 1e-9 mm)


def _edges(sf):
    """A Pyleecan surface's edges in mm: ("line", a, b, None) or ("arc", a, b, radius about the origin)."""
    out = []
    for ln in sf.get_lines():
        a, b = complex(ln.get_begin()) * 1e3, complex(ln.get_end()) * 1e3
        if type(ln).__name__ == "Segment":
            out.append(("line", a, b, None))
        else:
            r = abs(a)
            if abs(abs(b) - r) > TOL or abs(abs(complex(ln.get_center()) * 1e3)) > TOL:
                raise SystemExit(f"{sf.label}: only arcs about the rotor centre are supported")
            out.append(("arc", a, b, r))
    return out


def _clip_upper(edges, label):
    """Clip a line-only closed outline to y >= 0 (the half pole's side)."""
    if any(k != "line" for k, *_ in edges):
        raise SystemExit(f"{label}: a surface across the pole axis must have straight edges only")
    pts = [a for _, a, _, _ in edges]
    out = []
    for i, p in enumerate(pts):
        q = pts[(i + 1) % len(pts)]
        if p.imag >= -TOL:
            out.append(complex(p.real, max(p.imag, 0.0)))
        if (p.imag > TOL and q.imag < -TOL) or (p.imag < -TOL and q.imag > TOL):
            t = p.imag / (p.imag - q.imag)
            out.append(complex(p.real + t * (q.real - p.real), 0.0))
    return [("line", out[i], out[(i + 1) % len(out)], None) for i in range(len(out))]


def _holeud_chain(h):
    """Half-pole pocket outline of a drawn hole (HoleUD: the union of its void and magnet surfaces, revision 5), as
    the HoleM50 chain: inner apex on the pole axis round to the outer apex, the last segment the straight outer edge.
    Edges shared by two surfaces (also partly, along a common line) are interior; the rest is the outline."""
    surfs, mag = [], None
    for sf in h.build_geometry():
        e = _edges(sf)
        ys = [p.imag for _, a, b, _ in e for p in (a, b)]
        if min(ys) >= -TOL:
            surfs.append(e)
            if "HoleMag" in sf.label:
                if mag is not None:
                    raise SystemExit("more than one magnet on the y >= 0 side")
                mag = np.array([a for _, a, _, _ in e])
        elif max(ys) > TOL:
            surfs.append(_clip_upper(e, sf.label))
    if mag is None:
        raise SystemExit("no magnet surface on the y >= 0 side")
    verts = []
    for e in surfs:
        for _, a, b, _ in e:
            for p in (a, b):
                if all(abs(p - v) > TOL for v in verts):
                    verts.append(p)

    def snap(p):
        return min(verts, key=lambda v: abs(v - p))

    count, kept = {}, {}
    for e in surfs:
        for kind, a, b, r in e:
            a, b = snap(a), snap(b)
            pieces = [(a, b)]
            if kind == "line":   # split at every vertex lying on the segment (T-junctions along a shared line)
                d = b - a
                inner = sorted((((v - a) * d.conjugate()).real / abs(d) ** 2, v) for v in verts
                               if abs(((v - a) * d.conjugate()).imag) / abs(d) < TOL
                               and TOL < ((v - a) * d.conjugate()).real / abs(d) < abs(d) - TOL)
                chain = [a] + [v for _, v in inner] + [b]
                pieces = list(zip(chain[:-1], chain[1:]))
            for p, q in pieces:
                key = (kind, frozenset((verts.index(p), verts.index(q))))
                count[key] = count.get(key, 0) + 1
                kept[key] = (kind, p, q, r)
    bound = [kept[k] for k, n in count.items() if n == 1
             and not (abs(kept[k][1].imag) < TOL and abs(kept[k][2].imag) < TOL)]   # drop the pole-axis cut
    axis = sorted({p for _, a, b, _ in bound for p in (a, b) if abs(p.imag) < TOL}, key=lambda z: z.real)
    if len(axis) != 2:
        raise SystemExit(f"expected two pocket apexes on the pole axis, found {len(axis)}")
    cur, seq, left = axis[0], [], list(bound)
    while abs(cur - axis[1]) > TOL:
        nxt = [e for e in left if abs(e[1] - cur) < TOL or abs(e[2] - cur) < TOL]
        if len(nxt) != 1:
            raise SystemExit(f"pocket outline is not a simple chain at {cur * 1e-3} m ({len(nxt)} edges)")
        kind, a, b, r = nxt[0]
        left.remove(nxt[0])
        a, b = (a, b) if abs(a - cur) < TOL else (b, a)
        if seq and kind == "line" and seq[-1][0] == "line" and abs(
                ((b - seq[-1][1]) * (seq[-1][2] - seq[-1][1]).conjugate()).imag) / abs(b - seq[-1][1]) < TOL:
            seq[-1] = ("line", seq[-1][1], b, None)      # collinear with the previous segment: merge
        else:
            seq.append((kind, a, b, r))
        cur = b
    if left:
        raise SystemExit(f"{len(left)} outline edges are not on the chain from apex to apex")
    if seq[-1][0] != "line" or seq[-2][0] != "arc":
        raise SystemExit("the outline must end with the bridge arc and then the straight outer edge to the apex")
    return seq, mag


def _seat_on_outer_edge(seq, mag):
    """The magnet bears on the pocket's outer edge (the last segment, ending at the outer apex): from the apex to the
    projection of the magnet's far end on that edge; the magnet must lie along it."""
    _, p9, apex, _ = seq[-1]
    u = (p9 - apex) / abs(p9 - apex)
    s = ((mag - apex) * u.conjugate()).real
    n = ((mag - apex) * u.conjugate()).imag
    near = np.sort(np.abs(n))[:2]
    if s.min() < -0.5 or s.max() > abs(p9 - apex) + TOL or near.max() > 0.5:
        raise SystemExit(f"the magnet does not lie along the outer edge (s {s.min():.3f}-{s.max():.3f} mm of "
                         f"{abs(p9 - apex):.3f}, offset {near.max():.3f} mm)")
    return apex + u * s.max(), float(near.max())


def main(machine_path: str, out_path: str) -> None:
    from pyleecan.Functions.load import load

    m = load(machine_path)
    r = m.rotor
    h = r.hole[0]
    if type(h).__name__ == "HoleUD":
        return main_holeud(m, h, out_path)
    if type(h).__name__ != "HoleM50" or h.W1 != 0:
        raise SystemExit(f"only HoleM50 without a centre rib, or HoleUD, is supported, got {type(h).__name__}")
    p = {k: complex(v) * 1e3 for k, v in h._comp_point_coordinate().items()}
    c = {k: complex(v.real, -v.imag) for k, v in p.items()}   # Pyleecan's Z points sit at y < 0: mirror to y >= 0
    Rarc = abs(c["Z1"])
    # inner apex on the axis, round the inner side and the end void, back along the seat to the outer apex
    chain = [("line", c["Z7"], c["Z6"]), ("line", c["Z6"], c["Z5"]), ("line", c["Z5"], c["Z4"]),
             ("line", c["Z4"], c["Z3"]), ("line", c["Z3"], c["Z2"]), ("line", c["Z2"], c["Z1"]),
             ("arc", c["Z1"], c["Z9"]), ("line", c["Z9"], c["Z8"])]
    # Pyleecan's own surfaces put the magnet between Z8 (outer apex), Z3 and Z4 on the seat side: check the chain
    # reproduces the hole area it reports (both halves)
    zs = []
    for kind, a, b in chain:
        if kind == "line":
            zs.append(a)
        else:
            t0, t1 = np.angle(a), np.angle(b)
            zs.extend(Rarc * np.exp(1j * np.linspace(t0, t1, 64, endpoint=False)))
    zs.append(c["Z8"])
    A_half, _ = _polygon_area_centroid(np.array(zs))
    A_pyl = h.comp_surface() * 1e6 / 2
    if abs(abs(A_half) - A_pyl) > 1e-3 * A_pyl:
        raise SystemExit(f"pocket outline area {abs(A_half):.3f} mm^2 does not match Pyleecan's {A_pyl:.3f} mm^2")
    mag = None
    for sf in h.build_geometry():
        if "HoleMag" in sf.label:
            pts = [complex(l.get_begin()) * 1e3 for l in sf.get_lines()]
            z = np.array([complex(q.real, abs(q.imag)) for q in pts])
            if np.mean(np.imag(pts)) > 0:          # the y >= 0 magnet as Pyleecan builds it
                A, (cx, cy) = _polygon_area_centroid(z)
                mag = {"area_mm2": abs(A), "centroid_mm": [cx, cy]}
    if mag is None:
        raise SystemExit("no magnet surface on the y >= 0 side")

    def mat(mt):
        st = mt.struct
        return {"name": mt.name, "density_kg_m3": float(st.rho), "youngs_modulus_MPa": float(st.Ex) / 1e6,
                "poisson_ratio": float(st.nu_xy)}

    out = {
        "machine": m.name,
        "rotor_bore_radius_mm": r.Rint * 1e3, "rotor_outer_radius_mm": r.Rext * 1e3, "stack_mm": r.L1 * 1e3,
        "poles": int(2 * m.get_pole_pair_number()),
        "bridge_arc_radius_mm": Rarc,
        "pocket_half": [[kind, a.real, a.imag, b.real, b.imag] + ([Rarc] if kind == "arc" else [])
                        for kind, a, b in chain],
        "pocket_half_area_mm2": abs(A_half), "pocket_area_pyleecan_mm2": h.comp_surface() * 1e6,
        # the magnet bears on the outer edge from the outer apex Z8 to Z8c (Z8 + magnet width W4 along the edge)
        "seat_half": [c["Z8"].real, c["Z8"].imag, c["Z8c"].real, c["Z8c"].imag],
        "magnet_half": mag,
        "lamination": mat(r.mat_type), "magnet": mat(h.magnet_0.mat_type),
    }
    open(out_path, "w", encoding="utf-8").write(json.dumps(out, indent=1))


def _mat(mt):
    st = mt.struct
    return {"name": mt.name, "density_kg_m3": float(st.rho), "youngs_modulus_MPa": float(st.Ex) / 1e6,
            "poisson_ratio": float(st.nu_xy)}


def main_holeud(m, h, out_path: str) -> None:
    r = m.rotor
    seq, mag = _holeud_chain(h)
    arcs = [s for s in seq if s[0] == "arc"]
    if len(arcs) != 1:
        raise SystemExit(f"expected one bridge arc in the half outline, found {len(arcs)}")
    Rarc = arcs[0][3]
    zs = []
    for kind, a, b, _ in seq:
        if kind == "line":
            zs.append(a)
        else:
            zs.extend(Rarc * np.exp(1j * np.linspace(np.angle(a), np.angle(b), 64, endpoint=False)))
    zs.append(seq[-1][2])
    A_half, _ = _polygon_area_centroid(np.array(zs))
    A_pyl = h.comp_surface() * 1e6 / 2
    if abs(abs(A_half) - A_pyl) > 1e-3 * A_pyl:
        raise SystemExit(f"pocket outline area {abs(A_half):.3f} mm^2 does not match Pyleecan's {A_pyl:.3f} mm^2")
    A_m, (cx, cy) = _polygon_area_centroid(mag)
    seat_end, gap = _seat_on_outer_edge(seq, mag)
    apex = seq[-1][2]
    mags = list(h.magnet_dict.values())
    out = {
        "machine": m.name, "hole": "HoleUD",
        "rotor_bore_radius_mm": r.Rint * 1e3, "rotor_outer_radius_mm": r.Rext * 1e3, "stack_mm": r.L1 * 1e3,
        "poles": int(2 * m.get_pole_pair_number()),
        "bridge_arc_radius_mm": Rarc,
        "pocket_half": [[kind, a.real, a.imag, b.real, b.imag] + ([Rarc] if kind == "arc" else [])
                        for kind, a, b, _ in seq],
        "pocket_half_area_mm2": abs(A_half), "pocket_area_pyleecan_mm2": h.comp_surface() * 1e6,
        "seat_half": [apex.real, apex.imag, seat_end.real, seat_end.imag],
        "seat_gap_mm": gap,   # the magnet's offset from the edge it bears on (0.15 mm of polymer in revision 5)
        "magnet_half": {"area_mm2": abs(A_m), "centroid_mm": [cx, cy]},
        "magnet_length_mm": float(getattr(mags[0], "Lmag", r.L1)) * 1e3,
        "lamination": _mat(r.mat_type), "magnet": _mat(mags[0].mat_type),
    }
    open(out_path, "w", encoding="utf-8").write(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

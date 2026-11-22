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


def main(machine_path: str, out_path: str) -> None:
    from pyleecan.Functions.load import load

    m = load(machine_path)
    r = m.rotor
    h = r.hole[0]
    if type(h).__name__ != "HoleM50" or h.W1 != 0:
        raise SystemExit(f"only HoleM50 without a centre rib is supported, got {type(h).__name__} (W1 = {h.W1})")
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


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

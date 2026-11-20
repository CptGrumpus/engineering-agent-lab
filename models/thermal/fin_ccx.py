"""Straight rectangular fin: structured hex mesh and CalculiX heat-transfer deck.

Geometry (SI metres in the deck): x across the thickness t, y across the
width w, z along the fin from the base (z = 0) to the tip (z = L).
C3D8 elements, node (i, j, k) has id 1 + i + (nx+1) (j + (ny+1) k).

Boundary conditions:
  base face z = 0     temperature fixed at base_temperature_C (*BOUNDARY, dof 11)
  x faces, y faces,   film condition h, air_temperature_C (*FILM)
  tip face z = L

C3D8 face numbering (CalculiX manual): F1 1-2-3-4 (z-), F2 5-8-7-6 (z+),
F3 1-5-6-2 (y-), F4 2-6-7-3 (x+), F5 3-7-8-4 (y+), F6 4-8-5-1 (x-).

Outputs: nodal temperatures in the .frd (NT, 6 significant digits), the tip-face
nodal temperatures again in the .dat (NT, 7 significant digits, for the
requirement metric), and the total reaction heat flow of the base node set in
the .dat (RFL, TOTALS=ONLY).
"""

from __future__ import annotations

PARAMS = ("thickness_mm", "width_mm", "length_mm", "conductivity_W_per_mK", "htc_W_per_m2K",
          "base_temperature_C", "air_temperature_C", "element_size_mm")


def mesh_divisions(p: dict) -> tuple[int, int, int]:
    """Elements across thickness, width, length for the target element size."""
    s = float(p["element_size_mm"])
    return tuple(max(1, round(float(p[k]) / s))
                 for k in ("thickness_mm", "width_mm", "length_mm"))


def _node_id(i, j, k, nx, ny):
    return 1 + i + (nx + 1) * (j + (ny + 1) * k)


def write_deck(p: dict) -> str:
    nx, ny, nz = mesh_divisions(p)
    t = float(p["thickness_mm"]) * 1e-3
    w = float(p["width_mm"]) * 1e-3
    L = float(p["length_mm"]) * 1e-3
    k_cond = float(p["conductivity_W_per_mK"])
    h = float(p["htc_W_per_m2K"])
    tb = float(p["base_temperature_C"])
    ta = float(p["air_temperature_C"])

    out = ["*HEADING", "Straight rectangular fin, steady conduction with film convection", "*NODE, NSET=NALL"]
    for k in range(nz + 1):
        z = L * k / nz
        for j in range(ny + 1):
            y = w * j / ny
            for i in range(nx + 1):
                x = t * i / nx
                out.append(f"{_node_id(i, j, k, nx, ny)}, {x:.12e}, {y:.12e}, {z:.12e}")

    out.append("*ELEMENT, TYPE=C3D8, ELSET=EALL")
    faces = {"EXMIN": [], "EXMAX": [], "EYMIN": [], "EYMAX": [], "ETIP": []}
    eid = 0
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                eid += 1
                n1 = _node_id(i, j, k, nx, ny)
                n2 = _node_id(i + 1, j, k, nx, ny)
                n3 = _node_id(i + 1, j + 1, k, nx, ny)
                n4 = _node_id(i, j + 1, k, nx, ny)
                n5, n6, n7, n8 = (n + (nx + 1) * (ny + 1) for n in (n1, n2, n3, n4))
                out.append(f"{eid}, {n1}, {n2}, {n3}, {n4}, {n5}, {n6}, {n7}, {n8}")
                if i == 0:
                    faces["EXMIN"].append(eid)
                if i == nx - 1:
                    faces["EXMAX"].append(eid)
                if j == 0:
                    faces["EYMIN"].append(eid)
                if j == ny - 1:
                    faces["EYMAX"].append(eid)
                if k == nz - 1:
                    faces["ETIP"].append(eid)

    def id_lines(ids):
        return [", ".join(str(n) for n in ids[a:a + 16]) for a in range(0, len(ids), 16)]

    base = [_node_id(i, j, 0, nx, ny) for j in range(ny + 1) for i in range(nx + 1)]
    tip = [_node_id(i, j, nz, nx, ny) for j in range(ny + 1) for i in range(nx + 1)]
    out.append("*NSET, NSET=NBASE")
    out += id_lines(base)
    out.append("*NSET, NSET=NTIP")
    out += id_lines(tip)
    for name, ids in faces.items():
        out.append(f"*ELSET, ELSET={name}")
        out += id_lines(ids)

    out += ["*MATERIAL, NAME=AL6061", "*CONDUCTIVITY", f"{k_cond:.12e}",
            "*SOLID SECTION, ELSET=EALL, MATERIAL=AL6061",
            # initial temperature on every node (NALL is defined on the *NODE card)
            "*INITIAL CONDITIONS, TYPE=TEMPERATURE", f"NALL, {tb:.12e}"]
    out += ["*STEP", "*HEAT TRANSFER, STEADY STATE", "1., 1.",
            "*BOUNDARY", f"NBASE, 11, 11, {tb:.12e}", "*FILM"]
    face_label = {"EXMIN": "F6", "EXMAX": "F4", "EYMIN": "F3", "EYMAX": "F5", "ETIP": "F2"}
    for name, label in face_label.items():
        out.append(f"{name}, {label}, {ta:.12e}, {h:.12e}")
    out += ["*NODE FILE", "NT", "*NODE PRINT, NSET=NBASE, TOTALS=ONLY", "RFL",
            "*NODE PRINT, NSET=NTIP", "NT", "*END STEP", ""]
    return "\n".join(out)

"""The fan rotor (study 23) as a 3D solid, for its natural frequencies at rest: CadQuery -> Gmsh C3D10 -> CalculiX
*FREQUENCY. It checks the beam idealisation ROSS's rotor rests on (Timoshenko shaft elements, a rigid disc, point
bearings), first on the rotor exactly as idealised, then with each detail of the real rotor added: a hub under the
disc (bonded to the shaft: a shrink fit or a tight keyed fit), smaller bearing journals.

Axes (mm): the shaft along z from 0 to the bearing span L, the bearings at its end faces (as the ROSS model's end
nodes); half model y >= 0, so its symmetric modes are the lateral bending modes in the x-z plane (u_y = 0 on y = 0;
torsion and the other bending plane are left out). Each end face is a rigid body tied to a reference node on the axis
with a spring to ground in x (half the bearing's stiffness: half model) and free rotations, as a point bearing; one
reference node is held axially.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np


def g14(v) -> str:
    return f"{float(v):.14g}"


def dims(p: dict) -> dict:
    mm = lambda k: 1e3 * float(p.get(k, 0) or 0)  # noqa: E731 - the rotor study's parameters are in metres
    return {"L": mm("bearing_span_m"), "d": mm("shaft_diameter_m"), "D": mm("disc_diameter_m"),
            "w": mm("disc_width_m"), "dh": mm("hub_diameter_m"), "lh": mm("hub_length_m"),
            "dj": mm("journal_diameter_m"), "lj": mm("journal_length_m")}


def hand_volume_half(p: dict) -> float:
    """The half solid's volume by hand: shaft (journals), hub, disc, all bonded (no overlaps counted twice)."""
    g = dims(p)
    a = lambda d: math.pi * d * d / 8  # noqa: E731 - half a circle's area
    lj = g["lj"] if g["dj"] > 0 else 0.0
    shaft = a(g["d"]) * (g["L"] - 2 * lj) + a(g["dj"] or g["d"]) * 2 * lj
    hub = (a(g["dh"]) - a(g["d"])) * g["lh"] if g["dh"] > 0 else 0.0
    bore = g["dh"] if g["dh"] > 0 else g["d"]
    return shaft + hub + (a(g["D"]) - a(bore)) * g["w"]


def build_cad(p: dict, step: Path) -> dict:
    import cadquery as cq

    g = dims(p)
    L, zc = g["L"], g["L"] / 2
    cyl = lambda d, z0, z1: cq.Workplane("XY").circle(d / 2).extrude(z1 - z0).translate((0, 0, z0))  # noqa: E731
    if g["dj"] > 0:
        body = cyl(g["dj"], 0, g["lj"]).union(cyl(g["d"], g["lj"], L - g["lj"])).union(cyl(g["dj"], L - g["lj"], L))
    else:
        body = cyl(g["d"], 0, L)
    if g["dh"] > 0:
        body = body.union(cyl(g["dh"], zc - g["lh"] / 2, zc + g["lh"] / 2))
    body = body.union(cyl(g["D"], zc - g["w"] / 2, zc + g["w"] / 2))
    big = 4 * max(L, g["D"])
    body = body.intersect(cq.Workplane("XY").box(big, big, big, centered=(True, False, True)))
    if len(body.solids().vals()) != 1 or not body.val().isValid():
        raise RuntimeError("rotor solid is not one valid solid")
    cq.exporters.export(body, str(step))
    return {"volume_mm3": float(body.val().Volume()), "hand_volume_mm3": hand_volume_half(p)}


def build_mesh(step: Path, inp: Path, *, h: float, h_disc: float | None = None, seed: int = 0) -> dict:
    import gmsh

    gmsh.initialize(["-noenv"])
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("Mesh.RandomSeed", seed)
        gmsh.model.occ.importShapes(str(step))
        gmsh.model.occ.synchronize()
        vols = gmsh.model.getEntities(3)
        if len(vols) != 1:
            raise RuntimeError(f"expected one volume, found {vols}")
        gmsh.model.addPhysicalGroup(3, [vols[0][1]], name="ROTOR")
        gmsh.option.setNumber("Mesh.MeshSizeMax", h if h_disc is None else max(h, h_disc))
        gmsh.option.setNumber("Mesh.MeshSizeMin", 0.2 * h)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 16)
        for k, v in (("Mesh.ElementOrder", 2), ("Mesh.SecondOrderLinear", 0), ("Mesh.Algorithm3D", 10),
                     ("Mesh.SaveAll", 0)):
            gmsh.option.setNumber(k, v)
        gmsh.model.mesh.generate(3)
        gmsh.model.mesh.optimize("HighOrderElastic")
        et = gmsh.model.mesh.getElementsByType(11)[0]
        sj = np.asarray(gmsh.model.mesh.getElementQualities(et, "minSJ"))
        gmsh.write(str(inp))
        return {"elements": int(len(et)), "min_scaled_jacobian": float(sj.min()),
                "inverted_elements": int((sj <= 0).sum()), "gmsh": gmsh.__version__}
    finally:
        gmsh.finalize()


def write_deck(p: dict, mesh_inp: Path, deck: Path, modes: int = 6) -> dict:
    """*FREQUENCY with the two end faces as rigid bodies on point springs (k / 2 in x each, half model)."""
    from models.fea import keyed_shaft as ks

    g = dims(p)
    ids, xyz, eids, elems = ks.read_mesh(mesh_inp)
    tol = 1e-6 * g["L"]
    end0, end1 = ids[np.abs(xyz[:, 2]) < tol], ids[np.abs(xyz[:, 2] - g["L"]) < tol]
    sym = ids[(np.abs(xyz[:, 1]) < tol) & (np.abs(xyz[:, 2]) > tol) & (np.abs(xyz[:, 2] - g["L"]) > tol)]
    nmax = int(ids.max())
    r0, rot0, r1, rot1 = nmax + 1, nmax + 2, nmax + 3, nmax + 4
    k_half = float(p["bearing_stiffness_N_per_m"]) * 1e-3 / 2      # N/mm, half model
    E, nu, rho = float(p["youngs_modulus_Pa"]) * 1e-6, float(p["poisson_ratio"]), float(p["density_kg_per_m3"]) * 1e-12

    def nset(name, arr):
        arr = [int(v) for v in arr]
        return f"*NSET, NSET={name}\n" + "\n".join(", ".join(map(str, arr[i:i + 12])) for i in range(0, len(arr), 12))

    lines = ["*NODE"] + [f"{int(n)}, {g14(x)}, {g14(y)}, {g14(z)}" for n, (x, y, z) in zip(ids, xyz)]
    lines += [f"{r0}, 0, 0, 0", f"{rot0}, 0, 0, 0", f"{r1}, 0, 0, {g14(g['L'])}", f"{rot1}, 0, 0, {g14(g['L'])}"]
    lines.append("*ELEMENT, TYPE=C3D10, ELSET=ROTOR")
    lines += [f"{e}, " + ", ".join(str(v) for v in c) for e, c in zip(eids, elems)]
    e0 = int(eids.max()) + 1
    lines += ["*ELEMENT, TYPE=SPRING1, ELSET=BRG", f"{e0}, {r0}", f"{e0 + 1}, {r1}",
              # CalculiX 2.22 reads "*SPRING card without data" when the stiffness has no decimal point ("50000")
              "*SPRING, ELSET=BRG", "1,", f"{float(k_half):.14e},"]
    lines += [nset("END0", end0), nset("END1", end1), nset("SYM", sym),
              f"*RIGID BODY, NSET=END0, REF NODE={r0}, ROT NODE={rot0}",
              f"*RIGID BODY, NSET=END1, REF NODE={r1}, ROT NODE={rot1}",
              f"*MATERIAL, NAME=STEEL\n*ELASTIC\n{g14(E)}, {g14(nu)}\n*DENSITY\n{g14(rho)}",
              "*SOLID SECTION, ELSET=ROTOR, MATERIAL=STEEL",
              "*BOUNDARY", "SYM, 2, 2, 0.",
              f"{r0}, 2, 3, 0.", f"{r1}, 2, 2, 0.",                 # the reference nodes: symmetric, one held axially
              f"{rot0}, 1, 1, 0.", f"{rot0}, 3, 3, 0.", f"{rot1}, 1, 1, 0.", f"{rot1}, 3, 3, 0.",   # rotate about y only
              "*STEP", "*FREQUENCY", str(int(modes)), "*NODE FILE", "U", "*END STEP"]
    deck.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"nodes": int(len(ids)), "elements": int(len(eids)), "end_nodes": [int(len(end0)), int(len(end1))]}


def read_frequencies(dat: Path) -> list[float]:
    """Eigenfrequencies (Hz) from CalculiX's .dat eigenvalue table (the last of its columns before the imaginary
    part: cycles/time)."""
    out, on = [], False
    for ln in Path(dat).read_text(encoding="latin-1").splitlines():
        if "E I G E N V A L U E   O U T P U T" in ln:
            on = True
            continue
        if on:
            v = ln.split()
            if len(v) >= 4 and v[0].isdigit():
                out.append(float(v[3]))
            elif out and not v:
                break
    return out


def lateral_share(frd_mode: dict, X: np.ndarray, zc: float, w: float) -> float:
    """The share of the disc's displacement that is lateral (x) in a mode: |u_x| over |u| summed on the disc's
    nodes; near 1 for a bending mode, near 0 for an axial or umbrella mode."""
    m = np.abs(X[:, 2] - zc) <= w / 2 + 1e-6
    u = np.column_stack([frd_mode["D1"], frd_mode["D2"], frd_mode["D3"]])[m]
    return float(np.abs(u[:, 0]).sum() / max(np.linalg.norm(u, axis=1).sum(), 1e-30))

"""Stepped shaft with an end-milled keyway in the small section, running towards the shoulder fillet (study 26
part 2): CadQuery solid -> Gmsh C3D10 -> CalculiX, a coarse global model and finely meshed submodels.

Geometry (mm), as the part 1 shaft (models/fea/shaft_fillet_ccx.py): axis z, small section (diameter d) from the
loaded end z = 0 to the shoulder face z = zs, a fillet of radius r_f (centre at radius d/2 + r_f, z = zs - r_f),
large section (diameter D) to zs + L_large. The keyway (DIN 6885 form A, end-milled): width B, depth t1 below the
surface at +x, ends semicircular (end-mill diameter B), bottom corners rounded with radius r_k (the cutter's corner
radius); it runs from z_k0 to z_k1 = zs - r_f - gap, so `gap` is the clear length between the keyway's end and the
start of the shoulder fillet. Half model y >= 0: the keyway is centred on y = 0, so the geometry is symmetric about
that plane: bending about y (tension at +x, through the keyway) is symmetric (u_y = 0 on y = 0) and torsion is
antisymmetric (reflection in y = 0 reverses the torque: u_x = u_z = 0 on y = 0), whatever the geometry, as long as
it is symmetric about the plane.

Global model: the end tractions of the beam stress fields on z = 0 (consistent nodal forces, as part 1), the far end
clamped, mesh sized by distance to the keyway's corner fillets and the shoulder fillet (coarse). Submodels: the solid
cut by a box around one feature (the keyway's end at the shoulder, its far end, its middle), meshed finely; the
nodes on the box's cut faces take the global displacements (CalculiX *SUBMODEL / *BOUNDARY, SUBMODEL); y = 0 keeps
its symmetry or antisymmetry condition; no other load acts inside the box.

Numbers are written with at most 14 significant digits: CalculiX reads at most 20 characters per field.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

FACES = ((0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0))


def g14(v) -> str:
    return f"{float(v):.14g}"


def dims(p: dict) -> dict:
    d, D, rf = float(p["d_mm"]), float(p["D_mm"]), float(p["fillet_radius_mm"])
    zs, Ll = float(p["small_length_mm"]), float(p["large_length_mm"])
    out = {"d": d, "D": D, "rf": rf, "zs": zs, "z_end": zs + Ll, "R": d / 2, "R0": d / 2 + rf, "zc": zs - rf}
    if float(p.get("key_width_mm", 0)) > 0:
        B, t1, rk = float(p["key_width_mm"]), float(p["key_depth_mm"]), float(p["key_corner_radius_mm"])
        z1 = zs - rf - float(p["key_gap_mm"])
        out |= {"B": B, "t1": t1, "rk": rk, "z_k1": z1, "z_k0": z1 - float(p["key_length_mm"])}
    return out


def build_cad(p: dict, step: Path, box=None) -> dict:
    """The half shaft (y >= 0) with its keyway (if key_width_mm > 0), optionally cut to box = (x0, x1, y0, y1, z0, z1);
    written as STEP. Returns the solid's volume."""
    import cadquery as cq

    g = dims(p)
    R, Rl, rf, zs = g["R"], g["D"] / 2, g["rf"], g["zs"]
    prof = (cq.Workplane("XZ").moveTo(0, 0).lineTo(R, 0).lineTo(R, zs - rf)
            .radiusArc((R + rf, zs), rf).lineTo(Rl, zs).lineTo(Rl, g["z_end"]).lineTo(0, g["z_end"]).close())
    solid = prof.revolve(360, (0, 0, 0), (0, 1, 0))
    if "B" in g:
        L = g["z_k1"] - g["z_k0"]
        cutter = (cq.Workplane("YZ", origin=(R - g["t1"], 0, 0.5 * (g["z_k0"] + g["z_k1"])))
                  .slot2D(L, g["B"], angle=90).extrude(g["t1"] + 0.25 * g["d"]).faces("<X").edges().fillet(g["rk"]))
        solid = solid.cut(cutter)
    big = 4 * max(g["D"], g["z_end"])
    solid = solid.intersect(cq.Workplane("XY").box(big, big, big, centered=(True, False, True)))   # y >= 0
    if box is not None:
        x0, x1, y0, y1, z0, z1 = box
        solid = solid.intersect(cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False)
                                .translate((x0, y0, z0)))
    if not solid.val().isValid():
        raise RuntimeError("CadQuery solid is not valid")
    cq.exporters.export(solid, str(step))
    return {"volume_mm3": float(solid.val().Volume()), "faces": len(solid.faces().vals())}


def build_mesh(p: dict, step: Path, inp: Path, *, h_key: float, h_fillet: float, h_far: float, growth: float,
               band_deg: float = 60.0, seed: int = 0) -> dict:
    """Mesh the STEP solid: size h_key within 2 r_k of the keyway's corner fillets, h_fillet within 0.5 mm of the
    shoulder fillet inside +-band_deg of +x (coarser outside it), growing by `growth` per mm to h_far."""
    import gmsh

    g = dims(p)
    gmsh.initialize(["-noenv"])
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.option.setNumber("Mesh.RandomSeed", seed)
        gmsh.model.occ.importShapes(str(step))
        gmsh.model.occ.synchronize()
        vols = gmsh.model.getEntities(3)
        if len(vols) != 1:
            raise RuntimeError(f"expected one volume, found {vols}")
        key_f, shoulder = [], []
        for _, s in gmsh.model.getEntities(2):
            x0, y0, z0, x1, y1, z1 = gmsh.model.getBoundingBox(2, s)
            if "B" in g and abs(x0 - (g["R"] - g["t1"])) < 1e-3 and abs((x1 - x0) - g["rk"]) < 1e-3:
                key_f.append(s)
            if z0 > g["zc"] - 1e-3 and z1 < g["zs"] + 1e-3 and x1 - x0 > 1e-3 and z1 - z0 > 0.5 * g["rf"]:
                shoulder.append(s)
        gmsh.model.addPhysicalGroup(3, [vols[0][1]], name="SHAFT")
        f = gmsh.model.mesh.field
        fields = []
        if key_f:
            dk = f.add("Distance")
            f.setNumbers(dk, "SurfacesList", key_f)
            f.setNumber(dk, "Sampling", 80)
            mk = f.add("MathEval")
            f.setString(mk, "F", f"Min({g14(h_far)}, {g14(h_key)} + {g14(growth)}*Max(0, F{dk} - {g14(2 * g['rk'])}))")
            fields.append(mk)
        c, s_ = math.cos(math.radians(band_deg)), math.sin(math.radians(band_deg))
        dist = f"Fabs(Sqrt((Sqrt(x^2+y^2)-{g14(g['R0'])})^2+(z-{g14(g['zc'])})^2)-{g14(g['rf'])})"
        wedge = f"Max(0, Fabs(y)*({g14(c)}) - x*({g14(s_)}))"   # parentheses: Gmsh's parser rejects "*-1"
        ms = f.add("MathEval")
        f.setString(ms, "F", f"Min({g14(h_far)}, {g14(h_fillet)} + {g14(growth)}*(Max(0, {dist} - 0.5) + {wedge}))")
        fields.append(ms)
        mn = f.add("Min")
        f.setNumbers(mn, "FieldsList", fields)
        f.setAsBackgroundMesh(mn)
        for k in ("MeshSizeExtendFromBoundary", "MeshSizeFromPoints", "MeshSizeFromCurvature"):
            gmsh.option.setNumber(f"Mesh.{k}", 0)
        for k, v in (("Mesh.ElementOrder", 2), ("Mesh.SecondOrderLinear", 0), ("Mesh.Algorithm3D", 10),
                     ("Mesh.SaveAll", 0)):
            gmsh.option.setNumber(k, v)
        gmsh.model.mesh.generate(3)
        gmsh.model.mesh.optimize("HighOrderElastic")
        et = gmsh.model.mesh.getElementsByType(11)[0]
        sj = np.asarray(gmsh.model.mesh.getElementQualities(et, "minSJ"))
        gmsh.write(str(inp))
        return {"elements": int(len(et)), "min_scaled_jacobian": float(sj.min()),
                "inverted_elements": int((sj <= 0).sum()), "keyway_fillet_faces": len(key_f),
                "shoulder_fillet_faces": len(shoulder), "gmsh": gmsh.__version__}
    finally:
        gmsh.finalize()


def read_mesh(mesh_inp: Path):
    """(node ids, xyz, element ids, C3D10 connectivity) from Gmsh's .inp (C3D10 blocks only)."""
    text = Path(mesh_inp).read_text(encoding="utf-8")
    block = text.split("*NODE", 1)[1].split("*", 1)[0]
    rows = np.array([[float(v) for v in ln.split(",")] for ln in block.strip().splitlines()])
    ids, xyz = rows[:, 0].astype(int), rows[:, 1:4]
    eids, elems = [], []
    for part in text.split("*ELEMENT")[1:]:
        head, _, body = part.partition("\n")
        if "C3D10" not in head.upper():
            continue
        buf = [int(v) for v in body.split("*", 1)[0].replace(",", " ").split()]
        for k in range(0, len(buf), 11):
            eids.append(buf[k])
            elems.append(buf[k + 1:k + 11])
    used = np.unique(np.array(elems))
    keep = np.isin(ids, used)                       # Gmsh can write geometry vertices no element uses
    return ids[keep], xyz[keep], np.array(eids, dtype=int), np.array(elems, dtype=int)


def write_deck(p: dict, mesh_inp: Path, deck: Path, load: str, *, box=None, global_frd: str | None = None) -> dict:
    """Global deck (box None): end tractions on z = 0 and the far end clamped. Submodel deck: the nodes on the box's
    cut faces driven by global_frd. Both: y = 0 symmetric (bending) or antisymmetric (torsion); *NODE FILE U and
    *EL FILE S."""
    from models.fea import shaft_fillet_ccx as sf      # the part 1 load functions (consistent forces)

    g = dims(p)
    ids, xyz, eids, elems = read_mesh(mesh_inp)
    tol = 1e-6 * g["D"]
    on_sym = np.abs(xyz[:, 1]) < tol
    parts = [f"*NODE"] + [f"{int(n)}, {g14(x)}, {g14(y)}, {g14(z)}" for n, (x, y, z) in zip(ids, xyz)]
    parts.append("*ELEMENT, TYPE=C3D10, ELSET=SHAFT")
    parts += [f"{e}, " + ", ".join(str(v) for v in c) for e, c in zip(eids, elems)]
    out = {"nodes": int(len(ids)), "elements": int(len(eids))}

    def nset(name, arr):
        arr = [int(v) for v in arr]
        return f"*NSET, NSET={name}\n" + "\n".join(", ".join(map(str, arr[i:i + 12])) for i in range(0, len(arr), 12)) + "\n"

    sym_dofs = ((2,),) if load == "bending" else ((1,), (3,))
    if box is None:
        row = {int(n): k for k, n in enumerate(ids)}
        conn = np.vectorize(row.get)(elems)
        faces = sf.end_faces(xyz, conn, lambda X: np.abs(X[:, 2]) < tol)
        F = sf.consistent_forces(xyz, faces, sf.tractions(p, load))
        clamp = ids[np.abs(xyz[:, 2] - g["z_end"]) < tol]
        sym = ids[on_sym]
        bc = "*BOUNDARY\n" + "".join(f"SYM, {k[0]}, {k[0]}, 0.\n" for k in sym_dofs) + "CLAMP, 1, 3, 0.\n"
        cl = "*CLOAD\n" + "".join(f"{int(ids[n])}, {k + 1}, {g14(v)}\n" for n, f in sorted(F.items())
                                  for k, v in enumerate(f) if v != 0.0)
        sets = nset("SYM", sym) + nset("CLAMP", clamp)
        step = "*STEP\n*STATIC\n" + cl
        tail = "*NODE PRINT, NSET=CLAMP\nRF\n"
        Fa = np.array(list(F.values()))
        Xa = np.array([xyz[n] for n in F])
        out |= {"applied_force_N": Fa.sum(axis=0).tolist(), "applied_moment_Nmm": np.cross(Xa, Fa).sum(axis=0).tolist()}
        head = ""
    else:
        x0, x1, y0, y1, z0, z1 = box
        cut = np.zeros(len(ids), bool)
        for axis, lo, hi in ((0, x0, x1), (1, y0, y1), (2, z0, z1)):
            for v in (lo, hi):
                plane = np.abs(xyz[:, axis] - v) < tol
                if axis == 1 and abs(v) < tol:
                    continue                                  # y = 0 is the symmetry plane, not a cut
                cut |= plane
        if not cut.any():
            raise RuntimeError("no nodes on the submodel's cut faces")
        sym = ids[on_sym & ~cut]
        sets = nset("DRIVEN", ids[cut]) + nset("SYM", sym)
        head = f"*SUBMODEL, TYPE=NODE, INPUT={global_frd}\nDRIVEN\n"
        bc = "*BOUNDARY\n" + "".join(f"SYM, {k[0]}, {k[0]}, 0.\n" for k in sym_dofs)
        step = "*STEP\n*STATIC\n*BOUNDARY, SUBMODEL, STEP=1\nDRIVEN, 1, 3\n"
        tail = ""
        out |= {"driven_nodes": int(cut.sum())}
    deck.write_text("\n".join(parts) + "\n" + sets + head
                    + f"*MATERIAL, NAME=STEEL\n*ELASTIC\n{g14(p['youngs_modulus_MPa'])}, {g14(p['poisson_ratio'])}\n"
                    + "*SOLID SECTION, ELSET=SHAFT, MATERIAL=STEEL\n" + bc + step
                    + "*NODE FILE\nU\n*EL FILE\nS\n" + tail + "*END STEP\n", encoding="utf-8")
    return out


def principal(S: dict) -> np.ndarray:
    T = np.zeros((len(S["ids"]), 3, 3))
    T[:, 0, 0], T[:, 1, 1], T[:, 2, 2] = S["SXX"], S["SYY"], S["SZZ"]
    T[:, 0, 1] = T[:, 1, 0] = S["SXY"]
    T[:, 0, 2] = T[:, 2, 0] = S["SZX"]
    T[:, 1, 2] = T[:, 2, 1] = S["SYZ"]
    return np.linalg.eigvalsh(T)


def nominal(p: dict, load: str) -> float:
    d = float(p["d_mm"])
    if load == "bending":
        return float(p["bending_moment_Nm"]) * 1e3 * 32 / (math.pi * d ** 3)
    return float(p["torque_Nm"]) * 1e3 * 16 / (math.pi * d ** 3)


def region_peaks(p: dict, X: np.ndarray, ev: np.ndarray, load: str) -> dict:
    """Peak stress / nominal in each region (gross nominal stresses 32 M / pi d^3, 16 T / pi d^3): the maximum
    principal stress in bending, the maximum shear (s1 - s3) / 2 in torsion. Regions: the keyway's corner band
    (r_k-wide strip at its bottom) near its shoulder end, near its far end and in its middle third; the shoulder
    fillet's surface."""
    from models.fea import shaft_fillet_ccx as sf

    g = dims(p)
    v = ev[:, 2] if load == "bending" else 0.5 * (ev[:, 2] - ev[:, 0])
    nom = nominal(p, load)
    pf = {"D_mm": g["D"], "d_mm": g["d"], "fillet_radius_mm": g["rf"], "small_length_mm": g["zs"],
          "large_length_mm": g["z_end"] - g["zs"]}
    out = {}
    fil = sf.fillet_surface_mask(X, pf)
    if fil.any():
        k = np.flatnonzero(fil)[np.argmax(v[fil])]
        out["fillet"] = {"k": float(v[k] / nom), "xyz": X[k].tolist(), "nodes": int(fil.sum())}
    if "B" in g:
        corner = (X[:, 0] > g["R"] - g["t1"] - 1e-6) & (X[:, 0] < g["R"] - g["t1"] + g["rk"] + 1e-6)
        L = g["z_k1"] - g["z_k0"]
        for name, lo, hi in (("key_near_end", g["z_k1"] - g["B"], g["z_k1"] + 1e-6),
                             ("key_far_end", g["z_k0"] - 1e-6, g["z_k0"] + g["B"]),
                             ("key_middle", g["z_k0"] + L / 3, g["z_k1"] - L / 3)):
            m = corner & (X[:, 2] >= lo) & (X[:, 2] <= hi)
            if m.any():
                k = np.flatnonzero(m)[np.argmax(v[m])]
                out[name] = {"k": float(v[k] / nom), "xyz": X[k].tolist(), "nodes": int(m.sum())}
    return out

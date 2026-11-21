"""CAD-to-FEA pipeline: machined clevis bracket (base plate, upright lug with a pin hole, two
gussets, filleted internal corners) under an inclined pin load.

Geometry (mm), built in CadQuery:
  base    plate base_length x base_width x base_thickness, centred on x and y, z = 0..t_b; its
          bottom face is fixed to the structure (bolted and dowelled, treated as rigid)
  lug     upright plate in the x-z plane, thickness t_l (along y), width 2 R (along x): a rectangle
          from the base up to the pin centre at height H, capped by a half disc of radius R; pin hole
          of diameter d_p through it (along y)
  gussets two triangular ribs in the y-z plane at x = 0, one each side of the lug, thickness t_g
          (along x), height h_g up the lug face and length l_g = gusset_aspect x h_g along the base
  fillets radius r_f on the edges where the lug and the gussets meet the base and each other
Mesh: Gmsh 10-node tetrahedra, size element_size_mm, refined by curvature (fillets, hole).
Load: pin force (F_x, F_y, F_z) on a reference node tied to the hole surface by a rigid body (a
stiff pin); the reference node's displacement is the pin deflection.
Outputs: nodal displacements and stresses, nodal reactions on the base, the reference node.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

PARAMS = ("base_length_mm", "base_width_mm", "base_thickness_mm", "lug_radius_mm", "pin_height_mm",
          "pin_diameter_mm", "lug_thickness_mm", "gusset_thickness_mm", "gusset_height_mm", "gusset_aspect",
          "fillet_radius_mm", "youngs_modulus_MPa", "poisson_ratio", "density_t_per_mm3",
          "load_x_N", "load_y_N", "load_z_N", "element_size_mm")
TOL = 1e-4


def _f(p, k):
    return float(p[k])


def build_solid(p: dict):
    import cadquery as cq

    Lb, Wb, tb = _f(p, "base_length_mm"), _f(p, "base_width_mm"), _f(p, "base_thickness_mm")
    R, H, dp = _f(p, "lug_radius_mm"), _f(p, "pin_height_mm"), _f(p, "pin_diameter_mm")
    tl, tg, hg = _f(p, "lug_thickness_mm"), _f(p, "gusset_thickness_mm"), _f(p, "gusset_height_mm")
    lg = _f(p, "gusset_aspect") * hg
    rf = _f(p, "fillet_radius_mm")
    base = cq.Workplane("XY").box(Lb, Wb, tb, centered=(True, True, False))
    # lug profile in the x-z plane (XZ workplane: local x = global x, local y = global z), extruded both ways in y
    lug = (cq.Workplane("XZ").moveTo(-R, tb).lineTo(R, tb).lineTo(R, H)
           .threePointArc((0, H + R), (-R, H)).close().extrude(tl / 2, both=True))
    hole = cq.Workplane("XZ").center(0, H).circle(dp / 2).extrude(tl, both=True)
    # gussets in the y-z plane (YZ workplane: local x = global y, local y = global z), extruded both ways in x
    g_pos = (cq.Workplane("YZ").moveTo(tl / 2, tb).lineTo(tl / 2 + lg, tb).lineTo(tl / 2, tb + hg).close()
             .extrude(tg / 2, both=True))
    g_neg = (cq.Workplane("YZ").moveTo(-tl / 2, tb).lineTo(-tl / 2, tb + hg).lineTo(-tl / 2 - lg, tb).close()
             .extrude(tg / 2, both=True))
    solid = base.union(lug).union(g_pos).union(g_neg)
    if rf > 0:
        # internal edges where the parts meet: on the base top face (z = t_b, but not the base outline) and
        # where the gussets meet the lug faces (y = +-t_l/2, inside the gusset height)
        e = 1e-3
        sel = (cq.selectors.BoxSelector((-R - e, -tl / 2 - lg - e, tb - e), (R + e, tl / 2 + lg + e, tb + e))
               + cq.selectors.BoxSelector((-tg / 2 - e, -tl / 2 - e, tb + e), (tg / 2 + e, tl / 2 + e, tb + hg + e)))
        solid = solid.edges(sel).fillet(rf)
    solid = solid.cut(hole)
    return solid


def build_step(p: dict, path: Path) -> dict:
    import cadquery as cq

    solid = build_solid(p)
    cq.exporters.export(solid, str(path))
    v = solid.val()
    return {"volume_mm3": float(v.Volume()), "faces": len(v.Faces()), "valid": bool(v.isValid())}


def write_geo(p: dict, path: Path, step_name: str = "bracket.step") -> None:
    h = _f(p, "element_size_mm")
    path.write_text(f"""SetFactory("OpenCASCADE");
Merge "{step_name}";
Mesh.MeshSizeMax = {h!r}; Mesh.MeshSizeMin = {h / 4!r};
Mesh.MeshSizeFromCurvature = 12;
Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 0; Mesh.Optimize = 1;
Physical Volume("BRACKET") = Volume{{:}};
""", encoding="utf-8")


def read_mesh(mesh_inp: Path):
    text = Path(mesh_inp).read_text(encoding="utf-8")
    block = text.split("*NODE", 1)[1].split("*", 1)[0]
    rows = np.array([[float(v) for v in ln.split(",")] for ln in block.strip().splitlines()])
    ids, xyz = rows[:, 0].astype(int), rows[:, 1:4]
    elems = []
    for part in text.split("*ELEMENT")[1:]:
        head, _, body = part.partition("\n")
        if "C3D10" not in head.upper():
            continue
        buf = []
        for ln in body.splitlines():
            if ln.startswith("*"):
                break
            buf += [int(v) for v in ln.replace(",", " ").split()]
        elems += [buf[k + 1:k + 11] for k in range(0, len(buf), 11)]
    return ids, xyz, np.array(elems, dtype=int)


def tet10_volume(xyz_by_id: dict, elems) -> float:
    """Mesh volume from the corner nodes (straight-sided; curved faces make it slightly smaller)."""
    v = 0.0
    for e in elems:
        a, b, c, d = (np.array(xyz_by_id[n]) for n in e[:4])
        v += abs(np.dot(b - a, np.cross(c - a, d - a))) / 6
    return float(v)


def write_deck(p: dict, mesh_inp: Path, deck: Path) -> dict:
    ids, xyz, elems = read_mesh(mesh_inp)
    H, dp = _f(p, "pin_height_mm"), _f(p, "pin_diameter_mm")
    base = ids[np.isclose(xyz[:, 2], 0.0, atol=TOL)]
    r = np.hypot(xyz[:, 0], xyz[:, 2] - H)
    hole = ids[np.isclose(r, dp / 2, atol=1e-3 * dp)]
    if len(base) < 3 or len(hole) < 3:
        raise RuntimeError(f"base nodes {len(base)}, hole nodes {len(hole)}")
    ref = int(ids.max()) + 1
    E, nu, rho = _f(p, "youngs_modulus_MPa"), _f(p, "poisson_ratio"), _f(p, "density_t_per_mm3")
    rows = lambda a: [", ".join(str(int(v)) for v in a[s:s + 12]) for s in range(0, len(a), 12)]
    lines = [f"*INCLUDE, INPUT={Path(mesh_inp).name}", f"*NODE, NSET=NREF", f"{ref}, 0., 0., {H!r}",
             "*NSET, NSET=NBASE"] + rows(base) + ["*NSET, NSET=NHOLE"] + rows(hole)
    lines += ["*MATERIAL, NAME=AL6061", "*ELASTIC", f"{E!r}, {nu!r}", "*DENSITY", f"{rho!r}",
              "*SOLID SECTION, ELSET=BRACKET, MATERIAL=AL6061",
              "*RIGID BODY, NSET=NHOLE, REF NODE=" + str(ref),
              "*BOUNDARY", "NBASE, 1, 3, 0.",
              "*STEP", "*STATIC", "*CLOAD",
              f"{ref}, 1, {_f(p, 'load_x_N')!r}", f"{ref}, 2, {_f(p, 'load_y_N')!r}", f"{ref}, 3, {_f(p, 'load_z_N')!r}",
              "*NODE FILE", "U", "*EL FILE", "S",
              "*NODE PRINT, NSET=NBASE", "RF", "*NODE PRINT, NSET=NREF", "U",
              "*END STEP"]
    deck.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"nodes": int(len(ids)), "elements": int(len(elems)), "base_nodes": int(len(base)),
            "hole_nodes": int(len(hole)), "ref_node": ref,
            "mesh_volume_mm3": tet10_volume(dict(zip(ids.tolist(), xyz.tolist())), elems)}

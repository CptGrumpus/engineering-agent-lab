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
Reproducibility: the fillet edges are passed in a fixed geometric order, so the same parameters always
give the same STEP and the same mesh (see build_solid).
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
        # The edges go to the fillet in a fixed geometric order: CadQuery's "+" selector merges through a set
        # keyed on OCC shape hashes (memory addresses), so its order, and with it the fillet's face split,
        # changed from run to run (same shape and volume, different mesh).
        e = 1e-3
        boxes = (cq.selectors.BoxSelector((-R - e, -tl / 2 - lg - e, tb - e), (R + e, tl / 2 + lg + e, tb + e)),
                 cq.selectors.BoxSelector((-tg / 2 - e, -tl / 2 - e, tb + e), (tg / 2 + e, tl / 2 + e, tb + hg + e)))
        shape = solid.val()
        picked = {}
        for box in boxes:
            for edge in box.filter(shape.Edges()):
                c = edge.Center()
                picked.setdefault((round(c.x, 6), round(c.y, 6), round(c.z, 6), round(edge.Length(), 6)), edge)
        solid = cq.Workplane("XY").newObject([shape.fillet(rf, [picked[k] for k in sorted(picked)])])
    solid = solid.cut(hole)
    return solid


def build_step(p: dict, path: Path) -> dict:
    import cadquery as cq

    solid = build_solid(p)
    cq.exporters.export(solid, str(path))
    v = solid.val()
    return {"volume_mm3": float(v.Volume()), "faces": len(v.Faces()), "valid": bool(v.isValid())}


def curvature_points(h: float) -> int:
    """Elements per full circle on curved faces, scaled with the element size (12 at 4 mm, as in the
    optimisation run), so a smaller element_size_mm refines the fillets and the hole by the same ratio
    as the rest of the mesh. With a fixed count the fillet elements (about 1.6 mm on a 3 mm radius)
    would not change with element_size_mm, and a mesh study would understate the fillet peak's error."""
    return max(6, round(48.0 / h))


def fillet_refinement(p: dict) -> tuple[int, float]:
    """(elements per circle on curved faces, minimum element size).

    Without fillet_element_size_mm: curvature_points(h) and h / 4, as in clevis_opt and clevis_opt_r1.
    With it (h_f): enough elements per circle that a fillet of radius r_f gets elements no larger than
    h_f, and a minimum size (h_f / 2) that does not clamp them. The fillets are the smallest radius on
    the part, so this refines them most; the hole (not assessed) and the lug cap follow in proportion."""
    h = _f(p, "element_size_mm")
    if p.get("fillet_element_size_mm") is None:
        return curvature_points(h), h / 4
    hf = _f(p, "fillet_element_size_mm")
    return max(6, int(np.ceil(2 * np.pi * _f(p, "fillet_radius_mm") / hf))), min(h / 4, hf / 2)


def write_geo(p: dict, path: Path, step_name: str = "bracket.step", high_order_optimize: bool = False) -> None:
    """high_order_optimize: the fallback when curving the quadratic tets inverts one (Gmsh reports
    'elements with jac. < 0'): Gmsh's high-order optimiser moves the nodes of a small patch around it."""
    h = _f(p, "element_size_mm")
    n_curv, h_min = fillet_refinement(p)
    ho = " Mesh.HighOrderOptimize = 1;" if high_order_optimize else ""
    path.write_text(f"""SetFactory("OpenCASCADE");
Merge "{step_name}";
Mesh.MeshSizeMax = {h!r}; Mesh.MeshSizeMin = {h_min!r};
Mesh.MeshSizeFromCurvature = {n_curv};
Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 0; Mesh.Optimize = 1;{ho}
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


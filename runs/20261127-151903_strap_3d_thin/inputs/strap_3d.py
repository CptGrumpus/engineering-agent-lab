"""Study 2 part 2: the strap with its cable hole as a 3D solid, to measure what plane stress leaves out (the stress at
the hole edge varies through the 4 mm thickness: higher at mid-thickness, lower at the faces).

Geometry: the same CadQuery quarter face as study 2 (models/fea/strap_hole.py: x along the strap, y across it, the hole
at the origin, face at z = 0), extruded in Gmsh through the half thickness: an eighth model, symmetric about x = 0,
y = 0 and the mid-plane z = 0. The 2D mesh is all quadrilaterals, refined
at the hole as study 2's triangles were (Gmsh's Blossom full-quad recombination, which here keeps the requested
size), extruded in layers graded towards the free face z = t/2, where the
through-thickness gradient is steepest: 20-node bricks (C3D20).

Load: a uniform traction F / (W t) on the end face x = L / 2 (element-face pressure). Supports: symmetry on the three
planes. Reaction on x = 0: F / 4.

The references: in the thin-plate limit (t / d -> 0) the 3D solution is plane stress, so a thin plate run through the
same pipeline must reproduce study 2's plane-stress peak at mid-thickness and at the face alike. At finite thickness
the stresses averaged through the thickness satisfy plane-stress equilibrium exactly but not its constitutive law
(sigma_zz averages to zero over the thickness without vanishing inside), so the mean only approaches plane stress, to
order (t / r)^2: a measured difference, not a check (0.4 % at t / r = 0.5; generalised plane stress, Timoshenko and
Goodier, Theory of Elasticity, section 98). Equilibrium: the reaction on x = 0 and the ligament force are F / 4.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

PARAMS = ("length_mm", "width_mm", "thickness_mm", "hole_diameter_mm", "axial_load_N", "youngs_modulus_MPa",
          "poisson_ratio", "yield_strength_MPa", "hole_element_size_mm", "far_element_size_mm", "z_layers",
          "z_ratio")
TOL = 1e-6
#: C3D20 / C3D8 faces (CalculiX numbering) as corner-node index quadruples
HEX_FACES = ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0))


def layer_heights(n: int, ratio: float) -> list[float]:
    """Cumulative fractions of n layers through the half thickness, each layer ratio times thinner than the one before
    it going from the mid-plane to the free face (ratio 1: uniform)."""
    w = np.array([ratio ** -k for k in range(n)], float)
    return (np.cumsum(w) / w.sum()).tolist()


def n_layers(params: dict) -> int:
    """Element layers through the half thickness: z_layers, or with z_layers = 0 as many as the half thickness holds
    hole-edge elements (at least 4), so a mesh study refines through the thickness with the hole."""
    n = int(params["z_layers"])
    if n > 0:
        return n
    return max(4, round(float(params["thickness_mm"]) / 2 / float(params["hole_element_size_mm"])))


def write_geo(params: dict, path: Path, step_name: str = "quarter.step") -> None:
    r = float(params["hole_diameter_mm"]) / 2
    h_hole, h_far = float(params["hole_element_size_mm"]), float(params["far_element_size_mm"])
    n, q = n_layers(params), float(params["z_ratio"])
    cum = layer_heights(n, q)
    t2 = float(params["thickness_mm"]) / 2
    e = 1e-3
    path.write_text(f"""SetFactory("OpenCASCADE");
Merge "{step_name}";
hole() = Curve In BoundingBox{{{-e}, {-e}, -1, {r + e}, {r + e}, 1}};
Field[1] = Distance; Field[1].CurvesList = {{hole()}}; Field[1].Sampling = 400;
Field[2] = Threshold; Field[2].InField = 1;
Field[2].SizeMin = {h_hole!r}; Field[2].SizeMax = {h_far!r};
Field[2].DistMin = {r / 4!r}; Field[2].DistMax = {3 * r!r};
Background Field = 2;
Mesh.MeshSizeExtendFromBoundary = 0; Mesh.MeshSizeFromPoints = 0; Mesh.MeshSizeFromCurvature = 0;
Mesh.Algorithm = 8; Mesh.RecombinationAlgorithm = 3; Mesh.RecombineAll = 1;
Recombine Surface{{1}};
out[] = Extrude{{0, 0, {t2!r}}} {{ Surface{{1}}; Layers{{ {{{", ".join("1" for _ in cum)}}}, {{{", ".join(repr(c) for c in cum)}}} }}; Recombine; }};
Mesh.ElementOrder = 2; Mesh.SecondOrderIncomplete = 1; Mesh.SecondOrderLinear = 0;
Physical Volume("PLATE") = {{out[1]}};
""", encoding="utf-8")


def read_mesh(mesh_inp: Path):
    """Nodes (ids, xyz) and the C3D20 elements (ids, 20 node ids each) of a Gmsh Abaqus export."""
    text = Path(mesh_inp).read_text(encoding="utf-8")
    block = text.split("*NODE", 1)[1].split("*", 1)[0]
    rows = np.array([[float(v) for v in ln.split(",")] for ln in block.strip().splitlines()])
    ids, xyz = rows[:, 0].astype(int), rows[:, 1:4]
    eids, elems, other = [], [], 0
    for part in text.split("*ELEMENT")[1:]:
        head, _, body = part.partition("\n")
        buf = []
        for ln in body.splitlines():
            if ln.startswith("*"):
                break
            buf += [int(v) for v in ln.replace(",", " ").split()]
        if "C3D20" in head.upper():
            for k in range(0, len(buf), 21):
                eids.append(buf[k])
                elems.append(buf[k + 1:k + 21])
        elif any(s in head.upper() for s in ("C3D", "CPS", "CPE")):
            other += 1
    return ids, xyz, np.array(eids, int), np.array(elems, int), other


def write_deck(params: dict, mesh_inp: Path, deck: Path) -> dict:
    ids, xyz, eids, elems, other = read_mesh(mesh_inp)
    if other or not len(eids):
        raise RuntimeError(f"mesh is not all C3D20 bricks ({len(eids)} bricks, {other} other element blocks)")
    L2, W, t, F = float(params["length_mm"]) / 2, float(params["width_mm"]), float(params["thickness_mm"]), \
        float(params["axial_load_N"])
    row = {int(n): k for k, n in enumerate(ids)}
    conn = np.vectorize(row.get)(elems)
    on_end = np.abs(xyz[:, 0] - L2) < TOL
    faces = []
    for f, quad in enumerate(HEX_FACES):
        hit = np.all(on_end[conn[:, list(quad)]], axis=1)
        faces += [(int(eids[e]), f + 1) for e in np.flatnonzero(hit)]
    sigma = F / (W * t)
    sets = {"XSYM": ids[np.abs(xyz[:, 0]) < TOL], "YSYM": ids[np.abs(xyz[:, 1]) < TOL],
            "ZSYM": ids[np.abs(xyz[:, 2]) < TOL]}
    E, nu = float(params["youngs_modulus_MPa"]), float(params["poisson_ratio"])
    rows = lambda a: [", ".join(str(int(v)) for v in a[s:s + 12]) for s in range(0, len(a), 12)]  # noqa: E731
    lines = [f"*INCLUDE, INPUT={Path(mesh_inp).name}"]
    for k, v in sets.items():
        lines += [f"*NSET, NSET={k}"] + rows(v)
    lines += [f"*MATERIAL, NAME=AL", "*ELASTIC", f"{E!r}, {nu!r}", "*SOLID SECTION, ELSET=PLATE, MATERIAL=AL",
              "*BOUNDARY", "XSYM, 1, 1, 0.", "YSYM, 2, 2, 0.", "ZSYM, 3, 3, 0.", "*STEP", "*STATIC", "*DLOAD"]
    lines += [f"{e}, P{f}, {-sigma!r}" for e, f in faces]
    lines += ["*NODE FILE", "U", "*EL FILE", "S", "*NODE PRINT, NSET=XSYM, TOTALS=ONLY", "RF", "*END STEP"]
    deck.write_text("\n".join(lines) + "\n", encoding="utf-8")
    loaded_area = len(faces) and float(_face_area(xyz, conn, faces, eids))
    return {"nodes": int(len(ids)), "elements": int(len(eids)), "end_faces": len(faces),
            "loaded_area_mm2": loaded_area, "end_area_exact_mm2": W / 2 * t / 2, "traction_MPa": sigma}


def _face_area(xyz, conn, faces, eids) -> float:
    """Total area of the loaded faces (corner quads, flat): the load written is traction x this area."""
    pos = {int(e): k for k, e in enumerate(eids)}
    a = 0.0
    for e, f in faces:
        c = xyz[conn[pos[e], list(HEX_FACES[f - 1])]]
        a += 0.5 * np.linalg.norm(np.cross(c[2] - c[0], c[3] - c[1]))
    return a


def hole_edge_profile(ids, xyz, sxx: dict, r: float) -> tuple[np.ndarray, np.ndarray]:
    """sigma_xx at the hole edge on the ligament (x = 0, y = r), against z, sorted (corner and mid-side nodes)."""
    m = (np.abs(xyz[:, 0]) < TOL) & (np.abs(xyz[:, 1] - r) < 1e-6 * max(r, 1.0))
    z = xyz[m, 2]
    s = np.array([sxx[int(n)] for n in ids[m]])
    o = np.argsort(z)
    return z[o], s[o]


def through_mean(z: np.ndarray, s: np.ndarray, t2: float) -> float:
    """Mean over the half thickness of a nodal profile on 20-node bricks (quadratic along z between corner nodes:
    Simpson's rule on each element's corner, mid-side, corner triple)."""
    if len(z) % 2 == 0 or abs(z[0]) > TOL or abs(z[-1] - t2) > 1e-6:
        raise ValueError("expected an odd number of nodes from z = 0 to z = t/2")
    tot = sum((z[k + 2] - z[k]) / 6 * (s[k] + 4 * s[k + 1] + s[k + 2]) for k in range(0, len(z) - 2, 2))
    return float(tot / t2)


def ligament_force(ids, xyz, sxx: dict, r: float, W2: float, t2: float, n_layers: int) -> float:
    """Integral of sigma_xx over the ligament face x = 0 (y from r to W/2, z from 0 to t/2): the nodes form a tensor
    grid there (the 2D mesh's x = 0 edge times the layers); trapezoidal in y over corner and mid-side nodes, Simpson
    in z."""
    m = np.abs(xyz[:, 0]) < TOL
    ys = np.unique(np.round(xyz[m, 1], 9))
    vals = []
    for y in ys:
        mm = m & (np.abs(xyz[:, 1] - y) < 1e-8)
        z, s = xyz[mm, 2], np.array([sxx[int(n)] for n in ids[mm]])
        o = np.argsort(z)
        z, s = z[o], s[o]
        if len(z) == 2 * n_layers + 1:   # a corner line of the 2D mesh: corner and mid-side nodes along z
            vals.append(through_mean(z, s, t2) * t2)
        else:                            # a mid-side line: only the layers' corner levels carry nodes
            vals.append(float(np.trapezoid(s, z)))
    return float(np.trapezoid(vals, ys))

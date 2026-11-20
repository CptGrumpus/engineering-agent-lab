"""Surface extraction and scene export used by the result renders."""

import json

import numpy as np
import pytest

from harness.femesh import (boundary_triangles, compact, enclosed_volume, extrude_planar,
                            read_inp, write_scene)


def hex_block(nx, ny, nz, dx=1.0, dy=2.0, dz=3.0):
    """A structured block of C3D8 elements; returns nodes {id: xyz} and elements."""
    nid = lambda i, j, k: 1 + i + (nx + 1) * (j + (ny + 1) * k)  # noqa: E731
    nodes = {nid(i, j, k): (i * dx, j * dy, k * dz)
             for i in range(nx + 1) for j in range(ny + 1) for k in range(nz + 1)}
    elems = []
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                elems.append(("C3D8", [nid(i, j, k), nid(i + 1, j, k), nid(i + 1, j + 1, k), nid(i, j + 1, k),
                                       nid(i, j, k + 1), nid(i + 1, j, k + 1), nid(i + 1, j + 1, k + 1),
                                       nid(i, j + 1, k + 1)]))
    return nodes, elems


def as_arrays(nodes, tris):
    ids = sorted(nodes)
    index = {n: k for k, n in enumerate(ids)}
    return np.array([nodes[n] for n in ids]), np.vectorize(index.get)(tris)


def test_hex_block_surface_is_closed_outward_and_exact():
    nodes, elems = hex_block(3, 2, 2)
    tris = boundary_triangles(nodes, elems)
    # 2 triangles per boundary quad: 2*(3*2 + 3*2 + 2*2) quads
    assert len(tris) == 2 * 2 * (3 * 2 + 3 * 2 + 2 * 2)
    xyz, t = as_arrays(nodes, tris)
    assert enclosed_volume(xyz, t) == pytest.approx(3 * 4 * 6)
    assert enclosed_volume(xyz, t[:, ::-1]) == pytest.approx(-3 * 4 * 6)   # flipped faces -> negative


def test_tet_with_scrambled_node_order_still_faces_outward():
    nodes = {1: (0, 0, 0), 2: (1, 0, 0), 3: (0, 1, 0), 4: (0, 0, 1)}
    for conn in ([1, 2, 3, 4], [2, 1, 3, 4], [4, 3, 2, 1]):
        tris = boundary_triangles(nodes, [("C3D4", conn)])
        xyz, t = as_arrays(nodes, tris)
        assert enclosed_volume(xyz, t) == pytest.approx(1 / 6)


def test_extruded_plate_with_hole_encloses_its_volume():
    import matplotlib.tri as mtri

    r = np.concatenate([np.full(64, 5.0), np.linspace(6, 19, 6).repeat(64)])
    th = np.tile(np.linspace(0, 2 * np.pi, 64, endpoint=False), 7)
    pts = np.column_stack([r * np.cos(th), r * np.sin(th)])
    tri = mtri.Triangulation(pts[:, 0], pts[:, 1])
    c = pts[tri.triangles].mean(axis=1)
    t = tri.triangles[np.hypot(c[:, 0], c[:, 1]) >= 5.0]
    xyz, faces, val = extrude_planar(pts, t, np.hypot(pts[:, 0], pts[:, 1]), thickness=4.0)
    u, v = pts[t[:, 1]] - pts[t[:, 0]], pts[t[:, 2]] - pts[t[:, 0]]
    a = 0.5 * np.abs(u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0]).sum()
    assert enclosed_volume(xyz, faces) == pytest.approx(4.0 * a, rel=1e-12)
    assert len(val) == len(xyz)


def test_compact_drops_unused_nodes_and_keeps_fields_aligned():
    xyz = np.arange(15, dtype=float).reshape(5, 3)
    tris = np.array([[4, 2, 0]])
    x2, t2, f2 = compact(xyz, tris, np.array([10, 11, 12, 13, 14]))
    assert len(x2) == 3
    assert np.allclose(x2[t2[0]], xyz[[4, 2, 0]])
    assert list(f2[t2[0]]) == [14, 12, 10]


def test_read_inp_follows_includes(tmp_path):
    (tmp_path / "mesh.inp").write_text("*NODE\n1, 0, 0, 0\n2, 1, 0, 0\n3, 0, 1, 0\n4, 0, 0, 1\n"
                                       "*ELEMENT, TYPE=C3D4, ELSET=E\n1, 1, 2, 3, 4\n")
    (tmp_path / "job.inp").write_text("*INCLUDE, INPUT=mesh.inp\n*NODE PRINT, NSET=N\nU\n")
    nodes, elems = read_inp(tmp_path / "job.inp")
    assert len(nodes) == 4 and elems == [("C3D4", [1, 2, 3, 4])]


def test_write_scene_records_range_and_counts(tmp_path):
    xyz = np.eye(3)
    p = write_scene(tmp_path / "s", xyz, np.array([[0, 1, 2]]), np.array([1.0, 2.0, 5.0]), field="T", units="K")
    meta = json.loads(p.with_suffix(".json").read_text(encoding="utf-8"))
    assert (meta["vmin"], meta["vmax"], meta["data_max"]) == (1.0, 5.0, 5.0)
    assert (meta["n_vertices"], meta["n_triangles"]) == (3, 1)
    assert set(np.load(p).files) == {"xyz", "tris", "value"}


def test_solid_under_a_height_field_encloses_its_integral():
    from harness.femesh import solid_between

    # u = 1 - x^2 over x in [-1, 1], y in [0, 2]: integral 4/3 * 2; a fine grid gets close
    xs, ys = np.linspace(-1, 1, 201), np.linspace(0, 2, 5)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    xy = np.column_stack([X.ravel(), Y.ravel()])
    ny = len(ys)
    k = (np.arange(len(xs) - 1)[:, None] * ny + np.arange(ny - 1)[None, :]).ravel()
    tris = np.vstack([np.column_stack([k, k + ny, k + ny + 1]), np.column_stack([k, k + ny + 1, k + 1])])
    u = 1 - xy[:, 0] ** 2
    xyz, faces, _ = solid_between(xy, tris, u, u, np.zeros(len(u)))
    assert enclosed_volume(xyz, faces) == pytest.approx(8 / 3, rel=1e-4)

"""Stress linearisation along a stress classification line (SCL) and field sampling in 10-node tetrahedra.

Linearisation follows the method of ASME BPVC Section VIII Division 2, Annex 5-A (described here in our own words):
along a straight line through the wall, from one surface (s = 0) to the other (s = t),
  membrane  sigma_m = (1/t) integral sigma ds                            (every component)
  bending   sigma_b = (6/t^2) integral sigma (t/2 - s) ds                (only the two normal components tangent to
                                                                          the wall: not the component along the
                                                                          line, not the shears)
expressed in local axes (n along the line, m and h tangent to the wall). With the profile written as
sigma(s) ~ sigma_m + sigma_b (1 - 2 s / t), the linearised stress is sigma_m + sigma_b at s = 0 and sigma_m - sigma_b at
s = t; equivalent stresses are von Mises of these tensors (membrane: PL or Pm; membrane + bending: P + Q or PL + Pb,
as the location classifies them).

Sampling: nodal values (e.g. CalculiX's extrapolated, averaged nodal stresses) interpolated with the quadratic shape
functions of the 10-node tetrahedron containing each point (CalculiX/Abaqus C3D10 node order).
"""

from __future__ import annotations

import numpy as np

#: C3D10 edge nodes: node k (4..9) sits between corners EDGES[k-4]
EDGES = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))


def von_mises(s):
    """s: (..., 6) as xx, yy, zz, xy, yz, zx."""
    s = np.asarray(s, float)
    xx, yy, zz, xy, yz, zx = (s[..., k] for k in range(6))
    return np.sqrt(0.5 * ((xx - yy) ** 2 + (yy - zz) ** 2 + (zz - xx) ** 2) + 3 * (xy ** 2 + yz ** 2 + zx ** 2))


def to_matrix(s):
    s = np.asarray(s, float)
    xx, yy, zz, xy, yz, zx = (s[..., k] for k in range(6))
    return np.stack([np.stack([xx, xy, zx], -1), np.stack([xy, yy, yz], -1), np.stack([zx, yz, zz], -1)], -2)


def to_voigt(m):
    return np.stack([m[..., 0, 0], m[..., 1, 1], m[..., 2, 2], m[..., 0, 1], m[..., 1, 2], m[..., 2, 0]], -1)


def rotate(s, axes):
    """Stress components (…, 6) in the frame whose unit row vectors are axes (3, 3): sigma' = R sigma R^T."""
    R = np.asarray(axes, float)
    return to_voigt(R @ to_matrix(s) @ R.T)


def linearize(s_pos, stress, axes):
    """s_pos: (n,) positions along the line from 0 to t (n odd, equally spaced: Simpson); stress: (n, 6) global;
    axes: (3, 3) unit rows (n along the line, m, h tangent to the wall). Returns a dict of local tensors (6,) and
    von Mises equivalents: membrane, bending (only m-m and h-h), membrane +/- bending at s = 0 and s = t."""
    from scipy.integrate import simpson

    s_pos = np.asarray(s_pos, float)
    t = s_pos[-1] - s_pos[0]
    x = s_pos - s_pos[0]
    loc = rotate(stress, axes)  # (n, 6) in (n, m, h): index 0 = nn, 1 = mm, 2 = hh
    mem = simpson(loc, x=x, axis=0) / t
    ben_full = 6 / t ** 2 * simpson(loc * (t / 2 - x)[:, None], x=x, axis=0)
    ben = np.zeros(6)
    ben[1], ben[2] = ben_full[1], ben_full[2]
    # sigma(s) ~ mem + ben (1 - 2 s / t): bending is positive at s = 0 when the stress falls through the wall
    at0, att = mem + ben, mem - ben
    return {"membrane": mem, "bending": ben, "at_start": at0, "at_end": att,
            "membrane_vm": float(von_mises(mem)), "membrane_plus_bending_vm": float(max(von_mises(at0), von_mises(att))),
            "peak_total_vm": float(np.max(von_mises(loc))), "thickness": float(t)}


# --------------------------------------------------------------------------- sampling in C3D10

def tet10_shape(L):
    """Quadratic shape functions at barycentric coordinates L (…, 4)."""
    L = np.asarray(L, float)
    N = np.empty(L.shape[:-1] + (10,))
    for k in range(4):
        N[..., k] = L[..., k] * (2 * L[..., k] - 1)
    for k, (a, b) in enumerate(EDGES):
        N[..., 4 + k] = 4 * L[..., a] * L[..., b]
    return N


class Tet10Sampler:
    """Interpolate nodal fields at arbitrary points of a C3D10 mesh (straight-sided location of the element)."""

    def __init__(self, node_ids, xyz, elems):
        from scipy.spatial import cKDTree

        self.index = {int(n): k for k, n in enumerate(node_ids)}
        self.xyz = np.asarray(xyz, float)
        self.conn = np.vectorize(self.index.get)(np.asarray(elems, int))  # (ne, 10) row indices
        corners = self.xyz[self.conn[:, :4]]  # (ne, 4, 3)
        self.cent = corners.mean(axis=1)
        self.T = np.linalg.inv(np.transpose(corners[:, 1:] - corners[:, :1], (0, 2, 1)))  # (ne, 3, 3)
        self.p0 = corners[:, 0]
        self.size = np.max(np.linalg.norm(corners - self.cent[:, None], axis=2), axis=1)
        self.tree = cKDTree(self.cent)
        self.rmax = float(self.size.max())

    def locate(self, p, tol=1e-9):
        """(element row, barycentric coordinates) of the element containing p, else the nearest by violation."""
        cand = self.tree.query_ball_point(p, self.rmax * 1.01)
        best, best_viol, best_L = None, np.inf, None
        for e in cand:
            l123 = self.T[e] @ (p - self.p0[e])
            L = np.concatenate([[1 - l123.sum()], l123])
            viol = max(0.0, -L.min())
            if viol <= tol:
                return e, L
            if viol < best_viol:
                best, best_viol, best_L = e, viol, L
        if best is None:
            raise ValueError(f"point {p} outside the mesh")
        return best, best_L

    def sample(self, points, fields):
        """fields: (n_nodes, k) in node_ids order; returns (n_points, k) and the max barycentric violation."""
        out, worst = [], 0.0
        F = np.asarray(fields, float)
        for p in np.asarray(points, float):
            e, L = self.locate(p)
            worst = max(worst, max(0.0, -L.min()))
            out.append(tet10_shape(L) @ F[self.conn[e]])
        return np.array(out), worst

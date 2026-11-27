"""Plane frame analysis by the direct stiffness method, first order and second order (steel frame study).

An independent check on the CalculiX frame model: prismatic members with 3 degrees of freedom per node (u, v, theta),
loads at nodes and uniform loads along members, fixed or free supports.

- First order: the exact Euler-Bernoulli member stiffness and fixed-end forces.
- Second order: the exact stiffness of a member under a constant axial force P (stability functions, P-delta inside the
  member) plus the frame's sway (P-Delta, from solving in the deformed equilibrium of the member chords through the
  same functions), iterated until the axial forces settle. Uniform loads use the second-order fixed-end moments.
  Shear deformation is neglected.

Everything here is derived from the beam-column differential equation EI v'''' + P v'' = w (compression P > 0); the
tests check it against exact results (fixed-fixed beam w L^2 / 12, Euler's load, a cantilever under axial and lateral
load: M_base = H tan(kL) / k).
"""

from __future__ import annotations

import math

import numpy as np


def _stability(P: float, EI: float, L: float):
    """(s, c, phi) for axial force P (compression positive): end stiffness s EI / L, carry-over factor c, and the
    ratio of the second-order to the first-order fixed-end moment under a uniform load."""
    if abs(P) * L * L / EI < 1e-6:
        return 4.0, 0.5, 1.0
    u = math.sqrt(abs(P) / EI) * L
    h = u / 2
    if P > 0:   # compression
        d = 2 - 2 * math.cos(u) - u * math.sin(u)
        s = u * (math.sin(u) - u * math.cos(u)) / d
        sc = u * (u - math.sin(u)) / d
        phi = 3 * (math.tan(h) - h) / (h * h * math.tan(h))
    else:       # tension
        d = 2 - 2 * math.cosh(u) + u * math.sinh(u)
        s = u * (u * math.cosh(u) - math.sinh(u)) / d
        sc = u * (math.sinh(u) - u) / d
        phi = 3 * (h - math.tanh(h)) / (h * h * math.tanh(h))
    return s, sc / s, phi


def member_stiffness_local(E, A, I, L, P=0.0):
    """6 x 6 local stiffness (u1, v1, t1, u2, v2, t2) with axial compression P (exact beam-column)."""
    EI = E * I
    s, c, _ = _stability(P, EI, L)
    sc = s * c
    k_t = s * EI / L                       # rotational end stiffness
    k_c = sc * EI / L                      # carry-over
    k_vt = (s + sc) * EI / L ** 2          # moment from a chord rotation
    k_vv = 2 * (s + sc) * EI / L ** 3 - P / L   # sway stiffness, reduced by P / L (P-Delta of the chord)
    a = E * A / L
    return np.array([
        [a, 0, 0, -a, 0, 0],
        [0, k_vv, k_vt, 0, -k_vv, k_vt],
        [0, k_vt, k_t, 0, -k_vt, k_c],
        [-a, 0, 0, a, 0, 0],
        [0, -k_vv, -k_vt, 0, k_vv, -k_vt],
        [0, k_vt, k_c, 0, -k_vt, k_t],
    ])


def fixed_end_local(w, L, P, EI):
    """Fixed-end forces (local, on the member, counterclockwise moments positive) of a uniform load w in local +y."""
    _, _, phi = _stability(P, EI, L)
    M = w * L * L / 12 * phi
    return np.array([0.0, -w * L / 2, -M, 0.0, -w * L / 2, M])


def _springs(kl, fe, springs):
    """Rotational springs at member ends ({2: k_i, 5: k_j}, moment per radian; or (k, offset)): the member's end
    rotation becomes an internal dof joined to the node's rotation through the spring, and is condensed out (exact,
    also under the second-order stiffness; k = 0 is a hinge, k -> infinity a rigid joint). The condensed end moment
    is the spring's moment, which equals the member's. An offset delta makes the spring M = k (theta_node -
    theta_end - delta): a rotation the joint takes before the spring engages (bolt slip into bearing), loaded as a
    lack of fit."""
    sd = sorted(springs)
    n = 6 + len(sd)
    idx = list(range(6))
    for a, d in enumerate(sd):
        idx[d] = 6 + a
    K, F = np.zeros((n, n)), np.zeros(n)
    K[np.ix_(idx, idx)] += kl
    F[idx] += fe
    for a, d in enumerate(sd):
        v = springs[d]
        k, off = (float(v[0]), float(v[1])) if isinstance(v, (tuple, list)) else (float(v), 0.0)
        j = 6 + a
        K[d, d] += k
        K[j, j] += k
        K[d, j] -= k
        K[j, d] -= k
        F[d] -= k * off                  # the spring's moment at zero displacement: k (0 - 0 - delta) on the node
        F[j] += k * off
    keep, rel = list(range(6)), list(range(6, n))
    krr_inv = np.linalg.inv(K[np.ix_(rel, rel)])
    kar = K[np.ix_(keep, rel)]
    recover = (sd, krr_inv, K[np.ix_(rel, keep)], F[rel])   # the member-end rotations from the end displacements
    return K[np.ix_(keep, keep)] - kar @ krr_inv @ K[np.ix_(rel, keep)], F[keep] - kar @ krr_inv @ F[rel], recover


def _condense(kl, fe, rel):
    """Static condensation of the released end rotations: k* = kaa - kar krr^-1 kra, f* = fa - kar krr^-1 fr, put
    back as 6 x 6 / 6 with zero rows and columns at the released dofs (their end moments are then exactly zero)."""
    keep = [d for d in range(6) if d not in rel]
    krr_inv = np.linalg.inv(kl[np.ix_(rel, rel)])
    kar = kl[np.ix_(keep, rel)]
    kc, fc = np.zeros((6, 6)), np.zeros(6)
    kc[np.ix_(keep, keep)] = kl[np.ix_(keep, keep)] - kar @ krr_inv @ kl[np.ix_(rel, keep)]
    fc[keep] = fe[keep] - kar @ krr_inv @ fe[rel]
    return kc, fc


class Frame:
    def __init__(self):
        self.nodes: list[tuple[float, float]] = []
        self.members: list[dict] = []
        self.fixed: dict[int, tuple[bool, bool, bool]] = {}
        self.loads: dict[int, np.ndarray] = {}

    def node(self, x, y):
        self.nodes.append((float(x), float(y)))
        return len(self.nodes) - 1

    def member(self, i, j, E, A, I, w=0.0, release_i=False, release_j=False, spring_i=None, spring_j=None):
        """w: uniform load per length in the member's local +y (perpendicular, to the left of i -> j).
        release_i / release_j: a moment release (hinge) at that end; its rotation is condensed out of the member
        (exact under the second-order stiffness too: a pinned-pinned strut keeps only its axial stiffness and the
        P-Delta string stiffness -P/L). A node whose every member is released there has no rotational stiffness:
        give it support(n, ux=False, uy=False, rz=True).
        spring_i / spring_j: a rotational spring (moment per radian) between the member's end and its node: a
        semi-rigid connection (not with a release at the same end); or (k, delta), the spring engaging only after a
        relative rotation delta (signed as the member's end moment, counterclockwise positive)."""
        if (release_i and spring_i is not None) or (release_j and spring_j is not None):
            raise ValueError("an end takes a release or a spring, not both")
        self.members.append({"i": i, "j": j, "E": E, "A": A, "I": I, "w": float(w),
                             "release": [d for d, r in ((2, release_i), (5, release_j)) if r],
                             "springs": {d: k for d, k in ((2, spring_i), (5, spring_j)) if k is not None}})

    def support(self, n, ux=True, uy=True, rz=True):
        self.fixed[n] = (ux, uy, rz)

    def load(self, n, fx=0.0, fy=0.0, mz=0.0):
        self.loads[n] = self.loads.get(n, np.zeros(3)) + np.array([fx, fy, mz], float)

    def _geom(self, m):
        (x1, y1), (x2, y2) = self.nodes[m["i"]], self.nodes[m["j"]]
        L = math.hypot(x2 - x1, y2 - y1)
        c, s = (x2 - x1) / L, (y2 - y1) / L
        T = np.zeros((6, 6))
        R = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])
        T[:3, :3] = R
        T[3:, 3:] = R
        return L, T

    def solve(self, second_order=False, tol=1e-10, max_iter=200):
        """Displacements; end forces per member (local: N_i, V_i, M_i, N_j, V_j, M_j on the member); axial force
        (compression positive); reactions (global, at every dof: zero where free)."""
        n = len(self.nodes)
        P = np.zeros(len(self.members))
        for it in range(max_iter):
            K = np.zeros((3 * n, 3 * n))
            F = np.zeros(3 * n)
            for nd, f in self.loads.items():
                F[3 * nd:3 * nd + 3] += f
            local = []
            for e, m in enumerate(self.members):
                L, T = self._geom(m)
                Pe = P[e] if second_order else 0.0
                kl = member_stiffness_local(m["E"], m["A"], m["I"], L, Pe)
                fe = fixed_end_local(m["w"], L, Pe, m["E"] * m["I"])
                rec = None
                if m.get("springs"):
                    kl, fe, rec = _springs(kl, fe, m["springs"])
                if m.get("release"):
                    kl, fe = _condense(kl, fe, m["release"])
                dofs = [3 * m["i"], 3 * m["i"] + 1, 3 * m["i"] + 2, 3 * m["j"], 3 * m["j"] + 1, 3 * m["j"] + 2]
                K[np.ix_(dofs, dofs)] += T.T @ kl @ T
                F[dofs] -= T.T @ fe            # equivalent nodal loads
                local.append((dofs, T, kl, fe, rec))
            free = np.ones(3 * n, bool)
            for nd, fl in self.fixed.items():
                for d in range(3):
                    if fl[d]:
                        free[3 * nd + d] = False
            U = np.zeros(3 * n)
            U[free] = np.linalg.solve(K[np.ix_(free, free)], F[free])
            ends = [kl @ (T @ U[dofs]) + fe for dofs, T, kl, fe, _ in local]
            P_new = np.array([(f[0] - f[3]) / 2 for f in ends])
            done = not second_order or np.max(np.abs(P_new - P)) <= tol * max(1.0, float(np.max(np.abs(P_new))))
            P = P_new
            if done:
                break
        else:
            raise RuntimeError("second-order iteration did not converge (near or past the buckling load?)")
        R = np.zeros(3 * n)
        for (dofs, T, kl, fe, _), f in zip(local, ends):
            R[dofs] += T.T @ f
        # each spring's relative rotation theta_node - theta_member_end (the member-end rotation recovered from the
        # condensation)
        self.spring_rotations = {}
        for e, (dofs, T, kl, fe, rec) in enumerate(local):
            if rec is None:
                continue
            sd, krr_inv, krk, fr = rec
            u = T @ U[dofs]
            th = -krr_inv @ (krk @ u + fr)
            self.spring_rotations[e] = {d: float(u[d] - th[a]) for a, d in enumerate(sd)}
        F_applied = np.zeros(3 * n)
        for nd, f in self.loads.items():
            F_applied[3 * nd:3 * nd + 3] += f
        R -= F_applied
        R[free] = 0.0
        self.U, self.end_forces, self.axial, self.reactions, self.iterations = U, ends, P, R, it + 1
        return U

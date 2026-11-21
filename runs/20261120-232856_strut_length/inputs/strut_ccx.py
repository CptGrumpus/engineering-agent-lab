"""Pinned-pinned strut in compression: structured hex mesh and two CalculiX decks.

Geometry (mm, N, MPa): x along the strut from 0 to L, y across the width b, z through the
thickness h (the weak axis: buckling bends through h). C3D8I elements (incompatible modes,
accurate in bending with few elements through the thickness); node (i, j, k) has id
1 + i + (nx+1) (j + (ny+1) k).

Supports (pinned on the centroidal axis): at both ends the node line at z = 0 across the width
is held in z (a knife edge: the end face can rotate about y), and the centre node of each end
line is held in y. Load: equal and opposite compressive forces P on both end faces as uniform
tractions (consistent nodal forces, dead load); the axial rigid-body motion is removed by holding
the midspan axis node in x, whose reaction must then be zero (exact global equilibrium; a first
version held the x = 0 line in x and loaded only the x = L face).

Decks:
  buckle     *BUCKLE for the first modes under a reference load: buckling factor x P_ref = P_cr
  nonlinear  NLGEOM static on the imperfect geometry (initial bow e0 sin(pi x / L) in z added to
             the node coordinates), P ramped in equal increments to P_max; midspan displacements
             and the integration-point stresses of the midspan elements printed every increment
"""

from __future__ import annotations

import numpy as np

PARAMS = ("length_mm", "width_mm", "thickness_mm", "youngs_modulus_MPa", "poisson_ratio",
          "element_size_mm", "imperfection_over_length")


class StrutMesh:
    def __init__(self, params: dict):
        L, b, h = (float(params[k]) for k in ("length_mm", "width_mm", "thickness_mm"))
        s = float(params["element_size_mm"])
        self.nx = 2 * max(1, round(L / s / 2))          # even: a node plane at midspan
        self.ny = 2 * max(1, round(b / s / 2))          # even: a centre node on each end line
        self.nz = 2 * max(1, round(h / s / 2))          # even: a node line at z = 0
        self.L, self.b, self.h = L, b, h
        self.x = L * np.arange(self.nx + 1) / self.nx
        self.y = -b / 2 + b * np.arange(self.ny + 1) / self.ny
        self.z = -h / 2 + h * np.arange(self.nz + 1) / self.nz

    def nid(self, i, j, k):
        return 1 + i + (self.nx + 1) * (j + (self.ny + 1) * k)

    def eid(self, i, j, k):
        return 1 + i + self.nx * (j + self.ny * k)

    def connectivity(self) -> dict:
        out = {}
        for k in range(self.nz):
            for j in range(self.ny):
                for i in range(self.nx):
                    out[self.eid(i, j, k)] = [self.nid(i, j, k), self.nid(i + 1, j, k), self.nid(i + 1, j + 1, k),
                                              self.nid(i, j + 1, k), self.nid(i, j, k + 1), self.nid(i + 1, j, k + 1),
                                              self.nid(i + 1, j + 1, k + 1), self.nid(i, j + 1, k + 1)]
        return out

    def node_lines(self, bow_mm: float = 0.0):
        out = []
        for k, z in enumerate(self.z):
            for j, y in enumerate(self.y):
                for i, x in enumerate(self.x):
                    zz = z + bow_mm * np.sin(np.pi * x / self.L)
                    out.append(f"{self.nid(i, j, k)}, {float(x):.12e}, {float(y):.12e}, {float(zz):.12e}")
        return out

    def midspan_nodes(self):
        i = self.nx // 2
        return [self.nid(i, j, k) for k in range(self.nz + 1) for j in range(self.ny + 1)]

    def midspan_elements(self):
        i0, i1 = self.nx // 2 - 1, self.nx // 2
        return [self.eid(i, j, k) for k in range(self.nz) for j in range(self.ny) for i in (i0, i1)]

    def centreline_nodes(self):
        """Nodes on the axis (y = 0, z = 0) along the strut, in x order."""
        return [self.nid(i, self.ny // 2, self.nz // 2) for i in range(self.nx + 1)]


def _set(name, ids, kind="NSET"):
    ids = list(ids)
    return [f"*{kind}, {kind}={name}"] + [", ".join(str(v) for v in ids[s:s + 12]) for s in range(0, len(ids), 12)]


def _model(params: dict, m: StrutMesh, bow_mm: float) -> list[str]:
    E, nu = float(params["youngs_modulus_MPa"]), float(params["poisson_ratio"])
    kz = m.nz // 2
    left_line = [m.nid(0, j, kz) for j in range(m.ny + 1)]
    right_line = [m.nid(m.nx, j, kz) for j in range(m.ny + 1)]
    mid_axis = [m.nid(m.nx // 2, m.ny // 2, kz)]
    out = ["*HEADING", "Pinned-pinned strut in compression", "*NODE, NSET=NALL"] + m.node_lines(bow_mm)
    out += ["*ELEMENT, TYPE=C3D8I, ELSET=EALL"]
    out += [f"{e}, " + ", ".join(str(v) for v in n) for e, n in m.connectivity().items()]
    out += _set("NLEFTLINE", left_line) + _set("NRIGHTLINE", right_line)
    out += _set("NCENTRE", [m.nid(0, m.ny // 2, kz), m.nid(m.nx, m.ny // 2, kz)])
    out += _set("NMID", m.midspan_nodes()) + _set("EMID", m.midspan_elements(), "ELSET")
    out += _set("NAXIS", m.centreline_nodes()) + _set("NMIDAXIS", mid_axis)
    out += ["*MATERIAL, NAME=AL6061", "*ELASTIC", f"{E!r}, {nu!r}",
            "*SOLID SECTION, ELSET=EALL, MATERIAL=AL6061",
            "*BOUNDARY", "NMIDAXIS, 1, 1, 0.", "NLEFTLINE, 3, 3, 0.", "NRIGHTLINE, 3, 3, 0.",
            "NCENTRE, 2, 2, 0."]
    return out


def end_loads(m: StrutMesh, P: float) -> dict:
    """Consistent nodal forces (x) for uniform compressive tractions P / (b h) on both end faces."""
    loads: dict = {}
    dy, dz = np.diff(m.y), np.diff(m.z)
    for i, sign in ((m.nx, -1.0), (0, 1.0)):
        for k in range(m.nz):
            for j in range(m.ny):
                f = sign * P * dy[j] * dz[k] / (m.b * m.h) / 4
                for jj, kk in ((j, k), (j + 1, k), (j, k + 1), (j + 1, k + 1)):
                    n = m.nid(i, jj, kk)
                    loads[n] = loads.get(n, 0.0) + f
    return loads


def write_buckle_deck(params: dict, m: StrutMesh, p_ref: float, n_modes: int = 3) -> str:
    out = _model(params, m, 0.0)
    # Lanczos accuracy 1e-8 instead of the default 0.01
    out += ["*STEP", "*BUCKLE", f"{n_modes}, 1.e-8", "*CLOAD"]
    out += [f"{n}, 1, {float(f)!r}" for n, f in sorted(end_loads(m, p_ref).items())]
    out += ["*NODE FILE", "U", "*NODE PRINT, NSET=NAXIS", "U", "*END STEP"]
    return "\n".join(out) + "\n"


def write_nonlinear_deck(params: dict, m: StrutMesh, p_max: float, n_inc: int) -> str:
    e0 = float(params["imperfection_over_length"]) * m.L
    out = _model(params, m, e0)
    # tight Newton criteria: the default force residual (0.5 % of the average force) leaves the
    # global equilibrium a few parts per million out
    out += ["*STEP, NLGEOM, INC=1000", "*STATIC, DIRECT", f"{1.0 / n_inc!r}, 1.0",
            "*CONTROLS, PARAMETERS=FIELD", "1.e-7, 1.e-5", "*CLOAD"]
    out += [f"{n}, 1, {float(f)!r}" for n, f in sorted(end_loads(m, p_max).items())]
    out += ["*NODE PRINT, NSET=NMID, FREQUENCY=1", "U",
            "*EL PRINT, ELSET=EMID, FREQUENCY=1", "S",
            "*NODE PRINT, NSET=NMIDAXIS, TOTALS=ONLY, FREQUENCY=1", "RF",
            "*END STEP"]
    return "\n".join(out) + "\n"

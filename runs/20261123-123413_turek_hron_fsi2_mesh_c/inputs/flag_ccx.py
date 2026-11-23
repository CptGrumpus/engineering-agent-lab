"""Turek-Hron elastic flag (the CSM tests): structured plane-strain hex mesh and CalculiX decks.

Geometry (mm, N, s, tonne; benchmark values x 1000): the flag is the bar y in [190, 210], from where
it meets the cylinder (centre (200, 200), radius 50) to x = 600. Its left end lies on the cylinder
arc, x_left(y) = 200 + sqrt(50^2 - (y - 200)^2), and is clamped there (the cylinder is rigid). Point A
is (600, 200), the middle of the free end.

Mesh: nx elements along, ny (even, so A is a node) across, one C3D8I layer of thickness t in z with
every node held in z: plane strain, results per unit depth. Columns of nodes are spaced evenly from
the arc to x = 600 at each y. Node (i, j, k) has id 1 + i + (nx+1)(j + (ny+1) k).

St. Venant-Kirchhoff is CalculiX's *ELASTIC under NLGEOM (constant second Piola-Kirchhoff /
Green-Lagrange moduli), which is the benchmark's material law.

Decks:
  static     NLGEOM, gravity ramped to g in equal increments (CSM1, CSM2)
  frequency  linear modes of the unloaded flag (a check against beam theory)
  dynamic    NLGEOM, gravity applied at t = 0 to the undeformed flag (CSM3); fixed time step,
             alpha method (ALPHA = 0: no numerical damping)
"""

from __future__ import annotations

import numpy as np

PARAMS = ("density_kg_per_m3", "shear_modulus_Pa", "poisson_ratio", "gravity_m_per_s2",
          "flag_length_m", "flag_height_m", "cylinder_radius_m", "element_size_mm")

XC, YC = 200.0, 200.0          # cylinder centre, mm


class FlagMesh:
    def __init__(self, params: dict, thickness_mm: float = 1.0):
        r = float(params["cylinder_radius_m"]) * 1e3
        h = float(params["flag_height_m"]) * 1e3
        # the benchmark's length l = 0.35 runs from the cylinder's rightmost point (250) to 600
        self.x_end = XC + r + float(params["flag_length_m"]) * 1e3
        s = float(params["element_size_mm"])
        self.r, self.h, self.t = r, h, thickness_mm
        self.ny = 2 * max(1, round(h / s / 2))
        self.nx = max(1, round((self.x_end - XC - r) / s))
        self.y = YC - h / 2 + h * np.arange(self.ny + 1) / self.ny
        self.x_left = XC + np.sqrt(r * r - (self.y - YC) ** 2)

    def nid(self, i, j, k):
        return 1 + i + (self.nx + 1) * (j + (self.ny + 1) * k)

    def eid(self, i, j):
        return 1 + i + self.nx * j

    def xy(self, i, j):
        xl = self.x_left[j]
        return xl + (self.x_end - xl) * i / self.nx, self.y[j]

    def node_lines(self):
        out = []
        for k in (0, 1):
            for j in range(self.ny + 1):
                for i in range(self.nx + 1):
                    x, y = self.xy(i, j)
                    out.append(f"{self.nid(i, j, k)}, {float(x):.12e}, {float(y):.12e}, {k * self.t:.12e}")
        return out

    def connectivity(self):
        n = self.nid
        return {self.eid(i, j): [n(i, j, 0), n(i + 1, j, 0), n(i + 1, j + 1, 0), n(i, j + 1, 0),
                                 n(i, j, 1), n(i + 1, j, 1), n(i + 1, j + 1, 1), n(i, j + 1, 1)]
                for j in range(self.ny) for i in range(self.nx)}

    def point_a(self):
        return self.nid(self.nx, self.ny // 2, 0)

    def centreline_nodes(self):
        """Nodes on y = 200 (z = 0), from the clamp to A."""
        return [self.nid(i, self.ny // 2, 0) for i in range(self.nx + 1)]

    def clamp_nodes(self):
        return [self.nid(0, j, k) for k in (0, 1) for j in range(self.ny + 1)]

    def area_mm2(self):
        """Exact area of the mapped flag (trapezoid columns with the arc's chords at each y)."""
        w = self.x_end - self.x_left
        return float(np.trapezoid(w, self.y))


def _set(name, ids, kind="NSET"):
    ids = list(ids)
    return [f"*{kind}, {kind}={name}"] + [", ".join(str(v) for v in ids[s:s + 12]) for s in range(0, len(ids), 12)]


def _model(params: dict, m: FlagMesh) -> list[str]:
    nu = float(params["poisson_ratio"])
    E_MPa = 2 * float(params["shear_modulus_Pa"]) * (1 + nu) * 1e-6
    rho = float(params["density_kg_per_m3"]) * 1e-12          # tonne / mm^3
    out = ["*HEADING", "Turek-Hron elastic flag (CSM), plane strain", "*NODE, NSET=NALL"] + m.node_lines()
    out += ["*ELEMENT, TYPE=C3D8I, ELSET=EALL"]
    out += [f"{e}, " + ", ".join(str(v) for v in n) for e, n in m.connectivity().items()]
    out += _set("NCLAMP", m.clamp_nodes()) + _set("NA", [m.point_a()]) + _set("NCL", m.centreline_nodes())
    out += ["*MATERIAL, NAME=FLAG", "*ELASTIC", f"{E_MPa!r}, {nu!r}", "*DENSITY", f"{rho!r}",
            "*SOLID SECTION, ELSET=EALL, MATERIAL=FLAG",
            "*BOUNDARY", "NCLAMP, 1, 3, 0.", "NALL, 3, 3, 0."]
    return out


def _gravity(params):
    return f"EALL, GRAV, {float(params['gravity_m_per_s2']) * 1e3!r}, 0., -1., 0."


def write_static_deck(params: dict, m: FlagMesh, n_inc: int) -> str:
    out = _model(params, m)
    out += ["*STEP, NLGEOM, INC=1000", "*STATIC, DIRECT", f"{1.0 / n_inc!r}, 1.0",
            "*CONTROLS, PARAMETERS=FIELD", "1.e-8, 1.e-6", "*DLOAD", _gravity(params),
            "*NODE PRINT, NSET=NA, FREQUENCY=1", "U",
            "*NODE PRINT, NSET=NCLAMP, TOTALS=ONLY, FREQUENCY=1", "RF",
            "*NODE PRINT, NSET=NCL, FREQUENCY=1", "U", "*END STEP"]  # one frequency for all prints: see tool-notes
    return "\n".join(out) + "\n"


def write_frequency_deck(params: dict, m: FlagMesh, n_modes: int = 3) -> str:
    out = _model(params, m)
    out += ["*STEP", "*FREQUENCY", f"{n_modes}", "*END STEP"]
    return "\n".join(out) + "\n"


def write_dynamic_deck(params: dict, m: FlagMesh, dt: float, t_end: float, alpha: float = 0.0,
                       residual_rel: float = 1e-8) -> str:
    # residual_rel: CalculiX's force-residual criterion, relative to the time-averaged force. With tiny steps
    # 1e-8 fell below round-off late in the run (iterations crept from 2 to 12, then diverged at dt 0.000625)
    out = _model(params, m)
    out += [f"*STEP, NLGEOM, INC={int(round(t_end / dt)) + 10}", f"*DYNAMIC, DIRECT, ALPHA={alpha!r}",
            f"{dt!r}, {t_end!r}", "*CONTROLS, PARAMETERS=FIELD", f"{residual_rel!r}, 1.e-6",
            "*AMPLITUDE, NAME=STEPON", "0., 1., 1.e6, 1.", "*DLOAD, AMPLITUDE=STEPON", _gravity(params),
            "*NODE PRINT, NSET=NA, FREQUENCY=1", "U", "*END STEP"]
    return "\n".join(out) + "\n"

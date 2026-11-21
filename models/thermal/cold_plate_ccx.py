"""Cold-plate solid: structured hex mesh, CalculiX heat-transfer and thermal-stress decks.

The aluminium plate sits on the coolant channel of models/cfd/cold_plate_openfoam.py
(symmetric construction: one plate on each wall, so one plate is modelled).

Geometry (deck units mm, N, MPa, W, degC): x along the flow, from the channel inlet to
its outlet, with node columns at exactly the CFD wall-face edges, so each solid face on
the wetted surface matches one CFD wall face; y through the plate from the wetted face
(y = gap) to the outer face (y = gap + t); z one element deep (plane problem).
C3D8 (heat) and C3D8I (stress, incompatible modes for bending) on the same nodes;
node (i, j, k) has id 1 + i + (nx+1) (j + (ny+1) k).

C3D8 faces (CalculiX manual): F1 1-2-3-4 (z-), F2 5-8-7-6 (z+), F3 1-5-6-2 (y-),
F4 2-6-7-3 (x+), F5 3-7-8-4 (y+), F6 4-8-5-1 (x-). Wetted face = F3 of the first row,
outer face = F5 of the last row.

Heat transfer (steady): outer face, heat flux from the component over the footprint
(*DFLUX S5, one value per face); wetted face, film to the coolant with the coupling
coefficient h* and one sink temperature per face (*FILM F3); everything else adiabatic.
Thermal stress (static, linear): nodal temperatures from the heat-transfer result
(*TEMPERATURE, every node listed), stress free at the assembly temperature; held in z on
both depth faces (plane strain), in x on both end faces (axial growth and rotation
stopped), in y on the mid-thickness line of each end (height held).
"""

from __future__ import annotations

import numpy as np

PARAMS_SOLID = ("plate_thickness_mm", "plate_conductivity_W_per_mK", "coupling_htc_W_per_m2K",
                "youngs_modulus_MPa", "poisson_ratio", "expansion_per_K", "assembly_temperature_C")
DEPTH_MM = 0.5


class Grid:
    """Structured node grid: x edges (from the CFD wall faces), y through the plate."""

    def __init__(self, x_edges_mm, y0_mm: float, t_mm: float, n_t: int):
        self.x = np.asarray(x_edges_mm, float)
        if n_t % 2:
            raise ValueError("an even number of elements through the thickness is needed "
                             "(the end supports hold the mid-thickness node line)")
        self.y = y0_mm + t_mm * np.arange(n_t + 1) / n_t
        self.nx, self.ny = len(self.x) - 1, n_t

    def nid(self, i, j, k):
        return 1 + i + (self.nx + 1) * (j + (self.ny + 1) * k)

    def eid(self, i, j):
        return 1 + i + self.nx * j

    def node_lines(self):
        out = []
        for k, z in enumerate((0.0, DEPTH_MM)):
            for j, y in enumerate(self.y):
                for i, x in enumerate(self.x):
                    out.append(f"{self.nid(i, j, k)}, {float(x):.12e}, {float(y):.12e}, {z:.12e}")
        return out

    def connectivity(self) -> dict:
        """{element id: 8 node ids in CalculiX C3D8 order}."""
        return {self.eid(i, j): [self.nid(i, j, 0), self.nid(i + 1, j, 0), self.nid(i + 1, j + 1, 0),
                                 self.nid(i, j + 1, 0), self.nid(i, j, 1), self.nid(i + 1, j, 1),
                                 self.nid(i + 1, j + 1, 1), self.nid(i, j + 1, 1)]
                for j in range(self.ny) for i in range(self.nx)}

    def element_lines(self):
        return [f"{e}, " + ", ".join(str(v) for v in n) for e, n in self.connectivity().items()]

    def nset(self, name, ids):
        ids = list(ids)
        rows = [", ".join(str(v) for v in ids[s:s + 12]) for s in range(0, len(ids), 12)]
        return [f"*NSET, NSET={name}"] + rows

    def row_nodes(self, j):
        return [self.nid(i, j, k) for k in (0, 1) for i in range(self.nx + 1)]


def _mesh(grid: Grid, etype: str) -> list[str]:
    return (["*NODE, NSET=NALL"] + grid.node_lines()
            + [f"*ELEMENT, TYPE={etype}, ELSET=EALL"] + grid.element_lines()
            + grid.nset("NWET", grid.row_nodes(0)) + grid.nset("NOUT", grid.row_nodes(grid.ny)))


def write_thermal_deck(params: dict, grid: Grid, outer_flux_W_per_m2, sink_C) -> str:
    """outer_flux (W/m2) and sink (degC): one value per x face (len nx)."""
    k = float(params["plate_conductivity_W_per_mK"]) * 1e-3     # W/(mm K)
    h = float(params["coupling_htc_W_per_m2K"]) * 1e-6          # W/(mm2 K)
    q = np.asarray(outer_flux_W_per_m2, float) * 1e-6            # W/mm2
    sink = np.asarray(sink_C, float)
    if len(q) != grid.nx or len(sink) != grid.nx:
        raise ValueError("one flux and one sink temperature per x face")
    t0 = float(np.mean(sink))
    out = ["*HEADING", "Cold plate: steady conduction, component flux on the outer face, film to the coolant"]
    out += _mesh(grid, "C3D8")
    out += ["*MATERIAL, NAME=AL6061", "*CONDUCTIVITY", f"{k!r}",
            "*SOLID SECTION, ELSET=EALL, MATERIAL=AL6061",
            "*INITIAL CONDITIONS, TYPE=TEMPERATURE", f"NALL, {t0!r}",
            "*STEP", "*HEAT TRANSFER, STEADY STATE", "1., 1.", "*DFLUX"]
    out += [f"{grid.eid(i, grid.ny - 1)}, S5, {float(q[i])!r}" for i in range(grid.nx) if q[i] != 0.0]
    out += ["*FILM"]
    out += [f"{grid.eid(i, 0)}, F3, {float(sink[i])!r}, {h!r}" for i in range(grid.nx)]
    # every nodal temperature again in the .dat (7 significant digits; the .frd has 6)
    out += ["*NODE FILE", "NT", "*NODE PRINT, NSET=NALL", "NT", "*END STEP"]
    return "\n".join(out) + "\n"


def write_stress_deck(params: dict, grid: Grid, node_temperature: dict) -> str:
    """node_temperature: {node id: degC} for every node."""
    E, nu = float(params["youngs_modulus_MPa"]), float(params["poisson_ratio"])
    a, t_ref = float(params["expansion_per_K"]), float(params["assembly_temperature_C"])
    jm = grid.ny // 2
    ends = [grid.nid(i, j, k) for k in (0, 1) for j in range(grid.ny + 1) for i in (0, grid.nx)]
    mid = [grid.nid(i, jm, k) for k in (0, 1) for i in (0, grid.nx)]
    left = [grid.nid(0, j, k) for k in (0, 1) for j in range(grid.ny + 1)]
    right = [grid.nid(grid.nx, j, k) for k in (0, 1) for j in range(grid.ny + 1)]
    z0 = [grid.nid(i, j, 0) for j in range(grid.ny + 1) for i in range(grid.nx + 1)]
    z1 = [grid.nid(i, j, 1) for j in range(grid.ny + 1) for i in range(grid.nx + 1)]
    out = ["*HEADING", "Cold plate: thermal stress, plane strain, clamped at both ends"]
    out += _mesh(grid, "C3D8I")
    out += grid.nset("NENDS", ends) + grid.nset("NMID", mid) + grid.nset("NLEFT", left)
    out += grid.nset("NRIGHT", right) + grid.nset("NZ0", z0) + grid.nset("NZ1", z1)
    out += ["*MATERIAL, NAME=AL6061", "*ELASTIC", f"{E!r}, {nu!r}", "*EXPANSION", f"{a!r}",
            "*SOLID SECTION, ELSET=EALL, MATERIAL=AL6061",
            "*INITIAL CONDITIONS, TYPE=TEMPERATURE", f"NALL, {t_ref!r}",
            "*BOUNDARY", "NZ0, 3, 3, 0.", "NZ1, 3, 3, 0.", "NENDS, 1, 1, 0.", "NMID, 2, 2, 0.",
            "*STEP", "*STATIC", "*TEMPERATURE"]
    out += [f"{nid}, {float(T)!r}" for nid, T in sorted(node_temperature.items())]
    # integration-point stresses in the .dat: the study extrapolates them to the nodes itself
    # (the .frd nodal stresses of C3D8/C3D8I are 4e-5 low even for a uniform field)
    out += ["*NODE FILE", "U, NT", "*EL FILE", "S", "*EL PRINT, ELSET=EALL", "S",
            "*NODE PRINT, NSET=NLEFT, TOTALS=ONLY", "RF",
            "*NODE PRINT, NSET=NRIGHT, TOTALS=ONLY", "RF",
            "*END STEP"]
    return "\n".join(out) + "\n"

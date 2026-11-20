"""CAD-to-FEA modal pipeline: clamped bracket arm.

1. CadQuery builds the arm (x along the length from the clamped root at x = 0,
   y across the width, z through the thickness, centred) and exports STEP.
2. A Gmsh .geo script meshes the solid with 10-node tetrahedra of uniform size
   and writes an Abaqus .inp.
3. This module writes the CalculiX deck: steel with density, the root face
   fully fixed, and a *FREQUENCY step for the first n modes.

Units: N, mm, tonne, s. numpy floats are cast before formatting (numpy 2
prints np.float64(...)); the deck is always built from the mesh it includes.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

PARAMS = ("length_mm", "width_mm", "thickness_mm", "youngs_modulus_MPa", "poisson_ratio",
          "density_t_per_mm3", "element_size_mm", "n_modes")

TOL = 1e-6


def build_step(params: dict, path: Path) -> float:
    """Arm solid to STEP. Returns its volume (mm^3)."""
    import cadquery as cq

    L, b, h = (float(params[k]) for k in ("length_mm", "width_mm", "thickness_mm"))
    arm = cq.Workplane("XY").box(L, b, h, centered=(False, True, True))
    cq.exporters.export(arm, str(path))
    return float(arm.val().Volume())


def write_geo(params: dict, path: Path, step_name: str = "arm.step") -> None:
    hsize = float(params["element_size_mm"])
    path.write_text(f"""SetFactory("OpenCASCADE");
Merge "{step_name}";
Mesh.MeshSizeMax = {hsize!r}; Mesh.MeshSizeMin = {hsize!r};
Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 0;
Physical Volume("ARM") = Volume{{:}};
""", encoding="utf-8")


def read_mesh_nodes(mesh_inp: Path) -> tuple[np.ndarray, np.ndarray]:
    text = Path(mesh_inp).read_text(encoding="utf-8")
    block = text.split("*NODE", 1)[1].split("*", 1)[0]
    rows = np.array([[float(v) for v in ln.split(",")] for ln in block.strip().splitlines()])
    return rows[:, 0].astype(int), rows[:, 1:4]


def write_deck(params: dict, mesh_inp: Path, deck: Path) -> dict:
    ids, xyz = read_mesh_nodes(mesh_inp)
    root = ids[np.isclose(xyz[:, 0], 0.0, atol=TOL)]
    if len(root) < 3:
        raise RuntimeError("no nodes found on the root face x = 0")
    E, nu = float(params["youngs_modulus_MPa"]), float(params["poisson_ratio"])
    rho, n = float(params["density_t_per_mm3"]), int(params["n_modes"])
    deck.write_text(
        f"*INCLUDE, INPUT={Path(mesh_inp).name}\n*NSET, NSET=ROOT\n"
        + "\n".join(str(int(i)) for i in root) + "\n"
        + f"*MATERIAL, NAME=STEEL\n*ELASTIC\n{E!r}, {nu!r}\n*DENSITY\n{rho!r}\n"
        + "*SOLID SECTION, ELSET=ARM, MATERIAL=STEEL\n"
        + "*BOUNDARY\nROOT, 1, 3, 0.\n"
        + f"*STEP\n*FREQUENCY\n{n}\n*NODE FILE\nU\n*END STEP\n",
        encoding="utf-8")
    return {"nodes": int(len(ids)), "root_nodes": int(len(root))}

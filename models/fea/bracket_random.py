"""Random vibration of the clamped bracket arm (study C): the CalculiX deck.

Same arm, mesh and material as study 4 (models/fea/bracket_modal.py): x along the length from the clamped root at
x = 0, y across the width, z through the thickness, both centred. The deck has
1. a *FREQUENCY step (STORAGE=YES) for n modes, writing mode shapes (U) and modal stresses (S) to the .frd and the
   participation factors and effective masses to the .dat;
2. one *STEADY STATE DYNAMICS step per axis with a unit base acceleration (*BASE MOTION) and modal damping, printing
   the tip-centre displacement: the independent check of the Python modal superposition (CalculiX reports absolute
   displacement and damps absolute velocity; see build-model/references/tool-notes.md).

Units: N, mm, tonne, s (accelerations in mm/s^2, stresses in MPa).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

PARAMS = ("length_mm", "width_mm", "thickness_mm", "youngs_modulus_MPa", "poisson_ratio", "density_t_per_mm3",
          "element_size_mm", "n_modes", "damping_ratio")

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


def tip_node(ids: np.ndarray, xyz: np.ndarray, length: float) -> int:
    """The node on the free end nearest its centre (y = z = 0)."""
    end = np.isclose(xyz[:, 0], length, atol=TOL)
    if not end.any():
        raise RuntimeError("no nodes on the free end")
    k = np.flatnonzero(end)[np.argmin(np.hypot(xyz[end, 1], xyz[end, 2]))]
    return int(ids[k])


def write_deck(params: dict, mesh_inp: Path, deck: Path, f_lo: float, f_hi: float, n_points: int) -> dict:
    ids, xyz = read_mesh_nodes(mesh_inp)
    root = ids[np.isclose(xyz[:, 0], 0.0, atol=TOL)]
    if len(root) < 3:
        raise RuntimeError("no nodes found on the root face x = 0")
    tip = tip_node(ids, xyz, float(params["length_mm"]))
    E, nu = float(params["youngs_modulus_MPa"]), float(params["poisson_ratio"])
    rho, n, zeta = float(params["density_t_per_mm3"]), int(params["n_modes"]), float(params["damping_ratio"])
    harmonic = "".join(
        f"*STEP\n*STEADY STATE DYNAMICS\n{f_lo!r}, {f_hi!r}, {int(n_points)}, 1.\n*MODAL DAMPING\n1, {n}, {zeta!r}\n"
        f"*BASE MOTION, DOF={dof}, AMPLITUDE=UNIT, TYPE=ACCELERATION\n*NODE PRINT, NSET=TIP\nU\n*END STEP\n"
        for dof in (1, 2, 3))
    deck.write_text(
        f"*INCLUDE, INPUT={Path(mesh_inp).name}\n*NSET, NSET=ROOT\n"
        + "\n".join(str(int(i)) for i in root) + "\n"
        + f"*NSET, NSET=TIP\n{tip}\n"
        + f"*MATERIAL, NAME=STEEL\n*ELASTIC\n{E!r}, {nu!r}\n*DENSITY\n{rho!r}\n"
        + "*SOLID SECTION, ELSET=ARM, MATERIAL=STEEL\n"
        + "*BOUNDARY\nROOT, 1, 3, 0.\n"
        + "*AMPLITUDE, NAME=UNIT\n0., 1., 1.e6, 1.\n"
        + f"*STEP\n*FREQUENCY, STORAGE=YES\n{n}\n*NODE FILE\nU\n*EL FILE\nS\n*END STEP\n"
        + harmonic,
        encoding="utf-8")
    return {"nodes": int(len(ids)), "root_nodes": int(len(root)), "tip_node": tip}

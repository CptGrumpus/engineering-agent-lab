"""Strap with a central hole: proof load beyond notch yield, then unloading (CalculiX plasticity).

Geometry and mesh come from models/fea/strap_hole.py (CadQuery quarter face -> STEP -> Gmsh
6-node triangles refined at the hole), passed in by the backend so both sources are saved with
each run. This module writes the plastic deck for that mesh:

- plane stress through a thin analysed layer (strap_hole.ANALYSIS_THICKNESS_RATIO x hole
  diameter) with the forces scaled by the same factor, as in the elastic strap study (CalculiX
  expands plane-stress elements into one-layer wedges, which is not plane stress for a thick plate)
- material: elastic, then isotropic hardening along the case's (plastic strain, stress) table
- symmetry on x = 0 and y = 0; uniform traction on the far end as consistent nodal forces
- step 1 ramps the traction to the proof load, step 2 ramps it back to zero (geometrically linear,
  small strain); tight Newton criteria so the global equilibrium is exact to 1e-7
- output at the end of each step: displacements, stresses, total strains and equivalent plastic
  strain on the 2D nodes, and the reaction total on the x = 0 symmetry edge
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

PARAMS_PLASTIC = ("plastic_strain", "plastic_stress_MPa")


def edge_loads(params: dict, ids, x, y, analysis_ratio: float, tol: float = 1e-6):
    """Consistent nodal forces on the loaded edge x = L/2 (thin analysed layer); returns
    (node ids, forces, force scale)."""
    L2, W2 = float(params["length_mm"]) / 2, float(params["width_mm"]) / 2
    t, F = float(params["thickness_mm"]), float(params["axial_load_N"])
    scale = analysis_ratio * float(params["hole_diameter_mm"]) / t
    end = np.isclose(x, L2, atol=tol)
    order = np.argsort(y[end])
    eids, ey = ids[end][order], y[end][order]
    if len(eids) < 3 or len(eids) % 2 == 0:
        raise RuntimeError(f"loaded edge has {len(eids)} nodes; expected an odd count")
    q = scale * (F / 2) / W2
    load = np.zeros(len(eids))
    for k in range(0, len(eids) - 2, 2):
        seg = ey[k + 2] - ey[k]
        load[k] += q * seg / 6
        load[k + 1] += q * seg * 4 / 6
        load[k + 2] += q * seg / 6
    return eids, load, scale


def write_plastic_deck(params: dict, mesh_inp: Path, deck: Path, read_mesh_nodes, analysis_ratio: float,
                       tol: float = 1e-6) -> dict:
    ids, x, y = read_mesh_nodes(mesh_inp)
    eids, load, scale = edge_loads(params, ids, x, y, analysis_ratio, tol)
    xsym = ids[np.isclose(x, 0.0, atol=tol)]
    ysym = ids[np.isclose(y, 0.0, atol=tol)]
    ta = analysis_ratio * float(params["hole_diameter_mm"])
    E, nu = float(params["youngs_modulus_MPa"]), float(params["poisson_ratio"])
    ep = [float(v) for v in params["plastic_strain"]]
    sp = [float(v) for v in params["plastic_stress_MPa"]]

    def nset(name, arr):
        return f"*NSET, NSET={name}\n" + "\n".join(str(int(i)) for i in arr) + "\n"

    plastic = "".join(f"{s!r}, {e!r}\n" for s, e in zip(sp, ep))
    up = "".join(f"{int(i)}, 1, {float(f)!r}\n" for i, f in zip(eids, load))
    down = "".join(f"{int(i)}, 1, 0.\n" for i in eids)
    # FREQUENCY larger than the increment count: only the end of each step is written (files and prints)
    out = ("*NODE FILE, OUTPUT=2D, FREQUENCY=1000\nU\n*EL FILE, OUTPUT=2D, FREQUENCY=1000\nS, E, PEEQ\n"
           "*NODE PRINT, NSET=XSYM, TOTALS=ONLY, FREQUENCY=1000\nRF\n")
    controls = "*CONTROLS, PARAMETERS=FIELD\n1.e-7, 1.e-5\n"
    deck.write_text(
        f"*INCLUDE, INPUT={Path(mesh_inp).name}\n" + nset("XSYM", xsym) + nset("YSYM", ysym)
        + f"*MATERIAL, NAME=AL\n*ELASTIC\n{E!r}, {nu!r}\n*PLASTIC\n{plastic}"
        + f"*SOLID SECTION, ELSET=PLATE, MATERIAL=AL\n{ta!r}\n"
        + "*BOUNDARY\nXSYM, 1, 1, 0.\nYSYM, 2, 2, 0.\n"
        + "*STEP, INC=1000\n*STATIC\n0.05, 1., 1.e-5, 0.05\n" + controls + "*CLOAD\n" + up + out + "*END STEP\n"
        + "*STEP, INC=1000\n*STATIC\n0.05, 1., 1.e-5, 0.05\n" + controls + "*CLOAD, OP=NEW\n" + down + out
        + "*END STEP\n",
        encoding="utf-8")
    return {"nodes": int(len(ids)), "loaded_edge_nodes": int(len(eids)),
            "applied_load_N": float(load.sum()) / scale, "force_scale": scale, "analysis_thickness_mm": ta}

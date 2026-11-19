"""FreeCAD + CalculiX cantilever (model under test). Runs inside freecadcmd.

    freecadcmd cantilever_freecad.py   (reads CANTILEVER_INPUT env var -> JSON)

Input JSON keys (mm, N, MPa):
    length_mm, width_mm, height_mm, youngs_modulus_MPa, poisson_ratio,
    tip_load_N, mesh_size_mm, element_order ("1st" | "2nd"), workdir

Geometry: Part::Box, x = length, y = width, z = height.
    Face1 (x = 0)  fixed (all DOF)
    Face2 (x = L)  total force tip_load_N in -z, distributed by FreeCAD over the face
Mesh: Gmsh tetrahedra, CharacteristicLengthMax = mesh_size_mm.
Writes into workdir: cantilever.FCStd, the CalculiX deck (*.inp), results (*.frd,
*.dat), and freecad_summary.json.
"""

import json
import os
import sys
import traceback

import FreeCAD as App
import ObjectsFem
from femmesh.gmshtools import GmshTools
from femtools import ccxtools


def main():
    with open(os.environ["CANTILEVER_INPUT"], encoding="utf-8") as fh:
        p = json.load(fh)
    work = p["workdir"]
    summary = {"freecad_version": ".".join(App.Version()[:3]), "ok": False}

    doc = App.newDocument("cantilever")
    beam = doc.addObject("Part::Box", "Beam")
    beam.Length = p["length_mm"]
    beam.Width = p["width_mm"]
    beam.Height = p["height_mm"]
    doc.recompute()

    analysis = ObjectsFem.makeAnalysis(doc, "Analysis")
    solver = ObjectsFem.makeSolverCalculiXCcxTools(doc, "CalculiX")
    solver.AnalysisType = "static"
    solver.GeometricalNonlinearity = "linear"
    solver.ThermoMechSteadyState = False
    solver.MatrixSolverType = "default"
    solver.IterationsControlParameterTimeUse = False
    analysis.addObject(solver)

    material = ObjectsFem.makeMaterialSolid(doc, "Material")
    mat = material.Material
    mat["Name"] = "LinearElasticSteel"
    mat["YoungsModulus"] = f"{p['youngs_modulus_MPa']} MPa"
    mat["PoissonRatio"] = str(p["poisson_ratio"])
    mat["Density"] = "7850 kg/m^3"
    material.Material = mat
    analysis.addObject(material)

    fixed = ObjectsFem.makeConstraintFixed(doc, "Fixed")
    fixed.References = [(beam, "Face1")]
    analysis.addObject(fixed)

    load = ObjectsFem.makeConstraintForce(doc, "TipLoad")
    load.References = [(beam, "Face2")]
    load.Force = f"{abs(p['tip_load_N'])} N"
    load.Direction = (beam, ["Edge1"])  # Edge1 runs along z
    analysis.addObject(load)
    doc.recompute()
    dv = load.DirectionVector
    # point the load in -z regardless of Edge1's orientation
    if dv.z > 0:
        load.Reversed = not load.Reversed
        doc.recompute()
    summary["load_direction"] = [round(c, 12) for c in load.DirectionVector]

    mesh = ObjectsFem.makeMeshGmsh(doc, "Mesh")
    mesh.Shape = beam
    mesh.CharacteristicLengthMax = f"{p['mesh_size_mm']} mm"
    mesh.ElementOrder = p.get("element_order", "2nd")
    mesh.ElementDimension = "3D"
    analysis.addObject(mesh)
    doc.recompute()
    err = GmshTools(mesh).create_mesh()
    if err:
        raise RuntimeError(f"gmsh: {err}")
    doc.recompute()
    fem = mesh.FemMesh
    summary.update(nodes=fem.NodeCount, volumes=fem.VolumeCount)

    fea = ccxtools.FemToolsCcx(analysis, solver)
    fea.update_objects()
    fea.setup_working_dir(work)
    fea.setup_ccx()
    msg = fea.check_prerequisites()
    if msg:
        raise RuntimeError(f"prerequisites: {msg}")
    fea.write_inp_file()
    fea.ccx_run()
    summary["inp_file"] = os.path.basename(fea.inp_file_name)
    summary["ccx_binary"] = getattr(fea, "ccx_binary", None)
    doc.saveAs(os.path.join(work, "cantilever.FCStd"))
    summary["ok"] = True
    return summary


if __name__ == "__main__" or True:  # freecadcmd runs scripts with a different __name__
    try:
        out = main()
    except Exception:
        out = {"ok": False, "error": traceback.format_exc()}
    work = json.load(open(os.environ["CANTILEVER_INPUT"], encoding="utf-8"))["workdir"]
    with open(os.path.join(work, "freecad_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    sys.stdout.flush()

"""Run in the Pyleecan environment: writes the motor cross-section (every surface as a labelled polygon, in metres)
for scripts/make_drawings.py.

    PYTHONUTF8=1 ~/.venvs/pyleecan/Scripts/python.exe scripts/export_motor_geometry.py build/drawings/motor_geometry.json
"""
import json, sys
from pyleecan.Functions.load import load
m = load("models/motor/Toyota_Prius_ORNL.json")
out = []
for surf in m.build_geometry(sym=1):
    pts = []
    for ln in surf.get_lines():
        z = ln.discretize(24)
        pts += [[float(c.real), float(c.imag)] for c in z]
    out.append({"label": surf.label, "pts": pts})
json.dump({"surfaces": out, "Rext": m.stator.Rext, "Rint": m.rotor.Rint, "Rbore": m.stator.Rint, "Rrot": m.rotor.Rext}, open(sys.argv[1], "w"))
print(len(out), sorted({s["label"].split("_")[0] + "_" + s["label"].split("_")[1] if "_" in s["label"] else s["label"] for s in out})[:12])

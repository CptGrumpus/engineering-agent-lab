"""Mode shapes of the fan rotor (study 23) for the site's drawing and Campbell figure.

    ~/.venvs/ross/Scripts/python.exe -I scripts/export_fan_modes.py

The run saved its natural frequencies against speed (Campbell) but not the mode shapes. This rebuilds each point's
rotor from the run's own copy of the model (runs/<run>/inputs/fan_rotor.py, with that point's params.json), takes
the modes at the top of the operating range (3,000 rpm), and refuses to write unless every frequency matches the
run's recorded Campbell values at that speed to 0.01 %: the shapes then belong to the verified model, not to a new
one. Writes build/drawings/fan_rotor_modes.json; make_drawings.py and make_figures.py read it.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
RUN = REPO / "runs" / "20261123-162721_rotor_fan_design"
SPEED = 3000.0
NMODES = 4                    # backward and forward of the first two modes


def main():
    spec = importlib.util.spec_from_file_location("fan_rotor_run", RUN / "inputs" / "fan_rotor.py")
    fan = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fan)
    out = {"run": RUN.name, "speed_rpm": SPEED, "points": {}}
    for pdir in sorted((RUN / "points").iterdir()):
        params = json.loads((pdir / "solver" / "params.json").read_text(encoding="utf-8"))
        rec = json.loads((pdir / "point.json").read_text(encoding="utf-8"))["solver_outputs"]
        i = rec["campbell_rpm"].index(SPEED)
        recorded = np.asarray(rec["campbell_wd_rpm"][i][:NMODES])
        rotor = fan.build(params)
        modal = rotor.run_modal(speed=SPEED * fan.RPM, num_modes=2 * NMODES)
        wd = np.asarray(modal.wd[:NMODES]) / fan.RPM
        err = np.abs(wd / recorded - 1)
        assert err.max() < 1e-4, f"{pdir.name}: frequencies {wd} differ from the run's {recorded}"
        ev = np.asarray(modal.evectors)
        ndof = rotor.number_dof
        nodes = np.asarray(rotor.nodes_pos)
        shapes = []
        for j in range(NMODES):
            x = ev[0::ndof, j][: len(nodes)]                     # lateral displacement in x at each node
            x = x * np.exp(-1j * np.angle(x[np.argmax(np.abs(x))]))   # phase so the largest entry is real
            x = np.real(x)
            x = x / np.max(np.abs(x))
            shapes.append({"wd_rpm": float(wd[j]), "whirl": float(rec["campbell_whirl"][i][j]), "x": x.tolist()})
        out["points"][pdir.name] = {"shaft_diameter_m": params["shaft_diameter_m"],
                                    "bearing_stiffness_N_per_m": params["bearing_stiffness_N_per_m"],
                                    "nodes_m": nodes.tolist(), "modes": shapes, "max_freq_error": float(err.max())}
        print(pdir.name, np.round(wd), f"max error {err.max():.1e}")
    dst = REPO / "build" / "drawings" / "fan_rotor_modes.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out), encoding="utf-8")
    print("wrote", dst.relative_to(REPO))


if __name__ == "__main__":
    sys.exit(main())

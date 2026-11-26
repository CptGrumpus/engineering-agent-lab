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


CRIT_POINT = "p04_d65_kb1e7"  # the recommended 65 mm shaft at the soft end of the bearing band, the governing case


def critical(fan) -> int:
    """The forward mode at the first forward critical speed of the recommended design, for the 3D render.

    Refuses to write unless the rebuilt rotor's mass equals the run's exactly, and the forward mode's damped
    frequency at the recorded critical speed equals that speed to 0.1 % (the run interpolates the Campbell
    crossing linearly between 100 rpm points). Writes build/render/fan_rotor_critical.json."""
    pdir = RUN / "points" / CRIT_POINT
    params = json.loads((pdir / "solver" / "params.json").read_text(encoding="utf-8"))
    rec = json.loads((pdir / "point.json").read_text(encoding="utf-8"))
    n_c = float(rec["metrics"]["first_forward_critical_rpm"])
    fwd = [c for c in rec["solver_outputs"]["critical_speeds"] if c["whirl"] == "forward"][0]
    assert abs(fwd["rpm"] / n_c - 1) < 1e-12, (fwd, n_c)
    rotor = fan.build(params)
    assert abs(float(rotor.m) / rec["metrics"]["rotor_mass_kg"] - 1) < 1e-12, (rotor.m, rec["metrics"]["rotor_mass_kg"])
    modal = rotor.run_modal(speed=n_c * fan.RPM, num_modes=12)
    j = int(fwd["mode"])
    wd = float(modal.wd[j]) / fan.RPM
    assert abs(wd / n_c - 1) < 1e-3, f"mode {j} at {wd:.2f} rpm, the critical is {n_c:.2f}"
    whirl = float(np.asarray(modal.whirl_values())[j]) if callable(getattr(modal, "whirl_values", None)) \
        else float(np.asarray(modal.whirl_values)[j])
    assert whirl < 0.25, f"mode {j} is not forward (whirl {whirl})"
    ev = np.asarray(modal.evectors)[:, j]
    ndof = rotor.number_dof
    nodes = np.asarray(rotor.nodes_pos)
    x, y = ev[0::ndof][: len(nodes)], ev[1::ndof][: len(nodes)]
    ph = np.exp(-1j * np.angle(x[np.argmax(np.abs(x))]))
    x, y = x * ph, y * ph
    s = np.max(np.abs(x))
    out = {"run": RUN.name, "point": CRIT_POINT, "critical_rpm": n_c, "mode": j, "wd_rpm": wd, "whirl": whirl,
           "rotor_mass_kg": float(rotor.m), "nodes_m": nodes.tolist(),
           "x": (np.real(x) / s).tolist(), "y_imag": (np.imag(y) / s).tolist(),
           "shaft_diameter_m": params["shaft_diameter_m"], "disc_diameter_m": params["disc_diameter_m"],
           "disc_width_m": params["disc_width_m"], "disc_node": int(params["n_elements"]) // 2,
           "bearing_stiffness_N_per_m": params["bearing_stiffness_N_per_m"],
           "speed_max_rpm": params["speed_max_rpm"], "margin_pct": rec["metrics"].get("separation_margin_pct")}
    dst = REPO / "build" / "render" / "fan_rotor_critical.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"mode {j} at {wd:.2f} rpm against the critical {n_c:.2f} ({wd / n_c - 1:+.1e}), whirl {whirl:.2f}, "
          f"mass {rotor.m:.6f} kg; wrote {dst.relative_to(REPO)}")
    return 0


def main():
    spec = importlib.util.spec_from_file_location("fan_rotor_run", RUN / "inputs" / "fan_rotor.py")
    fan = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fan)
    if "--critical" in sys.argv:
        return critical(fan)
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

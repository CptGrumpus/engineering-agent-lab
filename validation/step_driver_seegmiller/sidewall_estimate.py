"""Study 19 part 2: a hand estimate of the tunnel's side-wall blockage, to test the page's explanation of the
pressure-recovery miss (ours 0.1534, measured 0.1307: 0.0227 high), before any 3D model.

The 2D model has no side walls. In the tunnel (span 15.1 cm = 11.9 step heights) a boundary layer grows on each side
wall; downstream of the step it grows faster, against the pressure rise. Its displacement thickness narrows the core
flow, which then runs faster and recovers less pressure. Estimate:
  1. the core velocity along the tunnel from the 2D model's own wall pressure: U(x) / U_ref = sqrt(1 - Cp(x)) with Cp
     referred to x = -4 H (the 2D model's run, step-side wall);
  2. each side wall's momentum thickness by the momentum integral, d theta / dx = Cf / 2 - (Hs + 2) (theta / U) dU/dx,
     from theta = 1.70 mm at x = -4 H (Re_theta 5000 at 44.2 m/s: the case description's inflow, the side walls taken as
     the floor's), Cf by Ludwieg-Tillmann, the shape factor Hs held at a value bracketed 1.4 to 1.8 (it grows in the
     adverse gradient; held constant it brackets the answer);
  3. the core's effective width W - 2 delta*, delta* = Hs theta: continuity gives U_3D / U_2D = (W - 2 delta*_-4H) /
     (W - 2 delta*(x)), and the recovery change Delta Cp(30 H) = (U_2D(30 H)^2 - U_3D(30 H)^2) / U_ref^2.
An estimate of the order, not a model: the side walls' own state at the step is assumed, the corner flows and the
floor-side-wall interaction are left out.

    .venv/Scripts/python.exe validation/step_driver_seegmiller/sidewall_estimate.py [run_id] [point_label]
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
H_STEP = 12.7          # mm (Driver and Seegmiller)
SPAN = 151.0           # mm
U_REF = 44.2           # m/s
NU = 1.5e-5            # m^2/s, air
THETA0 = 5000 * NU / U_REF * 1e3   # mm, Re_theta 5000 at x = -4 H


def cp_2d(run_id: str, label: str):
    o = json.loads((ROOT / "runs" / run_id / "points" / label / "point.json").read_text(encoding="utf-8"))["solver_outputs"]
    x, cp = np.asarray(o["profiles"]["x_p_over_h"]), np.asarray(o["profiles"]["cp"])
    cp = cp - np.interp(-4.0, x, cp)
    return x, cp


def estimate(x_h, cp, Hs: float) -> dict:
    m = (x_h >= -4.0) & (x_h <= 30.0)
    xh, c = x_h[m], cp[m]
    x = xh * H_STEP                                   # mm
    U = U_REF * np.sqrt(np.clip(1.0 - c, 1e-6, None))
    theta = np.zeros_like(x)
    theta[0] = THETA0
    for i in range(len(x) - 1):
        dx = x[i + 1] - x[i]
        Re_t = U[i] * theta[i] * 1e-3 / NU
        cf = 0.246 * 10 ** (-0.678 * Hs) * Re_t ** -0.268
        dUdx = (U[i + 1] - U[i]) / dx
        theta[i + 1] = theta[i] + dx * (cf / 2 - (Hs + 2) * theta[i] / U[i] * dUdx)
    dstar = Hs * theta
    ratio = (SPAN - 2 * dstar[0]) / (SPAN - 2 * dstar)
    U3 = U * ratio
    dcp = (U[-1] ** 2 - U3[-1] ** 2) / U_REF ** 2
    return {"Hs": Hs, "theta_30H_mm": float(theta[-1]), "dstar_-4H_mm": float(dstar[0]),
            "dstar_30H_mm": float(dstar[-1]), "core_speed_up_pct": float(100 * (ratio[-1] - 1)),
            "recovery_change": float(dcp)}


def main(run_id="20261122-233146_step_mesh", label="p02_mesh_level-1.4142"):
    x, cp = cp_2d(run_id, label)
    print(f"2D recovery Cp(30H) - Cp(-4H): {np.interp(30.0, x, cp):.4f}; measured 0.131; theta(-4H) {THETA0:.3f} mm")
    for Hs in (1.4, 1.6, 1.8):
        r = estimate(x, cp, Hs)
        print(f"Hs {Hs}: theta(30H) {r['theta_30H_mm']:.2f} mm, delta* {r['dstar_-4H_mm']:.2f} -> {r['dstar_30H_mm']:.2f} mm, "
              f"core +{r['core_speed_up_pct']:.2f} %, recovery lower by {r['recovery_change']:.4f}")


if __name__ == "__main__":
    main(*sys.argv[1:])

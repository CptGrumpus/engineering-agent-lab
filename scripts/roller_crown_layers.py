"""Study 10 part 2: does the 3D FE mesh draw the crown finely enough along the roller?

The FE model (models/fea/roller_3d.py) applies the crown as a drop of each layer plane, so its surface is the exact
drop at the planes and straight between them. Near the roller's end the logarithmic crown climbs steeply (6.5 um at
0.2 mm from the end, 30 um at the end), so a coarse end layer cuts the roller short and leaves a kink, which loads
like an edge. This script feeds that piecewise-linear profile to the half-space model (models/contact/
roller_halfspace.py, which has no end face at all) and compares it with the exact crown: any end peak it finds comes
from the drawing of the crown alone.

    python scripts/roller_crown_layers.py            # about 15 minutes

Written 2026-11-28 after roller_fe_mesh's 0.06 mm point read 724 MPa 0.46 mm from the end (0.2 mm end layer).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from models.contact import roller_halfspace as H  # noqa: E402
from models.fea import roller_3d as R3  # noqa: E402

# roller_fe_mesh's roller and crown (A = 1.3 x Lundberg)
P = dict(roller_radius_mm=50.0, roller_length_mm=30.0, plate_width_mm=60.0, youngs_modulus_MPa=210000.0,
         poisson_ratio=0.3, line_load_N_per_mm=500.0, profile="log", crown_A_um=1.793145692168688, crown_zm_um=30.0,
         cap_um=60.0, end_layer_mm=0.2, layer_growth=1.3, max_layer_mm=1.0, far_element_size_mm=4.0, z_fine_mm=0.0)
GRID = dict(nx=36, y_fine=0.02, y_max_cell=0.667)       # half-space cells: 0.02 mm at the end, finer than any layer


def fe_profile(end_layer: float, growth: float):
    """The drop the FE mesh draws: exact at its layer planes, linear between them."""
    roller, beyond = R3.layers(dict(P, end_layer_mm=end_layer, layer_growth=growth))
    zs = np.concatenate([[0.0], np.cumsum(roller)])
    d = R3.drop_um(P, zs)
    return (lambda p, z: np.interp(np.abs(np.asarray(z, float)), zs, d)), len(roller), len(beyond)


def end_max(r) -> float:
    pz = r["pressure_MPa"].max(axis=0)
    yc = 0.5 * (r["yf"][1:] + r["yf"][:-1])
    return float(pz[yc > 12.0].max())


def main() -> int:
    ex = H.solve(P, drop_um=R3.drop_um, **GRID)
    print(f"exact crown: peak {ex['peak_MPa']:.1f} MPa at {ex['peak_y_mm']:.3f} mm from mid-length; "
          f"largest beyond 12 mm {end_max(ex):.1f}")
    print("end layer  growth  layers (roller + beyond)  peak MPa  at mm   vs exact  largest beyond 12 mm")
    for h, g in [(0.2, 1.3), (0.1, 1.3), (0.05, 1.3), (0.1, 1.2), (0.05, 1.2), (0.025, 1.2), (0.05, 1.15)]:
        f, nr, nb = fe_profile(h, g)
        r = H.solve(P, drop_um=f, **GRID)
        print(f"{h:9.3f}  {g:6.2f}  {nr:7d} + {nb:<14d}  {r['peak_MPa']:8.1f}  {r['peak_y_mm']:6.3f}  "
              f"{100 * (r['peak_MPa'] / ex['peak_MPa'] - 1):+6.1f} %  {end_max(r):8.1f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

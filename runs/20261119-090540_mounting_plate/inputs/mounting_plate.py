"""Parametric mounting plate in CadQuery (model under test).

A rectangular plate (length along x, width along y, thickness along z) with
filleted vertical corners and a centred rectangular grid of through-holes.
Origin at the plate centre, bottom face on z = 0. Units: mm.
"""

from __future__ import annotations

import cadquery as cq

PARAMS = ("length_mm", "width_mm", "thickness_mm", "corner_radius_mm", "hole_diameter_mm",
          "holes_x", "holes_y", "hole_pitch_x_mm", "hole_pitch_y_mm", "density_g_per_mm3")


def hole_centres(p: dict) -> list[tuple[float, float]]:
    nx, ny = int(p["holes_x"]), int(p["holes_y"])
    px, py = float(p["hole_pitch_x_mm"]), float(p["hole_pitch_y_mm"])
    return [((i - (nx - 1) / 2) * px, (j - (ny - 1) / 2) * py)
            for j in range(ny) for i in range(nx)]


def build(p: dict) -> cq.Workplane:
    L, W, t = float(p["length_mm"]), float(p["width_mm"]), float(p["thickness_mm"])
    r, d = float(p["corner_radius_mm"]), float(p["hole_diameter_mm"])
    plate = cq.Workplane("XY").box(L, W, t, centered=(True, True, False))
    if r > 0:
        plate = plate.edges("|Z").fillet(r)
    return (plate.faces(">Z").workplane()
            .pushPoints(hole_centres(p)).hole(d))

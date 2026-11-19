"""Closed-form geometry of the mounting plate (independent of the CAD kernel).

Area of the outline with four corner fillets of radius r: each fillet removes
a square r x r and adds back a quarter circle, so

    A_outline = L W - (4 - pi) r^2
    A_net     = A_outline - N pi d^2 / 4
    V         = A_net t,  mass = rho V

Design-rule quantities for a hole grid (centres x_i = (i - (nx-1)/2) px):
    edge distance (centre to nearest straight edge)
        e = min((L - (nx-1) px) / 2, (W - (ny-1) py) / 2)
    ligament (web between adjacent holes) = min(px if nx > 1, py if ny > 1) - d
"""

from __future__ import annotations

import math


def net_area(L, W, r, d, n_holes) -> float:
    return L * W - (4.0 - math.pi) * r**2 - n_holes * math.pi * d**2 / 4.0


def volume(p: dict) -> float:
    n = int(p["holes_x"]) * int(p["holes_y"])
    return net_area(float(p["length_mm"]), float(p["width_mm"]), float(p["corner_radius_mm"]),
                    float(p["hole_diameter_mm"]), n) * float(p["thickness_mm"])


def edge_distance(p: dict) -> float:
    return min((float(p["length_mm"]) - (int(p["holes_x"]) - 1) * float(p["hole_pitch_x_mm"])) / 2,
               (float(p["width_mm"]) - (int(p["holes_y"]) - 1) * float(p["hole_pitch_y_mm"])) / 2)


def ligament(p: dict) -> float:
    pitches = []
    if int(p["holes_x"]) > 1:
        pitches.append(float(p["hole_pitch_x_mm"]))
    if int(p["holes_y"]) > 1:
        pitches.append(float(p["hole_pitch_y_mm"]))
    return min(pitches) - float(p["hole_diameter_mm"]) if pitches else math.inf

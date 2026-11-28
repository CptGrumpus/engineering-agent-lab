"""Study 7 (study 20 on the site), detailed CAD: the features of the client's lamination drawing that the 2D model
leaves out, measured from the drawing's vector paths (ORNL/TM-2005/33 Fig. 21, page 32 of Pub57487.pdf, sha256
179407ecf90a): the stator's three mounting ears, the notches on its outer edge, and the rotor's hub keys.

The drawing dimensions some of them (ear hole 0.360 in, ear root relief R0.234 in, notches 0.230 x 0.080 in and
0.474 x 0.094 in with R0.109 in, keys 4.152 in across a 4.356 in bore) but not where they sit or the ear's outline.
Those are measured here: the page scaled by the stator's outer diameter (10.600 in, an ellipse fit: the page is
scaled slightly unevenly), the bore (6.375 in) as a check of the scale, the dimensioned features as a check of the
measurement.

Two steps (PyMuPDF lives in the Pyleecan environment, scipy in the project venv):
    ~/.venvs/pyleecan/Scripts/python.exe -I scripts/motor_drawing_stator.py extract <Pub57487.pdf> <out dir>
    .venv/Scripts/python.exe scripts/motor_drawing_stator.py measure <out dir> [json out]

extract: black (stator) lines, black curves (the ear holes) and blue (rotor) paths of page 32, as segments in points.
measure: angles counter-clockwise from the drawing's +x axis, lengths in mm.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

IN = 25.4
OD_IN, BORE_IN = 10.600, 6.375
ROTOR_BORE_IN, KEYS_IN = 4.356, 4.152


def extract(pdf, out):
    import pymupdf
    p = pymupdf.open(pdf)[31]
    segs = {"black": [], "black_curves": [], "blue": []}
    for d in p.get_drawings():
        key = {(0.0, 0.0, 0.0): "black", (0.0, 0.0, 1.0): "blue"}.get(d.get("color"))
        if key is None:
            continue
        for it in d["items"]:
            if it[0] == "l":
                segs[key].append((it[1].x, it[1].y, it[2].x, it[2].y))
            elif it[0] == "c":
                q = np.array([[pt.x, pt.y] for pt in it[1:5]])
                t = np.linspace(0, 1, 13)[:, None]
                b = ((1 - t) ** 3 * q[0] + 3 * (1 - t) ** 2 * t * q[1] + 3 * (1 - t) * t ** 2 * q[2] + t ** 3 * q[3])
                segs["black_curves" if key == "black" else key] += [(*a, *c) for a, c in zip(b[:-1], b[1:])]
    Path(out).mkdir(parents=True, exist_ok=True)
    for k, v in segs.items():
        np.save(f"{out}/{k}_segs.npy", np.array(v, float))
        print(k, len(v), "segments")


def _densify(S, step):
    out = []
    for x1, y1, x2, y2 in S:
        n = max(2, int(math.hypot(x2 - x1, y2 - y1) / step) + 1)
        out.append(np.column_stack([np.linspace(x1, x2, n), np.linspace(y1, y2, n)]))
    return np.vstack(out)


def _circle_fit(P):
    A = np.column_stack([2 * P[:, 0], 2 * P[:, 1], np.ones(len(P))])
    cx, cy, c = np.linalg.lstsq(A, (P ** 2).sum(1), rcond=None)[0]
    return cx, cy, math.sqrt(c + cx * cx + cy * cy)


def _ellipse_fit(P):
    """Axis-aligned ellipse A x^2 + B y^2 + C x + D y = 1: centre and semi-axes."""
    A, B, C, D = np.linalg.lstsq(np.column_stack([P[:, 0] ** 2, P[:, 1] ** 2, P[:, 0], P[:, 1]]), np.ones(len(P)),
                                 rcond=None)[0]
    cx, cy = -C / (2 * A), -D / (2 * B)
    F = 1 + A * cx * cx + B * cy * cy
    return cx, cy, math.sqrt(F / A), math.sqrt(F / B)


def _in_window(th, centre, half):
    return np.abs((th - centre + 180) % 360 - 180) <= half


def measure(out, json_out=None):
    Rod, Rbore = OD_IN / 2 * IN, BORE_IN / 2 * IN
    P = _densify(np.load(f"{out}/black_segs.npy"), 0.05)
    Pc = _densify(np.load(f"{out}/black_curves_segs.npy"), 0.02)
    Pb = _densify(np.load(f"{out}/blue_segs.npy"), 0.05)
    # 1. scale: the outer edge away from the ears and notches (every 30 deg from 3 deg), fitted as an ellipse
    cx, cy, R = 219.14, 228.85, 99.0                         # rough centre and radius (points), refined below
    for _ in range(4):
        r = np.hypot(P[:, 0] - cx, P[:, 1] - cy)
        th = np.degrees(np.arctan2(-(P[:, 1] - cy), P[:, 0] - cx)) % 360
        clear = np.abs((th - 3 + 15) % 30 - 15) > 6
        on = clear & (np.abs(r - R) < 0.012 * R)
        cx, cy, ax_, by_ = _ellipse_fit(P[on])
        R = 0.5 * (ax_ + by_)
    kx, ky = Rod / ax_, Rod / by_
    to_mm = lambda Q: np.column_stack([(Q[:, 0] - cx) * kx, -(Q[:, 1] - cy) * ky])  # noqa: E731
    X, C, Y = to_mm(P), to_mm(Pc), to_mm(Pb)
    r, th = np.hypot(*X.T), np.degrees(np.arctan2(X[:, 1], X[:, 0])) % 360
    clear = np.abs((th - 3 + 15) % 30 - 15) > 6
    od = clear & (np.abs(r - Rod) < 1.0)
    bf = _circle_fit(X[np.abs(r - Rbore) < 0.25])
    res = {"drawing": "ORNL/TM-2005/33 Fig. 21 (Pub57487.pdf p. 32, sha256 179407ecf90a)",
           "scale": {"mm_per_point_x": kx, "mm_per_point_y": ky, "aspect_x_over_y": kx / ky,
                     "od_rms_mm": float(np.sqrt(np.mean((r[od] - Rod) ** 2)))},
           "check_bore_radius_mm": {"drawing": Rbore, "measured": bf[2], "centre_offset_mm": math.hypot(bf[0], bf[1])}}
    # 2. ears: the hole circles are the page's only curves near the OD (the inset's zoom circle lies far outside)
    cr, ct = np.hypot(*C.T), np.degrees(np.arctan2(C[:, 1], C[:, 0])) % 360
    ears = []
    for a in (94.0, 214.0, 334.0):
        hx, hy, hr = _circle_fit(C[_in_window(ct, a, 8) & (cr < Rod + 12)])
        hrad, hang = math.hypot(hx, hy), math.degrees(math.atan2(hy, hx)) % 360
        Q = X[_in_window(th, hang, 9) & (r < 149.0)]
        dq, rq = np.hypot(Q[:, 0] - hx, Q[:, 1] - hy), np.hypot(*Q.T)
        tab = Q[(rq > Rod + 0.4) & (dq > hr + 0.4)]
        dt = np.hypot(tab[:, 0] - hx, tab[:, 1] - hy)
        beyond = (tab @ np.array([hx, hy]) / hrad) > hrad + 1.0     # the rounded end, outward of the hole centre
        foot = Q[(rq > Rod + 0.4) & (rq < Rod + 1.0) & (dq > hr + 0.4)]
        fang = (np.degrees(np.arctan2(foot[:, 1], foot[:, 0])) - hang + 180) % 360 - 180
        rel = Q[(rq < Rod - 0.3) & (rq > Rod - 4)]
        rang = (np.degrees(np.arctan2(rel[:, 1], rel[:, 0])) - hang + 180) % 360 - 180
        ears.append({"hole_angle_deg": hang, "hole_centre_radius_mm": hrad, "hole_diameter_mm": 2 * hr,
                     "hole_diameter_drawing_mm": 0.360 * IN,
                     "tab_end_radius_about_hole_mm": float(np.median(dt[beyond])),
                     "tab_tip_radius_mm": float(rq.max()),
                     "tab_foot_offsets_deg": [float(fang.min()), float(fang.max())] if len(fang) else None,
                     "relief_depth_mm": float(Rod - np.hypot(*rel.T).min()) if len(rel) else None,
                     "relief_offsets_deg": ([float(rang[rang < 0].mean()), float(rang[rang > 0].mean())]
                                            if (rang < 0).any() and (rang > 0).any() else None)})
    res["ears"] = ears
    # 3. notches: outline points 0.4-3.5 mm inside the OD at the other 30 deg positions
    notches = []
    for a in np.arange(3.0, 360.0, 30.0):
        if any(abs((a - e["hole_angle_deg"] + 180) % 360 - 180) < 10 for e in ears):
            continue
        w = _in_window(th, a, 9) & (r < Rod - 0.4) & (r > Rod - 3.5)
        if w.sum() < 10:
            notches.append({"position_deg": float(a), "found": False})
            continue
        Q = X[w]
        ang = (np.degrees(np.arctan2(Q[:, 1], Q[:, 0])) - a + 180) % 360 - 180
        notches.append({"position_deg": float(a), "found": True,
                        "centre_deg": float(a + 0.5 * (ang.max() + ang.min())) % 360,
                        "width_mm": float(math.radians(ang.max() - ang.min()) * Rod),
                        "depth_mm": float(Rod - np.hypot(*Q.T).min())})
    res["notches"] = notches
    res["notches_drawing_mm"] = {"small_w_d": [0.230 * IN, 0.080 * IN], "large_w_d": [0.474 * IN, 0.094 * IN],
                                 "large_corner_radius": 0.109 * IN}
    # 4. rotor hub keys (blue): the bore 4.356 in, the keys' tops 4.152 in across
    Rrb, Rkey = ROTOR_BORE_IN / 2 * IN, KEYS_IN / 2 * IN
    rb, tb = np.hypot(*Y.T), np.degrees(np.arctan2(Y[:, 1], Y[:, 0])) % 360
    bpts = np.abs(rb - Rrb) < 0.3
    rbf = _circle_fit(Y[bpts]) if bpts.sum() > 20 else (math.nan,) * 3
    keys = []
    kp = (rb < Rrb - 0.4) & (rb > Rkey - 1.0)
    for a in np.arange(0.0, 360.0, 22.5):
        w = kp & _in_window(tb, a, 11.25)
        if w.sum() < 10:
            continue
        Q = Y[w]
        mid = math.atan2(Q[:, 1].mean(), Q[:, 0].mean())
        tvec = np.array([-math.sin(mid), math.cos(mid)])
        keys.append({"centre_deg": math.degrees(mid) % 360, "width_mm": float(np.ptp(Q @ tvec)),
                     "top_radius_mm": float(np.hypot(*Q.T).min()), "points": int(w.sum())})
    res["rotor"] = {"bore_radius_mm": {"drawing": Rrb, "measured": rbf[2]}, "key_top_radius_drawing_mm": Rkey,
                    "keys": keys}
    print(json.dumps(res, indent=1))
    if json_out:
        Path(json_out).write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    {"extract": extract, "measure": measure}[sys.argv[1]](*sys.argv[2:])

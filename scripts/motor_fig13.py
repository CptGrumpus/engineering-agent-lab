"""Study 7, the 18 % flux excess, step 5 (validation/motor_ornl/CALIBRATION_PLAN.md): ORNL's measured no-load air-gap
flux density (ORNL/TM-2004/137 Fig. 13, 2004 motor) against the revision-5 model's.

usage: <pyleecan python> scripts/motor_fig13.py <Pub57348.pdf> <solution.ans> <out.json>
Runs in the Pyleecan environment (PyMuPDF and pyFEMM); FEMM must be free.

- ORNL: the 2004 series' 13 markers (magenta filled squares) from the PDF's vector drawing, the gauss axis calibrated on
  the plot frame (+8000 at the top, -8000 at the bottom).
- Model: radial flux density at 80.90 mm (stator side of the gap) from the saved FEMM solution (one pole, antiperiodic), extended to
  a pole pair by antiperiodicity, sampled at the slot pitch (7.5 deg). One free parameter, the rotor angle of slot 1,
  fitted by least squares on the shapes each normalised by its own plateau (the planned zero-crossing alignment was
  degenerate, kept in the output); the amplitude is not fitted.
"""

from __future__ import annotations

import json
import math
import sys

import numpy as np

SLOTS, POLE_PAIRS = 48, 4
R_ROTOR, R_BORE = 80.1878, 80.9625          # mm, revision 5
# Pyleecan's air-gap element fills about 80.3-80.8 mm, where FEMM has no mesh to evaluate (mo_getb returns 0); the
# meshed air between it and the bore is sampled, 0.06 mm inside the bore, where a probe in the gap would sit
R_PROBE = 80.90


def ornl_series(pdf: str) -> list[float]:
    import fitz

    p = fitz.open(pdf)[11]
    dr = p.get_drawings()
    frame = [d["rect"] for d in dr if d["type"] == "f" and tuple(round(c, 2) for c in d["fill"]) == (0.75, 0.75, 0.75)][0]
    mag = sorted(((d["rect"].x0 + d["rect"].x1) / 2, (d["rect"].y0 + d["rect"].y1) / 2) for d in dr
                 if d["type"] == "fs" and tuple(round(c, 2) for c in d["fill"]) == (1.0, 0.0, 1.0)
                 and d["rect"].x1 < frame.x1)
    if len(mag) != 13:
        raise SystemExit(f"expected 13 markers in the 2004 series, found {len(mag)}")
    return [8000 - 16000 * (y - frame.y0) / (frame.y1 - frame.y0) for _, y in mag]


def model_br(ans: str, n: int = 721) -> tuple[np.ndarray, np.ndarray]:
    """Radial B (T) at the gap's mid-radius over the solution's angular span, and the angles (deg)."""
    import femm

    femm.openfemm(1)
    try:
        femm.opendocument(ans)
        r = R_PROBE / 1000.0          # the solution is in metres
        # the modelled sector: probe a full turn and keep the points FEMM can evaluate
        th = np.linspace(0.0, 360.0, 4 * n, endpoint=False)
        out = []
        for t in th:
            x, y = r * math.cos(math.radians(t)), r * math.sin(math.radians(t))
            b = femm.mo_getb(x, y)
            if b is None:
                continue
            bx, by = float(b[0]), float(b[1])
            out.append((t, bx * math.cos(math.radians(t)) + by * math.sin(math.radians(t))))
        femm.mo_close()
    finally:
        femm.closefemm()
    a = np.array(out)
    return a[:, 0], a[:, 1]


def main(pdf: str, ans: str, out_path: str) -> None:
    g = np.array(ornl_series(pdf))
    th, br = model_br(ans)
    # the modelled span: the contiguous angles where |B| is not ~0 outside the model (FEMM returns 0 there)
    inside = np.abs(br) > 1e-9
    th, br = th[inside], br[inside]
    span = th.max() - th.min()
    pole = 360.0 / (2 * POLE_PAIRS)
    if span < 0.9 * pole:
        raise SystemExit(f"the solution covers {span:.1f} deg, less than a pole ({pole} deg)")
    # one pole -> a pole pair by antiperiodicity (B(theta + pole) = -B(theta)), on a regular grid
    t0 = th.min()
    grid = np.linspace(0.0, pole, 361)
    b1 = np.interp(t0 + grid, th, br)
    full_t = np.concatenate([grid, grid[1:] + pole])
    full_b = np.concatenate([b1, -b1[1:]])
    period = 2 * pole
    f = lambda t: np.interp(np.mod(t, period), full_t, full_b)  # noqa: E731
    pitch = 360.0 / SLOTS
    plateau = lambda v: (np.mean(np.sort(np.abs(v[1:6]))[-3:]) + np.mean(np.sort(np.abs(v[7:12]))[-3:])) / 2  # noqa: E731
    gn = g / plateau(g)
    # (first attempt, kept in the JSON: slot 1 on a zero crossing of the model; degenerate, because the model's field
    # stays near zero over about two slot pitches between poles, so "zeros at slots 1, 7, 13" does not fix the angle)
    tt = np.linspace(0, period, 7201)
    bb = f(tt)
    zc = [tt[i] for i in range(len(tt) - 1) if bb[i] >= 0 > bb[i + 1]]
    zc_choice = min(zc, key=lambda z: abs(f(z + 6 * pitch)) + abs(f(z + 12 * pitch)))
    # the angle by least squares on the normalised shapes (one parameter; the amplitude is not fitted)
    cand = np.linspace(0, period, 3601)
    cost = [float(np.sum((f(z + pitch * np.arange(13)) / plateau(f(z + pitch * np.arange(13))) - gn) ** 2)) for z in cand]
    z = float(cand[int(np.argmin(cost))])
    s = f(z + pitch * np.arange(13)) * 1e4                       # gauss
    s_zc = f(zc_choice + pitch * np.arange(13)) * 1e4
    ratio = plateau(s) / plateau(g)
    shape = np.max(np.abs(s / plateau(s) - g / plateau(g)))
    res = {"ornl_2004_gauss": [round(v, 1) for v in g], "model_gauss": [round(float(v), 1) for v in s],
           "slot1_angle_deg_in_solution": float(z + t0), "plateau_ornl_gauss": float(plateau(g)),
           "plateau_model_gauss": float(plateau(s)), "plateau_ratio_model_over_ornl": float(ratio),
           "max_normalised_shape_difference": float(shape),
           "normalised_difference_by_slot": [round(float(v), 4) for v in (s / plateau(s) - g / plateau(g))],
           "zero_crossing_attempt": {"slot1_angle_deg": float(zc_choice + t0), "model_gauss": [round(float(v), 1) for v in s_zc],
                                     "plateau_ratio": float(plateau(s_zc) / plateau(g))},
           "model_profile_one_pole_pair": {"angle_deg": [round(float(v), 3) for v in full_t[::4]],
                                           "br_T": [round(float(v), 5) for v in full_b[::4]]},
           "radius_mm": R_PROBE, "solution": ans}
    open(out_path, "w", encoding="utf-8").write(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "solution"}, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:4])

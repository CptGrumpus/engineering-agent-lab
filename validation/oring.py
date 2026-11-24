"""Study 12, O-ring face seal: hand references (no FE).

- Gent's relation, Shore A hardness to Young's modulus (A. N. Gent, Rubber Chem. Technol. 31(4) 896-906, 1958; the
  form and grouping as Wikipedia's "Shore durometer" page gives it, checked against that page's own table: 5.520 MPa
  at 70). Departs from data below 40 Shore A.
- Lindley's force-compression relation for an O-ring between flat plates (P. B. Lindley, J. Inst. Rubber Ind. 1(4)
  209-213, 1967), F = pi D d E (1.25 c^1.5 + 50 c^6), as El Bahloul et al. (Int. J. Fluid Power 23(2), 2022) print it;
  the exponents are read from a garbled extraction and not yet confirmed from a second source: a secondary reference.
- Hertz line contact (a cylinder of radius R on a flat, plane strain): contact half-width b = sqrt(4 F' R / (pi E*))
  and peak pressure p0 = 2 F' / (pi b), with E* = E / (1 - nu^2) (4 E / 3 for an incompressible solid): the exact
  small-strain limit, used as relations between the FE's own force, width and peak pressure at small squeeze.
- Parker O-Ring Handbook ORD 5700, Fig. 2-6 (0.139 in cross-section): measured compression load per inch of seal,
  70 Shore A band, read from the PDF's vector lines (band ends; the log axis calibrated on the grid lines at 0.1 and
  1000 lbf/in, about 1 % reading uncertainty); a weak check: each band spans a factor of about 6.6.
- The tolerance stack: squeeze and groove fill by hand.
"""

from __future__ import annotations

import math

LBF_PER_IN_TO_N_PER_MM = 4.448222 / 25.4

#: Parker ORD 5700 Fig. 2-6, 0.139 in cross-section, 70 Shore A: percent compression -> (low, high) load, N per mm
PARKER_70A_0139_N_PER_MM = {5: (0.169, 1.113), 10: (0.356, 2.524), 20: (0.793, 5.119), 30: (1.891, 12.999),
                            40: (4.366, 28.530)}


def gent_youngs_modulus_MPa(shore_a: float) -> float:
    """E (MPa) from ASTM D2240 type A hardness (Gent 1958)."""
    s = float(shore_a)
    if not 40.0 <= s < 100.0:
        raise ValueError("Gent's relation departs from data below 40 Shore A and is infinite at 100")
    return 0.0981 * (56.0 + 7.62336 * s) / (0.137505 * (254.0 - 2.54 * s))


def lindley_force_per_length_N_per_mm(d_mm: float, E_MPa: float, c: float) -> float:
    """Lindley's compression force per unit length of seal (N/mm): F / (pi D) = d E (1.25 c^1.5 + 50 c^6)."""
    return d_mm * E_MPa * (1.25 * c ** 1.5 + 50.0 * c ** 6)


def hertz_line(F_per_length: float, R: float, E: float, nu: float = 0.5) -> tuple[float, float]:
    """(half-width b, peak pressure p0) of a cylinder of radius R pressed on a flat, force per unit length F'."""
    Es = E / (1.0 - nu * nu)
    b = math.sqrt(4.0 * F_per_length * R / (math.pi * Es))
    return b, 2.0 * F_per_length / (math.pi * b)


def squeeze(d_mm: float, depth_mm: float) -> float:
    """Fractional compression of the cross-section in a face-seal groove of the given depth."""
    return (d_mm - depth_mm) / d_mm


def groove_fill(d_mm: float, depth_mm: float, width_mm: float) -> float:
    """Cross-section area over groove area (the rubber's volume is conserved, so the installed fill equals this)."""
    return math.pi * d_mm ** 2 / 4.0 / (depth_mm * width_mm)


def stack(d_nom, d_tol, depth_nom, depth_tol, width_nom, width_tol) -> dict:
    """Worst-case corners of the tolerance stack."""
    return {"squeeze_min": squeeze(d_nom - d_tol, depth_nom + depth_tol),
            "squeeze_nom": squeeze(d_nom, depth_nom),
            "squeeze_max": squeeze(d_nom + d_tol, depth_nom - depth_tol),
            "fill_max": groove_fill(d_nom + d_tol, depth_nom - depth_tol, width_nom - width_tol)}

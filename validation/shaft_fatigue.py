"""Machine-elements study: a stepped shaft with a shoulder fillet, fatigue and yield by Shigley's method (no FE).

Sources (all fetched and read, 2026-11-24; none quoted from memory):

- Shoulder-fillet stress concentration of a stepped round shaft, Kt = C1 + C2 (2h/D) + C3 (2h/D)^2 + C4 (2h/D)^3 with
  h = (D - d)/2 the shoulder height and C_i functions of h/r. Coefficients from Pilkey, *Formulas for Stress, Strain,
  and Structural Matrices* 2nd ed. (2005), as transcribed by amesweb.info ("Shoulder fillet in a stepped circular
  shaft"); bending in two h/r ranges (0.1-2, 2-20), torsion one (0.25-4). The polynomial form (coefficients times
  powers of 2h/D; the web page's typesetting puts the powers outside the brackets) and the h definition are confirmed
  by Rogers, ASEE Midwest Section 2025 (peer.asee.org/57831), which quotes Roark's 8th ed. (Young, Budynas, Sadegh
  2011); Roark's low-range bending coefficients differ slightly from Pilkey's (ROARK_BENDING_LOW, up to 2.2 % in Kt).
  Nominal stresses 32 M / (pi d^3) and 16 T / (pi d^3) on the small diameter.
- Shigley's Mechanical Engineering Design, 11th ed. (Budynas, Nisbett 2019), chapter 6, as applied in the chapter-6
  solutions manual (Oakland University ME4300 copy): Se' = 0.5 Sut (Sut <= 1400 MPa, eq 6-10); surface factor
  ka = a Sut^b, machined a = 3.04 MPa, b = -0.217 (Table 6-2, eq 6-18; the 10th edition's 4.51 / -0.265, from the
  Hijazi chapter-6 notes, is kept as a sensitivity: 6.5 % higher at 1000 MPa); size factor kb = 1.24 d^-0.107
  (2.79-51 mm, eq 6-19); notch sensitivity q = 1 / (1 + sqrt(a) / sqrt(r)) (eq 6-33) with Neuber's constant for steels,
  sqrt(a) = 0.246 - 3.08e-3 Sut + 1.51e-5 Sut^2 - 2.67e-8 Sut^3 in bending/axial (eq 6-35) and
  0.190 - 2.51e-3 Sut + 1.35e-5 Sut^2 - 2.67e-8 Sut^3 in torsion (eq 6-36), Sut in kpsi, sqrt(a) in sqrt(in);
  checked against the manual's worked values (Sut 64 kpsi: 0.10373 and 0.07800); Kf = 1 + q (Kt - 1) (eq 6-32).
- Combined loading (Shigley ch. 6 and 7): von Mises alternating and mean stresses with Kf, Kfs applied and the
  endurance limit taken with kc = 1; modified Goodman 1/n = sa'/Se + sm'/Sut; ASME elliptic
  (n sa'/Se)^2 + (n sm'/Sy)^2 = 1; first-cycle yield n_y = Sy / s'max with s'max = [(Kf (sm + sa))^2 +
  3 (Kfs (tm + ta))^2]^0.5 (the conservative form Shigley's chapter 7 uses for shafts).

DIN 743 is a paid standard and is not used.
"""

from __future__ import annotations

import math

KPSI_PER_MPA = 1.0 / 6.894757
SQRT_MM_PER_SQRT_IN = math.sqrt(25.4)

#: Pilkey 2nd ed. (via amesweb.info): ((h/r range), coefficients of (1, sqrt(h/r), h/r) for C1..C4)
PILKEY_BENDING = (
    ((0.1, 2.0), ((0.947, 1.206, -0.131), (0.022, -3.405, 0.915), (0.869, 1.777, -0.555), (-0.810, 0.422, -0.260))),
    ((2.0, 20.0), ((1.232, 0.832, -0.008), (-3.813, 0.968, -0.260), (7.423, -4.868, 0.869), (-3.839, 3.070, -0.600))),
)
PILKEY_TORSION = (
    ((0.25, 4.0), ((0.905, 0.783, -0.075), (-0.437, -1.969, 0.553), (1.557, 1.073, -0.578), (-1.061, 0.171, 0.086))),
)
#: Roark's 8th ed. (via Rogers, ASEE 2025), bending, 0.25 <= h/r <= 2.0
ROARK_BENDING_LOW = (
    ((0.25, 2.0), ((0.927, 1.149, -0.086), (0.015, -3.281, 0.837), (0.847, 1.716, -0.506), (-0.790, 0.417, -0.246))),
)

#: Surface factor ka = a Sut^b (Sut in MPa), machined or cold-drawn
KA_MACHINED = {"shigley11": (3.04, -0.217), "shigley10": (4.51, -0.265)}

#: Neuber's constant for steels, sqrt(a) in sqrt(in) from Sut in kpsi (Shigley 11th ed. eqs 6-35, 6-36)
NEUBER_BENDING = (0.246, -3.08e-3, 1.51e-5, -2.67e-8)
NEUBER_TORSION = (0.190, -2.51e-3, 1.35e-5, -2.67e-8)


def _kt(table, D: float, d: float, r: float) -> float:
    if not D > d > 0 or r <= 0:
        raise ValueError("need D > d > 0 and r > 0")
    h = (D - d) / 2.0
    hr = h / r
    for (lo, hi), coeffs in table:
        if lo <= hr <= hi:
            C = [c0 + c1 * math.sqrt(hr) + c2 * hr for c0, c1, c2 in coeffs]
            x = 2.0 * h / D
            return C[0] + C[1] * x + C[2] * x ** 2 + C[3] * x ** 3
    raise ValueError(f"h/r = {hr:.3g} outside the fit's range")


def kt_bending(D: float, d: float, r: float, table=PILKEY_BENDING) -> float:
    """Shoulder-fillet Kt in bending, on 32 M / (pi d^3)."""
    return _kt(table, D, d, r)


def kt_torsion(D: float, d: float, r: float) -> float:
    """Shoulder-fillet Kts in torsion, on 16 T / (pi d^3)."""
    return _kt(PILKEY_TORSION, D, d, r)


def neuber_sqrt_a_mm(Sut_MPa: float, torsion: bool = False) -> float:
    """Neuber's constant sqrt(a) for steels in sqrt(mm) (fits valid 50-250 kpsi, 345-1720 MPa)."""
    s = Sut_MPa * KPSI_PER_MPA
    if not 50.0 <= s <= 250.0:
        raise ValueError("Neuber constant fit valid for 50-250 kpsi")
    c = NEUBER_TORSION if torsion else NEUBER_BENDING
    return (c[0] + c[1] * s + c[2] * s ** 2 + c[3] * s ** 3) * SQRT_MM_PER_SQRT_IN


def notch_sensitivity(r_mm: float, sqrt_a_mm: float) -> float:
    return 1.0 / (1.0 + sqrt_a_mm / math.sqrt(r_mm))


def kf(kt: float, q: float) -> float:
    return 1.0 + q * (kt - 1.0)


def endurance_limit(Sut_MPa: float, d_mm: float, edition: str = "shigley11", ke: float = 1.0) -> dict:
    """Se = ka kb kc kd ke Se' for rotating bending of a machined round bar (kc = kd = 1)."""
    se_prime = 0.5 * Sut_MPa if Sut_MPa <= 1400.0 else 700.0
    a, b = KA_MACHINED[edition]
    ka = a * Sut_MPa ** b
    if not 2.79 <= d_mm <= 254.0:
        raise ValueError("size factor fit valid for 2.79-254 mm")
    kb = 1.24 * d_mm ** -0.107 if d_mm <= 51.0 else 1.51 * d_mm ** -0.157
    return {"Se_prime": se_prime, "ka": ka, "kb": kb, "ke": ke, "Se": ka * kb * ke * se_prime}


def nominal_stresses(d_mm: float, M_Nm: float, T_Nm: float) -> tuple[float, float]:
    """(bending stress 32 M / (pi d^3), shear stress 16 T / (pi d^3)) in MPa."""
    z = math.pi * d_mm ** 3
    return 32.0 * M_Nm * 1e3 / z, 16.0 * T_Nm * 1e3 / z


def assess(D, d, r, M_Nm, T_Nm, Sut, Sy, *, kt_b=None, kt_t=None, edition="shigley11", ke=1.0, overload=1.5) -> dict:
    """Rotating bending M (fully reversed) and steady torque T at the shoulder fillet of a stepped shaft.

    kt_b, kt_t default to the Pilkey fits; pass the FE values to use those.
    """
    kt_b = kt_bending(D, d, r) if kt_b is None else kt_b
    kt_t = kt_torsion(D, d, r) if kt_t is None else kt_t
    qb = notch_sensitivity(r, neuber_sqrt_a_mm(Sut))
    qt = notch_sensitivity(r, neuber_sqrt_a_mm(Sut, torsion=True))
    Kf, Kfs = kf(kt_b, qb), kf(kt_t, qt)
    sa, tm = nominal_stresses(d, M_Nm, T_Nm)
    sa_vm = Kf * sa
    sm_vm = math.sqrt(3.0) * Kfs * tm
    se = endurance_limit(Sut, d, edition, ke)
    Se = se["Se"]
    n_goodman = 1.0 / (sa_vm / Se + sm_vm / Sut)
    n_elliptic = 1.0 / math.hypot(sa_vm / Se, sm_vm / Sy)
    smax = math.sqrt((Kf * overload * sa) ** 2 + 3.0 * (Kfs * overload * tm) ** 2)
    return {"Kt": kt_b, "Kts": kt_t, "q": qb, "qs": qt, "Kf": Kf, "Kfs": Kfs, "sigma_a_nom": sa, "tau_m_nom": tm,
            "sigma_a_vm": sa_vm, "sigma_m_vm": sm_vm, **se, "n_goodman": n_goodman, "n_elliptic": n_elliptic,
            "sigma_max_vm": smax, "n_yield": Sy / smax}


def minimum_radius(D, d, M_Nm, T_Nm, Sut, Sy, n_target, r_lo, r_hi, key="n_goodman", **kw) -> float | None:
    """Smallest fillet radius in [r_lo, r_hi] whose safety factor meets n_target (bisection; n rises with r)."""
    f = lambda r: assess(D, d, r, M_Nm, T_Nm, Sut, Sy, **kw)[key] - n_target  # noqa: E731
    if f(r_hi) < 0:
        return None
    if f(r_lo) >= 0:
        return r_lo
    a, b = r_lo, r_hi
    for _ in range(60):
        m = 0.5 * (a + b)
        a, b = (a, m) if f(m) >= 0 else (m, b)
    return b

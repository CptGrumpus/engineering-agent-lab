"""Stress-life (S-N) model for 6061-T6 aluminium, notch sensitivity, mean stress.

Material data (cited; fitted here, not copied as constants):
  Strain-controlled, fully reversed tests on 6061-T6, stress amplitude vs
  reversals to failure 2Nf, from the University of Waterloo Fatigue Design &
  Evaluation (FDE) database file aa6061merged:
    Chung and Abel, ASTM STP 942 (1988), 13 points;
    Brodrick and Spiering, ASTM J. of Materials (1972), 12 points.
  https://fde.uwaterloo.ca/Fde/Materials/Alum/AA6xxx/aa6061merged.html
  All points are below 5e4 reversals, so life at 1e7 cycles is an
  extrapolation; the study cross-checks it against the ASM datasheet value
  (96.5 MPa at 5e8 cycles, fully reversed, R.R. Moore), which is independent.

Basquin:   sigma_a = sigma_f' (2 N)^b       (fitted by least squares in log-log)
Mean stress (Smith-Watson-Topper): sigma_ar = sqrt(sigma_max * sigma_a), sigma_max > 0
Notch (Peterson): q = 1 / (1 + a / r), K_f = 1 + q (K_t - 1),
  a = 0.635 mm (0.025 in) for aluminium alloys (Peterson's Stress Concentration
  Factors; Shigley).
"""

from __future__ import annotations

import numpy as np

KSI = 6.894757  # MPa

# (stress amplitude ksi, reversals 2Nf)
CHUNG_ABEL_1988 = [(43.2, 192), (41.9, 342), (40.9, 700), (40.3, 1172), (39.1, 1384),
                   (37.2, 2420), (37.9, 2980), (35.1, 4420), (35.6, 5980), (33.8, 7640),
                   (33.0, 11800), (30.6, 23260), (30.3, 41760)]
BRODRICK_SPIERING_1972 = [(50.4, 152), (50.95, 142), (50.15, 198), (48.75, 334), (48.65, 300),
                          (48.15, 564), (45.7, 898), (45.65, 906), (40.5, 8358), (40.65, 7600),
                          (37.7, 15816), (37.1, 16200)]
DATA_SETS = {"both": CHUNG_ABEL_1988 + BRODRICK_SPIERING_1972,
             "chung_abel": CHUNG_ABEL_1988, "brodrick_spiering": BRODRICK_SPIERING_1972}

PETERSON_A_ALUMINIUM_MM = 0.635


def fit_basquin(data_set: str = "both") -> dict:
    data = DATA_SETS[data_set]
    s = np.array([d[0] * KSI for d in data])
    r = np.array([d[1] for d in data], float)
    b, ln_sf = np.polyfit(np.log(r), np.log(s), 1)
    resid = np.log(s) - (ln_sf + b * np.log(r))
    return {"sigma_f_MPa": float(np.exp(ln_sf)), "b": float(b),
            "log_scatter_sd": float(resid.std(ddof=2)), "n_points": int(len(s)),
            "max_reversals_in_data": float(r.max())}


def amplitude_at(reversals, fit: dict) -> float:
    return fit["sigma_f_MPa"] * reversals ** fit["b"]


def life_cycles(sigma_ar: float, fit: dict) -> float:
    """Cycles to failure N for an equivalent fully reversed amplitude sigma_ar."""
    return 0.5 * (sigma_ar / fit["sigma_f_MPa"]) ** (1.0 / fit["b"])


def notch_sensitivity(radius_mm: float, a_mm: float = PETERSON_A_ALUMINIUM_MM) -> float:
    return 1.0 / (1.0 + a_mm / radius_mm)


def fatigue_notch_factor(kt: float, radius_mm: float) -> float:
    return 1.0 + notch_sensitivity(radius_mm) * (kt - 1.0)


def swt_amplitude(sigma_max: float, sigma_min: float) -> float:
    sigma_a = 0.5 * (sigma_max - sigma_min)
    if sigma_max <= 0:
        return 0.0
    return float(np.sqrt(sigma_max * sigma_a))

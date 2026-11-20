"""ISO 2631-1:1997 frequency weighting Wk (vertical whole-body vibration, seated/standing).

Wk(s) = H_h(s) H_l(s) H_t(s) H_s(s), the product of (ISO 2631-1 Annex A):
    band-limiting high pass   H_h = s^2 / (s^2 + w1 s / Q1 + w1^2)            f1 = 0.4 Hz, Q1 = 1/sqrt(2)
    band-limiting low pass    H_l = w2^2 / (s^2 + w2 s / Q2 + w2^2)           f2 = 100 Hz, Q2 = 1/sqrt(2)
    a-v transition            H_t = (1 + s/w3) / (1 + s/(Q4 w4) + s^2/w4^2)   f3 = f4 = 12.5 Hz, Q4 = 0.63
    upward step               H_s = (s^2 + w5 s/Q5 + w5^2) / (s^2 + w6 s/Q6 + w6^2)
                                                                       f5 = 2.37, Q5 = 0.91, f6 = 3.35, Q6 = 0.91
The weighted RMS acceleration a_w is the RMS of the acceleration filtered by Wk.
Comfort guide (ISO 2631-1 Annex C): < 0.315 m/s^2 not uncomfortable; 0.315-0.63 a
little uncomfortable; 0.5-1 fairly uncomfortable; 0.8-1.6 uncomfortable; 1.25-2.5
very uncomfortable; > 2 extremely uncomfortable.
"""

from __future__ import annotations

import numpy as np
from scipy import signal

F1, F2, F3, F4, Q4, F5, Q5, F6, Q6 = 0.4, 100.0, 12.5, 12.5, 0.63, 2.37, 0.91, 3.35, 0.91
Q1 = Q2 = 1 / np.sqrt(2)

# Wk weighting factors from ISO 2631-1:1997 Table 3 (one-third-octave centre frequencies)
TABLE_WK = {1.0: 0.482, 2.0: 0.531, 4.0: 0.967, 5.0: 1.039, 6.3: 1.054, 8.0: 1.036,
            10.0: 0.988, 16.0: 0.768, 31.5: 0.405}

COMFORT = [(0.315, "not uncomfortable"), (0.63, "a little uncomfortable"), (1.0, "fairly uncomfortable"),
           (1.6, "uncomfortable"), (2.5, "very uncomfortable"), (np.inf, "extremely uncomfortable")]


def _w(f):
    return 2 * np.pi * f


def wk_tf() -> tuple[np.ndarray, np.ndarray]:
    """(numerator, denominator) polynomial coefficients of Wk(s), highest power first."""
    w1, w2, w3, w4, w5, w6 = (_w(f) for f in (F1, F2, F3, F4, F5, F6))
    parts = [([1, 0, 0], [1, w1 / Q1, w1**2]),
             ([w2**2], [1, w2 / Q2, w2**2]),
             ([1 / w3, 1], [1 / w4**2, 1 / (Q4 * w4), 1]),
             # upward step: unity gain at high frequency, (f5/f6)^2 at low frequency. Written first
             # with unity low-frequency gain, it came out exactly 2x the standard's Table 3 values.
             ([1, w5 / Q5, w5**2], [1, w6 / Q6, w6**2])]
    num, den = np.array([1.0]), np.array([1.0])
    for n, d in parts:
        num, den = np.polymul(num, n), np.polymul(den, d)
    return num, den


def wk(freq_hz) -> np.ndarray:
    """Complex Wk at the given frequencies."""
    num, den = wk_tf()
    s = 2j * np.pi * np.asarray(freq_hz, float)
    return np.polyval(num, s) / np.polyval(den, s)


def weighted_series(t: np.ndarray, a: np.ndarray) -> np.ndarray:
    """Acceleration filtered by Wk in the time domain (continuous filter, first-order hold)."""
    num, den = wk_tf()
    _, y, _ = signal.lsim(signal.TransferFunction(num, den), a, t, interp=True)
    return y


def comfort_class(aw: float) -> str:
    return next(label for limit, label in COMFORT if aw < limit)

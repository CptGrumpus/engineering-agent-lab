"""Motor electromagnetics (study 7): the signal processing that turns flux linkages into back-EMF."""

import numpy as np
import pytest

from studies.motor_em import STUDY, fundamental, line_emf_peak, pyleecan_python


def _three_phase(n=48, lam=0.2, h5=0.0, f=66.667):
    T = 1 / f
    t = np.arange(n) * T / n
    w = 2 * np.pi * f
    ph = [0, -2 * np.pi / 3, 2 * np.pi / 3]
    P = np.column_stack([lam * np.cos(w * t + a) + h5 * np.cos(5 * (w * t + a)) for a in ph])
    return t, P, w


def test_fundamental_amplitude_and_phase():
    t, P, _ = _three_phase(h5=0.01)
    F = fundamental(t, P)
    assert np.allclose(np.abs(F), 0.2, rtol=1e-12)                          # the 5th harmonic does not leak in
    d = np.degrees(np.angle(F[0]) - np.angle(F[1])) % 360
    assert d == pytest.approx(120.0, abs=1e-9)


def test_line_emf_peak_is_the_exact_derivative():
    t, P, w = _three_phase()
    # e_ab = d(phi_a - phi_b)/dt: amplitude sqrt(3) w lambda for pure sinusoids
    assert line_emf_peak(t, P[:, 0], P[:, 1], 1.0) == pytest.approx(np.sqrt(3) * w * 0.2, rel=1e-9)
    assert line_emf_peak(t, P[:, 0], P[:, 1], 6.0) == pytest.approx(6 * np.sqrt(3) * w * 0.2, rel=1e-9)


def test_harmonics_raise_the_line_peak():
    t, P0, _ = _three_phase()
    t, P5, _ = _three_phase(h5=0.01)
    assert line_emf_peak(t, P5[:, 0], P5[:, 1], 1.0) > line_emf_peak(t, P0[:, 0], P0[:, 1], 1.0)


def test_metrics_from_a_synthetic_machine():
    t, P, w = _three_phase(f=1000 / 60 * 4)                                 # 1000 rpm, 4 pole pairs
    s = {"time_s": t, "phi_a_Wb": P[:, 0], "phi_b_Wb": P[:, 1], "phi_c_Wb": P[:, 2]}
    params = {"speed_rpm": 1000.0, "max_speed_rpm": 6000.0}
    m = STUDY.compute_metrics(s, params, {}, {"pole_pairs": 4, "torque_Nm": [0.0, 0.1]})
    assert m["back_emf_LL_rms_per_krpm_V"] == pytest.approx(np.sqrt(3) * w * 0.2 / np.sqrt(2), rel=1e-9)
    assert m["back_emf_LL_peak_at_max_speed_V"] == pytest.approx(6 * np.sqrt(3) * w * 0.2, rel=1e-9)


def test_default_interpreter_path_has_no_user_name_baked_in():
    p = str(pyleecan_python())
    assert ".venvs" in p and "pyleecan" in p

"""Motor torque study (study 7): power balance and MTPA post-processing on signals with known answers."""

import numpy as np
import pytest

from studies.motor_torque import mtpa, power_balance, spectral_derivative


def _op(lam=0.2, I_rms=100.0, beta=0.7, n=48, f=66.667, h5=0.0, speed_rpm=1000.0, pole_pairs=4):
    t = np.arange(n) / (n * f)
    w = 2 * np.pi * f
    ph = np.array([0, -2 * np.pi / 3, 2 * np.pi / 3])
    phi = np.column_stack([lam * np.cos(w * t + a) + h5 * np.cos(5 * (w * t + a)) for a in ph])
    cur = np.column_stack([np.sqrt(2) * I_rms * np.cos(w * t + a + beta) for a in ph])
    # exact mean power for sinusoids: 3/2 * w * lam * Ipk * sin(beta) (the 5th harmonic carries no mean power)
    p = 1.5 * w * lam * np.sqrt(2) * I_rms * np.sin(beta)
    torque = np.full(n, p / (2 * np.pi * speed_rpm / 60))
    return {"time_s": t, "phi_Wb": phi, "current_A": cur, "torque_Nm": torque}, p


def test_spectral_derivative_is_exact_for_a_sinusoid():
    t = np.arange(48) / 48.0
    x = np.column_stack([np.sin(2 * np.pi * t), np.cos(6 * np.pi * t)])
    d = spectral_derivative(t, x)
    assert np.allclose(d[:, 0], 2 * np.pi * np.cos(2 * np.pi * t), atol=1e-9)
    assert np.allclose(d[:, 1], -6 * np.pi * np.sin(6 * np.pi * t), atol=1e-9)


@pytest.mark.parametrize("h5", [0.0, 0.01])
def test_power_balance_matches_torque_times_speed(h5):
    op, p = _op(h5=h5)
    p_el, p_mech = power_balance(op, 1000.0, flux_sign=1.0)
    assert p_el == pytest.approx(p, rel=1e-9)
    assert p_mech == pytest.approx(p, rel=1e-12)


def test_power_balance_detects_a_root_two_current_error():
    op, _ = _op()
    op["current_A"] = op["current_A"] / np.sqrt(2)          # currents read as peak instead of rms
    p_el, p_mech = power_balance(op, 1000.0, flux_sign=1.0)
    assert abs(p_el - p_mech) / p_mech > 0.25


def test_mtpa_parabola_and_bracketing():
    g = np.array([10, 20, 30, 40, 50, 60, 70.0])
    T = 300 - 0.1 * (g - 43.0) ** 2
    gm, Tm, interior = mtpa(g, T)
    assert interior and gm == pytest.approx(43.0) and Tm == pytest.approx(300.0)
    _, _, interior = mtpa(g, 300 - g)                        # maximum at the first angle
    assert not interior


def test_power_balance_sign_convention_is_enforced():
    op, _ = _op()
    p_el, p_mech = power_balance(op, 1000.0)                 # default: Pyleecan's sign, wrong for this signal
    assert p_el == pytest.approx(-p_mech, rel=1e-9)

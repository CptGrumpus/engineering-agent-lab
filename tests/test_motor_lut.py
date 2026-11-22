"""The dq look-up table study (study 7): pure-Python parts (the FEMM side is exercised by its smoke test and runs)."""

import numpy as np
import pytest

from studies.motor_lut import DQ_FLUX_SIGN, STUDY, dq_torque, iron_loss_W, series_from_outputs


def _op(i_d, i_q, pd, pq, T, coeff):
    return {"id_rms_A": i_d, "iq_rms_A": i_q, "phi_d_Wb": pd, "phi_q_Wb": pq, "torque_Nm": [T, T],
            "iron": {"stator": {"coeff_W": coeff}, "rotor": {"coeff_W": [0.0, 0.0, 0.0]}}}


def test_dq_torque_matches_the_smoke_test_point():
    # smoke test 2026-11-22: id -100, iq 150 A rms; FEMM 403.45 N m
    op = {"id_rms_A": -100.0, "iq_rms_A": 150.0, "phi_d_Wb": 0.02065, "phi_q_Wb": 0.30519}
    assert dq_torque(op, 4, DQ_FLUX_SIGN) == pytest.approx(403.45, rel=1e-3)


def test_iron_loss_polynomial_and_metrics():
    ops = [_op(-50.0, q, 0.15, 0.002 * q, 10 * q, [2.0, 0.01, 0.05]) for q in (0.0, 100.0, 200.0)]
    s = series_from_outputs(ops)
    f = 400.0
    assert iron_loss_W({k: v[0] for k, v in s.items()}, f) == pytest.approx(2.0 * f + 0.01 * f**2 + 0.05 * f**1.5)
    params = {"speed_rpm": 1000.0, "turns_per_slot": 9, "slot_fill": 1.0, "slot_area_mm2": 76.43}
    m = STUDY.compute_metrics(s, params, {}, {"pole_pairs": 4})
    assert m["torque_at_iq_max_Nm"] == 2000.0
    assert m["current_density_max_A_per_mm2"] == pytest.approx(9 * np.hypot(50, 200) / 76.43)
    f6 = 6000 / 60 * 4
    assert m["iron_loss_at_iq_max_6000rpm_W"] == pytest.approx(2.0 * f6 + 0.01 * f6**2 + 0.05 * f6**1.5)

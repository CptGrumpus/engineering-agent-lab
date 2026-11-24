"""Efficiency map from a dq table (study 7): the search, on a synthetic machine with constant inductances."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from studies.motor_efficiency import phase_resistance_20C

_spec = importlib.util.spec_from_file_location("em", Path(__file__).resolve().parent.parent / "models/motor/efficiency_map.py")
em = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(em)

P, PSI_M, LD, LQ = 4, 0.153, 1.3e-3, 2.0e-3


def synthetic(iron=(1.0, 0.004, 0.02)):
    ids, iqs = np.arange(-300.0, 0.1, 25.0), np.arange(0.0, 300.1, 25.0)
    D, Q = np.meshgrid(ids, iqs, indexing="ij")
    pd, pq = PSI_M + LD * D, LQ * Q
    g = {"id": ids, "iq": iqs, "phi_d_Wb": pd, "phi_q_Wb": pq, "torque_mean_Nm": 3 * P * (pd * Q - pq * D)}
    for c, v in zip("ABC", iron):
        g[f"iron_{c}_W"] = np.full_like(D, v)
    return g


def test_low_speed_point_is_minimum_current():
    """Iron loss independent of current: the lowest-loss point is the lowest-current one (MTPA)."""
    fine = em.fine_grid(synthetic(), step_A=1.0)
    r = em.operating_points(fine, speed_rpm=500, torques_Nm=[200.0], pole_pairs=P, r_ohm=0.06, v_max_rms=204.0,
                            i_max_rms=300.0)
    # brute force on the exact model
    g = np.radians(np.linspace(0, 89, 8901))
    best = None
    for I in np.arange(50, 300, 0.05):
        T = 3 * P * ((PSI_M - LD * I * np.sin(g)) * I * np.cos(g) + LQ * I * np.cos(g) * I * np.sin(g))
        if T.max() >= 200.0:
            best = I
            break
    assert r["current_A"][0] == pytest.approx(best, rel=0.01)
    assert r["torque_Nm"][0] == pytest.approx(200.0, rel=0.006)


def test_high_speed_points_respect_the_voltage_limit_and_efficiency_is_consistent():
    fine = em.fine_grid(synthetic(), step_A=1.0)
    m = em.efficiency_map(fine, speeds_rpm=[1000, 4000, 6000], torques_Nm=[20.0, 60.0, 100.0], pole_pairs=P,
                          r_ohm=0.06, v_max_rms=204.0, i_max_rms=300.0)
    ok = ~np.isnan(m["efficiency_pct"])
    assert ok.sum() >= 7
    assert np.all(m["voltage_V"][ok] <= 204.0 + 1e-9)
    w_m = 2 * np.pi * m["speed_rpm"][ok] / 60
    p_out = m["torque_Nm"][ok] * w_m
    eff = 100 * p_out / (p_out + m["p_cu_W"][ok] + m["p_fe_W"][ok])
    assert np.allclose(eff, m["efficiency_pct"][ok])
    # at 6000 rpm the open-circuit voltage (6000/1000 x 64 V) exceeds the limit: flux weakening, id < 0
    hi = ok & (m["speed_rpm"] == 6000)
    assert np.all(m["id_A"][hi] < -50)


def test_phase_resistance_from_geometry():
    p = {"stack_length_m": 0.08382, "end_connection_length_m": 0.118, "copper_resistivity_20C_ohm_m": 1.72e-8,
         "series_turns_per_phase": 72, "turn_copper_area_mm2": 8.492}
    assert phase_resistance_20C(p) == pytest.approx(1.72e-8 * 72 * (2 * 0.08382 + 2 * 0.118) / 8.492e-6)
    assert em.resistance(1.0, 100.0) == pytest.approx(1 + 0.00393 * 80)


def test_phase_resistance_measured_referred_to_20C():
    p = {"stack_length_m": 0.08382, "end_connection_length_m": 0.118, "copper_resistivity_20C_ohm_m": 1.72e-8,
         "series_turns_per_phase": 72, "turn_copper_area_mm2": 8.492, "copper_alpha_per_K": 0.00393,
         "phase_resistance_measured_ohm": 0.069, "phase_resistance_measured_at_C": 21.0}
    assert phase_resistance_20C(p) == pytest.approx(0.069 / (1 + 0.00393))
    p["phase_resistance_measured_ohm"] = 0.0           # 0 means: not given, use the geometry
    assert phase_resistance_20C(p) == pytest.approx(1.72e-8 * 72 * (2 * 0.08382 + 2 * 0.118) / 8.492e-6)


def _fake_run(root, name, ids, iqs, magnet_T=20.0, bump=0.0):
    """A motor_lut run on disk from the synthetic machine: one point per d-axis current, lut.csv per point."""
    import csv
    import json

    run = root / name
    for k, d in enumerate(ids):
        pdir = run / "points" / f"p{k:02d}"
        pdir.mkdir(parents=True)
        (pdir / "point.json").write_text(json.dumps({"status": "completed", "solver_outputs": {"pole_pairs": P},
                                                     "parameters": {"magnet_temperature_C": magnet_T}}))
        with open(pdir / "lut.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id_rms_A", "iq_rms_A", "torque_mean_Nm", "phi_d_Wb", "phi_q_Wb"]
                       + [f"{c}_iron_{x}_W" for c in ("stator", "rotor") for x in "ABC"])
            for q in iqs:
                pd, pq = PSI_M + LD * d, LQ * q
                w.writerow([d, q, 3 * P * (pd * q - pq * d) * (1 + bump), pd, pq, 1.0, 0.004, 0.02, 0.1, 0.0004, 0.002])
    return run


def test_merged_tables_form_the_union_grid_and_report_overlap_agreement(tmp_path):
    from studies.motor_efficiency import load_lut, run_list

    ids = [-50.0, -25.0, 0.0]
    main = _fake_run(tmp_path, "main", ids, [0.0, 25.0, 50.0])
    low = _fake_run(tmp_path, "low", ids, [6.25, 12.5, 25.0])
    g = load_lut([main, low])
    assert list(g["iq"]) == [0.0, 6.25, 12.5, 25.0, 50.0]
    assert g["torque_mean_Nm"].shape == (3, 5)
    assert g["merge_max_rel_diff"] == 0.0
    # a supplementary run that does not reproduce the shared row is caught, and the main run's values are kept
    off = _fake_run(tmp_path, "off", ids, [12.5, 25.0], bump=1e-3)
    g2 = load_lut([main, off])
    assert g2["merge_max_rel_diff"] == pytest.approx(1e-3, rel=1e-2)
    assert np.allclose(g2["torque_mean_Nm"][:, list(g2["iq"]).index(25.0)], g["torque_mean_Nm"][:, 3])
    assert run_list("a, b") == ["a", "b"] and run_list("a") == ["a"]


def test_merging_tables_at_different_magnet_temperatures_is_refused(tmp_path):
    from studies.motor_efficiency import load_lut

    a = _fake_run(tmp_path, "a", [0.0], [0.0, 25.0], magnet_T=20.0)
    b = _fake_run(tmp_path, "b", [0.0], [12.5], magnet_T=80.0)
    with pytest.raises(ValueError, match="magnet temperature"):
        load_lut([a, b])

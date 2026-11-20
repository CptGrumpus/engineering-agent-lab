from pathlib import Path

import numpy as np
import pytest
import tomllib

from excitation.road import N0, Road, iso8608_sinusoids
from harness.run import run_case
from harness.runio import read_json
from harness.verify import verify_run
from validation import quarter_car_reference as ref

BUMP = tomllib.loads(Path("cases/qc_speed_bump.toml").read_text(encoding="utf-8"))["parameters"]
ROAD = tomllib.loads(Path("cases/qc_iso_road.toml").read_text(encoding="utf-8"))["parameters"]


def test_transfer_functions_match_state_space():
    """Hand-derived polynomials vs C (jwI - A)^-1 B from the state matrices."""
    A, B = ref.state_space(BUMP)
    f = np.array([0.1, 1.2, 5.0, 11.7, 30.0])
    h = ref.frequency_response(BUMP, f)
    for fi, acc, travel, tire in zip(f, h["body_accel"], h["travel"], h["tire_deflection"]):
        s = 2j * np.pi * fi
        x = np.linalg.solve(s * np.eye(4) - A, B[:, 0])  # [zs, vs, zu, vu] per m of road
        assert acc == pytest.approx(s * x[1], rel=1e-9)
        assert travel == pytest.approx(x[0] - x[2], rel=1e-9)
        assert tire == pytest.approx(x[2] - 1.0, rel=1e-9)


def test_static_transmissibility_is_one():
    h = ref.frequency_response(BUMP, [1e-6])
    assert abs(h["travel"][0]) < 1e-9
    assert abs(h["tire_deflection"][0]) < 1e-9


def test_road_spectrum_matches_iso8608():
    s = iso8608_sinusoids(ROAD)
    v = ROAD["speed_m_per_s"]
    df = 1 / ROAD["window_s"]
    n = s.freq_hz / v
    gd = s.amp_m**2 / 2 / (df / v)  # back out the one-sided PSD from amplitudes
    assert np.allclose(gd, ROAD["road_Gd_n0_m3"] * (n / N0) ** -2, rtol=1e-12)
    # variance of the realised road over the window equals sum(A^2/2)
    t = np.arange(0, ROAD["window_s"], 1e-3)
    assert np.var(s.zr(t)) == pytest.approx(np.sum(s.amp_m**2 / 2), rel=1e-6)


def test_bump_profile():
    road = Road(BUMP)
    dur = BUMP["bump_length_m"] / BUMP["speed_m_per_s"]
    assert road.zr(dur / 2) == pytest.approx(BUMP["bump_height_m"])
    assert road.zr(-0.1) == 0 and road.zr(dur + 0.1) == 0
    t = np.linspace(0, dur, 2001)
    # central differences (interior points only; np.gradient is one-sided at the ends)
    assert np.allclose(np.gradient(road.zr(t), t)[1:-1], road.vr(t)[1:-1],
                       atol=1e-5 * road.vr(t).max())


def _small_case(tmp_path, src, values, edit=None):
    text = Path(src).read_text(encoding="utf-8").replace(
        "values = [600.0, 1000.0, 1500.0, 2200.0, 3500.0]", f"values = {values}")
    if edit:
        text = edit(text)
    p = tmp_path / Path(src).name
    p.write_text(text, encoding="utf-8")
    return p


def test_speed_bump_pipeline_passes(tmp_path):
    run_dir = run_case(_small_case(tmp_path, "cases/qc_speed_bump.toml", "[1000.0]"),
                       runs_root=tmp_path / "runs")
    assert verify_run(run_dir)["status"] == "PASS"
    m = read_json(run_dir / "manifest.json")["points"][0]["metrics"]
    assert m["peak_body_accel_m_per_s2"] == pytest.approx(3.56, abs=0.01)


def test_iso_road_pipeline_passes(tmp_path):
    run_dir = run_case(_small_case(tmp_path, "cases/qc_iso_road.toml", "[1500.0]"),
                       runs_root=tmp_path / "runs")
    summary = verify_run(run_dir)
    assert summary["status"] == "PASS", summary


def test_wheel_lift_invalidates_linear_model(tmp_path):
    """At 10 m/s the wheel leaves the road: numerics pass, validity check must fail."""
    run_dir = run_case(_small_case(tmp_path, "cases/qc_bump.toml", "[1500.0]"),
                       runs_root=tmp_path / "runs")
    checks = {c["id"]: c for c in verify_run(run_dir)["points"][0]["checks"]}
    assert checks["no_wheel_lift"]["status"] == "FAIL"
    assert checks["no_wheel_lift"]["kind"] == "validity"
    assert checks["reference_agreement"]["status"] == "PASS"


def test_window_must_be_whole_steps(tmp_path):
    case = _small_case(tmp_path, "cases/qc_iso_road.toml", "[1500.0]",
                       lambda s: s.replace("window_s = 10.0", "window_s = 10.0005"))
    run_dir = run_case(case, runs_root=tmp_path / "runs")
    point = read_json(run_dir / "manifest.json")["points"][0]
    assert point["status"] == "failed"
    assert "integer number of output steps" in point["error"]


def _bump_params(speed, c=1500.0):
    return dict(sprung_mass_kg=350.0, unsprung_mass_kg=45.0, suspension_stiffness_N_per_m=22000.0,
                damping_N_s_per_m=c, tire_stiffness_N_per_m=220000.0, road="bump",
                speed_m_per_s=speed, bump_height_m=0.04, bump_length_m=1.0, tire_model="liftoff")


def test_liftoff_reference_equals_linear_reference_when_wheel_stays_down():
    import numpy as np

    from validation import quarter_car_reference as ref
    p = _bump_params(5.0)
    t = np.linspace(0.0, 4.0, 8001)
    a, b = ref.time_response_liftoff(p, t), ref.time_response(p, t)
    assert a["events"] == []
    assert max(np.abs(a["zs_m"] - b["zs_m"]).max(), np.abs(a["zu_m"] - b["zu_m"]).max()) < 1e-7


def test_liftoff_model_matches_exact_events_and_response():
    import numpy as np

    from models import quarter_car as qc
    from validation import quarter_car_reference as ref
    p = _bump_params(10.0, c=600.0)
    r = qc.simulate(p, t_end_s=2.0, n_points=4001, method="DOP853", rtol=1e-9, atol=1e-12)
    exact = ref.time_response_liftoff(p, r["series"]["t_s"])
    got, want = r["outputs"]["tire_events"], exact["events"]
    assert [k for _, k in got] == [k for _, k in want] == ["liftoff", "touchdown"] * 2
    assert max(abs(a - b) for (a, _), (b, _) in zip(got, want)) < 1e-8
    assert np.abs(r["series"]["zu_m"] - exact["zu_m"]).max() / 0.04 < 1e-6


def test_liftoff_case_gives_the_verdict_the_linear_model_withheld(tmp_path):
    """Same 10 m/s bump as test_wheel_lift_invalidates_linear_model, with the lift-off tire:
    every check passes, there is no validity gate, and the road-holding verdict is a fail."""
    run_dir = run_case(_small_case(tmp_path, "cases/qc_bump_liftoff.toml", "[600.0]"),
                       runs_root=tmp_path / "runs")
    summary = verify_run(run_dir)
    assert summary["status"] == "PASS", summary
    checks = {c["id"] for c in summary["points"][0]["checks"]}
    assert "no_wheel_lift" not in checks and "contact_event_times" in checks
    m = read_json(run_dir / "manifest.json")["points"][0]["metrics"]
    assert m["airborne_time_ms"] == pytest.approx(59.0, abs=0.6)
    assert m["max_tire_load_ratio"] == pytest.approx(1.59, abs=0.01)


def test_bump_stop_switches_match_the_exact_piecewise_solution():
    from models import quarter_car as qc

    p = _bump_params(10.0, c=600.0) | {"bump_stop_gap_mm": 40.0, "bump_stop_stiffness_N_per_m": 300000.0}
    r = qc.simulate(p, t_end_s=2.0, n_points=4001, method="DOP853", rtol=1e-9, atol=1e-12)
    exact = ref.time_response_liftoff(p, r["series"]["t_s"])
    got = sorted(r["outputs"]["tire_events"] + r["outputs"]["stop_events"])
    assert [k for _, k in got] == [k for _, k in exact["events"]]
    assert "stop_on" in [k for _, k in got]
    assert max(abs(a - b) for (a, _), (b, _) in zip(got, exact["events"])) < 1e-8
    assert np.abs(r["series"]["zu_m"] - exact["zu_m"]).max() / 0.04 < 1e-6


def test_bump_stop_that_never_engages_changes_nothing():
    from models import quarter_car as qc

    base = _bump_params(10.0, c=3500.0)
    stop = base | {"bump_stop_gap_mm": 40.0, "bump_stop_stiffness_N_per_m": 300000.0}
    kw = dict(t_end_s=2.0, n_points=4001, method="DOP853", rtol=1e-9, atol=1e-12)
    a, b = qc.simulate(base, **kw)["series"], qc.simulate(stop, **kw)["series"]
    assert np.abs(a["zs_m"] - b["zs_m"]).max() < 1e-12

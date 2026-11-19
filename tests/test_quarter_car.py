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

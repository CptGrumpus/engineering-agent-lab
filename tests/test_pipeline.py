"""End-to-end: run -> verify -> report -> rerun, plus negative tests showing the
checks catch a wrong model and that bad inputs are rejected."""

from pathlib import Path

import numpy as np
import pytest

from harness.__main__ import main
from harness.case import CaseError, load_case
from harness.report import build_report
from harness.rerun import rerun
from harness.run import run_case
from harness.runio import read_json, read_timeseries, write_timeseries
from harness.verify import verify_run

CASE = Path("cases/msd_step.toml")


def small_case(tmp_path: Path, sweep_values="[0.1, 0.5, 2.0]", extra_edit=None) -> Path:
    text = CASE.read_text(encoding="utf-8")
    text = text.replace("values = [0.1, 0.3, 0.5, 0.7, 1.0, 2.0]", f"values = {sweep_values}")
    if extra_edit:
        text = extra_edit(text)
    p = tmp_path / "case.toml"
    p.write_text(text, encoding="utf-8")
    return p


def test_full_pipeline_passes_and_reproduces(tmp_path):
    run_dir = run_case(small_case(tmp_path), runs_root=tmp_path / "runs")
    manifest = read_json(run_dir / "manifest.json")
    assert manifest["status"] == "completed"
    assert manifest["environment"]["packages"]["scipy"]

    summary = verify_run(run_dir)
    assert summary["status"] == "PASS", summary

    report = build_report(run_dir).read_text(encoding="utf-8")
    assert "Verification status:** PASS" in report
    assert "72.94 %: **FAIL**" in report  # zeta = 0.1 violates REQ-001
    assert "Pending human review" in report
    for label in ("p00_damping_ratio-0.1", "p02_damping_ratio-2"):
        assert (run_dir / "points" / label / "response.png").exists()

    new_dir, result = rerun(run_dir)
    assert result["status"] == "PASS"
    assert all(p["bit_identical"] for p in result["points"])
    assert read_json(new_dir / "manifest.json")["rerun_of"] == run_dir.name


def test_verification_catches_wrong_model(tmp_path):
    """Corrupt the stored response by 0.1 % (e.g. a units or stiffness slip)."""
    run_dir = run_case(small_case(tmp_path, "[0.5]"), runs_root=tmp_path / "runs")
    ts = run_dir / "points" / "p00_damping_ratio-0.5" / "timeseries.csv"
    t, x, v = read_timeseries(ts)
    write_timeseries(ts, t, x * 1.001, v)

    summary = verify_run(run_dir)
    assert summary["status"] == "FAIL"
    failed = {c["id"] for c in summary["points"][0]["checks"] if c["status"] == "FAIL"}
    # steady_state (tol 1e-3) and energy_balance are deliberately coarser and
    # need not catch a 0.1 % error; the reference comparison must.
    assert {"reference_agreement", "solver_convergence"} <= failed

    report = build_report(run_dir).read_text(encoding="utf-8")
    assert "(unverified)" in report
    assert "must not be used for" in report


def test_too_short_simulation_fails_steady_state(tmp_path):
    case = small_case(tmp_path, "[0.1]",
                      lambda s: s.replace("t_end_s = 3.0", "t_end_s = 0.8")
                                 .replace("n_points = 30001", "n_points = 8001"))
    run_dir = run_case(case, runs_root=tmp_path / "runs")
    summary = verify_run(run_dir)
    checks = {c["id"]: c["status"] for c in summary["points"][0]["checks"]}
    assert checks["steady_state"] == "FAIL"
    assert summary["status"] == "FAIL"


def test_invalid_parameter_is_recorded_not_raised(tmp_path):
    run_dir = run_case(small_case(tmp_path, "[-0.5, 0.5]"), runs_root=tmp_path / "runs")
    manifest = read_json(run_dir / "manifest.json")
    assert manifest["status"] == "partial"
    assert "damping_ratio must be non-negative" in manifest["points"][0]["error"]
    assert verify_run(run_dir)["points"][0]["status"] == "NOT_RUN"


def test_bad_requirement_metric_rejected(tmp_path):
    case = small_case(tmp_path, extra_edit=lambda s: s.replace(
        'metric = "overshoot_pct"', 'metric = "overshoot"'))
    with pytest.raises(CaseError, match="metric must be one of"):
        load_case(case)
    assert main(["run", str(case), "--runs-root", str(tmp_path / "runs")]) == 2


def test_tampered_inputs_detected(tmp_path):
    run_dir = run_case(small_case(tmp_path, "[0.5]"), runs_root=tmp_path / "runs")
    saved = run_dir / "inputs" / "case.toml"
    saved.write_text(saved.read_text(encoding="utf-8").replace("limit = 20.0", "limit = 80.0"),
                     encoding="utf-8")
    with pytest.raises(RuntimeError, match="no longer matches"):
        verify_run(run_dir)


def test_failed_run_level_check_withholds_verdicts():
    from harness.report import evaluate

    case = {"requirements": [
        {"id": "R1", "text": "", "metric": "a", "operator": "<=", "limit": 1.0, "units": ""},
        {"id": "R2", "text": "", "metric": "b", "operator": "<=", "limit": 1.0, "units": ""}]}
    manifest = {"points": [{"label": "p0", "parameters": {}, "status": "completed",
                            "metrics": {"a": 0.5, "b": 0.5}}]}
    ver = {"points": [{"label": "p0", "status": "PASS", "checks": []}],
           "run_checks": [{"id": "discretization_a", "status": "FAIL", "metric": "a"}]}
    verdicts = {r["id"]: r["verdict"] for r in evaluate(case, manifest, ver)["points"][0]["requirements"]}
    assert verdicts == {"R1": "PASS (unverified)", "R2": "PASS"}
    ver["run_checks"] = [{"id": "run_level_error", "status": "FAIL"}]  # no metric: blanket
    verdicts = {r["id"]: r["verdict"] for r in evaluate(case, manifest, ver)["points"][0]["requirements"]}
    assert verdicts == {"R1": "PASS (unverified)", "R2": "PASS (unverified)"}

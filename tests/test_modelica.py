"""OpenModelica backend: end-to-end run, verification, and cross-tool check.

Skipped when omc is not installed.
"""

from pathlib import Path

import pytest

from harness.backends import ModelicaError, find_omc
from harness.compare import compare_runs
from harness.rerun import rerun
from harness.run import run_case
from harness.runio import read_json
from harness.verify import verify_run

try:
    find_omc()
    HAVE_OMC = True
except ModelicaError:
    HAVE_OMC = False

pytestmark = pytest.mark.skipif(not HAVE_OMC, reason="OpenModelica (omc) not installed")

SWEEP = "values = [0.1, 0.3, 0.5, 0.7, 1.0, 2.0]"


def write_case(tmp_path, src, sweep="[0.1, 2.0]", edit=None):
    text = Path(src).read_text(encoding="utf-8").replace(SWEEP, f"values = {sweep}")
    if edit:
        text = edit(text)
    p = tmp_path / Path(src).name
    p.write_text(text, encoding="utf-8")
    return p


def test_modelica_matches_reference_and_scipy(tmp_path):
    runs = tmp_path / "runs"
    om = run_case(write_case(tmp_path, "cases/msd_step_modelica.toml"), runs_root=runs)
    manifest = read_json(om / "manifest.json")
    assert manifest["status"] == "completed", manifest
    assert "OpenModelica" in manifest["environment"]["tools"]["omc"]
    assert (om / "inputs" / "EngLab.mo").exists()
    assert (om / "build" / "omc_build.log").exists()

    assert verify_run(om)["status"] == "PASS"

    sp = run_case(write_case(tmp_path, "cases/msd_step.toml"), runs_root=runs)
    result = compare_runs(om, sp)
    assert result["status"] == "PASS"
    assert result["against_model"] == "msd"

    _, repro = rerun(om)
    assert repro["status"] == "PASS"


def test_broken_model_source_is_recorded(tmp_path):
    case = write_case(tmp_path, "cases/msd_step_modelica.toml", "[0.5]")
    run_dir = run_case(case, runs_root=tmp_path / "runs")
    # Corrupt the saved model, then reproduce from it: the build must fail visibly.
    saved = run_dir / "inputs" / "EngLab.mo"
    saved.write_text(saved.read_text(encoding="utf-8").replace("end MSDStep;", ""),
                     encoding="utf-8")
    new_dir, repro = rerun(run_dir)
    manifest = read_json(new_dir / "manifest.json")
    assert manifest["status"] == "failed"
    assert "omc build failed" in manifest["prepare_error"]
    assert repro["status"] == "FAIL"

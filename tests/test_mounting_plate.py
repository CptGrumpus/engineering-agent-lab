from pathlib import Path

import pytest
import tomllib

from harness.run import run_case
from harness.runio import read_json
from harness.verify import verify_run
from models.cad import mounting_plate as model
from studies.mounting_plate import STUDY, measure
from validation import plate_geometry as ref

P = tomllib.loads(Path("cases/mounting_plate.toml").read_text(encoding="utf-8"))["parameters"]


def test_cad_volume_matches_closed_form():
    m = measure(model.build(P).val())
    assert m["valid"]
    assert m["volume_mm3"] == pytest.approx(ref.volume(P), rel=1e-12)
    assert len(m["holes"]) == 6


def test_no_fillet_and_single_row():
    p = dict(P, corner_radius_mm=0.0, holes_y=1)
    m = measure(model.build(p).val())
    assert m["volume_mm3"] == pytest.approx(ref.volume(p), rel=1e-12)
    assert [h[1] for h in m["holes"]] == pytest.approx([0.0, 0.0, 0.0])
    assert ref.ligament(p) == pytest.approx(40.0 - P["hole_diameter_mm"])


def test_holes_breaking_out_are_rejected():
    with pytest.raises(ValueError, match="break out"):
        STUDY.derive(dict(P, hole_pitch_x_mm=58.0))


def test_plate_pipeline(tmp_path):
    text = Path("cases/mounting_plate.toml").read_text(encoding="utf-8").replace(
        "values = [5.5, 6.6, 9.0, 11.0, 13.5]", "values = [9.0, 13.5]")
    case = tmp_path / "c.toml"
    case.write_text(text, encoding="utf-8")
    run_dir = run_case(case, runs_root=tmp_path / "runs")
    pts = read_json(run_dir / "manifest.json")["points"]
    assert pts[0]["metrics"]["mass_g"] == pytest.approx(148.4, abs=0.05)
    assert (run_dir / "points" / pts[0]["label"] / "solver" / "plate.step").exists()
    assert verify_run(run_dir)["status"] == "PASS"

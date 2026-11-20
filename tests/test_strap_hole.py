from pathlib import Path

import numpy as np
import pytest
from scipy.integrate import quad

from validation import stress_concentration as sc


def test_peterson_limits_and_values():
    assert sc.kt_net(0.0, 40.0) == pytest.approx(3.0)          # Kirsch, infinite plate
    assert sc.kt_net(39.999, 40.0) == pytest.approx(2.0, abs=1e-3)
    assert sc.kt_net(10.0, 40.0) == pytest.approx(2.4223, abs=1e-4)
    assert sc.peak_stress(5000, 40, 10, 4) == pytest.approx(100.93, abs=0.01)
    with pytest.raises(ValueError):
        sc.kt_net(40.0, 40.0)


def test_kirsch_ligament_peak_and_far_field():
    r, s = 5.0, 31.25
    assert sc.kirsch_sigma_xx_on_ligament(r, r, s) == pytest.approx(3 * s)
    assert sc.kirsch_sigma_xx_on_ligament(1e4, r, s) == pytest.approx(s, rel=1e-6)
    # in an infinite plate the ligament carries the removed load: the excess over
    # the far field integrates to sigma * r
    excess, _ = quad(lambda y: sc.kirsch_sigma_xx_on_ligament(y, r, s) - s, r, np.inf)
    assert excess == pytest.approx(s * r, rel=1e-9)


def test_requirement_crossing_predicted_near_17_mm():
    from scipy.optimize import brentq
    d = brentq(lambda d: sc.peak_stress(5000, 40, d, 4) - 120.0, 10, 20)
    assert d == pytest.approx(16.93, abs=0.01)


try:
    from studies.cantilever import find_freecadcmd
    find_freecadcmd()
    HAVE_FREECAD = True
except Exception:
    HAVE_FREECAD = False


@pytest.mark.skipif(not HAVE_FREECAD, reason="FreeCAD (CalculiX, Gmsh) not installed")
def test_pipeline_reproduces_kirsch_in_a_wide_plate(tmp_path):
    """Exact check of the CAD -> Gmsh -> CalculiX pipeline: a 10 mm hole in a
    1000 mm wide plate must give Kt_gross = 3 (Kirsch). Guards the plane-stress
    trap: CalculiX's 2D elements are one-layer 3D wedges, and a thick section
    gave 3.045 here."""
    from harness.run import run_case
    from harness.runio import read_json

    text = (Path("cases/strap_hole_mesh.toml").read_text(encoding="utf-8")
            .replace("values = [1.0, 0.5, 0.25, 0.125]", "values = [0.25]")
            .replace("width_mm = 40.0", "width_mm = 1000.0")
            .replace("length_mm = 160.0", "length_mm = 4000.0")
            .replace("far_element_size_mm = 4.0", "far_element_size_mm = 10.0"))
    case = tmp_path / "c.toml"
    case.write_text(text, encoding="utf-8")
    run_dir = run_case(case, runs_root=tmp_path / "runs")
    pt = read_json(run_dir / "manifest.json")["points"][0]
    assert pt["status"] == "completed"
    kt_gross = pt["metrics"]["peak_hole_stress_MPa"] / (5000 / (1000 * 4))
    assert kt_gross == pytest.approx(3.0, rel=5e-3)

from pathlib import Path

import numpy as np
import pytest

from harness.calculix import read_dat_total_forces, read_frd
from harness.convergence import discretization_uncertainty, gci
from validation import beam_theory as beam


def test_gci_recovers_manufactured_order_and_limit():
    f_exact, C, p = 2.0, 0.3, 2.0
    hs = (1.0, 1.6, 2.56)
    f = tuple(f_exact + C * h**p for h in hs)
    g = gci(hs, f)
    assert g["order"] == pytest.approx(p, rel=1e-9)
    assert g["extrapolated"] == pytest.approx(f_exact, rel=1e-12)
    # GCI must bound the true relative error of the fine solution
    assert g["gci_fine"] >= abs(f[0] - f_exact) / f_exact


def test_gci_nonconstant_refinement_ratio():
    hs = (1.0, 1.5, 2.7)
    f = tuple(5.0 - 0.2 * h**1.5 for h in hs)
    assert gci(hs, f)["order"] == pytest.approx(1.5, rel=1e-8)


def test_discretization_regimes():
    hs = (1.0, 1.6, 2.56)
    assert discretization_uncertainty(hs, (1.0, 1.01, 1.03))["regime"] == "monotone"
    osc = discretization_uncertainty(hs, (1.0, 1.002, 0.999))
    assert osc["regime"] == "oscillatory"
    assert osc["uncertainty"] == pytest.approx(1.25 * 0.5 * 0.003 / 1.0)
    assert discretization_uncertainty(hs, (1.0, 1.05, 1.06))["regime"] == "divergent"


def test_beam_theory_values():
    # 200 x 20 x 20 mm steel, 1 kN: EB tip = 0.952 mm, root stress = 150 MPa
    assert beam.euler_bernoulli_tip(1000, 200, 210000, 20, 20) == pytest.approx(0.952381, rel=1e-6)
    assert beam.bending_stress(1000, 200, 20, 20) == pytest.approx(150.0)
    assert beam.cowper_kappa(0.3) == pytest.approx(0.8497, rel=1e-4)
    assert beam.timoshenko_deflection(200, 1000, 200, 210000, 0.3, 20, 20) == pytest.approx(
        beam.timoshenko_tip(1000, 200, 210000, 0.3, 20, 20))


FRD = """    1C
    2C                             2                                     1
 -1         1 0.00000E+00 0.00000E+00 2.00000E+01
 -1         2 2.00000E+02 1.00000E+01-5.00000E+00
 -3
  100CL  101 1.000000000           2                     0    1           1
 -4  DISP        4    1
 -5  D1          1    2    1    0
 -5  D2          1    2    2    0
 -5  D3          1    2    3    0
 -5  ALL         1    2    0    0    1ALL
 -1         1 0.00000E+00 0.00000E+00 0.00000E+00
 -1         2 1.00000E-03-2.00000E-03-9.50000E-01
 -3
 9999
"""

DAT = """
 total force (fx,fy,fz) for set FIXED and time  0.1000000E+01

        5.354650E-11 -5.691158E-09  1.000000E+03
"""


def test_read_frd_fixed_width(tmp_path):
    p = tmp_path / "t.frd"
    p.write_text(FRD, encoding="latin-1")
    r = read_frd(p)
    assert list(r["nodes"]) == [1, 2]
    assert np.allclose(r["coords"][1], [200.0, 10.0, -5.0])  # adjacent fields, no space
    assert np.allclose(r["DISP"]["D3"], [0.0, -0.95])
    assert np.allclose(r["DISP"]["D2"], [0.0, -2e-3])


def test_read_dat_totals(tmp_path):
    p = tmp_path / "t.dat"
    p.write_text(DAT, encoding="latin-1")
    assert read_dat_total_forces(p)["FIXED"] == pytest.approx((5.35465e-11, -5.691158e-09, 1000.0))


try:
    from studies.cantilever import find_freecadcmd
    find_freecadcmd()
    HAVE_FREECAD = True
except Exception:
    HAVE_FREECAD = False


@pytest.mark.skipif(not HAVE_FREECAD, reason="FreeCAD not installed")
def test_cantilever_pipeline_tet10(tmp_path):
    from harness.run import run_case
    from harness.runio import read_json
    from harness.verify import verify_run

    text = Path("cases/cantilever_tet10.toml").read_text(encoding="utf-8").replace(
        "values = [8.0, 5.0, 3.125, 1.953125]", "values = [10.0, 8.0, 6.4]")
    case = tmp_path / "c.toml"
    case.write_text(text, encoding="utf-8")
    run_dir = run_case(case, runs_root=tmp_path / "runs")
    manifest = read_json(run_dir / "manifest.json")
    assert manifest["status"] == "completed"
    pt = manifest["points"][0]
    assert (run_dir / "points" / pt["label"] / "solver" / "cantilever.FCStd").exists()
    summary = verify_run(run_dir)
    by_id = {c["id"]: c for c in summary["points"][0]["checks"]}
    assert by_id["equilibrium"]["status"] == "PASS"
    assert by_id["tip_deflection_reference"]["status"] == "PASS"
    assert {c["id"] for c in summary["run_checks"]} == {
        "discretization_tip_deflection_mm", "discretization_root_bending_stress_MPa"}

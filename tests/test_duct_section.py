"""Study 11 part 2: the cross-section solver against its limits."""
import pytest

from models.thermal import duct_section as D
from studies.duct_section import frect_exact


def test_parallel_plate_limit_is_17_over_70():
    r = D.solve(1.0, 20.0, bc="H2", side="symmetry", ny=40)
    assert r["wall_peak_excess"] == pytest.approx(17 / 70, rel=2e-4)
    assert r["fRe"] == pytest.approx(24.0, rel=1e-3)


def test_rectangular_duct_friction_against_the_exact_series():
    for W in (4.0, 20.0):
        assert D.solve(1.0, W, bc="H1", ny=40)["fRe"] == pytest.approx(frect_exact(1.0, W), rel=1e-3)


def test_four_wall_nusselt_against_incropera():
    assert D.solve(1.0, 4.0, bc="H1_4", ny=40)["Nu"] == pytest.approx(5.33, abs=0.005)
    assert D.solve(1.0, 8.0, bc="H1_4", ny=40)["Nu"] == pytest.approx(6.49, abs=0.005)


def test_plate_reproduces_both_bounds():
    h2 = D.solve(1.0, 20.0, bc="H2", ny=20)["wall_peak_excess"]
    h1 = D.solve(1.0, 20.0, bc="H1", ny=20)["wall_peak_excess"]
    assert D.solve(1.0, 20.0, bc="plate", plate_conductance_rel=0.0, ny=20)["wall_peak_excess"] == pytest.approx(h2, rel=1e-9)
    assert D.solve(1.0, 20.0, bc="plate", plate_conductance_rel=1e7, ny=20)["wall_peak_excess"] == pytest.approx(h1, rel=1e-5)


def test_exact_series_limits():
    assert frect_exact(1.0, 1e6) == pytest.approx(24.0, rel=1e-5)        # parallel plates
    assert frect_exact(1.0, 1.0) == pytest.approx(14.227, abs=5e-4)     # square duct

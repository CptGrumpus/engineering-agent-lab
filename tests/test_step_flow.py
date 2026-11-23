"""Study 19 part 2 helpers: mesh grading, reattachment crossing, boundary-layer integrals."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from studies.step_flow import boundary_layer, crossings_up

_spec = importlib.util.spec_from_file_location(
    "step_model", Path(__file__).resolve().parent.parent / "models" / "cfd" / "step_openfoam.py")
W = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(W)


@pytest.mark.parametrize("length,n,first", [(0.9, 200, 3e-4), (0.05, 60, 8e-6), (1.0, 10, 0.2)])
def test_growth_fills_the_length(length, n, first):
    g = W.growth_for(length, n, first)
    assert first * (g ** n - 1) / (g - 1) == pytest.approx(length, rel=1e-9)


def test_crossings_up_finds_the_reattachment():
    x = np.linspace(0, 10, 101)
    cf = np.where(x < 6.3, -1.0, 1.0) * np.abs(x - 6.3) + 0.0
    cf[:5] = 0.5  # a small corner eddy near the step: positive, then negative again
    ups = crossings_up(x, cf)
    assert ups[-1] == pytest.approx(6.3, abs=1e-9)


def test_boundary_layer_integrals_of_a_linear_profile():
    # u = U y / d up to d, then U: theta = d / 6, delta* = d / 2 (exact)
    d, U = 0.02, 40.0
    y = np.linspace(1e-5, 0.05, 5001)
    u = np.minimum(U * y / d, U)
    bl = boundary_layer(y, u, 0.0)
    assert bl["theta"] == pytest.approx(d / 6, rel=2e-3)
    assert bl["delta_star"] == pytest.approx(d / 2, rel=2e-3)
    assert bl["delta99"] == pytest.approx(0.99 * d, rel=2e-3)

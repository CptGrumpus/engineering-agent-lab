"""Graetz thermal-entry reference used by the heated coolant channel study."""

import numpy as np
import pytest

from validation import graetz

PR = dict(H=1e-3, U=0.1, rho=997.0, cp=4180.0, k=0.607, q=30000.0, T_in=25.0)


def test_far_downstream_nusselt_is_the_exact_fully_developed_value():
    r = graetz.thermal_entry([1.0], **PR)                       # x* = 0.36, long past the entry length
    assert r["Nu"][0] == pytest.approx(140 / 17, rel=1e-6)


def test_bulk_temperature_obeys_the_energy_balance_exactly():
    x = np.array([0.001, 0.02, 0.05])
    r = graetz.thermal_entry(x, **PR)
    assert np.allclose(r["T_bulk"], graetz.bulk_temperature(x, 25.0, 30000.0, 1e-3, 0.1, 997.0, 4180.0), atol=1e-10)


def test_entry_region_has_higher_heat_transfer_and_the_grid_is_converged():
    x = np.array([0.001, 0.01, 0.05])
    a = graetz.thermal_entry(x, n_cells=200, **PR)
    b = graetz.thermal_entry(x, n_cells=400, **PR)
    assert np.all(np.diff(b["Nu"]) < 0) and b["Nu"][-1] > 140 / 17     # still developing at 50 mm
    assert np.max(np.abs(a["T_wall"] - b["T_wall"])) < 2e-3                # K


def test_wall_temperature_rise_is_linear_in_heat_flux():
    a = graetz.thermal_entry([0.05], **PR)
    b = graetz.thermal_entry([0.05], **(PR | {"q": 15000.0}))
    assert (b["T_wall"][0] - 25) == pytest.approx((a["T_wall"][0] - 25) / 2, rel=1e-12)

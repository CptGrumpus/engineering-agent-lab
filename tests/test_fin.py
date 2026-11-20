"""Heat-sink fin: 1D fin reference, deck writer, and a small CalculiX end-to-end run."""

from __future__ import annotations

import math
import shutil

import numpy as np
import pytest
from scipy.integrate import quad

from validation import fin_conduction as ref

NOMINAL = {"thickness_mm": 2.0, "width_mm": 20.0, "length_mm": 40.0,
           "conductivity_W_per_mK": 167.0, "htc_W_per_m2K": 25.0,
           "base_temperature_C": 80.0, "air_temperature_C": 25.0, "element_size_mm": 1.0}


# ----------------------------------------------------------------- reference

def test_reference_hand_values():
    # m L and tip ratio by hand: m = sqrt(25 * 0.044 / (167 * 4e-5)) = 12.832 1/m
    assert ref.fin_parameter(NOMINAL) == pytest.approx(12.8326, rel=1e-4)
    assert ref.tip_temperature_C(NOMINAL) == pytest.approx(73.207, abs=1e-3)
    assert ref.biot(NOMINAL) == pytest.approx(25 * 1e-3 / 167)


def test_reference_base_and_long_fin_limits():
    assert ref.temperature_C(NOMINAL, 0.0) == pytest.approx(80.0)
    long_fin = NOMINAL | {"length_mm": 2000.0}
    t, w = 2e-3, 20e-3
    q_inf = math.sqrt(25 * 2 * (w + t) * 167 * w * t) * 55
    assert ref.heat_flow_W(long_fin) == pytest.approx(q_inf, rel=1e-9)
    assert ref.tip_temperature_C(long_fin) == pytest.approx(25.0, abs=1e-6)


def test_reference_energy_balance_and_fourier():
    """q_f = convective loss along the sides + tip = -k A dtheta/dx at the base."""
    t, w, L, k, h = 2e-3, 20e-3, 40e-3, 167.0, 25.0
    side, _ = quad(lambda x: h * 2 * (w + t) * (ref.temperature_C(NOMINAL, x) - 25.0), 0, L)
    tip = h * w * t * (ref.tip_temperature_C(NOMINAL) - 25.0)
    assert ref.heat_flow_W(NOMINAL) == pytest.approx(side + tip, rel=1e-10)
    dx = 1e-7
    grad = (ref.temperature_C(NOMINAL, dx) - ref.temperature_C(NOMINAL, -dx)) / (2 * dx)
    assert ref.heat_flow_W(NOMINAL) == pytest.approx(-k * w * t * grad, rel=1e-6)


def test_reference_breakeven_and_efficiency():
    h_be = ref.breakeven_htc(NOMINAL, 60.0)
    assert ref.tip_temperature_C(NOMINAL | {"htc_W_per_m2K": h_be}) == pytest.approx(60.0, abs=1e-8)
    assert 90 < h_be < 100
    eta = ref.fin_efficiency(NOMINAL)
    assert 0.9 < eta < 1.0
    assert ref.fin_efficiency(NOMINAL | {"conductivity_W_per_mK": 1e9}) == pytest.approx(1, abs=1e-5)


# ----------------------------------------------------------------- model / study

def test_deck_writer_counts_and_faces():
    from models.thermal import fin_ccx as model

    mesh = model.mesh_divisions(NOMINAL)
    assert mesh == (2, 20, 40)
    deck = model.write_deck(NOMINAL)
    assert "np.float64" not in deck
    assert "*HEAT TRANSFER, STEADY STATE" in deck
    nx, ny, nz = mesh
    n_nodes = sum(1 for ln in deck.split("*ELEMENT")[0].splitlines()[3:] if ln[:1].isdigit())
    assert n_nodes == (nx + 1) * (ny + 1) * (nz + 1)
    # every exposed face appears once in the film loads; the base face has none
    films = [ln for ln in deck.splitlines() if ln.startswith("E") and ", F" in ln]
    assert {f.split(",")[1].strip() for f in films} == {"F2", "F3", "F4", "F5", "F6"}


def test_face_integration_of_uniform_field():
    """Convective loss of a uniform 1 K excess = h x exposed area."""
    from studies.fin import convective_loss_W

    p = NOMINAL | {"element_size_mm": 2.0}
    t, w, L = 2.0, 20.0, 40.0
    xs, ys, zs = np.linspace(0, t, 2), np.linspace(0, w, 11), np.linspace(0, L, 21)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    coords = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()]) * 1e-3
    temps = np.full(len(coords), 26.0)
    area = (2 * (w + t) * L + w * t) * 1e-6
    assert convective_loss_W(coords, temps, p) == pytest.approx(25.0 * area, rel=1e-12)


def test_fin_end_to_end(tmp_path):
    from studies.fin import find_ccx

    try:
        find_ccx()
    except RuntimeError:
        pytest.skip("CalculiX (ccx) not installed")
    from harness.report import build_report
    from harness.run import run_case
    from harness.verify import verify_run

    case = tmp_path / "fin.toml"
    text = open("cases/fin_mesh.toml", encoding="utf-8").read()
    text = text.replace("values = [2.0, 1.0, 0.5, 0.25]", "values = [2.0]")
    case.write_text(text, encoding="utf-8")
    run_dir = run_case(case, runs_root=tmp_path / "runs")
    summary = verify_run(run_dir)
    point = summary["points"][0]
    assert point["status"] == "PASS", point
    # the single-level run cannot do a GCI: run-level check fails by design
    assert summary["status"] == "FAIL"
    build_report(run_dir)


def test_missing_tip_film_is_caught():
    """Negative test: a deck without convection on the tip face fails the energy balance."""
    from studies.fin import STUDY, CalculiXFin, find_ccx

    try:
        find_ccx()
    except RuntimeError:
        pytest.skip("CalculiX (ccx) not installed")
    backend = CalculiXFin()
    backend.prepare()
    good = backend.model.write_deck
    backend.model.write_deck = lambda p: "\n".join(
        ln for ln in good(p).splitlines() if not ln.startswith("ETIP, F2"))
    p = NOMINAL | {"element_size_mm": 2.0}
    res = backend.solve(p, {})
    shutil.rmtree(res["cleanup"], ignore_errors=True)
    assert res["success"]
    m = STUDY.compute_metrics(res["series"], p, {}, res["outputs"])
    rel = abs(m["base_heat_flow_W"] - res["outputs"]["convective_loss_W"]) / res["outputs"]["convective_loss_W"]
    assert rel > 1e-2  # tolerance in the cases is 1e-4

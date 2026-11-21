"""Turek-Hron flag (study 6, solid stage): the elastica reference, the mesh, the clamp load share,
the last-period analysis, and one small end-to-end CalculiX run."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from studies.flag_csm import band_deviation, clamp_load_share, last_period
from validation import elastica

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("flag_ccx_t", ROOT / "models/fea/flag_ccx.py")
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)

CSM1 = dict(density_kg_per_m3=1000.0, shear_modulus_Pa=0.5e6, poisson_ratio=0.4, gravity_m_per_s2=2.0,
            flag_length_m=0.35, flag_height_m=0.02, cylinder_radius_m=0.05, element_size_mm=5.0,
            benchmark_ux_A_mm=-7.18767, benchmark_uy_A_mm=-66.1023)


def test_elastica_tends_to_linear_beam_theory_for_a_small_load():
    r = elastica.elastica_tip(1e-6, 0.35, 1.0)
    lin = elastica.linear_tip(1e-6, 0.35, 1.0)
    assert r["uy"] == pytest.approx(lin["uy"], rel=1e-6)
    assert r["slope"] == pytest.approx(lin["slope"], rel=1e-6)
    assert abs(r["ux"]) < 1e-9 * abs(r["uy"]) * 1e3          # second order


def test_elastica_is_inextensible_and_stiffens_under_large_load():
    q, L, EI = 40.0, 0.35, 1.1111
    r = elastica.elastica_tip(q, L, EI)
    arc = np.sum(np.hypot(np.diff(r["x"]), np.diff(r["y"])))
    assert arc == pytest.approx(L, rel=1e-6)
    assert abs(r["uy"]) < abs(elastica.linear_tip(q, L, EI)["uy"])     # large rotation shortens the lever


def test_elastica_matches_turek_hron_only_in_plane_strain():
    # the benchmark does not say; the elastica decides it (plane stress misses by 17 %)
    h, nu, E = 0.02, 0.4, 1.4e6
    q = 1000 * 2.0 * h
    strain = elastica.elastica_tip(q, 0.35, elastica.plane_strain_modulus(E, nu) * h**3 / 12)["uy"]
    stress = elastica.elastica_tip(q, 0.35, E * h**3 / 12)["uy"]
    assert strain == pytest.approx(-66.1023e-3, rel=0.01)
    assert abs(stress / -66.1023e-3 - 1) > 0.15


def test_cantilever_frequency_textbook_root():
    # f1 = 1.8751^2 / (2 pi L^2) sqrt(EI / m)
    f = elastica.cantilever_frequencies(1.0, 1.0, 1.0, 1)[0]
    assert f == pytest.approx(1.8751040687**2 / (2 * np.pi), rel=1e-9)


def test_mesh_root_lies_on_the_cylinder_and_point_a_is_a_node():
    m = F.FlagMesh(CSM1)
    assert m.x_end == pytest.approx(600.0)
    for j in range(m.ny + 1):
        x, y = m.xy(0, j)
        assert np.hypot(x - 200.0, y - 200.0) == pytest.approx(50.0, rel=1e-12)
    assert m.xy(m.nx, m.ny // 2) == pytest.approx((600.0, 200.0))
    assert m.point_a() == m.nid(m.nx, m.ny // 2, 0)


def test_clamp_load_share_is_half_the_first_column():
    m = F.FlagMesh(CSM1)
    share, area = clamp_load_share(m)
    assert area == pytest.approx(m.area_mm2(), rel=1e-12)
    # first column has 1/nx of the area (to within the arc's chord) and gives half to its left nodes
    assert share == pytest.approx(0.5 / m.nx, rel=0.01)


def test_last_period_reads_mean_amplitude_frequency_like_the_benchmark():
    t = np.linspace(0, 6, 6001)
    f = 1.1
    uy = -64.0 + 64.0 * np.cos(2 * np.pi * f * t)        # starts at 0, swings to -128
    ux = -14.0 + 14.0 * np.cos(2 * np.pi * f * t)
    lp = last_period(t, ux, uy)
    assert lp["frequency_Hz"] == pytest.approx(f, rel=1e-6)
    assert lp["uy_mean_mm"] == pytest.approx(-64.0, abs=1e-6)
    assert lp["uy_amplitude_mm"] == pytest.approx(64.0, abs=1e-6)
    assert lp["ux_mean_mm"] == pytest.approx(-14.0, abs=1e-6)
    assert lp["period_spread"] < 1e-6 and lp["trough_depth_spread"] < 1e-9


def test_band_deviation():
    assert band_deviation(-64.0, (-64.766, -63.607)) == 0.0
    assert band_deviation(1.09, (1.0956, 1.0995)) == pytest.approx(100 * 0.0056 / 1.0956)
    assert band_deviation(-65.0, (-64.766, -63.607)) == pytest.approx(100 * 0.234 / 64.766)


def test_static_flag_end_to_end(tmp_path):
    from studies.fin import find_ccx
    try:
        find_ccx()
    except Exception:
        pytest.skip("CalculiX not installed")
    from studies.flag_csm import STUDY, CalculiXFlag
    b = CalculiXFlag()
    b.prepare()
    params = dict(CSM1, element_size_mm=10.0)
    res = b.solve(params, {"increments": 4})
    assert res["success"], res["message"]
    m = STUDY.compute_metrics(res["series"], params, {}, res["outputs"])
    assert m["uy_A_mm"] == pytest.approx(-66.1, rel=0.01)
    out = res["outputs"]
    assert out["reaction_y_N"][-1] == pytest.approx(out["weight_N"] * (1 - out["clamp_load_share"]), rel=1e-6)


def test_last_period_ignores_a_higher_mode_riding_on_the_swing():
    # a sudden release also excites mode 2; a local-extremum search read 1.71 Hz for this signal
    t = np.linspace(0, 6, 48001)
    uy = -0.0347 + 0.0347 * np.cos(2 * np.pi * 1.0723 * t) + 0.002 * np.cos(2 * np.pi * 6.6 * t)
    lp = last_period(t, 0 * uy, uy)
    assert lp["mean_frequency_Hz"] == pytest.approx(1.0723, rel=2e-3)
    assert lp["periods_seen"] >= 5

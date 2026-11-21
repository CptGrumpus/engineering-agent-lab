"""Cold-plate thermal chain: the three independent references, the stress extrapolation, and the
case-writer helpers the coupling loop relies on."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from harness.calculix import HEX8_EXTRAPOLATION, hex8_nodal_stress
from validation import graetz
from validation import plate_conduction as pc
from validation import thermal_stress as ts

ROOT = Path(__file__).resolve().parent.parent
PR = dict(H=1e-3, U=0.1, rho=997.0, cp=4180.0, k=0.607, T_in=25.0)


def _load(rel):
    spec = importlib.util.spec_from_file_location(Path(rel).stem + "_t", ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- CFD-stage reference

def test_flux_profile_reference_reproduces_the_uniform_flux_solution():
    xe = np.linspace(0.0, 0.05, 401)
    r = graetz.thermal_entry_profile(xe, np.full(400, 30000.0), **PR)
    ref = graetz.thermal_entry(r["x"][[5, 100, 399]], q=30000.0, **PR)
    assert np.allclose(r["T_wall"][[5, 100, 399]], ref["T_wall"], atol=1e-9)
    assert np.allclose(r["T_bulk"][[5, 100, 399]], ref["T_bulk"], atol=1e-9)


def test_flux_profile_reference_closes_the_energy_balance_for_any_profile():
    xe = np.linspace(0.0, 0.06, 241)
    q = 30000.0 * (1 + 0.8 * np.sin(np.linspace(0, 7, 240)))
    r = graetz.thermal_entry_profile(xe, q, **PR)
    heat = 2 * np.sum(q * np.diff(xe))                               # both walls, per unit depth
    rise_end = heat / (PR["rho"] * PR["cp"] * PR["U"] * PR["H"])
    # bulk at the last segment centre misses half of the last segment's heat
    half = 2 * q[-1] * np.diff(xe)[-1] / 2 / (PR["rho"] * PR["cp"] * PR["U"] * PR["H"])
    assert r["T_bulk"][-1] - 25.0 == pytest.approx(rise_end - half, rel=1e-9)


def test_unheated_entry_leaves_the_fluid_at_inlet_temperature():
    xe = np.linspace(0.0, 0.01, 81)
    q = np.where(np.arange(80) < 40, 0.0, 30000.0)
    r = graetz.thermal_entry_profile(xe, q, **PR)
    assert np.allclose(r["T_wall"][:40], 25.0, atol=1e-12)


# ---------------------------------------------------------------- plate-stage reference

def test_plate_series_reduces_to_the_slab_for_uniform_data():
    L, t, k, h = 60.0, 3.0, 0.167, 2.5e-3
    e = np.linspace(0, L, 61)
    x = np.linspace(0, L, 9)
    for y in (0.0, 1.0, 3.0):
        T = pc.temperature(x, np.full_like(x, y), L=L, t=t, k=k, h=h, q_edges=e, q_values=np.full(60, 0.03),
                           r_edges=e, r_values=np.full(60, 30.0), n_terms=2000)
        assert np.allclose(T, 30 + 0.03 / h + 0.03 * y / k, atol=1e-10)


def test_plate_series_converges_and_conserves_heat():
    L, t, k, h = 60.0, 3.0, 0.167, 2.5e-3
    e = np.linspace(0, L, 481)
    q = np.where((e[:-1] >= 5 - 1e-9) & (e[1:] <= 55 + 1e-9), 0.03, 0.0)
    r = 25 + 7 * (e[:-1] + e[1:]) / 2 / L
    # wetted temperature at every segment's two Gauss points: exact film integral per segment
    g = np.array([-1, 1]) / np.sqrt(3)
    xm, dx = (e[:-1] + e[1:]) / 2, np.diff(e)
    xg = (xm[:, None] + g[None, :] * dx[:, None] / 2).ravel()
    T1 = pc.temperature(xg, np.zeros_like(xg), L=L, t=t, k=k, h=h, q_edges=e, q_values=q,
                        r_edges=e, r_values=r, n_terms=20000)
    T2 = pc.temperature(xg, np.zeros_like(xg), L=L, t=t, k=k, h=h, q_edges=e, q_values=q,
                        r_edges=e, r_values=r, n_terms=40000)
    assert np.max(np.abs(T1 - T2)) < 1e-6
    film = np.sum(h * (T1.reshape(-1, 2).mean(axis=1) - r) * dx)
    assert film == pytest.approx(np.sum(q * dx), rel=1e-5)


# ---------------------------------------------------------------- stress-stage reference

def test_uniform_rise_gives_the_exact_restrained_stress():
    x, y = np.linspace(0, 60, 61), np.linspace(1, 4, 13)
    r = ts.clamped_strip(x, y, np.full((61, 13), 20.0), E=68900, nu=0.33, alpha=23.6e-6)
    exact = ts.uniform_restrained_stress(68900, 0.33, 23.6e-6, 20.0)
    assert np.allclose(r["sigma_x"], exact, rtol=1e-12) and np.allclose(r["sigma_z"], exact, rtol=1e-12)


def test_linear_gradient_in_a_clamped_strip_is_fully_restrained():
    # clamped ends stop the bending too, so every fibre carries -E alpha dT / (1 - nu)
    x, y = np.linspace(0, 60, 31), np.linspace(1, 4, 7)
    dT = np.repeat((10 + 2 * (y - 1))[None, :], 31, axis=0)
    r = ts.clamped_strip(x, y, dT, E=68900, nu=0.33, alpha=23.6e-6)
    assert np.allclose(r["sigma_x"], -68900 * 23.6e-6 * dT / (1 - 0.33), rtol=1e-10)


def test_axial_force_is_constant_and_balances_the_mean_rise():
    x, y = np.linspace(0, 60, 121), np.linspace(1, 4, 13)
    dT = 15 + 10 * np.sin(x / 9)[:, None] + 0 * y[None, :]
    r = ts.clamped_strip(x, y, dT, E=68900, nu=0.33, alpha=23.6e-6)
    N_sec = np.trapezoid(r["sigma_x"], y, axis=1)
    assert np.allclose(N_sec, r["N"], rtol=1e-10)


def test_buckling_stress_formula():
    assert ts.clamped_strip_buckling_stress(68900, 0.33, 3.0, 60.0) == pytest.approx(
        4 * np.pi**2 * 68900 / (1 - 0.33**2) * (3.0**3 / 12) / (3.0 * 60.0**2))


# ---------------------------------------------------------------- stress extrapolation

def test_hex8_extrapolation_is_exact_for_linear_fields():
    assert np.allclose(HEX8_EXTRAPOLATION.sum(axis=1), 1.0, atol=1e-14)
    gp = np.array([(sx, sy, sz) for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)]) / np.sqrt(3)
    nodes = np.array([(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
                      (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)], float)
    f = lambda p: 3 + 2 * p[:, 0] - p[:, 1] + 0.5 * p[:, 2]
    assert np.allclose(HEX8_EXTRAPOLATION @ f(gp), f(nodes), atol=1e-12)


def test_nodal_stress_averages_shared_nodes():
    conn = {1: [1, 2, 3, 4, 5, 6, 7, 8], 2: [2, 9, 10, 3, 6, 11, 12, 7]}
    ip = {1: np.full((8, 6), 10.0), 2: np.full((8, 6), 20.0)}
    s = hex8_nodal_stress(ip, conn)
    assert s[1][0] == pytest.approx(10.0) and s[2][0] == pytest.approx(15.0) and s[9][0] == pytest.approx(20.0)


# ---------------------------------------------------------------- case writers

P = dict(gap_mm=1.0, footprint_length_mm=50.0, entry_length_mm=5.0, exit_length_mm=5.0, unplated_length_mm=5.0,
         cells_across_gap=20, cell_aspect_ratio=5.0)


def test_cfd_faces_and_plate_mask():
    w = _load("models/cfd/cold_plate_openfoam.py")
    assert w.block_counts(P) == [(20, 20), (20, 20), (200, 20), (20, 20), (20, 20)]
    fe = w.face_edges_mm(P)
    assert fe[0] == -10.0 and fe[-1] == 60.0 and len(fe) == 281
    pm = w.plate_faces(P)
    assert pm.sum() == 240 and not pm[:20].any() and not pm[-20:].any()


def test_wall_flux_and_end_time_are_rewritten_in_place(tmp_path):
    w = _load("models/cfd/cold_plate_openfoam.py")
    T = tmp_path / "T"
    T.write_text("""boundaryField
{
    inlet { type fixedValue; value uniform 25; }
    wall_bottom
    {
        type            fixedGradient;
        gradient        nonuniform List<scalar>
3
(
1 2 3
)
;
        value           uniform 25;
    }
    wall_top { type fixedGradient; gradient uniform 7; value uniform 25; }
}
""")
    w.set_wall_flux(T, [0.607, 1.214, 0.0], 0.607)
    text = T.read_text()
    assert text.count("gradient nonuniform List<scalar> 3 (1.0 2.0 0.0);") == 2
    assert "value           uniform 25;" in text
    cd = tmp_path / "controlDict"
    cd.write_text("solver functions;\nendTime         2500;\nwriteInterval 100;\n")
    w.set_end_time(cd, 3500)
    assert "endTime         3500;" in cd.read_text()


def test_solid_grid_matches_the_cfd_faces_and_numbers_c3d8_correctly():
    sw = _load("models/thermal/cold_plate_ccx.py")
    g = sw.Grid(np.linspace(-5, 55, 241), 1.0, 3.0, 12)
    assert g.nx == 240 and g.ny == 12 and g.y[0] == 1.0 and g.y[-1] == pytest.approx(4.0)
    c = g.connectivity()[g.eid(0, 0)]
    assert c == [g.nid(0, 0, 0), g.nid(1, 0, 0), g.nid(1, 1, 0), g.nid(0, 1, 0),
                 g.nid(0, 0, 1), g.nid(1, 0, 1), g.nid(1, 1, 1), g.nid(0, 1, 1)]
    with pytest.raises(ValueError):
        sw.Grid(np.linspace(0, 1, 3), 1.0, 3.0, 5)            # odd: no mid-thickness node line


def test_wall_reference_region_excludes_a_band_round_the_plate_edges():
    from studies.cold_plate import wall_reference_region

    edges = np.linspace(0.0, 70.0, 141)                       # 0.5 mm faces; plate from 5 to 65 mm
    xc = 0.5 * (edges[1:] + edges[:-1])
    q = np.where((xc > 5.0) & (xc < 65.0), 1e4, 0.0)
    mask, band = wall_reference_region(edges, q, 1.0, {})
    assert band == 0.0 and mask.all()                          # default: every face, as before
    mask, band = wall_reference_region(edges, q, 1.0, {"wall_edge_exclusion_gaps": 2})
    assert band == 2.0
    assert not mask[(np.abs(xc - 5.0) < 2.0) | (np.abs(xc - 65.0) < 2.0)].any()
    assert mask[(np.abs(xc - 5.0) > 2.0) & (np.abs(xc - 65.0) > 2.0)].all()

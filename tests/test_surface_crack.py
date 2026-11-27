"""Study 24 part 2 (surface crack): Newman-Raju, front geometry, energy integral, growth law, deck (no CalculiX)."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from studies.surface_crack import growth, ratio_function

spec = importlib.util.spec_from_file_location("sc", Path(__file__).resolve().parent.parent / "models/fea/surface_crack.py")
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)

P = {"thickness_mm": 10.0, "half_width_mm": 50.0, "sigma_max_MPa": 150.0, "stress_ratio": 0.1, "paris_C": 5.21e-13,
     "paris_m": 3.0, "dK_threshold": 63.0, "initial_depth_mm": 2.0, "initial_half_length_mm": 5.0,
     "end_depth_ratio": 0.8}


def test_newman_raju_semicircle_in_a_wide_thick_plate():
    # a/c = 1, a/t -> 0, c/b -> 0: M1 = 1.04, Q = 2.464; g = 1.1 at the surface
    F = lambda phi: sc.newman_raju_F(0.01, 0.01, 1000.0, 1e6, phi)  # noqa: E731
    assert F(np.pi / 2) == pytest.approx(1.04 / np.sqrt(2.464), rel=1e-6)
    assert F(0.0) == pytest.approx(1.04 * 1.1 / np.sqrt(2.464), rel=1e-6)


def test_newman_raju_detectable_flaw_by_hand():
    # a = 2, c = 5, t = 10, b = 50: M1 1.094, M2 0.94333, M3 -0.44573 (+14 0.6^24), Q 1.32325, fw 1.00123
    M3 = 0.5 - 1 / 1.05 + 14 * 0.6 ** 24
    base = 1.094 + 0.89 / 0.6 * 0.04 - 0.54 * 0.04 + M3 * 0.0016
    Q = 1 + 1.464 * 0.4 ** 1.65
    fw = (1 / np.cos(np.pi * 5 / 100 * np.sqrt(0.2))) ** 0.5
    assert sc.newman_raju_F(2, 5, 10, 50, np.pi / 2) == pytest.approx(base * fw / np.sqrt(Q), rel=1e-12)
    assert sc.newman_raju_F(2, 5, 10, 50, 0.0) == pytest.approx(base * 1.114 * 0.4 ** 0.5 * fw / np.sqrt(Q), rel=1e-12)


def test_front_coords_recovers_angle_and_distance():
    a, c = 2.0, 5.0
    phi = np.radians([3, 20, 45, 70, 89])
    x, z = c * np.cos(phi), a * np.sin(phi)
    n = np.column_stack([a * np.cos(phi), c * np.sin(phi)])        # outward normal of the ellipse
    n /= np.linalg.norm(n, axis=1)[:, None]
    r = 0.07
    ph, rr, s = sc.front_coords(x - r * n[:, 0], z - r * n[:, 1], a, c)   # points behind the front
    assert ph == pytest.approx(phi, abs=1e-9)
    assert rr == pytest.approx(r, abs=1e-9)
    assert sc.arc_length(np.pi / 2, 3.0, 3.0) == pytest.approx(3.0 * np.pi / 2, rel=1e-6)


def test_energy_integral_constant_K_on_a_quarter_circle():
    E, nu, K, a = 210000.0, 0.3, 400.0, 3.0
    st = np.linspace(0, 90, 19)
    expect = 0.5 * a * a * (np.pi / 2) * K ** 2 * (1 - nu ** 2) / E
    assert sc.energy_integral(st, np.full(19, K), a, a, E, nu) == pytest.approx(expect, rel=1e-12)


def test_growth_life_and_k_scaling():
    g = growth(P)
    assert g["a_end"] == pytest.approx(8.0, abs=1e-6)
    assert g["life"] == pytest.approx(133423, rel=2e-4)            # hand integration (scratch, RK45 rtol 1e-9)
    assert g["K_deep_a0"] / 31.6227766 == pytest.approx(11.707, abs=1e-3)
    # every Delta K on the path is above the threshold, so scaling K by s scales the life by s^-3
    g2 = growth(P, ratio_function([2, 8], [0.98, 0.98]))
    assert g2["life"] == pytest.approx(g["life"] / 0.98 ** 3, rel=1e-6)
    assert growth(P, method="LSODA")["life"] == pytest.approx(g["life"], rel=1e-5)


def test_deck_loads_and_crack_face(tmp_path):
    pytest.importorskip("gmsh")
    a, c = 2.0, 5.0
    sc.mesh(tmp_path / "mesh.inp", a=a, c=c, Wh=50, H=100, t=10, h_front=0.4, h_far=10.0, r_fine=1.6)
    info = sc.write_deck(tmp_path / "mesh.inp", tmp_path / "job.inp", a=a, c=c, Wh=50, H=100, t=10, sigma=150.0,
                         E=210000.0, nu=0.3)
    assert info["area_check"] == pytest.approx(1.0, abs=1e-12)
    xyz = np.array(list(info["crack_xyz"].values()))
    assert np.all(np.abs(xyz[:, 1]) < 1e-9)
    assert np.all((xyz[:, 0] / c) ** 2 + (xyz[:, 2] / a) ** 2 < 1)
    assert info["crack_nodes"] > 20 and info["ligament_nodes"] > 100
    assert "np.float" not in (tmp_path / "job.inp").read_text()


def test_weighted_energy_integrals_add_up():
    a, c, E, nu = 2.0, 5.0, 210000.0, 0.3
    st = np.linspace(0, 90, 19)
    K = 150 * np.sqrt(np.pi * a) * sc.newman_raju_F(a, c, 10, 50, np.radians(st))
    total = sc.energy_integral(st, K, a, c, E, nu)
    parts = sc.energy_integral(st, K, a, c, E, nu, weight="depth") + sc.energy_integral(st, K, a, c, E, nu, weight="surface")
    assert parts == pytest.approx(total, rel=1e-12)
    # constant K on a quarter circle: the depth and surface weights each take half
    Kc = np.full(19, 400.0)
    assert sc.energy_integral(st, Kc, 3, 3, E, nu, weight="depth") == pytest.approx(
        0.5 * sc.energy_integral(st, Kc, 3, 3, E, nu), rel=1e-3)

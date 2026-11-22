"""Turek-Hron FSI: the case writer (units, sets, coupling config) and the log parsers."""

import importlib.util
import re
from pathlib import Path

import numpy as np
import pytest

from studies.turek_hron_fsi import STUDY, read_forces, read_iterations, read_watchpoint

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("fsi_t", ROOT / "models/fsi/turek_hron_fsi.py")
W = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(W)

FSI1 = dict(solid_density_kg_per_m3=1000.0, shear_modulus_Pa=0.5e6, poisson_ratio=0.4, fluid_density_kg_per_m3=1000.0,
            kinematic_viscosity_m2_per_s=1e-3, mean_velocity_m_per_s=0.2, fluid_cell_size_m=0.005,
            solid_element_size_mm=5.0, time_step_s=0.005, end_time_s=1.0, benchmark_ux_A_m=2.270493e-05,
            benchmark_uy_A_m=8.208773e-04, benchmark_drag_N_per_m=14.29426, benchmark_lift_N_per_m=0.7637460)


@pytest.fixture(scope="module")
def case(tmp_path_factory):
    root = tmp_path_factory.mktemp("fsi")
    info = W.write_case(FSI1, {"solid_alpha": -0.3}, root)
    return root, info


def test_solid_is_si_and_as_thick_as_the_fluid_is_deep(case):
    root, _ = case
    text = (root / "solid/flag.inp").read_text(encoding="utf-8")
    nodes = re.search(r"\*NODE, NSET=Nall\n(.*?)\n\*ELEMENT", text, re.S).group(1).splitlines()
    xyz = np.array([[float(v) for v in ln.split(",")[1:]] for ln in nodes])
    assert xyz[:, 0].max() == pytest.approx(0.6) and xyz[:, 1].min() == pytest.approx(0.19)
    assert xyz[:, 2].max() == pytest.approx(W.DEPTH)                     # same depth as the fluid
    assert "1400000.0" in text.replace("1400000.0000000002", "1400000.0")  # E = 2 mu (1 + nu) in Pa
    assert "*DYNAMIC, ALPHA=-0.3" in text and "NLGEOM" in text


def test_wetted_set_excludes_the_clamped_root(case):
    root, _ = case
    text = (root / "solid/flag.inp").read_text(encoding="utf-8")

    def nset(name):
        body = re.search(rf"\*NSET, NSET={name}\n(.*?)\n\*", text, re.S).group(1)
        return {int(v) for v in re.findall(r"\d+", body)}
    assert nset("Nsurface") and not (nset("Nsurface") & nset("Nfix"))


def test_coupling_config_and_watch_point(case):
    root, _ = case
    x = (root / "precice-config.xml").read_text(encoding="utf-8")
    assert 'coordinate="0.6;0.2"' in x
    assert 'dimensions="2"' in x and "parallel-implicit" in x
    assert 'time-window-size value="0.005"' in x


def test_fluid_patches_split_cylinder_and_flag(case):
    root, _ = case
    geo = (root / "fluid/mesh.geo").read_text(encoding="utf-8")
    assert '"flag"' in geo and '"cylinder"' in geo
    pre = (root / "fluid/system/preciceDict").read_text(encoding="utf-8")
    assert "patches           (flag);" in pre
    u = (root / "fluid/0/U").read_text(encoding="utf-8")
    assert "codedFixedValue" in u and "cos(constant::mathematical::pi*t/T)" in u


def test_parsers(tmp_path):
    wp = tmp_path / "wp.log"
    wp.write_text("  Time  Coordinate0  Coordinate1  Displacement0  Displacement1  Force0  Force1\n"
                  " 0.0 0.6 0.2 0.0 0.0 0.0 0.0\n 0.005 0.6 0.2 1e-6 2e-5 3e-3 4e-3\n", encoding="utf-8")
    w = read_watchpoint(wp)
    assert w.shape == (2, 7) and w[-1, 4] == pytest.approx(2e-5)
    it = tmp_path / "it.log"
    it.write_text("TimeWindow  TotalIterations  Iterations  Convergence\n1 8 8 1\n2 12 4 1\n3 62 50 0\n", encoding="utf-8")
    a = read_iterations(it)
    assert int(np.sum(a[:, 3] < 0.5)) == 1


def test_metrics_and_deviations():
    s = {"t_s": [0, 1], "ux_A_m": [0, 2.3e-5], "uy_A_m": [0, 8.2e-4], "drag_N_per_m": [0, 14.3],
         "lift_N_per_m": [0, 0.76]}
    m = STUDY.compute_metrics(s, FSI1, {}, {})
    assert m["uy_A_deviation_pct"] == pytest.approx(100 * abs(8.2e-4 - 8.208773e-04) / 8.208773e-04)
    assert m["drag_deviation_pct"] == pytest.approx(100 * abs(14.3 - 14.29426) / 14.29426)


def test_read_forces_v2512_columns(tmp_path):
    # a real line from the FSI1 prototype's force.dat (OpenFOAM v2512): time, total, pressure, viscous
    f = tmp_path / "force.dat"
    header = "# Time total_x total_y total_z pressure_x pressure_y pressure_z viscous_x viscous_y viscous_z"
    line = ("20 1.4293411941e-01 7.6400687906e-03 3.2651933942e-16 7.4303797201e-02 7.4777669948e-03 "
            "7.8861320633e-21 6.8630322211e-02 1.6230179579e-04 3.2651145329e-16")
    f.write_text(header + chr(10) + line + chr(10), encoding="utf-8")
    F = read_forces(f)
    assert (F[-1, 1] + F[-1, 3]) / 0.01 == pytest.approx(14.293411941, rel=1e-9)   # drag = pressure + viscous = total
    assert (F[-1, 2] + F[-1, 4]) / 0.01 == pytest.approx(0.76400687906, rel=1e-9)

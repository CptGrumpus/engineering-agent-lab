"""Turek-Hron fluid stage: the forces parser, the domain area, the mesh script and the exact inflow."""

import importlib.util
import re
from pathlib import Path

import numpy as np
import pytest

from studies.turek_hron_cfd import STUDY, _domain_area, read_forces

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("turek_hron_t", ROOT / "models/cfd/turek_hron_openfoam.py")
W = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(W)

CFD1 = dict(mean_velocity_m_per_s=0.2, kinematic_viscosity_m2_per_s=1e-3, density_kg_per_m3=1000.0,
            flag_length_m=0.35, cell_size_m=0.005, benchmark_drag_N_per_m=14.2929, benchmark_lift_N_per_m=1.11905)
NUMERICS = dict(max_iterations=100, residual_p=1e-10, residual_U=1e-11, inlet_table_points=401)

FORCES_DAT = """# Forces
# CofR                : (2.000000e-01 2.000000e-01 0.000000e+00)
# Time                	forces(pressure viscous) moment(pressure viscous)
239                 	((7.256357891778e-02 1.057790834562e-02 -1.197801475274e-20) (6.936861811521e-02 4.240507097571e-04 -9.288405787826e-21)) ((-5.288954172811e-05 3.628178945889e-04 1.035092043350e-03) (-2.120253548785e-06 3.468430905760e-04 -8.699857737628e-06))
240                 	((7.256357891778e-02 1.057790834564e-02 -1.197801475272e-20) (6.936861811520e-02 4.240507097582e-04 -9.288405787828e-21)) ((-5.288954172818e-05 3.628178945889e-04 1.035092043351e-03) (-2.120253548791e-06 3.468430905760e-04 -8.699857737720e-06))
"""


def test_read_forces_takes_pressure_and_viscous_x_y(tmp_path):
    f = tmp_path / "forces.dat"
    f.write_text(FORCES_DAT, encoding="utf-8")
    F = read_forces(f)
    assert F.shape == (2, 5)
    assert F[-1, 0] == 240
    assert F[-1, 1] == pytest.approx(7.256357891778e-02) and F[-1, 2] == pytest.approx(1.057790834564e-02)
    assert F[-1, 3] == pytest.approx(6.936861811520e-02) and F[-1, 4] == pytest.approx(4.240507097582e-04)


def test_domain_area_is_channel_minus_disk_minus_flag():
    no_flag = _domain_area(dict(CFD1, flag_length_m=0.0))
    assert no_flag == pytest.approx(2.5 * 0.41 - np.pi * 0.05**2, rel=1e-12)
    # the flag adds its 0.35 x 0.02 m outside the disk, less the sliver of the disk it overlaps beyond x = 0.25
    y = 0.01
    sliver = 2 * (0.05 - np.sqrt(0.05**2 - y**2)) * y   # bounded above by the cap; the exact value is smaller
    flag_out = no_flag - _domain_area(CFD1)
    assert 0.35 * 0.02 < flag_out < 0.35 * 0.02 + sliver


def test_mesh_script_names_every_patch_and_puts_the_flag_end_at_0p6(tmp_path):
    geo = tmp_path / "mesh.geo"
    W.write_geo(CFD1, geo)
    text = geo.read_text(encoding="utf-8")
    for name in ("inlet", "outlet", "walls", "body", "frontAndBack", "fluid"):
        assert f'"{name}"' in text
    rect = re.search(r"Rectangle\(3\) = \{([^}]*)\}", text).group(1).split(",")
    x0, width = float(rect[0]), float(rect[3])
    assert x0 + width == pytest.approx(0.6)
    assert "Field[2].SizeMin = 0.005" in text            # the size is written in, not left to -setnumber
    W.write_geo(dict(CFD1, flag_length_m=0.0), geo)
    assert "Rectangle(3)" not in geo.read_text(encoding="utf-8")


def test_inlet_table_is_the_benchmark_parabola(tmp_path):
    W.write_case(CFD1, NUMERICS, tmp_path / "case")
    text = (tmp_path / "case/0/U").read_text(encoding="utf-8")
    assert "fixedProfile" in text and "laminarBL" not in text
    pts = [(float(y), float(u)) for y, u in re.findall(r"\(([-0-9.e]+) \(([-0-9.e]+) 0 0\)\)", text)]
    y, u = np.array(pts).T
    assert len(y) == 401 and y[0] == 0 and y[-1] == pytest.approx(0.41)
    assert np.max(u) == pytest.approx(1.5 * 0.2, rel=1e-12)
    assert np.allclose(u, 1.5 * 0.2 * 4 * y * (0.41 - y) / 0.41**2, rtol=0, atol=1e-15)
    assert np.trapezoid(u, y) / 0.41 == pytest.approx(0.2, rel=1e-5)   # mean velocity


def test_metrics_and_deviation():
    series = {"drag_N_per_m": np.array([14.0, 14.3]), "lift_N_per_m": np.array([1.0, 1.1])}
    m = STUDY.compute_metrics(series, CFD1, {}, {})
    assert m["drag_N_per_m"] == 14.3
    assert m["drag_deviation_pct"] == pytest.approx(100 * abs(14.3 - 14.2929) / 14.2929)
    assert STUDY.derive(CFD1)["reynolds_D"] == pytest.approx(20.0)

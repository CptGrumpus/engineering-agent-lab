"""Strut buckling: the column references and the .dat parsing that fooled the first smoke run."""

import numpy as np
import pytest

from studies.strut_buckling import buckling_modes, read_dat_blocks
from validation import column_buckling as cb

E, NU, SY, B, H = 68900.0, 0.33, 276.0, 25.0, 16.0


def test_shear_correction_vanishes_for_a_slender_column():
    assert cb.critical_load(E, NU, B, H, 5000.0) == pytest.approx(cb.euler_load(E, B, H, 5000.0), rel=1e-4)
    assert cb.critical_load(E, NU, B, H, 300.0) < cb.euler_load(E, B, H, 300.0)


def test_perry_robertson_root_satisfies_its_equation_and_tends_to_the_limits():
    L, e0 = 600.0, 0.6
    A, I, r = cb.section(B, H)
    P = cb.perry_robertson_load(E, SY, B, H, L, e0)
    s, sE = P / A, cb.euler_load(E, B, H, L) / A
    eta = e0 * (H / 2) / r**2
    assert s * (1 + eta / (1 - s / sE)) == pytest.approx(SY, rel=1e-10)
    assert cb.perry_robertson_load(E, SY, B, H, L, 1e-9) == pytest.approx(min(SY * A, sE * A), rel=1e-6)


def test_southwell_recovers_p_cr_and_the_bow_from_amplification_data():
    P = np.linspace(2000, 14000, 12)
    w = cb.amplified_deflection(P, 16000.0, 0.6)
    p_cr, e0 = cb.southwell(P, w, 0.6)
    assert p_cr == pytest.approx(16000.0, rel=1e-10) and e0 == pytest.approx(0.6, rel=1e-9)


def test_euler_range_boundary():
    # Euler stress = s_y / 2 at L / r = pi sqrt(2 E / s_y)
    r = cb.section(B, H)[2]
    L = np.pi * np.sqrt(2 * E / SY) * r
    assert cb.euler_range(E, SY, B, H, L * 1.001) and not cb.euler_range(E, SY, B, H, L * 0.999)
    assert cb.johnson_stress(E, SY, B, H, L) == pytest.approx(SY / 2, rel=1e-12)   # tangent at the boundary


BUCKLE_DAT = """
 displacements (vx,vy,vz) for set NAXIS and time  0.0000000E+00

         1  0.000000E+00  0.000000E+00  0.000000E+00
         2 -1.000000E-03  0.000000E+00  1.000000E-16

                    E I G E N V A L U E    N U M B E R     1


 displacements (vx,vy,vz) for set NAXIS and time  0.0000000E+00

         1  0.000000E+00  0.000000E+00  0.000000E+00
         2  0.000000E+00  0.000000E+00  1.000000E+00

                    E I G E N V A L U E    N U M B E R     2


 displacements (vx,vy,vz) for set NAXIS and time  0.0000000E+00

         1  0.000000E+00  0.000000E+00  0.000000E+00
         2  0.000000E+00  0.000000E+00 -2.000000E+00
"""


def test_mode_parser_skips_the_static_pre_buckling_block(tmp_path):
    f = tmp_path / "buckle.dat"
    f.write_text(BUCKLE_DAT)
    assert len(read_dat_blocks(f)) == 3                      # the trap: three blocks, two modes
    modes = buckling_modes(f)
    assert len(modes) == 2 and modes[0][1, 3] == 1.0 and modes[1][1, 3] == -2.0

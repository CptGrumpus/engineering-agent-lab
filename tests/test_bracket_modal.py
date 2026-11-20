from pathlib import Path

import numpy as np
import pytest

from validation import beam_vibration as bv

E, NU, RHO = 210000.0, 0.3, 7.85e-9


def test_timoshenko_solver_reaches_euler_bernoulli_for_a_slender_beam():
    # L/h = 300: shear and rotary inertia are negligible, so the 1D Timoshenko
    # model must reproduce the exact Euler-Bernoulli frequencies
    L, b, h = 1200.0, 25.0, 4.0
    A, I = b * h, b * h**3 / 12
    f, x, w = bv.timoshenko_modes(L, E, NU, I, A, RHO, n_modes=3)
    for n in (1, 2, 3):
        assert f[n - 1] == pytest.approx(bv.euler_bernoulli(n, L, E, I, RHO, A), rel=2e-4)
    # first-mode effective mass of a uniform cantilever is 0.6131 of its mass
    assert bv.effective_mass_fraction(x, w[0], RHO, A, L) == pytest.approx(0.6131, abs=2e-3)


def test_timoshenko_lowers_frequencies_of_a_stocky_beam():
    L, b, h = 150.0, 25.0, 8.0
    A, I = b * h, b * h**3 / 12
    f, _, _ = bv.timoshenko_modes(L, E, NU, I, A, RHO, n_modes=3)
    eb = [bv.euler_bernoulli(n, L, E, I, RHO, A) for n in (1, 2, 3)]
    assert all(fi < ei for fi, ei in zip(f, eb))
    assert f[0] / eb[0] > 0.99 and f[2] / eb[2] < 0.98   # higher modes feel shear more


def test_torsion_and_mac():
    assert bv.torsion_rect_J(10.0, 10.0) == pytest.approx(0.1406 * 10.0**4, rel=2e-3)  # square
    v = np.sin(np.linspace(0, 3, 50))
    assert bv.mac(v, 3 * v) == pytest.approx(1.0)
    assert bv.mac(v, np.cos(np.linspace(0, 3, 50))) < 0.9


def test_mode_classification_from_effective_mass():
    from studies.bracket_modal import classify
    total = np.array([1.0, 1.0, 1.0, 0.01, 1.7, 1.7])
    eff = np.array([[0, 0, 0.61, 0, 1.0, 0],      # flapwise
                    [0, 0.6, 0, 0, 0, 1.0],       # in-plane
                    [0, 0, 0, 0.008, 0, 0],       # torsion
                    [0.8, 0, 0, 0, 0, 0]])        # axial
    assert classify(eff, total) == ["flapwise", "in-plane", "torsion", "axial"]


def test_dat_frequency_parser(tmp_path):
    from harness.calculix import read_dat_frequency
    dat = tmp_path / "j.dat"
    dat.write_text("""
     E I G E N V A L U E   O U T P U T

 MODE NO    EIGENVALUE                       FREQUENCY
                                     REAL PART            IMAGINARY PART
                           (RAD/TIME)      (CYCLES/TIME     (RAD/TIME)

      1   0.3528621E+07   0.1878462E+04   0.2989666E+03   0.0000000E+00
      2   0.3288413E+08   0.5734468E+04   0.9126690E+03   0.0000000E+00

     E F F E C T I V E   M O D A L   M A S S

MODE NO.   X-COMPONENT     Y-COMPONENT     Z-COMPONENT     X-ROTATION      Y-ROTATION      Z-ROTATION

      1   0.0000000E+00   0.0000000E+00   0.1438789E-03   0.0000000E+00   0.1714380E+01   0.0000000E+00
      2   0.0000000E+00   0.1442299E-03   0.0000000E+00   0.0000000E+00   0.0000000E+00   0.1728072E+01
TOTAL     0.0000000E+00   0.1442299E-03   0.1438789E-03   0.0000000E+00   0.1714380E+01   0.1728072E+01

     T O T A L   E F F E C T I V E   M A S S

MODE NO.   X-COMPONENT     Y-COMPONENT     Z-COMPONENT     X-ROTATION      Y-ROTATION      Z-ROTATION

          0.2344281E-03   0.2344281E-03   0.2344281E-03   0.1346652E-01   0.1767501E+01   0.1778466E+01
""", encoding="latin-1")
    r = read_dat_frequency(dat)
    assert np.allclose(r["frequency_Hz"], [298.9666, 912.669])
    assert r["effective_mass"].shape == (2, 6) and r["effective_mass"][0, 2] == pytest.approx(1.438789e-4)
    assert r["total_effective_mass"][0] == pytest.approx(2.344281e-4)

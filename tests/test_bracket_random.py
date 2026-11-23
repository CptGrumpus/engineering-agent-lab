"""Study C (random vibration): the response and fatigue functions against closed forms."""

import math

import numpy as np
import pytest

from studies import bracket_random as R


def test_modal_coordinate_at_resonance_is_gamma_over_2_zeta_wn2():
    wn, g, z = 2 * math.pi * 262.0, 0.0112, 0.02
    q = R.modal_coords(np.array([wn]), np.array([g]), z, np.array([wn]))[0, 0]
    assert abs(q) == pytest.approx(g / (2 * z * wn ** 2), rel=1e-12)
    assert q.imag > 0                                    # -Gamma / (2 j zeta wn^2) = +j Gamma / (2 zeta wn^2)


def test_absolute_damping_adds_calculix_forcing():
    wn, g, z, w = 1000.0, 0.01, 0.05, 400.0
    qa = R.modal_coords(np.array([wn]), np.array([g]), z, np.array([w]), absolute_damping=True)[0, 0]
    q = R.modal_coords(np.array([wn]), np.array([g]), z, np.array([w]))[0, 0]
    assert qa - q == pytest.approx(2j * z * wn * g / w / (wn ** 2 - w ** 2 + 2j * z * wn * w), rel=1e-12)


def test_band_integral_of_one_mode_matches_miles():
    fn, z, S, pg = 262.0, 0.02, 0.04 * R.G ** 2, 1.5
    f = R.freq_grid(np.array([fn]), z, 1.0, 50000.0, n_log=4000, n_res=400)
    q = R.modal_coords(np.array([2 * math.pi * fn]), np.array([pg]), z, 2 * math.pi * f)[0]
    rms = math.sqrt(R.integrate(np.abs(q) ** 2 * S, f))
    assert rms == pytest.approx(R.miles_tip_rms(pg, fn, z, S), rel=2e-3)


def test_von_mises_mean_square_of_a_uniaxial_stress_is_its_mean_square():
    f = np.linspace(10, 100, 50)
    s = np.zeros((6, len(f)), complex)
    s[0] = (1 + 2j) * f / 100
    S = np.full_like(f, 3.0)
    assert R.vm_mean_square(s, S, f) == pytest.approx(R.integrate(np.abs(s[0]) ** 2 * S, f), rel=1e-12)
    s2 = np.zeros_like(s)
    s2[3] = s[0]                                          # pure shear: von Mises^2 = 3 tau^2
    assert R.vm_mean_square(s2, S, f) == pytest.approx(3 * R.integrate(np.abs(s[0]) ** 2 * S, f), rel=1e-12)


def test_ec3_curve_corners():
    c = 160.0
    dD, dL = c * 0.4 ** (1 / 3), c * 0.4 ** (1 / 3) * 0.05 ** 0.2
    assert dD / c == pytest.approx(0.737, abs=1e-3) and dL / c == pytest.approx(0.405, abs=1e-3)
    n = R.ec3_cycles(np.array([c, dD, dL * 1.0000001, dL * 0.99]), c)
    assert n[0] == pytest.approx(2e6) and n[1] == pytest.approx(5e6) and n[2] == pytest.approx(1e8, rel=1e-5)
    assert np.isinf(n[3])


def test_steinberg_in_the_slope_3_region():
    m0, m2 = 100.0 ** 2, 100.0 ** 2 * 300.0 ** 2          # sigma 100 MPa, zero crossings 300 Hz
    c, T = 160.0, 10.0
    d = R.steinberg_damage((m0, 0.0, m2, 0.0), T, c)
    want = sum(fr * 300.0 * T * (2 * k * 100.0) ** 3 / (2e6 * c ** 3) for k, fr in ((1, .683), (2, .271), (3, .0433)))
    assert d == pytest.approx(want, rel=1e-12)


def test_dirlik_density_integrates_to_one_and_is_near_rayleigh_for_a_narrow_band():
    f = np.linspace(250.0, 274.0, 2001)                   # narrow band around 262 Hz
    G = np.exp(-0.5 * ((f - 262.0) / 2.0) ** 2)
    m = R.spectral_moments(G, f)
    s = np.linspace(1e-9, 14 * math.sqrt(m[0]), 20000)
    p = R.dirlik_pdf(s, m)
    assert R.integrate(p, s) == pytest.approx(1.0, abs=2e-3)
    rayleigh = s / (4 * m[0]) * np.exp(-s ** 2 / (8 * m[0]))
    third = lambda d: R.integrate(s ** 3 * d, s)          # noqa: E731  the moment that drives slope-3 damage
    assert third(p) == pytest.approx(third(rayleigh), rel=0.03)


def test_dat_readers(tmp_path):
    dat = tmp_path / "job.dat"
    dat.write_text("""
                        S T E P       1


     P A R T I C I P A T I O N   F A C T O R S

MODE NO.   X-COMPONENT     Y-COMPONENT     Z-COMPONENT     X-ROTATION      Y-ROTATION      Z-ROTATION

      1  -0.2303193E-08  -0.1154702E-07   0.1122030E-01  -0.3320132E-06  -0.1224657E+01  -0.1250471E-05
      2   0.4012014E-07   0.1123484E-01  -0.2962257E-07   0.8745352E-07  -0.1712922E-06   0.1229684E+01

     E F F E C T I V E   M O D A L   M A S S

                        S T E P       2


 displacements (vx,vy,vz) for set TIP and time  0.1000000E+03

        57  1.0E-08 -2.0E-13  3.0E-06
 displacements (vx,vy,vz) for set TIP and time  0.1000000E+03

        57  4.0E-09 -5.0E-13  6.0E-08
 displacements (vx,vy,vz) for set TIP and time  0.2000000E+03

        57  7.0E-08 -8.0E-13  9.0E-06
 displacements (vx,vy,vz) for set TIP and time  0.2000000E+03

        57  1.1E-09 -1.2E-13  1.3E-08
""", encoding="latin-1")
    g = R.read_participation(dat)
    assert g.shape == (2, 6) and g[0, 2] == pytest.approx(0.0112203) and g[1, 5] == pytest.approx(1.229684)
    h = R.read_harmonic_tip(dat)
    assert len(h) == 1
    assert h[0]["f_Hz"].tolist() == [100.0, 200.0]
    assert h[0]["re"][1, 2] == pytest.approx(9e-6) and h[0]["im"][0, 2] == pytest.approx(6e-8)

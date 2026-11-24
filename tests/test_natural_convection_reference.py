"""Study 11 references: de Vahl Davis Table V as transcribed, two-surface radiation exchange limits."""

import math

import pytest

from validation import natural_convection as N


def test_table_v_transcription_and_trends():
    t = N.DE_VAHL_DAVIS
    assert [t[ra]["Nu"] for ra in (1e3, 1e4, 1e5, 1e6)] == [1.118, 2.243, 4.519, 8.800]
    assert [t[ra]["w_max"] for ra in (1e3, 1e4, 1e5, 1e6)] == [3.697, 19.617, 68.59, 219.36]
    for ra in t:    # mid-plane and cavity-average Nusselt agree within the stated error
        assert abs(t[ra]["Nu_half"] - t[ra]["Nu"]) / t[ra]["Nu"] <= N.DE_VAHL_DAVIS_ERROR[ra]


def test_parallel_plates_black_and_grey():
    q_black = N.parallel_plates_flux(400.0, 300.0, 1.0, 1.0)
    assert q_black == pytest.approx(N.SIGMA * (400.0 ** 4 - 300.0 ** 4))
    assert N.parallel_plates_flux(400.0, 300.0, 0.5, 0.5) == pytest.approx(q_black / 3.0)


def test_concentric_cylinders_limits():
    """r2 >> r1: a small body in a large enclosure, q = eps1 sigma A1 (T1^4 - T2^4)."""
    q = N.concentric_cylinders_per_length(400.0, 300.0, 0.3, 0.8, 0.01, 100.0)
    assert q == pytest.approx(0.3 * N.SIGMA * 2 * math.pi * 0.01 * (400.0 ** 4 - 300.0 ** 4), rel=1e-3)
    # r1 = r2: the parallel-plate result per unit area
    q2 = N.concentric_cylinders_per_length(400.0, 300.0, 0.3, 0.8, 1.0, 1.0)
    assert q2 / (2 * math.pi) == pytest.approx(N.parallel_plates_flux(400.0, 300.0, 0.3, 0.8))

"""The Elmer motor model's conventions: magnetisation against a closed form (needs Elmer; skipped without it), and
the B-H table it hands Elmer."""
import numpy as np
import pytest

from models.motor import elmer_em


def test_bh_table_is_monotone_and_starts_at_zero():
    rows = np.array(elmer_em._bh_table([[0, 0], [33.4, 0.1], [100, 1.0], [1000, 1.5], [10000, 1.8], [300000, 2.37]]))
    assert rows[0, 0] == 0 and rows[0, 1] == 0
    assert np.all(np.diff(rows[:, 0]) > 0) and np.all(np.diff(rows[:, 1]) >= 0)


@pytest.mark.skipif(not (elmer_em.ELMER_HOME / "bin/ElmerSolver.exe").exists(), reason="Elmer not installed")
def test_cylinder_closed_form(tmp_path):
    r = elmer_em.cylinder_check(tmp_path / "cyl")
    assert abs(r["rel_error"]) < 3e-3                 # B inside = Br / (1 + mu_r); the other convention is -11 %
    assert r["converged"]

"""The board temperature profile and a part's footprint maximum (studies/enclosure_thermal.py, 2026-11-25)."""
import math

import numpy as np

from studies.enclosure_thermal import board_profile, part_max_C


def test_profile_takes_the_hotter_cell_over_the_thickness_and_measures_from_the_board_end():
    # two cells through the thickness at x = 26, 28, 30 mm (board starts at 25 mm)
    C = np.array([[0.026, 0.0295, 0], [0.026, 0.0305, 0], [0.028, 0.0295, 0], [0.028, 0.0305, 0],
                  [0.030, 0.0295, 0], [0.030, 0.0305, 0]])
    T = np.array([350.0, 351.0, 352.0, 349.0, 360.0, 361.5]) + 0.0
    prof = board_profile(C, T, 0.025)
    assert [p[0] for p in prof] == [1.0, 3.0, 5.0]
    assert np.allclose([p[1] for p in prof], [351.0 - 273.15, 352.0 - 273.15, 361.5 - 273.15])


def test_part_max_over_its_footprint_only():
    prof = [[1.0, 70.0], [3.0, 72.0], [5.0, 75.0], [7.0, 80.0], [17.0, 90.0]]
    assert part_max_C(prof, [3.0, 7.0]) == 80.0
    assert math.isnan(part_max_C(prof, [8.0, 9.0]))

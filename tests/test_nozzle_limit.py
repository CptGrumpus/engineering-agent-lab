"""Study 18 part 2: the limit-load deck's schedule, the collapse read from CalculiX's status file, the reference."""
import math

import pytest

from models.fea import nozzle_limit as NL

P = {"shell_inner_radius_mm": 500.0, "shell_thickness_mm": 16.0, "shell_half_length_mm": 1000.0,
     "nozzle_inner_radius_mm": 100.0, "nozzle_thickness_mm": 12.0, "nozzle_length_mm": 350.0,
     "weld_fillet_radius_mm": 10.0, "pressure_MPa": 3.5, "allowable_stress_MPa": 138.0, "load_factor_max": 2.4}

STA = """SUMMARY OF JOB INFORMATION
  STEP      INC     ATT  ITRS     TOT TIME     STEP TIME      INC TIME
     1          1     1     2  0.100000E+01  0.100000E+01  0.100000E+01
     2          1     1     3  0.200000E+01  0.100000E+01  0.100000E+01
     3          1     1     4  0.250000E+01  0.500000E+00  0.500000E+00
     3          2     1U    4  0.250000E+01  0.500000E+00  0.500000E+00
     3          2     2     6  0.262500E+01  0.625000E+00  0.125000E+00
     3          3     1U    5  0.262500E+01  0.625000E+00  0.125000E+00
"""


def test_schedule_steps_through_the_code_load():
    assert NL.schedule(P) == pytest.approx([1.0, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2, 2.3, 2.4])
    assert NL.schedule(P | {"load_factor_max": 1.5}) == [1.0, 1.5]


def test_cylinder_collapse_pressure():
    # (2 / sqrt 3) x 207 x ln(516 / 500)
    assert NL.collapse_pressure_cylinder(P) == pytest.approx(2 / math.sqrt(3) * 207 * math.log(516 / 500), rel=1e-12)
    assert NL.collapse_pressure_cylinder(P) == pytest.approx(7.5289, abs=1e-4)


def test_last_converged_skips_unconverged_attempts(tmp_path):
    (tmp_path / "job.sta").write_text(STA)
    assert NL.last_converged(tmp_path / "job.sta") == (3, 0.625)


def test_collapse_located_inside_the_last_step(tmp_path):
    (tmp_path / "job.sta").write_text(STA)
    dat = []
    for k in (1, 2):                     # steps 1 and 2 completed (load factors 1.0 and 1.5)
        t = f"{float(k):.7E}"
        dat += [f" total force (fx,fy,fz) for set NSYMY and time  {t}", "", " 0. -1. 0.", "",
                f" total force (fx,fy,fz) for set NSYMZ and time  {t}", "", " 0. 0. -1.", "",
                f" forces (fx,fy,fz) for set NBACK and time  {t}", "", " 1 0. 0. 0.", ""]
        for m in ("NTOE", "NCROTCH", "NFAR"):
            dat += [f" displacements (vx,vy,vz) for set {m} and time  {t}", "", f" 5 {0.1 * k} 0. 0.", ""]
    (tmp_path / "job.dat").write_text("\n".join(dat) + "\n")
    h = NL.read_history(tmp_path / "job.dat", tmp_path / "job.sta", [1.0, 1.5, 1.6, 1.7])
    assert h["lambda"] == [1.0, 1.5]
    assert h["u_toe_mm"] == pytest.approx([0.1, 0.2])
    # step 3 runs from 1.5 to 1.6; its last converged step time is 0.625
    assert h["collapse_load_factor"] == pytest.approx(1.5 + 0.625 * 0.1)
    assert not h["completed_all_steps"]

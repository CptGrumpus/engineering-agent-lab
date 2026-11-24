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


def test_averaged_metrics_ignore_step_jitter():
    """FSI1 revision 1: with metric_average_s the metrics are window means, so a lift that jitters at every step about
    the right value reports that value, where the final value would report the jitter."""
    from studies.turek_hron_fsi import _window_means

    t = np.arange(0, 12.0001, 0.0025)
    lift = 0.7637 * (1 + 0.02 * (-1) ** np.arange(len(t)))
    series = {"t_s": t, "ux_A_m": np.full_like(t, 2.27e-5), "uy_A_m": np.full_like(t, 8.2e-4),
              "drag_N_per_m": np.full_like(t, 14.29), "lift_N_per_m": lift}
    params = {"benchmark_ux_A_m": 2.27e-5, "benchmark_uy_A_m": 8.2e-4, "benchmark_drag_N_per_m": 14.29,
              "benchmark_lift_N_per_m": 0.7637}
    final = STUDY.compute_metrics(series, params, {"numerics": {}})
    mean = STUDY.compute_metrics(series, params, {"numerics": {"metric_average_s": 2.0}})
    assert final["lift_deviation_pct"] == pytest.approx(2.0, rel=1e-6)
    assert mean["lift_deviation_pct"] < 0.01

    Ff = np.column_stack([t, np.full_like(t, 0.3), lift * 0.01, np.zeros_like(t), np.zeros_like(t)])
    blocks = [{"kind": "total", "set": "NFIX", "time": float(x), "rows": np.array([[-0.3, -l * 0.01]])}
              for x, l in zip(t, lift)]
    m = _window_means({"metric_average_s": 2.0}, Ff, blocks)
    assert np.allclose(np.array(m["flag_fluid_force_mean_N"]) + np.array(m["clamp_reaction_mean_N"]), 0, atol=1e-12)
    assert _window_means({}, Ff, blocks) == {}


def test_transfer_per_window_ignores_inertia(tmp_path):
    """The per-window transfer check compares forces at the same instant, so a large oscillating force (whose
    end-of-run balance with a clamp reaction would include the body's inertia) passes when the transfer is exact,
    and a 1 % loss in the mapping shows up as 1e-2."""
    from studies.turek_hron_fsi import read_watchintegral, transfer_per_window

    t = np.arange(1, 2001) * 1e-3
    fx, fy = 2.0 + 0.5 * np.sin(2 * np.pi * 4 * t), 2.4 * np.sin(2 * np.pi * 2 * t)
    for name, k in (("fluid", 1.0), ("solid", 0.99)):
        rows = "\n".join(f"{a:.6e}  {b:.9e}  {c:.9e}  0.0  0.0" for a, b, c in zip(t, k * fx, k * fy))
        (tmp_path / f"{name}.log").write_text("  Time  Force0  Force1  Displacement0  Displacement1\n" + rows + "\n",
                                              encoding="utf-8")
    wf, ws = read_watchintegral(tmp_path / "fluid.log"), read_watchintegral(tmp_path / "solid.log")
    Ff = np.column_stack([t, fx * 0.9, fy * 0.8, fx * 0.1, fy * 0.2])  # pressure + viscous parts of the same force
    r = transfer_per_window(wf, ws, Ff, 1.0, 2.0)
    assert r["transfer_windows"] == 1000
    assert r["transfer_fluid_max_rel"] < 1e-8
    assert r["transfer_mapping_max_rel"] == pytest.approx(0.01, rel=1e-6)


def test_precice_config_has_watch_integrals(tmp_path):
    info = W.write_case(FSI1, {}, tmp_path / "case")
    xml = (tmp_path / "case" / "precice-config.xml").read_text(encoding="utf-8")
    assert '<watch-integral mesh="Fluid-Mesh" name="Wet" scale-with-connectivity="false" />' in xml
    assert '<watch-integral mesh="Solid-Mesh" name="Wet" scale-with-connectivity="false" />' in xml


def test_flag_cell_quality_flags_a_cell_wrapped_around_the_tip_corner():
    from studies.turek_hron_fsi import flag_cell_quality
    # flag top y = 0.21, tip x = 0.6. Good corner: three square cells share the corner node (0.6, 0.21).
    h = 0.002
    xy = {1: (0.6 - h, 0.21), 2: (0.6, 0.21), 3: (0.6, 0.21 + h), 4: (0.6 - h, 0.21 + h), 5: (0.6 + h, 0.21 + h),
          6: (0.6 + h, 0.21), 7: (0.6 + h, 0.21 - h), 8: (0.6, 0.21 - h)}
    good = [[1, 2, 3, 4], [2, 6, 5, 3], [8, 7, 6, 2]]
    q = flag_cell_quality(xy, good, 0.25, 0.6, 0.19, 0.21)
    assert q["flag_cell_max_angle_deg"] == pytest.approx(90.0)
    # noise_a's defect: one quad spans the corner, nearly flat (165 deg) at the corner node.
    xy |= {9: (0.6 + 0.0014, 0.21 + 0.00037), 10: (0.6 - 0.00034, 0.21 + 0.0013)}
    bad = [[1, 2, 9, 10]]
    q = flag_cell_quality(xy, bad, 0.25, 0.6, 0.19, 0.21)
    assert q["flag_cell_max_angle_deg"] > 150 and q["flag_cell_max_angle_at_m"][0] == pytest.approx(0.6, abs=2e-3)
    # cells away from the flag are ignored
    far = {11: (1.0, 0.3), 12: (1.01, 0.3), 13: (1.01, 0.301), 14: (1.0, 0.35)}
    assert flag_cell_quality(far, [[11, 12, 13, 14]], 0.25, 0.6, 0.19, 0.21)["flag_cell_max_angle_deg"] == 0.0


def test_mesh_noise_table_classes_a_spread_under_the_noise_as_converged():
    import copy

    import studies.turek_hron_fsi as T
    pts = []
    for i, (h, uy) in enumerate(((0.0025, 0.81749e-3), (0.0017677670, 0.82119e-3), (0.00125, 0.81300e-3))):
        m = {"ux_A_m": 2.26e-5 * (1 + 0.001 * i), "uy_A_m": uy, "drag_N_per_m": 14.29 + 0.001 * i,
             "lift_N_per_m": 0.762 + 0.001 * i}
        pts.append({"status": "completed", "parameters": {"fluid_cell_size_m": h}, "metrics": m, "label": f"p{i}"})
    case = {"sweep": {"parameter": "fluid_cell_size_m"}, "verification": {"gci_max": 0.01}}
    _, d0 = T.STUDY.verify_run_level(case, {"points": pts}, None)
    assert d0["uy_A_m"]["uncertainty"] == float("inf")                 # r1: 'divergent (oscillating, growing)'
    case2 = copy.deepcopy(case)
    case2["verification"]["mesh_noise_rel"] = {"uy_A_m": 0.0194}
    _, d1 = T.STUDY.verify_run_level(case2, {"points": pts}, None)
    assert d1["uy_A_m"]["regime"] == "converged"
    assert d1["uy_A_m"]["uncertainty"] == pytest.approx(1.25 * 0.5 * (0.82119 - 0.81300) / 0.81300, rel=1e-6)
    assert d1["drag_N_per_m"] == d0["drag_N_per_m"]                     # metrics not in the table: unchanged


def test_periodic_mesh_study_converges_the_periodic_metrics_not_the_snapshot():
    import studies.turek_hron_fsi as T
    pts = []
    for i, h in enumerate((0.0035355339, 0.0025, 0.0017677670)):
        m = {k: 1.0 + 0.01 / (i + 1) for k in T.PERIODIC_METRICS}
        m |= {"ux_A_m": 1.0 + i, "uy_A_m": -1.0 * i, "drag_N_per_m": 10.0 * i, "lift_N_per_m": 5.0 - i}   # snapshots
        pts.append({"status": "completed", "parameters": {"fluid_cell_size_m": h}, "metrics": m, "label": f"p{i}"})
    case = {"sweep": {"parameter": "fluid_cell_size_m"}, "numerics": {"periodic_periods": 4},
            "verification": {"gci_max": 0.01}}
    checks, d = T.STUDY.verify_run_level(case, {"points": pts}, None)
    assert set(d) - {"meshes_used"} == set(T.PERIODIC_GCI_METRICS)
    assert {c["metric"] for c in checks} == {f"{m}_deviation_pct" for m in T.PERIODIC_GCI_METRICS}


def test_dense_writing_adds_only_a_function_object(tmp_path):
    """Crash diagnosis: writeObjects from a set time; without it the controlDict is unchanged, and the main write
    control is never touched (re-reading it mid-run resets the end time the preCICE adapter extends)."""
    W.write_case(FSI1, {"solid_alpha": -0.3}, tmp_path / "plain")
    W.write_case(FSI1, {"solid_alpha": -0.3, "dense_write_from_s": 0.8}, tmp_path / "dense")
    plain = (tmp_path / "plain/fluid/system/controlDict").read_text()
    dense = (tmp_path / "dense/fluid/system/controlDict").read_text()
    assert "writeObjects" not in plain and "runTimeModifiable" not in plain
    assert not (tmp_path / "plain/fluid/dense_write_from_s").exists()
    assert re.search(r"type\s+writeObjects;", dense) and re.search(r"timeStart\s+0\.8;", dense)
    assert "pointDisplacement" in dense and "runTimeModifiable" not in dense
    assert float((tmp_path / "dense/fluid/dense_write_from_s").read_text()) == 0.8
    # everything outside the function object is identical
    fo = dense[dense.index("    denseWrite"):dense.index("    }\n", dense.index("    denseWrite")) + 6]
    assert dense.replace(fo, "") == plain


def test_frozen_motion_diffusivity_distance_and_floor():
    """Exact distance to the cylinder and the flag rectangle; faces on the body take half their cell's distance."""
    spec = importlib.util.spec_from_file_location("fmd", ROOT / "models/fsi/frozen_motion_diffusivity.py")
    F = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(F)
    g = {"xc": 0.2, "yc": 0.2, "r": 0.05, "flag_x0": 0.249, "flag_x1": 0.6, "flag_y0": 0.19, "flag_y1": 0.21,
         "exponent": 1.0}
    P = np.array([[0.2, 0.3, 0.0],      # above the cylinder: 0.1 - 0.05
                  [0.7, 0.2, 0.0],      # beyond the tip: 0.1
                  [0.4, 0.25, 0.0],     # above the flag: 0.04
                  [0.63, 0.25, 0.0],    # off the tip corner: hypot(0.03, 0.04)
                  [0.4, 0.2, 0.0]])     # inside the flag: 0
    assert F.body_distance(P, g) == pytest.approx([0.05, 0.1, 0.04, 0.05, 0.0])
    # one square cell above the flag (x 0.40-0.41, y 0.21-0.22): its bottom face lies on the flag
    pts = np.array([[0.40, 0.21, 0], [0.41, 0.21, 0], [0.41, 0.22, 0], [0.40, 0.22, 0]], float)
    faces = [[0, 1], [1, 2], [2, 3], [3, 0]]
    gam = F.diffusivity(pts, faces, np.zeros(4, int), g)
    d_cell = 0.005                                           # mean of the face centres: y = 0.215
    assert gam[0] == pytest.approx(1 / (0.5 * d_cell))       # on the flag: floored
    assert gam[2] == pytest.approx(1 / 0.01)                 # the top face, 0.01 from the flag

"""Clevis bracket (the optimisation loop's 3D part): geometry, guards, and the lug-section reference."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from studies.clevis_bracket import STUDY, section_check

ROOT = Path(__file__).resolve().parent.parent
P = dict(base_length_mm=100.0, base_width_mm=100.0, base_thickness_mm=10.0, lug_radius_mm=20.0, pin_height_mm=70.0,
         pin_diameter_mm=16.0, lug_thickness_mm=12.0, gusset_thickness_mm=8.0, gusset_height_mm=40.0, gusset_aspect=0.7,
         fillet_radius_mm=3.0, youngs_modulus_MPa=68900.0, poisson_ratio=0.33, density_t_per_mm3=2.7e-9,
         load_x_N=1500.0, load_y_N=1000.0, load_z_N=4500.0, element_size_mm=4.0, yield_strength_MPa=276.0)


def _model():
    spec = importlib.util.spec_from_file_location("clevis_t", ROOT / "models/fea/clevis_bracket.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_solid_is_valid_and_grows_with_each_variable():
    pytest.importorskip("cadquery")
    m = _model()
    v0 = m.build_solid(P).val()
    assert v0.isValid()
    for k in ("lug_thickness_mm", "gusset_thickness_mm", "gusset_height_mm"):
        assert m.build_solid(P | {k: P[k] + 2}).val().Volume() > v0.Volume()


def test_every_corner_of_the_design_space_builds():
    pytest.importorskip("cadquery")
    m = _model()
    for tl in (5.0, 20.0):
        for tg in (3.0, 12.0):
            for hg in (8.0, 50.0):
                assert m.build_solid(P | {"lug_thickness_mm": tl, "gusset_thickness_mm": tg,
                                          "gusset_height_mm": hg}).val().isValid()


def test_derive_rejects_gussets_past_the_base_or_the_pin():
    with pytest.raises(ValueError):
        STUDY.derive(P | {"gusset_height_mm": 70.0, "gusset_aspect": 0.7})
    with pytest.raises(ValueError):
        STUDY.derive(P | {"gusset_height_mm": 60.0, "gusset_aspect": 0.1})


def test_section_reference_on_an_exact_beam_field():
    p = P | {"gusset_height_mm": 10.0}            # clear lug section between the gussets and the hole
    tl, R, H = p["lug_thickness_mm"], p["lug_radius_mm"], p["pin_height_mm"]
    z0 = 0.5 * (10 + 10 + 3 + H - 8)
    xs, ys = np.meshgrid([-R, R], [-tl / 2, tl / 2])
    x, y = xs.ravel(), ys.ravel()
    A, Ixx, Iyy = 2 * R * tl, 2 * R * tl**3 / 12, tl * (2 * R) ** 3 / 12
    szz = 4500 / A - 1500 * (H - z0) * x / Iyy - 1000 * (H - z0) * y / Ixx
    series = {"x_mm": x, "y_mm": y, "z_mm": np.full_like(x, z0), "szz_MPa": szz}
    r = section_check(series, p)
    assert r is not None and r["max_err_rel"] < 1e-12
    assert section_check(series, P) is None           # 40 mm gussets: no clear section


def test_curvature_refinement_scales_with_element_size(tmp_path):
    """The optimisation run's 4 mm mesh is unchanged (12 per circle); finer levels refine the fillets too."""
    m = _model()
    assert [m.curvature_points(h) for h in (6.0, 4.0, 8 / 3, 2.0)] == [8, 12, 18, 24]
    m.write_geo(P, tmp_path / "mesh.geo")
    assert "Mesh.MeshSizeFromCurvature = 12;" in (tmp_path / "mesh.geo").read_text(encoding="utf-8")


def _step_body(path):
    """STEP text without the lines that carry a timestamp or an export counter."""
    return "".join(x for x in path.read_text(encoding="utf-8").splitlines(True)
                   if "FILE_NAME" not in x and "translator" not in x)


def test_build_is_reproducible_whatever_was_built_before(tmp_path):
    """The fillet edges used to reach OCC in set order (memory addresses): same shape, different face split."""
    pytest.importorskip("cadquery")
    m = _model()
    m.build_step(P, tmp_path / "a.step")
    for tl in (6.0, 15.0):
        m.build_solid(P | {"lug_thickness_mm": tl})
    m.build_step(P, tmp_path / "b.step")
    assert _step_body(tmp_path / "a.step") == _step_body(tmp_path / "b.step")


def test_inverted_tet_detector():
    from studies.clevis_bracket import INVERTED

    assert INVERTED.search("Warning : Volume mesh: worst distortion = -0.0185 (avg = 0.99, 1 elements with jac. < 0)")
    assert not INVERTED.search("Info    : Volume mesh: worst distortion = 0.21 (avg = 0.99, 0 elements with jac. < 0)")
    assert not INVERTED.search("Info    : 62494 nodes 50779 elements")


def test_high_order_fallback_only_when_asked(tmp_path):
    m = _model()
    m.write_geo(P, tmp_path / "a.geo")
    m.write_geo(P, tmp_path / "b.geo", high_order_optimize=True)
    assert "HighOrderOptimize" not in (tmp_path / "a.geo").read_text(encoding="utf-8")
    assert "Mesh.HighOrderOptimize = 1;" in (tmp_path / "b.geo").read_text(encoding="utf-8")


def test_fillet_refinement_is_optional_and_refines_the_fillets(tmp_path):
    m = _model()
    assert m.fillet_refinement(P) == (12, 1.0)                     # as in clevis_opt / clevis_opt_r1
    n, h_min = m.fillet_refinement(P | {"fillet_element_size_mm": 1.0})
    assert 2 * np.pi * P["fillet_radius_mm"] / n <= 1.0 and h_min <= 0.5
    m.write_geo(P | {"fillet_element_size_mm": 1.0}, tmp_path / "mesh.geo")
    assert f"Mesh.MeshSizeFromCurvature = {n};" in (tmp_path / "mesh.geo").read_text(encoding="utf-8")


def test_run_level_gci_on_a_fillet_size_sweep():
    """An oscillating fine-fillet band (the c011 values) gives a finite uncertainty, checked against the limit."""
    case = {"sweep": {"parameter": "fillet_element_size_mm"}, "verification": {"gci_max": 0.01},
            "requirements": [{"metric": "peak_von_mises_MPa", "limit": 100.0}]}
    pts = [{"label": f"p{i}", "status": "completed", "parameters": {"fillet_element_size_mm": h},
            "metrics": {"peak_von_mises_MPa": v}} for i, (h, v) in enumerate(((1.0, 96.61), (0.85, 97.62), (0.75, 96.83)))]
    checks, detail = STUDY.verify_run_level(case, {"points": pts}, pts)
    by = {c["id"]: c for c in checks}
    assert detail["peak_von_mises_MPa"]["regime"] == "oscillatory"
    assert by["discretization_peak_von_mises_MPa"]["status"] == "PASS"
    assert by["requirement_margin_peak_von_mises_MPa"]["status"] == "PASS"


def test_fillet_sweep_can_leave_a_globally_converged_metric_to_the_global_study():
    """clevis_confirm_r1_fillet: deflection 0.06359 / 0.0636 / 0.0636 mm gave an 'anomalous' order of 4.72."""
    reqs = [{"metric": "peak_von_mises_MPa", "limit": 100.0}, {"metric": "pin_deflection_mm", "limit": 0.1}]
    pts = [{"label": f"p{i}", "status": "completed", "parameters": {"fillet_element_size_mm": h},
            "metrics": {"peak_von_mises_MPa": v, "pin_deflection_mm": d}}
           for i, (h, v, d) in enumerate(((1.0, 96.61, 0.0635871), (0.85, 97.62, 0.0635984), (0.75, 96.83, 0.0636027)))]
    base = {"sweep": {"parameter": "fillet_element_size_mm"}, "requirements": reqs}
    checks, _ = STUDY.verify_run_level(base | {"verification": {"gci_max": 0.01}}, {"points": pts}, pts)
    assert any(c["id"] == "discretization_pin_deflection_mm" and c["status"] == "FAIL" for c in checks)
    checks, detail = STUDY.verify_run_level(
        base | {"verification": {"gci_max": 0.01, "mesh_study_metrics": ["peak_von_mises_MPa"]}}, {"points": pts}, pts)
    assert {c["id"] for c in checks} == {"discretization_peak_von_mises_MPa", "requirement_margin_peak_von_mises_MPa"}
    assert all(c["status"] == "PASS" for c in checks)
    assert detail["not_assessed_by_this_sweep"] == ["pin_deflection_mm"]


def test_mesh_noise_floor_classes_a_jittering_resolved_peak_as_converged():
    """clevis_confirm_r2: 97.36 / 97.54 / 98.33 MPa read as 'divergent' with the round-off floor."""
    reqs = [{"metric": "peak_von_mises_MPa", "limit": 100.0}]
    pts = [{"label": f"p{i}", "status": "completed", "parameters": {"fillet_element_size_mm": h},
            "metrics": {"peak_von_mises_MPa": v}} for i, (h, v) in enumerate(((1.0, 97.36), (0.85, 97.54), (0.75, 98.33)))]
    base = {"sweep": {"parameter": "fillet_element_size_mm"}, "requirements": reqs}
    checks, detail = STUDY.verify_run_level(base | {"verification": {"gci_max": 0.01}}, {"points": pts}, pts)
    assert detail["peak_von_mises_MPa"]["regime"] == "divergent"
    checks, detail = STUDY.verify_run_level(base | {"verification": {"gci_max": 0.01, "mesh_noise_rel": 0.015}},
                                            {"points": pts}, pts)
    u = detail["peak_von_mises_MPa"]
    assert u["regime"] == "converged" and u["uncertainty"] == pytest.approx(1.25 * 0.5 * (98.33 - 97.36) / 98.33)
    assert all(c["status"] == "PASS" for c in checks)

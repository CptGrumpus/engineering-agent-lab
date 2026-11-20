"""The task graders are verified like the models: the reference answer scores full marks,
and every documented trap fails on the criterion it should break. Trap answers are
computed from first principles here, not copied from the solution tables."""

import importlib.util
import math
from pathlib import Path

import pytest

TASKS = Path(__file__).resolve().parent.parent / "tasks"


def grader(name):
    spec = importlib.util.spec_from_file_location(f"grader_{name}", TASKS / name / "grader.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def failed(result):
    return {c["criterion"] for c in result["criteria"] if not c["passed"]}


@pytest.mark.parametrize("name", ["hertz_roller_contact", "heated_channel_wall_temperature",
                                  "cantilever_root_stress"])
def test_reference_answer_scores_full_marks_and_garbage_scores_zero(name):
    g = grader(name)
    assert g.grade(dict(g.REFERENCE))["passed"]
    assert g.grade({})["score"] == 0.0


def test_reference_values_come_from_the_independent_solutions():
    from validation import graetz, hertz

    r = hertz.line_contact(500.0, 50.0, 210000.0, 0.3)
    ref = grader("hertz_roller_contact").REFERENCE
    assert ref["peak_contact_pressure_MPa"] == pytest.approx(r["peak_pressure_MPa"], rel=1e-4)
    assert ref["max_shear_depth_mm"] == pytest.approx(r["max_shear_depth_mm"], rel=1e-3)
    t = graetz.thermal_entry([0.05], H=1e-3, U=0.1, rho=997.0, cp=4180.0, k=0.607, q=30000.0, T_in=25.0)
    ref = grader("heated_channel_wall_temperature").REFERENCE
    assert ref["peak_wall_temperature_C"] == pytest.approx(t["T_wall"][0], abs=1e-3)
    assert ref["nusselt_at_end_of_heating"] == pytest.approx(t["Nu"][0], abs=1e-3)


def test_hertz_traps():
    g = grader("hertz_roller_contact")
    ref = dict(g.REFERENCE)
    # E instead of E*: a scales with sqrt(E*/E), p0 with its inverse
    s = math.sqrt((210000 / (2 * (1 - 0.09))) / 210000)
    a, p0 = ref["contact_half_width_mm"] * s, ref["peak_contact_pressure_MPa"] / s
    wrong = ref | {"contact_half_width_mm": a, "peak_contact_pressure_MPa": p0,
                   "max_subsurface_shear_MPa": 0.3 * p0, "max_shear_depth_mm": 0.786 * a,
                   "pressure_limit_met": p0 <= 650}
    assert p0 > 650
    assert {"contact_half_width_mm", "peak_contact_pressure_MPa", "pressure_limit_met"} <= failed(g.grade(wrong))
    # shear taken at the surface
    assert "max_shear_depth_mm" in failed(g.grade(ref | {"max_shear_depth_mm": 0.0}))
    # surface pressure read from extrapolated element stresses (3.5 % high on a fine-ish mesh)
    assert failed(g.grade(ref | {"peak_contact_pressure_MPa": 1.035 * ref["peak_contact_pressure_MPa"]})) \
        == {"peak_contact_pressure_MPa"}


def test_heated_channel_traps():
    g = grader("heated_channel_wall_temperature")
    ref = dict(g.REFERENCE)
    bulk = 25 + ref["coolant_rise_K"]
    for nu in (140 / 17, 7.541, 5.385):            # fully developed, constant wall T, one wall heated
        tw = bulk + 30000 * 2e-3 / (0.607 * nu)
        bad = failed(g.grade(ref | {"peak_wall_temperature_C": tw, "nusselt_at_end_of_heating": nu,
                                    "wall_limit_met": tw <= 45}))
        assert {"peak_wall_temperature_C", "nusselt_at_end_of_heating"} <= bad
        if tw > 45:
            assert "wall_limit_met" in bad
    assert failed(g.grade(ref | {"coolant_rise_K": ref["coolant_rise_K"] / 2})) == {"coolant_rise_K"}


def test_cantilever_traps():
    g = grader("cantilever_root_stress")
    ref = dict(g.REFERENCE)
    corner = ref | {"root_bending_stress_MPa": 217.0, "stress_limit_met": False, "peak_fe_stress_is_singular": False}
    assert failed(g.grade(corner)) == {"root_bending_stress_MPa", "stress_limit_met", "peak_fe_stress_is_singular"}
    full_depth = 1000 * 200 * 20 / (20 * 20**3 / 12)
    assert full_depth == pytest.approx(300.0)
    assert "root_bending_stress_MPa" in failed(g.grade(ref | {"root_bending_stress_MPa": full_depth}))
    # both beam theories (0.952, 0.960) and the 3D result (0.953) are accepted
    for d in (0.952, 0.953, 0.960):
        assert g.grade(ref | {"tip_deflection_mm": d})["passed"]
    assert "tip_deflection_mm" in failed(g.grade(ref | {"tip_deflection_mm": 0.952 * 0.8}))   # linear tets, too stiff

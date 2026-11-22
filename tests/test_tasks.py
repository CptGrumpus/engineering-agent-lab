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
                                  "cantilever_root_stress", "sagging_strip_clearance",
                                  "nozzle_stress_linearisation"])
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


def test_sagging_strip_reference_and_traps():
    """Reference vs the elastica; each trap computed here from first principles fails where it should."""
    from validation import elastica as e

    g = grader("sagging_strip_clearance")
    ref = dict(g.REFERENCE)
    assert g.grade(ref)["passed"] and g.grade({})["score"] == 0.0
    L, h, q, E, nu = 0.40, 0.020, 1200 * 9.81 * 0.020, 10e6, 0.45
    Ep = e.plane_strain_modulus(E, nu)
    assert ref["bending_modulus_MPa"] == pytest.approx(Ep / 1e6, rel=1e-3)
    right = e.elastica_tip(q, L, Ep * h**3 / 12)
    assert ref["tip_drop_mm"] == pytest.approx(-right["uy"] * 1e3, rel=0.005)      # FE and elastica agree
    assert ref["tip_pull_in_mm"] == pytest.approx(-right["ux"] * 1e3, rel=0.01)
    # the elastica answer itself must pass (a beam solver is a valid method)
    beam = {"tip_drop_mm": -right["uy"] * 1e3, "tip_pull_in_mm": -right["ux"] * 1e3,
            "bending_modulus_MPa": Ep / 1e6, "clearance_met": True}
    assert g.grade(beam)["passed"]
    # trap 1: small-deflection formula, plane strain right -> drop 90.1 mm, fails the 89 mm clearance
    lin = -e.linear_tip(q, L, Ep * h**3 / 12)["uy"] * 1e3
    assert lin > 89.0
    t1 = {"tip_drop_mm": lin, "tip_pull_in_mm": 0.0, "bending_modulus_MPa": Ep / 1e6, "clearance_met": False}
    assert failed(g.grade(t1)) == {"tip_drop_mm", "tip_pull_in_mm", "clearance_met"}
    # trap 2: plane stress, large deflection right
    ps = e.elastica_tip(q, L, E * h**3 / 12)
    t2 = {"tip_drop_mm": -ps["uy"] * 1e3, "tip_pull_in_mm": -ps["ux"] * 1e3, "bending_modulus_MPa": E / 1e6,
          "clearance_met": False}
    assert failed(g.grade(t2)) == {"tip_drop_mm", "tip_pull_in_mm", "bending_modulus_MPa", "clearance_met"}
    # the limit sits between the right answer and the nearest trap
    assert -right["uy"] * 1e3 < 89.0 < lin


def _nozzle_table():
    import numpy as np

    rows = [ln for ln in (TASKS / "nozzle_stress_linearisation" / "task.md").read_text(encoding="utf-8").splitlines()
            if ln.startswith("| ") and ln[2].isdigit()]
    data = np.array([[float(c) for c in ln.strip("| ").split("|")] for ln in rows])
    return data[:, 0], data[:, 1:]


def test_nozzle_reference_and_traps():
    """Reference from the task's own table through harness/linearize.py; each trap computed from the same table."""
    import numpy as np
    from scipy.integrate import simpson

    from harness.linearize import linearize, von_mises

    g = grader("nozzle_stress_linearisation")
    ref = dict(g.REFERENCE)
    s, L = _nozzle_table()
    assert len(s) == 21 and s[-1] == pytest.approx(16.0)
    res = linearize(s, L, np.eye(3))
    assert ref["pl_MPa"] == pytest.approx(res["membrane_vm"], abs=0.01)
    assert ref["pq_MPa"] == pytest.approx(res["membrane_plus_bending_vm"], abs=0.01)
    assert von_mises(res["at_start"]) > von_mises(res["at_end"])           # the inner surface governs
    t = s[-1]
    mem = simpson(L, x=s, axis=0) / t
    ben = 6 / t**2 * simpson(L * (t / 2 - s)[:, None], x=s, axis=0)

    def answer(pl, pq, surface="inner"):
        return ref | {"pl_MPa": pl, "pq_MPa": pq, "pq_governing_surface": surface,
                      "pl_limit_met": pl <= 207, "pq_limit_met": pq <= 414}

    # the trapezoid rule is an acceptable method
    tr_mem = np.trapezoid(L, x=s, axis=0) / t
    assert g.grade(answer(float(von_mises(tr_mem)), ref["pq_MPa"]))["passed"]
    # traps that flip the PL verdict
    avg_vm = float(simpson(von_mises(L), x=s) / t)
    peak = float(von_mises(L).max())
    hoop = float(mem[2])
    m = np.array([[mem[0], mem[3], mem[5]], [mem[3], mem[1], mem[4]], [mem[5], mem[4], mem[2]]])
    ev = np.linalg.eigvalsh(m)
    tresca = float(ev[-1] - ev[0])
    for wrong in (avg_vm, peak, hoop, tresca):
        assert wrong > 207
        assert {"pl_MPa", "pl_limit_met"} <= failed(g.grade(answer(wrong, ref["pq_MPa"])))
    # shears dropped: still a pass, but the PL value is caught
    no_shear = float(von_mises(np.r_[mem[:3], 0, 0, 0]))
    assert no_shear < 207 and failed(g.grade(answer(no_shear, ref["pq_MPa"]))) == {"pl_MPa"}
    # bending applied to every component
    allb = max(float(von_mises(mem + ben)), float(von_mises(mem - ben)))
    assert failed(g.grade(answer(ref["pl_MPa"], allb))) == {"pq_MPa"}
    # bending sign reversed: the outer surface looks governing
    assert failed(g.grade(answer(ref["pl_MPa"], ref["pq_MPa"], "outer"))) == {"pq_governing_surface"}

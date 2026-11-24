"""Model registry: case-file `model` name -> (study, backend class)."""

from __future__ import annotations

from harness.backend_base import Backend
from harness.study import Study


def _studies() -> list[Study]:
    from studies import (cantilever, channel_flow, duct_flow,  # lazy: avoids cycles
                         fin, mounting_plate, msd, quarter_car, strap_hole,
                         bracket_modal, strap_fatigue, hertz_contact, heated_channel,
                         cold_plate, tapered_bracket, strut_buckling,
                         strap_plastic, bolted_joint, clevis_bracket, flag_csm, turek_hron_cfd, turek_hron_fsi, motor_em,
                         motor_torque, motor_lut, motor_efficiency, rotor_stress, pressure_vessel, pipe_flow,
                         motor_thermal, vessel_head, step_flow, bracket_random, bracket_random_uq,
                         rotor_critical, edge_crack, oring_seal, cavity_convection)

    return [msd.STUDY, quarter_car.STUDY, cantilever.STUDY, mounting_plate.STUDY,
            channel_flow.STUDY, duct_flow.STUDY, fin.STUDY, strap_hole.STUDY, bracket_modal.STUDY,
            strap_fatigue.STUDY, hertz_contact.STUDY, heated_channel.STUDY, cold_plate.STUDY,
            tapered_bracket.STUDY, strut_buckling.STUDY,
            strap_plastic.STUDY, bolted_joint.STUDY,
            clevis_bracket.STUDY, flag_csm.STUDY, flag_csm.STUDY_CSM3, turek_hron_cfd.STUDY, turek_hron_fsi.STUDY, motor_em.STUDY,
            motor_torque.STUDY, motor_lut.STUDY, motor_efficiency.STUDY, rotor_stress.STUDY, pressure_vessel.STUDY, pipe_flow.STUDY,
            motor_thermal.STUDY, vessel_head.STUDY, step_flow.STUDY, bracket_random.STUDY, bracket_random_uq.STUDY,
            rotor_critical.STUDY, edge_crack.STUDY, oring_seal.STUDY, cavity_convection.STUDY]


def models() -> dict[str, tuple[Study, type[Backend]]]:
    return {name: (s, b) for s in _studies() for name, b in s.models.items()}


def resolve(model: str) -> tuple[Study, Backend]:
    table = models()
    if model not in table:
        raise ValueError(f"unsupported model {model!r}; supported: {sorted(table)}")
    study, backend_cls = table[model]
    return study, backend_cls()


def study_for(model: str) -> Study:
    table = models()
    if model not in table:
        raise ValueError(f"unsupported model {model!r}; supported: {sorted(table)}")
    return table[model][0]

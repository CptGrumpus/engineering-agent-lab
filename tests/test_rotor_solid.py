"""Study 23 part 2: the rotor solid's geometry (models/fea/rotor_solid.py) against hand volumes; the ROSS builder's
element diameters for the hub and journals (models/rotor/fan_rotor.py runs in its own environment, so only the
diameter layout is tested here)."""
import importlib.util
from pathlib import Path

import pytest

from models.fea import rotor_solid as rs

P = {"bearing_span_m": 1.0, "shaft_diameter_m": 0.065, "disc_diameter_m": 0.4, "disc_width_m": 0.025,
     "bearing_stiffness_N_per_m": 1e7, "youngs_modulus_Pa": 205e9, "poisson_ratio": 0.29, "density_kg_per_m3": 7850.0,
     "n_elements": 20}
DETAIL = {"hub_diameter_m": 0.13, "hub_length_m": 0.1, "journal_diameter_m": 0.055, "journal_length_m": 0.05}


@pytest.mark.parametrize("extra", [{}, DETAIL], ids=["uniform", "detailed"])
def test_solid_matches_hand_volume(tmp_path, extra):
    pytest.importorskip("cadquery")
    cad = rs.build_cad(P | extra, tmp_path / "r.step")
    assert cad["volume_mm3"] == pytest.approx(cad["hand_volume_mm3"], rel=1e-9)


def test_ross_element_diameters_put_hub_and_journals_on_nodes():
    spec = importlib.util.spec_from_file_location("fan_rotor_src", Path("models/rotor/fan_rotor.py"))
    src = Path(spec.origin).read_text(encoding="utf-8")
    ns: dict = {}
    # the function needs no ROSS: execute only its definition
    exec(src[src.index("OPTIONAL = "):src.index("\ndef build(")], ns)
    d = ns["diameters"](P | DETAIL)
    assert d[0] == d[-1] == 0.055 and d[1] == d[-2] == 0.065          # one 50 mm journal element at each end
    assert d[9] == d[10] == 0.13 and d[8] == d[11] == 0.065            # the hub: the two elements at mid-span
    with pytest.raises(ValueError):
        ns["diameters"](P | DETAIL | {"hub_length_m": 0.07})

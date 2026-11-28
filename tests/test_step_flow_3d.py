"""Study 19 part 3: the 3D step writer (models/cfd/step3d_openfoam.py) keeps the 2D x-y mesh exactly, maps every 3D
cell to its 2D cell, and writes the side wall as a wall or a symmetry plane."""

import importlib.util
import re
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("step3d_model", ROOT / "models" / "cfd" / "step3d_openfoam.py")
W3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(W3)

P = {"step_height_m": 0.0127, "inlet_height_ratio": 8.0, "reynolds_number_h": 37500.0, "inlet_velocity_m_per_s": 41.95,
     "reference_velocity_m_per_s": 44.2, "upstream_length_m": 1.153, "downstream_length_over_h": 50.0,
     "inlet_turbulence_intensity": 0.01, "inlet_viscosity_ratio": 10.0, "mesh_level": 0.25, "turbulence_model": "kOmegaSST",
     "half_span_m": 0.0755, "side_wall": 1, "spanwise_level": 0.5, "side_wall_start_m": -1.153}
NUM = {"residual_p": 1e-6, "residual_U": 2e-7, "residual_turb": 2e-6, "max_iterations": 10, "stage1_iterations": 5}


def test_spanwise_grading_fills_the_half_span():
    g = W3.geometry(P)
    gz, n, y1 = g["growth_z"], g["nz"], g["y1z_m"]
    assert y1 * (gz ** n - 1) / (gz - 1) == pytest.approx(P["half_span_m"], rel=1e-9)
    assert g["cells"] == g["cells_2d"] * n


def test_too_few_spanwise_cells_are_refused():
    with pytest.raises(ValueError, match="cannot fill"):
        W3.geometry(P | {"spanwise_level": 0.25})


def test_no_split_when_the_side_wall_starts_at_the_inlet():
    assert W3.geometry(P)["split"] is None


def test_split_keeps_block_a_faces():
    g = W3.geometry(P | {"side_wall_start_m": -0.5})
    sp = g["split"]
    gu, ms, n = sp["growth_up"], sp["m_s"], g["nx_up"]
    # the split face is one of the 2D grading's faces, and the two blocks' cells continue its progression
    assert sp["x_s_m"] == pytest.approx(-g["dx_lip_m"] * (gu ** ms - 1) / (gu - 1), rel=1e-12)
    assert abs(sp["x_s_m"] + 0.5) < g["dx_lip_m"] * gu ** ms
    assert 0 < ms < n


@pytest.mark.parametrize("start", [-1.153, -0.5])
def test_extrude_index_covers_every_2d_cell_once_per_layer(start):
    g = W3.geometry(P | {"side_wall_start_m": start})
    idx = W3.extrude_index(g)
    assert len(idx) == g["cells"]
    counts = np.bincount(idx, minlength=g["cells_2d"])
    assert np.all(counts == g["nz"])


def test_extrude_index_with_a_split_follows_block_a_in_x():
    g = W3.geometry(P | {"side_wall_start_m": -0.5})
    ms, nxu, ny = g["split"]["m_s"], g["nx_up"], g["ny_duct"]
    idx = W3.extrude_index(g)
    n1 = (nxu - ms) * ny * g["nz"]
    # first layer of block A2 starts at 2D column nxu - ms of block A's first row
    assert idx[n1] == nxu - ms
    assert idx[(nxu - ms) * ny] == 0  # block A1's second layer repeats its first


@pytest.mark.parametrize("side_wall,start", [(1, -1.153), (0, -1.153), (1, -0.5)])
def test_written_case(tmp_path, side_wall, start):
    p = P | {"side_wall": side_wall, "side_wall_start_m": start}
    g = W3.write_case(p, NUM, tmp_path)
    bm = (tmp_path / "system/blockMeshDict").read_text(encoding="utf-8")
    assert "empty" not in bm
    assert re.search(r"sideWall\s+\{ type " + ("wall" if side_wall else "symmetry"), bm)
    assert ("sideWallSlip" in bm) == (start > -1.153)
    for f in ("U", "p", "k", "omega", "nut"):
        txt = (tmp_path / "0" / f).read_text(encoding="utf-8")
        assert "frontAndBack" not in txt and "midPlane" in txt and "sideWall" in txt
    nblocks = bm.count("hex (")
    assert nblocks == (4 if g["split"] else 3)
    assert f"numberOfSubdomains 1;" in (tmp_path / "system/decomposeParDict").read_text(encoding="utf-8")


def test_initial_field_is_copied_to_every_layer(tmp_path):
    g = W3.geometry(P)
    n2 = g["cells_2d"]
    init = {"U": np.column_stack([np.arange(n2, dtype=float), np.zeros(n2), np.zeros(n2)]),
            "p": np.arange(n2, dtype=float), "k": np.ones(n2), "omega": np.ones(n2), "nut": np.zeros(n2)}
    W3.write_case(P, NUM, tmp_path, initial=init)
    txt = (tmp_path / "0/p").read_text(encoding="utf-8")
    body = txt.split("(", 1)[1].split(")", 1)[0].split()
    vals = np.array(body, dtype=float)
    assert len(vals) == g["cells"]
    np.testing.assert_array_equal(vals, np.arange(n2, dtype=float)[W3.extrude_index(g)])

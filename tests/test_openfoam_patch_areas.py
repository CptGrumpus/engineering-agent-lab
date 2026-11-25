"""harness.openfoam.patch_face_areas on a hand-written ascii polyMesh: two cells of unequal width (2.0 and 2.5 mm)
one cell deep, so the bottom patch has two faces of different area (a sum times one face area would be wrong)."""

import numpy as np
import pytest

from harness.openfoam import patch_face_areas

HEAD = 'FoamFile\n{{\n    format ascii;\n    class {cls};\n    object {obj};\n}}\n\n'


def _write(d, name, cls, body):
    (d / name).write_text(HEAD.format(cls=cls, obj=name) + body, encoding="utf-8")


def test_patch_face_areas_unequal_faces(tmp_path):
    d = tmp_path / "polyMesh"
    d.mkdir()
    xs, h, dz = (0.0, 2.0e-3, 4.5e-3), 3.0e-3, 1.0e-3
    pts = [(x, y, z) for z in (0.0, dz) for y in (0.0, h) for x in xs]   # index = x + 3 y + 6 z

    def i(ix, iy, iz):
        return ix + 3 * iy + 6 * iz
    faces = [
        (i(1, 0, 0), i(1, 1, 0), i(1, 1, 1), i(1, 0, 1)),              # internal face
        (i(0, 0, 0), i(1, 0, 0), i(1, 0, 1), i(0, 0, 1)),              # bottom, cell 0 (2.0 mm)
        (i(1, 0, 0), i(2, 0, 0), i(2, 0, 1), i(1, 0, 1)),              # bottom, cell 1 (2.5 mm)
        (i(0, 1, 0), i(0, 1, 1), i(1, 1, 1), i(1, 1, 0)),              # top
        (i(1, 1, 0), i(1, 1, 1), i(2, 1, 1), i(2, 1, 0)),
    ]
    _write(d, "points", "vectorField", f"{len(pts)}\n(\n" + "\n".join(f"({x!r} {y!r} {z!r})" for x, y, z in pts)
           + "\n)\n")
    _write(d, "faces", "faceList", f"{len(faces)}\n(\n" + "\n".join(f"4({' '.join(map(str, f))})" for f in faces)
           + "\n)\n")
    _write(d, "boundary", "polyBoundaryMesh", "2\n(\n    bottom\n    {\n        type wall;\n        nFaces 2;\n"
           "        startFace 1;\n    }\n    top\n    {\n        type wall;\n        nFaces 2;\n        startFace 3;\n"
           "    }\n)\n")
    a = patch_face_areas(d, "bottom")
    assert a == pytest.approx(np.array([2.0e-3 * dz, 2.5e-3 * dz]), rel=1e-12)
    assert patch_face_areas(d, "top").sum() == pytest.approx(4.5e-3 * dz, rel=1e-12)
    with pytest.raises(ValueError):
        patch_face_areas(d, "walls")

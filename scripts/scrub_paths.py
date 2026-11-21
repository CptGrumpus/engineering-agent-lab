"""Redact personal paths from run folders before they are committed.

    python scripts/scrub_paths.py                 # every folder under runs/
    python scripts/scrub_paths.py runs/<run_id>   # one run

Solver logs (OpenFOAM, Gmsh, FreeCAD, OpenModelica) print absolute paths that include the
Windows user name. This replaces the repository root with <repo> and the home folder with ~,
and deletes stray __pycache__ folders. Results are not touched. tests/test_privacy.py fails if
a committed file still contains a personal path.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from harness.privacy import REPO, scrub_tree  # noqa: E402


def main(argv: list[str]) -> int:
    targets = [Path(a) for a in argv] or [REPO / "runs"]
    for t in targets:
        r = scrub_tree(t.resolve())
        print(f"{t}: {r['files_redacted']} files redacted, {r['pycache_removed']} __pycache__ folders removed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

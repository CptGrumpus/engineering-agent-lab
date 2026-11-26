"""List every failed point in the runs and mark those missing from FAILURES.md.

Usage: python scripts/list_failures.py [--all]   (default: committed runs only; --all includes uncommitted run dirs)
Exit code 1 when a run with a failed point is not in FAILURES.md (tests/test_failures_ledger.py checks the same).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def failed_points(include_uncommitted: bool = False) -> list[dict]:
    if include_uncommitted:
        files = sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in ROOT.glob("runs/*/points/*/point.json"))
    else:
        files = subprocess.run(["git", "ls-files", "runs/*/points/*/point.json"], cwd=ROOT, capture_output=True,
                               text=True, check=True).stdout.split()
    out = []
    for f in files:
        p = json.loads((ROOT / f).read_text(encoding="utf-8"))
        if p.get("status") != "completed":
            msg = (p.get("solver") or {}).get("message") or p.get("error") or ""
            out.append({"run": f.split("/")[1], "point": p.get("label"), "message": " ".join(msg.split())[:160]})
    return out


def main(argv) -> int:
    ledger = (ROOT / "FAILURES.md").read_text(encoding="utf-8")
    rows = failed_points("--all" in argv)
    missing = sorted({r["run"] for r in rows if r["run"] not in ledger})
    for r in rows:
        mark = "MISSING" if r["run"] in missing else "listed "
        print(f"{mark}  {r['run']}  {r['point']}  {r['message']}")
    print(f"{len(rows)} failed points in {len({r['run'] for r in rows})} runs; {len(missing)} runs not in FAILURES.md")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

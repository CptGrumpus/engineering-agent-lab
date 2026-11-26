"""Every committed run with a failed point is recorded in FAILURES.md (software, what happened, cause, status)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from list_failures import ROOT, failed_points  # noqa: E402


def test_every_failed_run_is_in_the_ledger():
    ledger = (ROOT / "FAILURES.md").read_text(encoding="utf-8")
    missing = sorted({r["run"] for r in failed_points() if r["run"] not in ledger})
    assert not missing, f"add these runs to FAILURES.md: {missing}"

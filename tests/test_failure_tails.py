"""A failed point keeps the end of every solver log the study did not copy, before its work dir is deleted."""
from pathlib import Path

from harness.run import TAIL_LINES, keep_failure_tails


def test_failure_tails_keep_uncopied_logs_only(tmp_path):
    work = tmp_path / "work"
    (work / "fluid").mkdir(parents=True)
    big = work / "fluid" / "log.pimpleFoam"
    big.write_text("".join(f"Time = {i}\n" for i in range(5000)) + "Floating point exception\n", encoding="utf-8")
    copied = work / "solid.log"
    copied.write_text("copied in full\n", encoding="utf-8")
    own = work / "log.ccx"
    own.write_text("x\n", encoding="utf-8")
    (work / "log.ccx.tail").write_text("x\n", encoding="utf-8")        # the study kept its own tail
    (work / "field.vtk").write_text("not a log\n", encoding="utf-8")
    dest = tmp_path / "tails"
    kept = keep_failure_tails(work, {copied, work / "log.ccx.tail"}, dest)
    assert kept == ["fluid/log.pimpleFoam"]
    text = (dest / "fluid" / "log.pimpleFoam.tail").read_text(encoding="utf-8").splitlines()
    assert text[-1] == "Floating point exception"
    assert len(text) == TAIL_LINES + 1                                  # header line plus the tail
    assert text[1] == f"Time = {5000 - TAIL_LINES + 1}"


def test_failure_tails_missing_work_dir(tmp_path):
    assert keep_failure_tails(tmp_path / "gone", set(), tmp_path / "tails") == []

"""Guards on the study records (quick wins from REPO_AUDIT.md, 2026-11-26).

1. A case file's settings must still equal the `inputs/case.toml` its latest committed run saved: a case header
   gets its Results block after the run, and an edit there must never change what was run (comments are free).
2. Every registered model is in the README's study table (five were missing on 2026-11-25).
"""
import subprocess
import tomllib
from pathlib import Path

from harness import registry

ROOT = Path(__file__).resolve().parent.parent


def _latest_committed_inputs() -> dict[str, Path]:
    out = subprocess.run(["git", "ls-files", "runs/*/inputs/case.toml"], cwd=ROOT, capture_output=True, text=True,
                         check=True).stdout.split()
    latest = {}
    for f in sorted(out):                                   # run ids start with the time stamp: last one wins
        path = ROOT / f
        latest[tomllib.loads(path.read_text(encoding="utf-8"))["case"]["name"]] = path
    return latest


def test_case_files_match_their_latest_committed_run():
    latest = _latest_committed_inputs()
    compared, differ = 0, []
    for case in sorted((ROOT / "cases").glob("*.toml")):
        data = tomllib.loads(case.read_text(encoding="utf-8"))
        run_inputs = latest.get(data["case"]["name"])
        if run_inputs is None:                              # not run yet, or its run is not committed
            continue
        compared += 1
        if tomllib.loads(run_inputs.read_text(encoding="utf-8")) != data:
            differ.append(f"{case.name} != {run_inputs.relative_to(ROOT)}")
    assert compared > 200, compared
    assert not differ, "case settings changed after the run (start a new case or revision instead):\n" + "\n".join(differ)


def test_every_registered_model_is_in_the_readme():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    missing = [m for m in sorted(registry.models()) if f"`{m}`" not in readme]
    assert not missing, f"add these models to the README's study table: {missing}"

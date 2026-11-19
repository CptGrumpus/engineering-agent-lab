"""Command-line entry point.

    python -m harness run      cases/msd_step.toml     # simulate, save evidence
    python -m harness verify   runs/<run_id>           # independent checks
    python -m harness report   runs/<run_id>           # requirements report
    python -m harness pipeline cases/msd_step.toml     # run + verify + report
    python -m harness rerun    runs/<run_id>           # reproduce from saved inputs
    python -m harness compare  runs/<run_id> runs/<other_run_id>   # cross-tool check

Exit code: 0 when the step completed and every check passed; 1 when the step
completed but something failed (simulation, check, or reproducibility);
2 for usage or input errors.
"""

from __future__ import annotations

import argparse
import sys

from harness.case import CaseError


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m harness")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, target in (("run", "case"), ("pipeline", "case"),
                         ("verify", "run_dir"), ("report", "run_dir"), ("rerun", "run_dir")):
        sp = sub.add_parser(name)
        sp.add_argument(target)
        if target == "case":
            sp.add_argument("--runs-root", default="runs")
    sp = sub.add_parser("compare")
    sp.add_argument("run_dir")
    sp.add_argument("against_dir")
    args = ap.parse_args(argv)

    from harness.compare import compare_runs
    from harness.report import build_report
    from harness.rerun import rerun
    from harness.run import run_case
    from harness.runio import read_json
    from harness.verify import verify_run

    try:
        if args.cmd == "run":
            run_dir = run_case(args.case, args.runs_root)
            print(f"RUN_DIR {run_dir.as_posix()}")
            return 0 if read_json(run_dir / "manifest.json")["status"] == "completed" else 1
        if args.cmd == "verify":
            summary = verify_run(args.run_dir)
            print(f"VERIFICATION {summary['status']}")
            return 0 if summary["status"] == "PASS" else 1
        if args.cmd == "report":
            out = build_report(args.run_dir)
            print(f"REPORT {out.as_posix()}")
            return 0
        if args.cmd == "pipeline":
            run_dir = run_case(args.case, args.runs_root)
            summary = verify_run(run_dir)
            out = build_report(run_dir)
            print(f"RUN_DIR {run_dir.as_posix()}")
            print(f"VERIFICATION {summary['status']}")
            print(f"REPORT {out.as_posix()}")
            return 0 if summary["status"] == "PASS" else 1
        if args.cmd == "compare":
            result = compare_runs(args.run_dir, args.against_dir)
            for pt in result["points"]:
                print(f"{pt['label']}: {pt['status']}  max_rel_diff "
                      f"{pt.get('max_rel_diff', float('nan')):.3e}  tol {result['tolerance']:.0e}")
            print(f"CROSS_CHECK {result['status']}")
            return 0 if result["status"] == "PASS" else 1
        if args.cmd == "rerun":
            new_dir, result = rerun(args.run_dir)
            print(f"RUN_DIR {new_dir.as_posix()}")
            print(f"REPRODUCIBILITY {result['status']}")
            return 0 if result["status"] == "PASS" else 1
    except (CaseError, FileNotFoundError, ValueError) as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())

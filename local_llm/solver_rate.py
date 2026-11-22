"""Measure a running OpenFOAM solver's speed from its log: iterations and simulated time per wall minute.

Usage: python local_llm/solver_rate.py <log.pimpleFoam> [window_s=120] [label]
Counts 'ExecutionTime' lines (one per solver iteration, coupling sub-iterations included) appended during
the window, and the simulated time advanced ('Time = ...'). Prints one JSON line; append it to the ledger
to pair with LLM runs (PLAN.md O8).
"""
import datetime
import json
import os
import re
import sys
import time


def main(log, window=120.0, label=""):
    start_size = os.path.getsize(log)
    with open(log, "rb") as f:
        f.seek(max(0, start_size - 20000))
        times = re.findall(rb"^Time = ([0-9.eE+-]+)", f.read(), re.M)
    t0 = float(times[-1]) if times else None
    started = datetime.datetime.now()
    time.sleep(window)
    with open(log, "rb") as f:
        f.seek(start_size)
        new = f.read()
    iters = len(re.findall(rb"^ExecutionTime", new, re.M))
    times = re.findall(rb"^Time = ([0-9.eE+-]+)", new, re.M)
    t1 = float(times[-1]) if times else t0
    print(json.dumps({
        "time": started.isoformat(timespec="seconds"), "label": label, "test": "solver_rate",
        "window_s": window, "iters_per_min": round(iters * 60 / window, 2),
        "sim_s_per_min": round((t1 - t0) * 60 / window, 5) if t0 is not None else None,
        "sim_time_start": t0, "sim_time_end": t1,
        "log": log.replace("\\", "/").replace(os.path.expanduser("~").replace("\\", "/"), "~"),
    }))


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    main(a[0], float(a[1]) if len(a) > 1 else 120.0, a[2] if len(a) > 2 else "")

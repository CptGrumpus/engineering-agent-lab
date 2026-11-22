# Results

| Date | Variant | Model | Score (weighted) | Notes |
|---|---|---|---|---|
| 2026-11-22 | with skills | Opus 5.5 (general-purpose agent with the skill-eval-runner instructions; the runner agent was not loaded in that session) | 8 / 8: all six graders pass | Did not confirm 1 %; traced the 0.9 % to the 80-cell point (mesh error about -3.3 % cancelling a +2.4 % model error); gave the converged value as +2.4 % above Prandtl with GCI 1.05 % (just over its 1 % limit); cited the correlation's +-2 % scatter, the sublayer-resolved condition and the wall functions' -5 %; named run 20261122-153857. Recommended "within about 2.5 %, budget +-5 %". No new simulation (it re-ran `harness verify` on three runs in its worktree and wrote an independent six-correlation check). Grading by the parent session against graders/. No baseline run yet. |

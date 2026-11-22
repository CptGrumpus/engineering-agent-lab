# Local LLM optimisation: plan and experiment log

Goal: make Inkling 2 Mini fast enough to be useful in this repo's workflow, ideally for workflow planning
(drafts a human or Claude reviews), while it shares the machine with CPU-heavy solver runs.

**Value check (2026-11-21).** The user is on a flat Claude subscription, so "saving" means stretching
usage limits. An audit of this project's Claude Code sessions found that input is 99% re-sent context and
driven by session length (calls over 400k context = 66% of input). Solver logs and run output together
are only ~5% of input. So pre-reading by the local model can save at most ~5%; the big lever was earlier
compaction and clearing (auto-compact set to 300k, handoff rule in CLAUDE.md). The local model's case
rests on offline batch work that doesn't touch the limits, planning drafts if O10 shows they're good,
and the portfolio value of this log.

## Key learnings (2026-11-21)

The log below has the evidence; this is the distilled version.

1. **Check what hardware the engine actually sees before tuning anything.** The Unsloth build lacked
   CUDA runtime DLLs and silently ran CPU-only; `-ngl 99` did nothing. `llama-bench --list-devices`
   would have caught it in one second. The first trial's speed numbers measured a broken setup.
2. **Read the model's structure; it predicts which levers work.** A stdlib GGUF header parser showed the
   looped core (blocks 6-17 run 3× per token). Putting those experts on the GPU gave +30% generation,
   about double the standard last-layers option. Generic advice would have missed it.
3. **Prompt reading is limited by the PCIe copy of experts per micro-batch.** Bigger micro-batches
   amortise it: `-ub 2048` took prompt reading from 22 to ~490 tok/s. 4096 got slower (VRAM pressure).
4. **Generation is memory-bound, not core-bound.** Speed was flat from 3 to 12 threads (~9.3 tok/s), so
   extra threads only steal cores from solvers.
5. **To share the machine, separate the jobs and measure both sides.** Pinning the LLM to CCD 2 at low
   priority cost a ~2-core solver 10%, against 26% unpinned, with no loss to the LLM. Measure the
   solver's speed too (`solver_rate.py`), not only tok/s.
6. **Check the value before building the integration.** The token audit showed local pre-reading could
   save at most ~5% of Claude usage, while session length drove 66%. The cheapest, biggest win was a
   setting (`autoCompactWindow` 300k) plus a habit (frequent handoffs and `/clear`), not new software.
7. **Measurement hygiene:** interleave controls (control, candidate, control). Record host state with
   every run. Relabel a run that went wrong rather than deleting it (the failed "pinned" window became
   control 2). Keep home-folder paths out of committed logs.

Method: from [inference-optimisation-skill](https://github.com/sybil-solutions/inference-optimisation-skill)
(MIT), followed by hand, not installed:
- compute the ceiling first ([THEORY.md](THEORY.md));
- change one thing per experiment;
- record every run, failures included, in [ledger.jsonl](ledger.jsonl) via [bench.ps1](bench.ps1);
- check output quality before calling a config "best".

Machine: Ryzen 9 5900X (2 CCDs × 6 cores), 64 GB DDR4 running at 2666 (kit rated 3200), RTX 3070 8 GB
on PCIe 4.0 x16, Windows 11, driver 621.14. Engine: Unsloth llama.cpp b12588-mix (needed for this
model's looped GGUF layout). Model: `unsloth/Inkling-2-Mini-GGUF:UD-Q4_K_M` (16.6 GB).

## Action items

Status: `todo`, `doing`, `done`, `rejected`, or `blocked (reason)`.

| # | Item | Status | Result / note |
|---|---|---|---|
| O1 | Ceiling from the GGUF tensor table | done | ~17 tok/s decode with all experts in RAM; see THEORY.md |
| O2 | Find out why the GPU wasn't used | done | CUDA runtime DLLs missing; fixed per process with PATH, see log 2026-11-21 |
| O3 | Idle baseline with the GPU on: prompt reading at 512/2K/8K, generation | todo | needs FSI1 finished; everything below so far was measured with FSI1 running |
| O4 | Thread count and CCD pinning sweep (`-t`, `-C`) | done (with FSI1 running) | flat from 3 to 12 threads (~9.2 tok/s); pinning to CCD 2 is what matters. Recheck idle in O3 |
| O5 | Batch sizes for prompt reading (`-b`, `-ub`) | done | `-ub 2048`: ~490 tok/s at 2K prompt (22 before). 4096 is slower, probably VRAM pressure |
| O6 | Experts on the GPU: last layers (`-ncmoe`) vs looped core layers (`-ot`) | doing | core blocks 6-9: +30% generation; last 4 blocks: +16%. But peak VRAM 7.8 GB of 8: too tight. Next: fewer blocks or `-ub 1024` |
| O7 | Flash attention and KV cache type | todo | |
| O8 | Contention: LLM speed with a solver running, and solver speed with the LLM running | doing | pinned LLM costs FSI1 ~10%, unpinned 10-thread ~26%. One window per condition; repeat with t=3 and with a multi-core solver |
| O9 | Long-context check: needle retrieval at ~50% and ~100% of the working context | todo | gate before any config is "best" |
| O10 | Planning retest at medium/high effort, with the repo's process rules in the prompt | todo | the original goal; repeat the mesh-study and inlet-diagnosis tasks from the first trial |
| O11 | RAM at its rated 3200 (XMP in the BIOS) | blocked (user's call, BIOS change) | ~20% more RAM bandwidth for the LLM and the solvers |
| O12 | Wire it into the repo: `harness/local_llm.py`, a run lock/queue so it doesn't collide with studies | todo | after O8 says how to run it alongside |
| O13 | Speculative decoding (draft model or n-gram) | todo | low priority; often loses when bandwidth-bound |

## Log

### 2026-11-21

- **O1 ceiling.** Read the GGUF header with a stdlib parser. 24 stored blocks, blocks 6-17 looped 3×,
  so 48 layer passes per token; 128 experts, top-8; experts 14.8 GB of 16.6. Decode ceiling ~17 tok/s
  with all experts in RAM. See THEORY.md.
- **O2 the GPU was never used.** `llama-bench --list-devices` showed no devices. `ggml-cuda.dll` imports
  `cudart64_12`, `cublas64_12` and `cublasLt64_12`, which the Unsloth zip doesn't include and Windows
  didn't report as missing. The mainline b12608 folder has them (CUDA 12.4 runtime). Putting that
  folder first on PATH for the process makes CUDA0 appear. No files were copied. **Every earlier
  number (4.4 tok/s generating, 22 tok/s prompt) was CPU-only, with `-ngl 99` doing nothing.**
- **First GPU run** (single run, not controlled; FSI1 using ~2 cores; 6 threads on CCD 2, low
  priority, all experts on CPU): prompt 512 at 206 tok/s, generation at 8.9 tok/s. 9.4× and 2× the old
  numbers.
- **Tooling.** `bench.ps1` wraps llama-bench: adds the CUDA runtime path, records host state (CPU load,
  solver processes in WSL, peak VRAM) and appends to `ledger.jsonl`. `solver_rate.py` measures a running
  OpenFOAM solver's iterations per minute from its log.
- **O8 contention** (FSI1 = pimpleFoam + CalculiX via preCICE, ~2 cores; solver probe windows 100-120 s):

  | FSI1 condition | iterations/min | vs controls |
  |---|---:|---:|
  | alone, 4 controls interleaved (290.5, 298.2, 302.4, 295.2) | mean 296.6 | |
  | LLM on CCD 2 (`-C 0xFFF000`), 6 threads, `--prio -1` | 267.0 | −10% |
  | LLM unpinned, 10 threads, normal priority (the original setup) | 219.6 | −26% |

  LLM side in the same windows: pinned 230 / 8.35 tok/s (prompt / generation), unpinned 214 / 8.06. Pinning
  is better for both. One window per condition so far.
  Mistake on the way: the first "LLM pinned" window ran without the LLM (`powershell -File` mangled an array
  argument), so it became control 2. `bench.ps1` now takes the llama-bench arguments as one string.
- **O5 micro-batch** (prompt 2048, pinned, FSI1 running): `-ub` 512 → 235, 1024 → 349, 2048 → 494 tok/s,
  nearly linear, as expected if each micro-batch pays one PCIe copy of the experts. At prompt 4096:
  `-ub` 2048 → 445, 4096 → 281 (slower; likely VRAM pressure, unconfirmed). **Keep `-ub 2048`.**
- **O6 expert placement** (`-ub 2048`, prompt 2048 / gen 128, 4 reps, interleaved):

  | config | generation tok/s | prompt tok/s | peak VRAM (whole GPU) |
  |---|---:|---:|---:|
  | all experts CPU (run 1 / run 2) | 7.44 / 8.34 | 500 / 487 | 7.1 / 5.7 GB |
  | `-ot blk\.[6-9]\.ffn_.*_exps=CUDA0` (looped core) | **10.27** | 535 | 7.8 GB |
  | `-ncmoe 20` (last 4 blocks) | 9.14 | 506 | 7.95 GB |

  Core placement beats last-block placement, as THEORY.md predicted (about 2× the gain per GB here, not
  3×). The VRAM peak is too close to 8 GB for daily use with a desktop running.
- **O4 threads** (CCD 2, core blocks on GPU, gen 64): t=3 9.17, 4 8.30, 6 9.31, 8 9.24, 12 9.34 tok/s.
  Flat, so generation isn't compute-bound. Effective RAM traffic is only ~13 GB/s (1.39 GB/token × 9.3),
  well under the ~34 GB/s ceiling, which points at per-layer CPU↔GPU handoff latency (48 passes per token)
  or the FSI1 run sharing bandwidth. The idle run (O3) will separate the two. **For running beside
  studies, use 3-4 threads.**

**Best so far, alongside a solver:** `-ngl 99 -ub 2048 -t 4 -C 0xFFF000 --prio -1` + core experts on GPU
(VRAM-tight) → ~490 tok/s prompt (22×), ~9-10 tok/s generation (2.1-2.3×), solver cost ~10%.

## Next session

Handoff written 2026-11-21 23:16.

1. **Running jobs:** none from this workstream. No llama-server is running and the GPU is free. FSI1
   (study 6, another workstream) is still running: check with `wsl -e pgrep -a pimpleFoam`; expected
   done about 03:00-03:30. Don't run the idle baseline (O3) until it has finished.
2. **When FSI1 finishes:** run O3 idle, with interleaved repeats, e.g.
   `.\local_llm\bench.ps1 -Label "O3 idle best" -BenchArgs "-t 4 -C 0xFFF000 -ub 2048 -p 512,2048,8192 -n 128 -r 5 -ot blk\.[6-9]\.ffn_.*_exps=CUDA0 -ncmoe 99"`,
   plus the same with `-ncmoe 99` alone and `-t 3,6,12`. Compare with the contended numbers above.
3. **Decisions this session:** pin the LLM to CCD 2 at low priority when it runs beside solvers (22:00);
   flat subscription, so judge it on usage limits (22:50); `autoCompactWindow` 300000 in the user's
   settings and a handoff rule in CLAUDE.md (23:15). Open question for the user: XMP (O11).
4. **Uncommitted:** none from this workstream after this commit.
5. **Next steps, in order:** O3 → O6 (fit core experts in less VRAM: blocks 6-8 only, or `-ub 1024`)
   → O7 (flash attention) → O9 (needle check) → O10 (planning retest) → O8 (contention with a
   multi-core solver) → O12 (wiring) only if O10 is worth it.

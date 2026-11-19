# Engineering skills

Executable skills live in [.claude/skills/](../.claude/skills/), where Claude Code discovers them
automatically. This file tracks the skill plan and the standard each skill must meet.

## Status

| Skill | Status | Location |
|---|---|---|
| Requirements and assumptions | Partial: captured in the case file (`assumptions`, `[[requirements]]`, `[verification]`). No interactive elicitation skill yet. | `cases/*.toml` |
| Model preparation | Not built. Only a hand-written model exists (`models/msd.py`). | - |
| Simulation execution | **Built** | [run-case](../.claude/skills/run-case/SKILL.md) |
| Verification and evidence | **Built** | [verify-against-reference](../.claude/skills/verify-against-reference/SKILL.md) |
| Engineering review report | **Built** | [requirements-report](../.claude/skills/requirements-report/SKILL.md) |

All built skills support model `msd` (Python + SciPy) only.

## Requirements and assumptions

Capture inputs with units, operating conditions, constraints, missing information, and measurable acceptance criteria. Identify assumptions that need human review.

## Model preparation

Create or modify geometry, equations, material definitions, loads, and boundary conditions through documented tool interfaces. Save the source and check that it represents the intended case.

## Simulation execution

Record tool versions, inputs, numerical settings, execution status, and logs. Preserve failed runs as useful diagnostic evidence. Make the procedure repeatable without relying on an agent's conversational memory.

## Verification and evidence

Apply relevant independent checks: analytical references, benchmark comparisons, conservation, reaction balance, mesh or time-step convergence, and sensitivity to assumptions. A solver success message or plausible plot is insufficient on its own.

## Engineering review report

Connect each requirement to a result, check, and evidence file. State failures, uncertainty, and what remains unvalidated. Leave engineering acceptance to human review.

## Definition of a useful skill

Each eventual skill should identify its purpose, required inputs, supported tool/version, execution procedure, expected artifacts, meaningful checks, failure handling, and when human judgment is needed.

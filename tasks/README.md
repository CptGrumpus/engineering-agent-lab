# Engineering evaluation tasks

Tasks in the style of an AI-training pipeline: each one asks a model (or an engineer) to
turn physical requirements into a model, solve it, and judge whether the result meets
the constraints. Every task is built from a verified study in this repository, so its
reference answer has independent evidence behind it.

Each task folder holds:

| File | Purpose |
|---|---|
| `task.md` | The problem as the solver receives it, with the required answer format (JSON) |
| `solution.md` | The reference solution, its method, the evidence behind it, and the traps the task is designed to expose |
| `grader.py` | `grade(answer: dict) -> dict`: scores a submitted answer criterion by criterion |

The graders are verified like the models: `tests/test_tasks.py` checks that each grader
gives the reference answer full marks and fails every documented trap answer on the
criterion that trap should break. A grader that passes a wrong answer is a bug.

| Task | Discipline | What it tests | Built from |
|---|---|---|---|
| [hertz_roller_contact](hertz_roller_contact/task.md) | Contact mechanics | Line-contact Hertz with the combined modulus, subsurface shear | [study 10](../portfolio/10-roller-contact.md) |
| [heated_channel_wall_temperature](heated_channel_wall_temperature/task.md) | Heat transfer | Thermal entry vs fully developed flow, the right Nusselt number | [study 11](../portfolio/11-cold-plate-heat-transfer.md) |
| [cantilever_root_stress](cantilever_root_stress/task.md) | Structural FEA | Telling a mesh singularity from a real stress | [study 1](../portfolio/01-cantilever-bracket.md) |
| [sagging_strip_clearance](sagging_strip_clearance/task.md) | Structural, large deflection | Plane strain for a wide strip, and geometric nonlinearity: either trap alone flips the clearance verdict | study 6, solid stage ([draft](../portfolio/17-fsi-flag-turek-hron.md)) |

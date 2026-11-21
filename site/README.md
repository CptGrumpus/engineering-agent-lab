# Published portfolio page

Source of the published portfolio page (a private claude.ai artifact).

- `index.html`: the page as published. It references `v2/*` (renders, thumbnails, response plots) and `img/*` (the figures in `portfolio/img` and the run folders).
- `build_v2.py`: builds `index.html` from `v2_template.html` (layout, hero, viewport, method, gallery, agent workflow, tasks, lessons, footer), `featured.html` (the featured study, the optimiser, shown right after the viewer), `studies.html` (the other eleven study write-ups, each turned into a collapsible panel at build time) and `extras.py`. It reads the real pipeline output for the terminal panel from the lift-off run log.
- `extras.py`: the short summary at the top (code size and test count read from the repository), the requirements table, the capabilities table, and the interactive grader demo. The demo's criteria are read from `tasks/*/grader.py`, every preset answer is graded by the Python grader, and the build fails unless the page's JavaScript grader agrees with the Python graders on every preset and on random answers (needs `node`).
- `make_assets.py`: builds the viewport renders and gallery thumbnails from the Blender passes in `build/render/` (run `scripts/make_renders.py` first).
- `index_v1.html`, `contact_section.html`, `heat_section.html`: earlier sources, superseded by `studies.html` and kept for reference only.

The scripts expect to sit together in one folder with `v2/` beside them; the repository and render paths are set at the top of each.

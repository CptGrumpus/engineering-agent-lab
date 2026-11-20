# Published portfolio page

Source of the published portfolio page (a private claude.ai artifact).

- `index.html`: the page as published. It references `v2/*` (renders, thumbnails) and `img/*` (the figures in `portfolio/img` and the run folders).
- `build_v2.py`: assembles `index.html` from `v2_template.html` (layout, hero viewport, method, gallery, agent workflow, findings), the case-study sections in `index_v1.html`, and `contact_section.html`. It reads the real pipeline output for the terminal panel from the lift-off run log.
- `make_assets.py`: builds the viewport renders and gallery thumbnails from the Blender passes in `build/render/` (run `scripts/make_renders.py` first).

The scripts expect to sit together in one folder with `v2/` beside them; the repository and render paths are set at the top of each.

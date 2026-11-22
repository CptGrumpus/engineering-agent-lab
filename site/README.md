# Published portfolio site

Source of the portfolio site, published at https://cptgrumpus.github.io/engineering-agent-lab/ (served from `docs/`).

To rebuild after a change:

    .venv\Scripts\python.exe site\build_v2.py      # writes the pages and assets into docs/
    .venv\Scripts\python.exe site\export_docs.py   # copies every referenced image into docs/, fails if one is missing
    .venv\Scripts\python.exe site\check_viewer3d.py  # 3D view checks and script errors, every page, headless Chrome

## Pages

| Page | Built from |
|---|---|
| `index.html`, the home page: intro, a viewer with five highlighted results, the gallery of study cards, links to the other pages | `pages/home.html` |
| One page per gallery card (16): the result viewer, an "at a glance" side panel with the requirements, the write-up, the case file's record, evidence links, previous/next | `studies/<key>.html`, one hand-written file per study |
| `how-i-work.html`: the method, the agent's skills, capabilities, how the images are checked, lessons | `pages/how.html` |
| `grading.html`: the interactive grader demo | `pages/grading.html`, `extras.py` |
| `in-progress.html`: the studies still running | `pages/progress.html` |
| `requirements.html`: every requirement in one table | `extras.REQS` |

Every page shares `pages/layout.html` (head, top menu, contact footer) and `assets/site.css`, `assets/site.js`. Pages with a result viewer add `pages/viewer.html`, `assets/viewer.js` and, where a result has a 3D mesh, `assets/viewer3d.js`.

## How it fits together

- `build_v2.py` holds the site's data: `VP` (one viewer entry per study), `CARDS` (one gallery entry per study), `GROUPS` (studies of the same part shown as one card and one page, each study a part of it), `SLUG` (page file names), `CASES` (the case files whose recorded assumptions, limits and inputs are shown on each study's page) and `HIGHLIGHTS` (the results in the home page's viewer).
- A study's write-up is `studies/<key>.html`: a `<section class="study">` with a label, a title and a body whose sections are `<h3>` headings (The question, The answer, Why it matters, The model, How it works, How I checked it, What I caught along the way, Limits). `{{CASE}}` in the body marks where the case file's record goes. On a single-study page the headings become `<h2>`; in a report they stay `<h3>` under each part's title. Each heading gets an id, and the page's contents list is built from them.
- Links are written as `href="#key"` anywhere in the sources, where `key` is a study or an old section name. The build turns each into the right page address (`STUDY_URL`, `SECTION_URL`) unless the id is on the same page. It fails on a link to an id or page that doesn't exist, on a duplicate id, and on an unbalanced brace in the stylesheet.
- Old addresses keep working: `index.html#bolted_joint`, `#tasks` and the like forward to the page that now holds them (`window.LEGACY`, read by `site.js`).
- Asset links carry a hash of the stylesheet and scripts (`?v=...`), so a change shows up without a hard refresh.
- `extras.py`: the requirements (`REQS`), the capabilities table, the evidence links for each study (its write-up and run reports on GitHub; only committed files are linked), the repository counts, and the grader demo. The demo's criteria are read from `tasks/*/grader.py`, every preset answer is graded by the Python grader, and the build fails unless the page's JavaScript grader agrees with the Python graders on every preset and on random answers (needs `node`).
- `make_og.py`: the link preview cards (1200 × 630). `v2/og_card.png` for the home page, and `v2/og_<page>.png` for each study, so a link to one study previews as that study.
- `make_mesh3d.py`, `assets/viewer3d.js`: the interactive 3D view. `make_mesh3d.py` writes `v2/m3d_<id>.bin` from the same surfaces and fields the Blender renders use (`build/render/`) and reads each file back against its source; `v2/m3d.json` indexes them so the site builds without `build/`. `viewer3d.js` is plain WebGL2: the field is banded per pixel as the render's shader does, with the legend's colours.
- `check_viewer3d.py` (with `check_viewer3d.mjs`): opens every page of the built site in headless Chrome (the list is `docs/pages.json`), fails on any script error, and holds each 3D view to the renders' own checks from four angles: unlit pixels on the legend (99.5 %) and the lit view reading as the right band (2 %).
- Load-step frames: `scripts/make_study_renders.py --frames` renders a study at each load step for the viewer's slider (`v2/fr_<study>_*.webp`, indexed in `v2/frames.json`); every frame passes the render checks. `make_thumb_loops.py` builds the gallery's looping thumbnails from them.
- `make_assets.py`: builds the viewport renders and gallery thumbnails from the Blender passes in `build/render/` (run `scripts/make_renders.py` first).
- `index_v1.html`, `contact_section.html`, `heat_section.html`: earlier sources, kept for reference only.

The scripts expect to sit together in this folder with `v2/`, `pages/`, `studies/` and `assets/` beside them; the repository and render paths are set at the top of each.

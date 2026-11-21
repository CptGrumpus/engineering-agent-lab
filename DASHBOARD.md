# Dashboard backlog

Open work on the portfolio dashboard. Two items are open, and both follow the other studies. Studies themselves are tracked in [BACKLOG.md](BACKLOG.md).

## Where the dashboard lives

Both copies are built from `site/`:

- **Public:** https://cptgrumpus.github.io/engineering-agent-lab/, served from `docs/`. This is the link to give clients.
- **Private:** the claude.ai copy, visible only to me unless shared.

To rebuild after a change: run `site/build_v2.py`, then `site/export_docs.py`, then `site/check_viewer3d.py` (checks the 3D view in headless Chrome), then commit and push. See [site/README.md](site/README.md) for how the page is put together.

## Decisions made

Decided 2026-11-21:

- **Contact:** an email button only. No name on the page and no LinkedIn yet; LinkedIn can be added once my profile is updated.
- **Services:** no services list. The page showcases the work and ends with a simple contact section, so people can ask for whatever they need. One line says I'm available for remote contract work.

## Biggest impact

| # | Item | What it involves | Needs from me | Status |
|---|---|---|---|---|
| 1 | Contact section | A closing section with an email button, plus a Contact button in the top bar | Nothing | Done. The address is stored encoded and only decoded when someone clicks, to keep it away from scrapers |
| 2 | Evidence links | Each study ends with links to its write-up and run reports on the public repo. Only committed files are linked, so study 12's links appear by themselves once its runs are committed | Nothing | Done for studies 1 to 11 |
| 3 | Services section | A short "what I can do for you" block listing the offers | Nothing | Dropped. I decided to let the work speak for itself and keep only the contact section |
| 4 | Link preview card | Open Graph card (1200 × 630) from the optimised bracket render, with the counts from the run records | Nothing | Done |

## Polish and quality

| # | Item | What it involves | Status |
|---|---|---|---|
| 5 | Light mode and phone check | Full review at 360, 390, 768 and 1280 px in light and dark, with every panel open | Done. Fixed three overflows and a clipped phone menu |
| 6 | Faster loading | GIF animations to WebP | Done. Lossless, identical frames and timing; 2.71 MB down to 1.94 MB, not the half I'd guessed, because the GIFs are dithered |
| 7 | Sample deliverable link | Link the coolant-channel client memo | Done, from the summary and from study 5 |
| 8 | Render legibility check | Check that the lit image reads as the right colour band | Done. Caught the fin render (2.28 % misread against a 2 % limit); re-lit, now 0 % |

## Larger items and ones that follow the studies

| # | Item | What it involves | Waits on | Status |
|---|---|---|---|---|
| 9 | New studies on the page | The cold-plate thermal chain, buckling, strap proof load and the 3D clevis each get a viewer tab, a gallery card, a write-up and visuals, using the same pipeline as study 12 (`scripts/make_clevis_visuals.py`) | Nothing now: studies 1 to 5 were committed on 2026-11-21 | Ready to start. The "Harder studies" section already lists their results and links their write-ups on GitHub. Study 12 already moved to the clevis bracket; the other four use the same route (`scripts/make_clevis_visuals.py` is the newest template) |
| 10 | Heat-transfer wall verdict | Study 11's wall temperature is withheld until a finer mesh shows the peak converging. Once that run passes, flip the verdict on the page | The finer-mesh run | Not started |
| 11 | Interactive 3D viewer | Rotate the parts in the browser | Nothing | Done for five of the seven viewer tabs. The contact close-up and the flow height field stay as images |

## Ideas not yet scheduled

- **3D for the contact and flow tabs.** The contact view is a section close-up and the flow view a height field; both would need their own camera handling.
- **A colour-blind option.** The turbo scale isn't colour-blind safe. A viridis version of the renders and 3D view would help readers who need it.
- **Mesh size on phones.** The fatigue strap's 3D mesh is 905 KB. Fine on Wi-Fi, slow on a weak mobile connection; it could be decimated away from the hole.

## Recently done

| Date | Item | What changed |
|---|---|---|
| 2026-11-21 | Study 12 rebuilt around the clevis bracket | The write-up had moved from the tapered cantilever to a machined clevis, so the featured section, viewer tab, 3D view, gallery card, requirements, lesson and preview card now show the clevis: 372 g, 4 % lighter, 98.3 MPa (98.9 with mesh uncertainty) against 100. New `scripts/make_clevis_visuals.py` renders all 27 candidates and design D from the saved runs (meshes regenerated and matched node for node); every render passed all three checks. New figures: the search animation, before and after, and why the optimiser stalled in mesh noise. The tapered version is credited in the notes with a link to its runs |
| 2026-11-21 | "What's next" brought up to date | Now "Six harder studies: five done, one in progress", with each finished study's result, its check and a link to its write-up, and where the fluid-structure study stands |
| 2026-11-21 | Contact section | "Get in touch" closes the showcase, with an email button and a "show the address" link; a Contact button stays in the top bar at every width. Checked at 360, 390, 768 and 1280 px in light and dark |
| 2026-11-21 | Interactive 3D view | "Rotate in 3D" in the result viewer for five results. Same surface and colour bands as the renders, checked the same way from four angles per tab (100 % on the legend, at most 0.62 % misread). Plain WebGL2, loaded only on request; mouse, touch and keyboard. Also fixed a live bug where the grader's task tabs were wired into the result viewer |
| 2026-11-21 | Render legibility check | Third render check, on the lit image. All 13 published renders and the 33 optimisation renders measured; only the fin failed, and it now passes after raising its ambient light. Closes the open item in the render-results skill |
| 2026-11-21 | Evidence links, preview card, memo link, WebP | Items 2, 4, 6 and 7 above. All 45 GitHub links checked live |
| 2026-11-21 | Phone and light-mode pass | The requirements table pushed the phone page to 786 px wide when opened; a chip and the menu were clipped. Fixed and rechecked at four widths |
| 2026-11-21 | Page reorganised around the optimiser | Study 12 gets its own section right after the viewer (headline numbers, search animation beside the loop steps, before-and-after and stress-along-span figures, what the checks caught, full method on demand), first in the nav. Results now come before process. The eleven other write-ups are collapsible panels that the gallery and lesson links open; the page is 15,700 px instead of 28,200 |
| 2026-11-21 | Study 12 on the dashboard | Viewer opens on the optimised bracket; featured card, write-up, search animation, before-and-after render and stress-along-span chart. Hero counts now come from the run records (1,478 checks, 36 runs) |
| 2026-11-21 | Public site refreshed | `docs/` rebuilt from the new page with `site/export_docs.py` |
| 2026-11-20 | Personal paths removed | Run records and logs no longer carry the Windows user name, commits use the GitHub no-reply address, and a test guards against leaks |
| 2026-11-20 | Plain-language rewrite | All page copy rewritten in a first-person voice |
| 2026-11-20 | Grader demo, requirements table, summary | Live grading of the three evaluation tasks, all requirements in one table, and a short summary at the top |
| 2026-11-20 | Filters fixed | The discipline filters now hide cards; they had never worked |

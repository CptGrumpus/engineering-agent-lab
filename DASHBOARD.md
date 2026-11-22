# Dashboard backlog

Open work on the portfolio dashboard. One item is open, keeping the fluid-structure card current; the rest are ideas. Studies themselves are tracked in [BACKLOG.md](BACKLOG.md).

## Where the dashboard lives

https://cptgrumpus.github.io/engineering-agent-lab/, built from `site/` and served from `docs/`. This is the link to give clients. (An older claude.ai copy exists but isn't kept up to date.)

To rebuild after a change: run `site/build_v2.py`, then `site/export_docs.py`, then `site/check_viewer3d.py` (checks the 3D view in headless Chrome), then commit and push. See [site/README.md](site/README.md) for how the page is put together.

## Decisions made

Decided 2026-11-21:

- **Contact:** an email button only. No name on the page and no LinkedIn yet; LinkedIn can be added once my profile is updated.
- **Services:** no services list. The page showcases the work and ends with a simple contact section, so people can ask for whatever they need. One line says I'm available for remote contract work.

## Biggest impact

| # | Item | What it involves | Needs from me | Status |
|---|---|---|---|---|
| 1 | Contact section | A closing section with an email button, plus a Contact button in the top bar | Nothing | Done. The address is stored encoded and only decoded when someone clicks, to keep it away from scrapers |
| 2 | Evidence links | Each study ends with links to its write-up and run reports on the public repo. Only committed files are linked, so study 12's links appear by themselves once its runs are committed | Nothing | Done for all twelve |
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
| 9 | New studies on the page | Studies 13 to 16 each get a gallery card, a collapsible write-up, requirements rows and checked renders | Nothing | Done 2026-11-21. Viewer tabs for all four; the strut and bolted joint also rotate in 3D |
| 10 | Heat-transfer wall verdict | Study 11's wall temperature was withheld until a finer mesh showed the peak converging | Nothing | Done 2026-11-21: verified at 44.03 °C (uncertainty 0.23 %) and shown as a pass on the card, the write-up and the requirements table |
| 12 | Menu label | The top menu said "Next" for the section now called "Harder studies" | Nothing | Done: now "Harder" |
| 13 | Keep the fluid-structure card current | The flexible-flag card in "Harder studies" describes where study 6 stands; the coupled stage has started since it was written | Study 6's progress (2026-11-21 evening): solid CSM1/CSM2 and fluid CFD1/CFD2 drag verified; the coupled FSI1 prototype matched the benchmark (tip -0.34 %, drag -0.006 %); the FSI1 mesh study and CSM3 r3 finish tonight. Draft write-up: `portfolio/17-fsi-flag-turek-hron.md` (not in the index yet) | Update with item 9, and again when the coupled runs finish |
| 14 | Fourth graded task | `tasks/sagging_strip_clearance` (new 2026-11-21): a sagging strip's clearance, where plane strain and large deflection each flip the verdict. Add it to the grader demo and the tasks list beside the other three | Nothing (grader tested in `tests/test_tasks.py`) | Ready for the page |
| 11 | Interactive 3D viewer | Rotate the parts in the browser | Nothing | Done for five of the seven viewer tabs. The contact close-up and the flow height field stay as images |

## Ideas not yet scheduled

Aim: better visuals and more "wow", without loosening any check. Every new visual still goes through the volume, legend-colour and legibility checks.

- **Scrub through an analysis.** Done for the strut and the strap proof test. The bolted joint's side-load step was considered and left out: the saved run reaches full slip within two of its six increments, so there's only one in-between state to show.
- **Watch the bolted joint slip.** An animation of the side-load step: the stuck region of the interface shrinking until the whole joint slides, next to the load-displacement curve. The contact output is already in the re-solve.
- **Animated mode shapes in 3D.** Done for the modal study's first mode (see below).
- **Before-and-after slider** for the optimised bracket. Done (see below).
- **Load-ramp animations for the gallery,** like the optimiser's search animation: short loops that show the result forming, used as the card thumbnails on hover.
- **Section views.** Cut the bolted joint through its axis to show the pressure cone inside the plates, and the clevis through the lug to show where the stress runs.
- **Study limits that only new analysis can close.** These used to sit in the page footer and now live in each study's own panel. For the study session, if wanted: a frequency-weighted measure of the bump response for study 7 (ISO 2631-1 running rms or vibration dose, with predictions written first); the cold plate with side walls, in 3D, for study 15; and the fin's air-side coefficient from a correlation or an air-side model instead of a given value (study 6 already sweeps it and finds the tip fails only at about 95 W/m²K). Comparison with measured data comes from the motor study, which is in progress.
- **3D for the contact and flow tabs.** The contact view is a section close-up and the flow view a height field; both would need their own camera handling.
- **Lighter meshes for the 3D view.** The fatigue strap (905 KB), and the strap proof test and cold plate (too heavy today), could be decimated away from the regions that matter, so they can rotate too.

## Recently done

| Date | Item | What changed |
|---|---|---|
| 2026-11-22 | Animated mode shape in 3D | In 3D, the bracket arm's first mode swings back and forth ("Animate the mode", pausable; off for reduced-motion users). The 3D file format gained an optional displacement block, flagged in its header and round-trip checked; the static frame is still the checked shape, and the page's 3D check always captures that frame |
| 2026-11-21 | "What these studies don't cover" removed from the footer | Each limit now sits where it applies: study 11 and study 7 got a note in their panels (study 15 already had one, and study 6 states and sweeps its air-side coefficient). The "pending human review" line was a duplicate of the "A person signs off" rule in "How I work". The two general points, made-up parameters and no measured data yet, are said once in "The work" intro, with the motor study as the first comparison against test data. The footer is now the toolchain only |
| 2026-11-21 | Intro rewritten to let the work speak | Headline "Simulation, proof attached." The paragraph opens with three results from the studies (a joint that slips 4 % too early, a strut that buckles at 23 kN, a bracket lightened over 78 designs) and ends by inviting the visitor to pick one and check it. No "I am" sentence. The link preview card and page title carry the same headline |
| 2026-11-21 | Before-and-after wipe for the optimised bracket | The featured section's side-by-side figure is now a wipe: drag across one image from the starting design (387.7 g, 88.9 MPa) to design D (372.0 g, 97.4 MPa). Both rendered with one camera and crop by `scripts/make_clevis_visuals.py --wipe` and both through the three render checks; the legend is built from the render's own bands, with ticks at their true values |
| 2026-11-21 | Load-step slider for the strap proof test | 20 frames through the proof test, loading to 15 kN and back: the hole edge yields after about 9 kN, the yielded zone reaches 1.8 mm (recorded 1.84 mm), and unloading is elastic down to the −77 MPa left behind. One colour scale (−100 to 300 MPa, a band edge at yield) for every frame and for the main render; every frame passes the three render checks (worst misread 0.59 %). The re-solve prints at every increment, so the check is that every line the evidence run printed appears in it, in order, numbers to round-off |
| 2026-11-21 | Load-step slider in the viewer | The strut can be stepped through, or played, from 1 kN to 21.5 kN: 19 load steps from the re-solve, one camera, one crop and one stress scale, each frame through the three render checks (100 % on the legend, 0 % misread). The readout gives the load as a share of buckling, the mid-span movement and the peak stress. Each step's displacement is checked against what the solver printed at that step. Motor card updated with its first verified result |
| 2026-11-21 | Page reorganised: one place per study | Intro (with the old summary box folded in), then "The work": the 16 gallery cards choose what the result viewer shows, and the chosen study's answer and full write-up open right under it. Featured optimiser, lessons, then "How I work" (method, agent and capabilities in one section), grading, "Now working on" (the flexible flag and the motor study) and contact. Menu down to five links plus Contact. Each study used to appear up to five times; the page with every panel open went from 58,900 to 14,600 px. Also fixed: the Contact button jumped to study 10 (two elements shared one id), and the build now fails on duplicate ids, dead links and unbalanced style braces |
| 2026-11-21 | Studies 13 to 16 on the page; study 11 verified; a fourth grading task | Strut buckling, strap proof test, cold-plate chain and bolted joint each have a gallery card, a write-up, requirements rows and a viewer tab. New `scripts/make_study_renders.py` re-solves each recorded deck (adding only output requests), requires the solver's printed results to match the evidence run byte for byte and the headline value read from the new field to match the record, then renders through the three checks. The checks caught four things on the way: a strap render that read as the wrong band (6.3 % misread), a 20-band cold-plate scale too fine to read (5.4 %), an inside-out plate (volume −200 %), and a bolted-joint pressure surface whose volume came out 2.6 % over the clamp force because the solver's nodal contact pressures are extrapolated (the study 10 trap); that view was replaced. Study 11's wall verdict is now a pass. The page says sixteen studies and four grading tasks; the sagging-strip task joined the grading demo, with its traps |
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

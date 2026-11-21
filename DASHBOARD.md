# Dashboard backlog

Open work on the portfolio dashboard. Eleven items are open: six need nothing from me, two wait on a decision about what to show publicly, and three are larger or depend on the other studies. Studies themselves are tracked in [BACKLOG.md](BACKLOG.md).

## Where the dashboard lives

Both copies are built from `site/`:

- **Public:** https://cptgrumpus.github.io/engineering-agent-lab/, served from `docs/`. This is the link to give clients.
- **Private:** the claude.ai copy, visible only to me unless shared.

To rebuild after a change: run `site/build_v2.py`, then `site/export_docs.py`, then commit and push. See [site/README.md](site/README.md) for how the page is put together.

## Decisions needed from me

Items 1 and 3 can't start until I decide what goes on a public page. The page currently shows no name.

- [ ] **Name and contact:** show my name or not, and which link to give (LinkedIn, an email address, or a contact form).
- [ ] **Services:** which offers to list (FEA and contact, CFD and heat transfer, design optimisation, verification audits of existing models, AI-evaluation task writing), and whether to mention availability.

## Biggest impact

These four turn the page from a portfolio into something that wins work.

| # | Item | What it involves | Needs from me | Status |
|---|---|---|---|---|
| 1 | Contact section | A closing section with my name, a one-line offer and a link | The name and contact decision | Needs my input |
| 2 | Evidence links | Each study links to its run report on the public repo. Study 12's links wait until its code is committed | Nothing | Not started |
| 3 | Services section | A short "what I can do for you" block listing the offers | The services decision | Needs my input |
| 4 | Link preview card | A preview image and title when the link is pasted into LinkedIn, email or Slack, using the optimised bracket render | Nothing | Not started |

## Polish and quality

All four can go ahead without any input from me.

| # | Item | What it involves | Needs from me | Status |
|---|---|---|---|---|
| 5 | Light mode and phone check | A full review of the page in light mode and at phone width. So far only dark mode has had a full pass | Nothing | Not started |
| 6 | Faster loading | Convert the two GIF animations, about 1 MB each, to WebP at roughly half the size | Nothing | Not started |
| 7 | Sample deliverable link | Link the coolant-channel client memo ([portfolio/deliverables/coolant-channel-memo.md](portfolio/deliverables/coolant-channel-memo.md)) as "see a sample report" | Nothing | Not started |
| 8 | Render legibility check | Extend the render check to the lit image, where a dark side face could be misread as the wrong colour band | Nothing | Not started |

## Larger items and ones that follow the studies

Items 9 and 10 start when the other study session finishes its work. The 3D viewer is independent, but it's the biggest job here.

| # | Item | What it involves | Waits on | Status |
|---|---|---|---|---|
| 9 | New studies on the page | The cold-plate thermal chain (in progress) and buckling (next) each get a viewer tab, a gallery card, a write-up and visuals, using the same pipeline as study 12 (`scripts/make_opt_visuals.py`) | Those studies being verified and committed | Not started |
| 10 | Heat-transfer wall verdict | Study 11's wall temperature is withheld until a finer mesh shows the peak converging. Once that run passes, flip the verdict on the page | The finer-mesh run | Not started |
| 11 | Interactive 3D viewer | Let visitors rotate the parts in the browser instead of seeing fixed renders | Nothing, but it's the most work | Not started |

## Recently done

| Date | Item | What changed |
|---|---|---|
| 2026-11-21 | Study 12 on the dashboard | Viewer opens on the optimised bracket; featured card, write-up, search animation, before-and-after render and stress-along-span chart. Hero counts now come from the run records (1,478 checks, 36 runs) |
| 2026-11-21 | Public site refreshed | `docs/` rebuilt from the new page with `site/export_docs.py` |
| 2026-11-20 | Personal paths removed | Run records and logs no longer carry the Windows user name, commits use the GitHub no-reply address, and a test guards against leaks |
| 2026-11-20 | Plain-language rewrite | All page copy rewritten in a first-person voice |
| 2026-11-20 | Grader demo, requirements table, summary | Live grading of the three evaluation tasks, all requirements in one table, and a short summary at the top |
| 2026-11-20 | Filters fixed | The discipline filters now hide cards; they had never worked |

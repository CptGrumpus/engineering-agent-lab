---
name: portfolio-site
description: Rules for any work on the published portfolio site and its dashboard (site/, docs/, DASHBOARD.md) - writing or editing page copy, headings, study titles, cards, the in-progress page, requirement rows, or rebuilding and publishing. Use it whenever a study's status, wording or title on the site changes, even for a one-line edit.
---

# Portfolio site and dashboard

The site is built from `site/` into `docs/` and read by hiring managers and clients. Every rule here came from
something that went wrong on it.

## Titles are in title case

Anything that is a title uses title case: page titles and `<title>`, every heading (h1 to h4), study titles on
cards, pagers and the requirements table, card titles on the In Progress, How I Work and home pages, the "Simulation
Portfolio" label beside the name in the top bar, the nav, the filter buttons and the 404 page. Sentences are not titles: ledes, captions, chart headings, card answers and run-in labels stay in
sentence case.

The style is AP: capitalise every word, including the first, the last and the first after a colon; keep
articles, coordinating conjunctions and prepositions of three letters or fewer in lower case (a, an, the, and, but,
or, nor, for, yet, as, at, by, in, of, off, on, per, to, via, vs); capitalise each part of a hyphenated word
except those short words ("Mass-Spring-Damper", "Roller-on-Plate"); leave acronyms and units as written (CAD, FEA,
3D, kW, 12 mm).

**How it's enforced.** `site/titlecase.py` applies the rule to every title as `site/build_v2.py` writes the pages,
so a heading typed in sentence case in a study fragment still publishes correctly. Write titles in title case in the
source anyway, so the source reads like the site. When you add a new kind of title element (a new card type, a new
page section), add its pattern to `_TITLE_ELEMENTS` in `site/titlecase.py` and check the built page; a title the
patterns don't reach is published as written. Run `python site/titlecase.py` to see the rule on sample titles.

Why: titles in sentence case after the first word read as unfinished on a portfolio page (the user's call,
2026-11-23).

## Before publishing a study's status

Read BACKLOG.md's newest handoff and `git log` first. The study session may be ahead of the repo or of an older
handoff; the first motor page was written from a handoff an hour old and said a comparison hadn't run.

## Numbers handed over by the study session

Check any summary number against the data before it goes in a caption. The motor field export came with "stator
≤ 0.8 T"; the data says 95 % of the stator is under 0.9 T and the tooth tips reach 1.76 T. A one-line percentile
check is cheap; a wrong number on the page isn't.

The same goes for a finished write-up. Before a study's page goes up, read each run's report status and its
`checks.json`: the O-ring write-up said "passes every requirement" and "volume conserved to 3e-4", but its runs'
reports said verification FAIL (two cross-checks just over tolerance, one not in the write-up) and the volume check
read 5e-4. A miss that doesn't touch a verdict still goes on the page, with a verdict that says so
(`"checkmiss"`: "Passes; two cross-checks just missed").

Four more checks, all from the sealed enclosure's write-up (study 27, 2026-11-25):

- **Quote a benchmark stage at the setting the study's own runs use.** The write-up said radiation was "within 0.05 %
  at the chosen angular resolution"; the box runs used 16 ray directions, where the same stage reads 0.92 % against
  a 1 % limit. Read the setting from the production case file (`n_phi`) and quote that row.
- **Round from the data, and count from the reports.** 98.446 had become 98.45 and then 98.5 (it's 98.4), and
  "five runs failed the heat balance" was six in the `checks.json` files.
- **Look at what the run saved beside the requirement's metric.** The requirement is on the component; the saved
  `board_max_C` showed the board hotter than the component once the fix was in (98 °C, with no limit set for it).
  That goes on the page as a finding the requirement doesn't cover, and back to the study session.
- **A recorded status can be wrong in both directions.** After the study's own correction to the heat balance, two
  recorded FAILs were settled runs and four recorded PASSes weren't. Recompute the corrected check in the chart
  script, gate it on the values the case headers record, and mark the runs from that.

A pass from a run that failed its own settling or balance check is `"unsettled"` in `REQS` ("Met; run not settled"),
which doesn't count as met. A study whose fix clears only some of its requirements gets the card verdict `"partfix"`
("Fails; the fix covers one limit of two"), in the fail colour.

## Wording

Plain, first person, the way an engineer would say it to a colleague. No stock phrases or filler, no em dashes as
a crutch, no claims a number doesn't back. After a wording change, reread the changed pages and check every
statement against the runs (a "the problems are made up" line went out after two studies used published data).

## How a study page is ordered

The user's rule (2026-11-23): a reader must see what the thing is before the result. Recruiters give a page under a
minute, and a verdict about a part they haven't seen means nothing; the drawings used to sit halfway down, after the
result chart, so every page read as "just results". Every study page runs, top to bottom:

1. Title and a **one-line question** (`QUESTION` in `build_v2.py`, plain words, the part and the decision in one sentence).
2. **The setup**: the study's drawing from `scripts/make_drawings.py`, captioned. A page made of several studies opens
   with the drawing that best shows the part (`SETUP`); the other parts keep theirs in their own sections.
3. **The answer**: the verdict and the one-paragraph answer.
4. The result viewer (the chart or 3D render).
5. The write-up: question, answer, **the model** (moved up by the build to follow the answer), why it matters, how it
   works, the checks, what I caught, the limits, the case record and the evidence.

The home cards follow the same rule: each card shows the study's setup drawing on the left and its result on the
right, with the finding and the verdict under both. The build cuts `v2/tc_<study>.webp` from the drawing itself
(title block off, trimmed, fitted to 16:10), so a redrawn part updates its card; the result is the chart's
`th_<key>.webp`. When a drawing carries a table or a second plot beside the part, add a `CARD_CROP` entry and look at the card:
a crop through a block of notes leaves half-words at the edge. A long part (the shaft is 3.5 times wider than
tall) shrinks to a strip on the card: crop to the part itself and leave the detail views and text blocks for the page. The setup-first rule was settled for the pages on
2026-11-23; applying it to the cards was asked again a day later, so apply it to every new place a study is shown
rather than asking.

The home page leads with the strongest studies (user, 2026-11-24): the first screen's picture, the three lead
studies (`LEAD` in `build_v2.py`) and the cards (`FRONT`, which also sets the pager's order). Strongest means what a
hiring client values most: real hardware or measured data, a cause traced, several physics, a design decision. The
traction motor leads. When a study lands, decide where it goes in `FRONT` rather than letting it fall to the end.

The home page is the Showcase (user's choice, 2026-11-24, on the `ui-redesign` branch): one dark theme, the result
plots' colour scale as the brand. It answers a first-time visitor's questions in order: who and what (the first
screen names the person, the work and how to get in touch), proof (three lead studies, each a pair: the part, then the
answer, with one number and what the checks caught), range (every kind of analysis as a tag that opens its study),
what's on offer and what comes back (`SERVICES`, the sample memo shown as a page, the four method steps), trust
(one dot per requirement and the mistakes the checks caught), then every part. What it must not do:

- Type a number twice. Counts come from `extras.REQS`, the method steps and lessons from `pages/how.html`, the memo
  from the memo file. A lead study's typed words carry `quotes`, and the build fails when the study's card or lesson
  stops saying them: change the card first, then the lead's words.
- Use a section id that is also a study's key (`contact` is the roller study and the footer): links written as
  `#key` are rewritten to the study's page, and old one-page links are redirected by key.
- Put a heading through the title-case rule that it gets wrong. A phrasal verb's "on" comes out lower case ("What I
  Can Take on"): reword the heading.
- Set large numbers in the display face: its 1 reads as a broken glyph, so they use the body face.

The first screen's picture is exported by `scripts/make_field_map.py --hero` from the gated field data, not cropped
from the figure. A lead study with a 3D render shows it bare on the dark page; a chart or a drawing sits on a
paper-coloured plate (`on-plate`).

Every study needs a drawing, so a new study isn't finished without one. The drawing shows the physical setup: the
part with its main dimensions, the supports and loads, what's modelled (a half or a quarter), the inputs that are
uncertain, and the load history when it matters (a cycle, a proof load). Read every value from the case file; a result
shown on a drawing is labelled as the result. Render it and look at it before publishing: leader lines through holes
and labels crowding the footer only show up there. The build asserts every page has its `QUESTION`.

Visuals are kept current, and made for a client deciding whether to hire (user, 2026-11-24). When a study's
result lands, refresh its drawings and figures in the same update, not just the words; an In progress card gets
its setup drawing too. Aim each one at what a hiring client scans for: the physical part and what's modelled, the
verdict against the requirement, and the independent check. Where a run saved more than its figure shows (a time
history, a Campbell table), draw from it: the flag's real tip paths, the rotor's real mode shapes.

## Adding a finished study to the site

A study the study session has written up (`portfolio/NN-*.md`) gets a section on the site, not just an in-progress
card. The pieces, all in `site/`:

1. `studies/<key>.html`: the hand-written section (same headings as the others, `{{CASE}}` where the case record goes).
   A drawing in `scripts/make_drawings.py` with its caption in `DRAWINGS`, and the page's line in `QUESTION`.
2. `build_v2.py`: a `CARDS` row, one `VP` viewer entry (a chart can be the viewer: `"kind": "figure"`), `CASES`, and
   either a `SLUG` of its own or a place in `GROUPS` with a `PART_LABEL` when it's another study of the same part
   (study 21 joined study 4's bracket arm; the step joined study 19). Keep an existing page's slug so shared links work.
3. `extras.py`: `STUDY_DOCS`, its `REQS` rows, and `RUN_PREFIX` when two parts share one write-up, so each part lists
   only its own runs. `RUN_LIST` instead names the exact runs and drops the write-up link, for a page whose write-up
   tells a different story than the page (the motor, until `portfolio/20` is rewritten). `RUN_GLOB` adds runs the
   write-up cites by a pattern (`runs/20261124-1714*_enclosure_fix_*`), which the run-name search doesn't see.
4. A chart in `scripts/make_figures.py` read from the run and the case file, never copied from the run's PNG. Render
   a PNG preview and look at it before publishing: label collisions and clipped headings only show up there.
   A study with its own card needs a gallery thumbnail, `site/v2/th_<key>.webp`: call `thumb(fig, ax, key)` before
   `fk.save` so the card's picture is cut from the chart and changes with it. Hand-cut thumbnails went stale twice
   (the motor card kept a withdrawn result, the pipe card the word "converged"). On a study's own page the chart is
   already the viewer, so don't repeat it in the body; a part of a grouped page does show its chart in the body.
5. Take the study off the in-progress page in the same commit.

When an existing study's result changes, its status lives in more places than its page. Update them together:
the page's chips, answer, tables and figure captions (`studies/<key>.html`); its `REQS` rows in `extras.py`
(the requirements panel beside the page and the requirements page: the motor's still said "withheld" after its
text was updated); its `CARDS` blurb; its In progress card; and the run IDs its figures read in
`make_figures.py` (the motor's rotor chart still drew the blind run). A pass that rests on an unexplained
discrepancy gets its own `REQS` status that doesn't count as met (the motor's rated power, which rides on the
18 % flux, is "provisional").

A study closed with open items (the motor: no client to answer its last questions) isn't in progress any more. Give
its card a verdict that says so (`"closed"`: "Closed, with client questions"), take it off the In progress page, drop
any "where it stands day to day" link to it, and reword limits that said data "isn't used" if the closing step used it.

Don't write "today" or "now" into page copy: the site is static, so "Finished today" on the In progress page was a
day stale before anyone noticed. Say "recently" or give the date.

## Editing the source safely

- Write patch scripts with the Write tool, not a Git Bash heredoc: the heredoc turns `\\n` into a real newline
  inside Python strings and the patch silently stops matching. A quoted heredoc (`<<'EOF'`) does it too; it broke
  a chart label on 2026-11-23. No heredocs for Python at all.
- Make a patch script safe to run twice. Check for the whole new text, not just the old: when the old text is a
  prefix of the new (adding entries after a line), a second run inserts them again. The build's
  one-viewer-entry-per-study assert caught that once. A line inserted twice isn't caught by anything (study 25's
  `QUESTION` line and the motor's air-gap table row both published twice): check for the new line itself, not for
  the old one being gone.

## Building and publishing

```
.venv\Scripts\python.exe site\build_v2.py
.venv\Scripts\python.exe site\export_docs.py
.venv\Scripts\python.exe site\check_viewer3d.py
```

All three must pass. Check changed pages at 360 px wide for sideways overflow. The study session commits in the
same clone: add and commit only your own paths, in one command, and never leave files staged.

Work on a feature branch goes in a git worktree (a second folder), never a branch switch in this clone: a switch
would move the study session onto the branch and its commits with it. The redesign lives in
`../engineering-agent-lab-ui` on `ui-redesign` (2026-11-24); run its scripts with this clone's `.venv`. Design
mock-ups there are filled from `build_v2.py`'s own data by `site/proposals/build_proposals.py`, so a mock-up never
shows a number the site doesn't.

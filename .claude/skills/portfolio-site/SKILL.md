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
   tells a different story than the page (the motor, until `portfolio/20` is rewritten).
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
  one-viewer-entry-per-study assert caught that once.

## Building and publishing

```
.venv\Scripts\python.exe site\build_v2.py
.venv\Scripts\python.exe site\export_docs.py
.venv\Scripts\python.exe site\check_viewer3d.py
```

All three must pass. Check changed pages at 360 px wide for sideways overflow. The study session commits in the
same clone: add and commit only your own paths, in one command, and never leave files staged.

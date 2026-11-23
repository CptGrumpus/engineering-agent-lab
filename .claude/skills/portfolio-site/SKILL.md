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

## Wording

Plain, first person, the way an engineer would say it to a colleague. No stock phrases or filler, no em dashes as
a crutch, no claims a number doesn't back. After a wording change, reread the changed pages and check every
statement against the runs (a "the problems are made up" line went out after two studies used published data).

## Adding a finished study to the site

A study the study session has written up (`portfolio/NN-*.md`) gets a section on the site, not just an in-progress
card. The pieces, all in `site/`:

1. `studies/<key>.html`: the hand-written section (same headings as the others, `{{CASE}}` where the case record goes).
2. `build_v2.py`: a `CARDS` row, one `VP` viewer entry (a chart can be the viewer: `"kind": "figure"`), `CASES`, and
   either a `SLUG` of its own or a place in `GROUPS` with a `PART_LABEL` when it's another study of the same part
   (study 21 joined study 4's bracket arm; the step joined study 19). Keep an existing page's slug so shared links work.
3. `extras.py`: `STUDY_DOCS`, its `REQS` rows, and `RUN_PREFIX` when two parts share one write-up, so each part lists
   only its own runs.
4. A chart in `scripts/make_figures.py` read from the run and the case file, never copied from the run's PNG. Render
   a PNG preview and look at it before publishing: label collisions and clipped headings only show up there.
5. Take the study off the in-progress page in the same commit.

## Editing the source safely

- Write patch scripts with the Write tool, not a Git Bash heredoc: the heredoc turns `\\n` into a real newline
  inside Python strings and the patch silently stops matching.
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

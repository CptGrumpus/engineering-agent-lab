---
name: portfolio-site
description: Rules for any work on the published portfolio site and its dashboard (site/, docs/, DASHBOARD.md) - writing or editing page copy, headings, study titles, cards, the in-progress page, requirement rows, or rebuilding and publishing. Use it whenever a study's status, wording or title on the site changes, even for a one-line edit.
---

# Portfolio site and dashboard

The site is built from `site/` into `docs/` and read by hiring managers and clients. Every rule here came from
something that went wrong on it.

## Titles are in title case

Anything that is a title uses title case: page titles and `<title>`, every heading (h1 to h4), study titles on
cards, pagers and the requirements table, card titles on the in-progress, How I work and home pages, the nav and the
filter buttons. Sentences are not titles: ledes, captions, chart headings, card answers and run-in labels stay in
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

## Wording

Plain, first person, the way an engineer would say it to a colleague. No stock phrases or filler, no em dashes as
a crutch, no claims a number doesn't back. After a wording change, reread the changed pages and check every
statement against the runs (a "the problems are made up" line went out after two studies used published data).

## Building and publishing

```
.venv\Scripts\python.exe site\build_v2.py
.venv\Scripts\python.exe site\export_docs.py
.venv\Scripts\python.exe site\check_viewer3d.py
```

All three must pass. Check changed pages at 360 px wide for sideways overflow. The study session commits in the
same clone: add and commit only your own paths, in one command, and never leave files staged.

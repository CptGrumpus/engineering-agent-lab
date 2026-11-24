---
name: publication-figures
description: Make a chart, plot, diagram or dimensioned drawing for the portfolio site, a report or a client memo that is sharp and easy to read. Use whenever a figure is going in front of a reader - "make a chart/plot/figure/diagram", "this image is blurry", "make it prettier", a new study page - and any time a harness response.png or sweep.png is about to be shown outside a run report. Redraws from the run's saved data in the house style (scripts/figkit.py) or draws the model from its case file (scripts/make_drawings.py); never screenshots or copies a working plot.
---

# Publication figures

A figure on the site is a communication product built on a verified result, like a
render. It has to be sharp at any size, readable without the write-up, and it must
not say anything the run didn't.

The harness's own plots (response.png, sweep.png) are working plots: 130 dpi, titled
with the case name, axes labelled with metric names. They belong in run reports.
Don't put one on the site or in a deliverable. Redraw it.

## Two kinds of figure

| Kind | Script | Output |
|---|---|---|
| Chart of results | `scripts/make_figures.py`, one function per chart, built on `scripts/figkit.py` | `site/v2/fig_<name>.svg` |
| Drawing of the model: views, sections, schematics | `scripts/make_drawings.py`, one function per study | `site/v2/dwg_<study>.webp` |

## Where the numbers come from

- Data: the committed run (point.json, cells.csv or the study's series file).
- Limits: the case file's requirements. Pass, fail or unverified: verification.json.
- Reference curves: the validation module the study's own checks use.
- Dimensions in a drawing: the case file's parameters.
- A typed-in number is allowed only for a result quoted in a label, and it must
  match the write-up. If a number isn't in a run or a case file, it doesn't go on
  the figure.

## Chart rules (figkit.py carries them)

1. Vector SVG, text as outlines. FULL width (8.4 in) for a figure on its own row,
   HALF (4.4 in) for one of a pair. Don't squeeze a wide multi-panel figure into
   half a row: split it or give it the full row.
2. A headline in words that says what the chart shows ("No gap meets both
   limits"), then one muted line saying what is plotted. No case names, metric
   names or run labels anywhere on the figure.
3. Model in blue, independent reference in orange, both named in a key. Text is
   never coloured.
4. A limit is a line with the failing side shaded and labelled.
5. Status by shape and colour: filled circle meets, filled diamond misses, hollow
   circle not verified. An unverified result is shown, greyed and labelled, never
   hidden and never drawn as a pass.
6. Hairline solid grid, no box, 2 px lines, markers with a surface-coloured ring.
   Thin out dense point clouds (every nth point, denser where the curve bends).
7. Label the few values that matter. Axis labels in plain words with units
   ("distance from the side wall, mm").
8. One scale per axis. Never two y-scales on one panel.

## Drawing rules

- To scale in both directions, or the sheet says what is stretched and by how much.
- Outline dark, section cuts hatched, loads in blue, the feature the study is
  about (assessed lines, the contact, the bridges) in the warm accent, dimensions
  in grey with the value on the line.
- A title strip: study number, part, view, and "Drawn from the case file's inputs".
- Use real geometry where it exists: CadQuery solids through `hlr()`, the motor
  through `scripts/export_motor_geometry.py`.

## Steps

1. Find the run and its saved data. Read the harness's plot function
   (harness/plotting.py, or the study's own) to see how the arrays are laid out.
   Don't guess.
2. Write the function and run the script for that figure only.
3. Look at it: render it in a browser at 1000 px and at 400 px wide. Fix
   collisions, clipped labels and anything that falls off an axis.
4. Put it on the page (`site/studies/<key>.html`) with alt text that states the
   finding and a caption that adds something the headline doesn't.
5. Run `site/build_v2.py` and `site/export_docs.py`, and check 360 and 1280 px.

## Data a run didn't save

Some runs save results but not everything a figure needs (the fan rotor saved its Campbell values, not its mode
shapes). Rebuild the model from the run's own copy of its source (`runs/<run>/inputs/`) with each point's
`params.json`, and refuse to use it unless it reproduces numbers the run recorded (`scripts/export_fan_modes.py`
gates the shapes on the run's frequencies, to 0.01 %). Then the figure shows the verified model, not a new one.
Say so in the figure's line or the drawing's footer, and give `finish(..., source=...)` the true source when a
drawing isn't drawn only from the case file (a traced client drawing).

The same goes for a field export handed over by the study session (`build/render/*/field.npz`): the drawing script
runs the gate itself against the run's own output, not a "gate passed" note in the export's JSON, which a newer
export may not carry (`scripts/make_field_map.py` checks the circuit fluxes against the run's `flux_linkage.csv`).
When the export moves to a new model revision, re-check every label against the new geometry: revision 4's
"non-magnetic shell" label landed inside revision 5's magnet, and a label placed past the view's edge is clipped
without warning.

## Before it ships

- [ ] No code names, case labels or metric names on the figure
- [ ] Every number traces to a run or a case file
- [ ] Units on every axis
- [ ] Readable at 400 px wide
- [ ] An unverified result is marked as such
- [ ] Looked at, not just generated

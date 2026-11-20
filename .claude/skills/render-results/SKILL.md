---
name: render-results
description: Turn a verified simulation result into a presentation-quality 3D render (Blender, Cycles) with a legend that provably matches the colours, or a clean CAD hero render. Use whenever the user wants renders, "Blender", photoreal or presentation images, contour plots on the 3D part, deformed-shape or mode-shape pictures, figures for a client deck, report or portfolio, or asks to make results "look more professional", even if they don't name Blender.
---

# Render results

A render is a communication product built on a verified result. It must not
say anything the study doesn't: the colours must be the legend's colours, the
range and any capping must be stated, and a magnified deformation must say by
how much. The pipeline enforces the first with an automated check and the
rest with required caption fields.

## The pipeline (one command)

```
.venv\Scripts\python.exe scripts\make_renders.py [--only NAME ...] [--samples N]
```

1. **Export** (`harness/femesh.py`): read the solver deck (`read_inp`, follows
   `*INCLUDE`), extract the outer surface (`boundary_triangles`: faces owned by
   one element, oriented away from the element centroid), drop interior and
   mid-side nodes (`compact`), and write the scene (`write_scene`): `.npz`
   geometry + scalar per vertex, `.json` metadata (field, units, range, bands,
   view, title, caption, design volume).
2. **Render** (`scripts/blender/render_scene.py`, run by Blender in background
   mode): scalar mapped to a constant colour ramp in the shader, Standard view
   transform, three area lights, shadow catcher on a transparent background,
   camera solved to frame the part. Writes a beauty pass and an unlit check pass.
3. **Check**, and refuse to publish on failure:
   - *Geometry*: the undeformed surface's enclosed volume equals the part's
     design volume (within 0.5 %). A missing, duplicated or inward face changes
     the volume, so this catches extraction bugs and unit mix-ups.
   - *Colour*: on the unlit pass, at least 99.5 % of part pixels must be a
     legend band colour (within 3/255 per channel). Also records which bands
     are visible, so you know whether the peak is actually in view.
4. **Annotate** (matplotlib): legend from the same range and band colours the
   shader used, title, caption, and a credit line. Results go to
   `portfolio/img/render_*.png`; the check log goes to `portfolio/img/renders.json`.

Blender is located from `$BLENDER` or the portable install under
`%LOCALAPPDATA%\Programs\Blender`. It's verified with 4.5 LTS, using the OptiX
GPU at about 8–12 s per image and falling back to the CPU automatically.

## Adding a scene

Write a `scene_<name>()` in `scripts/make_renders.py` that loads the evidence
run, builds `xyz`, `tris`, `value` and calls `write_scene` with at least:

| field | why |
|---|---|
| `field`, `units`, `vmin`, `vmax`, `bands`, `band_colors=bands(n)` | the legend; the shader and the legend read the same numbers |
| `expected_volume_mm3` | design volume from the dimensions, for the geometry check |
| `title`, `caption` | the caption states the deformation scale, the range capping and the model simplifications (e.g. "quarter model mirrored") |
| `ghost_xyz` (deformed scenes) | the undeformed shape, drawn as a feature-edge outline |
| `elev`, `azim` (optional `frame_box`, `distance_factor`, `fill`) | the view; `frame_box` frames a detail, such as the region around a hole |

Register it in `SCENES`. Multi-image figures (an overview plus a close-up, or
several modes) go through `annotate_grid` with one shared legend.

## Choosing the contour range and bands

- **Banded contours** (8–14 bands) read the way an FE post-processor's do, and
  they make the colour check exact. Smooth gradients can't be checked.
- **Put a band edge away from any value that dominates the part.** If the
  nominal stress sits on a band edge, round-off appears as speckle. The strap's
  31.25 MPa sat on the 30 MPa edge until the bands were shifted to −37.5…112.5
  in 15 MPa steps.
- **Cap the range at a meaningful value when there's a singularity**, and say
  so in the caption. For example, the cantilever is capped at the 150 MPa
  beam-theory stress because the clamp corners are singular. Without a cap,
  a few singular nodes set the scale and the rest of the part turns one colour.
- **Mode shapes**: show colour as displacement relative to that mode's largest
  motion (0–1), not in physical units, because mode amplitude is arbitrary.
  Choose the amplitude per mode type: bending modes at about 16 % of the length,
  torsion much less (5 mm on a 25 mm arm), or it twists into nonsense.

## Traps found while building this (each one cost a render)

- **Filmic/AgX tone mapping changes colours.** Blender's default view transform
  desaturates and shifts hues, so the part no longer matches the legend. Use
  `Standard`; the colour check catches any regression.
- **Never interpolate colours, interpolate the scalar.** Vertex colours blend
  in RGB between vertices, which produces colours that aren't on the colormap.
  Store the scalar as a mesh attribute and colour it in the shader.
- **Over-lit renders wash out the contours.** Blender area-light watts depend on
  scene scale. The script normalises every part to a 2-unit size so that one
  light rig (key 260 W, fill 90 W, rim 160 W, world 0.25) suits all parts.
- **Shadow-catcher haze.** The catcher leaves a 2–4 % black veil over the whole
  ground plane, which shows as a hard-edged rectangle in the composite. Fade
  the shadow alpha to zero towards the image border (`beauty()`).
- **A translucent undeformed shape tints the result.** Draw it as a thin outline
  of its feature edges instead, the way FE post-processors do.
- **Units.** The heat-transfer deck is in metres and the structural decks in mm.
  Convert before the volume check, which flags the mismatch at once.
- **Plane-stress or thin-layer models** (the strap) have no real thickness:
  mirror the quarter-model field and extrude it to the actual plate thickness
  (`extrude_planar`). Say so in the caption.

## What to say about a render

A render shows where the stress, heat or motion is. The numbers come from the
verified study, and the render's caption says where it came from and how it
was scaled. The checks show that the picture is faithful: the surface encloses
the right volume, and every pixel is a legend colour.

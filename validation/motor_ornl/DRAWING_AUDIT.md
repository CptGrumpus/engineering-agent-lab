# Study 7: the motor model against its drawings, part by part

> **2026-11-23 13:55: superseded in part by `CLIENT_DATA.md`.** The magnet is 83.1 x 18.9 x 6.5 mm (ORNL/TM-2010/253
> Table 2.7), not the 19.24 x 5.31 mm of the design report audited below, and its remanence is measured (1.255 T at
> 20 C). The magnet rows below describe the revision-4 model, which used the wrong thickness.

Audit of the revision-4 primary machine (`models/motor/Toyota_Prius_ORNL_mag531centre.json`: drawn pocket, 5.31 mm
magnet centred in a polymer shell, Br 1.243 T) against every source a client would provide. Done 2026-11-23
13:35-13:40 (times from `date`), after the revision-4 and 1.12 T runs, as build-model step 3 asks. Nothing in the model was changed by
this audit; differences become hypotheses, each tested on its own later.

Sources (all opened before this audit; nothing new used):
- **Drawing**: ORNL/TM-2005/33 Fig. 21 (Pub57487.pdf, report p. 25, PDF page 32, sha256 179407ec...), the 2004
  stator and rotor laminations with dimensions in inches. Re-rendered for this audit at 400 and 900 dpi.
- **Design report**: ORNL/TM-2004/120 Tables 5.3-5.4 (sha256 6548edc4...), dimensions and inputs of ORNL's own
  parametric model of this motor.
- **Teardown**: ORNL/TM-2004/137 (Pub57348.pdf, sha256 32469ab0...), pp. 4-10: winding connection, laminations,
  slot fill, end windings, magnets.
- **Pyleecan**: values inherited from Pyleecan's `Toyota_Prius.json` and never replaced.

Legend: **match** (within drawing precision), **minor** (differs, effect estimated below 1 % on back-EMF),
**differs** (could move results by more), **not checked** (no source gives it).

## Stator

| Item | Source value | Model | Verdict | Note |
|---|---|---|---|---|
| Outer diameter | 10.600 in = 269.24 mm (drawing); Rad3 134.62 mm (design report) | Rext 134.62 mm | match | |
| Bore | 6.375 in = 161.93 mm (drawing) | Rint 80.963 mm | match | |
| Slots | 48: tooth 0.300 in + slot 0.125 in = 0.425 in pitch at r 3.23 in gives 47.8 (drawing) | Zs 48 | match | Pyleecan's; the drawing agrees |
| Slot opening, tooth tip, slot width, round end | 0.076 / 0.040 / 0.124 / 0.222 in (drawing) | W0 / H0 / W1 / W2 as drawn | match | |
| Slot depth (bore to slot end) | 1.320 in = 33.53 mm: slot end at r 114.5 mm (drawing, label and outline agree) | H0 + H2 = 33.53 mm | match | |
| Slot end radius in the design report | Rad2 116.5 mm (design report) | 114.5 mm | **differs between sources** | The design report puts the slot end 2.0 mm deeper (yoke 18.1 against 20.1 mm). The drawing is the hardware source; stator yoke peaks at 0.6 T (teeth 0.77 T) in our solution, so the yoke depth barely matters at open circuit |
| Stator mounting ears, bolt holes, OD notches | R0.234, Ø0.360, 0.349, 0.474, 0.094, R0.109, 0.080, 0.230 in (drawing) | not modelled | minor | Outside the magnetic path (yoke 0.6 T peak). **In the detailed CAD (2026-11-27):** three ears 120 deg apart (holes Ø0.360 in at r 138.5 mm, end radius 8.9 mm, root reliefs R0.234 in 1.2 mm deep), six 0.474 x 0.094 in notches with R0.109 in corners and three 0.230 x 0.080 in, all on tooth centres every 30 deg; positions and the ear outline measured from the drawing's vectors (`drawing_stator/`, `scripts/motor_drawing_stator.py`); with them the core weighs 19.05 kg, the BOM's value (`models/cad/prius_motor.py`) |
| Stack length | 3.3 in = 83.82 mm (teardown); Lstk 83.57 mm (design report) | L1 83.82 mm | minor | 0.3 % between sources; back-EMF scales with it |
| Lamination | 0.014 in = 0.36 mm, grade not given (teardown) | M330-35A, 0.35 mm (stand-in) | minor | Three grades moved back-EMF by 0.13 % (blind study) |
| Stacking factor | not given | Kf1 0.95 (Pyleecan), not used by the FEMM solve | not checked | FEMM reads only the B-H curve; the solve treats the stack as solid steel. Steel at 0.6-0.9 T is far from saturation, so the missing 5 % of steel changes little at open circuit |

## Winding

| Item | Source value | Model | Verdict | Note |
|---|---|---|---|---|
| Turns per coil | TC 9 (design report Table 5.4) | Ntcoil 9 | match | Was "Pyleecan's, unconfirmed" in the blind study (candidate cause 3): now confirmed by the design report |
| Layers | 1 (design report Table 5.4) | Nlayer 1 | match | |
| Parallel paths | series in the 2004 model, parallel in 2003 (teardown p. 4) | Npcp 1 | match | 72 series turns per phase |
| Coil pitch | not stated | 6 slots (full pitch, 48 slots / 8 poles) | not checked | Standard for a single-layer, q = 2 winding |
| Strands | not stated; slot fill 0.84 by "squares of insulated wires" over net slot area (teardown p. 7) | 13 x 0.912 mm per turn (Pyleecan) | not checked | Rough check: 117 strands at about 0.95 mm insulated is 105 mm² of squares in a slot of about 150 mm² gross, 125-130 mm² net: 0.81-0.84. Consistent; matters for resistance only |
| End windings | about 1.5 in per side (teardown p. 7) | Pyleecan Lewout 19.4 mm (unused); the efficiency study's own end connection has 38.4 mm axial height | match | Pyleecan's value is not used in the analysis. The detailed CAD first drew a 19.4 mm ring from it (2026-11-27); since 2026-11-28 its end turns reach the teardown's 1.5 in |

## Rotor

| Item | Source value | Model | Verdict | Note |
|---|---|---|---|---|
| Outer diameter | 6.314 in = 160.38 mm (drawing); Rad1 80.19 mm (design report) | Rext 80.188 mm | match | Air gap 0.775 mm |
| Inner diameter | 4.356 in = 110.64 mm (drawing) | Rint 55.32 mm | match | |
| Hub keys | four keys on the bore, 4.152 in across (drawing; teardown p. 10). **Corrected 2026-11-27:** the drawing shows two keys, 180 deg apart, 5.04 mm wide (measured), 4.152 in across their tops; the teardown's count was not re-read | not modelled (in the detailed CAD as drawn) | minor | Inside the yoke's inner edge |
| Steel hub ring under the laminations | the design report's model includes "the outer ring of the shaft" as rotor iron that "carries some of the magnetic flux" (RadSH 50.46 mm, so a ring about 4.9 mm thick) | not modelled: Pyleecan leaves the shaft unmeshed and the rotor iron ends at 55.32 mm | minor | Probed in the saved revision-4 solution (open circuit): the rotor yoke under the V peaks at 0.94 T and carries 7.3 T·mm per metre of depth. Unsaturated, so a parallel ring changes the path's reluctance little. Estimated under 0.5 % on back-EMF; not run |
| Pockets per pole | one continuous V hole per pole, 8 in all, no centre rib (drawing, whole rotor re-rendered) | HoleM50 W1 = 0: one V hole, no rib | match | |
| Pocket thickness | 6.80 mm measured on 8 poles (drawing) | 6.80 mm | match | |
| Arm angle, apex depths | 17.4 deg; 10.65 / 17.76 mm below the OD (drawing) | 17.4 deg; 10.65 / 17.78 mm | match | |
| Bridge | 0.056 in = 1.42 mm and 0.060 in = 1.52 mm at two points of the pocket end (drawing); 1.45 mm (design report) | 1.45 mm (one value, HoleM50's single bridge) | minor | The template has one bridge thickness; the drawing's pocket end is shaped (two values and small stops). Bridge leakage is about 2.6 T·mm against about 13.5 Br per magnet, and moves in proportion to the bridge: 0.07 mm is under 0.5 % |
| Pocket end shape and magnet stops | small notches near each end of the pocket (drawing) | HoleM50's straight ends, no stops | **differs** (revision 4) | Not measured. The stops set where the magnet sits along the arm, and the end shape sets bridge leakage. **Revision 5 (traced pocket): match**, outline within 0.075 mm median, magnets on the stops (2026-11-23, `scripts/motor_drawing_stops.py`) |
| Magnet size | 19.24 x 5.31 mm, 38.48 mm for the pair (design report Table 5.3); face width about 19-20 mm in the teardown photo | 19.24 x 5.31 mm | match | |
| Magnet across the pocket | polymer-moulded, sized to the pocket (teardown pp. 9-10) | centred, 0.745 mm of non-magnetic material on each face | match (primary) | Outer and inner placements are the bounds: 85.3 / 79.3 V |
| Magnet along the arm | not given; the stops would set it | from the V apex outwards (HoleM50 placement), leaving 1.5-5 mm of air along the arm between the magnet's outer end and the bridge arc | **not checked** (revision 4) | The drawn stops were not measured. Moving the magnet towards the bridge raises the leakage through it. **Revision 5: measured**, every magnet sits on its stop, at most about 0.4 mm of play (2026-11-23) |
| Magnet axial length | not given | = stack, 83.82 mm | not checked | |
| Magnetisation | parallel, normal to the magnet face | parallel, normal to the face (±17.4 deg offsets) | match | |
| Magnet material | Br 1.243 T (extrapolated to H = 0 from points at -7.2 to -4.7 kOe), recoil permeability 1.129, temperature not stated (teardown Fig. 14) | 1.243 T, 1.129, taken as 20 C | **not checked** | 1 % on Br is about 1.2 % on back-EMF. ORNL's design value 1.12 T is most likely the same material hot (about 119 C; CALIBRATION_PLAN.md) |

## Labels left over

The material names inside the machine files still read "Lamination M400-50A" (the `desc` field), although their
B-H data, thickness and path are M330-35A. A label only, but misleading; fix in `build_prius_ornl.py` when the machine
is next rebuilt. In the case files, `motor_prius_rev4_oc.toml` and `motor_prius_rev4_oc_br112.toml` still carry the
blind model's limitation "the magnet fills the pocket thickness". The `_br112` case's assumptions also still say
1.243 T. Both are noted in the cases' Results.

## What could still explain the remaining -7.8 % (centred) on back-EMF

In rough order of size, each to be tested on its own:
1. **Magnet remanence and temperature** (not checked): the extrapolation of the sample curve and its unknown
   temperature. A few percent either way. A client would have the magnet grade's datasheet; look for it before
   anything else.
2. **Magnet position along the arm and the pocket-end shape** (differs, not measured): the drawn stops, measured on
   the vector outline as the pocket thickness was, then one revision with the magnet where the stops put it.
3. **What ORNL's "scaled" back-EMF means** (measurement side, open since the blind study): the scaling is not explained
   in the report.
4. 2D end effects: would lower the model further, so they cannot close a gap where the model is already low.
5. Small items together under about 1-1.5 %: hub ring, bridge value, stack length, stacking factor.

"""Build our 2004 Prius machine definition from published dimensions (study 7 geometry rebuild). Pyleecan environment.

usage: <pyleecan python> models/motor/build_prius_ornl.py   (writes models/motor/Toyota_Prius_ORNL.json, prints the table)

Source of every dimension changed here: ORNL/TM-2005/33, "Report on Toyota Prius Motor Thermal Management" (FY 2005),
Fig. 21 "Schematic of Prius motor stator and rotor", report page 25 (PDF page 32),
https://info.ornl.gov/sites/publications/Files/Pub57487.pdf. Only that figure was read: the report's test-data pages
stay closed so that the ORNL performance comparison remains blind.

How the drawing was read (2026-11-21): the labels are vector text (PyMuPDF get_text). The slot inset gives the depth
1.320 in (bore to the end of the round), the opening 0.076 in, the tooth tip 0.040 in, the slot width 0.124 in and the
round end 0.222 in diameter. The main view's vector outline, scaled by fitting a circle to the bore (6.375 in), agrees:
0.076 in at the bore, 0.125 in just above the tooth tip widening linearly to 0.218 in at r = 4.35 in, slot end at
r = 4.51 in (depth 1.32 in), tooth 0.300 in near the bore (the drawing's own "0.300" label).

Rotor and magnets (ROTOR_CHANGES, MAGNET_CHANGES), checked 2026-11-21 late evening:
- Fig. 21 draws each pole's V pocket as a vector outline. The figure is stretched 1.1 % in x against y in the PDF (its
  rotor OD outline is an ellipse, x/y 1.0114); corrected by scaling x and y separately to the labelled 6.314 in OD.
  Measured on all 8 poles: arm angle to tangential 17.4 deg (sd 0.13; Pyleecan 17.46), pocket thickness 6.80 mm
  (sd 0.03; Pyleecan 6.50), outer apex 10.65 mm below the OD (Pyleecan H0 10.96), inner apex 17.76 mm (Pyleecan
  17.78). So the inner edge is Pyleecan's and the extra thickness is on the air-gap side: H0 = 10.65, H3 = 6.80, and
  W0 = 41.21 mm to keep the arm angle. In HoleM50 the magnet fills the pocket thickness (6.80 mm).
- Bridge 1.45 mm: ORNL/TM-2004/120 (PM Motor Parametric Design Analyses, July 2004), Table 5.3 and Fig. 5.2, which
  marks this dimension as "Bridge"; Fig. 21's red label 0.056 in (1.42 mm) agrees. Pyleecan: H1 = 1.5 mm.
- Magnet material: ORNL/TM-2004/137 (design report) Fig. 14, ORNL's measured B-H line of a Prius magnet sample
  (opened by the user's decision, 2026-11-21; a material property, not motor performance), digitized from 906 pixels
  of ORNL's fitted line: Br 1.243 T (12.43 kG at H = 0, an extrapolation: the measured points span -7.2 to -4.7 kOe),
  recoil permeability 1.129, Hcb -876 kA/m. Pyleecan: Br 1.24 T, 1.05. Temperature not stated: taken as 20 C.
- Not adopted: TM-2004/120's magnet 19.24 x 5.31 mm (MagWid 38.48 mm for the pair) and Br 1.12 T. A 5.31 mm magnet
  in the drawing's 6.78 mm pocket would need a different hole model; the size change nets about -0.4 % on back-EMF
  (scratch sensitivity), and 1.12 T matches 1.24 T at about 120 C with the material's -0.1 %/K, so it is probably a
  hot value. Recorded as alternatives.

What stays Pyleecan's: the magnet width (18.9 mm) and the V's other parameters, the laminations' material (M400-50A),
the winding (9 turns per coil; the thermal report's text gives 9 conductor bundles per slot) and the stack (83.82 mm =
3.3 in, which ORNL's 2004 design report ORNL/TM-2004/137 confirms).
"""

from __future__ import annotations

from os.path import join
from pathlib import Path

IN = 0.0254
SOURCE = "ORNL/TM-2005/33 Fig. 21"
OUT = Path(__file__).resolve().parent / "Toyota_Prius_ORNL.json"

# (object path, attribute, value in inches, how the drawing gives it)
CHANGES = [
    ("stator", "Rext", 10.600 / 2, "stator OD 10.600 in"),
    ("stator", "Rint", 6.375 / 2, "stator bore 6.375 in"),
    ("rotor", "Rext", 6.314 / 2, "rotor OD 6.314 in"),
    ("rotor", "Rint", 4.356 / 2, "rotor ID 4.356 in"),
    ("shaft", "Drsh", 4.356, "shaft diameter = rotor ID 4.356 in"),
    ("stator.slot", "W0", 0.076, "slot opening 0.076 in"),
    ("stator.slot", "H0", 0.040, "tooth tip height 0.040 in"),
    ("stator.slot", "H1", 0.0, "flat shoulder under the tooth tip (inset)"),
    ("stator.slot", "W1", 0.124, "slot width 0.124 in at the shoulder (main view 0.1246 in)"),
    ("stator.slot", "W2", 0.222, "round end 0.222 in diameter"),
    ("stator.slot", "R1", 0.222 / 2, "round end radius = 0.222 in / 2"),
    ("stator.slot", "H2", 1.320 - 0.040, "slot depth 1.320 in minus the tooth tip 0.040 in (SlotW11: depth = H0 + H1 + H2)"),
]


# rotor pocket (HoleM50): (object path, attribute, value in metres, source label, how it was obtained)
ROTOR_CHANGES = [
    ("rotor.hole.0", "H3", 6.80e-3, "6.80 mm", "Fig. 21 pocket thickness, measured from the vector outline on 8 poles (sd 0.03 mm) after correcting the figure's 1.1 % x/y stretch; the magnet fills it in HoleM50"),
    ("rotor.hole.0", "H0", 10.65e-3, "10.65 mm", "Fig. 21 outer apex depth below the rotor OD (8 poles, sd 0.03 mm, stretch corrected); the inner apex then sits at 17.78 mm, as drawn (17.76)"),
    ("rotor.hole.0", "H1", 1.45e-3, "1.45 mm", "ORNL/TM-2004/120 Table 5.3 'Bridge' (Fig. 21 red label 0.056 in = 1.42 mm)"),
    ("rotor.hole.0", "W0", 41.206e-3, "41.21 mm", "solved so the arm stays at Fig. 21's 17.4 deg to tangential (8 poles, sd 0.13 deg) with H0 and H1 above (HoleM50 ties the arm angle to H0, H1 and W0)"),
]
# magnet material, both magnets of the pole: (attribute of mat_type.mag, value, source label, how it was obtained)
MAGNET_CHANGES = [
    ("Brm20", 1.243, "1.243 T", "ORNL/TM-2004/137 Fig. 14, measured line of a Prius magnet sample, digitized (B at H = 0)"),
    ("mur_lin", 1.129, "1.129", "ORNL/TM-2004/137 Fig. 14, slope of the same line"),
]


def _materials(m):
    yield m.stator.mat_type
    yield m.rotor.mat_type
    if m.shaft and m.shaft.mat_type:
        yield m.shaft.mat_type
    for hole in m.rotor.hole:
        yield hole.magnet_0.mat_type
        yield hole.magnet_1.mat_type
    w = m.stator.winding
    if w and w.conductor:
        for k in ("cond_mat", "ins_mat"):
            if getattr(w.conductor, k, None):
                yield getattr(w.conductor, k)


def _get(m, path):
    for part in path.split("."):
        m = m[int(part)] if part.isdigit() else getattr(m, part)
    return m


def build():
    from pyleecan.definitions import DATA_DIR
    from pyleecan.Functions.load import load

    m = load(join(DATA_DIR, "Machine", "Toyota_Prius.json"))
    rows = []
    for path, attr, inches, note in CHANGES:
        obj = _get(m, path)
        old, new = getattr(obj, attr), inches * IN
        setattr(obj, attr, new)
        rows.append((f"{path}.{attr}", old, new, note))
    for path, attr, value, label, note in ROTOR_CHANGES:
        obj = _get(m, path)
        old = getattr(obj, attr)
        setattr(obj, attr, value)
        rows.append((f"{path}.{attr}", old, value, f"{label}: {note}"))
    mags = [mag for hole in m.rotor.hole for mag in (hole.magnet_0, hole.magnet_1)]
    for attr, value, label, note in MAGNET_CHANGES:
        old = {getattr(mag.mat_type.mag, attr) for mag in mags}
        if len(old) != 1:
            raise ValueError(f"the magnets disagree on {attr}: {old}")
        for mag in mags:
            setattr(mag.mat_type.mag, attr, value)
        rows.append((f"magnets.mat_type.mag.{attr}", old.pop(), value, f"{label}: {note}"))
    m.name = "Toyota_Prius_ORNL"
    m.desc = (f"2004 Toyota Prius: Pyleecan's Toyota_Prius.json with the stator, rotor and slot dimensions of {SOURCE}, "
              "the pocket thickness from the same figure, the bridge from ORNL/TM-2004/120 and the magnet B-H line from "
              "ORNL/TM-2004/137 Fig. 14 (see models/motor/build_prius_ornl.py); magnet width, laminations and winding "
              "unchanged.")
    m.stator.slot.check()
    m.rotor.hole[0].check()
    # Pyleecan's bundled file carries absolute material paths from its authors' computer; keep the file
    # names only, so no personal path is committed (tests/test_privacy.py)
    for mat in {id(x): x for x in _materials(m)}.values():
        if mat.path and ("/" in mat.path or "\\" in mat.path):
            mat.path = mat.path.replace("\\", "/").rsplit("/", 1)[-1]
    m.save(str(OUT))
    return m, rows


def main():
    m, rows = build()
    print("| Parameter | Pyleecan file | Ours | Difference | Source |")
    print("|---|---|---|---|---|")
    for name, old, new, note in rows:
        diff = "" if not old else f"{100 * (new - old) / old:+.1f} %"
        k, u = (1, "") if name.startswith("magnets.") else (1e3, " mm")
        print(f"| {name} | {k * old:.3f}{u} | {k * new:.3f}{u} | {diff} | {note} |")
    s = m.stator.slot
    print(f"\nair gap {1e3 * (m.stator.Rint - m.rotor.Rext):.4f} mm; slot depth H0+H1+H2 {1e3 * (s.H0 + s.H1 + s.H2):.3f} mm; "
          f"slot area {1e6 * s.comp_surface():.1f} mm^2, active {1e6 * s.comp_surface_active():.1f} mm^2")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

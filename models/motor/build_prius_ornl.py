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

What stays Pyleecan's (no published source in hand yet): the magnet pockets (HoleM50; Fig. 21 draws them but does not
dimension them, apart from two red labels 0.060 in and 0.056 in that look like the bridges, against Pyleecan's
H1 = 1.5 mm), the magnets and their material, the laminations' material (M400-50A), the winding (9 turns per coil;
the same report's text gives 9 conductor bundles per slot) and the stack (83.82 mm = 3.3 in, which ORNL's 2004
design report ORNL/TM-2004/137 confirms).
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


def _get(m, path):
    for part in path.split("."):
        m = getattr(m, part)
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
    m.name = "Toyota_Prius_ORNL"
    m.desc = (f"2004 Toyota Prius: Pyleecan's Toyota_Prius.json with the stator, rotor and slot dimensions of {SOURCE} "
              "(see models/motor/build_prius_ornl.py); magnets, materials and winding unchanged.")
    m.stator.slot.check()
    m.save(str(OUT))
    return m, rows


def main():
    m, rows = build()
    print(f"| Parameter | Pyleecan file (mm) | {SOURCE} (mm) | Difference | Drawing |")
    print("|---|---|---|---|---|")
    for name, old, new, note in rows:
        diff = "" if not old else f"{100 * (new - old) / old:+.1f} %"
        print(f"| {name} | {1e3 * old:.3f} | {1e3 * new:.3f} | {diff} | {note} |")
    s = m.stator.slot
    print(f"\nair gap {1e3 * (m.stator.Rint - m.rotor.Rext):.4f} mm; slot depth H0+H1+H2 {1e3 * (s.H0 + s.H1 + s.H2):.3f} mm; "
          f"slot area {1e6 * s.comp_surface():.1f} mm^2, active {1e6 * s.comp_surface_active():.1f} mm^2")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

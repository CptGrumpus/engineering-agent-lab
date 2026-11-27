"""A bolted flange-plated FR moment connection, beam to column flange (steel frame study, part 2): every limit state
of AISC 360-22 that Example II.B-1 of the v16.0 Design Examples checks, plus the ones a knee joint (the beam at the
column's top) adds: the column-end forms of J10, panel-zone shear (J10.6) and a cap plate as the transverse
stiffener (J10.7, J10.8) where the column flange or web alone does not carry the top flange force.

Units kip and inch (as validation/aisc_connections.py). Sections are Shapes Database dicts (validation/aisc360.shape).

Geometry `g` (inch):
  bolt:  {"d", "Fnv"}                                    diameter, nominal shear stress (54 ksi: Group A, threads N)
  fp:    {"b", "t", "Fy", "Fu", "gage", "n", "s", "le", "lev_beam", "D16"}
         flange plates (top and bottom alike): width, thickness, two bolt lines `gage` apart with `n` bolts each at
         pitch `s`; `le` from the last bolt to the plate's end, `lev_beam` from the first bolt to the beam's end;
         fillet welds of `D16` sixteenths on both faces across the plate's width to the column flange
  wp:    {"L", "t", "Fy", "Fu", "n", "s", "le", "leh", "D16"}
         single web plate: length, thickness, `n` bolts at `s`, vertical edge `le`, horizontal edge `leh`; welded
         both sides over L to the column flange
  col:   {"z_top", "z_bot"}   distance from the column's end to the top and bottom flange plates (None: far away)
  cap:   optional {"t", "b", "Fy"} a stiffener (cap plate) at the top flange plate: thickness, width each side of
         the web, yield stress
Forces: Mu (kip-in), Vu (kip), Pu (the beam's axial force, kip, either sign: |Pu| / 2 is added to each flange force),
Vc (the column's shear just below the joint, kip, for the panel zone; 0 conservative). At a knee the column's axial
force is the beam's shear, so Vu is the panel zone's Pr (J10-10).
"""

from __future__ import annotations

from validation import aisc_connections as c

FY, FU = 50.0, 65.0          # the beam and column: ASTM A992


def _ply(d, t, Fu, lc, Fnv):
    return c.bolt_strength(d, t, Fu, lc, Fnv)


def checks(beam: dict, col: dict, g: dict, Mu: float, Vu: float, Pu: float = 0.0, Vc: float = 0.0) -> list[dict]:
    """Each limit state as {"id", "text", "demand", "capacity", "ratio"} (phi R_n, LRFD)."""
    d, Fnv = g["bolt"]["d"], g["bolt"].get("Fnv", 54.0)
    dh = c.hole_std(d)
    a = dh + 1 / 16                                    # hole width for net areas (B4.3b)
    fp, wp, cz = g["fp"], g["wp"], g.get("col", {})
    out = []

    def add(cid, text, demand, capacity):
        out.append({"id": cid, "text": text, "demand": demand, "capacity": capacity, "ratio": demand / capacity})

    Pf_bolts = Mu / beam["d"] + abs(Pu) / 2                    # at the faying surface (Manual Eq. 11-1)
    Pf_plate = Mu / (beam["d"] + fp["t"]) + abs(Pu) / 2        # at the plates' mid-thickness

    # the beam at its bolt holes (F13.1)
    Afg = beam["bf"] * beam["tf"]
    Afn = Afg - 2 * a * beam["tf"]
    phiMn = c.flange_rupture_moment(FY, FU, Afg, Afn, beam["Sx"])
    if phiMn is not None:
        add("beam_flange_rupture", "beam flexure at the flange bolt holes (F13-1)", Mu, phiMn)

    # web plate: bolts (plate edge bolt + interior; beam web: no edge, all interior), shear, block shear, welds
    t_web = beam["tw"]
    edge = min(_ply(d, wp["t"], wp["Fu"], wp["le"] - dh / 2, Fnv), _ply(d, t_web, FU, wp["s"] - dh, Fnv))
    inner = min(_ply(d, wp["t"], wp["Fu"], wp["s"] - dh, Fnv), _ply(d, t_web, FU, wp["s"] - dh, Fnv))
    add("web_bolts", "web plate bolt group: shear, bearing, tearout (J3.6, J3.11)", Vu, edge + (wp["n"] - 1) * inner)
    add("web_plate_shear_yield", "web plate shear yielding (J4-3)", Vu, c.shear_yield(wp["Fy"], wp["L"] * wp["t"]))
    add("web_plate_shear_rupture", "web plate shear rupture (J4-4)", Vu,
        c.shear_rupture(wp["Fu"], (wp["L"] - wp["n"] * a) * wp["t"]))
    agv = (wp["n"] - 1) * wp["s"] + wp["le"]
    add("web_plate_block_shear", "web plate block shear (J4-5)", Vu,
        c.block_shear(wp["Fy"], wp["Fu"], agv * wp["t"], (agv - (wp["n"] - 0.5) * a) * wp["t"],
                      (wp["leh"] - 0.5 * a) * wp["t"]))
    add("web_plate_welds", "web plate fillet welds to the column flange (J2.4)", Vu,
        2 * c.fillet_weld(wp["D16"], wp["L"]))
    add("column_flange_rupture_web_welds", "column flange shear rupture along the web plate welds (J4-4)", Vu,
        c.shear_rupture(FU, 2 * wp["L"] * col["tf"]))

    # flange plates: bolts, tension, compression, block shear, welds; the beam flange's block shear
    per_bolt_edge = min(_ply(d, fp["t"], fp["Fu"], fp["le"] - dh / 2, Fnv),
                        _ply(d, beam["tf"], FU, fp["lev_beam"] - dh / 2, Fnv))
    per_bolt_in = min(_ply(d, fp["t"], fp["Fu"], fp["s"] - dh, Fnv), _ply(d, beam["tf"], FU, fp["s"] - dh, Fnv))
    add("flange_bolts", "flange plate bolt group, two lines: shear, bearing, tearout (J3.6, J3.11)", Pf_bolts,
        2 * (per_bolt_edge + (fp["n"] - 1) * per_bolt_in))
    add("flange_plate_tension_yield", "tension flange plate yielding (J4-1)", Pf_plate,
        c.tension_yield(fp["Fy"], fp["b"] * fp["t"]))
    add("flange_plate_tension_rupture", "tension flange plate rupture, U = 1.0 (J4-2)", Pf_plate,
        c.tension_rupture(fp["Fu"], (fp["b"] - 2 * a) * fp["t"]))
    add("flange_plate_compression", "compression flange plate, K = 0.65 between bolts (J4.4)", Pf_plate,
        c.compression_short(fp["Fy"], fp["b"], fp["t"], fp["s"]))
    lgv = (fp["n"] - 1) * fp["s"] + fp["le"]
    leh = (fp["b"] - fp["gage"]) / 2
    add("flange_plate_block_shear_1", "flange plate block shear, the two outside blocks (J4-5)", Pf_plate,
        2 * c.block_shear(fp["Fy"], fp["Fu"], lgv * fp["t"], (lgv - (fp["n"] - 0.5) * a) * fp["t"],
                          (leh - 0.5 * a) * fp["t"]))
    add("flange_plate_block_shear_3", "flange plate block shear, one line and across the gage (J4-5)", Pf_plate,
        c.block_shear(fp["Fy"], fp["Fu"], lgv * fp["t"], (lgv - (fp["n"] - 0.5) * a) * fp["t"],
                      (fp["gage"] + leh - 1.5 * a) * fp["t"]))
    lgb = (fp["n"] - 1) * fp["s"] + fp["lev_beam"]
    lehb = (beam["bf"] - fp["gage"]) / 2
    add("beam_flange_block_shear", "beam flange block shear outside the bolt lines (J4-5)", Pf_bolts,
        2 * c.block_shear(FY, FU, lgb * beam["tf"], (lgb - (fp["n"] - 0.5) * a) * beam["tf"],
                          (lehb - 0.5 * a) * beam["tf"]))
    add("flange_plate_welds", "flange plate fillet welds across the column flange, both faces, k_ds 1.5 (J2.4)",
        Pf_plate, 2 * c.fillet_weld(fp["D16"], fp["b"], theta_deg=90))

    # the column (J10): tension at the top plate, compression at the bottom plate
    zt, zb = cz.get("z_top"), cz.get("z_bot")
    end_t = zt is not None
    flb = c.flange_local_bending(FY, col["tf"], near_end=end_t and zt < 10 * col["tf"])
    wly_t = c.web_local_yielding(FY, col["tw"], col["kdes"], fp["t"], near_end=end_t and zt < col["d"])
    cap = g.get("cap")
    if cap:
        need = max(Pf_plate - min(flb, wly_t), 0.0)
        add("cap_plate_yield", "cap plate (stiffener) at the tension plate: force beyond the column's own strength "
            "(J10.7, J10-1 / J10-3), tension yielding", max(need, 1e-12),
            0.90 * cap["Fy"] * 2 * cap["b"] * cap["t"])
        add("cap_plate_width", "stiffener width + tw / 2 at least a third of the plate width (J10.8): b_plate/3 "
            "against b + tw/2", fp["b"] / 3, cap["b"] + col["tw"] / 2)
        add("cap_plate_thickness", "stiffener thickness at least half the plate's (J10.8)", fp["t"] / 2, cap["t"])
    else:
        add("column_flange_local_bending", "column flange local bending at the tension plate (J10.1)", Pf_plate, flb)
        add("column_web_yielding_top", "column web local yielding at the tension plate (J10.2)", Pf_plate, wly_t)
    end_b = zb is not None
    add("column_web_yielding_bottom", "column web local yielding at the compression plate (J10.2)", Pf_plate,
        c.web_local_yielding(FY, col["tw"], col["kdes"], fp["t"], near_end=end_b and zb < col["d"]))
    add("column_web_crippling", "column web local crippling at the compression plate (J10.3)", Pf_plate,
        c.web_crippling(FY, col["tw"], col["tf"], col["d"], fp["t"], near_end=end_b and zb < col["d"] / 2))
    Pc = FY * col["A"]
    add("panel_zone_shear", "column panel-zone shear, flange force less the column shear (J10.6a)",
        max(Pf_bolts - abs(Vc), 1e-12), c.panel_zone_shear(FY, col["d"], col["tw"], abs(Vu), Pc))
    return out

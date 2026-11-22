"""Lumped steady thermal network of our 2004 Prius machine (study 7), built from the machine geometry. Pure numpy.

Each solid region is one node at its mean temperature, connected by T-equivalent circuits (Mellor, Roberts and Turner,
"Lumped parameter thermal model for electrical machines of TEFC design", IEE Proc. B 138(5), 1991): a slab or a
cylinder with uniform heat generation is a centre point with a resistance to each face and a negative resistance from
the centre to the mean-temperature node, where the loss is injected. With that, each node's temperature is the exact
volume mean of the 1D conduction solution through it (tests/test_motor_thermal.py checks this against the closed form).

Nodes (the whole machine; the two ends are symmetric and lumped):
  coolant (fixed)  housing  yoke (stator back iron)  teeth  winding in the slots  end windings  end-space air  rotor
plus face nodes: yoke outer face, yoke inner face (= tooth roots and slot bottoms), stator bore (tooth tips), winding
surface (inside the slot liner), slot exits (where the conductors leave the stack), rotor outer face.

Paths:
  slot winding -> (across the slot: slab of the mean slot width, both sides) -> winding surface -> slot liner ->
      tooth flanks (share of the liner perimeter) and slot bottoms (yoke inner face)
  slot winding -> (along the stack: slab of the stack length, axial copper conductivity) -> slot exits
  end windings -> (along the end turn, both ways to the slot exits: slab of the end-connection length) -> slot exits
  end windings -> end-space air (convection over the end-winding surface)
  teeth: radial slab from the bore to the tooth roots; the flanks reach the tooth mean through w_t / (6 k A)
  yoke: radial cylinder from the slot bottom radius to the stator OD
  yoke outer face -> interface gap -> housing -> jacket film -> coolant
  stator bore <- air gap (conduction, Nu = 2 on 2 g) <- rotor outer face; rotor: radial cylinder, adiabatic bore
  rotor end faces and housing end caps <-> end-space air (end-space correlations)

Hotspots: in the slot cross-section, peak = surface + 1.5 (mean - surface), the slab value (the CalculiX slot-pitch
check measures it); in the end turn, peak = slot exit + 1.5 (mean - slot exit). The winding hotspot is the larger.
Magnets carry no loss in this model (magnet eddy loss is outside the efficiency model too), so they sit at the rotor
temperature; the rotor's mean node stands for them.
"""

from __future__ import annotations

import math

import numpy as np

K_AIR = 0.03  # W/(m K) near 100 C; the air-gap and interface conduction use it


# ---------------------------------------------------------------------------------------------- T-equivalent pieces
def slab_teq(length: float, area: float, k: float) -> tuple[float, float]:
    """Slab of thickness `length` across `area`: (R from the centre to each face, R from the centre to the mean
    node, negative)."""
    return length / (2 * k * area), -length / (6 * k * area)


def cyl_teq(r_in: float, r_out: float, length: float, k: float) -> tuple[float, float, float]:
    """Hollow cylinder, radial conduction: (R centre -> outer face, R centre -> inner face, R centre -> mean node).
    Mellor et al. 1991, eq. for the radial T-equivalent of a cylinder with uniform generation."""
    r1, r2 = r_out, r_in
    lg = math.log(r1 / r2)
    d = r1 ** 2 - r2 ** 2
    c = 1 / (4 * math.pi * k * length)
    R_out = c * (1 - 2 * r2 ** 2 * lg / d)
    R_in = c * (2 * r1 ** 2 * lg / d - 1)
    R_c = -1 / (8 * math.pi * k * length * d) * (r1 ** 2 + r2 ** 2 - 4 * r1 ** 2 * r2 ** 2 * lg / d)
    return R_out, R_in, R_c


def end_space_k(p: dict, surface: str) -> tuple[float, float, float]:
    return tuple(float(p[f"h_{surface}_k{i}"]) for i in (1, 2, 3))


def end_space_h(v_m_s: float, k1: float, k2: float, k3: float, scale: float = 1.0) -> float:
    """h = k1 + k2 v^k3 (W/m^2 K), v the rotor peripheral speed (m/s); the form of Boglietti and Cavagnino 2007 eq. 1,
    h = k1 (1 + k2' v^k3), with k2 = k1 k2'."""
    return scale * (k1 + k2 * v_m_s ** k3)


# --------------------------------------------------------------------------------------------------------- network
class Network:
    """Linear conductance network: named nodes, resistances, heat sources, fixed temperatures."""

    def __init__(self):
        self.nodes: list[str] = []
        self.edges: list[tuple[str, str, float]] = []
        self.src: dict[str, float] = {}
        self.fixed: dict[str, float] = {}

    def _n(self, name):
        if name not in self.nodes:
            self.nodes.append(name)
        return name

    def R(self, a, b, r):
        if not np.isfinite(r) or r == 0:
            raise ValueError(f"bad resistance {a}-{b}: {r}")
        self.edges.append((self._n(a), self._n(b), float(r)))

    def Q(self, a, w):
        self.src[self._n(a)] = self.src.get(a, 0.0) + float(w)

    def fix(self, a, t):
        self.fixed[self._n(a)] = float(t)

    def solve(self) -> dict:
        idx = {n: i for i, n in enumerate(self.nodes)}
        n = len(self.nodes)
        G = np.zeros((n, n))
        for a, b, r in self.edges:
            i, j, g = idx[a], idx[b], 1 / r
            G[i, i] += g
            G[j, j] += g
            G[i, j] -= g
            G[j, i] -= g
        q = np.array([self.src.get(m, 0.0) for m in self.nodes])
        free = [i for i, m in enumerate(self.nodes) if m not in self.fixed]
        fx = [i for i, m in enumerate(self.nodes) if m in self.fixed]
        T = np.zeros(n)
        T[fx] = [self.fixed[self.nodes[i]] for i in fx]
        A = G[np.ix_(free, free)]
        rhs = q[free] - G[np.ix_(free, fx)] @ T[fx]
        T[free] = np.linalg.solve(A, rhs)
        temps = {m: float(T[idx[m]]) for m in self.nodes}
        # heat leaving through the fixed nodes (to the sinks) and the balance against the sources
        q_sink = float(np.sum(q[fx] - G[fx] @ T))  # heat each fixed node absorbs
        q_src = float(np.sum(q))
        return {"T": temps, "q_sources_W": q_src, "q_sinks_W": q_sink,
                "balance_rel": abs(q_src - q_sink) / max(abs(q_src), 1e-30)}

    def flow(self, temps, a, b) -> float:
        """Heat flow a -> b summed over the edges joining them (W)."""
        return sum((temps[x] - temps[y]) / r if (x, y) == (a, b) else (temps[y] - temps[x]) / r
                   for x, y, r in self.edges if {x, y} == {a, b})


# -------------------------------------------------------------------------------------------------------- geometry
def geometry(p: dict) -> dict:
    """Derived dimensions (SI) from the case parameters (mm in the case)."""
    mm = 1e-3
    g = {}
    Zs = int(p["n_slots"])
    L = float(p["stack_length_mm"]) * mm
    r_so, r_bore = float(p["stator_outer_radius_mm"]) * mm, float(p["stator_bore_radius_mm"]) * mm
    x1 = float(p["slot_shoulder_x_mm"]) * mm          # slot frame: x radial along the slot axis, y tangential
    w1, w2 = float(p["slot_width_shoulder_mm"]) * mm, float(p["slot_width_round_mm"]) * mm
    xc = float(p["slot_round_centre_x_mm"]) * mm
    R1 = w2 / 2
    t_l = float(p["liner_thickness_mm"]) * mm
    r_sb = xc + R1                                    # slot bottom on the slot axis
    # slot region below the shoulder (the winding's envelope including the liner): trapezoid + half disc
    a_trap = (w1 + w2) / 2 * (xc - x1)
    a_slot = a_trap + math.pi * R1 ** 2 / 2
    side = math.hypot(xc - x1, (w2 - w1) / 2)
    perim_side = 2 * side
    perim_round = math.pi * R1
    perim = perim_side + perim_round                  # liner length (the shoulder face is the wedge: adiabatic)
    # winding region inside the liner
    w1i, w2i, R1i = w1 - 2 * t_l, w2 - 2 * t_l, R1 - t_l
    a_wind = (w1i + w2i) / 2 * (xc - x1) + math.pi * R1i ** 2 / 2
    a_liner = a_slot - a_wind
    depth = (xc - x1) + R1i                           # winding depth along the slot axis
    w_mean = a_wind / depth                           # mean winding width (slab thickness across the slot)
    # iron: teeth from the bore to r_sb, yoke from r_sb to the OD (per slot pitch, then x Zs)
    theta = 2 * math.pi / Zs
    a_ring_teeth = theta / 2 * (r_sb ** 2 - r_bore ** 2)
    x0 = math.sqrt(r_bore ** 2 - (float(p["slot_opening_mm"]) * mm / 2) ** 2)
    a_opening = float(p["slot_opening_mm"]) * mm * (x1 - x0)  # slot opening (air/wedge) between the tooth tips
    a_teeth = a_ring_teeth - a_slot - a_opening               # per slot pitch (the arc segment at the bore ignored)
    a_yoke = theta / 2 * (r_so ** 2 - r_sb ** 2)
    r_mid_tooth = (r_bore + r_sb) / 2
    w_tooth = a_teeth / (r_sb - r_bore)                       # mean tooth width
    g.update(Zs=Zs, L=L, r_so=r_so, r_bore=r_bore, r_sb=r_sb, x1=x1, xc=xc, R1=R1, w1=w1, w2=w2, t_l=t_l,
             a_slot=a_slot, a_wind=a_wind, a_liner=a_liner, perim=perim, perim_side=perim_side,
             perim_round=perim_round, depth=depth, w_mean=w_mean, a_teeth=a_teeth, a_yoke=a_yoke,
             w_tooth=w_tooth, r_mid_tooth=r_mid_tooth, tooth_len=r_sb - r_bore, theta=theta)
    # copper
    a_cu = float(p["copper_area_per_slot_mm2"]) * mm ** 2
    g["fill_winding"] = a_cu / a_wind                         # copper fraction of the winding region
    # rotor
    g["r_ro"], g["r_ri"] = float(p["rotor_outer_radius_mm"]) * mm, float(p["rotor_inner_radius_mm"]) * mm
    g["gap"] = r_bore - g["r_ro"]
    # end windings: an annulus of the slot depth by the axial extension, at the mean slot radius
    g["l_end"] = float(p["end_connection_length_mm"]) * mm   # conductor length outside the stack, per side
    g["ext"] = float(p["end_extension_mm"]) * mm            # axial extension of the end winding, per side
    g["r_ew"] = (r_bore + r_sb) / 2
    g["a_cu_slot"] = a_cu
    g["slot_opening"] = float(p["slot_opening_mm"]) * mm
    return g


def winding_conductivity(p: dict, g: dict) -> tuple[float, float]:
    """(across the slot, along the conductors) in W/(m K). Across: impregnant with copper strands, Maxwell-Garnett /
    Hashin-Shtrikman lower bound for highly conducting cylinders, k_imp (1 + phi) / (1 - phi). Along: copper fraction
    times copper."""
    phi = g["fill_winding"]
    k_imp, k_cu = float(p["impregnant_conductivity_W_mK"]), float(p["copper_conductivity_W_mK"])
    k_x = float(p.get("winding_k_scale", 1.0)) * k_imp * (1 + phi) / (1 - phi)
    return k_x, phi * k_cu


# -------------------------------------------------------------------------------------------------- the networks
def stator_section(net: Network, p: dict, g: dict, *, L: float, q_wind: float, q_teeth: float, q_yoke: float,
                   prefix: str = "") -> None:
    """The stator's cross-section part for a stack length L (all Zs slots): slot winding, liner, teeth, yoke.
    Nodes: W (winding mean), WS (winding surface), T (teeth mean), Tc, B (bore), Y (yoke mean), Yc, YI (yoke inner
    face = tooth roots and slot bottoms), YO (yoke outer face)."""
    P = prefix
    Zs = g["Zs"]
    k_fe = float(p["lamination_conductivity_W_mK"])
    k_x, _ = winding_conductivity(p, g)
    # winding across the slot: slab of thickness w_mean, area depth x L per slot, both sides
    A_w = g["depth"] * L * Zs
    Rh, Rc = slab_teq(g["w_mean"], A_w, k_x)
    net.R(P + "Wc", P + "W", Rc)   # negative: centre -> mean
    net.R(P + "Wc", P + "WS", Rh / 2)  # both faces in parallel
    net.Q(P + "W", q_wind)
    # liner: thin wall over the slot perimeter, split between the tooth flanks and the slot bottoms
    k_l = float(p["liner_conductivity_W_mK"])
    R_liner = g["t_l"] / (k_l * g["perim"] * L * Zs)
    f_side = g["perim_side"] / g["perim"]
    net.R(P + "WS", P + "LF", R_liner / f_side)
    net.R(P + "WS", P + "YI", R_liner / (1 - f_side))
    # teeth: flanks -> tooth mean, w_t / (6 k A_flanks); radial slab from the bore (B) to the roots (YI)
    A_fl = 2 * g["depth"] * L * Zs
    net.R(P + "LF", P + "T", g["w_tooth"] / (6 * k_fe * A_fl))
    Rh_t, Rc_t = slab_teq(g["tooth_len"], g["w_tooth"] * L * Zs, k_fe)
    net.R(P + "Tc", P + "T", Rc_t)
    net.R(P + "Tc", P + "B", Rh_t)
    net.R(P + "Tc", P + "YI", Rh_t)
    net.Q(P + "T", q_teeth)
    # yoke: radial cylinder r_sb -> r_so
    Ro, Ri, Rcy = cyl_teq(g["r_sb"], g["r_so"], L, k_fe)
    net.R(P + "Yc", P + "Y", Rcy)
    net.R(P + "Yc", P + "YO", Ro)
    net.R(P + "Yc", P + "YI", Ri)
    net.Q(P + "Y", q_yoke)


def outer_resistance(p: dict, g: dict, L: float) -> float:
    """Yoke outer face -> coolant over a stack length L: interface gap, housing wall, jacket film (series)."""
    A_so = 2 * math.pi * g["r_so"] * L
    R_int = float(p["interface_gap_mm"]) * 1e-3 / (K_AIR * A_so)
    r_h = g["r_so"] + float(p["housing_wall_mm"]) * 1e-3
    R_h = math.log(r_h / g["r_so"]) / (2 * math.pi * float(p["housing_conductivity_W_mK"]) * L)
    R_j = 1 / (float(p["jacket_htc_W_m2K"]) * 2 * math.pi * r_h * L)
    return R_int + R_h + R_j


def air_gap_h(p: dict, g: dict) -> float:
    """Conduction across the gap (laminar Couette, Nu = 2 on the hydraulic diameter 2 g): h = k / g, times a stated
    factor for the vortex regime (1 = conduction only, the lower bound)."""
    return float(p.get("air_gap_h_factor", 1.0)) * K_AIR / g["gap"]


def machine(p: dict, g: dict, losses: dict, speed_rpm: float) -> tuple[Network, dict]:
    """The whole machine. losses: W for 'cu_slot', 'cu_end', 'fe_teeth', 'fe_yoke', 'fe_rotor'."""
    net = Network()
    L = g["L"]
    Zs = g["Zs"]
    stator_section(net, p, g, L=L, q_wind=losses["cu_slot"], q_teeth=losses["fe_teeth"], q_yoke=losses["fe_yoke"])
    _, k_z = winding_conductivity(p, g)
    k_cu = float(p["copper_conductivity_W_mK"])
    # slot winding along the stack: slab of length L (centre at mid-stack), copper fraction conductivity, both ends
    Rh_z, Rc_z = slab_teq(L, g["a_wind"] * Zs, k_z)
    net.R("Wz", "W", Rc_z)
    net.R("Wz", "X", Rh_z / 2)
    # end windings (both ends): each end turn runs l_end between two slot exits; slab of length l_end on the copper
    # section of all slots, both ends of the turn at the slot exits; two ends of the machine in parallel
    A_cu = g["a_cu_slot"] * Zs
    Rh_e, Rc_e = slab_teq(g["l_end"], A_cu, k_cu)
    net.R("Ec", "E", Rc_e / 2)
    net.R("Ec", "X", Rh_e / 4)
    net.Q("E", losses["cu_end"])
    # end-winding surface to end-space air (Boglietti and Cavagnino 2007 eq. 4 form: pi/2 x perimeter x pi D, two ends)
    v = 2 * math.pi * speed_rpm / 60 * g["r_ro"]
    perim_ew = 2 * (g["depth"] + g["ext"])
    S_ew = 2 * (math.pi / 2) * perim_ew * math.pi * 2 * g["r_ew"]
    sc = float(p.get("end_space_h_scale", 1.0))
    h_ew = end_space_h(v, *end_space_k(p, "winding_end_space"), scale=sc)
    net.R("E", "AIR", 1 / (h_ew * S_ew))
    # housing: the jacket wets the housing over the stack and the end-winding extensions
    L_h = L + 2 * g["ext"]
    r_h = g["r_so"] + float(p["housing_wall_mm"]) * 1e-3
    A_so = 2 * math.pi * g["r_so"] * L
    net.R("YO", "H", float(p["interface_gap_mm"]) * 1e-3 / (K_AIR * A_so)
          + math.log(r_h / g["r_so"]) / (2 * math.pi * float(p["housing_conductivity_W_mK"]) * L))
    net.R("H", "COOLANT", 1 / (float(p["jacket_htc_W_m2K"]) * 2 * math.pi * r_h * L_h))
    # end-space air to the housing: the housing bore over the extensions and the two end caps (annulus to the shaft)
    S_hs = 2 * (2 * math.pi * g["r_so"] * g["ext"] + math.pi * (g["r_so"] ** 2 - g["r_ri"] ** 2))
    h_hs = end_space_h(v, *end_space_k(p, "housing_end_space"), scale=sc)
    net.R("AIR", "H", 1 / (h_hs * S_hs))
    # rotor: radial cylinder, adiabatic bore; outer face -> air gap -> bore; end faces -> end-space air
    Ro, Ri, Rcy = cyl_teq(g["r_ri"], g["r_ro"], L, float(p["lamination_conductivity_W_mK"]))
    net.R("Rc", "ROT", Rcy)
    net.R("Rc", "RO", Ro)
    net.R("RO", "B", 1 / (air_gap_h(p, g) * 2 * math.pi * g["r_ro"] * L))
    S_re = 2 * math.pi * (g["r_ro"] ** 2 - g["r_ri"] ** 2)
    h_re = end_space_h(v, *end_space_k(p, "rotor_end_space"), scale=sc)
    net.R("ROT", "AIR", 1 / (h_re * S_re))
    net.Q("ROT", losses["fe_rotor"])
    net.fix("COOLANT", float(p["coolant_temperature_C"]))
    info = {"v_rotor_m_s": v, "h_end_winding": h_ew, "h_housing_end": h_hs, "h_rotor_end": h_re,
            "h_air_gap": air_gap_h(p, g), "S_end_winding_m2": S_ew}
    return net, info


def hotspots(T: dict) -> dict:
    slot = T["WS"] + 1.5 * (T["W"] - T["WS"])
    end = T["X"] + 1.5 * (T["E"] - T["X"])
    return {"slot_hotspot_C": slot, "end_hotspot_C": end, "winding_hotspot_C": max(slot, end),
            "winding_mean_C": None}


def steady(p: dict, g: dict, losses: dict, speed_rpm: float) -> dict:
    net, info = machine(p, g, losses, speed_rpm)
    s = net.solve()
    T = s["T"]
    h = hotspots(T)
    # copper-weighted winding mean (the temperature the phase resistance sees): slot and end lengths
    Ls, Le = g["L"], g["l_end"]
    h["winding_mean_C"] = (Ls * T["W"] + Le * T["E"]) / (Ls + Le)
    return s | h | {"info": info, "net": net}


def section_check_network(p: dict, g: dict, *, q_wind: float, q_teeth: float, q_yoke: float, t_rotor_C: float,
                          L: float = 1.0) -> dict:
    """The cross-section subnetwork alone (no axial paths): outer face -> coolant through the series outer
    resistance, bore -> fixed rotor surface temperature through the air gap. What the CalculiX slot-pitch model
    computes with the same losses and boundary conditions (per metre of stack by default)."""
    net = Network()
    stator_section(net, p, g, L=L, q_wind=q_wind, q_teeth=q_teeth, q_yoke=q_yoke)
    net.R("YO", "COOLANT", outer_resistance(p, g, L))
    net.R("B", "ROTOR", 1 / (air_gap_h(p, g) * 2 * math.pi * g["r_ro"] * L))
    net.fix("COOLANT", float(p["coolant_temperature_C"]))
    net.fix("ROTOR", t_rotor_C)
    s = net.solve()
    T = s["T"]
    s["slot_hotspot_C"] = T["WS"] + 1.5 * (T["W"] - T["WS"])
    return s

"""Single-bay portal frame analysis for AISC 360-22 Chapter C (steel frame study), on the verified plane-frame solver
(validation/frame2d.py: exact second order by stability functions, so P-delta inside each member is included without
subdividing it).

Direct Analysis Method (Specification C2): second-order analysis; all stiffnesses multiplied by 0.8 (C2.3: EA and EI;
tau_b = 1 when alpha Pr / Pns <= 0.5 in every member, checked and reported, else EI is reduced by tau_b); out-of-plumbness
by notional loads N = 0.002 alpha Y at each level (C2-1), given by the caller; effective length = unbraced length (C3).
Unit-agnostic: give everything in one consistent system.

Tested against Example C.1A of the v16.0 Design Examples (pinned-base portal with a leaning column):
tests/test_aisc_frame.py.
"""

from __future__ import annotations

from validation.frame2d import Frame


def portal(*, H: float, L: float, E: float, col: dict, beam: dict, w: float, P_tops=(0.0, 0.0), H_left: float = 0.0,
           base: str = "fixed", stiffness_factor: float = 1.0, second_order: bool = True, P_leaning: float = 0.0,
           n_col: int = 1, n_beam: int = 2, knee_k: float | None = None, knee_slip: float = 0.0) -> dict:
    """Portal: columns of height H at x = 0 and x = L, beam of span L between their tops (rigid joints).

    col, beam: section dicts with A and Ix. w: uniform gravity load on the beam (positive down). P_tops: point loads
    down at the left and right column tops. H_left: lateral load (positive to +x) at the left column top (wind or
    notional load). base: 'fixed' or 'pinned'. stiffness_factor: 0.8 for the direct analysis method (EA and EI).
    P_leaning: gravity on a leaning column (pinned both ends, height H) tied to the right column top by a pinned link.
    n_col, n_beam: members per column / beam (for force and deflection output along them; the solution is exact
    at the nodes either way).
    knee_k: rotational stiffness of each knee connection (moment per radian, nominal: stiffness_factor applies to it
    as to the members, C2.3) as a spring at each end of the beam; None: rigid knees. knee_slip: a rotation the knee
    takes before its spring engages (bolt slip into bearing): M = k (theta - slip), solved exactly as a lack of fit
    (monotonic loading); a knee whose gap never closes is a hinge. knee_springs reports each knee's secant
    stiffness M / theta, knee_rotations its rotation.
    """
    if knee_k is None and knee_slip:
        raise ValueError("knee_slip needs knee_k")
    common = dict(H=H, L=L, E=E, col=col, beam=beam, w=w, P_tops=P_tops, H_left=H_left, base=base,
                  stiffness_factor=stiffness_factor, second_order=second_order, P_leaning=P_leaning, n_col=n_col,
                  n_beam=n_beam)
    if knee_k is None:
        r = _portal_once(**common, springs=None)
        r["knee_springs"] = r["knee_rotations"] = None
        return r
    k_el = knee_k * stiffness_factor
    if not knee_slip:
        r = _portal_once(**common, springs=[k_el, k_el])
    else:
        # a gap, then the spring: M = k (theta - slip) once a knee's gap has closed, linear with the slip as a lack
        # of fit (monotonic loading). Start from both knees open (hinges); a knee whose hinge rotation exceeds the
        # slip closes, its lack of fit signed as that rotation; solve again until no knee changes state.
        state = [None, None]                                   # None: open; +1 / -1: closed, the gap's sign
        for _ in range(6):
            sp = [0.0 if st is None else (k_el, st * knee_slip) for st in state]
            r = _portal_once(**common, springs=sp)
            rot = r["spring_rotations"]
            new = list(state)
            for i in range(2):
                if state[i] is None and abs(rot[i]) > knee_slip:
                    new[i] = 1.0 if rot[i] > 0 else -1.0
                elif state[i] is not None and rot[i] * state[i] < knee_slip:
                    new[i] = None                              # the spring would pull: the gap reopens
            if new == state:
                break
            state = new
        else:
            raise RuntimeError("knee slip states did not settle")
        r["knee_open"] = [st is None for st in state]
    m = [abs(v) for v in r["beam_end_moments"]]
    rot = [knee_slip + mi / k_el if knee_slip else mi / k_el for mi in m]
    r["knee_rotations"] = rot
    r["knee_springs"] = [mi / ti if ti > 0 else 0.0 for mi, ti in zip(m, rot)]       # secant
    return r


def _portal_once(*, H, L, E, col, beam, w, P_tops, H_left, base, stiffness_factor, second_order, P_leaning, n_col,
                 n_beam, springs) -> dict:
    f = Frame()
    Es = E * stiffness_factor
    bl, tl = f.node(0, 0), None
    left = [bl] + [f.node(0, H * k / n_col) for k in range(1, n_col + 1)]
    beam_nodes = [left[-1]] + [f.node(L * k / n_beam, H) for k in range(1, n_beam)]
    right_top = f.node(L, H)
    beam_nodes.append(right_top)
    right = [f.node(L, H * k / n_col) for k in range(0, n_col)] + [right_top]
    for a, b in zip(left, left[1:]):
        f.member(a, b, Es, col["A"], col["Ix"])
    for a, b in zip(right, right[1:]):
        f.member(a, b, Es, col["A"], col["Ix"])
    first_beam = len(f.members)
    pairs = list(zip(beam_nodes, beam_nodes[1:]))
    for k, (a, b) in enumerate(pairs):
        f.member(a, b, Es, beam["A"], beam["Ix"], w=-w,
                 spring_i=springs[0] if springs and k == 0 else None,
                 spring_j=springs[1] if springs and k == len(pairs) - 1 else None)
    pinned = base == "pinned"
    f.support(left[0], rz=not pinned)
    f.support(right[0], rz=not pinned)
    if P_leaning:
        lb, lt = f.node(2 * L, 0), f.node(2 * L, H)
        f.member(lb, lt, Es, col["A"], col["Ix"], release_i=True, release_j=True)
        f.member(right_top, lt, Es, beam["A"], beam["Ix"], release_i=True, release_j=True)
        f.support(lb, rz=True)                       # pinned base; the rotation has no stiffness: held
        f.support(lt, ux=False, uy=False, rz=True)
        f.load(lt, fy=-P_leaning)
    f.load(left[-1], fx=H_left, fy=-P_tops[0])
    f.load(right_top, fy=-P_tops[1])
    U = f.solve(second_order=second_order)
    ends = f.end_forces

    def col_out(nodes, start):
        """Axial force (compression +), top and base moments and base shear of a column (members bottom-up)."""
        m0, m1 = ends[start], ends[start + n_col - 1]
        return {"N": float(f.axial[start]), "M_base": float(m0[2]), "M_top": float(-m1[5]),
                "V_base": float(m0[1]), "ux_top": float(U[3 * nodes[-1]])}
    out = {"left": col_out(left, 0), "right": col_out(right, n_col),
           "drift": float((U[3 * left[-1]] + U[3 * right_top]) / 2),
           "beam_mid_uy": float(U[3 * beam_nodes[n_beam // 2] + 1]) if n_beam % 2 == 0 else None,
           "beam_N": float(f.axial[first_beam]),
           "beam_end_moments": (float(ends[first_beam][2]), float(-ends[first_beam + n_beam - 1][5])),
           "iterations": f.iterations}
    out["beam_M_mid"] = float(-ends[first_beam + n_beam // 2 - 1][5]) if n_beam % 2 == 0 else None
    out["reactions"] = {"left": [float(v) for v in f.reactions[3 * left[0]:3 * left[0] + 3]],
                        "right": [float(v) for v in f.reactions[3 * right[0]:3 * right[0] + 3]]}
    out["frame"] = f
    sr = getattr(f, "spring_rotations", {})
    out["spring_rotations"] = [sr.get(first_beam, {}).get(2, 0.0), sr.get(first_beam + n_beam - 1, {}).get(5, 0.0)]
    return out


def tau_b(alpha_Pr: float, Pns: float) -> float:
    """C2-2a / C2-2b."""
    r = alpha_Pr / Pns
    return 1.0 if r <= 0.5 else 4 * r * (1 - r)

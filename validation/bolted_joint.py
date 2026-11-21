"""Preloaded bolted joint: VDI 2230 Part 1 (2015) hand method and the friction slip limit.

Independent reference for the bolted-joint study (models/fea/bolted_joint_ccx.py). It shares no
code with the finite element path.

Through-bolted joint, two plates of total clamp length l_K, bolt nominal diameter d, washer
(head) bearing diameter d_W, hole d_h, plate outer diameter D_A.

    bolt compliance   delta_S = delta_SK + delta_1 + delta_Gew + delta_G + delta_M     (VDI 5.1.1)
                      head 0.5 d / (E A_N), shank l_1 / (E A_N), free thread l_Gew / (E A_d3),
                      engaged thread 0.5 d / (E A_d3), nut 0.4 d / (E A_N)
    plate compliance  pressure cone (VDI 5.1.2.2), D_A >= D_A,Gr:
                      tan phi = 0.362 + 0.032 ln(beta_L / 2) + 0.153 ln y, beta_L = l_K / d_W, y = D_A / d_W
                      delta_P = 2 ln[(d_W + d_h)(d_W + w l_K tan phi - d_h) /
                                     ((d_W - d_h)(d_W + w l_K tan phi + d_h))] / (w E pi d_h tan phi), w = 1
                      the cone reaches the interface at diameter D_A,Gr = d_W + w l_K tan phi
    load factor       Phi_n = n delta_P / (delta_S + delta_P)
    embedding loss    F_Z = f_Z / (delta_S + delta_P)
    opening           external axial load at which the clamp force vanishes: F_A = F_K / (1 - Phi_n)
    slip              Coulomb friction at q_F interfaces: F_Q = mu q_F F_K          (exact once the whole
                      interface slides: the total friction is mu times the total contact force)
"""

from __future__ import annotations

import numpy as np

# ISO 898 / VDI 2230 thread data for M8 (coarse): d, pitch, d3 (minor), d2 (pitch dia.)
THREADS = {"M8": {"d": 8.0, "P": 1.25, "d3": 6.466, "d2": 7.188}}


def bolt_compliance(E, thread="M8", shank_length=0.0, free_thread_length=0.0):
    t = THREADS[thread]
    d = t["d"]
    A_N = np.pi * d**2 / 4
    A_d3 = np.pi * t["d3"] ** 2 / 4
    parts = {"head": 0.5 * d / (E * A_N), "shank": shank_length / (E * A_N),
             "free_thread": free_thread_length / (E * A_d3), "engaged_thread": 0.5 * d / (E * A_d3),
             "nut": 0.4 * d / (E * A_N)}
    return float(sum(parts.values())), parts


def cone_tan_phi(l_K, d_W, D_A):
    return 0.362 + 0.032 * np.log(l_K / d_W / 2) + 0.153 * np.log(D_A / d_W)


def cone_limit_diameter(l_K, d_W, D_A, w=1.0):
    return d_W + w * l_K * cone_tan_phi(l_K, d_W, D_A)


def plate_compliance(E, l_K, d_W, d_h, D_A, w=1.0):
    """Clamped-plate compliance by the VDI pressure cone (D_A at least the cone limit)."""
    tphi = cone_tan_phi(l_K, d_W, D_A)
    if D_A < cone_limit_diameter(l_K, d_W, D_A, w):
        raise ValueError("plate narrower than the cone limit: the sleeve-and-cone formula applies")
    a = d_W + w * l_K * tphi
    return float(2 * np.log((d_W + d_h) * (a - d_h) / ((d_W - d_h) * (a + d_h))) / (w * E * np.pi * d_h * tphi))


def load_factor(delta_S, delta_P, n=1.0):
    return n * delta_P / (delta_S + delta_P)


def embedding_loss(f_Z, delta_S, delta_P):
    return f_Z / (delta_S + delta_P)


def opening_load(F_K, phi_n):
    return F_K / (1 - phi_n)


def slip_load(mu, F_K, interfaces=1):
    return mu * interfaces * F_K

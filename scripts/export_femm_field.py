"""Export a saved FEMM magnetostatic solution (.ans) for the site's field render: nodes, triangles, FEMM group and |B| per
element (npz), and the circuit fluxes per metre of depth (json) so the export can be checked against the run's
flux_linkage.csv. Runs in the Pyleecan environment; FEMM must be free (one FEMM at a time).

    ~/.venvs/pyleecan/Scripts/python.exe scripts/export_femm_field.py <solution.ans> <out.npz>

Pyleecan overwrites its .ans per machine name on every run: copy the evidence run's .ans to build/ first.
"""
import sys, json, math, femm, numpy as np
ans, out = sys.argv[1], sys.argv[2]
femm.openfemm(1); femm.opendocument(ans)
nn, ne = int(femm.mo_numnodes()), int(femm.mo_numelements())
nodes = np.array([femm.mo_getnode(i)[:2] for i in range(1, nn + 1)])
tri = np.zeros((ne, 3), int); bmag = np.zeros(ne); grp = np.zeros(ne, int); cen = np.zeros((ne, 2))
for k in range(1, ne + 1):
    e = femm.mo_getelement(k)          # n1 n2 n3 xc yc area group
    tri[k-1] = [int(e[0]) - 1, int(e[1]) - 1, int(e[2]) - 1]; cen[k-1] = e[3:5]; grp[k-1] = int(e[6])
    bx, by = femm.mo_getb(e[3], e[4]); bmag[k-1] = math.hypot(bx, by)
circ = {c: femm.mo_getcircuitproperties(c)[2] for c in ("Circs0", "Circs1", "Circs2")}  # flux linkage per 1 m depth
femm.closefemm()
np.savez_compressed(out, nodes_m=nodes, tri=tri, bmag_T=bmag, group=grp, centroid_m=cen)
json.dump({"nodes": nn, "elements": ne, "circuit_flux_Wb_per_m": circ, "bmag_max_T": float(bmag.max()),
           "groups": sorted(set(int(g) for g in grp))}, open(out.replace(".npz", ".json"), "w"), indent=1)
print(nn, ne, circ, round(float(bmag.max()), 3))

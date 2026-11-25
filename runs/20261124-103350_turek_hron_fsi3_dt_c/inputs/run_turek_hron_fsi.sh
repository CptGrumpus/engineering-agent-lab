#!/bin/bash
# Run one Turek-Hron FSI case inside WSL: convert the fluid mesh (written by Gmsh on the Windows side as
# fluid/mesh.msh), set the patch types, check the mesh, then run both preCICE participants together.
# usage: run_turek_hron_fsi.sh <case_dir> <openfoam_v2512_etc_bashrc>
# Exit codes: 10 bad case dir, 11 OpenFOAM environment, 19 gmshToFoam, 18 patch types, 20 checkMesh,
#             21 frozen motion diffusivity,
#             30 solid participant failed, 31 fluid participant failed, 32 writeCellCentres.
CASE="$1"; BASHRC="$2"
HERE="$(cd "$(dirname "$0")" && pwd)"
# clear the positional arguments first: `source` passes them on, and the openfoam.com bashrc parses them
# as its own options (with them it crawled for minutes; without, it loads in 0.4 s)
set --
cd "$CASE" || exit 10
source "$BASHRC" || exit 11
{
  echo "openfoam_version=$WM_PROJECT_VERSION"
  dpkg-query -W -f='openfoam_package=${Package} ${Version}\n' openfoam2512 2>/dev/null
  dpkg-query -W -f='precice=${Version}\n' libprecice3 2>/dev/null
  dpkg-query -W -f='calculix_precice=${Version}\n' calculix-precice3 2>/dev/null
  . /etc/os-release && echo "linux=$PRETTY_NAME"
} > versions.txt
cd fluid || exit 10
gmshToFoam mesh.msh > log.gmshToFoam 2>&1 || exit 19
for p in "frontAndBack empty" "walls wall" "cylinder wall" "flag wall"; do
  read -r name kind <<< "$p"
  foamDictionary constant/polyMesh/boundary -entry "entry0/$name/type" -set "$kind" > /dev/null 2>&1 || exit 18
done
checkMesh > log.checkMesh 2>&1 || exit 20
# frozen mesh-motion diffusivity (numerics mesh_motion = "frozen"): written once from the base mesh
if [ -f frozen_diffusivity.json ]; then
  python3 "$HERE/frozen_motion_diffusivity.py" . > log.motionDiffusivity 2>&1 || exit 21
fi
cd ../solid || exit 10
ccx_preCICE -i flag -precice-participant Solid > log.ccx 2>&1 &
solid_pid=$!
cd ../fluid
pimpleFoam > log.pimpleFoam 2>&1
fluid_rc=$?
wait $solid_pid
solid_rc=$?
[ $solid_rc -ne 0 ] && exit 30
[ $fluid_rc -ne 0 ] && exit 31
postProcess -func writeCellCentres -latestTime > log.writeCellCentres 2>&1 || exit 32
exit 0

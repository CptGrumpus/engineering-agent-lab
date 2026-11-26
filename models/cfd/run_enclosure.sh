#!/bin/bash
# Run one enclosure conjugate-heat-transfer case inside WSL (study 11, stage 3): blockMesh, splitMeshRegions
# (cell zones -> regions fluid, board, component), checkMesh, foamMultiRun (steady), cell centres per region.
# usage: run_enclosure.sh <case_dir> <openfoam_etc_bashrc>
# Exit codes: 10 bad case dir, 11 OpenFOAM environment, 20 blockMesh, 25 splitMeshRegions, 21 checkMesh,
#             22 foamMultiRun, 24 writeCellCentres.
CASE="$1"; BASHRC="$2"
# clear the positional arguments before `source`: the openfoam bashrc would parse them as its own options
set --
cd "$CASE" || exit 10
source "$BASHRC" || exit 11
{
  echo "openfoam_version=$WM_PROJECT_VERSION"
  dpkg-query -W -f='openfoam_package=${Package} ${Version}\n' "openfoam$WM_PROJECT_VERSION" 2>/dev/null
  . /etc/os-release && echo "linux=$PRETTY_NAME"
} > versions.txt
blockMesh > log.blockMesh 2>&1 || exit 20
splitMeshRegions -cellZones all > log.splitMeshRegions 2>&1 || exit 25
checkMesh -region fluid > log.checkMesh 2>&1 || exit 21
foamMultiRun > log.foamMultiRun 2>&1 || exit 22
# every region splitMeshRegions made (the redesign adds shell and bridge), so the final fields can be plotted
for d in constant/*/polyMesh; do
  r=$(basename "$(dirname "$d")")
  foamPostProcess -region $r -func writeCellCentres -latestTime > log.writeCellCentres.$r 2>&1 || exit 24
done
exit 0

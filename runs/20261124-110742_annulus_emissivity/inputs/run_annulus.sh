#!/bin/bash
# Run one annulus radiation case inside WSL (study 11, stage 2): blockMesh, checkMesh, steady foamRun (fluid solver
# with fvDOM), then the cell centres for the Python post-processing.
# usage: run_annulus.sh <case_dir> <openfoam_etc_bashrc>
# Exit codes: 10 bad case dir, 11 OpenFOAM environment, 20 blockMesh, 21 checkMesh, 22 foamRun, 24 writeCellCentres.
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
checkMesh > log.checkMesh 2>&1 || exit 21
foamRun > log.foamRun 2>&1 || exit 22
foamPostProcess -func writeCellCentres -latestTime > log.writeCellCentres 2>&1 || exit 24
exit 0

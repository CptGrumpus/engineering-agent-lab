#!/bin/bash
# Run one fully developed pipe-flow case inside WSL (study 19).
# usage: run_pipe.sh <case_dir> <openfoam_etc_bashrc>
# Exit codes: 10 bad case dir, 11 OpenFOAM environment, 20 blockMesh, 21 checkMesh, 22 foamRun,
#             23 writeCellCentres, 24 writeCellVolumes.
cd "$1" || exit 10
source "$2" || exit 11
{
  echo "openfoam_version=$WM_PROJECT_VERSION"
  dpkg-query -W -f='openfoam_package=${Package} ${Version}\n' "openfoam$WM_PROJECT_VERSION" 2>/dev/null
  . /etc/os-release && echo "linux=$PRETTY_NAME"
} > versions.txt
blockMesh > log.blockMesh 2>&1 || exit 20
checkMesh > log.checkMesh 2>&1 || exit 21
foamRun > log.foamRun 2>&1 || exit 22
foamPostProcess -func writeCellCentres -latestTime > log.writeCellCentres 2>&1 || exit 23
foamPostProcess -func writeCellVolumes -latestTime > log.writeCellVolumes 2>&1 || exit 24
exit 0

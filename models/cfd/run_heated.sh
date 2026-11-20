#!/bin/bash
# Run one heated-channel case inside WSL, in two stages:
#   1. foamRun with incompressibleFluid: flow (and a first pass of temperature)
#   2. foamRun with the `functions` solver on the frozen, converged flow: only the
#      scalarTransport function object runs, so thousands of temperature iterations
#      cost a fraction of a flow iteration each
# usage: run_heated.sh <case_dir> <openfoam_etc_bashrc>
# Stage 2 settings come from system/controlDict.temperature (written by the case writer).
# Exit codes: 10 bad case dir, 11 OpenFOAM environment, 20 blockMesh, 21 checkMesh,
#             22 foamRun (flow), 24 foamRun (temperature), 23 writeCellCentres.
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
cp system/controlDict system/controlDict.flow
cp system/controlDict.temperature system/controlDict
foamRun > log.foamRun.temperature 2>&1 || exit 24
foamPostProcess -func writeCellCentres -latestTime > log.writeCellCentres 2>&1 || exit 23
exit 0

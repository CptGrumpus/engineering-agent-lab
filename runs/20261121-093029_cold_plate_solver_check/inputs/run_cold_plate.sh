#!/bin/bash
# Run one cold-plate coolant case inside WSL.
# usage: run_cold_plate.sh <case_dir> <openfoam_etc_bashrc> full|temperature
#   full         blockMesh, checkMesh, flow (incompressibleFluid), then temperature alone on
#                the frozen flow (the `functions` solver), then the cell and face centres
#   temperature  continue the temperature stage from the latest time (the coupling loop
#                has already rewritten the wall gradients and endTime); log appended per pass
# Exit codes: 10 bad case dir, 11 OpenFOAM environment, 12 bad mode, 20 blockMesh,
#             21 checkMesh, 22 foamRun (flow), 24 foamRun (temperature), 23 writeCellCentres.
cd "$1" || exit 10
source "$2" || exit 11
case "$3" in
  full)
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
    ;;
  temperature)
    echo "=== coupling pass $(date -u +%H:%M:%S)" >> log.foamRun.coupling
    foamRun >> log.foamRun.coupling 2>&1 || exit 24
    ;;
  *) exit 12 ;;
esac
exit 0

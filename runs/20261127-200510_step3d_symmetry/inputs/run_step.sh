#!/bin/bash
# Run one backward-facing-step case inside WSL (study 19 part 2), on one core at the lowest priority (nice 19):
# the machine is shared with other studies and the user's own programs.
# usage: run_step.sh <case_dir> <openfoam_etc_bashrc>
# Two stages (models/cfd/step_openfoam.py): a start-up with first-order k and omega, then the second-order run.
# Exit codes: 10 bad case dir, 11 OpenFOAM environment, 20 blockMesh, 22 foamRun, 23 writeCellCentres.
# checkMesh is recorded, not a gate: its aspect-ratio test flags the wall-resolved 2D cells (checked in Python).
cd "$1" || exit 10
source "$2" || exit 11
{
  echo "openfoam_version=$WM_PROJECT_VERSION"
  dpkg-query -W -f='openfoam_package=${Package} ${Version}\n' "openfoam$WM_PROJECT_VERSION" 2>/dev/null
  . /etc/os-release && echo "linux=$PRETTY_NAME"
} > versions.txt
blockMesh > log.blockMesh 2>&1 || exit 20
checkMesh > log.checkMesh 2>&1
nice -n 19 foamRun > log.foamRun.stage1 2>&1 || exit 22
mv system/controlDict.stage2 system/controlDict && mv system/fvSchemes.stage2 system/fvSchemes || exit 22
nice -n 19 foamRun > log.foamRun 2>&1 || exit 22
foamPostProcess -func writeCellCentres -latestTime > log.writeCellCentres 2>&1 || exit 23
exit 0

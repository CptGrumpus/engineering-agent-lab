#!/bin/bash
# Run one 3D backward-facing-step case inside WSL (study 19 part 3) on <n_procs> MPI processes (1 = serial), at the
# lowest priority (nice 19, inherited by the MPI ranks) and unbound (--bind-to none: the machine is shared, so the
# scheduler places the ranks).
# usage: run_step3d.sh <case_dir> <openfoam_etc_bashrc> <n_procs>
# Two stages as the 2D model (models/cfd/step_openfoam.py): a start-up with first-order k and omega, then the
# second-order run. The 0/ fields are written by models/cfd/step3d_openfoam.py (from the 2D solution).
# Exit codes: 10 bad case dir, 11 OpenFOAM environment, 20 blockMesh, 21 decomposePar, 22 foamRun,
# 23 writeCellCentres, 24 reconstructPar.
cd "$1" || exit 10
source "$2" || exit 11
NP="${3:-1}"
{
  echo "openfoam_version=$WM_PROJECT_VERSION"
  dpkg-query -W -f='openfoam_package=${Package} ${Version}\n' "openfoam$WM_PROJECT_VERSION" 2>/dev/null
  . /etc/os-release && echo "linux=$PRETTY_NAME"
  echo "mpi=$(mpirun --version 2>/dev/null | head -1)"
  echo "n_procs=$NP"
} > versions.txt
blockMesh > log.blockMesh 2>&1 || exit 20
checkMesh > log.checkMesh 2>&1
if [ "$NP" -gt 1 ]; then
  decomposePar -force > log.decomposePar 2>&1 || exit 21
  RUN=(nice -n 19 mpirun -np "$NP" --bind-to none foamRun -parallel)
else
  RUN=(nice -n 19 foamRun)
fi
"${RUN[@]}" > log.foamRun.stage1 2>&1 || exit 22
mv system/controlDict.stage2 system/controlDict && mv system/fvSchemes.stage2 system/fvSchemes || exit 22
"${RUN[@]}" > log.foamRun 2>&1 || exit 22
if [ "$NP" -gt 1 ]; then
  reconstructPar -latestTime > log.reconstructPar 2>&1 || exit 24
  rm -rf processor*
fi
foamPostProcess -func writeCellCentres -latestTime > log.writeCellCentres 2>&1 || exit 23
exit 0

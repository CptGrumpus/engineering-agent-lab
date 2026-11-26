#!/bin/bash
# Run one Turek-Hron fluid case inside WSL: convert the Gmsh mesh, set the patch types, check the
# mesh, solve steady, write cell centres.
# usage: run_turek_hron.sh <case_dir> <openfoam_etc_bashrc>
# Exit codes: 10 bad case dir, 11 OpenFOAM environment, 19 gmshToFoam, 18 patch types,
#             20 checkMesh, 22 foamRun, 23 writeCellCentres.
cd "$1" || exit 10
source "$2" || exit 11
{
  echo "openfoam_version=$WM_PROJECT_VERSION"
  dpkg-query -W -f='openfoam_package=${Package} ${Version}\n' "openfoam$WM_PROJECT_VERSION" 2>/dev/null
  . /etc/os-release && echo "linux=$PRETTY_NAME"
} > versions.txt
gmshToFoam mesh.msh > log.gmshToFoam 2>&1 || exit 19
for p in "frontAndBack empty" "walls wall" "body wall"; do
  read -r name kind <<< "$p"
  foamDictionary constant/polyMesh/boundary -entry "entry0/$name/type" -set "$kind" > /dev/null 2>&1 || exit 18
done
checkMesh > log.checkMesh 2>&1 || exit 20
foamRun > log.foamRun 2>&1 || exit 22
foamPostProcess -func writeCellCentres -latestTime > log.writeCellCentres 2>&1 || exit 23
exit 0

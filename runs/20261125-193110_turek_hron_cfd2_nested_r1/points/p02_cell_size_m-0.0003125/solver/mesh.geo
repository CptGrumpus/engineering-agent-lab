SetFactory("OpenCASCADE");
Rectangle(1) = {0, 0, 0, 2.5, 0.41};
Disk(2) = {0.2, 0.2, 0, 0.05};
Rectangle(3) = {0.2, 0.19, 0, 0.39999999999999997, 0.02};
BooleanUnion{ Surface{2}; Delete; }{ Surface{3}; Delete; }
BooleanDifference{ Surface{1}; Delete; }{ Surface{2}; Delete; }
eps = 1e-6;
d = 0.01;
body() = Curve In BoundingBox{0.15000000000000002-eps, 0.15000000000000002-eps, -eps, 0.6+eps, 0.25+eps, eps};
Field[1] = Distance; Field[1].CurvesList = {body()}; Field[1].Sampling = 400;
Field[2] = Threshold; Field[2].InField = 1; Field[2].SizeMin = 0.0025; Field[2].SizeMax = 0.015;
Field[2].DistMin = 0.0; Field[2].DistMax = 0.3;
Background Field = 2;
Mesh.MeshSizeExtendFromBoundary = 0; Mesh.MeshSizeFromPoints = 0; Mesh.MeshSizeFromCurvature = 0;
Mesh.Algorithm = 8; Recombine Surface{1};
Physical Curve("inlet") = Curve In BoundingBox{-eps, -eps, -eps, eps, 0.41+eps, eps};
Physical Curve("outlet") = Curve In BoundingBox{2.5-eps, -eps, -eps, 2.5+eps, 0.41+eps, eps};
Physical Curve("walls") = {Curve In BoundingBox{-eps, -eps, -eps, 2.5+eps, eps, eps}, Curve In BoundingBox{-eps, 0.41-eps, -eps, 2.5+eps, 0.41+eps, eps}};
Physical Curve("body") = body();
Physical Surface("fluid") = {1};
Mesh.MshFileVersion = 2.2;
Mesh 2;
RefineMesh;
RefineMesh;
RefineMesh;
Save "mesh2d.msh";

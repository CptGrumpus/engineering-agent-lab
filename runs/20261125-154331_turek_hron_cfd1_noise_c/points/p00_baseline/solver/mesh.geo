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
Field[2] = Threshold; Field[2].InField = 1; Field[2].SizeMin = 0.00127; Field[2].SizeMax = 0.00762;
Field[2].DistMin = 0.0; Field[2].DistMax = 0.3;
Background Field = 2;
Mesh.MeshSizeExtendFromBoundary = 0; Mesh.MeshSizeFromPoints = 0; Mesh.MeshSizeFromCurvature = 0;
Mesh.Algorithm = 8; Recombine Surface{1};
ex[] = Extrude{0, 0, d}{ Surface{1}; Layers{1}; Recombine; };
Physical Surface("inlet") = Surface In BoundingBox{-eps, -eps, -eps, eps, 0.41+eps, d+eps};
Physical Surface("outlet") = Surface In BoundingBox{2.5-eps, -eps, -eps, 2.5+eps, 0.41+eps, d+eps};
Physical Surface("walls") = {Surface In BoundingBox{-eps, -eps, -eps, 2.5+eps, eps, d+eps}, Surface In BoundingBox{-eps, 0.41-eps, -eps, 2.5+eps, 0.41+eps, d+eps}};
Physical Surface("body") = Surface In BoundingBox{0.15000000000000002-eps, 0.15000000000000002-eps, -eps, 0.6+eps, 0.25+eps, d+eps};
Physical Surface("frontAndBack") = {Surface In BoundingBox{-eps, -eps, -eps, 2.5+eps, 0.41+eps, eps}, Surface In BoundingBox{-eps, -eps, d-eps, 2.5+eps, 0.41+eps, d+eps}};
Physical Volume("fluid") = {ex[1]};

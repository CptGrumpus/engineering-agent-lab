Geometry.AutoCoherence = 0;
// block (half): top face y = 0, contact point at the origin
Point(1) = {0, 0, 0}; Point(2) = {60.0, 0, 0}; Point(3) = {60.0, -50.0, 0}; Point(4) = {0, -50.0, 0};
Line(1) = {1, 2}; Line(2) = {2, 3}; Line(3) = {3, 4}; Line(4) = {4, 1};
Curve Loop(1) = {1, 2, 3, 4}; Plane Surface(1) = {1};
// roller (quarter disc), lowest point at the origin, centre at (0, R)
Point(11) = {0, 0, 0}; Point(12) = {0, 50.0, 0}; Point(13) = {50.0, 50.0, 0};
Circle(11) = {11, 12, 13}; Line(12) = {13, 12}; Line(13) = {12, 11};
Curve Loop(2) = {11, 12, 13}; Plane Surface(2) = {2};
Field[1] = Distance; Field[1].PointsList = {1, 11};
Field[2] = Threshold; Field[2].InField = 1;
Field[2].SizeMin = 0.02; Field[2].SizeMax = 4.0;
Field[2].DistMin = 1.6; Field[2].DistMax = 33.6;
Background Field = 2;
Mesh.MeshSizeExtendFromBoundary = 0; Mesh.MeshSizeFromPoints = 0; Mesh.MeshSizeFromCurvature = 0;
Mesh.Algorithm = 8; Mesh.RecombineAll = 1; Mesh.SubdivisionAlgorithm = 1;
Mesh.ElementOrder = 1;
b[] = Extrude {0, 0, 0.5} { Surface{1}; Layers{1}; Recombine; };
r[] = Extrude {0, 0, 0.5} { Surface{2}; Layers{1}; Recombine; };
Physical Volume("BLOCK") = {b[1]};
Physical Volume("ROLLER") = {r[1]};

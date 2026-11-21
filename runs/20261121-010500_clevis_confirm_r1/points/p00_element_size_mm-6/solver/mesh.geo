SetFactory("OpenCASCADE");
Merge "bracket.step";
Mesh.MeshSizeMax = 6.0; Mesh.MeshSizeMin = 1.5;
Mesh.MeshSizeFromCurvature = 8;
Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 0; Mesh.Optimize = 1; Mesh.HighOrderOptimize = 1;
Physical Volume("BRACKET") = Volume{:};

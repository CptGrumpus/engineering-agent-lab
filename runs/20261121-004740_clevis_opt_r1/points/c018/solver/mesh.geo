SetFactory("OpenCASCADE");
Merge "bracket.step";
Mesh.MeshSizeMax = 4.0; Mesh.MeshSizeMin = 1.0;
Mesh.MeshSizeFromCurvature = 12;
Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 0; Mesh.Optimize = 1; Mesh.HighOrderOptimize = 1;
Physical Volume("BRACKET") = Volume{:};

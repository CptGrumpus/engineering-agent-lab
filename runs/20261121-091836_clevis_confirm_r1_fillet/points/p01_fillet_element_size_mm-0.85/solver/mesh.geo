SetFactory("OpenCASCADE");
Merge "bracket.step";
Mesh.MeshSizeMax = 4.0; Mesh.MeshSizeMin = 0.425;
Mesh.MeshSizeFromCurvature = 23;
Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 0; Mesh.Optimize = 1;
Physical Volume("BRACKET") = Volume{:};

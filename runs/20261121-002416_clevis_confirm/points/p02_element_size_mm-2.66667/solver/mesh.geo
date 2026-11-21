SetFactory("OpenCASCADE");
Merge "bracket.step";
Mesh.MeshSizeMax = 2.6666666666666665; Mesh.MeshSizeMin = 0.6666666666666666;
Mesh.MeshSizeFromCurvature = 18;
Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 0; Mesh.Optimize = 1;
Physical Volume("BRACKET") = Volume{:};

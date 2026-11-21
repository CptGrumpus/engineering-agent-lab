SetFactory("OpenCASCADE");
Merge "bracket.step";
Mesh.MeshSizeMax = 2.0; Mesh.MeshSizeMin = 2.0;
Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 0;
Mesh.Optimize = 1;
Physical Volume("BRACKET") = Volume{:};

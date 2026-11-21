SetFactory("OpenCASCADE");
Merge "bracket.step";
Mesh.MeshSizeMax = 4.5; Mesh.MeshSizeMin = 4.5;
Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 0;
Mesh.Optimize = 1;
Physical Volume("BRACKET") = Volume{:};

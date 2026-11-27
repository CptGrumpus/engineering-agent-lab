SetFactory("OpenCASCADE");
Merge "cover.step";
Mesh.MeshSizeMax = 1.5; Mesh.MeshSizeMin = 0.30000000000000004; Mesh.MeshSizeFromCurvature = 12;
Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 0; Mesh.Optimize = 1;
Physical Volume("COVER") = Volume{:};

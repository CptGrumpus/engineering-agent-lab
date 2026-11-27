SetFactory("OpenCASCADE");
Merge "cover.step";
Mesh.MeshSizeMax = 2.0; Mesh.MeshSizeMin = 0.4; Mesh.MeshSizeFromCurvature = 12;
Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 0; Mesh.Optimize = 1;
Physical Volume("COVER") = Volume{:};

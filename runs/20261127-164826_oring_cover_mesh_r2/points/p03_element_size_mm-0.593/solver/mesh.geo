SetFactory("OpenCASCADE");
Merge "cover.step";
Mesh.MeshSizeMax = 0.593; Mesh.MeshSizeMin = 0.1186; Mesh.MeshSizeFromCurvature = 0;
Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 0; Mesh.Optimize = 1;
Physical Volume("COVER") = Volume{:};

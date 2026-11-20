SetFactory("OpenCASCADE");
Merge "arm.step";
Mesh.MeshSizeMax = 5.0; Mesh.MeshSizeMin = 5.0;
Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 0;
Physical Volume("ARM") = Volume{:};

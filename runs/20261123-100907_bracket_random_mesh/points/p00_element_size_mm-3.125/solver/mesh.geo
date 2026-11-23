SetFactory("OpenCASCADE");
Merge "arm.step";
Mesh.MeshSizeMax = 3.125; Mesh.MeshSizeMin = 3.125;
Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 0;
Physical Volume("ARM") = Volume{:};

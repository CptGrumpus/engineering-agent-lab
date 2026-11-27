SetFactory("OpenCASCADE");
Merge "vessel.step";
Field[1] = MathEval;
Field[1].F = "Min(24.0, 13.5 + 0.08*Max(0, Sqrt((x-516.0)^2+y^2+z^2) - 140.0))";
Background Field = 1;
Mesh.MeshSizeExtendFromBoundary = 0; Mesh.MeshSizeFromPoints = 0; Mesh.MeshSizeFromCurvature = 0;
Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 0; Mesh.Optimize = 1;
Physical Volume("VESSEL") = Volume{:};

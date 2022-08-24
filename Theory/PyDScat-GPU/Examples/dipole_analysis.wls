#!/usr/bin/env wolframscript

(* Change the path accordingly *)
AppendTo[$Path, "path_of_this_file"];

<<NanoparticleProperties`

baseDirectory = $ScriptCommandLine[[2]] 
filePath = $ScriptCommandLine[[3]] 

coordData = N@Import[filePath, "CSV"];
coordDataScaled = 0.001*coordData

output = createMeshElementsGrid[coordDataScaled, 3];
Export[baseDirectory <> "/mesh_coordinates.csv", output, "CSV"]
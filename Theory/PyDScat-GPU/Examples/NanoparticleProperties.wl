(* ------------------------------------------------------------------------ *)
(* -------- CALCULATES NANOPARTICLE PROPERTIES FROM COORDINATE DATA ------- *)
(* ------------------------------------------------------------------------ *)

BeginPackage["NanoparticleProperties`"];

calculateProp::usage = "Calculate properties of nanoparticle from a continuum mesh"
createDipoles::usage = "Creates the list of dipoles from the nanoparticle geometry"

<<NDSolve`FEM`
(*baseDirectory = Directory[]*)

(* Physical Constants *)
latticeC = 0.4065;     (* Lattice Constant for Gold in nanometers *)
dLength = 1;          (* Dipole Length for creating Nanoparticle Geometry in nanometers *)

calculateProp[coordData_,coordNumData_, step_, baseDirectory_] := Module[{nnGraph, SurfaceAtoms, RegionMesh, NpMesh, npVolume, npSurfaceArea, shapeComplex},
    (* Calculates properties of nanoparicles by creating continuum mesh *)
    coordDataReal = coordData; (* Converting atomic coordinates into nm *)
    nnGraph = NearestNeighborGraph[coordDataReal];
    coordNumList = Flatten@(IntegerPart/@coordNumData);
    SurfaceAtoms = Pick[coordDataReal, coordNumList, Except[12,_Integer]];
    RegionMesh = DelaunayMesh[SurfaceAtoms];
    NpMesh = ToBoundaryMesh[RegionMesh, "BoundaryMeshGenerator" -> "RegionPlot", "MaxBoundaryCellMeasure" -> 0.1];
    Export[baseDirectory <> "/np_mesh.png", NpMesh["Wireframe"], ImageResolution -> 300];
    npVolume = Volume@RegionMesh*(latticeC^3);
    npSurfaceArea = SurfaceArea@RegionMesh*(latticeC^2);
    shapeComplex = N[npSurfaceArea/(36 \[Pi] npVolume^2)^((1/3))];
    Return[{npVolume, npSurfaceArea, shapeComplex}]]


createDipoles[coordData_, coordNumData_, step_, baseDirectory_] := Module[{xRange, yRange, zRange, nDipolesX, nDipolesY, nDipolesZ, dipoleList, dipoleListF},
    (* Creates coordinates of the dipoles by creating continuum mesh for DDA calculations *)
    coordDataReal = coordData*latticeC; (* Converting atomic coordinates into nm *)
    coordNumList = Flatten@(IntegerPart/@coordNumData);
    SurfaceAtoms = Pick[coordDataReal, coordNumList, Except[12,_Integer]];
    RegionMesh = DelaunayMesh[SurfaceAtoms];
    {xRange, yRange, zRange} = N@RegionBounds[RegionMesh];
    nDipolesX = First@Round[(1/dLength)*Differences@xRange];
    nDipolesY = First@Round[(1/dLength)*Differences@yRange];
    nDipolesZ = First@Round[(1/dLength)*Differences@zRange];
    dipoleList = Flatten[Table[{xRange[[1]] + xD*dLength, 
                                yRange[[1]] + yD*dLength,
                                zRange[[1]] + zD*dLength},
                                {xD, nDipolesX}, {yD, nDipolesY}, {zD, nDipolesZ}],2];
    
    dipoleListF = Pick[#[[1]], #[[2]]]&/@Evaluate[{#, RegionMember[RegionMesh, #]}&/@dipoleList];
    Export[baseDirectory <> "/dipoleList_" <> step <> ".csv", dipoleListF,"CSV"];
    Return[Length@dipoleListF]]


createMeshElements[coordData_, sizeFac_] := Module[{nnGraph, coordNumList, NpMesh, reg, elementMesh},
    (* Creates regular mesh around the nanoparticle to perform electric field calculations *)
    minP = sizeFac*(Min /@ {coordData[[All, 1]], coordData[[All, 2]], coordData[[All, 3]]});
    maxP = sizeFac*(Max /@ {coordData[[All, 1]], coordData[[All, 2]], coordData[[All, 3]]});

    nnGraph = NearestNeighborGraph[coordData];
    coordNumList = Table[Length[VertexList[NeighborhoodGraph[nnGraph, coordData[[i]]]]] - 1, {i, Length@coordData}];
    NpMesh = DelaunayMesh[Pick[coordData, coordNumList, Except[12, _Integer]]];
    reg = RegionDifference[DiscretizeRegion@Cuboid[minP, maxP], NpMesh];
    elementMesh = ToElementMesh[reg, MaxCellMeasure -> 0.05];
    Return[elementMesh["Coordinates"]]]  


createMeshElementsGrid[coordData_, sizeFac_] := Module[{nnGraph, coordNumList, NpMesh, reg, elementMesh, nPoints, gridPoints},
    (* Creates rectangular grid around the nanoparticle to perform electric field calculations *)
    minP = sizeFac*(Min /@ {coordData[[All, 1]], coordData[[All, 2]], coordData[[All, 3]]});
    maxP = sizeFac*(Max /@ {coordData[[All, 1]], coordData[[All, 2]], coordData[[All, 3]]});
    nPoints = (maxP - minP)/30;
    points = Flatten[Table[{i,j,k}, {i, minP[[1]],maxP[[1]], nPoints[[1]]}, 
                                    {j, minP[[2]],maxP[[2]], nPoints[[2]]}, 
                                    {k, minP[[3]],maxP[[3]], nPoints[[3]]}], 2];

    nnGraph = NearestNeighborGraph[coordData];
    coordNumList = Table[Length[VertexList[NeighborhoodGraph[nnGraph, coordData[[i]]]]] - 1, {i, Length@coordData}];
    NpMesh = DelaunayMesh[Pick[coordData, coordNumList, Except[12, _Integer]]];
    gridPoints = Pick[points, RegionMember[NpMesh, #] & /@ points, False];
    Return[gridPoints]]  


plotElectricFieldProfile[dipoleData_, meshData_, efieldData_] := Module[{npRegion, meshDataN, EFieldDataN, intp},
    (* Plots magnitude of the electric field profile around the nanoparticle *)
    npRegion = Region[Style[DelaunayMesh[dipoleData], Yellow]];
    meshDataN = 10^3 Delete[meshData, Partition[Union[Position[efieldData , "nan"][[All, 1]]], 1]];
    EFieldDataN = Delete[EFieldData, Partition[Union[Position[efieldData , "nan"][[All, 1]]], 1]];

    plot = Show[{ListDensityPlot3D[MapThread[Flatten@{#1, #2} &, {meshDataN, Norm /@ EFieldDataN}], 
                                       OpacityFunction -> Function[f, f^2.7], PlotRange -> Full, 
                                       ColorFunctionScaling -> True, ColorFunction -> "BrightBands", 
                                       PlotTheme -> "Marketing", PlotLegends -> Automatic, 
                                       PerformanceGoal -> "Quality", 
                                       LabelStyle -> {Black, Directive[Black, FontColor -> Black, FontSize -> 14]}], npRegion}];
                                       
    Return[plot]]

EndPackage[]

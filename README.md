# FDA Nozzle CFD

Reproducible OpenFOAM CFD simulation of the FDA's public benchmark nozzle
geometry (the "FDA Nozzle" / "FDA Benchmark Medical Device" model), with the
goal of validating simulated flow fields against real experimental
velocimetry data (PIV / LDA velocity measurements) published for this
benchmark.

## Purpose

The FDA nozzle is a well-known round-robin CFD validation case for medical
devices, originally developed to assess whether CFD can reliably predict flow
in blood-contacting devices. This repository sets up an OpenFOAM case for
that geometry so that:

- Simulation results (velocity fields, pressure drop, shear stress) can be
  reproduced from scratch by anyone cloning this repo.
- Simulated velocity profiles at the benchmark's measurement planes can be
  compared directly against the publicly available experimental PIV/velocity
  data for the same geometry and flow conditions.

## Relation to the `hemolysis-calculator` project

This project is a companion/upstream data source for
[`hemolysis-calculator`](https://github.com/sarantisgkritsalis/hemolysis-calculator).
The velocity and shear stress fields produced by the CFD runs in this
repository are intended to be exported and fed into that project's
haemolysis (red blood cell damage) model as input flow data. In other words:

- **This repo (`fda-nozzle-cfd`)**: produces validated flow field data
  (velocity, shear stress) from CFD simulation of the FDA nozzle benchmark.
- **`hemolysis-calculator`**: consumes that flow field data to estimate
  haemolysis / blood damage using the shear stress history along
  streamlines.

Any changes to mesh resolution, turbulence model, or solver settings here
that affect the exported shear stress fields should be considered together
with their downstream impact on `hemolysis-calculator` results.

## Case structure

```
0/               Initial and boundary conditions (U, p, k, epsilon, etc.)
constant/        Mesh (polyMesh/), geometry (triSurface/), transport &
                 turbulence properties
system/          Solver control, discretization schemes, linear solver
                 settings, fvSchemes/fvSolution/controlDict
postprocessing/  Extracted results: velocity profiles at benchmark
                 measurement planes, pressure drop, wall shear stress
plots/           Generated plots comparing CFD results against experimental
                 PIV/velocity data
```

## Status

Skeleton only — mesh, boundary conditions, and solver setup are not yet
populated.

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

## Dependencies

- **OpenFOAM v2312** (or a compatible OpenFOAM.com release) — provides
  `blockMesh`, `snappyHexMesh`, `checkMesh`, `simpleFoam` used to build the
  mesh and run the case.
- **ParaView 6.x with `pvpython`** — only needed to regenerate the images in
  `plots/` via `pvpython scripts/render_cfd_results.py`; not required to
  build the mesh or run the solver.
- **Python 3** (standard library only, no pip packages) — for
  `scripts/generate_nozzle_geometry.py`, which regenerates
  `constant/triSurface/fda_nozzle_wall.stl` from the published dimensions
  (see `constant/triSurface/SOURCES.md`).

There is no `requirements.txt` because nothing here is installed via pip:
`generate_nozzle_geometry.py` has no external dependencies, and
`render_cfd_results.py` runs inside ParaView's own bundled Python
(`pvpython`), not a separate virtualenv.

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

## Current Status & Future Work

Mesh, boundary conditions, and a first solver run are in place:

- **Mesh**: coarse `blockMesh` background + `snappyHexMesh` (castellate +
  snap, no boundary layers yet) around `constant/triSurface/fda_nozzle_wall.stl`.
  8560 cells. `checkMesh` reports `Mesh OK` (max non-orthogonality 41.3°,
  max skewness 0.6).
- **Fluid**: blood-analog Newtonian fluid from Hariharan et al. 2011
  (rho = 1056 kg/m^3, nu = 3.314394e-06 m^2/s), see
  `constant/transportProperties`.
- **Case run**: throat Re = 6500 (fully turbulent case), steady RANS with
  `simpleFoam` + kOmegaSST (`constant/turbulenceProperties`). Inlet/outlet
  velocities derived from Re via mass conservation
  (U_throat = 5.386 m/s, U_inlet = 0.598 m/s); see the comments in `0/U`,
  `0/k`, `0/omega` for the exact derivation.

### Results (t=1000, throat Re=6500)

Rendered with `scripts/render_cfd_results.py` (pvpython); regenerate after
any new run with `pvpython scripts/render_cfd_results.py`.

**Velocity magnitude, axial slice** — acceleration through the throat,
diffusion after the sudden expansion:
![Velocity magnitude axial slice](plots/velocity_magnitude_axial_slice.png)

**Pressure, axial slice** — pressure drop through the contraction, partial
recovery downstream:
![Pressure axial slice](plots/pressure_axial_slice.png)

**Streamlines** — seeded across the inlet diameter, colored by velocity
magnitude, shown over the wall outline:
![Streamlines colored by velocity magnitude](plots/streamlines_velocity.png)

**y+ on `nozzleWall`** — see the known limitation below (no boundary layers
yet, so most of the wall sits below y+ = 30):
![y+ on nozzleWall](plots/yplus_nozzle_wall.png)

### Known limitations of this run (not yet resolved)

- **Residuals did not fully converge.** `U` residuals drop quickly early on
  then plateau around ~0.05 instead of continuing down to the
  `residualControl` targets in `system/fvSolution`, with intermittent
  "bounding k" events. This is consistent with a known feature of the FDA
  nozzle benchmark at this Reynolds number reported in the literature: the
  shear layer downstream of the sudden expansion sheds vortices and is
  inherently unsteady, which a steady-state RANS solver cannot fully settle
  into a single fixed point. It is not necessarily a sign of a mesh or
  boundary-condition error.
- **y+ on `nozzleWall` averages ~11.5** (min 0.78, max 47.7) — because no
  boundary layers have been added yet (`snappyHexMeshDict` has
  `addLayers false`), much of the wall sits in the buffer region rather
  than solidly above y+ = 30, where the wall functions (`kqRWallFunction`,
  `omegaWallFunction`, `nutkWallFunction`) are formally valid.
- **Practical consequence**: wall shear stress from this run should be
  treated as **indicative only, not quantitatively validated** — this
  matters directly for `hemolysis-calculator`, which consumes shear stress
  as its primary input. Do not feed this run's shear stress into the
  haemolysis model as a validated result yet.

### Next steps

1. **Boundary layers**: enable `addLayers true` in `system/snappyHexMeshDict`
   (with tuned `nSurfaceLayers` / `finalLayerThickness`) so `nozzleWall` sits
   consistently above y+ = 30 (or move to a low-Re wall treatment targeting
   y+ ~ 1), so wall shear stress can be trusted quantitatively.
2. **Transient solver**: re-run with `pimpleFoam` to capture the unsteady
   shear-layer / vortex-shedding behaviour downstream of the sudden
   expansion directly, instead of relying on a steady RANS plateau.
3. **`hemolysis-calculator` hand-off**: once (1) and (2) give a
   quantitatively trustworthy shear stress field, add an export step that
   writes velocity + shear stress history along streamlines in the format
   `hemolysis-calculator` expects, and wire it into that project's
   haemolysis model as validated input.
4. **Post-processing script**: add the script (populating `postprocessing/`
   and `plots/`) that extracts velocity profiles at the benchmark's PIV
   measurement planes and plots them against the published experimental
   data, closing the loop described in "Purpose" above.

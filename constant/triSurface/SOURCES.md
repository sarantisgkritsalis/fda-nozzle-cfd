# Geometry provenance

## What we looked for

We looked for a ready-to-use STL/CAD file for the FDA benchmark nozzle in
[`OSEL-DAM/CFD-and-Blood-Damage-Benchmarks`](https://github.com/OSEL-DAM/CFD-and-Blood-Damage-Benchmarks),
folder `Nozzle/`. It does not contain one:

- `Nozzle/Data/*.zip` (`SE_exp_*`, `CD_Re_*`, `bundle.zip`) contain only
  experimental PIV velocity data (`.txt` files per Reynolds number / axial
  station), not geometry.
- `Nozzle/Publications/` contains only papers (PDF).
- The repo's own `Nozzle/README.md` points to the Hariharan et al. 2011
  paper (paywalled on Springer/ASME) and to `https://nciphub.org/wiki/FDA_CFD`
  for CAD files. **`nciphub.org` no longer resolves** (checked 2026-07-27;
  DNS lookup fails, no evidence of a migrated replacement found via web
  search). This was historically the official host for the STL/STEP
  geometry used in the FDA round-robin study, but it is no longer
  reachable.

## What we used instead

`Hariharan_PIV_Analysis_of_Nozzle_2011.pdf` is itself freely hosted in the
same GitHub repo
(`Nozzle/Publications/Hariharan_PIV_Analysis_of_Nozzle_2011.pdf`). Its
Figure 1 is a fully dimensioned schematic of the nozzle wall:

> Hariharan P, Giarra M, Reddy V, Day SW, Manning KB, Deutsch S,
> Stewart SFC, Myers MR, Berman MR, Burgreen GW, Paterson EG,
> Malinauskas RA. "Multilaboratory Particle Image Velocimetry Analysis of
> the FDA Benchmark Nozzle Model to Support Validation of Computational
> Fluid Dynamics Simulations." *J Biomech Eng.* 2011;133(4):041002.
> doi:[10.1115/1.4003440](https://doi.org/10.1115/1.4003440)

Dimensions read from Fig. 1 (official):

| Feature                        | Value    |
|---------------------------------|----------|
| Inlet / outlet pipe diameter D  | 12 mm    |
| Throat diameter d               | 4 mm     |
| Contraction full cone angle     | 20°      |
| Contraction axial length        | 22.685 mm|
| Throat axial length             | 40 mm    |
| Expansion geometry               | sharp step (no fillet) |

`fda_nozzle_wall.stl` was generated from these numbers by
[`scripts/generate_nozzle_geometry.py`](../../scripts/generate_nozzle_geometry.py)
(pure-Python axisymmetric revolve, no external dependencies). Regenerate it
with:

```
python3 scripts/generate_nozzle_geometry.py
```

## What is NOT official

Fig. 1 only dimensions the contraction/throat/expansion piece itself — it
does not specify the length of the straight inlet/outlet pipe sections. The
script adds two stub lengths purely so the geometry has usable inlet/outlet
faces for meshing:

- Inlet stub: 20 mm (arbitrary buffer, not from the paper)
- Outlet stub: 80 mm (~20 step-heights; chosen because the paper reports
  the recirculation zone reattaches ~15–20H downstream of the sudden
  expansion, where step height H = 4 mm)

Change `L_INLET_STUB` / `L_OUTLET_STUB` at the top of the script if a
different domain length is needed.

## If an authoritative CAD file turns up later

If `nciphub.org` comes back, gets migrated, or an original STEP/STL file is
obtained by other means (e.g. institutional Springer access to the
supplementary material, or contacting the study authors), it should
replace this generated file and this document should be updated
accordingly — the generated wall matches the published dimensions but is
not a substitute for the original CAD if bit-for-bit provenance ever
matters.

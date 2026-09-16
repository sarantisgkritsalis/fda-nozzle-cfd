"""Export nozzleWall shear stress + a point-estimate exposure time for
hand-off to hemolysis-calculator (pvpython).

Reads the wallShearStress and yPlus fields on the nozzleWall patch (both
must already exist in the requested time directories -- generate them
first with e.g. `simpleFoam -postProcess -func wallShearStress -time 1000`
and `... -func yPlus -time 1000` if missing) and writes two CSVs to
postprocessing/:

- wall_shear_stress_full.csv: every nozzleWall face, at both the steady
  (1000) and transient-latest (1000.15) times, with position, dynamic
  shear stress (Pa), y+, and a per-face confidence flag.
- hemolysis_calculator_input.csv: a small point-estimate summary in the
  (shear_stress_pa, exposure_time_s) scalar format hemolysis-calculator's
  single-exposure power-law model actually consumes (it does not ingest
  full fields or streamlines -- see its README).

Run from the case root with:

    pvpython scripts/export_wall_shear_stress.py

Caveats (see README "Known limitations" and the Step 5 write-up):
- wallShearStress from an incompressible solver is kinematic (m^2/s^2);
  this script converts to dynamic shear stress (Pa) by multiplying by
  rho = 1056 kg/m^3 (constant/transportProperties).
- ~15% of nozzleWall faces, concentrated at the throat, still have
  y+ > 5 (the resolved-sublayer threshold used elsewhere in this repo --
  see "Why y+ ~ 1 instead of y+ ~ 30"). Those faces are exported with
  confidence = low_confidence_throat_tail rather than being dropped,
  since the throat is also the highest-shear, most hemolysis-relevant
  region; treat them with caution downstream.
- exposure_time_s is NOT a Lagrangian residence time (no streamline
  integration is done in this repo yet) -- it is the throat transit time
  (L_throat / U_throat), a standard order-of-magnitude single-exposure
  estimate for the peak-shear region, matching the granularity
  hemolysis-calculator's point-estimate mode actually uses.
"""

import csv
import os

from paraview import servermanager
from paraview.simple import *  # noqa: F401,F403

CASE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOAM_FILE = os.path.join(CASE_ROOT, "case.foam")
OUT_DIR = os.path.join(CASE_ROOT, "postprocessing")

# constant/transportProperties: blood-analog fluid, Hariharan et al. 2011.
RHO = 1056.0  # kg/m^3

# scripts/generate_nozzle_geometry.py (L_THROAT) and README (U_throat,
# derived from throat Re=6500 via mass conservation).
L_THROAT = 0.040  # m
U_THROAT = 5.386  # m/s
EXPOSURE_TIME_S = L_THROAT / U_THROAT

# nutkWallFunction switches formula at yPlusLam ~ 11; README treats y+ <= 5
# as solidly resolved-sublayer. See "Why y+ ~ 1 instead of y+ ~ 30".
YPLUS_TRUST_THRESHOLD = 5.0

TIMES = [
    ("steady_1000", 1000),
    ("transient_1000.15", 1000.15),
]

if not os.path.exists(FOAM_FILE):
    open(FOAM_FILE, "w").close()
os.makedirs(OUT_DIR, exist_ok=True)

paraview.simple._DisableFirstRenderCameraReset()

full_rows = []

for label, t in TIMES:
    reader = OpenFOAMReader(FileName=FOAM_FILE)
    reader.MeshRegions = ["patch/nozzleWall"]
    reader.CellArrays = ["wallShearStress", "yPlus"]
    reader.Createcelltopointfiltereddata = 0
    reader.UpdatePipeline(time=t)
    merged = MergeBlocks(Input=reader)
    merged.UpdatePipeline(time=t)

    block = servermanager.Fetch(merged)
    if hasattr(block, "GetBlock"):
        block = block.GetBlock(0)

    cell_data = block.GetCellData()
    tau_arr = cell_data.GetArray("wallShearStress")
    yplus_arr = cell_data.GetArray("yPlus")
    if tau_arr is None or yplus_arr is None:
        raise RuntimeError(
            "wallShearStress/yPlus not found on nozzleWall at time %s -- "
            "generate them first, e.g.:\n"
            "  simpleFoam -postProcess -func wallShearStress -time %s\n"
            "  simpleFoam -postProcess -func yPlus -time %s" % (t, t, t)
        )

    n = block.GetNumberOfCells()
    for i in range(n):
        bounds = block.GetCell(i).GetBounds()
        cx = (bounds[0] + bounds[1]) / 2.0
        cy = (bounds[2] + bounds[3]) / 2.0
        cz = (bounds[4] + bounds[5]) / 2.0

        txk, tyk, tzk = tau_arr.GetTuple3(i)
        yplus = yplus_arr.GetTuple1(i)

        tx, ty, tz = txk * RHO, tyk * RHO, tzk * RHO  # Pa
        mag = (tx * tx + ty * ty + tz * tz) ** 0.5
        confidence = (
            "validated" if yplus <= YPLUS_TRUST_THRESHOLD else "low_confidence_throat_tail"
        )

        full_rows.append(
            [label, t, cx, cy, cz, tx, ty, tz, mag, yplus, confidence]
        )

full_path = os.path.join(OUT_DIR, "wall_shear_stress_full.csv")
with open(full_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(
        [
            "run",
            "time",
            "x_m",
            "y_m",
            "z_m",
            "tau_x_pa",
            "tau_y_pa",
            "tau_z_pa",
            "tau_magnitude_pa",
            "y_plus",
            "confidence",
        ]
    )
    writer.writerows(full_rows)

# ---------------------------------------------------------------- summary
# hemolysis-calculator's single-exposure power-law model takes one scalar
# shear_stress_pa + one scalar exposure_time_s per sample (see its
# data/reference_data.csv schema: sample_id, shear_stress_pa,
# exposure_time_s, hi_measured_percent) -- it does not consume full fields
# or streamlines. Report both a validated (y+ <= 5) and a throat/peak
# point estimate rather than picking one, since the peak is also the
# least-certain value.
transient_rows = [r for r in full_rows if r[0] == "transient_1000.15"]
validated_rows = [r for r in transient_rows if r[10] == "validated"]

validated_peak = max(validated_rows, key=lambda r: r[8])
overall_peak = max(transient_rows, key=lambda r: r[8])

summary_path = os.path.join(OUT_DIR, "hemolysis_calculator_input.csv")
with open(summary_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(
        ["sample_id", "shear_stress_pa", "exposure_time_s", "hi_measured_percent", "confidence", "source"]
    )
    writer.writerow(
        [
            "fda_nozzle_cfd_validated_peak",
            round(validated_peak[8], 4),
            round(EXPOSURE_TIME_S, 6),
            "",
            "validated",
            "fda-nozzle-cfd transient_1000.15, y_plus=%.3f" % validated_peak[9],
        ]
    )
    writer.writerow(
        [
            "fda_nozzle_cfd_overall_peak",
            round(overall_peak[8], 4),
            round(EXPOSURE_TIME_S, 6),
            "",
            overall_peak[10],
            "fda-nozzle-cfd transient_1000.15, y_plus=%.3f" % overall_peak[9],
        ]
    )

print("Wrote", full_path)
print("Wrote", summary_path)

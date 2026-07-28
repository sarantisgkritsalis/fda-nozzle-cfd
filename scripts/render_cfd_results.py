"""Render PNG snapshots of the FDA nozzle simpleFoam results (pvpython).

Reads the latest time directory of the OpenFOAM case in this repo and
writes velocity/pressure/yPlus/streamline images to plots/. Run from the
case root with:

    pvpython scripts/render_cfd_results.py
"""

import os

from paraview.simple import *  # noqa: F401,F403

CASE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOAM_FILE = os.path.join(CASE_ROOT, "case.foam")
OUT_DIR = os.path.join(CASE_ROOT, "plots")
LATEST_TIME = 1000

# Nozzle axis is +Z (see blockMeshDict / 0/U). Side-on view: camera looking
# along -Y, with -X as "up" so +Z (flow direction) maps to the horizontal
# screen axis -- inlet on the left, outlet on the right -- matching the
# 1600x500 landscape canvas instead of wasting width on an end-on view.
Z_MID = 0.081
CAM_POS = [0.0, -0.35, Z_MID]
CAM_FOCAL = [0.0, 0.0, Z_MID]
CAM_UP = [-1.0, 0.0, 0.0]

paraview.simple._DisableFirstRenderCameraReset()

if not os.path.exists(FOAM_FILE):
    open(FOAM_FILE, "w").close()

os.makedirs(OUT_DIR, exist_ok=True)


def side_view(view):
    cam = view.GetActiveCamera()
    cam.SetPosition(*CAM_POS)
    cam.SetFocalPoint(*CAM_FOCAL)
    cam.SetViewUp(*CAM_UP)
    ResetCamera(view)
    cam.Zoom(1.5)


def save(view, name):
    Render(view)
    SaveScreenshot(os.path.join(OUT_DIR, name), view, ImageResolution=view.ViewSize)


def style_bar(bar, title):
    bar.Title = title
    bar.ComponentTitle = ""
    bar.WindowLocation = "Lower Right Corner"
    bar.TitleColor = [0, 0, 0]
    bar.LabelColor = [0, 0, 0]


view = GetActiveViewOrCreate("RenderView")
view.ViewSize = [1600, 500]
view.OrientationAxesVisibility = 0
view.UseColorPaletteForBackground = 0
view.Background = [1, 1, 1]

reader = OpenFOAMReader(FileName=FOAM_FILE)
reader.MeshRegions = ["internalMesh"]
reader.CellArrays = ["U", "p", "k", "omega", "nut", "yPlus"]
reader.Createcelltopointfiltereddata = 1
reader.UpdatePipeline(time=LATEST_TIME)
merged = MergeBlocks(Input=reader)

wall_reader = OpenFOAMReader(FileName=FOAM_FILE)
wall_reader.MeshRegions = ["patch/nozzleWall"]
wall_reader.CellArrays = ["U", "p", "k", "omega", "nut", "yPlus"]
wall_reader.Createcelltopointfiltereddata = 1
wall_reader.UpdatePipeline(time=LATEST_TIME)
wall_merged = MergeBlocks(Input=wall_reader)

# yPlus only exists in the 1000/ time directory (not written at t=0), so the
# scene's own time must be pinned to it -- otherwise Render() re-evaluates
# the pipeline at t=0 and yPlus coloring silently gets an empty data range.
scene = GetAnimationScene()
scene.UpdateAnimationUsingDataTimeSteps()
scene.AnimationTime = LATEST_TIME

# ---------------------------------------------------------------- U slice
slice_y = Slice(Input=merged)
slice_y.SliceType = "Plane"
slice_y.SliceType.Origin = [0, 0, Z_MID]
slice_y.SliceType.Normal = [0, 1, 0]

disp_slice = Show(slice_y, view)
disp_slice.Representation = "Surface"
ColorBy(disp_slice, ("POINTS", "U", "Magnitude"))
disp_slice.SetScalarBarVisibility(view, True)
uLUT = GetColorTransferFunction("U")
uLUT.ApplyPreset("Cool to Warm", True)
uLUT.RescaleTransferFunction(0.0, 6.0)
bar_u = GetScalarBar(uLUT, view)
style_bar(bar_u, "U magnitude [m/s]")

side_view(view)
save(view, "velocity_magnitude_axial_slice.png")

disp_slice.SetScalarBarVisibility(view, False)

# ---------------------------------------------------------------- p slice
ColorBy(disp_slice, ("POINTS", "p"))
disp_slice.SetScalarBarVisibility(view, True)
disp_slice.RescaleTransferFunctionToDataRange(False, True)
pLUT = GetColorTransferFunction("p")
pLUT.ApplyPreset("Cool to Warm", True)
bar_p = GetScalarBar(pLUT, view)
style_bar(bar_p, "kinematic p [m^2/s^2]")

save(view, "pressure_axial_slice.png")

disp_slice.SetScalarBarVisibility(view, False)
Hide(slice_y, view)

# ---------------------------------------------------------------- streamlines
# Seed across a diameter near the inlet so streamlines at different radii
# (core flow vs. near-wall / recirculation past the sudden expansion) are
# all visible from the side. Wall patch shown as a translucent wireframe
# for context (not the full internal volume mesh, which is too cluttered).
stream = StreamTracer(Input=merged, SeedType="Line")
stream.Vectors = ["POINTS", "U"]
stream.MaximumStreamlineLength = 0.163
stream.IntegrationDirection = "FORWARD"
stream.SeedType.Point1 = [-0.0059, 0.0, 0.0005]
stream.SeedType.Point2 = [0.0059, 0.0, 0.0005]
stream.SeedType.Resolution = 20

tube = Tube(Input=stream)
tube.Radius = 0.00008

disp_wall_ctx = Show(wall_merged, view)
disp_wall_ctx.Representation = "Surface"
disp_wall_ctx.AmbientColor = [0.6, 0.6, 0.6]
disp_wall_ctx.DiffuseColor = [0.6, 0.6, 0.6]
disp_wall_ctx.Opacity = 0.15

disp_stream = Show(tube, view)
ColorBy(disp_stream, ("POINTS", "U", "Magnitude"))
disp_stream.SetScalarBarVisibility(view, True)
uLUT.RescaleTransferFunction(0.0, 6.0)
bar_u2 = GetScalarBar(uLUT, view)
style_bar(bar_u2, "U magnitude [m/s]")

side_view(view)
save(view, "streamlines_velocity.png")

disp_stream.SetScalarBarVisibility(view, False)
Hide(tube, view)
Hide(wall_merged, view)

# ---------------------------------------------------------------- yPlus on wall
# Show() returns the *same* representation used for the wall context in the
# streamlines step above, so its leftover Opacity=0.15 / gray tint must be
# reset -- otherwise the surface renders as a faint gray blob regardless of
# the color map applied.
disp_w = Show(wall_merged, view)
disp_w.Representation = "Surface"
disp_w.Opacity = 1.0
disp_w.AmbientColor = [1, 1, 1]
disp_w.DiffuseColor = [1, 1, 1]
ColorBy(disp_w, ("POINTS", "yPlus"))
disp_w.SetScalarBarVisibility(view, True)
disp_w.RescaleTransferFunctionToDataRange(False, True)
yLUT = GetColorTransferFunction("yPlus")
yLUT.ApplyPreset("Cool to Warm", True)
bar_y = GetScalarBar(yLUT, view)
style_bar(bar_y, "y+")

side_view(view)
save(view, "yplus_nozzle_wall.png")

print("Wrote images to", OUT_DIR)

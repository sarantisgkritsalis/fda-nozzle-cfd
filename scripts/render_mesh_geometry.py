"""Render PNG snapshots of the nozzle geometry and volume mesh (pvpython).

Unlike render_cfd_results.py, this script does not need a solved case: it
reads the nozzleWall patch and volume mesh from constant/polyMesh at t=0
(0/ boundary conditions are uniform, so they're valid against any mesh).
That makes it safe to (re)run right after blockMesh/snappyHexMesh, before
simpleFoam has produced a solution -- useful for documenting mesh changes
(e.g. boundary layers) independently of a solver run. Run from the case
root with:

    pvpython scripts/render_mesh_geometry.py

Note: geometry is read via the nozzleWall patch (OpenFOAMReader), not
STLReader directly on the .stl -- a bare STLReader pipeline combined with
OrientationAxesVisibility = 0 renders a blank frame in this ParaView build
(6.0.1); the OpenFOAMReader patch pipeline does not have that problem.
"""

import os

from paraview.simple import *  # noqa: F401,F403

CASE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOAM_FILE = os.path.join(CASE_ROOT, "case.foam")
OUT_DIR = os.path.join(CASE_ROOT, "plots")

# Throat spans z = 0.042685 to 0.082685 (see generate_nozzle_geometry.py);
# pad a bit on each side to show the contraction and the start of the
# sudden expansion around it.
THROAT_Z_MIN = 0.035
THROAT_Z_MAX = 0.090
Z_MID = 0.081

paraview.simple._DisableFirstRenderCameraReset()

os.makedirs(OUT_DIR, exist_ok=True)
if not os.path.exists(FOAM_FILE):
    open(FOAM_FILE, "w").close()


def save(view, name):
    Render(view)
    SaveScreenshot(os.path.join(OUT_DIR, name), view, ImageResolution=view.ViewSize)


view = GetActiveViewOrCreate("RenderView")
view.OrientationAxesVisibility = 0
view.UseColorPaletteForBackground = 0
view.Background = [1, 1, 1]

# --------------------------------------------------------- geometry (wall)
view.ViewSize = [1200, 900]

wall_reader = OpenFOAMReader(FileName=FOAM_FILE)
wall_reader.MeshRegions = ["patch/nozzleWall"]
wall_reader.CellArrays = []
wall_reader.UpdatePipeline(time=0)
wall_merged = MergeBlocks(Input=wall_reader)

disp_wall = Show(wall_merged, view)
disp_wall.Representation = "Surface"
disp_wall.AmbientColor = [0.75, 0.78, 0.85]
disp_wall.DiffuseColor = [0.75, 0.78, 0.85]

cam = view.GetActiveCamera()
cam.SetPosition(0.06, -0.09, 0.24)
cam.SetFocalPoint(0.0, 0.0, Z_MID)
cam.SetViewUp(0.0, 1.0, 0.0)
ResetCamera(view)
cam.Zoom(1.3)

save(view, "geometry_nozzle_wall.png")
Hide(wall_merged, view)

# ---------------------------------------------------------------- mesh (t=0)
view.ViewSize = [1600, 500]

reader = OpenFOAMReader(FileName=FOAM_FILE)
reader.MeshRegions = ["internalMesh"]
reader.CellArrays = []
reader.UpdatePipeline(time=0)
merged = MergeBlocks(Input=reader)

# Crinkle clip (keeps whole cells) rather than Slice: the boundary-layer
# cells at nozzleWall are polyhedra, and cutting through them directly with
# Slice hits "non-manifold triangulation" cells that get silently dropped
# from the cut -- which would make the layers invisible in exactly the
# picture meant to show them off.
slice_y = Clip(Input=merged)
slice_y.ClipType = "Plane"
slice_y.ClipType.Origin = [0, 0, Z_MID]
slice_y.ClipType.Normal = [0, 1, 0]
slice_y.Crinkleclip = 1
# Keep the +Y half and view from -Y (an empty, removed region) so the
# camera looks straight at the newly exposed cut face instead of the
# tube's outer wall.
slice_y.Invert = 0

disp_slice = Show(slice_y, view)
disp_slice.Representation = "Surface With Edges"
disp_slice.AmbientColor = [0.85, 0.9, 0.95]
disp_slice.DiffuseColor = [0.85, 0.9, 0.95]
disp_slice.EdgeColor = [0.2, 0.2, 0.2]

side_cam = view.GetActiveCamera()
side_cam.SetPosition(0.0, -0.35, Z_MID)
side_cam.SetFocalPoint(0.0, 0.0, Z_MID)
side_cam.SetViewUp(-1.0, 0.0, 0.0)
ResetCamera(view)
side_cam.Zoom(1.5)

save(view, "mesh_overview.png")

# Throat close-up: same slice, camera framed on the throat + boundary layers.
view.ResetCamera(-0.006, 0.006, -0.006, 0.006, THROAT_Z_MIN, THROAT_Z_MAX)
side_cam.Zoom(1.4)
save(view, "mesh_throat_boundary_layers.png")

print("Wrote images to", OUT_DIR)

#!/usr/bin/env python3
"""
Generate an axisymmetric surface STL of the FDA benchmark nozzle wall.

No official STL/STEP/CAD file for this benchmark is downloadable anymore
(the original host, nciphub.org/wiki/FDA_CFD, no longer resolves). This
script instead reconstructs the wall geometry parametrically from the
dimensions given in Fig. 1 of the primary reference:

    Hariharan P, Giarra M, Reddy V, Day SW, Manning KB, Deutsch S,
    Stewart SFC, Myers MR, Berman MR, Burgreen GW, Paterson EG,
    Malinauskas RA. "Multilaboratory Particle Image Velocimetry Analysis
    of the FDA Benchmark Nozzle Model to Support Validation of
    Computational Fluid Dynamics Simulations." J Biomech Eng.
    2011;133(4):041002. doi:10.1115/1.4003440

    (freely mirrored at
     github.com/OSEL-DAM/CFD-and-Blood-Damage-Benchmarks/blob/main/Nozzle/Publications/Hariharan_PIV_Analysis_of_Nozzle_2011.pdf)

Dimensions taken directly from Fig. 1 of that paper (official, not guessed):
    inlet/outlet pipe diameter   D       = 12 mm
    throat diameter              d       = 4 mm
    contraction half-angle                 10 deg (20 deg full cone angle)
    contraction axial length     L_con   = 22.685 mm
    throat axial length          L_throat= 40 mm
    expansion from throat back to D is a SHARP step (no fillet, no
    gradual diffuser) -- this is the "sudden expansion" configuration.

Straight inlet/outlet stub lengths are NOT given in Fig. 1 (it only
dimensions the contraction/throat/expansion piece itself) and are added
here purely so the geometry has usable inlet/outlet faces for meshing.
They are NOT part of the official benchmark dimensions -- see the
STUB lengths below and constant/triSurface/SOURCES.md for the
rationale and how to change them.
"""

import math

# ---------------------------------------------------------------------------
# Official dimensions (Fig. 1, Hariharan et al. 2011) -- do not change
# without updating the citation above.
# ---------------------------------------------------------------------------
R_PIPE = 0.012 / 2      # inlet/outlet pipe radius [m]  (D = 12 mm)
R_THROAT = 0.004 / 2    # throat radius [m]             (d = 4 mm)
L_CONTRACTION = 0.022685  # contraction axial length [m]
L_THROAT = 0.040          # throat axial length [m]

# ---------------------------------------------------------------------------
# Arbitrary stub lengths (NOT from the paper) -- purely to give the mesh
# usable inlet/outlet end faces. Outlet stub is chosen long enough to
# contain the recirculation reattachment zone, which the paper reports
# occurs ~15-20 step-heights (H = R_PIPE - R_THROAT = 4 mm) downstream
# of the sudden expansion, i.e. ~60-80 mm.
# ---------------------------------------------------------------------------
L_INLET_STUB = 0.020   # 20 mm
L_OUTLET_STUB = 0.080  # 80 mm (~20H, covers reported reattachment length)

N_THETA = 90  # circumferential resolution (4 deg per facet)

OUT_PATH = "constant/triSurface/fda_nozzle_wall.stl"


def build_profile():
    """Axial profile of the wall as a list of (z, r) points, in flow order."""
    z0 = 0.0
    z1 = z0 + L_INLET_STUB
    z2 = z1 + L_CONTRACTION
    z3 = z2 + L_THROAT
    z4 = z3  # sudden expansion: zero-length step, radius jumps
    z5 = z4 + L_OUTLET_STUB
    return [
        (z0, R_PIPE),
        (z1, R_PIPE),
        (z2, R_THROAT),
        (z3, R_THROAT),
        (z4, R_PIPE),
        (z5, R_PIPE),
    ]


def outward_normal(dz, dr, theta):
    """Outward-facing normal (away from the axis / out of the fluid) for a
    surface-of-revolution segment with meridian tangent (dz, dr)."""
    norm = math.hypot(dz, dr)
    if norm == 0:
        dzn, drn = 0.0, 1.0
    else:
        dzn, drn = dz / norm, dr / norm
    return (dzn * math.cos(theta), dzn * math.sin(theta), -drn)


def tri_normal(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    return (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def revolve_segment(z0, r0, z1, r1, n_theta):
    """Yield (v0, v1, v2) triangles revolving the (z0,r0)-(z1,r1) segment
    360 degrees, with outward-pointing winding."""
    dz, dr = z1 - z0, r1 - r0
    dtheta = 2 * math.pi / n_theta
    for i in range(n_theta):
        th0 = i * dtheta
        th1 = (i + 1) * dtheta
        a = (r0 * math.cos(th0), r0 * math.sin(th0), z0)
        b = (r0 * math.cos(th1), r0 * math.sin(th1), z0)
        c = (r1 * math.cos(th0), r1 * math.sin(th0), z1)
        d = (r1 * math.cos(th1), r1 * math.sin(th1), z1)

        theta_mid = th0 + dtheta / 2
        ref = outward_normal(dz, dr, theta_mid)

        for tri in [(a, b, c), (b, d, c)]:
            n = tri_normal(*tri)
            if dot(n, ref) < 0:
                tri = (tri[0], tri[2], tri[1])
            yield tri


def write_stl_ascii(path, triangles, name="fda_nozzle_wall"):
    with open(path, "w") as f:
        f.write(f"solid {name}\n")
        for a, b, c in triangles:
            nx, ny, nz = tri_normal(a, b, c)
            n = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            f.write(f"  facet normal {nx/n:.6e} {ny/n:.6e} {nz/n:.6e}\n")
            f.write("    outer loop\n")
            for v in (a, b, c):
                f.write(f"      vertex {v[0]:.6e} {v[1]:.6e} {v[2]:.6e}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        f.write(f"endsolid {name}\n")


def main():
    profile = build_profile()
    triangles = []
    for (z0, r0), (z1, r1) in zip(profile[:-1], profile[1:]):
        triangles.extend(revolve_segment(z0, r0, z1, r1, N_THETA))
    write_stl_ascii(OUT_PATH, triangles)
    print(f"Wrote {len(triangles)} triangles to {OUT_PATH}")


if __name__ == "__main__":
    main()

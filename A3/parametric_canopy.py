"""
Assignment 3: Parametric Structural Canopy — Pseudocode Scaffold

Author: Your Name

    This file is a **high-level pseudocode**.
    It outlines the pipeline and function responsibilities. 
    Use it as a guide and fill in the bodies with your own logic.
"""

#r: numpy
import numpy as np
import rhinoscriptsyntax as rs
import random

# -------------------------------
# Helpers
# -------------------------------

def seed_everything(seed):
    """Set seeds for reproducibility.
    Parameters
    ----------
    seed : int | None
        Random seed for reproducibility.
    """
    if seed is None:
        return
    try:
        random.seed(seed)
        np.random.seed(seed)
    except Exception as e:
        raise RuntimeError(f"Failed to set random seeds: {e}")



def uv_grid(divU, divV):
    """Create uniform UV samples in [0,1]x[0,1].
    Hints: Use `numpy.linspace` and `numpy.meshgrid`.
    Returns
    -------
    U, V : 2D arrays
        Same shape grids for sampling surfaces/heightmaps.
    """
    # TODO: Create arrays U and V using np.linspace and np.meshgrid
    # TODO: Ensure U and V are 2D grids with shape (divU, divV)
    raise NotImplementedError("Implement using np.linspace and np.meshgrid")


def bbox_corners(geo):
    """Return four reasonable anchor points for supports.
    Hints: `rs.BoundingBox(geo)` returns 8 corners. Pick a subset (e.g.,
    [0,1,3,4]) or choose custom anchors.
    """
    # TODO: Get bounding box corners using rs.BoundingBox(geo)
    # TODO: Select four meaningful corners from the 8 returned points
    raise NotImplementedError("Implement using rs.BoundingBox or custom logic")


# -------------------------------
# 1) Heightmap (placeholder)
# -------------------------------

def heightmap(U, V, amplitude=1.0, frequency=1.0, phase=0.0):
    """Compute a scalar field H over U,V.
    Hints: Combine sin/cos, ridges, fBm noise, radial attractors, etc.
    Avoid loops by vectorizing where possible (NumPy arrays).
    Returns: H with same shape as U,V.
    """
    # TODO: Build a heightmap using vectorized NumPy operations
    # TODO: Consider combining sin, cos, noise, or attractor-based functions
    raise NotImplementedError("Design your own heightmap function")


# -------------------------------
# 2) Source point grid (planar OR sampled from surface)
# -------------------------------

def make_point_grid_xy(divU, divV, origin=(0.0, 0.0, 0.0), size=(10.0, 10.0)):
    """Create a simple planar XY grid of points as a fallback when no surface exists.
    Hints: Build with UV samples → map to XY using origin/size. Return a
    rectangular list-of-lists of points.
    """
    # TODO: Build a 2D grid of points using UV samples
    # TODO: Map UV to XY coordinates based on origin and size
    raise NotImplementedError("Map UV samples to XY coordinates and return a grid")


def sample_point_grid_from_surface(base_surface, U, V):
    """Sample raw points from an existing NURBS surface without offsets.
    Hints: Use `rs.SurfaceDomain(base_surface, dir)` to get real-valued domains
    and map unit U,V to those intervals. Evaluate with `rs.EvaluateSurface`.
    Returns: list[list[point]] with same dimensions as U,V.
    """
    # TODO: Get surface domains with rs.SurfaceDomain
    # TODO: Convert unit UV grids to real parameter values
    # TODO: Use rs.EvaluateSurface to build the point grid
    raise NotImplementedError("Sample using rs.SurfaceDomain + rs.EvaluateSurface")


# -------------------------------
# 3) Deform point grid (Z or surface normals)
# -------------------------------

def manipulate_points_z(point_grid, H):
    """Return a deformed copy of a planar point_grid by offsetting along +Z.
    Hints: For each point p=(x,y,z), produce (x, y, z + H[i,j]). Keep shapes consistent.
    """
    # TODO: Iterate over point grid and apply height H along +Z direction
    # TODO: Maintain grid structure and point order
    raise NotImplementedError("Offset planar grid along +Z using H")


def manipulate_points_along_normals(point_grid, H, base_surface, U, V):
    """Deform points by offsetting along surface normals.
    Hints:
      - Map unit U,V to real surface params via `rs.SurfaceDomain`.
      - Query normals with `rs.SurfaceNormal(base_surface, (u,v))`.
      - Displace each point: p + H[i,j] * n.
    Edge cases: if normal is None or near-zero, fall back or skip.
    """
    # TODO: Get surface normals at each UV and displace points along them
    # TODO: Handle cases where normals may be None or zero-length
    raise NotImplementedError("Offset sampled points along surface normals")


# -------------------------------
# 4) Construct canopy surface from points
# -------------------------------

def surface_from_point_grid(point_grid):
    """Build a NURBS surface from a rectangular grid of points.
    Hints: Flatten the grid and use `rs.AddSrfPtGrid((rows, cols), flat_points)`.
    Returns: surface id (Brep) or None.
    """
    # TODO: Flatten grid and pass to rs.AddSrfPtGrid to construct surface
    # TODO: Return surface ID
    raise NotImplementedError("Use rs.AddSrfPtGrid to build a surface")


# -------------------------------
# 5) Uniform sampling + tessellation
# -------------------------------

def sample_surface_uniform(surface_id, divU, divV):
    """Sample points on a surface using uniform UV in [0,1].
    Hints: `rs.SurfaceDomain` to map unit UV → real UV, then `rs.EvaluateSurface`.
    Returns: list[list[point]].
    """
    # TODO: Map uniform UV samples to real surface parameters
    # TODO: Use rs.EvaluateSurface to create point grid
    raise NotImplementedError("Sample the surface uniformly into a point grid")


def tessellate_panels_from_grid(point_grid):
    """Create panels from each cell in a point grid.
    Options:
      - Two triangular NURBS patches per quad via `rs.AddSrfPt([a,b,d])`, etc.
      - Or construct a Mesh (acceptable if the brief allows meshes).
    Return a list of panel ids, consistent in type.
    """
    # TODO: For each cell in the grid, create two triangular or one quad panel
    # TODO: Use rs.AddSrfPt or mesh construction based on desired output
    raise NotImplementedError("Convert grid cells into panels (tri or quad)")


# -------------------------------
# 6) Branching supports (placeholder)
# -------------------------------

def generate_supports(roots, depth=2, length=5.0, length_reduction=0.7, n_children=2, seed=None):
    """Generate a simple recursive branching structure from anchor points.
    Hints:
      - Seed randomness (`random` / `numpy.random`).
      - Build segments with `rs.AddLine(start, end)`.
      - Optionally add jitter per generation and terminate at `depth`.
      - (Optional) attract to canopy by projecting or intersecting with surface/mesh.
    Return a list of curve ids.
    """
    # TODO: Use recursive logic to generate branching curves from root points
    # TODO: Add randomness and length reduction per generation
    raise NotImplementedError("Implement recursive branching from given roots")


# -------------------------------
# Pipeline (read-only outline)
# -------------------------------
# The following mirrors the TEMPLATE.md pseudocode. It does not execute any
# geometry by default and leaves GhPython outputs as empty placeholders. Fill in
# your implementations above and call them here.

# Example variable names expected from GhPython inputs:
# base_surface, divU, divV, amplitude, frequency, phase,
# rec_depth, br_length, len_reduct, n_branches, seed

# 1. Seed RNG
seed_everything(seed)

# 2. Build UV grids
U, V = uv_grid(divU, divV)

# 3. Heightmap
H = heightmap(U, V, amplitude=amplitude, frequency=frequency, phase=phase)

# 4. Source point grid (choose ONE)
# P_src = make_point_grid_xy(divU, divV, origin=(0,0,0), size=(10,10))
P_src = sample_point_grid_from_surface(base_surface, U, V)

# 5. Deform points (choose ONE)
# P_def = manipulate_points_z(P_src, H)
P_def = manipulate_points_along_normals(P_src, H, base_surface, U, V)

# 6. Construct canopy surface
surf = surface_from_point_grid(P_def)

# 7. Uniform sampling for panelization
Sgrid = sample_surface_uniform(surf, divU, divV)

# 8. Tessellate into panels
panels = tessellate_panels_from_grid(Sgrid)

# 9. Choose support anchors
roots = bbox_corners(surf)

# 10. Generate supports
supports = generate_supports(
    roots,
    depth=rec_depth,
    length=br_length,
    length_reduction=len_reduct,
    n_children=n_branches,
    seed=seed,
)

# 11. Set GhPython outputs
out_surface      = None
out_tessellation = []
out_supports     = []

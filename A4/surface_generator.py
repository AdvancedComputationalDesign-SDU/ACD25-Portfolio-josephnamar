#r: numpy
import Rhino.Geometry as rg
import rhinoscriptsyntax as rs
import numpy as np
import random
import math

# ---------------------------------------------------------------------------
# INPUT CONTRACT (Grasshopper)
# ---------------------------------------------------------------------------
# Required inputs:
# - base_surface : Surface/BrepFace/Brep (if Brep, first face is used)
# - divU         : int, U subdivisions
# - divV         : int, V subdivisions
# - frequency    : float, wave frequency for heightmap
# - phase        : float, wave phase shift
# - amplitude    : float, displacement amplitude along surface normal
# - lift         : float, global Z offset after displacement
#
# Optional inputs:
# - seed            : int, random seed (for deterministic random mode)
# - heightmap_type  : int (0 = wave+bump, 1 = radial falloff + random noise)
#
# Outputs:
# - out_surface : generated displaced surface (NurbsSurface or Brep fallback)
# - out_points  : flattened displaced Point3d grid used to create the surface
# - srf_id      : compatibility output (always None in this RhinoCommon workflow)
# ---------------------------------------------------------------------------


def coerce_face_or_surface(geo):
    """Coerce GH/Rhino input into a RhinoCommon Surface/BrepFace when possible."""
    g = getattr(geo, "Geometry", geo)
    try:
        import System
        if isinstance(g, System.Guid):
            g = rs.coercesurface(g) or rs.coercebrep(g)
    except:
        pass
    if isinstance(g, rg.Brep) and g.Faces.Count > 0:
        return g.Faces[0]
    return g


def as_int(value, default, min_value=None):
    try:
        out = int(value)
    except:
        out = int(default)
    if min_value is not None and out < min_value:
        out = int(min_value)
    return out


def as_float(value, default, min_value=None):
    try:
        out = float(value)
    except:
        out = float(default)
    if min_value is not None and out < min_value:
        out = float(min_value)
    return out


def eval_point_normal(srf_obj, u, v):
    """Sample a surface point + unitized normal; fallback normal is +Z."""
    pt = srf_obj.PointAt(u, v)
    n = srf_obj.NormalAt(u, v)
    if (not n.IsValid) or n.IsZero:
        n = rg.Vector3d(0, 0, 1)
    else:
        n.Unitize()
    return pt, n


def generate_heightmap(U, V, amp, freq, phs, heightmap_type):
    """Generate a displacement field in normalized UV space."""
    un = np.linspace(0.0, 1.0, U + 1)
    vn = np.linspace(0.0, 1.0, V + 1)
    Un, Vn = np.meshgrid(un, vn, indexing="ij")

    if int(heightmap_type) == 0:
        # Structured field: sinusoidal wave blended with central bump.
        wave = np.sin((2.0 * math.pi * freq * (Un + Vn)) + phs)
        dist = np.sqrt((Un - 0.5) ** 2 + (Vn - 0.5) ** 2)
        bump = np.exp(-5.0 * dist ** 2)
        H = amp * (0.6 * wave + 0.4 * bump)
    else:
        # Stochastic field: radial falloff multiplied by random noise.
        R = np.sqrt((Un - 0.5) ** 2 + (Vn - 0.5) ** 2)
        mx = np.max(R) if np.max(R) != 0.0 else 1.0
        falloff = 1.0 - (R / mx)
        noise = (np.random.rand(*R.shape) - 0.5) * 2.0
        H = amp * falloff * noise

    return H


def build_surface_candidates(pts_grid, u_count, v_count, deg_u, deg_v):
    """Try both flattening orders when rebuilding a point-grid NurbsSurface."""
    pts_a = [pts_grid[i][j] for i in range(u_count) for j in range(v_count)]
    pts_b = [pts_grid[i][j] for j in range(v_count) for i in range(u_count)]

    srf_a = rg.NurbsSurface.CreateThroughPoints(pts_a, u_count, v_count, deg_u, deg_v, False, False)
    srf_b = rg.NurbsSurface.CreateThroughPoints(pts_b, u_count, v_count, deg_u, deg_v, False, False)
    return srf_a, pts_a, srf_b, pts_b


def loft_surface_from_grid(pts_grid, u_count, v_count, along_u=True):
    """Fallback if direct point-grid Nurbs reconstruction fails."""
    curves = []
    if along_u:
        for i in range(u_count):
            row_pts = [pts_grid[i][j] for j in range(v_count)]
            pl = rg.Polyline(row_pts)
            if pl.IsValid and pl.Count >= 2:
                curves.append(pl.ToNurbsCurve())
    else:
        for j in range(v_count):
            col_pts = [pts_grid[i][j] for i in range(u_count)]
            pl = rg.Polyline(col_pts)
            if pl.IsValid and pl.Count >= 2:
                curves.append(pl.ToNurbsCurve())

    if len(curves) < 2:
        return None

    breps = rg.Brep.CreateFromLoft(
        curves,
        rg.Point3d.Unset,
        rg.Point3d.Unset,
        rg.LoftType.Normal,
        False
    )
    if breps and len(breps) > 0 and breps[0] and breps[0].IsValid:
        return breps[0]
    return None


def first_face_surface(brep_obj):
    if brep_obj and isinstance(brep_obj, rg.Brep) and brep_obj.Faces.Count > 0:
        return brep_obj.Faces[0].ToNurbsSurface()
    return None


# ---------------------------------------------------------------------------
# INPUT NORMALIZATION
# ---------------------------------------------------------------------------
IN_base_surface = globals().get("base_surface", None)
IN_seed = globals().get("seed", None)
IN_divU = globals().get("divU", 24)
IN_divV = globals().get("divV", 24)
IN_frequency = globals().get("frequency", 1.0)
IN_phase = globals().get("phase", 0.0)
IN_amplitude = globals().get("amplitude", 1.0)
IN_lift = globals().get("lift", 0.0)
IN_heightmap_type = globals().get("heightmap_type", 0)

U = as_int(IN_divU, 24, min_value=1)
V = as_int(IN_divV, 24, min_value=1)
freq = as_float(IN_frequency, 1.0)
phs = as_float(IN_phase, 0.0)
amp = as_float(IN_amplitude, 1.0)
lift_val = as_float(IN_lift, 0.0)
heightmap_type = as_int(IN_heightmap_type, 0, min_value=0)

# Keep seed deterministic when provided.
if IN_seed is not None:
    try:
        seed_i = int(IN_seed)
        random.seed(seed_i)
        np.random.seed(seed_i)
    except:
        pass


# ---------------------------------------------------------------------------
# OUTPUTS
# ---------------------------------------------------------------------------
out_surface = None
out_points = []
srf_id = None  # Compatibility placeholder; no document object is created here.


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
srf_obj = coerce_face_or_surface(IN_base_surface)

if srf_obj is not None and isinstance(srf_obj, (rg.Surface, rg.BrepFace)):
    dom_u = srf_obj.Domain(0)
    dom_v = srf_obj.Domain(1)

    # Parameter-space sampling grid.
    u_vals = np.linspace(dom_u.T0, dom_u.T1, U + 1)
    v_vals = np.linspace(dom_v.T0, dom_v.T1, V + 1)
    Ug, Vg = np.meshgrid(u_vals, v_vals, indexing="ij")

    # Heightmap drives normal displacement.
    H = generate_heightmap(U, V, amp, freq, phs, heightmap_type)

    # Sample displaced points.
    pts_grid = [[None] * (V + 1) for _ in range(U + 1)]
    for i in range(U + 1):
        for j in range(V + 1):
            pt, n = eval_point_normal(srf_obj, float(Ug[i, j]), float(Vg[i, j]))
            p = pt + n * float(H[i, j])
            pts_grid[i][j] = rg.Point3d(float(p.X), float(p.Y), float(p.Z + lift_val))

    # Keep degrees valid for small grids.
    deg_u = 3 if (U + 1) >= 4 else max(1, U)
    deg_v = 3 if (V + 1) >= 4 else max(1, V)

    # Preferred reconstruction: direct Nurbs through points.
    srf_a, pts_a, srf_b, pts_b = build_surface_candidates(
        pts_grid, U + 1, V + 1, deg_u, deg_v
    )

    if srf_a and srf_a.IsValid:
        out_surface = srf_a
        out_points = pts_a
    elif srf_b and srf_b.IsValid:
        out_surface = srf_b
        out_points = pts_b
    else:
        # Fallback: loft across sampled rows/columns.
        loft_a = loft_surface_from_grid(pts_grid, U + 1, V + 1, along_u=True)
        loft_b = loft_surface_from_grid(pts_grid, U + 1, V + 1, along_u=False)

        if loft_a and loft_a.IsValid:
            out_surface = first_face_surface(loft_a) or loft_a
        elif loft_b and loft_b.IsValid:
            out_surface = first_face_surface(loft_b) or loft_b

        out_points = pts_a

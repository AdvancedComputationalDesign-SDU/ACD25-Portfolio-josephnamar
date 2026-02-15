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
# - divU         : int, U subdivisions used to rebuild out_surface
# - divV         : int, V subdivisions used to rebuild out_surface
# - frequency    : float, wave frequency for the displacement field
# - phase        : float, wave phase shift
# - amplitude    : float, displacement amplitude along surface normal
# - lift         : float, global Z offset after displacement
#
# Optional inputs:
# - seed            : int, deterministic seed (mainly for noise mode)
# - heightmap_type  : int (0 = wave+bump, 1 = radial falloff + deterministic noise)
#
# - point_divU      : int, optional output-point U subdivisions (independent of divU)
# - point_divV      : int, optional output-point V subdivisions (independent of divV)
#   Aliases supported: seed_divU/seed_divV, out_divU/out_divV
#
# Outputs:
# - out_surface : generated displaced surface (NurbsSurface or Brep fallback)
# - out_points  : flattened displaced Point3d grid (uses point_divU/point_divV)
# - srf_id      : compatibility output (always None in this RhinoCommon workflow)
# ---------------------------------------------------------------------------


def coerce_face_or_surface(geo):
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
    pt = srf_obj.PointAt(u, v)
    n = srf_obj.NormalAt(u, v)
    if (not n.IsValid) or n.IsZero:
        n = rg.Vector3d(0, 0, 1)
    else:
        n.Unitize()
    return pt, n


def deterministic_noise(un, vn, seed_val):
    # Deterministic pseudo-noise in [-1, 1], independent of grid resolution.
    n = np.sin((12.9898 * un) + (78.233 * vn) + (37.719 * float(seed_val))) * 43758.5453
    frac = n - np.floor(n)
    return (frac * 2.0) - 1.0


def evaluate_height_field(un, vn, amp, freq, phs, heightmap_type, seed_val):
    if int(heightmap_type) == 0:
        wave = np.sin((2.0 * math.pi * freq * (un + vn)) + phs)
        dist = np.sqrt((un - 0.5) ** 2 + (vn - 0.5) ** 2)
        bump = np.exp(-5.0 * dist ** 2)
        return amp * (0.6 * wave + 0.4 * bump)

    r = np.sqrt((un - 0.5) ** 2 + (vn - 0.5) ** 2)
    mx = np.max(r) if np.max(r) != 0.0 else 1.0
    falloff = 1.0 - (r / mx)
    noise = deterministic_noise(un, vn, seed_val)
    return amp * falloff * noise


def sample_displaced_grid(
    srf_obj,
    dom_u,
    dom_v,
    u_div,
    v_div,
    amp,
    freq,
    phs,
    heightmap_type,
    lift_val,
    seed_val
):
    # Parameter-space sampling.
    u_vals = np.linspace(dom_u.T0, dom_u.T1, u_div + 1)
    v_vals = np.linspace(dom_v.T0, dom_v.T1, v_div + 1)
    Ug, Vg = np.meshgrid(u_vals, v_vals, indexing="ij")

    # Normalized UV for displacement field evaluation.
    un = np.linspace(0.0, 1.0, u_div + 1)
    vn = np.linspace(0.0, 1.0, v_div + 1)
    Un, Vn = np.meshgrid(un, vn, indexing="ij")

    H = evaluate_height_field(Un, Vn, amp, freq, phs, heightmap_type, seed_val)

    pts_grid = [[None] * (v_div + 1) for _ in range(u_div + 1)]
    pts_flat = []

    for i in range(u_div + 1):
        for j in range(v_div + 1):
            pt, n = eval_point_normal(srf_obj, float(Ug[i, j]), float(Vg[i, j]))
            p = pt + n * float(H[i, j])
            p3 = rg.Point3d(float(p.X), float(p.Y), float(p.Z + lift_val))
            pts_grid[i][j] = p3
            pts_flat.append(p3)

    return pts_grid, pts_flat


def build_surface_candidates(pts_grid, u_count, v_count, deg_u, deg_v):
    pts_a = [pts_grid[i][j] for i in range(u_count) for j in range(v_count)]
    pts_b = [pts_grid[i][j] for j in range(v_count) for i in range(u_count)]

    srf_a = rg.NurbsSurface.CreateThroughPoints(pts_a, u_count, v_count, deg_u, deg_v, False, False)
    srf_b = rg.NurbsSurface.CreateThroughPoints(pts_b, u_count, v_count, deg_u, deg_v, False, False)
    return srf_a, pts_a, srf_b, pts_b


def loft_surface_from_grid(pts_grid, u_count, v_count, along_u=True):
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

# Independent output-point density controls.
IN_point_divU = globals().get(
    "point_divU",
    globals().get("seed_divU", globals().get("out_divU", IN_divU))
)
IN_point_divV = globals().get(
    "point_divV",
    globals().get("seed_divV", globals().get("out_divV", IN_divV))
)

U = as_int(IN_divU, 24, min_value=1)
V = as_int(IN_divV, 24, min_value=1)
U_pts = as_int(IN_point_divU, U, min_value=1)
V_pts = as_int(IN_point_divV, V, min_value=1)

freq = as_float(IN_frequency, 1.0)
phs = as_float(IN_phase, 0.0)
amp = as_float(IN_amplitude, 1.0)
lift_val = as_float(IN_lift, 0.0)
heightmap_type = as_int(IN_heightmap_type, 0, min_value=0)

seed_i = 0
if IN_seed is not None:
    try:
        seed_i = int(IN_seed)
    except:
        seed_i = 0
random.seed(seed_i)
np.random.seed(seed_i)


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

    # 1) Build displaced grid used to reconstruct the output surface.
    pts_grid_surface, pts_flat_surface = sample_displaced_grid(
        srf_obj,
        dom_u,
        dom_v,
        U,
        V,
        amp,
        freq,
        phs,
        heightmap_type,
        lift_val,
        seed_i
    )

    deg_u = 3 if (U + 1) >= 4 else max(1, U)
    deg_v = 3 if (V + 1) >= 4 else max(1, V)

    srf_a, pts_a, srf_b, pts_b = build_surface_candidates(
        pts_grid_surface, U + 1, V + 1, deg_u, deg_v
    )

    if srf_a and srf_a.IsValid:
        out_surface = srf_a
    elif srf_b and srf_b.IsValid:
        out_surface = srf_b
    else:
        loft_a = loft_surface_from_grid(pts_grid_surface, U + 1, V + 1, along_u=True)
        loft_b = loft_surface_from_grid(pts_grid_surface, U + 1, V + 1, along_u=False)

        if loft_a and loft_a.IsValid:
            out_surface = first_face_surface(loft_a) or loft_a
        elif loft_b and loft_b.IsValid:
            out_surface = first_face_surface(loft_b) or loft_b

    # 2) Build output points with independent density (for agent seeding/control).
    if (U_pts == U) and (V_pts == V):
        out_points = pts_flat_surface
    else:
        _, pts_flat_dense = sample_displaced_grid(
            srf_obj,
            dom_u,
            dom_v,
            U_pts,
            V_pts,
            amp,
            freq,
            phs,
            heightmap_type,
            lift_val,
            seed_i
        )
        out_points = pts_flat_dense

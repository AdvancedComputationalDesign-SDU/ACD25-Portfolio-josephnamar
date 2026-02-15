import Rhino
import Rhino.Geometry as rg
import rhinoscriptsyntax as rs
import numpy as np

from Grasshopper import DataTree
from Grasshopper.Kernel.Data import GH_Path

# ---------------------------------------------------------------------------
# OUTPUT VARIABLES
# ---------------------------------------------------------------------------
canopy_srf = None
canopy_pts_flat = []
canopy_pts_tree = DataTree[object]()
H_out = []

# Surface build candidates and runtime messages for debugging.
canopy_srf_A = None
canopy_srf_B = None
debug = []

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

def eval_point_normal(srf_obj, u, v):
    pt = srf_obj.PointAt(u, v)
    n = srf_obj.NormalAt(u, v)
    if (not n.IsValid) or n.IsZero:
        n = rg.Vector3d(0, 0, 1)
    else:
        n.Unitize()
    return pt, n

def generate_heightmap(du0, du1, dv0, dv1, U, V, amp, freq_u, freq_v, heightmap_type, seed):
    np.random.seed(int(seed) if seed is not None else 0)
    u_vals = np.linspace(du0, du1, U + 1)
    v_vals = np.linspace(dv0, dv1, V + 1)
    Ug, Vg = np.meshgrid(u_vals, v_vals, indexing="ij")

    if int(heightmap_type) == 0:
        H = amp * np.sin(freq_u * Ug) * np.cos(freq_v * Vg)
    else:
        cu = 0.5 * (du0 + du1)
        cv = 0.5 * (dv0 + dv1)
        R = np.sqrt((Ug - cu) ** 2 + (Vg - cv) ** 2)
        mx = np.max(R) if np.max(R) != 0 else 1.0
        falloff = 1.0 - (R / mx)
        noise = (np.random.rand(*R.shape) - 0.5) * 2.0
        H = amp * falloff * noise

    return Ug, Vg, H

def build_surface_candidates(pts_grid, u_count, v_count, deg_u, deg_v):
    # Candidate A uses i-major flattening.
    pts_a = [pts_grid[i][j] for i in range(u_count) for j in range(v_count)]
    # Candidate B uses j-major flattening.
    pts_b = [pts_grid[i][j] for j in range(v_count) for i in range(u_count)]

    srf_a = rg.NurbsSurface.CreateThroughPoints(pts_a, u_count, v_count, deg_u, deg_v, False, False)
    srf_b = rg.NurbsSurface.CreateThroughPoints(pts_b, u_count, v_count, deg_u, deg_v, False, False)

    return srf_a, pts_a, srf_b, pts_b

def loft_surface_from_grid(pts_grid, u_count, v_count, along_u=True):
    section_curves = []
    if along_u:
        for i in range(u_count):
            row_pts = [pts_grid[i][j] for j in range(v_count)]
            pl = rg.Polyline(row_pts)
            if pl.IsValid and pl.Count >= 2:
                section_curves.append(pl.ToNurbsCurve())
    else:
        for j in range(v_count):
            col_pts = [pts_grid[i][j] for i in range(u_count)]
            pl = rg.Polyline(col_pts)
            if pl.IsValid and pl.Count >= 2:
                section_curves.append(pl.ToNurbsCurve())

    if len(section_curves) < 2:
        return None

    loft = rg.Brep.CreateFromLoft(
        section_curves,
        rg.Point3d.Unset,
        rg.Point3d.Unset,
        rg.LoftType.Normal,
        False
    )
    if loft and len(loft) > 0 and loft[0] and loft[0].IsValid:
        return loft[0]
    return None

def first_face_surface(brep_obj):
    if brep_obj and isinstance(brep_obj, rg.Brep) and brep_obj.Faces.Count > 0:
        return brep_obj.Faces[0].ToNurbsSurface()
    return None

def is_finite_point(p):
    # Check both Rhino validity and finite numeric values.
    if p is None or (not p.IsValid):
        return False
    x, y, z = p.X, p.Y, p.Z
    if (x != x) or (y != y) or (z != z):
        return False
    if abs(x) > 1e12 or abs(y) > 1e12 or abs(z) > 1e12:
        return False
    return True

def as_int(value, default, min_value=None):
    try:
        out = int(value)
    except (TypeError, ValueError):
        out = int(default)
    if min_value is not None and out < min_value:
        out = int(min_value)
    return out

def as_float(value, default, min_value=None):
    try:
        out = float(value)
    except (TypeError, ValueError):
        out = float(default)
    if min_value is not None and out < min_value:
        out = float(min_value)
    return out

# ---------------------------------------------------------------------------
# INPUT NORMALIZATION
# ---------------------------------------------------------------------------
U = as_int(U, 30, min_value=1)
V = as_int(V, 15, min_value=1)
amp = as_float(amp, 5.0)
freq_u = as_float(freq_u, 1.0)
freq_v = as_float(freq_v, 1.0)
heightmap_type = as_int(heightmap_type, 0, min_value=0)
seed = as_int(seed, 1)
tessellation_type = as_int(globals().get("tessellation_type", 0), 0, min_value=0)
if tessellation_type not in (0, 1):
    tessellation_type = 0

debug.append(
    "Inputs sanitized: U={}, V={}, amp={}, freq_u={}, freq_v={}, heightmap_type={}, seed={}, tessellation_type={}".format(
        U, V, amp, freq_u, freq_v, heightmap_type, seed, tessellation_type
    )
)

srf_obj = coerce_face_or_surface(srf)
pts_grid = []
bad_count = 0

if srf_obj is None:
    debug.append("srf is None or could not be coerced.")
else:
    du = srf_obj.Domain(0); dv = srf_obj.Domain(1)
    du0, du1 = du.T0, du.T1
    dv0, dv1 = dv.T0, dv.T1

    Ug, Vg, H = generate_heightmap(du0, du1, dv0, dv1, U, V, amp, freq_u, freq_v, heightmap_type, seed)
    H_out = H.tolist()

    # Sample displaced points and store them in list/tree form.
    pts_grid = [[None]*(V+1) for _ in range(U+1)]
    bad_count = 0

    for i in range(U + 1):
        path = GH_Path(i)
        for j in range(V + 1):
            u = float(Ug[i, j]); v = float(Vg[i, j])
            pt, n = eval_point_normal(srf_obj, u, v)
            p = pt + n * float(H[i, j])
            p = rg.Point3d(float(p.X), float(p.Y), float(p.Z))
            pts_grid[i][j] = p
            canopy_pts_tree.Add(p, path)
            if not is_finite_point(p):
                bad_count += 1

    debug.append("Grid size expected: {} x {}".format(U+1, V+1))
    debug.append("Invalid/NaN points found: {}".format(bad_count))

    # Keep surface degree within valid limits for the current grid size.
    deg_u = 3 if (U + 1) >= 4 else max(1, (U + 1) - 1)
    deg_v = 3 if (V + 1) >= 4 else max(1, (V + 1) - 1)

    debug.append("Degrees used: ({}, {})".format(deg_u, deg_v))

    srf_A, Pts_A, srf_B, Pts_B = build_surface_candidates(
        pts_grid, U + 1, V + 1, deg_u, deg_v
    )

    canopy_srf_A = srf_A
    canopy_srf_B = srf_B

    debug.append("CreateThroughPoints A valid: {}".format(bool(srf_A and srf_A.IsValid)))
    debug.append("CreateThroughPoints B valid: {}".format(bool(srf_B and srf_B.IsValid)))

    # Prefer direct NURBS reconstruction; fall back to loft if needed.
    if srf_A and srf_A.IsValid:
        canopy_srf = srf_A
        canopy_pts_flat = Pts_A
        debug.append("Chosen: A (i-major flatten).")
    elif srf_B and srf_B.IsValid:
        canopy_srf = srf_B
        canopy_pts_flat = Pts_B
        debug.append("Chosen: B (j-major flatten).")
    else:
        loft_A = loft_surface_from_grid(pts_grid, U + 1, V + 1, along_u=True)
        loft_B = loft_surface_from_grid(pts_grid, U + 1, V + 1, along_u=False)
        debug.append("Loft fallback A valid: {}".format(bool(loft_A and loft_A.IsValid)))
        debug.append("Loft fallback B valid: {}".format(bool(loft_B and loft_B.IsValid)))

        if loft_A and loft_A.IsValid:
            surf_from_loft_A = first_face_surface(loft_A)
            canopy_srf = surf_from_loft_A if surf_from_loft_A else loft_A
            debug.append("Chosen: Loft fallback A (sections along U). Face surface extracted: {}".format(bool(surf_from_loft_A)))
        elif loft_B and loft_B.IsValid:
            surf_from_loft_B = first_face_surface(loft_B)
            canopy_srf = surf_from_loft_B if surf_from_loft_B else loft_B
            debug.append("Chosen: Loft fallback B (sections along V). Face surface extracted: {}".format(bool(surf_from_loft_B)))
        else:
            canopy_srf = None
            debug.append("All surface build attempts failed.")

        canopy_pts_flat = Pts_A
        debug.append("Most likely cause: grid ordering mismatch or problematic source surface/domain.")

if canopy_srf is not None:
    debug.append("Final canopy_srf type: {}".format(type(canopy_srf).__name__))

# ---------------------------------------------------------------------------
# TESSELLATION
# ---------------------------------------------------------------------------
panels = []
mesh = rg.Mesh()

if srf_obj is not None and bad_count == 0:
    # Vertex index convention: i*(V+1) + j.
    rows = U + 1
    cols = V + 1

    # Add mesh vertices.
    for i in range(rows):
        for j in range(cols):
            mesh.Vertices.Add(pts_grid[i][j])

    # Build panel curves and corresponding mesh faces cell by cell.
    for i in range(rows - 1):
        for j in range(cols - 1):
            A = pts_grid[i][j]
            B = pts_grid[i + 1][j]
            C = pts_grid[i + 1][j + 1]
            D = pts_grid[i][j + 1]

            # Mesh indices for this cell.
            a = i * cols + j
            b = a + cols
            c = b + 1
            d = a + 1

            if tessellation_type == 0:
                quad_pl = rg.Polyline([A, B, C, D, A])
                panels.append(quad_pl.ToNurbsCurve())
                mesh.Faces.AddFace(a, b, c, d)
            else:
                tri1 = rg.Polyline([A, B, C, A])
                tri2 = rg.Polyline([A, C, D, A])
                panels.append(tri1.ToNurbsCurve())
                panels.append(tri2.ToNurbsCurve())
                mesh.Faces.AddFace(a, b, c)
                mesh.Faces.AddFace(a, c, d)

    mesh.Normals.ComputeNormals()
    mesh.Compact()
else:
    # Skip tessellation when point sampling is invalid.
    panels = []
    mesh = None

# ---------------------------------------------------------------------------
# FINAL OUTPUTS
# ---------------------------------------------------------------------------
out_points_flat = canopy_pts_flat
out_points_tree = canopy_pts_tree
out_heightmap = H_out
out_panels = panels
out_mesh = mesh

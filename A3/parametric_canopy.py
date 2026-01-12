import Rhino
import Rhino.Geometry as rg
import rhinoscriptsyntax as rs
import numpy as np

from Grasshopper import DataTree
from Grasshopper.Kernel.Data import GH_Path

# --- outputs you already have ---
canopy_srf = None
canopy_pts_flat = []
canopy_pts_tree = DataTree[object]()
H_out = []

# --- optional debug outputs (create in GH if you want) ---
canopy_srf_A = None  # flatten order A
canopy_srf_B = None  # flatten order B
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
    Ug, Vg = np.meshgrid(u_vals, v_vals, indexing="ij")  # (U+1, V+1)

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

def is_finite_point(p):
    # Rhino Point3d has IsValid, but not NaN check; do both
    if p is None or (not p.IsValid):
        return False
    x, y, z = p.X, p.Y, p.Z
    if (x != x) or (y != y) or (z != z):  # NaN check
        return False
    if abs(x) > 1e12 or abs(y) > 1e12 or abs(z) > 1e12:
        return False
    return True

# --- sanitize inputs ---
U = int(U) if U is not None else 30
V = int(V) if V is not None else 15
amp = float(amp) if amp is not None else 5.0
freq_u = float(freq_u) if freq_u is not None else 1.0
freq_v = float(freq_v) if freq_v is not None else 1.0
heightmap_type = int(heightmap_type) if heightmap_type is not None else 0
seed = int(seed) if seed is not None else 1

srf_obj = coerce_face_or_surface(srf)

if srf_obj is None:
    debug.append("srf is None or could not be coerced.")
else:
    du = srf_obj.Domain(0); dv = srf_obj.Domain(1)
    du0, du1 = du.T0, du.T1
    dv0, dv1 = dv.T0, dv.T1

    Ug, Vg, H = generate_heightmap(du0, du1, dv0, dv1, U, V, amp, freq_u, freq_v, heightmap_type, seed)
    H_out = H.tolist()

    # Build grid and tree
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

    # Two flatten orders
    # A: i-major then j (row-major in U)
    Pts_A = [pts_grid[i][j] for i in range(U+1) for j in range(V+1)]
    # B: j-major then i (row-major in V)
    Pts_B = [pts_grid[i][j] for j in range(V+1) for i in range(U+1)]

    # Degrees
    deg_u = 3 if (U + 1) >= 4 else max(1, (U + 1) - 1)
    deg_v = 3 if (V + 1) >= 4 else max(1, (V + 1) - 1)

    debug.append("Degrees used: ({}, {})".format(deg_u, deg_v))

    # Try both surfaces using AddSrfPtGrid
    guid_A = rs.AddSrfPtGrid((U+1, V+1), Pts_A, degree=(deg_u, deg_v))
    guid_B = rs.AddSrfPtGrid((U+1, V+1), Pts_B, degree=(deg_u, deg_v))

    canopy_srf_A = guid_A
    canopy_srf_B = guid_B

    debug.append("AddSrfPtGrid guid_A: {}".format(guid_A))
    debug.append("AddSrfPtGrid guid_B: {}".format(guid_B))

    # Choose the one that worked
    if guid_A:
        canopy_srf = guid_A
        canopy_pts_flat = Pts_A
        debug.append("Chosen: A (i-major flatten).")
    elif guid_B:
        canopy_srf = guid_B
        canopy_pts_flat = Pts_B
        debug.append("Chosen: B (j-major flatten).")
    else:
        canopy_srf = None
        canopy_pts_flat = Pts_A
        debug.append("Both surface builds failed. Most likely cause: invalid points or srf is problematic (trimmed/singular).")

# -------------------------
# Tessellation (Step 2)
# -------------------------
panels_quads = []
panels_tris = []
mesh_quads = rg.Mesh()
mesh_tris = rg.Mesh()

if srf_obj is not None and bad_count == 0:
    # Build vertices for meshes from pts_grid in a consistent indexing scheme:
    # vertex index = i*(V+1) + j  (i-major, j-minor)
    rows = U + 1
    cols = V + 1

    # Add vertices
    for i in range(rows):
        for j in range(cols):
            mesh_quads.Vertices.Add(pts_grid[i][j])
            mesh_tris.Vertices.Add(pts_grid[i][j])

    # Build faces + panel polylines per cell
    for i in range(rows - 1):
        for j in range(cols - 1):
            A = pts_grid[i][j]
            B = pts_grid[i + 1][j]
            C = pts_grid[i + 1][j + 1]
            D = pts_grid[i][j + 1]

            # Quad polyline (closed)
            quad_pl = rg.Polyline([A, B, C, D, A])
            panels_quads.append(quad_pl.ToNurbsCurve())

            # Two triangle polylines (closed)
            tri1 = rg.Polyline([A, B, C, A])
            tri2 = rg.Polyline([A, C, D, A])
            panels_tris.append(tri1.ToNurbsCurve())
            panels_tris.append(tri2.ToNurbsCurve())

            # Mesh indices
            a = i * cols + j
            b = a + cols
            c = b + 1
            d = a + 1

            # Quad mesh face (as quad)
            mesh_quads.Faces.AddFace(a, b, c, d)

            # Tri mesh faces (two triangles)
            mesh_tris.Faces.AddFace(a, b, c)
            mesh_tris.Faces.AddFace(a, c, d)

    mesh_quads.Normals.ComputeNormals()
    mesh_quads.Compact()

    mesh_tris.Normals.ComputeNormals()
    mesh_tris.Compact()
else:
    # If you have invalid points, panels/meshes are unreliable
    panels_quads = []
    panels_tris = []
    mesh_quads = None
    mesh_tris = None

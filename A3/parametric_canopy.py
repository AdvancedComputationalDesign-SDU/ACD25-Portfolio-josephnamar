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
root_points = []
root_points_ground = []
root_trunks = []
support_branches = []
supports = []

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

def heightmap_local_minima_indices(H):
    rows, cols = H.shape
    minima = []
    if rows < 3 or cols < 3:
        idx = np.unravel_index(np.argmin(H), H.shape)
        return [(int(idx[0]), int(idx[1]), float(H[idx]))]

    for i in range(1, rows - 1):
        for j in range(1, cols - 1):
            h_ij = float(H[i, j])
            is_local_min = True
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if di == 0 and dj == 0:
                        continue
                    ni = i + di
                    nj = j + dj
                    if float(H[ni, nj]) < h_ij:
                        is_local_min = False
                        break
                if not is_local_min:
                    break
            if is_local_min:
                minima.append((i, j, h_ij))

    if not minima:
        idx = np.unravel_index(np.argmin(H), H.shape)
        minima = [(int(idx[0]), int(idx[1]), float(H[idx]))]

    minima.sort(key=lambda x: x[2])
    return minima

def dedupe_line_curves(curves, precision=6):
    out = []
    seen = set()
    for c in curves:
        if c is None:
            continue
        p0 = c.PointAtStart
        p1 = c.PointAtEnd
        key = (
            round(p0.X, precision), round(p0.Y, precision), round(p0.Z, precision),
            round(p1.X, precision), round(p1.Y, precision), round(p1.Z, precision)
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out

def trim_branches_to_mesh(curves, mesh_obj, tol=1e-3, cull_non_intersecting=False):
    if not curves:
        return []
    if mesh_obj is None or (not isinstance(mesh_obj, rg.Mesh)) or mesh_obj.Vertices.Count == 0:
        return list(curves)

    trimmed = []
    for c in curves:
        if c is None:
            continue

        p0 = c.PointAtStart
        p1 = c.PointAtEnd
        if p0.DistanceTo(p1) <= tol:
            continue

        line = rg.Line(p0, p1)
        hit_raw = None
        try:
            hit_raw = rg.Intersect.Intersection.MeshLine(mesh_obj, line)
        except:
            hit_raw = None

        hit_pts = []
        def collect_meshline_hits(obj):
            if obj is None:
                return
            if isinstance(obj, rg.Point3d):
                hit_pts.append(obj)
                return
            if isinstance(obj, (int, float)):
                t = float(obj)
                if (-tol <= t) and (t <= 1.0 + tol):
                    hit_pts.append(line.PointAt(t))
                return
            try:
                it = iter(obj)
            except TypeError:
                try:
                    t = float(obj)
                    if (-tol <= t) and (t <= 1.0 + tol):
                        hit_pts.append(line.PointAt(t))
                except:
                    pass
                return
            for sub in it:
                collect_meshline_hits(sub)

        collect_meshline_hits(hit_raw)

        if not hit_pts:
            if not cull_non_intersecting:
                trimmed.append(c)
            continue

        first_hit = None
        best_d = None
        for hp in hit_pts:
            d = p0.DistanceTo(hp)
            if (best_d is None) or (d < best_d):
                best_d = d
                first_hit = hp

        if first_hit is None:
            if not cull_non_intersecting:
                trimmed.append(c)
            continue

        if p0.DistanceTo(first_hit) > tol:
            trimmed.append(rg.Line(p0, first_hit).ToNurbsCurve())

    return dedupe_line_curves(trimmed)

def generate_recursive_support_branches(
    root_ground_pts,
    root_top_pts,
    depth,
    branches_per_node,
    base_length,
    length_reduction,
    branch_start_height,
    trim_mesh=None,
    trim_tol=1e-3
):
    if depth <= 0:
        return []

    def local_frame_from_direction(direction):
        d = rg.Vector3d(direction)
        if d.IsZero:
            d = rg.Vector3d(0, 0, 1)
        d.Unitize()

        ref = rg.Vector3d(0, 0, 1)
        if abs(rg.Vector3d.Multiply(d, ref)) > 0.95:
            ref = rg.Vector3d(1, 0, 0)

        x_axis = rg.Vector3d.CrossProduct(d, ref)
        if x_axis.IsZero:
            x_axis = rg.Vector3d(1, 0, 0)
        x_axis.Unitize()

        y_axis = rg.Vector3d.CrossProduct(d, x_axis)
        if y_axis.IsZero:
            y_axis = rg.Vector3d(0, 1, 0)
        y_axis.Unitize()

        return x_axis, y_axis

    root_count = min(len(root_ground_pts), len(root_top_pts))
    non_leaf_segments = []
    leaf_records = []

    for idx in range(root_count):
        root_ground = root_ground_pts[idx]
        target_pt = root_top_pts[idx]

        trunk_vec = rg.Vector3d(target_pt - root_ground)
        trunk_len = trunk_vec.Length
        if trunk_len > 1e-6:
            trunk_dir = rg.Vector3d(trunk_vec)
            trunk_dir.Unitize()
            start_dist = min(max(float(branch_start_height), 0.0), trunk_len)
            start_pt = root_ground + trunk_dir * start_dist
        else:
            start_pt = root_ground

        base_dir = rg.Vector3d(target_pt - start_pt)
        if base_dir.IsZero:
            base_dir = rg.Vector3d(0, 0, 1)
        else:
            base_dir.Unitize()

        trunk_dist = root_ground.DistanceTo(target_pt)
        first_len = float(base_length) if base_length > 0.0 else (trunk_dist / float(max(1, depth)))
        if first_len <= 1e-6:
            first_len = 1.0

        root_phase = (0.173 * float(start_pt.X) + 0.117 * float(start_pt.Y) + 0.619 * float(idx)) % (2.0 * np.pi)

        def grow(point, direction, level, length):
            if level <= 0 or length <= 1e-6:
                return

            x_axis, y_axis = local_frame_from_direction(direction)

            for branch_idx in range(branches_per_node):
                theta = root_phase + (2.0 * np.pi * float(branch_idx)) / float(max(1, branches_per_node))
                theta += 0.45 * float(level)

                lateral = x_axis * float(np.cos(theta)) + y_axis * float(np.sin(theta))
                new_dir = rg.Vector3d(direction) * 0.85
                new_dir += lateral * 0.50
                if new_dir.IsZero:
                    new_dir = rg.Vector3d(direction)
                if new_dir.IsZero:
                    new_dir = rg.Vector3d(0, 0, 1)
                new_dir.Unitize()

                end_pt = point + new_dir * float(length)
                seg_curve = rg.Line(point, end_pt).ToNurbsCurve()
                if level == 1:
                    leaf_records.append((seg_curve, end_pt, rg.Vector3d(new_dir)))
                else:
                    non_leaf_segments.append(seg_curve)
                    grow(end_pt, new_dir, level - 1, length * float(length_reduction))

        grow(start_pt, base_dir, depth, first_len)

    leaf_extension = 10.0
    leaf_segments = []
    for leaf_seg, tip_pt, tip_dir in leaf_records:
        leaf_start = leaf_seg.PointAtStart
        ext_dir = rg.Vector3d(tip_dir)
        if ext_dir.IsZero:
            continue

        ext_dir.Unitize()
        extended_tip = tip_pt + ext_dir * leaf_extension
        if leaf_start.DistanceTo(extended_tip) > 1e-6:
            leaf_segments.append(rg.Line(leaf_start, extended_tip).ToNurbsCurve())

    if trim_mesh is None:
        return dedupe_line_curves(list(non_leaf_segments) + list(leaf_segments))

    kept_non_leaf = trim_branches_to_mesh(
        non_leaf_segments, trim_mesh, tol=trim_tol, cull_non_intersecting=False
    )
    kept_leaf = trim_branches_to_mesh(
        leaf_segments, trim_mesh, tol=trim_tol, cull_non_intersecting=True
    )
    return dedupe_line_curves(list(kept_non_leaf) + list(kept_leaf))

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
rec_depth = as_int(globals().get("rec_depth", 3), 3, min_value=0)
n_branches = as_int(globals().get("n_branches", 2), 2, min_value=1)
br_length = as_float(globals().get("br_length", 0.0), 0.0, min_value=0.0)
len_reduct = as_float(globals().get("len_reduct", 0.7), 0.7)
if len_reduct <= 0.0:
    len_reduct = 0.7
if len_reduct >= 1.0:
    len_reduct = 0.95
branch_start_height = as_float(globals().get("branch_start_height", 0.0), 0.0, min_value=0.0)
max_branch_roots = as_int(globals().get("max_branch_roots", 8), 8, min_value=1)

srf_obj = coerce_face_or_surface(srf)
pts_grid = []
bad_count = 0

if srf_obj is not None:
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

    # Keep surface degree within valid limits for the current grid size.
    deg_u = 3 if (U + 1) >= 4 else max(1, (U + 1) - 1)
    deg_v = 3 if (V + 1) >= 4 else max(1, (V + 1) - 1)

    srf_A, Pts_A, srf_B, Pts_B = build_surface_candidates(
        pts_grid, U + 1, V + 1, deg_u, deg_v
    )

    # Prefer direct NURBS reconstruction; fall back to loft if needed.
    if srf_A and srf_A.IsValid:
        canopy_srf = srf_A
        canopy_pts_flat = Pts_A
    elif srf_B and srf_B.IsValid:
        canopy_srf = srf_B
        canopy_pts_flat = Pts_B
    else:
        loft_A = loft_surface_from_grid(pts_grid, U + 1, V + 1, along_u=True)
        loft_B = loft_surface_from_grid(pts_grid, U + 1, V + 1, along_u=False)

        if loft_A and loft_A.IsValid:
            surf_from_loft_A = first_face_surface(loft_A)
            canopy_srf = surf_from_loft_A if surf_from_loft_A else loft_A
        elif loft_B and loft_B.IsValid:
            surf_from_loft_B = first_face_surface(loft_B)
            canopy_srf = surf_from_loft_B if surf_from_loft_B else loft_B
        else:
            canopy_srf = None

        canopy_pts_flat = Pts_A

# ---------------------------------------------------------------------------
# ROOT POINTS (FROM HEIGHTMAP MINIMA)
# ---------------------------------------------------------------------------
if pts_grid and bad_count == 0:
    minima = heightmap_local_minima_indices(H)
    for i, j, _ in minima:
        p_top = pts_grid[i][j]
        p_ground = rg.Point3d(p_top.X, p_top.Y, 0.0)
        root_points.append(p_top)
        root_points_ground.append(p_ground)
        root_trunks.append(rg.Line(p_ground, p_top).ToNurbsCurve())

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
# RECURSIVE SUPPORT BRANCHES
# ---------------------------------------------------------------------------
if root_points and root_points_ground and rec_depth > 0:
    root_count = min(len(root_points), max_branch_roots)
    trim_tol = 1e-3
    if mesh is not None:
        try:
            doc = Rhino.RhinoDoc.ActiveDoc
            if doc is not None:
                trim_tol = max(trim_tol, float(doc.ModelAbsoluteTolerance))
        except:
            pass
    support_branches = generate_recursive_support_branches(
        root_points_ground[:root_count],
        root_points[:root_count],
        rec_depth,
        n_branches,
        br_length,
        len_reduct,
        branch_start_height,
        trim_mesh=mesh,
        trim_tol=trim_tol
    )
else:
    support_branches = []

supports = list(root_trunks) + list(support_branches)

# ---------------------------------------------------------------------------
# FINAL OUTPUTS
# ---------------------------------------------------------------------------
out_points_flat = canopy_pts_flat
out_points_tree = canopy_pts_tree
out_heightmap = H_out
out_root_points = root_points
out_root_points_ground = root_points_ground
out_root_trunks = root_trunks
out_support_branches = support_branches
out_supports = supports
out_panels = panels
out_mesh = mesh

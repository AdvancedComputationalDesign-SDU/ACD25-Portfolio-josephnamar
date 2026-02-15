import scriptcontext as sc
import Rhino.Geometry as rg
import rhinoscriptsyntax as rs

# ---------------------------------------------------------------------------
# INPUT CONTRACT (Grasshopper)
# ---------------------------------------------------------------------------
# Inputs:
# - run          : bool. When False, no mesh is generated.
# - base_surface : Surface/BrepFace/Brep (if Brep, first face is used)
# - points       : moving points (typically simulator P output)
#
# Optional inputs:
# - grid_u         : int. Optional explicit number of points in U direction.
# - grid_v         : int. Optional explicit number of points in V direction.
#
# Outputs:
# - out_mesh  : quad mesh (disconnected quads for per-panel shape stability)
# - out_edges : panel boundary lines
# - dbg       : debug string
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def as_list(x):
    if x is None:
        return []
    try:
        items = list(x)
    except:
        return [x]

    # One-level unwrap for common GH case: (points_list,)
    if len(items) == 1:
        only = items[0]
        try:
            nested = list(only)
            if len(nested) > 0:
                return nested
        except:
            pass
    return items


def as_bool(v, default=False):
    if v is None:
        return bool(default)
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("1", "true", "t", "yes", "y", "on"):
        return True
    if s in ("0", "false", "f", "no", "n", "off"):
        return False
    return bool(default)


def as_int(v, default, min_value=None):
    try:
        out = int(v)
    except:
        out = int(default)
    if min_value is not None and out < min_value:
        out = int(min_value)
    return out


def as_float(v, default):
    try:
        return float(v)
    except:
        return float(default)


def clamp01(x):
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def clamp(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def to_point3d(obj):
    """
    Robust point coercion for GH wiring variants:
    - Point3d / point-like objects
    - wrapped objects with .Location
    - Agent objects with .position
    """
    if obj is None:
        return None

    # Agent-like object from simulator/builder.
    if hasattr(obj, "position"):
        try:
            return rg.Point3d(obj.position)
        except:
            pass

    p = getattr(obj, "Location", obj)
    try:
        return rg.Point3d(p)
    except:
        pass
    try:
        return rg.Point3d(float(p.X), float(p.Y), float(p.Z))
    except:
        return None


def coerce_face(base_surface):
    srf = getattr(base_surface, "Geometry", base_surface)

    try:
        import System
        if isinstance(srf, System.Guid):
            srf = rs.coercesurface(srf) or rs.coercebrep(srf)
    except:
        pass

    if isinstance(srf, rg.Brep):
        if srf.Faces.Count == 0:
            return None
        srf = srf.Faces[0]

    if not isinstance(srf, (rg.Surface, rg.BrepFace)):
        return None

    return srf


def project_points_to_uv(surface, pts):
    uv = []
    valid_pts = []
    bad = 0
    for p in pts:
        p3 = to_point3d(p)
        if p3 is None:
            bad += 1
            continue

        ok, u, v = surface.ClosestPoint(p3)
        if not ok:
            bad += 1
            continue

        uv.append((float(u), float(v)))
        valid_pts.append(p3)

    return uv, valid_pts, bad


def infer_grid_dims(n, aspect_uv):
    """
    Infer (u_count, v_count) from number of points using factor pairs.
    Chooses pair whose u/v ratio best matches surface UV aspect.
    """
    if n < 4:
        return None

    candidates = []
    r = int(n ** 0.5)
    for a in range(2, r + 1):
        if n % a != 0:
            continue
        b = n // a
        candidates.append((a, b))
        if a != b:
            candidates.append((b, a))

    if not candidates:
        return None

    best = None
    best_err = None
    target = max(1e-9, float(aspect_uv))
    for u_count, v_count in candidates:
        ratio = float(u_count) / float(v_count)
        err = abs(ratio - target)
        if (best_err is None) or (err < best_err):
            best_err = err
            best = (u_count, v_count)

    return best


def build_quad_faces(u_count, v_count):
    """
    Flat index convention: idx = i * v_count + j
    where i in [0, u_count-1], j in [0, v_count-1].
    """
    quads = []
    for i in range(u_count - 1):
        for j in range(v_count - 1):
            a = i * v_count + j
            b = (i + 1) * v_count + j
            c = (i + 1) * v_count + (j + 1)
            d = i * v_count + (j + 1)
            quads.append((a, b, c, d))
    return quads


# -----------------------
# Optional fallback triangulation
# -----------------------
def orient2d(ax, ay, bx, by, cx, cy):
    return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)


def circumcircle_contains(ax, ay, bx, by, cx, cy, px, py):
    ax -= px
    ay -= py
    bx -= px
    by -= py
    cx -= px
    cy -= py

    a2 = ax * ax + ay * ay
    b2 = bx * bx + by * by
    c2 = cx * cx + cy * cy

    det = (ax * (by * c2 - b2 * cy) -
           ay * (bx * c2 - b2 * cx) +
           a2 * (bx * cy - by * cx))
    return det > 1e-12


def delaunay_triangulate_2d(pts):
    n = len(pts)
    if n < 3:
        return []

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    dmax = max(maxx - minx, maxy - miny)
    if dmax == 0.0:
        return []

    mx = 0.5 * (minx + maxx)
    my = 0.5 * (miny + maxy)

    p0 = (mx - 20 * dmax, my - dmax)
    p1 = (mx, my + 20 * dmax)
    p2 = (mx + 20 * dmax, my - dmax)

    pts_ext = pts + [p0, p1, p2]
    s0, s1, s2 = n, n + 1, n + 2
    tris = [(s0, s1, s2)]

    for i in range(n):
        px, py = pts_ext[i]
        bad = []

        for t in tris:
            ia, ib, ic = t
            ax, ay = pts_ext[ia]
            bx, by = pts_ext[ib]
            cx, cy = pts_ext[ic]

            if orient2d(ax, ay, bx, by, cx, cy) < 0.0:
                bx, by, cx, cy = cx, cy, bx, by

            if circumcircle_contains(ax, ay, bx, by, cx, cy, px, py):
                bad.append(t)

        edge_count = {}

        def add_edge(a, b):
            if a > b:
                a, b = b, a
            edge_count[(a, b)] = edge_count.get((a, b), 0) + 1

        for ia, ib, ic in bad:
            add_edge(ia, ib)
            add_edge(ib, ic)
            add_edge(ic, ia)

        if bad:
            bad_set = set(bad)
            tris = [t for t in tris if t not in bad_set]

        boundary = [e for e, c in edge_count.items() if c == 1]
        for a, b in boundary:
            tris.append((a, b, i))

    out = []
    for a, b, c in tris:
        if a >= n or b >= n or c >= n:
            continue
        if a == b or b == c or c == a:
            continue
        out.append((a, b, c))

    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
out_mesh = None
out_edges = []
dbg = ""

run_flag = as_bool(globals().get("run", True), True)

if not run_flag:
    dbg = "run is False"
else:
    srf = coerce_face(globals().get("base_surface", None))
    pts = as_list(globals().get("points", None))

    if srf is None:
        dbg = "ERROR: base_surface is invalid"
    elif len(pts) < 3:
        dbg = "ERROR: need at least 3 points"
    else:
        uv_pts, valid_pts, bad = project_points_to_uv(srf, pts)
        n = len(uv_pts)

        if n < 3:
            dbg = "ERROR: <3 valid projected points (bad={})".format(bad)
        else:
            dom_u = srf.Domain(0)
            dom_v = srf.Domain(1)
            du = float(dom_u.T1 - dom_u.T0)
            dv = float(dom_v.T1 - dom_v.T0)
            if du == 0.0 or dv == 0.0:
                dbg = "ERROR: surface domain is degenerate"
            else:
                aspect = abs(du / dv) if abs(dv) > 1e-12 else 1.0

                # Optional explicit grid dimensions (points in U and V).
                gu_in = globals().get("grid_u", None)
                gv_in = globals().get("grid_v", None)
                if (gu_in is not None) and (gv_in is not None):
                    u_count = as_int(gu_in, 0, min_value=2)
                    v_count = as_int(gv_in, 0, min_value=2)
                    dims = (u_count, v_count)
                else:
                    dims = infer_grid_dims(n, aspect)

                use_quads = False
                if dims is not None:
                    u_count, v_count = dims
                    if (u_count * v_count) == n and u_count >= 2 and v_count >= 2:
                        use_quads = True

                if use_quads:
                    guid = str(ghenv.Component.InstanceGuid)
                    k_dims = "A4_quad_dims_" + guid
                    k_faces = "A4_quad_faces_" + guid

                    quads = build_quad_faces(u_count, v_count)

                    if (sc.sticky.get(k_dims, None) != (u_count, v_count)) or (k_faces not in sc.sticky):
                        sc.sticky[k_dims] = (u_count, v_count)
                        sc.sticky[k_faces] = quads

                    quads = sc.sticky.get(k_faces, quads)

                    mesh = rg.Mesh()

                    # Build disconnected quads directly from current moving points.
                    for (a, b, c, d) in quads:
                        ua, va = uv_pts[a]
                        ub, vb = uv_pts[b]
                        uc, vc = uv_pts[c]
                        ud, vd = uv_pts[d]

                        quad_pts = [
                            srf.PointAt(clamp(ua, float(dom_u.T0), float(dom_u.T1)), clamp(va, float(dom_v.T0), float(dom_v.T1))),
                            srf.PointAt(clamp(ub, float(dom_u.T0), float(dom_u.T1)), clamp(vb, float(dom_v.T0), float(dom_v.T1))),
                            srf.PointAt(clamp(uc, float(dom_u.T0), float(dom_u.T1)), clamp(vc, float(dom_v.T0), float(dom_v.T1))),
                            srf.PointAt(clamp(ud, float(dom_u.T0), float(dom_u.T1)), clamp(vd, float(dom_v.T0), float(dom_v.T1))),
                        ]

                        base = mesh.Vertices.Count
                        for p in quad_pts:
                            mesh.Vertices.Add(p)
                        mesh.Faces.AddFace(base + 0, base + 1, base + 2, base + 3)

                        out_edges.append(rg.Line(quad_pts[0], quad_pts[1]))
                        out_edges.append(rg.Line(quad_pts[1], quad_pts[2]))
                        out_edges.append(rg.Line(quad_pts[2], quad_pts[3]))
                        out_edges.append(rg.Line(quad_pts[3], quad_pts[0]))

                    if mesh.Faces.Count == 0:
                        dbg = "ERROR: no quad faces created"
                    else:
                        mesh.Normals.ComputeNormals()
                        mesh.Compact()
                        out_mesh = mesh
                        dbg = "OK(quads): input:{} valid:{} bad:{} grid:{}x{} quads:{}".format(
                            len(pts), n, bad, u_count, v_count, mesh.Faces.Count
                        )
                else:
                    # Fallback if grid cannot be inferred: triangulate current points.
                    uv_norm = []
                    for (u, v) in uv_pts:
                        un = clamp01((u - float(dom_u.T0)) / du)
                        vn = clamp01((v - float(dom_v.T0)) / dv)
                        uv_norm.append((un, vn))

                    tris = delaunay_triangulate_2d(uv_norm)
                    if len(tris) == 0:
                        dbg = "ERROR: triangulation returned 0 triangles"
                    else:
                        mesh = rg.Mesh()
                        for p in valid_pts:
                            mesh.Vertices.Add(p)

                        for (a, b, c) in tris:
                            mesh.Faces.AddFace(int(a), int(b), int(c))

                        mesh.Normals.ComputeNormals()
                        mesh.Compact()
                        out_mesh = mesh

                        edge_set = set()
                        for f in mesh.Faces:
                            if not f.IsTriangle:
                                continue
                            A, B, C = f.A, f.B, f.C
                            for i, j in ((A, B), (B, C), (C, A)):
                                if i > j:
                                    i, j = j, i
                                edge_set.add((i, j))

                        for i, j in edge_set:
                            out_edges.append(rg.Line(mesh.Vertices[i], mesh.Vertices[j]))

                        dbg = "OK(tris): input:{} valid:{} bad:{} tris:{}".format(
                            len(pts), n, bad, mesh.Faces.Count
                        )

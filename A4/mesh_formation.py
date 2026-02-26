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
# Outputs:
# - out_mesh  : dynamic triangle mesh (UV Delaunay rebuilt each solve)
# - out_edges : mesh boundary lines
# - dbg       : debug string
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _is_point_like(x):
    if x is None:
        return False
    if isinstance(x, rg.Point3d):
        return True
    if hasattr(x, "position"):
        return True
    if hasattr(x, "Location"):
        return True
    if hasattr(x, "X") and hasattr(x, "Y") and hasattr(x, "Z"):
        return True
    return False


def _flatten_any(obj, out):
    if obj is None:
        return
    if _is_point_like(obj):
        out.append(obj)
        return
    if isinstance(obj, (str, bytes)):
        out.append(obj)
        return
    try:
        items = list(obj)
    except:
        out.append(obj)
        return
    if len(items) == 0:
        return
    for it in items:
        _flatten_any(it, out)


def as_list(x):
    """
    Deep-flatten common GH wrappers/data-tree-like nesting into a point-candidate list.
    """
    out = []
    _flatten_any(x, out)
    return out


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


def collect_mesh_edges(mesh):
    edge_set = set()
    for f in mesh.Faces:
        if f.IsTriangle:
            pairs = ((f.A, f.B), (f.B, f.C), (f.C, f.A))
        else:
            pairs = ((f.A, f.B), (f.B, f.C), (f.C, f.D), (f.D, f.A))
        for i, j in pairs:
            if i > j:
                i, j = j, i
            edge_set.add((i, j))
    return edge_set


def orient_triangle_faces_up(mesh):
    """
    Enforce upward (+Z) winding for triangle faces.
    """
    verts = mesh.Vertices
    for fi in range(mesh.Faces.Count):
        f = mesh.Faces[fi]
        if not f.IsTriangle:
            continue
        a = int(f.A)
        b = int(f.B)
        c = int(f.C)
        pa = rg.Point3d(verts[a].X, verts[a].Y, verts[a].Z)
        pb = rg.Point3d(verts[b].X, verts[b].Y, verts[b].Z)
        pc = rg.Point3d(verts[c].X, verts[c].Y, verts[c].Z)
        n = rg.Vector3d.CrossProduct(rg.Vector3d(pb - pa), rg.Vector3d(pc - pa))
        if n.Z < 0.0:
            mesh.Faces.SetFace(fi, a, c, b)


# -----------------------
# Delaunay triangulation (UV)
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
                # Option 1: dynamic topology. Rebuild Delaunay connectivity every solve.
                uv_norm = []
                for (u, v) in uv_pts:
                    un = clamp01((u - float(dom_u.T0)) / du)
                    vn = clamp01((v - float(dom_v.T0)) / dv)
                    uv_norm.append((un, vn))

                tris = delaunay_triangulate_2d(uv_norm)
                if len(tris) == 0:
                    dbg = "ERROR: dynamic triangulation returned 0 triangles"
                else:
                    mesh = rg.Mesh()
                    for (u, v) in uv_pts:
                        u_clamp = clamp(u, float(dom_u.T0), float(dom_u.T1))
                        v_clamp = clamp(v, float(dom_v.T0), float(dom_v.T1))
                        mesh.Vertices.Add(srf.PointAt(u_clamp, v_clamp))

                    for (a, b, c) in tris:
                        mesh.Faces.AddFace(int(a), int(b), int(c))

                    orient_triangle_faces_up(mesh)
                    mesh.Normals.ComputeNormals()
                    mesh.Compact()
                    out_mesh = mesh

                    edge_set = collect_mesh_edges(mesh)
                    for i, j in edge_set:
                        out_edges.append(rg.Line(mesh.Vertices[i], mesh.Vertices[j]))

                    dbg = "OK(dynamic_tris_up): input:{} valid:{} bad:{} tris:{} edges:{} topology:rebuilt".format(
                        len(pts), n, bad, mesh.Faces.Count, len(edge_set)
                    )

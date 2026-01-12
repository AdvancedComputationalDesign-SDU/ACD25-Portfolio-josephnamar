import Rhino.Geometry as rg
import rhinoscriptsyntax as rs

# -----------------------
# Helpers: unwrap/coerce surface
# -----------------------
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

def as_list(x):
    if x is None:
        return []
    try:
        return list(x)
    except:
        return [x]

def clamp01(t):
    return max(0.0, min(1.0, t))

# -----------------------
# 2D Delaunay triangulation (Bowyer–Watson)
# -----------------------
def orient2d(ax, ay, bx, by, cx, cy):
    return (bx-ax)*(cy-ay) - (by-ay)*(cx-ax)

def circumcircle_contains(ax, ay, bx, by, cx, cy, px, py):
    # expects triangle abc in CCW order
    ax -= px; ay -= py
    bx -= px; by -= py
    cx -= px; cy -= py

    a2 = ax*ax + ay*ay
    b2 = bx*bx + by*by
    c2 = cx*cx + cy*cy

    det = (ax * (by*c2 - b2*cy) -
           ay * (bx*c2 - b2*cx) +
           a2 * (bx*cy - by*cx))
    return det > 1e-12

def delaunay_triangulate_2d(pts):
    n = len(pts)
    if n < 3:
        return []

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    dx = maxx - minx
    dy = maxy - miny
    dmax = max(dx, dy)
    if dmax == 0.0:
        return []

    mx = 0.5 * (minx + maxx)
    my = 0.5 * (miny + maxy)

    # super triangle
    p0 = (mx - 20*dmax, my - dmax)
    p1 = (mx,           my + 20*dmax)
    p2 = (mx + 20*dmax, my - dmax)

    pts_ext = pts + [p0, p1, p2]
    s0, s1, s2 = n, n+1, n+2
    tris = [(s0, s1, s2)]

    for i in range(n):
        px, py = pts_ext[i]

        bad = []
        for t in tris:
            ia, ib, ic = t
            ax, ay = pts_ext[ia]
            bx, by = pts_ext[ib]
            cx, cy = pts_ext[ic]

            # For testing only: ensure CCW orientation by swapping B and C coordinates,
            # but keep the ORIGINAL triangle tuple t for removal.
            if orient2d(ax, ay, bx, by, cx, cy) < 0.0:
                bx, by, cx, cy = cx, cy, bx, by

            if circumcircle_contains(ax, ay, bx, by, cx, cy, px, py):
                bad.append(t)  # IMPORTANT: append original tuple

        # boundary edges of hole
        edge_count = {}
        def add_edge(a, b):
            if a > b:
                a, b = b, a
            edge_count[(a, b)] = edge_count.get((a, b), 0) + 1

        for (ia, ib, ic) in bad:
            add_edge(ia, ib)
            add_edge(ib, ic)
            add_edge(ic, ia)

        # remove bad triangles
        if bad:
            bad_set = set(bad)
            tris = [t for t in tris if t not in bad_set]

        boundary = [e for e, c in edge_count.items() if c == 1]

        # re-triangulate hole
        for (a, b) in boundary:
            tris.append((a, b, i))

    # remove triangles that reference super triangle vertices
    out = []
    for (a, b, c) in tris:
        if a >= n or b >= n or c >= n:
            continue
        if a == b or b == c or c == a:
            continue
        out.append((a, b, c))

    return out

# -----------------------
# Main
# -----------------------
out_mesh = None
out_edges = []
dbg = ""

if not run:
    dbg = "run is False"
else:
    srf = coerce_face(base_surface)
    pts = as_list(points)

    if srf is None:
        dbg = "ERROR: base_surface is not a Surface/BrepFace (or could not be coerced)"
    elif len(pts) < 3:
        dbg = "ERROR: need at least 3 points"
    else:
        dom_u = srf.Domain(0)
        dom_v = srf.Domain(1)
        du = float(dom_u.T1 - dom_u.T0)
        dv = float(dom_v.T1 - dom_v.T0)

        if du == 0.0 or dv == 0.0:
            dbg = "ERROR: surface domain is degenerate"
        else:
            uv_srf = []
            uv_norm = []
            bad = 0

            # project points to UV once
            for p in pts:
                p3 = rg.Point3d(p)
                ok, u, v = srf.ClosestPoint(p3)
                if not ok:
                    bad += 1
                    continue

                uv_srf.append((u, v))
                un = clamp01((u - dom_u.T0) / du)
                vn = clamp01((v - dom_v.T0) / dv)
                uv_norm.append((un, vn))

            n = len(uv_norm)
            if n < 3:
                dbg = "ERROR: <3 valid projected points (bad={})".format(bad)
            else:
                # triangulate in normalized UV
                tris = delaunay_triangulate_2d(uv_norm)

                if len(tris) == 0:
                    dbg = "ERROR: triangulation returned 0 triangles"
                else:
                    mesh = rg.Mesh()

                    # vertices on the original surface from stored UVs
                    for (u, v) in uv_srf:
                        mesh.Vertices.Add(srf.PointAt(u, v))

                    # faces
                    for (a, b, c) in tris:
                        mesh.Faces.AddFace(int(a), int(b), int(c))

                    if mesh.Faces.Count == 0:
                        dbg = "ERROR: no faces created"
                    else:
                        mesh.Normals.ComputeNormals()
                        mesh.Compact()
                        out_mesh = mesh

                        # unique edges for visualization
                        edge_set = set()
                        for f in mesh.Faces:
                            if not f.IsTriangle:
                                continue
                            A, B, C = f.A, f.B, f.C
                            for i, j in [(A, B), (B, C), (C, A)]:
                                if i > j:
                                    i, j = j, i
                                edge_set.add((i, j))

                        for i, j in edge_set:
                            out_edges.append(rg.Line(mesh.Vertices[i], mesh.Vertices[j]))

                        dbg = "OK: input:{} valid:{} bad:{} verts:{} tris:{} edges:{}".format(
                            len(pts), n, bad, mesh.Vertices.Count, mesh.Faces.Count, len(out_edges)
                        )

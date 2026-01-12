#r: numpy
import Rhino.Geometry as rg
import rhinoscriptsyntax as rs
import Rhino
import numpy as np
import random
import math
import System

# ------------------------------------------------------------
# Unwrap/coerce base_surface to RhinoCommon surface/face
# ------------------------------------------------------------
srf = getattr(base_surface, "Geometry", base_surface)

if srf is None:
    out_surface = None
    out_points = []
    srf_id = None
else:
    # If Brep, take first face
    if isinstance(srf, rg.Brep):
        if srf.Faces.Count == 0:
            out_surface = None
            out_points = []
            srf_id = None
        else:
            srf = srf.Faces[0]

    if not isinstance(srf, (rg.Surface, rg.BrepFace)):
        out_surface = None
        out_points = []
        srf_id = None
    else:
        # ------------------------------------------------------------
        # Seed
        # ------------------------------------------------------------
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        divU = int(divU)
        divV = int(divV)

        # Need at least 4x4 points for degree-3 surfaces
        uCount = max(4, divU + 1)
        vCount = max(4, divV + 1)

        # Clamp degrees so they never violate the function contract
        deg_u = min(3, uCount - 1)
        deg_v = min(3, vCount - 1)

        # ------------------------------------------------------------
        # Normalized UV grid
        # ------------------------------------------------------------
        Uu, Vv = np.meshgrid(
            np.linspace(0.0, 1.0, uCount),
            np.linspace(0.0, 1.0, vCount),
            indexing="xy"
        )

        # ------------------------------------------------------------
        # Heightmap (wave + bump)
        # ------------------------------------------------------------
        wave = np.sin(2.0 * math.pi * float(frequency) * (Uu + Vv) + float(phase))
        cx, cy = 0.5, 0.5
        dist = np.sqrt((Uu - cx) ** 2 + (Vv - cy) ** 2)
        bump = np.exp(-5.0 * dist ** 2)
        H = float(amplitude) * (0.6 * wave + 0.4 * bump)

        # ------------------------------------------------------------
        # Map normalized UV to surface domain, sample points + normals
        # ------------------------------------------------------------
        dom_u = srf.Domain(0)
        dom_v = srf.Domain(1)

        out_points = []   # Point3d list for GH visibility/debug
        pts_for_rs = []   # tuple list for AddSrfPtGrid

        for v_i in range(vCount):
            for u_i in range(uCount):
                u = dom_u.T0 + float(Uu[v_i, u_i]) * (dom_u.T1 - dom_u.T0)
                v = dom_v.T0 + float(Vv[v_i, u_i]) * (dom_v.T1 - dom_v.T0)

                p = srf.PointAt(u, v)
                n = srf.NormalAt(u, v)
                if n.IsTiny():
                    n = rg.Vector3d(0, 0, 1)
                else:
                    n.Unitize()

                d = float(H[v_i, u_i])
                pp = rg.Point3d(
                    p.X + n.X * d,
                    p.Y + n.Y * d,
                    p.Z + n.Z * d + float(lift)
                )

                out_points.append(pp)
                pts_for_rs.append((pp.X, pp.Y, pp.Z))

        # ------------------------------------------------------------
        # Create surface using RhinoScriptSyntax (returns guid on success)
        # ------------------------------------------------------------
        srf_id = rs.AddSrfPtGrid(
            (uCount, vCount),
            pts_for_rs,
            degree=(deg_u, deg_v),
            closed=(False, False)
        )

        # ------------------------------------------------------------
        # Convert guid -> real geometry for Grasshopper preview
        # RhinoDoc.ActiveDoc.Objects.FindId(guid) returns the RhinoObject. :contentReference[oaicite:4]{index=4}
        # ------------------------------------------------------------
        out_surface = None
        if srf_id:
            # Ensure we have a System.Guid
            if isinstance(srf_id, str):
                gid = System.Guid(srf_id)
            else:
                gid = srf_id

            rh_obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(gid)
            if rh_obj:
                # DuplicateGeometry gives GH a safe copy
                out_surface = rh_obj.Geometry.Duplicate()

import rhinoscriptsyntax as rs
import random
import numpy as np
import Rhino.Geometry as rg

# ---------------------------------------------------------------------------
# INPUT CONTRACT (Grasshopper)
# ---------------------------------------------------------------------------
# Inputs:
# - reset        : bool. Rebuilds agents when True (edge/hold behavior is handled upstream).
# - base_surface : Surface/BrepFace/Brep. If Brep, first face is used.
# - seed         : int (optional). Random/NumPy seed for repeatable initialization noise.
# - max_speed    : float. Base step size for each agent.
# - seed_points  : list[Point3d]. Initial points projected to the surface as agent starts.
#
# Outputs:
# - agents       : list[Agent] for downstream simulation.
# Notes:
# - Debug values are still stored on the component instance as:
#   self.dbg and self.seed_preview
# - If seed_points is empty, a fallback UV grid is generated from:
#   fallback_div_u, fallback_div_v (optional globals; default 8, 8).
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------
def seed_everything(seed):
    if seed is None: return
    try: s = int(seed)
    except: return
    random.seed(s)
    np.random.seed(s)

def coerce_surface_face(base_surface):
    srf_geo = getattr(base_surface, "Geometry", base_surface)
    try:
        import System
        if isinstance(srf_geo, System.Guid):
            srf_geo = rs.coercesurface(srf_geo)
    except:
        pass
    if isinstance(srf_geo, rg.Brep) and srf_geo.Faces.Count > 0:
        srf_geo = srf_geo.Faces[0]
    return srf_geo

def iter_any(obj):
    if obj is None:
        return []
    try:
        return [x for x in obj]
    except:
        return [obj]

def to_point3d(pt):
    p = getattr(pt, "Location", pt)
    try:
        c = rs.coerce3dpoint(p)
        return rg.Point3d(c[0], c[1], c[2])
    except:
        pass
    try:
        return rg.Point3d(p.X, p.Y, p.Z)
    except:
        return None

def key3(p, prec=6):
    return (round(p.X, prec), round(p.Y, prec), round(p.Z, prec))

def key2(u, v, prec=6):
    return (round(u, prec), round(v, prec))

def as_int(value, default, min_value=None):
    try:
        out = int(value)
    except:
        out = int(default)
    if min_value is not None and out < min_value:
        out = int(min_value)
    return out

def clamp_param(t, dom):
    if t < dom.T0: return dom.T0
    if t > dom.T1: return dom.T1
    return t

def project_to_tangent(v, n):
    # v_tan = v - n*(v·n)
    return v - n * rg.Vector3d.Multiply(v, n)

# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------
class Agent:
    def __init__(self, surface, uv, max_speed):
        self.surface = surface
        self.uv = rg.Point2d(uv.X, uv.Y)
        self.uv0 = rg.Point2d(uv.X, uv.Y)

        self.position = rg.Point3d(surface.PointAt(self.uv.X, self.uv.Y))
        self.velocity = rg.Vector3d(0, 0, 0)

        self.base_speed = float(max_speed)
        self.max_speed = float(max_speed)

        # behavior parameters (tune)
        self.base_spacing = 1.0
        self.curv_gain = 0.25
        self.slope_gain = 1.2
        self.sep_gain = 1.0
        self.home_gain = 0.1
        self.noise_gain = 0.01

        # modulation strengths (tune)
        self.curv_speed_k = 3.0
        self.slope_speed_k = 2.0
        self.slope_spacing_k = 0.8
        self.curv_follow_k = 1.5

        # numerics
        self.noise = 0.003
        self.eps_frac = 0.01

        # sensed values
        self.nearest_dist = None
        self.curv_dir = None
        self.curv_mag = 0.0
        self.normal = rg.Vector3d(0, 0, 1)
        self.slope_mag = 0.0
        self.slope_seek = rg.Vector3d(0, 0, 0)

    def sense(self, agents):
        # nearest neighbor distance only (for adaptive spacing)
        self.nearest_dist = None
        for other in agents:
            if other is self:
                continue
            d = self.position.DistanceTo(other.position)
            if self.nearest_dist is None or d < self.nearest_dist:
                self.nearest_dist = d

        # surface signals
        self.curv_dir = None
        self.curv_mag = 0.0
        self.slope_mag = 0.0
        self.slope_seek = rg.Vector3d(0, 0, 0)

        try:
            # normal
            n = self.surface.NormalAt(self.uv.X, self.uv.Y)
            if not n.IsZero:
                n.Unitize()
            self.normal = n

            # slope magnitude relative to world Z
            z = rg.Vector3d(0, 0, 1)
            dz = abs(rg.Vector3d.Multiply(n, z))  # |n·Z|
            self.slope_mag = 1.0 - max(0.0, min(1.0, dz))

            # curvature
            sc = self.surface.CurvatureAt(self.uv.X, self.uv.Y)
            if sc is not None:
                k0 = abs(sc.Kappa(0)); k1 = abs(sc.Kappa(1))
                d0 = sc.Direction(0); d1 = sc.Direction(1)

                # choose minimum curvature direction
                if k0 <= k1:
                    self.curv_dir = d0
                    self.curv_mag = k0
                else:
                    self.curv_dir = d1
                    self.curv_mag = k1

                if self.curv_dir is not None and self.curv_dir.Length > 1e-9:
                    self.curv_dir.Unitize()
                else:
                    self.curv_dir = None

            # direction toward higher slope magnitude (finite-difference in UV)
            du = self.surface.Domain(0)
            dv = self.surface.Domain(1)
            eps_u = self.eps_frac * (du.T1 - du.T0)
            eps_v = self.eps_frac * (dv.T1 - dv.T0)

            u0 = self.uv.X
            v0 = self.uv.Y
            p = self.position

            u_p = clamp_param(u0 + eps_u, du)
            u_m = clamp_param(u0 - eps_u, du)
            v_p = clamp_param(v0 + eps_v, dv)
            v_m = clamp_param(v0 - eps_v, dv)

            def slope_mag_at(uq, vq):
                n_q = self.surface.NormalAt(uq, vq)
                if n_q.IsZero:
                    return 0.0
                n_q.Unitize()
                dz_q = abs(rg.Vector3d.Multiply(n_q, z))
                return 1.0 - max(0.0, min(1.0, dz_q))

            m_u_p = slope_mag_at(u_p, v0)
            m_u_m = slope_mag_at(u_m, v0)
            m_v_p = slope_mag_at(u0, v_p)
            m_v_m = slope_mag_at(u0, v_m)

            # Gradient of slope magnitude in UV: move in +grad direction
            grad_u = m_u_p - m_u_m
            grad_v = m_v_p - m_v_m

            p_u = self.surface.PointAt(u_p, v0)
            p_v = self.surface.PointAt(u0, v_p)
            tu = rg.Vector3d(p_u - p)
            tv = rg.Vector3d(p_v - p)

            slope_seek = (tu * grad_u) + (tv * grad_v)
            slope_seek = project_to_tangent(slope_seek, n)
            if slope_seek.Length > 1e-9:
                slope_seek.Unitize()
                self.slope_seek = slope_seek
            else:
                self.slope_seek = rg.Vector3d(0, 0, 0)

        except:
            self.normal = rg.Vector3d(0, 0, 1)
            self.curv_dir = None
            self.curv_mag = 0.0
            self.slope_mag = 0.0
            self.slope_seek = rg.Vector3d(0, 0, 0)

    def decide(self, agents):
        # Modulate parameters by curvature + slope
        k = max(0.0, float(self.curv_mag))
        s = max(0.0, min(1.0, float(self.slope_mag)))

        # speed slows on high curvature and steep slope
        speed = self.base_speed / (1.0 + self.curv_speed_k * k + self.slope_speed_k * s)
        speed = max(0.001, min(self.base_speed, speed))

        # separation radius increases on steep slope (visible effect)
        R = self.base_spacing * (1.0 + self.slope_spacing_k * s)
        R = max(1e-6, R)

        # curvature-follow weight increases with curvature
        w_curv = self.curv_gain * (1.0 + self.curv_follow_k * k)
        w_slope = self.slope_gain
        w_sep = self.sep_gain
        w_home = self.home_gain
        w_noise = self.noise_gain

        # Separation force (sum over neighbors within R)
        sep = rg.Vector3d(0, 0, 0)
        for other in agents:
            if other is self:
                continue
            d = self.position.DistanceTo(other.position)
            if d <= 1e-9 or d > R:
                continue
            v = rg.Vector3d(self.position - other.position)
            if v.Length > 1e-9:
                v.Unitize()
            w = (R - d) / R
            sep += v * w

        if sep.Length > 1e-9:
            sep.Unitize()

        # Curvature flow direction (already tangent-ish, but project anyway)
        curv = rg.Vector3d(0, 0, 0)
        if self.curv_dir is not None:
            curv = rg.Vector3d(self.curv_dir)
            curv = project_to_tangent(curv, self.normal)
            if curv.Length > 1e-9:
                curv.Unitize()
            else:
                curv = rg.Vector3d(0, 0, 0)

        # Slope-seeking drift (toward steeper regions)
        slope = rg.Vector3d(self.slope_seek)
        if slope.Length > 1e-9:
            slope.Unitize()

        # Home spring (to original uv point on surface)
        home_pt = self.surface.PointAt(self.uv0.X, self.uv0.Y)
        home = rg.Vector3d(home_pt - self.position)
        home = project_to_tangent(home, self.normal)
        if home.Length > 1e-9:
            home.Unitize()
        else:
            home = rg.Vector3d(0, 0, 0)

        # Noise (3D, then tangent)
        noise = rg.Vector3d(
            random.uniform(-1.0, 1.0),
            random.uniform(-1.0, 1.0),
            random.uniform(-1.0, 1.0)
        )
        noise = project_to_tangent(noise, self.normal)
        if noise.Length > 1e-9:
            noise.Unitize()
        else:
            noise = rg.Vector3d(0, 0, 0)

        # Combine
        move = (sep * w_sep) + (curv * w_curv) + (slope * w_slope) + (home * w_home) + (noise * w_noise)

        # Tangent projection safety
        move = project_to_tangent(move, self.normal)

        if move.Length > 1e-9:
            move.Unitize()
        else:
            move = rg.Vector3d(0, 0, 0)

        # Store per-step step length
        self.step_len = speed
        self.move_dir = move
        self.rep_radius = R

    def move(self):
        prev = rg.Point3d(self.position)

        if not hasattr(self, "move_dir") or self.move_dir.IsZero:
            self.velocity = rg.Vector3d(0, 0, 0)
            return

        proposed = self.position + self.move_dir * self.step_len

        ok, u2, v2 = self.surface.ClosestPoint(proposed)
        if ok:
            du = self.surface.Domain(0)
            dv = self.surface.Domain(1)
            u2 = clamp_param(u2, du)
            v2 = clamp_param(v2, dv)
            self.uv = rg.Point2d(u2, v2)
            self.position = rg.Point3d(self.surface.PointAt(u2, v2))

        self.velocity = rg.Vector3d(self.position - prev)

    def update(self, agents):
        self.sense(agents)
        self.decide(agents)
        self.move()

# ---------------------------------------------------------------------------
# Agent builder from seed points
# ---------------------------------------------------------------------------
def build_agents_from_seed(surface, seed_points, max_speed):
    pts_raw = iter_any(seed_points)
    pts3 = []
    for pt in pts_raw:
        p3 = to_point3d(pt)
        if p3 is not None:
            pts3.append(p3)

    # Fallback: if no explicit seed points, seed a regular UV lattice.
    if (not pts3) and (surface is not None):
        div_u = as_int(globals().get("fallback_div_u", 8), 8, min_value=1)
        div_v = as_int(globals().get("fallback_div_v", 8), 8, min_value=1)
        du = surface.Domain(0)
        dv = surface.Domain(1)
        for i in range(div_u + 1):
            u = du.T0 + (float(i) / float(div_u)) * (du.T1 - du.T0)
            for j in range(div_v + 1):
                v = dv.T0 + (float(j) / float(div_v)) * (dv.T1 - dv.T0)
                pts3.append(surface.PointAt(u, v))

    agents = []
    uvs = []
    poss = []

    for p3 in pts3:
        ok, u, v = surface.ClosestPoint(p3)
        if not ok:
            continue
        uv = rg.Point2d(u, v)
        a = Agent(surface, uv, max_speed)
        agents.append(a)
        uvs.append(key2(u, v))
        poss.append(key3(a.position))

    dbg = "seed_raw:{0} seed_coerced:{1} agents:{2} unique_uv:{3} unique_pos:{4} unique_seed:{5}".format(
        len(pts_raw), len(pts3), len(agents),
        len(set(uvs)), len(set(poss)), len(set([key3(p) for p in pts3]))
    )
    return agents, dbg, pts3

# ---------------------------------------------------------------------------
# Grasshopper script entry
# ---------------------------------------------------------------------------
class MyComponent(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self,
            reset,
            base_surface,
            seed,
            max_speed,
            seed_points: list[object]):
        seed_everything(seed)
        srf = coerce_surface_face(base_surface)

        if reset or not hasattr(self, "agents") or not hasattr(self, "_inited"):
            if srf is None:
                self.agents = []
                self.dbg = "ERROR: base_surface is None or could not be coerced"
                self.seed_preview = []
            else:
                self.agents, self.dbg, self.seed_preview = build_agents_from_seed(
                    srf, seed_points, max_speed
                )
            self._inited = True

        agents = getattr(self, "agents", [])
        dbg = getattr(self, "dbg", "")
        seed_preview = getattr(self, "seed_preview", [])

        # Return tuple arity to match current GH output-port count.
        out_count = 1
        try:
            out_count = int(self.Component.Params.Output.Count)
        except:
            out_count = 1

        if out_count <= 1:
            return (agents,)
        if out_count == 2:
            return agents, dbg
        return agents, dbg, seed_preview

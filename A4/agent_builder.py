import random
import numpy as np
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg

# ---------------------------------------------------------------------------
# INPUT CONTRACT (Grasshopper)
# ---------------------------------------------------------------------------
# Inputs:
# - reset        : bool. Rebuilds agents when True.
# - base_surface : Surface/BrepFace/Brep (if Brep, first face is used)
# - seed         : int (optional). Seeds random + numpy for repeatability.
# - max_speed    : float. Base step length for each agent.
# - seed_points  : list[Point3d]. Required explicit seed points.
#
# Outputs:
# - agents       : list[Agent]
# - dbg          : debug string (if output port exists)
# - seed_preview : accepted seed points (if output port exists)
#
# Notes:
# - Builder no longer generates fallback seeds. Provide `seed_points`.
# - Main force defaults/controls live in `agent_simulator.py`.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# INTERNAL CONFIG
# ---------------------------------------------------------------------------
# Structural graph setup only. Force defaults live in agent_simulator.py.
STRUCT_CFG = {"grid_u": None, "grid_v": None, "use_diagonals": False}

# ---------------------------------------------------------------------------
# SCALAR HELPERS
# ---------------------------------------------------------------------------
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


def clamp01(x):
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def clamp_param(t, dom):
    return dom.T0 if t < dom.T0 else (dom.T1 if t > dom.T1 else t)

# ---------------------------------------------------------------------------
# INPUT COERCION
# ---------------------------------------------------------------------------
def seed_everything(seed):
    if seed is None:
        return
    try:
        s = int(seed)
    except:
        return
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


def project_to_tangent(v, n):
    return v - n * rg.Vector3d.Multiply(v, n)

# ---------------------------------------------------------------------------
# STRUCTURAL TOPOLOGY HELPERS
# ---------------------------------------------------------------------------
def infer_grid_dims(n, aspect_uv):
    n = as_int(n, 0, min_value=0)
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
    target = max(1e-9, float(aspect_uv))
    best, best_err = None, None
    for u_count, v_count in candidates:
        err = abs((float(u_count) / float(v_count)) - target)
        if (best_err is None) or (err < best_err):
            best, best_err = (u_count, v_count), err
    return best


def assign_structural_links(agents, surface):
    for a in agents:
        a.struct_neighbors, a.struct_rest_lengths = [], []
    if not agents:
        return {"enabled": False, "reason": "empty", "u_count": 0, "v_count": 0, "links": 0}

    n = len(agents)
    u_count = v_count = None
    if (STRUCT_CFG.get("grid_u") is not None) and (STRUCT_CFG.get("grid_v") is not None):
        u_try = as_int(STRUCT_CFG["grid_u"], 0, min_value=2)
        v_try = as_int(STRUCT_CFG["grid_v"], 0, min_value=2)
        if (u_try * v_try) == n:
            u_count, v_count = u_try, v_try
    if (u_count is None) or (v_count is None):
        du = abs(float(surface.Domain(0).T1 - surface.Domain(0).T0))
        dv = abs(float(surface.Domain(1).T1 - surface.Domain(1).T0))
        dims = infer_grid_dims(n, (du / dv) if dv > 1e-12 else 1.0)
        if dims is not None:
            u_count, v_count = dims
    if (u_count is None) or (v_count is None) or (u_count < 2) or (v_count < 2) or ((u_count * v_count) != n):
        return {"enabled": False, "reason": "dims_not_inferred", "u_count": 0, "v_count": 0, "links": 0}

    offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if bool(STRUCT_CFG.get("use_diagonals", False)):
        offsets += [(-1, -1), (-1, 1), (1, -1), (1, 1)]

    links = 0
    for i in range(u_count):
        for j in range(v_count):
            idx = (i * v_count) + j
            p = agents[idx].position
            neigh, rests = [], []
            for di, dj in offsets:
                ni, nj = i + di, j + dj
                if ni < 0 or ni >= u_count or nj < 0 or nj >= v_count:
                    continue
                nidx = (ni * v_count) + nj
                d = float(p.DistanceTo(agents[nidx].position))
                if d <= 1e-9:
                    continue
                neigh.append(nidx)
                rests.append(d)
            agents[idx].struct_neighbors = neigh
            agents[idx].struct_rest_lengths = rests
            links += len(neigh)

    return {"enabled": True, "reason": "ok", "u_count": int(u_count), "v_count": int(v_count), "links": int(links)}


class Agent:
    def __init__(self, surface, uv, max_speed):
        self.surface = surface
        self.uv = rg.Point2d(uv.X, uv.Y)
        self.uv0 = rg.Point2d(uv.X, uv.Y)
        self.position = rg.Point3d(surface.PointAt(self.uv.X, self.uv.Y))
        self.velocity = rg.Vector3d(0, 0, 0)
        self.struct_neighbors, self.struct_rest_lengths = [], []

        # Runtime-controlled from agent_simulator (sliders).
        self.base_speed = max(1e-6, float(max_speed))
        self.sep_gain = 0.0
        self.coh_gain = 0.0
        self.base_spacing = 1.0
        self.freedom = 0.0
        self.curv_gain = 0.0
        self.slope_gain = 0.0
        self.struct_spring_gain = 0.0
        self.struct_min_dist_gain = 0.0

        # Fixed internals (kept in builder).
        self.coh_radius_mult = 2.0
        self.momentum = 0.6
        self.curv_speed_k = 1.2
        self.slope_speed_k = 0.9
        self.slope_spacing_k = 0.8
        self.curv_follow_k = 1.5
        self.eps_frac = 0.01
        self.group_slope_gain = 0.55
        self.slope_peer_gain = 0.45
        self.slope_diff_min = 0.04
        self.curv_use_max = True
        self.curv_scale = 0.08
        self.curv_damp = 0.60
        self.slope_damp = 0.25
        self.hardcore_ratio = 0.35
        self.hardcore_boost = 2.0
        self.sep_vec_cap = 3.0
        self.struct_enable = True
        self.struct_min_dist_ratio = 0.70

        self.momentum = clamp01(float(self.momentum))
        self.curv_damp = clamp01(float(self.curv_damp))
        self.slope_damp = clamp01(float(self.slope_damp))
        self._refresh_freedom_gains()
        self.curv_dir = None
        self.curv_mag = 0.0
        self.normal = rg.Vector3d(0, 0, 1)
        self.slope_mag = 0.0
        self.slope_seek = rg.Vector3d(0, 0, 0)

    def _refresh_freedom_gains(self):
        self.home_gain = 0.08 * (1.0 - self.freedom)
        self.noise_gain = 0.002 + (0.012 * self.freedom)

    def apply_runtime_params(self, params):
        if not isinstance(params, dict) or not params:
            return
        if "max_speed" in params:
            self.base_speed = as_float(params["max_speed"], self.base_speed, min_value=1e-6)
        if "sep_gain" in params:
            self.sep_gain = as_float(params["sep_gain"], self.sep_gain, min_value=0.0)
        if "coh_gain" in params:
            self.coh_gain = as_float(params["coh_gain"], self.coh_gain, min_value=0.0)
        if "base_spacing" in params:
            self.base_spacing = as_float(params["base_spacing"], self.base_spacing, min_value=1e-6)
        if "freedom" in params:
            self.freedom = clamp01(as_float(params["freedom"], self.freedom))
        if "curv_gain" in params:
            self.curv_gain = as_float(params["curv_gain"], self.curv_gain, min_value=0.0)
        if "slope_gain" in params:
            self.slope_gain = as_float(params["slope_gain"], self.slope_gain, min_value=0.0)
        if "struct_spring_gain" in params:
            self.struct_spring_gain = as_float(params["struct_spring_gain"], self.struct_spring_gain, min_value=0.0)
        if "struct_min_dist_gain" in params:
            self.struct_min_dist_gain = as_float(params["struct_min_dist_gain"], self.struct_min_dist_gain, min_value=0.0)
        self._refresh_freedom_gains()

    def sense(self, _agents):
        self.curv_dir = None
        self.curv_mag = 0.0
        self.slope_mag = 0.0
        self.slope_seek = rg.Vector3d(0, 0, 0)
        try:
            n = self.surface.NormalAt(self.uv.X, self.uv.Y)
            if not n.IsZero:
                n.Unitize()
            self.normal = n
            z = rg.Vector3d(0, 0, 1)
            self.slope_mag = 1.0 - max(0.0, min(1.0, abs(rg.Vector3d.Multiply(n, z))))

            sc = self.surface.CurvatureAt(self.uv.X, self.uv.Y)
            if sc is not None:
                k0, k1 = abs(sc.Kappa(0)), abs(sc.Kappa(1))
                d0, d1 = sc.Direction(0), sc.Direction(1)
                self.curv_dir, self.curv_mag = ((d0, k0) if k0 >= k1 else (d1, k1)) if self.curv_use_max else ((d0, k0) if k0 <= k1 else (d1, k1))
                if self.curv_dir is not None and self.curv_dir.Length > 1e-9:
                    self.curv_dir.Unitize()
                else:
                    self.curv_dir = None

            du, dv = self.surface.Domain(0), self.surface.Domain(1)
            eps_u = self.eps_frac * (du.T1 - du.T0)
            eps_v = self.eps_frac * (dv.T1 - dv.T0)
            u0, v0, p = self.uv.X, self.uv.Y, self.position
            u_p, u_m = clamp_param(u0 + eps_u, du), clamp_param(u0 - eps_u, du)
            v_p, v_m = clamp_param(v0 + eps_v, dv), clamp_param(v0 - eps_v, dv)

            def slope_at(uq, vq):
                n_q = self.surface.NormalAt(uq, vq)
                if n_q.IsZero:
                    return 0.0
                n_q.Unitize()
                return 1.0 - max(0.0, min(1.0, abs(rg.Vector3d.Multiply(n_q, z))))

            grad_u = slope_at(u_p, v0) - slope_at(u_m, v0)
            grad_v = slope_at(u0, v_p) - slope_at(u0, v_m)
            tu = rg.Vector3d(self.surface.PointAt(u_p, v0) - p)
            tv = rg.Vector3d(self.surface.PointAt(u0, v_p) - p)
            slope_seek = project_to_tangent((tu * grad_u) + (tv * grad_v), n)
            if slope_seek.Length > 1e-9:
                slope_seek.Unitize()
                self.slope_seek = slope_seek
        except:
            self.normal = rg.Vector3d(0, 0, 1)
            self.curv_dir = None
            self.curv_mag = 0.0
            self.slope_mag = 0.0
            self.slope_seek = rg.Vector3d(0, 0, 0)

    def decide(self, agents):
        k = max(0.0, float(self.curv_mag))
        s = max(0.0, min(1.0, float(self.slope_mag)))
        curv_norm = k / (k + max(1e-9, self.curv_scale))
        speed_scale = (1.0 - clamp01(self.curv_damp * curv_norm)) * (1.0 - clamp01(self.slope_damp * s))
        speed_scale /= 1.0 + (0.35 * self.curv_speed_k * curv_norm) + (0.25 * self.slope_speed_k * s)
        speed_scale = max(0.10 + (0.40 * self.freedom), min(1.0, speed_scale))
        speed = self.base_speed * speed_scale

        R = max(1e-6, self.base_spacing * (1.0 + self.slope_spacing_k * s))
        R_coh = R * max(1.0, self.coh_radius_mult)
        hard_core = max(1e-9, self.hardcore_ratio * R)

        sep = rg.Vector3d(0, 0, 0)
        coh_sum = rg.Vector3d(0, 0, 0)
        coh_count = 0
        peer_slope_vec = rg.Vector3d(0, 0, 0)
        local_slope_sum, local_slope_count = s, 1

        for other in agents:
            if other is self:
                continue
            d = self.position.DistanceTo(other.position)
            if d <= 1e-9:
                continue

            if d <= R:
                away = rg.Vector3d(self.position - other.position)
                if away.Length > 1e-9:
                    away.Unitize()
                    falloff = max(0.0, (R - d) / R)
                    if d < hard_core:
                        falloff *= (1.0 + self.hardcore_boost * max(0.0, (hard_core - d) / hard_core))
                    sep += away * falloff

            if d <= R_coh:
                coh_sum += rg.Vector3d(other.position - self.position)
                coh_count += 1
                o_s = getattr(other, "slope_mag", None)
                if o_s is not None:
                    try:
                        o_s_val = max(0.0, min(1.0, float(o_s)))
                        local_slope_sum += o_s_val
                        local_slope_count += 1
                        if o_s_val > (s + self.slope_diff_min):
                            to_other = rg.Vector3d(other.position - self.position)
                            if to_other.Length > 1e-9:
                                to_other.Unitize()
                                w_sd = o_s_val - s
                                w_dist = max(0.0, (R_coh - d) / max(1e-9, R_coh))
                                peer_slope_vec += to_other * (w_sd * w_dist)
                    except:
                        pass

        sep = project_to_tangent(sep, self.normal)
        sep_len = sep.Length
        if sep_len > self.sep_vec_cap and sep_len > 1e-9:
            sep *= (self.sep_vec_cap / sep_len)

        coh = rg.Vector3d(0, 0, 0)
        if coh_count > 0:
            coh = project_to_tangent(rg.Vector3d(coh_sum) * (1.0 / float(coh_count)), self.normal)
            if coh.Length > 1e-9:
                coh.Unitize()
            else:
                coh = rg.Vector3d(0, 0, 0)

        peer_slope = project_to_tangent(peer_slope_vec, self.normal)
        if peer_slope.Length > 1e-9:
            peer_slope.Unitize()
        else:
            peer_slope = rg.Vector3d(0, 0, 0)

        struct_spring = rg.Vector3d(0, 0, 0)
        struct_min_push = rg.Vector3d(0, 0, 0)
        if self.struct_enable:
            n_count = min(len(self.struct_neighbors), len(self.struct_rest_lengths))
            min_ratio = max(0.05, float(self.struct_min_dist_ratio))
            for i in range(n_count):
                oi = int(self.struct_neighbors[i])
                if oi < 0 or oi >= len(agents):
                    continue
                rest = max(1e-6, float(self.struct_rest_lengths[i]))
                to_other = rg.Vector3d(agents[oi].position - self.position)
                d = float(to_other.Length)
                if d <= 1e-9:
                    continue
                to_other.Unitize()
                struct_spring += to_other * ((d - rest) / rest)
                min_d = min_ratio * rest
                if d < min_d:
                    struct_min_push -= to_other * ((min_d - d) / max(1e-9, min_d))
            struct_spring = project_to_tangent(struct_spring, self.normal)
            struct_min_push = project_to_tangent(struct_min_push, self.normal)

        mean_slope = local_slope_sum / float(max(1, local_slope_count))
        sep_group_scale = 1.0 + (self.group_slope_gain * mean_slope)
        coh_group_scale = max(0.35, 1.0 - (0.35 * self.group_slope_gain * mean_slope))

        curv = rg.Vector3d(0, 0, 0)
        if self.curv_dir is not None:
            curv = project_to_tangent(rg.Vector3d(self.curv_dir), self.normal)
            if curv.Length > 1e-9:
                curv.Unitize()
            else:
                curv = rg.Vector3d(0, 0, 0)

        slope = rg.Vector3d(self.slope_seek)
        if slope.Length > 1e-9:
            slope.Unitize()

        home = project_to_tangent(rg.Vector3d(self.surface.PointAt(self.uv0.X, self.uv0.Y) - self.position), self.normal)
        if home.Length > 1e-9:
            home.Unitize()
        else:
            home = rg.Vector3d(0, 0, 0)

        noise = rg.Vector3d(random.uniform(-1.0, 1.0), random.uniform(-1.0, 1.0), random.uniform(-1.0, 1.0))
        noise = project_to_tangent(noise, self.normal)
        if noise.Length > 1e-9:
            noise.Unitize()
        else:
            noise = rg.Vector3d(0, 0, 0)

        move = (
            (sep * (self.sep_gain * sep_group_scale)) + (coh * (self.coh_gain * coh_group_scale)) +
            (peer_slope * self.slope_peer_gain) + (struct_spring * self.struct_spring_gain) +
            (struct_min_push * self.struct_min_dist_gain) +
            (curv * (self.curv_gain * (1.0 + self.curv_follow_k * k))) +
            (slope * self.slope_gain) + (home * self.home_gain) + (noise * self.noise_gain)
        )
        move = project_to_tangent(move, self.normal)

        if self.velocity is not None and self.velocity.Length > 1e-9:
            vdir = project_to_tangent(rg.Vector3d(self.velocity), self.normal)
            if vdir.Length > 1e-9:
                vdir.Unitize()
                move = (move * (1.0 - self.momentum)) + (vdir * self.momentum)

        if move.Length > 1e-9:
            move.Unitize()
        else:
            move = rg.Vector3d(0, 0, 0)

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
            du, dv = self.surface.Domain(0), self.surface.Domain(1)
            u2, v2 = clamp_param(u2, du), clamp_param(v2, dv)
            self.uv = rg.Point2d(u2, v2)
            self.position = rg.Point3d(self.surface.PointAt(u2, v2))
        self.velocity = rg.Vector3d(self.position - prev)

    def update(self, agents, runtime_params=None):
        self.apply_runtime_params(runtime_params)
        self.sense(agents)
        self.decide(agents)
        self.move()


# ---------------------------------------------------------------------------
# AGENT BUILD
# ---------------------------------------------------------------------------
def build_agents_from_seed(surface, seed_points, max_speed):
    pts_raw = iter_any(seed_points)
    pts3 = [p for p in [to_point3d(pt) for pt in pts_raw] if p is not None]

    if not pts3:
        return [], "ERROR: seed_points is empty or invalid (no builder fallback)", []

    agents, uv_keys, pos_keys = [], [], []
    for p3 in pts3:
        ok, u, v = surface.ClosestPoint(p3)
        if not ok:
            continue
        a = Agent(surface, rg.Point2d(u, v), max_speed)
        agents.append(a)
        uv_keys.append((round(u, 6), round(v, 6)))
        pos_keys.append((round(a.position.X, 6), round(a.position.Y, 6), round(a.position.Z, 6)))

    struct_info = assign_structural_links(agents, surface)
    dbg = (
        "seed_raw:{0} seed_valid:{1} agents:{2} unique_uv:{3} unique_pos:{4} unique_seed:{5} "
        "struct:{6} dims:{7}x{8} links:{9}"
    ).format(
        len(pts_raw), len(pts3), len(agents), len(set(uv_keys)), len(set(pos_keys)),
        len(set([(round(p.X, 6), round(p.Y, 6), round(p.Z, 6)) for p in pts3])),
        "on" if bool(struct_info.get("enabled", False)) else "off:" + str(struct_info.get("reason", "na")),
        int(struct_info.get("u_count", 0)), int(struct_info.get("v_count", 0)), int(struct_info.get("links", 0)),
    )
    return agents, dbg, pts3


class MyComponent(Grasshopper.Kernel.GH_ScriptInstance):
    # -----------------------------------------------------------------------
    # GH SCRIPT ENTRY
    # -----------------------------------------------------------------------
    def RunScript(self, reset, base_surface, seed, max_speed, seed_points: list[object]):
        seed_everything(seed)
        srf = coerce_surface_face(base_surface)
        if reset or not hasattr(self, "agents") or not hasattr(self, "_inited"):
            if srf is None:
                self.agents, self.dbg, self.seed_preview = [], "ERROR: base_surface is None or could not be coerced", []
            else:
                self.agents, self.dbg, self.seed_preview = build_agents_from_seed(srf, seed_points, max_speed)
            self._inited = True

        agents = getattr(self, "agents", [])
        dbg = getattr(self, "dbg", "")
        seed_preview = getattr(self, "seed_preview", [])

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

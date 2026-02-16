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
# - If seed_points is empty, a fallback UV grid is generated internally.
# - Agent/seed tuning values are currently INTERNAL ONLY (constants below).
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# INTERNAL TUNING (edit here, no GH input required)
# ---------------------------------------------------------------------------
FALLBACK_DIV_U = 8
FALLBACK_DIV_V = 8

AGENT_FREEDOM = 0.75
AGENT_BASE_SPACING = 1.25
AGENT_CURV_GAIN = 0.45
AGENT_SLOPE_GAIN = 0.95
AGENT_SEP_GAIN = 1.85
AGENT_COH_GAIN = 0.72
AGENT_COH_RADIUS_MULT = 2.0
AGENT_MOMENTUM = 0.6
AGENT_CURV_SPEED_K = 1.2
AGENT_SLOPE_SPEED_K = 0.9
AGENT_SLOPE_SPACING_K = 0.8
AGENT_CURV_FOLLOW_K = 1.5
AGENT_EPS_FRAC = 0.01
# Neighborhood mean-slope modulation for group behavior:
# steeper local neighborhoods -> stronger separation and slightly weaker cohesion.
AGENT_GROUP_SLOPE_GAIN = 0.55
# Peer slope-follow rule:
# if neighbor slope is higher than self, self is gently attracted toward that neighbor.
AGENT_SLOPE_PEER_GAIN = 0.45
AGENT_SLOPE_DIFF_MIN = 0.04
# Reference-like stability controls.
AGENT_CURV_USE_MAX = True
AGENT_CURV_SCALE = 0.08
AGENT_CURV_DAMP = 0.60
AGENT_SLOPE_DAMP = 0.25
AGENT_HARDCORE_RATIO = 0.35
AGENT_HARDCORE_BOOST = 2.0
AGENT_SEP_VEC_CAP = 3.0
# Structural constraints (quad-preserving behavior).
STRUCT_ENABLE = True
STRUCT_GRID_U = None         # set int to force grid U count; None = infer
STRUCT_GRID_V = None         # set int to force grid V count; None = infer
STRUCT_USE_DIAGONALS = False # True adds diagonal structural springs
STRUCT_SPRING_GAIN = 0.65    # spring toward rest edge lengths
STRUCT_MIN_DIST_RATIO = 0.70 # minimum allowed fraction of structural rest length
STRUCT_MIN_DIST_GAIN = 1.45  # push strength when structural edges collapse

# Seed shaping. Set SEED_INIT_AGENT_COUNT to None to use all available seeds.
SEED_INIT_AGENT_COUNT = None
SEED_SLOPE_BIAS = 0.0
SEED_SLOPE_POWER = 2.0

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

def as_float(value, default, min_value=None):
    try:
        out = float(value)
    except:
        out = float(default)
    if min_value is not None and out < min_value:
        out = float(min_value)
    return out

def clamp01(x):
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x

def clamp_param(t, dom):
    if t < dom.T0: return dom.T0
    if t > dom.T1: return dom.T1
    return t

def project_to_tangent(v, n):
    # v_tan = v - n*(v·n)
    return v - n * rg.Vector3d.Multiply(v, n)


def slope_magnitude_from_normal(n):
    if n is None or n.IsZero:
        return 0.0
    nn = rg.Vector3d(n)
    nn.Unitize()
    z = rg.Vector3d(0, 0, 1)
    dz = abs(rg.Vector3d.Multiply(nn, z))
    return 1.0 - max(0.0, min(1.0, dz))


def select_seed_points(surface, pts3, target_count, slope_bias, slope_power, seed_val):
    """
    Select initial seed points, optionally biased toward high-slope regions.
    Returns selected points and a debug tuple: (candidate_count, selected_count).
    """
    if not pts3:
        return [], (0, 0)

    n = len(pts3)
    target = as_int(target_count, n, min_value=1)
    b = clamp01(as_float(slope_bias, 0.0))
    pwr = as_float(slope_power, 2.0, min_value=0.1)

    # Fast path: no bias and no resampling requested.
    if b <= 1e-12 and target == n:
        return list(pts3), (n, n)

    candidates = []
    weights = []

    for p3 in pts3:
        ok, u, v = surface.ClosestPoint(p3)
        if not ok:
            continue
        nrm = surface.NormalAt(u, v)
        slope_mag = slope_magnitude_from_normal(nrm)
        w = (1.0 - b) + (b * (slope_mag ** pwr))
        if w <= 1e-12:
            w = 1e-12
        candidates.append(p3)
        weights.append(w)

    m = len(candidates)
    if m == 0:
        return [], (0, 0)

    w = np.array(weights, dtype=float)
    w_sum = float(np.sum(w))
    if w_sum <= 1e-12:
        w[:] = 1.0 / float(m)
    else:
        w /= w_sum

    replace = bool(target > m)
    rng = np.random.RandomState(int(seed_val) if seed_val is not None else 0)
    try:
        idx = rng.choice(m, size=target, replace=replace, p=w)
    except:
        idx = rng.choice(m, size=target, replace=replace)

    selected = [candidates[int(i)] for i in idx]
    return selected, (m, len(selected))


def infer_grid_dims(n, aspect_uv):
    """
    Infer (u_count, v_count) from total point count using factor pairs.
    Chooses pair whose u/v ratio best matches surface UV aspect.
    """
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
    best = None
    best_err = None
    for u_count, v_count in candidates:
        ratio = float(u_count) / float(v_count)
        err = abs(ratio - target)
        if (best_err is None) or (err < best_err):
            best_err = err
            best = (u_count, v_count)
    return best


def assign_structural_links(agents, surface):
    """
    Build structural neighbor graph (grid edges) and rest edge lengths.
    Assumes current ordering corresponds to row-major UV grid:
      idx = i * v_count + j
    """
    for a in agents:
        a.struct_i = -1
        a.struct_j = -1
        a.struct_neighbors = []
        a.struct_rest_lengths = []

    if (not bool(STRUCT_ENABLE)) or (not agents):
        return {
            "enabled": False,
            "reason": "disabled_or_empty",
            "u_count": 0,
            "v_count": 0,
            "links": 0
        }

    n = len(agents)
    u_count = None
    v_count = None

    if (STRUCT_GRID_U is not None) and (STRUCT_GRID_V is not None):
        u_try = as_int(STRUCT_GRID_U, 0, min_value=2)
        v_try = as_int(STRUCT_GRID_V, 0, min_value=2)
        if (u_try * v_try) == n:
            u_count, v_count = u_try, v_try

    if (u_count is None) or (v_count is None):
        dom_u = surface.Domain(0)
        dom_v = surface.Domain(1)
        du = abs(float(dom_u.T1 - dom_u.T0))
        dv = abs(float(dom_v.T1 - dom_v.T0))
        aspect = (du / dv) if dv > 1e-12 else 1.0
        dims = infer_grid_dims(n, aspect)
        if dims is not None:
            u_count, v_count = dims

    if (u_count is None) or (v_count is None) or (u_count < 2) or (v_count < 2) or ((u_count * v_count) != n):
        return {
            "enabled": False,
            "reason": "dims_not_inferred",
            "u_count": 0,
            "v_count": 0,
            "links": 0
        }

    if bool(STRUCT_USE_DIAGONALS):
        offsets = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    else:
        offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    total_links = 0
    for i in range(u_count):
        for j in range(v_count):
            idx = (i * v_count) + j
            a = agents[idx]
            a.struct_i = i
            a.struct_j = j

            neighbors = []
            rest_lengths = []
            p = a.position

            for di, dj in offsets:
                ni = i + di
                nj = j + dj
                if ni < 0 or ni >= u_count or nj < 0 or nj >= v_count:
                    continue
                nidx = (ni * v_count) + nj
                q = agents[nidx].position
                d = float(p.DistanceTo(q))
                if d <= 1e-9:
                    continue
                neighbors.append(int(nidx))
                rest_lengths.append(d)

            a.struct_neighbors = neighbors
            a.struct_rest_lengths = rest_lengths
            total_links += len(neighbors)

    return {
        "enabled": True,
        "reason": "ok",
        "u_count": int(u_count),
        "v_count": int(v_count),
        "links": int(total_links)
    }

# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------
class Agent:
    def __init__(self, surface, uv, max_speed, idx=None):
        self.surface = surface
        self.uv = rg.Point2d(uv.X, uv.Y)
        self.uv0 = rg.Point2d(uv.X, uv.Y)
        self.idx = as_int(idx, -1) if idx is not None else -1
        self.struct_i = -1
        self.struct_j = -1
        self.struct_neighbors = []
        self.struct_rest_lengths = []

        self.position = rg.Point3d(surface.PointAt(self.uv.X, self.uv.Y))
        self.velocity = rg.Vector3d(0, 0, 0)

        self.base_speed = float(max_speed)
        self.max_speed = float(max_speed)

        freedom = clamp01(float(AGENT_FREEDOM))
        self.freedom = freedom

        # behavior parameters (tune)
        self.base_spacing = max(1e-6, float(AGENT_BASE_SPACING))
        self.curv_gain = max(0.0, float(AGENT_CURV_GAIN))
        self.slope_gain = max(0.0, float(AGENT_SLOPE_GAIN))
        self.sep_gain = max(0.0, float(AGENT_SEP_GAIN))
        self.coh_gain = max(0.0, float(AGENT_COH_GAIN))
        self.coh_radius_mult = max(1.0, float(AGENT_COH_RADIUS_MULT))
        self.momentum = clamp01(float(AGENT_MOMENTUM))

        # Higher freedom -> weaker home pull + more exploratory jitter.
        self.home_gain = 0.08 * (1.0 - freedom)
        self.noise_gain = 0.002 + (0.012 * freedom)

        # modulation strengths (tune)
        self.curv_speed_k = max(0.0, float(AGENT_CURV_SPEED_K))
        self.slope_speed_k = max(0.0, float(AGENT_SLOPE_SPEED_K))
        self.slope_spacing_k = max(0.0, float(AGENT_SLOPE_SPACING_K))
        self.curv_follow_k = max(0.0, float(AGENT_CURV_FOLLOW_K))

        # numerics
        self.noise = 0.003
        self.eps_frac = max(1e-6, float(AGENT_EPS_FRAC))

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

                # Choose dominant curvature direction (reference-style behavior).
                if bool(AGENT_CURV_USE_MAX):
                    if k0 >= k1:
                        self.curv_dir = d0
                        self.curv_mag = k0
                    else:
                        self.curv_dir = d1
                        self.curv_mag = k1
                else:
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
        # Surface-conditioned scalars.
        k = max(0.0, float(self.curv_mag))
        s = max(0.0, min(1.0, float(self.slope_mag)))

        # Reference-like speed damping: sharp slowdown on high curvature,
        # then a secondary slowdown on steep slope.
        curv_scale = max(1e-9, float(AGENT_CURV_SCALE))
        curv_norm = k / (k + curv_scale)
        speed_scale = (1.0 - clamp01(float(AGENT_CURV_DAMP) * curv_norm))
        speed_scale *= (1.0 - clamp01(float(AGENT_SLOPE_DAMP) * s))
        speed_scale /= (
            1.0 +
            (0.35 * self.curv_speed_k * curv_norm) +
            (0.25 * self.slope_speed_k * s)
        )
        min_ratio = 0.10 + (0.40 * self.freedom)
        speed_scale = max(min_ratio, min(1.0, speed_scale))
        speed = self.base_speed * speed_scale

        # Neighborhood radii.
        R = self.base_spacing * (1.0 + self.slope_spacing_k * s)
        R = max(1e-6, R)
        R_coh = R * max(1.0, float(self.coh_radius_mult))
        hard_core = max(1e-9, float(AGENT_HARDCORE_RATIO) * R)

        # Direction weights.
        w_curv = self.curv_gain * (1.0 + self.curv_follow_k * k)
        w_slope = self.slope_gain
        w_sep = self.sep_gain
        w_coh = self.coh_gain
        w_peer = max(0.0, float(AGENT_SLOPE_PEER_GAIN))
        w_struct_spring = max(0.0, float(STRUCT_SPRING_GAIN))
        w_struct_min = max(0.0, float(STRUCT_MIN_DIST_GAIN))
        w_home = self.home_gain
        w_noise = self.noise_gain

        # Neighbor accumulation.
        sep = rg.Vector3d(0, 0, 0)
        coh_sum = rg.Vector3d(0, 0, 0)
        coh_count = 0
        peer_slope_vec = rg.Vector3d(0, 0, 0)
        local_slope_sum = s
        local_slope_count = 1
        slope_diff_min = max(0.0, float(AGENT_SLOPE_DIFF_MIN))

        for other in agents:
            if other is self:
                continue
            d = self.position.DistanceTo(other.position)
            if d <= 1e-9:
                continue

            # Distance-weighted repulsion, with a hard-core push to avoid overlap.
            if d <= R:
                away = rg.Vector3d(self.position - other.position)
                if away.Length > 1e-9:
                    away.Unitize()
                    falloff = max(0.0, (R - d) / R)
                    if d < hard_core:
                        hc = max(0.0, (hard_core - d) / hard_core)
                        falloff *= (1.0 + (float(AGENT_HARDCORE_BOOST) * hc))
                    sep += away * falloff

            if d <= R_coh:
                coh_sum += rg.Vector3d(other.position - self.position)
                coh_count += 1

                # Neighborhood slope context + low-slope follower behavior.
                o_s = getattr(other, "slope_mag", None)
                if o_s is not None:
                    try:
                        o_s_val = max(0.0, min(1.0, float(o_s)))
                        local_slope_sum += o_s_val
                        local_slope_count += 1

                        if o_s_val > (s + slope_diff_min):
                            to_other = rg.Vector3d(other.position - self.position)
                            if to_other.Length > 1e-9:
                                to_other.Unitize()
                                w_sd = o_s_val - s
                                w_dist = max(0.0, (R_coh - d) / max(1e-9, R_coh))
                                peer_slope_vec += to_other * (w_sd * w_dist)
                    except:
                        pass

        # Keep repulsion magnitude (for crowd pressure), only cap extreme values.
        sep = project_to_tangent(sep, self.normal)
        sep_len = sep.Length
        if sep_len > 1e-9:
            sep_cap = max(1e-6, float(AGENT_SEP_VEC_CAP))
            if sep_len > sep_cap:
                sep *= (sep_cap / sep_len)
        else:
            sep = rg.Vector3d(0, 0, 0)

        coh = rg.Vector3d(0, 0, 0)
        if coh_count > 0:
            coh = rg.Vector3d(coh_sum) * (1.0 / float(coh_count))
            coh = project_to_tangent(coh, self.normal)
            if coh.Length > 1e-9:
                coh.Unitize()
            else:
                coh = rg.Vector3d(0, 0, 0)

        peer_slope = project_to_tangent(peer_slope_vec, self.normal)
        if peer_slope.Length > 1e-9:
            peer_slope.Unitize()
        else:
            peer_slope = rg.Vector3d(0, 0, 0)

        # Structural constraints (fixed neighbors from initial grid):
        # 1) spring toward rest edge lengths
        # 2) hard minimum edge length to resist local inversion/swapping
        struct_spring = rg.Vector3d(0, 0, 0)
        struct_min_push = rg.Vector3d(0, 0, 0)
        min_ratio = max(0.05, float(STRUCT_MIN_DIST_RATIO))
        if bool(STRUCT_ENABLE):
            n_ids = getattr(self, "struct_neighbors", [])
            n_rest = getattr(self, "struct_rest_lengths", [])
            n_count = min(len(n_ids), len(n_rest))
            for k_idx in range(n_count):
                oi = int(n_ids[k_idx])
                if oi < 0 or oi >= len(agents):
                    continue
                other = agents[oi]
                rest = max(1e-6, float(n_rest[k_idx]))
                to_other = rg.Vector3d(other.position - self.position)
                d = float(to_other.Length)
                if d <= 1e-9:
                    continue
                to_other.Unitize()

                # Hooke-like spring in direction of neighbor.
                stretch = (d - rest) / rest
                struct_spring += to_other * stretch

                # Minimum-length barrier.
                min_d = min_ratio * rest
                if d < min_d:
                    collapse = (min_d - d) / max(1e-9, min_d)
                    struct_min_push -= to_other * collapse

        struct_spring = project_to_tangent(struct_spring, self.normal)
        struct_min_push = project_to_tangent(struct_min_push, self.normal)

        # Steeper neighborhoods: more spacing pressure, a bit less cohesion.
        mean_slope_local = local_slope_sum / float(max(1, local_slope_count))
        sep_group_scale = 1.0 + (float(AGENT_GROUP_SLOPE_GAIN) * mean_slope_local)
        coh_group_scale = max(
            0.35,
            1.0 - (0.35 * float(AGENT_GROUP_SLOPE_GAIN) * mean_slope_local)
        )

        curv = rg.Vector3d(0, 0, 0)
        if self.curv_dir is not None:
            curv = rg.Vector3d(self.curv_dir)
            curv = project_to_tangent(curv, self.normal)
            if curv.Length > 1e-9:
                curv.Unitize()
            else:
                curv = rg.Vector3d(0, 0, 0)

        slope = rg.Vector3d(self.slope_seek)
        if slope.Length > 1e-9:
            slope.Unitize()

        # Home spring (to original uv point on surface).
        home_pt = self.surface.PointAt(self.uv0.X, self.uv0.Y)
        home = rg.Vector3d(home_pt - self.position)
        home = project_to_tangent(home, self.normal)
        if home.Length > 1e-9:
            home.Unitize()
        else:
            home = rg.Vector3d(0, 0, 0)

        # Noise (3D, then tangent).
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

        # Combine.
        move = (
            (sep * (w_sep * sep_group_scale)) +
            (coh * (w_coh * coh_group_scale)) +
            (peer_slope * w_peer) +
            (struct_spring * w_struct_spring) +
            (struct_min_push * w_struct_min) +
            (curv * w_curv) +
            (slope * w_slope) +
            (home * w_home) +
            (noise * w_noise)
        )

        # Tangent projection safety.
        move = project_to_tangent(move, self.normal)

        # Directional continuity.
        if hasattr(self, "velocity") and self.velocity is not None and self.velocity.Length > 1e-9:
            vdir = rg.Vector3d(self.velocity)
            vdir = project_to_tangent(vdir, self.normal)
            if vdir.Length > 1e-9:
                vdir.Unitize()
                m = clamp01(float(self.momentum))
                move = (move * (1.0 - m)) + (vdir * m)

        if move.Length > 1e-9:
            move.Unitize()
        else:
            move = rg.Vector3d(0, 0, 0)

        # Store per-step movement.
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
def build_agents_from_seed(surface, seed_points, max_speed, seed_val=None):
    pts_raw = iter_any(seed_points)
    pts3 = []
    for pt in pts_raw:
        p3 = to_point3d(pt)
        if p3 is not None:
            pts3.append(p3)

    # Fallback: if no explicit seed points, seed a regular UV lattice.
    if (not pts3) and (surface is not None):
        div_u = as_int(FALLBACK_DIV_U, 8, min_value=1)
        div_v = as_int(FALLBACK_DIV_V, 8, min_value=1)
        du = surface.Domain(0)
        dv = surface.Domain(1)
        for i in range(div_u + 1):
            u = du.T0 + (float(i) / float(div_u)) * (du.T1 - du.T0)
            for j in range(div_v + 1):
                v = dv.T0 + (float(j) / float(div_v)) * (dv.T1 - dv.T0)
                pts3.append(surface.PointAt(u, v))

    # Internal slope-biased seeding (configured at top of file).
    if SEED_INIT_AGENT_COUNT is None:
        init_agent_count = len(pts3)
    else:
        init_agent_count = as_int(SEED_INIT_AGENT_COUNT, len(pts3), min_value=1)
    seed_slope_bias = clamp01(float(SEED_SLOPE_BIAS))
    seed_slope_power = max(0.1, float(SEED_SLOPE_POWER))

    pts3_selected, sel_dbg = select_seed_points(
        surface,
        pts3,
        init_agent_count,
        seed_slope_bias,
        seed_slope_power,
        seed_val
    )

    agents = []
    uvs = []
    poss = []

    for p3 in pts3_selected:
        ok, u, v = surface.ClosestPoint(p3)
        if not ok:
            continue
        uv = rg.Point2d(u, v)
        a = Agent(surface, uv, max_speed, idx=len(agents))
        agents.append(a)
        uvs.append(key2(u, v))
        poss.append(key3(a.position))

    struct_info = assign_structural_links(agents, surface)

    dbg = (
        "seed_raw:{0} seed_coerced:{1} seed_selected:{2} agents:{3} "
        "unique_uv:{4} unique_pos:{5} unique_seed:{6} "
        "slope_bias:{7:.3f} slope_power:{8:.3f} "
        "struct:{9} dims:{10}x{11} links:{12}"
    ).format(
        len(pts_raw), len(pts3), sel_dbg[1], len(agents),
        len(set(uvs)), len(set(poss)), len(set([key3(p) for p in pts3_selected])),
        float(clamp01(seed_slope_bias)), float(seed_slope_power),
        "on" if bool(struct_info.get("enabled", False)) else "off:" + str(struct_info.get("reason", "na")),
        int(struct_info.get("u_count", 0)),
        int(struct_info.get("v_count", 0)),
        int(struct_info.get("links", 0))
    )
    return agents, dbg, pts3_selected

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
                    srf, seed_points, max_speed, seed
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

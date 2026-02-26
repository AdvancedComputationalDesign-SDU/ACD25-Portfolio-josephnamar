#r: numpy
import Rhino.Geometry as rg
import rhinoscriptsyntax as rs
import numpy as np
import random
import math

# ---------------------------------------------------------------------------
# INPUT CONTRACT (Grasshopper)
# ---------------------------------------------------------------------------
# Required inputs:
# - base_surface : Surface/BrepFace/Brep (if Brep, first face is used)
# - divU         : int, U subdivisions used to rebuild out_surface
# - divV         : int, V subdivisions used to rebuild out_surface
# - frequency    : float, wave frequency for the displacement field
# - phase        : float, wave phase shift
# - amplitude    : float, displacement amplitude along surface normal
# - lift         : float, global Z offset after displacement
#
# Optional inputs:
# - seed            : int, deterministic seed (mainly for noise mode)
# - heightmap_type  : int (0 = wave+bump, 1 = radial falloff + deterministic noise)
#
# - point_divU      : int, optional output-point U subdivisions (independent of divU)
# - point_divV      : int, optional output-point V subdivisions (independent of divV)
#   Aliases supported: seed_divU/seed_divV, out_divU/out_divV
#
# - terrain_complexity : float in [0,1]. Higher = more detail + more macro variation
# - terrain_steepness  : float in [0,1]. Higher = sharper ridges + steeper transitions
#
# Outputs:
# - out_surface : generated displaced surface (NurbsSurface or Brep fallback)
# - out_points  : flattened displaced Point3d list (uniform grid by point_divU/point_divV)
# - srf_id      : compatibility output (always None in this RhinoCommon workflow)
# ---------------------------------------------------------------------------


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


def eval_point_normal(srf_obj, u, v):
    pt = srf_obj.PointAt(u, v)
    n = srf_obj.NormalAt(u, v)
    if (not n.IsValid) or n.IsZero:
        n = rg.Vector3d(0, 0, 1)
    else:
        n.Unitize()
    return pt, n


def deterministic_noise(un, vn, seed_val):
    # Deterministic pseudo-noise in [-1, 1], independent of grid resolution.
    n = np.sin((12.9898 * un) + (78.233 * vn) + (37.719 * float(seed_val))) * 43758.5453
    frac = n - np.floor(n)
    return (frac * 2.0) - 1.0

def value_noise_2d(un, vn, cells_u, cells_v, seed_val):
    """
    Smooth value noise sampled from a random lattice with bilinear interpolation.
    Output range: [0, 1].
    """
    cu = max(1, int(cells_u))
    cv = max(1, int(cells_v))
    rng = np.random.RandomState(int(seed_val))
    lattice = rng.rand(cu + 1, cv + 1)

    x = np.minimum(un * float(cu), float(cu) - 1e-9)
    y = np.minimum(vn * float(cv), float(cv) - 1e-9)

    xi = np.floor(x).astype(np.int32)
    yi = np.floor(y).astype(np.int32)
    xf = x - xi
    yf = y - yi

    # Smoothstep interpolation for gentler slope transitions.
    sx = xf * xf * (3.0 - 2.0 * xf)
    sy = yf * yf * (3.0 - 2.0 * yf)

    xi1 = xi + 1
    yi1 = yi + 1

    v00 = lattice[xi, yi]
    v10 = lattice[xi1, yi]
    v01 = lattice[xi, yi1]
    v11 = lattice[xi1, yi1]

    a = v00 + (v10 - v00) * sx
    b = v01 + (v11 - v01) * sx
    return a + (b - a) * sy

def fbm_noise_2d(un, vn, base_cells, octaves, roughness, lacunarity, seed_val):
    """
    Fractal Brownian motion noise from value-noise octaves.
    Output range: approximately [0, 1].
    """
    octv = max(1, int(octaves))
    amp = 1.0
    sum_amp = 0.0
    out = np.zeros_like(un, dtype=float)
    cells = max(1.0, float(base_cells))

    for o in range(octv):
        n = value_noise_2d(un, vn, int(round(cells)), int(round(cells)), int(seed_val) + (o * 1013))
        out += amp * n
        sum_amp += amp
        amp *= float(roughness)
        cells *= float(lacunarity)

    if sum_amp > 1e-12:
        out /= sum_amp
    return out

def random_terrain_field(un, vn, amp, freq, seed_val, opts):
    """
    Random terrain with mixed low/high slope zones:
    - multi-octave smooth noise
    - optional ridged mixing
    - macro hill/valley blobs
    """
    octaves = int(opts.get("octaves", 5))
    roughness = float(opts.get("roughness", 0.55))
    lacunarity = float(opts.get("lacunarity", 2.0))
    ridge_mix = clamp01(float(opts.get("ridge_mix", 0.35)))
    peak_count = max(0, int(opts.get("peak_count", 6)))
    peak_strength = max(0.0, float(opts.get("peak_strength", 0.6)))
    contrast = max(0.1, float(opts.get("contrast", 1.5)))

    base_cells = max(1.0, 2.0 * max(0.25, float(freq)))

    fbm = fbm_noise_2d(un, vn, base_cells, octaves, roughness, lacunarity, seed_val)
    base = (fbm * 2.0) - 1.0

    # Ridged variant emphasizes steeper transitions.
    ridged01 = 1.0 - np.abs(base)
    ridged = (ridged01 * 2.0) - 1.0
    terrain = ((1.0 - ridge_mix) * base) + (ridge_mix * ridged)

    # Add macro hills/valleys to create broad low/high slope regions.
    if peak_count > 0 and peak_strength > 1e-12:
        rng = np.random.RandomState(int(seed_val) + 7919)
        macro = np.zeros_like(un, dtype=float)
        for _ in range(peak_count):
            cx = rng.rand()
            cy = rng.rand()
            sigma = rng.uniform(0.08, 0.28)
            h = rng.uniform(-1.0, 1.0)
            d2 = ((un - cx) ** 2 + (vn - cy) ** 2) / max(1e-9, sigma * sigma)
            macro += h * np.exp(-0.5 * d2)
        m = np.max(np.abs(macro))
        if m > 1e-12:
            macro /= m
        terrain = ((1.0 - peak_strength) * terrain) + (peak_strength * macro)

    # Contrast boost for clearer steep/flat distinctions.
    terrain = np.tanh(contrast * terrain)
    return float(amp) * terrain


def terrain_options_from_controls(complexity, steepness):
    """
    Map two user-friendly controls to full random-terrain parameters.
    """
    c = clamp01(float(complexity))
    s = clamp01(float(steepness))

    octaves = int(round(3.0 + 5.0 * c))          # 3..8
    roughness = max(0.25, 0.72 - 0.27 * c)       # ~0.72..0.45
    lacunarity = 1.5 + 1.0 * c                   # 1.5..2.5
    ridge_mix = clamp01(0.10 + 0.80 * s)         # 0.1..0.9
    peak_count = int(round(2.0 + 8.0 * c))       # 2..10
    peak_strength = clamp01(0.20 + 0.65 * c)     # 0.2..0.85
    contrast = 0.9 + 2.2 * s                     # 0.9..3.1

    return {
        "octaves": octaves,
        "roughness": roughness,
        "lacunarity": lacunarity,
        "ridge_mix": ridge_mix,
        "peak_count": peak_count,
        "peak_strength": peak_strength,
        "contrast": contrast
    }


def evaluate_height_field(un, vn, amp, freq, phs, heightmap_type, seed_val, terrain_opts=None):
    if int(heightmap_type) == 0:
        wave = np.sin((2.0 * math.pi * freq * (un + vn)) + phs)
        dist = np.sqrt((un - 0.5) ** 2 + (vn - 0.5) ** 2)
        bump = np.exp(-5.0 * dist ** 2)
        return amp * (0.6 * wave + 0.4 * bump)

    # Richer random terrain mode (type 1).
    return random_terrain_field(un, vn, amp, freq, seed_val, terrain_opts or {})


def sample_displaced_grid(
    srf_obj,
    dom_u,
    dom_v,
    u_div,
    v_div,
    amp,
    freq,
    phs,
    heightmap_type,
    lift_val,
    seed_val,
    terrain_opts=None
):
    # Parameter-space sampling.
    u_vals = np.linspace(dom_u.T0, dom_u.T1, u_div + 1)
    v_vals = np.linspace(dom_v.T0, dom_v.T1, v_div + 1)
    Ug, Vg = np.meshgrid(u_vals, v_vals, indexing="ij")

    # Normalized UV for displacement field evaluation.
    un = np.linspace(0.0, 1.0, u_div + 1)
    vn = np.linspace(0.0, 1.0, v_div + 1)
    Un, Vn = np.meshgrid(un, vn, indexing="ij")

    H = evaluate_height_field(Un, Vn, amp, freq, phs, heightmap_type, seed_val, terrain_opts)

    pts_grid = [[None] * (v_div + 1) for _ in range(u_div + 1)]
    pts_flat = []

    for i in range(u_div + 1):
        for j in range(v_div + 1):
            pt, n = eval_point_normal(srf_obj, float(Ug[i, j]), float(Vg[i, j]))
            p = pt + n * float(H[i, j])
            p3 = rg.Point3d(float(p.X), float(p.Y), float(p.Z + lift_val))
            pts_grid[i][j] = p3
            pts_flat.append(p3)

    return pts_grid, pts_flat


def build_surface_candidates(pts_grid, u_count, v_count, deg_u, deg_v):
    pts_a = [pts_grid[i][j] for i in range(u_count) for j in range(v_count)]
    pts_b = [pts_grid[i][j] for j in range(v_count) for i in range(u_count)]

    srf_a = rg.NurbsSurface.CreateThroughPoints(pts_a, u_count, v_count, deg_u, deg_v, False, False)
    srf_b = rg.NurbsSurface.CreateThroughPoints(pts_b, u_count, v_count, deg_u, deg_v, False, False)
    return srf_a, pts_a, srf_b, pts_b


def loft_surface_from_grid(pts_grid, u_count, v_count, along_u=True):
    curves = []
    if along_u:
        for i in range(u_count):
            row_pts = [pts_grid[i][j] for j in range(v_count)]
            pl = rg.Polyline(row_pts)
            if pl.IsValid and pl.Count >= 2:
                curves.append(pl.ToNurbsCurve())
    else:
        for j in range(v_count):
            col_pts = [pts_grid[i][j] for i in range(u_count)]
            pl = rg.Polyline(col_pts)
            if pl.IsValid and pl.Count >= 2:
                curves.append(pl.ToNurbsCurve())

    if len(curves) < 2:
        return None

    breps = rg.Brep.CreateFromLoft(
        curves,
        rg.Point3d.Unset,
        rg.Point3d.Unset,
        rg.LoftType.Normal,
        False
    )
    if breps and len(breps) > 0 and breps[0] and breps[0].IsValid:
        return breps[0]
    return None


def first_face_surface(brep_obj):
    if brep_obj and isinstance(brep_obj, rg.Brep) and brep_obj.Faces.Count > 0:
        return brep_obj.Faces[0].ToNurbsSurface()
    return None


# ---------------------------------------------------------------------------
# INPUT NORMALIZATION
# ---------------------------------------------------------------------------
IN_base_surface = globals().get("base_surface", None)
IN_seed = globals().get("seed", None)
IN_divU = globals().get("divU", 24)
IN_divV = globals().get("divV", 24)
IN_frequency = globals().get("frequency", 1.0)
IN_phase = globals().get("phase", 0.0)
IN_amplitude = globals().get("amplitude", 1.0)
IN_lift = globals().get("lift", 0.0)
IN_heightmap_type = globals().get("heightmap_type", 0)
IN_terrain_complexity = globals().get("terrain_complexity", 0.6)
IN_terrain_steepness = globals().get("terrain_steepness", 0.6)

# Independent output-point density controls.
IN_point_divU = globals().get(
    "point_divU",
    globals().get("seed_divU", globals().get("out_divU", IN_divU))
)
IN_point_divV = globals().get(
    "point_divV",
    globals().get("seed_divV", globals().get("out_divV", IN_divV))
)

U = as_int(IN_divU, 24, min_value=1)
V = as_int(IN_divV, 24, min_value=1)
U_pts = as_int(IN_point_divU, U, min_value=1)
V_pts = as_int(IN_point_divV, V, min_value=1)

freq = as_float(IN_frequency, 1.0)
phs = as_float(IN_phase, 0.0)
amp = as_float(IN_amplitude, 1.0)
lift_val = as_float(IN_lift, 0.0)
heightmap_type = as_int(IN_heightmap_type, 0, min_value=0)
terrain_complexity = clamp01(as_float(IN_terrain_complexity, 0.6))
terrain_steepness = clamp01(as_float(IN_terrain_steepness, 0.6))

seed_i = 0
if IN_seed is not None:
    try:
        seed_i = int(IN_seed)
    except:
        seed_i = 0
random.seed(seed_i)
np.random.seed(seed_i)

terrain_opts = terrain_options_from_controls(terrain_complexity, terrain_steepness)


# ---------------------------------------------------------------------------
# OUTPUTS
# ---------------------------------------------------------------------------
out_surface = None
out_points = []
srf_id = None  # Compatibility placeholder; no document object is created here.


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
srf_obj = coerce_face_or_surface(IN_base_surface)

if srf_obj is not None and isinstance(srf_obj, (rg.Surface, rg.BrepFace)):
    dom_u = srf_obj.Domain(0)
    dom_v = srf_obj.Domain(1)

    # 1) Build displaced grid used to reconstruct the output surface.
    pts_grid_surface, pts_flat_surface = sample_displaced_grid(
        srf_obj,
        dom_u,
        dom_v,
        U,
        V,
        amp,
        freq,
        phs,
        heightmap_type,
        lift_val,
        seed_i,
        terrain_opts
    )

    deg_u = 3 if (U + 1) >= 4 else max(1, U)
    deg_v = 3 if (V + 1) >= 4 else max(1, V)

    srf_a, pts_a, srf_b, pts_b = build_surface_candidates(
        pts_grid_surface, U + 1, V + 1, deg_u, deg_v
    )

    if srf_a and srf_a.IsValid:
        out_surface = srf_a
    elif srf_b and srf_b.IsValid:
        out_surface = srf_b
    else:
        loft_a = loft_surface_from_grid(pts_grid_surface, U + 1, V + 1, along_u=True)
        loft_b = loft_surface_from_grid(pts_grid_surface, U + 1, V + 1, along_u=False)

        if loft_a and loft_a.IsValid:
            out_surface = first_face_surface(loft_a) or loft_a
        elif loft_b and loft_b.IsValid:
            out_surface = first_face_surface(loft_b) or loft_b

    # 2) Build output points with independent density (for agent seeding/control).
    if (U_pts == U) and (V_pts == V):
        out_points = pts_flat_surface
    else:
        _, pts_flat_dense = sample_displaced_grid(
            srf_obj,
            dom_u,
            dom_v,
            U_pts,
            V_pts,
            amp,
            freq,
            phs,
            heightmap_type,
            lift_val,
            seed_i,
            terrain_opts
        )
        out_points = pts_flat_dense

import scriptcontext as sc
import Rhino.Geometry as rg

# ---------------------------------------------------------------------------
# INPUT CONTRACT (Grasshopper)
# ---------------------------------------------------------------------------
# Inputs:
# - agents : list[Agent] from agent_builder (preferred)
# - step   : bool. Advances simulation only on rising edge (False->True)
# - reset  : bool (optional). Resets agents to their start UV/position
# Main live force inputs (recommended GH sliders):
# - max_speed
# - sep_gain
# - coh_gain (or cohesion_gain)
# - base_spacing
# - freedom
# - struct_spring_gain
# - struct_min_dist_gain
#
# Backward compatibility:
# - If `agents` input is not wired, script will try legacy `x.agents`.
#
# Outputs:
# - agents / agents_out : updated agent list
# - P                   : list[Point3d] agent positions
# - V                   : list[Line] velocity vectors
# - D                   : debug string
# ---------------------------------------------------------------------------


def as_bool(value, default=False):
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in ("1", "true", "t", "yes", "y", "on"):
        return True
    if s in ("0", "false", "f", "no", "n", "off"):
        return False
    return bool(default)


def iter_any(obj):
    if obj is None:
        return []
    try:
        return [x for x in obj]
    except:
        return [obj]


def normalize_agents_input(obj):
    """
    Accept list/tuple/wrapped inputs and return a clean list[Agent]-like objects.
    Handles one-level wrapping such as (agents_list,) from a single-output builder.
    """
    items = iter_any(obj)
    if len(items) == 1:
        only = items[0]
        try:
            nested = [x for x in only]
            if nested and hasattr(nested[0], "update"):
                items = nested
        except:
            pass

    out = []
    for a in items:
        if hasattr(a, "update") and hasattr(a, "position"):
            out.append(a)
    return out


def collect_runtime_params():
    """
    Collect main force parameters from simulator GH inputs.
    Keys are normalized to names used by Agent.apply_runtime_params.
    """
    alias_map = {
        "max_speed": ["max_speed", "max_speed_live", "speed"],
        "sep_gain": ["sep_gain"],
        "coh_gain": ["coh_gain", "cohesion_gain"],
        "base_spacing": ["base_spacing"],
        "freedom": ["freedom"],
        "struct_spring_gain": ["struct_spring_gain"],
        "struct_min_dist_gain": ["struct_min_dist_gain"],
    }

    out = {}
    for key, aliases in alias_map.items():
        for name in aliases:
            val = globals().get(name, None)
            if val is not None:
                out[key] = val
                break
    return out


# ---------------------------------------------------------------------------
# Read inputs
# ---------------------------------------------------------------------------
in_agents = globals().get("agents", None)
if in_agents is None:
    # Legacy fallback: previous setup passed builder component instance as x.
    x = globals().get("x", None)
    if x is not None and hasattr(x, "agents"):
        in_agents = getattr(x, "agents", None)

step_flag = as_bool(globals().get("step", False), False)
reset_flag = as_bool(globals().get("reset", False), False)
runtime_params = collect_runtime_params()


# ---------------------------------------------------------------------------
# Sticky state (edge-trigger stepping)
# ---------------------------------------------------------------------------
guid = str(ghenv.Component.InstanceGuid)
k_prev = "A4_prev_step_" + guid
k_prev_reset = "A4_prev_reset_" + guid
k_step = "A4_step_count_" + guid
k_agents = "A4_agents_state_" + guid
k_last_disp = "A4_last_mean_disp_" + guid

if k_prev not in sc.sticky:
    sc.sticky[k_prev] = False
if k_prev_reset not in sc.sticky:
    sc.sticky[k_prev_reset] = False
if k_step not in sc.sticky:
    sc.sticky[k_step] = 0
if k_last_disp not in sc.sticky:
    sc.sticky[k_last_disp] = 0.0

do_step = (step_flag is True) and (sc.sticky[k_prev] is False)
sc.sticky[k_prev] = step_flag

do_reset = (reset_flag is True) and (sc.sticky[k_prev_reset] is False)
sc.sticky[k_prev_reset] = reset_flag

# Persistent agent state lives in sticky and only re-initializes on reset.
if do_reset or (k_agents not in sc.sticky):
    sc.sticky[k_agents] = normalize_agents_input(in_agents)

agents_state = sc.sticky.get(k_agents, [])
if (not agents_state) and in_agents is not None:
    # One-time recovery if sticky got cleared unexpectedly.
    agents_state = normalize_agents_input(in_agents)
    sc.sticky[k_agents] = agents_state

# Apply live slider values every solve so next step always uses latest params.
if agents_state and runtime_params:
    for a in agents_state:
        try:
            if hasattr(a, "apply_runtime_params"):
                a.apply_runtime_params(runtime_params)
        except:
            pass


# ---------------------------------------------------------------------------
# Optional reset + simulation step
# ---------------------------------------------------------------------------
if do_reset:
    for a in agents_state:
        uv0 = getattr(a, "uv0", None)
        srf = getattr(a, "surface", None)
        if (uv0 is not None) and (srf is not None):
            try:
                a.uv = rg.Point2d(uv0.X, uv0.Y)
                a.position = rg.Point3d(srf.PointAt(uv0.X, uv0.Y))
            except:
                pass

        try:
            a.velocity = rg.Vector3d(0, 0, 0)
        except:
            pass
        try:
            a.age = 0
        except:
            pass
        try:
            a.spawn_cooldown = 0
        except:
            pass

    sc.sticky[k_step] = 0
    sc.sticky[k_last_disp] = 0.0

prev_pos = {}
for a in agents_state:
    p = getattr(a, "position", None)
    if p is not None:
        prev_pos[id(a)] = rg.Point3d(p)

update_fail_count = 0
if do_step and agents_state:
    step_disp_sum = 0.0
    step_disp_count = 0

    for a in agents_state:
        try:
            try:
                a.update(agents_state, runtime_params)
            except TypeError:
                # Backward compatibility with older Agent.update(self, agents).
                a.update(agents_state)
        except:
            # Keep stepping robust if one agent fails.
            update_fail_count += 1

        # Ensure velocity reflects actual displacement this step.
        # This makes V robust even if an Agent implementation does not set velocity.
        p_prev = prev_pos.get(id(a), None)
        p_now = getattr(a, "position", None)
        if p_prev is not None and p_now is not None:
            try:
                a.velocity = rg.Vector3d(rg.Point3d(p_now) - p_prev)
                vlen = float(a.velocity.Length)
                if vlen > 1e-9:
                    step_disp_sum += vlen
                    step_disp_count += 1
            except:
                pass

    sc.sticky[k_step] = int(sc.sticky.get(k_step, 0)) + 1
    if step_disp_count > 0:
        sc.sticky[k_last_disp] = step_disp_sum / float(step_disp_count)
    else:
        sc.sticky[k_last_disp] = 0.0

# Persist updated state for the next solve.
sc.sticky[k_agents] = agents_state


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
P = []
V = []
vel_sum = 0.0
vel_count = 0

for a in agents_state:
    p = getattr(a, "position", None)
    if p is None:
        continue

    p3 = rg.Point3d(p)
    P.append(p3)

    vel = getattr(a, "velocity", None)
    if vel is not None and vel.Length > 1e-9:
        vel_sum += float(vel.Length)
        vel_count += 1
        V.append(rg.Line(p3, p3 + vel))
    else:
        # Fallback display: predicted direction from last decision, if available.
        md = getattr(a, "move_dir", None)
        sl = float(getattr(a, "step_len", 0.0))
        if md is not None and hasattr(md, "Length") and md.Length > 1e-9 and sl > 1e-9:
            md_u = rg.Vector3d(md)
            md_u.Unitize()
            V.append(rg.Line(p3, p3 + (md_u * sl)))

agents = agents_state      # Preferred output name.
agents_out = agents_state  # Alias output name.

D = "agents:{0} step_count:{1} stepped:{2} reset:{3}".format(
    len(agents_state),
    int(sc.sticky.get(k_step, 0)),
    do_step,
    do_reset
)
if update_fail_count > 0:
    D += " update_fail:{0}".format(update_fail_count)
if len(runtime_params) > 0:
    keys = sorted([str(k) for k in runtime_params.keys()])
    preview = ",".join(keys[:6])
    if len(keys) > 6:
        preview += ",..."
    D += " params:{0}[{1}]".format(len(runtime_params), preview)

if vel_count > 0:
    D += " mean_disp:{0:.4f}".format(vel_sum / float(vel_count))
else:
    D += " mean_disp:0.0000"

D += " last_step_disp:{0:.4f}".format(float(sc.sticky.get(k_last_disp, 0.0)))

if len(P) > 0:
    p0 = P[0]
    D += " p0:({0:.3f},{1:.3f},{2:.3f})".format(float(p0.X), float(p0.Y), float(p0.Z))

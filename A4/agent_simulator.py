import scriptcontext as sc
import Rhino.Geometry as rg

# ---------------------------------------------------------------------------
# INPUT CONTRACT (Grasshopper)
# ---------------------------------------------------------------------------
# Inputs:
# - agents : list[Agent] from agent_builder (preferred)
# - step   : bool. Advances simulation only on rising edge (False->True)
# - reset  : bool (optional). Resets agents to their start UV/position
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


# ---------------------------------------------------------------------------
# Read inputs
# ---------------------------------------------------------------------------
in_agents = globals().get("agents", None)
if in_agents is None:
    # Legacy fallback: previous setup passed builder component instance as x.
    x = globals().get("x", None)
    if x is not None and hasattr(x, "agents"):
        in_agents = getattr(x, "agents", None)

agents_state = iter_any(in_agents)
step_flag = as_bool(globals().get("step", False), False)
reset_flag = as_bool(globals().get("reset", False), False)


# ---------------------------------------------------------------------------
# Sticky state (edge-trigger stepping)
# ---------------------------------------------------------------------------
guid = str(ghenv.Component.InstanceGuid)
k_prev = "A4_prev_step_" + guid
k_step = "A4_step_count_" + guid

if k_prev not in sc.sticky:
    sc.sticky[k_prev] = False
if k_step not in sc.sticky:
    sc.sticky[k_step] = 0

do_step = (step_flag is True) and (sc.sticky[k_prev] is False)
sc.sticky[k_prev] = step_flag


# ---------------------------------------------------------------------------
# Optional reset + simulation step
# ---------------------------------------------------------------------------
if reset_flag:
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

prev_pos = {}
for a in agents_state:
    p = getattr(a, "position", None)
    if p is not None:
        prev_pos[id(a)] = rg.Point3d(p)

update_fail_count = 0
if do_step and agents_state:
    for a in agents_state:
        try:
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
            except:
                pass
    sc.sticky[k_step] = int(sc.sticky.get(k_step, 0)) + 1


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
P = []
V = []
for a in agents_state:
    p = getattr(a, "position", None)
    if p is None:
        continue
    p3 = rg.Point3d(p)
    P.append(p3)

    vel = getattr(a, "velocity", None)
    if vel is not None and vel.Length > 1e-9:
        V.append(rg.Line(p3, p3 + vel))

agents = agents_state      # Preferred output name.
agents_out = agents_state  # Alias output name.

D = "agents:{0} step_count:{1} stepped:{2} reset:{3}".format(
    len(agents_state),
    int(sc.sticky.get(k_step, 0)),
    do_step,
    reset_flag
)
if update_fail_count > 0:
    D += " update_fail:{0}".format(update_fail_count)

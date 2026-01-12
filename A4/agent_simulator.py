import scriptcontext as sc
import Rhino.Geometry as rg

# Retrieve agents
agents = None
if x is not None and hasattr(x, "agents"):
    agents = x.agents

# Edge trigger keyed by THIS simulator instance (prevents cross-component conflicts)
k_prev = "A4_prev_step_" + str(ghenv.Component.InstanceGuid)
if k_prev not in sc.sticky:
    sc.sticky[k_prev] = False

do_step = (step is True) and (sc.sticky[k_prev] is False)
sc.sticky[k_prev] = step

# Step
if agents is not None and do_step:
    for a in agents:
        a.update(agents)

# Outputs
P = []
V = []
if agents is not None:
    for a in agents:
        # force fresh Point3d copy
        P.append(rg.Point3d(a.position))
        if a.velocity is not None and a.velocity.Length > 1e-9:
            V.append(rg.Line(a.position, a.position + a.velocity))

D = "agents:{0} stepped:{1}".format(0 if agents is None else len(agents), do_step)

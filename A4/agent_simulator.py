"""
Assignment 4: Agent-Based Model for Surface Panelization
Author: Your Name

Agent Simulator (Mode B – edge-triggered, RhinoCommon-only)
"""

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
import scriptcontext as sc
import Rhino.Geometry as rg

# -----------------------------------------------------------------------------
# Retrieve agents from builder
# -----------------------------------------------------------------------------
agents = None
if x is not None and hasattr(x, "agents"):
    agents = x.agents

# -----------------------------------------------------------------------------
# Reset step memory when agent set changes
# -----------------------------------------------------------------------------
if "agents_id" not in sc.sticky:
    sc.sticky["agents_id"] = None
    sc.sticky["prev_step"] = False

current_id = id(agents)

if sc.sticky["agents_id"] != current_id:
    sc.sticky["agents_id"] = current_id
    sc.sticky["prev_step"] = False

# -----------------------------------------------------------------------------
# Edge-triggered stepping (False → True)
# -----------------------------------------------------------------------------
prev_step = sc.sticky["prev_step"]
do_step = (step is True) and (prev_step is False)

if agents is not None and do_step:
    for agent in agents:
        agent.update(agents)

sc.sticky["prev_step"] = step

# -----------------------------------------------------------------------------
# Visualization (RhinoCommon ONLY — no document writes)
# -----------------------------------------------------------------------------
P = []  # agent positions (Point3d)
V = []  # velocity vectors (Line)

if agents is not None:
    for agent in agents:
        pos = agent.position
        vel = agent.velocity

        # output position
        P.append(pos)

        # output velocity only if non-zero
        if vel.Length > 1e-9:
            V.append(rg.Line(pos, pos + vel))

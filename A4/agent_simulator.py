"""
Assignment 4: Agent-Based Model for Surface Panelization
Agent Simulator (edge-triggered step)
"""

import rhinoscriptsyntax as rs
import scriptcontext as sc

# -------------------------------------------------------------------------
# Retrieve agents
# -------------------------------------------------------------------------
agents = None
if x is not None and hasattr(x, "agents"):
    agents = x.agents

# -------------------------------------------------------------------------
# Persistent storage for previous step value
# -------------------------------------------------------------------------
if "prev_step" not in sc.sticky:
    sc.sticky["prev_step"] = False

prev_step = sc.sticky["prev_step"]

# -------------------------------------------------------------------------
# Detect rising edge: False -> True
# -------------------------------------------------------------------------
do_step = (step is True) and (prev_step is False)

# -------------------------------------------------------------------------
# Step simulation (exactly once per click)
# -------------------------------------------------------------------------
if agents is not None and do_step:
    for agent in agents:
        agent.update(agents)

# store current step state
sc.sticky["prev_step"] = step

# -------------------------------------------------------------------------
# Visualization
# -------------------------------------------------------------------------
P = []
V = []

if agents is not None:
    for agent in agents:
        pos = agent.position
        vel = agent.velocity

        P.append(rs.AddPoint(pos.X, pos.Y, pos.Z))

        end = pos + vel
        V.append(rs.AddLine(
            (pos.X, pos.Y, pos.Z),
            (end.X, end.Y, end.Z)
        ))

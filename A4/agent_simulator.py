"""
Assignment 4: Agent-Based Model for Surface Panelization
Author: Your Name

Agent Simulator Template

Description:
This file defines the structural outline for stepping and visualizing
agents within Grasshopper. No simulation logic is implemented. All behavior
(update, responding to signals, movement, etc.) must be
implemented inside your Agent class in `agent_builder.py`.

Note: This script is intended to be used within Grasshopper's Python
scripting component.
"""

# -----------------------------------------------------------------------------
# Imports (extend as needed)
# -----------------------------------------------------------------------------
import rhinoscriptsyntax as rs
import numpy as np

# -----------------------------------------------------------------------------
# Retrieve agents from upstream Grasshopper component
# -----------------------------------------------------------------------------
# Expected pattern (example):
# agents = x.agents  # where `x` is a stateful component instance
# Replace `x` and the attribute name with whatever your GH setup uses.

agents = x.agents # access agents from the agents_builder component

# -----------------------------------------------------------------------------
# Step simulation (delegated to Agent methods)
# -----------------------------------------------------------------------------
# Suggested loop structure:
if agents is not None:
    for agent in agents:
        agent.update(agents)

# -----------------------------------------------------------------------------
# Visualization placeholders (Rhino + NumPy-friendly)
# -----------------------------------------------------------------------------
# Minimal outputs:
# - Points representing agent positions
# - Vectors, polylines, trails, or any custom debug geometry

P = []  # list of position points (e.g., rs.AddPoint(...))
V = []  # list of velocity vectors or other debug geometry

# Example geometry generation (uncomment and adapt):
for agent in agents:
    P.append(rs.AddPoint(agent.position[0], agent.position[1], agent.position[2]))
    # create a line or vector visualization from pos in direction vel
    end = agent.position + agent.velocity
    V.append(rs.AddLine(rs.coerce3dpoint(pos), rs.coerce3dpoint(end)))
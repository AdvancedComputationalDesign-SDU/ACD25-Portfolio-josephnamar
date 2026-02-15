"""
A4 agent_builder placeholder.

This file is intentionally reduced so the current commit can focus on
surface generation only.
"""

import Rhino.Geometry as rg


class MyComponent(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, reset, base_surface, seed, max_speed, seed_points: list[object]):
        if reset or (not hasattr(self, "agents")):
            self.agents = []

        x = self
        dbg = "agent_builder placeholder active (no agents built)"
        seed_preview = []
        return x, dbg, seed_preview

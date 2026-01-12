"""
Assignment 4: Agent-Based Model for Surface Panelization

Author: Your Name

Agent Builder Template
"""

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
import rhinoscriptsyntax as rs
import random
import numpy as np
import Rhino
import Rhino.Geometry as rg

# -----------------------------------------------------------------------------
# Utility
# -----------------------------------------------------------------------------
def seed_everything(seed):
    if seed is None:
        return
    try:
        s = int(seed)
    except:
        return
    random.seed(s)
    np.random.seed(s)

# -----------------------------------------------------------------------------
# Agent
# -----------------------------------------------------------------------------
class Agent:
    """Represents a single agent with position, velocity, and state."""

    def __init__(self, position, velocity):
        self.position = position          # Point3d (public)
        self.velocity = velocity          # Vector3d (public)

        self.uv = None                    # Point2d (internal)
        self.uv_velocity = None           # Vector2d (internal)
        self.surface = None

        self.max_speed = 0.02
        self.noise = 0.003
        self.age = 0

        # sensed values
        self.nearest_dist = None
        self.nearest_vec = None
        self.curv_dir = None              # Vector3d
        self.curv_mag = 0.0

    # -------------------------------------------------------------------------
    # SENSE
    # -------------------------------------------------------------------------
    def sense(self, agents):
        """Sense neighbors and surface curvature."""
        # --- neighbor sensing ---
        self.nearest_dist = None
        self.nearest_vec = None

        for other in agents:
            if other is self:
                continue
            d = self.position.DistanceTo(other.position)
            if self.nearest_dist is None or d < self.nearest_dist:
                self.nearest_dist = d
                v = rg.Vector3d(self.position - other.position)
                if v.Length > 1e-9:
                    v.Unitize()
                self.nearest_vec = v

        # --- curvature sensing ---
        self.curv_dir = None
        self.curv_mag = 0.0

        if self.surface is None or self.uv is None:
            return

        try:
            sc = self.surface.CurvatureAt(self.uv.X, self.uv.Y)
            if sc is None:
                return

            k0 = abs(sc.Kappa(0))
            k1 = abs(sc.Kappa(1))

            d0 = sc.Direction(0)
            d1 = sc.Direction(1)

            # choose minimum curvature direction (panel-friendly)
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

        except:
            self.curv_dir = None
            self.curv_mag = 0.0

    # -------------------------------------------------------------------------
    # DECIDE
    # -------------------------------------------------------------------------
    def decide(self):
        """Blend curvature following and spacing repulsion."""
        if self.uv_velocity is None:
            self.uv_velocity = rg.Vector2d(self.max_speed, 0.0)

        # weights
        target_spacing = 1.0
        repel_gain = 0.01
        curv_gain = 0.02

        du = self.surface.Domain(0)
        dv = self.surface.Domain(1)

        # --- curvature following ---
        if self.curv_dir is not None:
            eps = 0.01 * (du.T1 - du.T0)
            pu = self.surface.PointAt(min(du.T1, self.uv.X + eps), self.uv.Y)
            pv = self.surface.PointAt(self.uv.X, min(dv.T1, self.uv.Y + eps))

            tu = pu - self.position
            tv = pv - self.position

            cu = rg.Vector3d.Multiply(self.curv_dir, tu)
            cv = rg.Vector3d.Multiply(self.curv_dir, tv)

            self.uv_velocity.X += curv_gain * cu
            self.uv_velocity.Y += curv_gain * cv

        # --- neighbor repulsion ---
        if self.nearest_dist is not None and self.nearest_dist < target_spacing:
            eps = 0.01 * (du.T1 - du.T0)
            pu = self.surface.PointAt(min(du.T1, self.uv.X + eps), self.uv.Y)
            pv = self.surface.PointAt(self.uv.X, min(dv.T1, self.uv.Y + eps))

            tu = pu - self.position
            tv = pv - self.position

            ru = rg.Vector3d.Multiply(self.nearest_vec, tu)
            rv = rg.Vector3d.Multiply(self.nearest_vec, tv)

            self.uv_velocity.X += repel_gain * ru
            self.uv_velocity.Y += repel_gain * rv

        # --- noise ---
        self.uv_velocity.X += random.uniform(-1.0, 1.0) * self.noise
        self.uv_velocity.Y += random.uniform(-1.0, 1.0) * self.noise

        # clamp speed
        sp = (self.uv_velocity.X**2 + self.uv_velocity.Y**2) ** 0.5
        if sp > self.max_speed:
            self.uv_velocity.X = (self.uv_velocity.X / sp) * self.max_speed
            self.uv_velocity.Y = (self.uv_velocity.Y / sp) * self.max_speed

    # -------------------------------------------------------------------------
    # MOVE
    # -------------------------------------------------------------------------
    def move(self):
        if self.surface is None or self.uv is None:
            return

        du = self.surface.Domain(0)
        dv = self.surface.Domain(1)

        u = max(du.T0, min(du.T1, self.uv.X + self.uv_velocity.X))
        v = max(dv.T0, min(dv.T1, self.uv.Y + self.uv_velocity.Y))

        prev = self.position

        self.uv = rg.Point2d(u, v)
        self.position = self.surface.PointAt(u, v)
        self.velocity = rg.Vector3d(self.position - prev)

        self.age += 1

    # -------------------------------------------------------------------------
    # UPDATE
    # -------------------------------------------------------------------------
    def update(self, agents):
        self.sense(agents)
        self.decide()
        self.move()

# -----------------------------------------------------------------------------
# Factory
# -----------------------------------------------------------------------------
def build_agents(num_agents, initial_data=None):
    initial_data = initial_data or {}
    seed_everything(initial_data.get("seed", None))

    srf = initial_data.get("surface", None)
    srf_geo = getattr(srf, "Geometry", srf)

    try:
        import System
        if isinstance(srf_geo, System.Guid):
            srf_geo = rs.coercesurface(srf_geo)
    except:
        pass

    if isinstance(srf_geo, rg.Brep) and srf_geo.Faces.Count > 0:
        srf_geo = srf_geo.Faces[0]

    du = srf_geo.Domain(0)
    dv = srf_geo.Domain(1)

    max_speed = float(initial_data.get("max_speed", 0.02))

    agents = []
    for _ in range(int(num_agents)):
        u = random.uniform(du.T0, du.T1)
        v = random.uniform(dv.T0, dv.T1)

        ang = random.uniform(0.0, 2.0 * np.pi)
        spd = random.uniform(0.005, max_speed)

        a = Agent(srf_geo.PointAt(u, v), rg.Vector3d(0, 0, 0))
        a.surface = srf_geo
        a.uv = rg.Point2d(u, v)
        a.uv_velocity = rg.Vector2d(np.cos(ang) * spd, np.sin(ang) * spd)
        a.max_speed = max_speed

        agents.append(a)

    return agents

# -----------------------------------------------------------------------------
# Grasshopper stateful component
# -----------------------------------------------------------------------------
class MyComponent(Grasshopper.Kernel.GH_ScriptInstance):
    def RunScript(self, N, reset, base_surface, seed, max_speed):
        if reset or not hasattr(self, "agents"):
            init = {"seed": seed, "surface": base_surface, "max_speed": max_speed}
            self.agents = build_agents(N, initial_data=init)
        return self

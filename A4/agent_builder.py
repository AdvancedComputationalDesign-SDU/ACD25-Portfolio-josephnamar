"""
Assignment 4: Agent-Based Model for Surface Panelization

Author: Your Name

Agent Builder Template

Description:
Defines the core Agent class and factory methods for constructing an
agent-based system. Provides a high-level OOP structure for sensing,
decision-making, and movement, along with a stateful Grasshopper
GH_ScriptInstance example.

Note: This script is intended to be used within Grasshopper's Python
scripting component.
"""


# -----------------------------------------------------------------------------
# Imports (extend as needed)
# -----------------------------------------------------------------------------
import rhinoscriptsyntax as rs
import random
import numpy as np


# -----------------------------------------------------------------------------
# Utility functions (optional)
# -----------------------------------------------------------------------------
def seed_everything(seed):
    """Set random seeds for reproducibility."""
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

seed_everything(42)

# -----------------------------------------------------------------------------
# Core agent class
# -----------------------------------------------------------------------------
class Agent:
    """Represents a single agent with position, velocity, and state."""

    def __init__(self, position, velocity):
        """
        Initialize the agent with position and velocity.
        """
        self.position = position
        self.velocity = velocity
        # TODO: Add any other attributes you need (e.g., id, age, type, etc.).

    def sense(self, signals):
        """Read environmental signals relevant to the agent."""
        # TODO: Implement sensing logic based on your chosen signals.
        pass

    def decide(self):
        """Decide on actions based on sensed information."""
        # TODO: Implement decision rules.
        pass

    def move(self):
        """Update position according to velocity and rules."""
        # TODO: Implement movement logic.
        pass

    def update(self, agents):
        """Perform one update cycle: sense, decide, and move."""
        # TODO: Call sense / decide / move here, or structure as you prefer.
        pass


# -----------------------------------------------------------------------------
# Factory for creating agents
# -----------------------------------------------------------------------------
def build_agents(num_agents, initial_data=None):
    """Create and initialize a list of Agent instances."""
    # TODO: Implement build_agents(...) based on your design.
    raise NotImplementedError("Implement build_agents(...) based on your design.")


# -----------------------------------------------------------------------------
# Grasshopper script instance (structural placeholder)
# -----------------------------------------------------------------------------
"""Example container for managing agent state in Grasshopper.

Use this class to maintain and update agents between recomputations.
"""

class MyComponent(Grasshopper.Kernel.GH_ScriptInstance):
    """Manages persistent agent list across Grasshopper runs."""

    def RunScript(self, N:int, reset:bool):
        """
        Main entry point called by Grasshopper.

        Parameters
        ----------
        N : int
            Number of agents.
        reset : bool
            When True, reinitialize agents.
        """
        if reset or not hasattr(self, "agents"):
            self.agents = build_agents(N)
        return self
---
layout: default
title: Project Documentation
parent: "A4: Agent-Based Modeling for Surface Panelization"
nav_order: 2
nav_exclude: false
search_exclude: false
---

# Assignment 4: Agent-Based Modeling for Surface Panelization

[View on GitHub]({{ site.github.repository_url }})

![Example Structural Panelization](images/agent_based.jpg)

## Objective

In this assignment, you will develop an **agent-based system for surface rationalization** using **Object-Oriented Programming (OOP)** in Python. Building on the surface you generated in Assignment 3 (or a comparable heightmap-driven surface), you will design agents that respond to geometric signals and collectively produce **panelization patterns**. The core idea is that agents move, interact, and make decisions based on how they sample the geometry, and their trajectories and interactions become the basis for a rationalized panelization of that surface.

Your implementation must incorporate **at least two types of geometric signals** (chosen from curvature, slope, vector fields, scalar fields, and spatial influences) when defining agent behavior. The primary outputs of this assignment are: (1) a rationalized panelization of your surface and (2) simulated agent trajectories and fields that you document and analyze.

---

## Repository Structure

```
A4/
├── index.md                    # Do not edit front matter or content
├── README.md                   # Project documentation; Keep front matter, replace the rest with your project documentation
├── BRIEF.md                    # Assignment brief; Do not edit front matter or content
├── agent_panelization.gh       # Your grasshopper definition
├── surface_generator.py        # Your surface_generator implementation
├── agent_builder.py            # Your agent_builder implementation
├── agent_simulator.py          # Your agent_simulator implementation
├── ...                         # Any additional implementation
└── images/                     # Add diagram, intermediary, and final images here
    ├── agent_based.png         # Assignment brief image; Do not delete
    └── ...
```
---
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

![Project overview placeholder](images/a4_overview_placeholder.png)

---

## Table of Contents
- [Overview](#overview)
- [Method](#method)
  - [System Architecture](#system-architecture)
  - [Surface Generation](#surface-generation)
  - [Agent Initialization (Builder)](#agent-initialization-builder)
  - [Agent Sensing and Behavior (Builder Class + Simulator Control)](#agent-sensing-and-behavior-builder-class--simulator-control)
  - [Simulation Loop and Live Sliders](#simulation-loop-and-live-sliders)
  - [Panelization / Mesh Formation](#panelization--mesh-formation)
  - [Pseudo-code](#pseudo-code)
- [Results](#results)
- [Discussion](#discussion)
- [Reproducibility](#reproducibility)
- [AI Use](#ai-use)

---

## Overview

This project develops an **agent-based panelization workflow** on a displaced
surface in Rhino/Grasshopper using modular Python scripts and OOP.

The system is structured as:

1. `surface_generator.py` creates a terrain-like surface from UV-based height
   fields.
2. `agent_builder.py` initializes agents on the surface and assigns structural
   neighborhood links.
3. `agent_simulator.py` advances agents step-by-step and applies live runtime
   force parameters from Grasshopper sliders.
4. `mesh_formation.py` rebuilds a dynamic connectivity mesh from moving points.

The two primary geometric signals used by agents are:

1. **Curvature** (principal curvature direction + magnitude).
2. **Slope** (surface steepness and local slope gradient direction).

These signals are combined with neighbor interaction forces and structural
constraints to produce adaptive panelization behavior over time.

---

## Method

### System Architecture

The implementation follows a modular pipeline where each script has one clear
responsibility:

- `surface_generator.py`: produce `out_surface` and seed points.
- `agent_builder.py`: create `Agent` objects with persistent state.
- `agent_simulator.py`: run step-based updates and apply live slider controls.
- `mesh_formation.py`: construct dynamic topology from current agent positions.

This separation keeps initialization logic independent from simulation controls
and makes iteration inside Grasshopper more stable.

---

### Surface Generation

The base surface is sampled in UV and displaced along normals using one of two
height field modes:

1. Wave + bump field.
2. Random terrain field (multi-octave noise + ridged mixing + macro features).

Key controls include:

- `divU`, `divV` for surface resolution.
- `frequency`, `phase`, `amplitude`, `lift` for displacement shaping.
- `terrain_complexity`, `terrain_steepness` for stochastic terrain structure.

This stage outputs both a reconstructed displaced surface and a point set for
agent seeding.

---

### Agent Initialization (Builder)

`agent_builder.py` handles:

1. Coercion of incoming seed points to `Point3d`.
2. Optional fallback UV grid if no seed points are supplied.
3. Optional slope-biased seed selection.
4. Agent object creation with initial UV, position, velocity, and defaults.
5. Structural neighbor link assignment (grid inference + rest lengths).

Each `Agent` stores:

- Persistent kinematic state (`uv`, `position`, `velocity`).
- Surface-signal state (`curv_dir`, `curv_mag`, `slope_mag`, `slope_seek`).
- Structural constraints (`struct_neighbors`, `struct_rest_lengths`).

---

### Agent Sensing and Behavior (Builder Class + Simulator Control)

The behavior logic is encapsulated in the `Agent` class (`sense`, `decide`,
`move`, `update`) while major gains are updated live from simulator sliders.

Forces currently combined include:

1. Neighbor separation.
2. Cohesion toward local center.
3. Peer slope-follow attraction.
4. Curvature-direction drift.
5. Slope-gradient drift.
6. Home spring toward initial UV.
7. Tangential noise.
8. Structural spring toward rest edge lengths.
9. Structural minimum-distance push.

The movement vector is projected to the surface tangent plane before stepping,
then re-projected to valid UV via `ClosestPoint`.

---

### Simulation Loop and Live Sliders

`agent_simulator.py` provides an edge-triggered step loop (`False -> True` on
`step`) and persistent state via `scriptcontext.sticky`.

Live controls are collected each solve and pushed into each agent through
`apply_runtime_params`, enabling continuous tuning during simulation without
rebuilding the agent set.

Main runtime sliders:

- `max_speed`
- `sep_gain`
- `coh_gain` (or `cohesion_gain`)
- `base_spacing`
- `freedom`
- `struct_spring_gain`
- `struct_min_dist_gain`

---

### Panelization / Mesh Formation

`mesh_formation.py` projects agent points to UV and rebuilds **dynamic Delaunay
triangulation** each solve.

This dynamic topology avoids stale connectivity when agents move significantly,
and outputs:

- `out_mesh` (triangle mesh).
- `out_edges` (mesh edge lines for visual structure).

---

### Pseudo-code

```python
# surface_generator.py
surface = coerce_base_surface(base_surface)
height_field = evaluate_height_field(UV, mode, controls, seed)
displaced_points = displace_along_normal(surface, height_field)
out_surface = rebuild_surface(displaced_points)
out_points = sample_seed_points(displaced_points, point_density)
```

```python
# agent_builder.py
seed_pts = coerce_or_fallback_seed_points(seed_points, surface)
seed_pts = optional_slope_biased_selection(seed_pts, slope_bias, slope_power)
agents = [Agent(surface, uv_from_point(p), max_speed) for p in seed_pts]
assign_structural_links(agents)  # neighbors + rest lengths
return agents
```

```python
# agent_simulator.py
agents_state = sticky_load_or_init(agents_input, reset)
runtime = collect_runtime_params_from_sliders()
for a in agents_state:
    a.apply_runtime_params(runtime)
if rising_edge(step):
    for a in agents_state:
        a.update(agents_state, runtime)
positions, velocity_lines = collect_outputs(agents_state)
sticky_store(agents_state)
```

```python
# agent.update()
sense_surface_signals()         # curvature + slope
compute_neighbor_forces()       # separation, cohesion, peer slope
compute_structural_forces()     # spring + min-distance barrier
blend_forces_and_momentum()
project_to_tangent_and_move()
```

```python
# mesh_formation.py
uv_pts = project_points_to_surface_uv(points)
tris = delaunay_triangulate_2d(normalize_uv(uv_pts))
out_mesh = build_mesh_from_triangles(surface, uv_pts, tris)
out_edges = unique_mesh_edges(out_mesh)
```

---

## Results

### Variation A - Balanced Flocking (Placeholder)

![Variation A placeholder](images/a4_variation_a_placeholder.png)

---

### Variation B - Strong Separation / Open Pattern (Placeholder)

![Variation B placeholder](images/a4_variation_b_placeholder.png)

---

### Variation C - Strong Structural Constraint / Ordered Pattern (Placeholder)

![Variation C placeholder](images/a4_variation_c_placeholder.png)

---

### Agent Trajectories and Field Visualization (Placeholder)

![Trajectories placeholder](images/a4_trajectories_placeholder.png)
![Field visualization placeholder](images/a4_field_placeholder.png)

---

### Final Panelization Outputs (Placeholders)

| View 1 | View 2 |
| --- | --- |
| ![](images/a4_final_panelization_01_placeholder.png) | ![](images/a4_final_panelization_02_placeholder.png) |

| Detail 1 | Detail 2 |
| --- | --- |
| ![](images/a4_final_detail_01_placeholder.png) | ![](images/a4_final_detail_02_placeholder.png) |

---

## Discussion

The workflow balances two needs:

1. **Geometric responsiveness** through curvature and slope sensing.
2. **Topological stability** through structural neighbor constraints and dynamic
   mesh reconstruction.

Moving live force controls into `agent_simulator.py` improved experimentation
speed in Grasshopper, since behavior can be tuned during runtime rather than
requiring rebuilds. Dynamic triangulation in `mesh_formation.py` also reduces
visual artifacts when points drift away from their initial ordering.

Challenges included point overlap, unstable connectivity, and force balancing.
These were addressed through structural min-distance constraints, capped
repulsion, and runtime slider tuning.

---

## Reproducibility

Recommended baseline values used in this setup:

- `sep_gain = 1.85`
- `coh_gain = 0.72`
- `base_spacing = 1.25`
- `freedom = 0.75`
- `struct_spring_gain = 0.65`
- `struct_min_dist_gain = 1.45`

Notes:

1. Keep a fixed `seed` for comparable runs.
2. Use edge-trigger stepping (`step` toggles) in simulator.
3. Reset agents when changing initial conditions (`reset = True` once).
4. Capture at least three slider regimes for final variation comparisons.

---

## AI Use

AI tools were used to assist with:

1. Code refactoring and modular cleanup across builder/simulator scripts.
2. Debugging edge cases in agent update and mesh reconstruction workflows.
3. Structuring and drafting this technical documentation.

All final design decisions, parameter calibration, and visual evaluation were
performed by the student.

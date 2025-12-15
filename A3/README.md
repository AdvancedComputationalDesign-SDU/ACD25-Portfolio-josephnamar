---
layout: default
title: Project Documentation
parent: "A3: Parametric Structural Canopy"
nav_order: 2
nav_exclude: false
search_exclude: false
---

# Assignment 3: Parametric Structural Canopy

[View on GitHub]({{ site.github.repository_url }})

![Example Canopy](images/canopy.jpg)

## Objective

In this assignment you will design and generate a **parametric structural canopy** in **Grasshopper** using the **GhPython (Python 3)** component. You will combine: (1) a **NumPy-driven heightmap** that modulates a NURBS surface, (2) **tessellation** of the resulting surface, and (3) **recursive, branching vertical supports** with controlled randomness. Your goal is to produce a small **family of design solutions** by varying parameters and algorithms, then communicate your process and results in a clear, reproducible report. You are asked to present **three** visually distinct designs. Each design must vary at least **two** of the implemented computational logic (heightmap-based surface geometry, tessellation strategy, branching supports).

---

## Repository Structure

```
A3/
├── index.md                    # Do not edit front matter or content
├── README.md                   # Project documentation; Keep front matter, replace the rest with your project documentation
├── BRIEF.md                    # Assignment brief; Do not edit front matter or content
├── parametric_canopy.py        # Your code implementation
├── parametric_canopy.gh        # Your grasshopper definition
└── images/                     # Add diagram, intermediary, and final images here
    ├── canopy.png              # Assignment brief image; Do not delete
    └── ...
```

---
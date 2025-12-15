---
layout: default
title: Project Documentation
parent: "A2: Exploring Fractals through Recursive Geometric Patterns"
nav_order: 2
nav_exclude: false
search_exclude: false
---

# Assignment 2: Exploring Fractals through Recursive Geometric Patterns

[View on GitHub]({{ site.github.repository_url }})

![Example Fractal](images/branching.png)

## Objective

In this assignment you will implement a **recursive generator** and enrich it with **geometric influences** that shape how the structure grows in space. You will work with geometric primitives (lines, polylines) using **Shapely** and render the results (e.g., with Matplotlib). The core of the assignment is to **couple formal grammar growth with spatial rules** such as attractor/repulsor points, fields, and collision constraints to produce expressive, controllable patterns.

While the branching or growth approach can be inspired by L-systems, it does not have to be strictly L-system based. You are encouraged to explore recursive generation methods influenced by spatial constraints and geometric rules that govern how the fractal develops and interacts with its environment. This opens opportunities to experiment with recursive branching logic, adaptive scaling, and spatial modulation beyond formal grammar rewriting.

---

## Repository structure

```
A2/
├── index.md                    # Do not edit front matter or content
├── README.md                   # Project documentation; Keep front matter, replace the rest with your project documentation
├── BRIEF.md                    # Assignment brief; Do not edit front matter or content
├── fractal_generator.py        # Your code implementation
└── images/                     # Add diagram, intermediary, and final images here
    ├── branching.png           # Assignment brief image; Do not delete
    └── ...
```
---
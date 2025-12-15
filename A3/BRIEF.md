---
layout: default
title: Assignment Brief
parent: "A3: Parametric Structural Canopy"
nav_order: 1
nav_exclude: false
search_exclude: false
---

# Assignment 3: Parametric Structural Canopy

[View on GitHub]({{ site.github.repository_url }})

![Example Canopy](images/canopy.jpg)

## Objective

In this assignment you will design and generate a **parametric structural canopy** in **Grasshopper** using the **GhPython (Python 3)** component. You will combine: (1) a **NumPy-driven heightmap** that modulates a NURBS surface, (2) **tessellation** of the resulting surface, and (3) **recursive, branching vertical supports** with controlled randomness. Your goal is to produce a small **family of design solutions** by varying parameters and algorithms, then communicate your process and results in a clear, reproducible report. You are asked to present **three** visually distinct designs. Each design must vary at least **two** of the implemented computational logic (heightmap-based surface geometry, tessellation strategy, branching supports).

---

## Table of Contents

- [Learning Goals](#learning-goals)
- [Tasks](#tasks)
- [Repository Structure](#repository-structure)
- [Instructions](#instructions)
- [Integration Challenges](#integration-challenges)
- [Submission Guidelines](#submission-guidelines)
- [Evaluation Criteria](#evaluation-criteria)
- [Resources](#resources)
- [Academic Integrity and AI Tool Use](#academic-integrity-and-ai-tool-use)
- [Contact](#contact)

---

## Learning Goals

- Practice **parametric modeling** in Grasshopper with **GhPython**.
- Implement **heightmap generation** in pixel/array space using **continuous mathematical functions** with **NumPy**, and use this 2D array to modulate a NURBS surface.
- Develop a **tessellation strategy** (such as quadrilateral, triangular, diagrid, etc.).
- Build **recursive branching** supports with controllable parameters and **seeded randomness**.
- Use **rhinoscriptsyntax** and/or **Rhino.Geometry (RhinoCommon)** to construct, query, and validate geometry.
- Explore **parameterization, reproducibility**, and clear communication of methods and results.

---

## Tasks

1. **Implement Parametric Canopy Script**

   - Create/complete a Python script (`parametric_canopy.py`) for use inside GhPython to generate a structural canopy.
   - Use **rhinoscriptsyntax** (and optionally **Rhino.Geometry** or other more extensive APIs) to construct geometry. For any external libraries you might need (such as NumPy), at the **top of your script**, add:
     ```python
     #r: numpy
     import numpy as np
     ```
   - Define the parameters of your canopy **explicitly** as Grasshopper inputs. Some of such parameters include but should be adjusted based on your **own** implementation:
     - **Heightmap Parameters**: `amplitude`, `frequency`, `phase`, etc.
     - **Recursion Parameters**: recursion base case, `angle`, `length`, `length_reduction`, `branches`, `angle_variation`, etc.
     - **Tessellation Parameters**: `divU`, `divV`, etc.
   - Allow customization of these parameters to enable exploration of different designs.

2. **Generate Distinct Outputs**

   - Produce **three** visually distinct canopy designs. Each design must vary at least **two** of:
     - (a) **Heightmap**-based surface geometry
     - (b) **Tessellation** strategy
     - (c) **Supports** (recursive branching)

3. **Visualization**
   - Use clear preview styles and/or custom display pipelines. Map thickness/color to signals (depth, curvature, recursion level).
   - Export clean images (axes/UI off) suitable for documentation.
4. **Explore Advanced Concepts**

   - **Extend Tessellations**: explore more advanced tessellation strategies such as voronoi, tangent-plane-intersection (TPI), and/or mixed strategies.
   - **Modify Geometric Rules**: introduce randomness, attractors/repulsors, user input, etc.

5. **Documentation**

   - Present a detailed write-up of your project in `README.md` using a similar structure to the template provided in `TEMPLATE.md`.
   - Include pseudo-code, technical explanations, parameter tables (with any random seeds), and images of your results.
   - Discuss challenges faced and how you addressed them.


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

## Instructions

1. **Clone the Repository**
   - Accept the assignment on GitHub Classroom and clone the repository to your local machine.

2. **Set Up Your Environment**
   - Open Rhino → Grasshopper, place a **GhPython** component, and copy the logic from `parametric_canopy.py`.
   - Configure inputs and outputs for the GhPython component with appropriate variable names and type hinting.

3. **Implement the Canopy**
   - **Implement the Heightmap with NumPy in GhPython**. Build `H(U,V)` using continuous functions and evaluate it vectorially over a UV grid. Sample with the surface’s domains and offset along normals.
   - **Tessellate** the modified surface into a mesh using at least two strategies (quad and triangular). Voronoi/diagrid optional.
   - Implement **Recursive Supports** that branch with parameters (angles, length reductions, depth, branches). Return line/curve geometry for preview.

4. **Customize Parameters**
   - Drive parameters via Grasshopper sliders and value lists. Provide a few **preset parameter sets** in comments and/or as named groups in the GH file.

5. **Generate & Save Outputs**
   - Produce at least **three** distinct variations with varied implementations in at least 2 of the manipulation logic (base surface, tessellation, supports).
   - Export images to `images/` with descriptive names (e.g., `canopy_baseA_quad.png`). Record the parameter sets (and random seeds if used) in your README.

6. **Document**
   - Write your report in **`README.md`** with pseudo-code, parameter tables, discussion of methods, and the resulting images.

7. **Version Control**
   - Make regular commits with meaningful messages and push to your repository.

8. **Review & Finalize**
   - Ensure code runs without errors, is readable, and clearly parameterized.

---

## Integration Challenges

Focus on these specific integration issues and address them in your report.

- **Heightmap → Surface Mapping & Scaling**  
  Map pixel indices `(i, j)` to surface parameters `(u, v)` and sample points/normals in surface space.  
  *Use:* `rs.SurfaceDomain`, `rs.EvaluateSurface`, `rs.SurfaceClosestPoint`, `rs.SurfaceNormal`, `rs.SurfaceFrame`.  

- **Branch–Surface Intersections & Graceful Attachment**  
  Ensure branch endpoints intersect or snap to the tessellated canopy; align the final segment with the generated surface; avoid gaps.  
  *Hints*: `rs.CurveSurfaceIntersection`, `rs.CurveBrepIntersect`, `rs.CurveMeshIntersection`, `rs.ProjectPointToMesh`, `rs.ProjectCurveToMesh`, `rs.CurveEndPoint`, `rs.CurveClosestPoint`.

- **Geometry Thickness (Optional)**  
  Give physical thickness to panels and supports.  
  *Hints*: supports → `rs.AddPipe` (vary radii by depth/curvature); NURBS canopies → `rs.OffsetSurface`; meshes → use RhinoCommon mesh offset/duplication with normal displacements, then join/weld.

---

## Submission Guidelines

**What to Submit**
  - Your `parametric_canopy.py` script.
  - Your Grasshopper definition file `parametric_canopy.gh`.
  - Completed `README.md` with pseudo-code, explanations, and images.
  - Generated images saved in the `images/` folder.

---

## Evaluation Criteria

- **Implementation & Functionality**
  - Effective and correct use of Rhino.Geometry APIs.
  - Working canopy pipeline: **Heightmap** → NURBS Surface → **Tessellation** → **Supports**.
- **Design Exploration**
  - Diversity and quality of variations; clarity of visual communication.
- **Technical Understanding**
  - Sound parameterization; clear pseudo-code and explanations.
- **Code Quality**
  - Readability, organization, meaningful names, comments.
- **Documentation**
  - Thorough, reproducible `README.md` with images and parameter tables.
- **Use of Git**
  - Regular, meaningful commits; organized repo.
- **Bonus**
  - Any Advanced Challenge implementation.

---

## Resources

- **Rhino & Grasshopper**
  - Rhino.Python Guides: https://developer.rhino3d.com/guides/rhinopython/
  - rhinoscriptsyntax: https://developer.rhino3d.com/api/rhinoscriptsyntax/
  - RhinoCommon SDK: https://developer.rhino3d.com/api/RhinoCommon/html/N_Rhino_Geometry.htm
- **Surface Tessellations**
  - Voronoi Diagrams: https://en.wikipedia.org/wiki/Voronoi_diagram
  - Delaunay Triangulation: https://en.wikipedia.org/wiki/Delaunay_triangulation
  - Diagrid: https://en.wikipedia.org/wiki/Diagrid

---

## Academic Integrity and AI Tool Use
- You may use AI tools for **boilerplate, refactoring, linting, and debugging**. If you do, you must:
  1. **Cite** the tools and prompts you used in your `README.md` under a short **AI Acknowledgments** subsection.
  2. Keep **algorithmic choices** and the **core implementation** your own. Do not submit turnkey solutions.
  3. Be prepared to **explain any part of your code** (live or written). You may be asked to walk through it.
- **Prohibited**: uncredited copying from classmates or the internet; submitting code/images you do not understand; using AI to generate the entire assignment without substantive modification.

## Contact

If you have any questions or need assistance, please reach out via email or the course forum.

---

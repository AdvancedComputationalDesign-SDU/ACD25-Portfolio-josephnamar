---
layout: default
title: Assignment Brief
parent: "A2: Exploring Fractals through Recursive Geometric Patterns"
nav_order: 1
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

## Table of Contents

- [Learning Goals](#learning-goals)
- [Tasks](#tasks)
- [Getting Started](#getting-started)
- [Repository Structure](#repository-structure)
- [Instructions](#instructions)
- [Advanced Challenges (Optional for Extra Points)](#advanced-challenges-optional-for-extra-points)
- [Submission Guidelines](#submission-guidelines)
- [Evaluation Criteria](#evaluation-criteria)
- [Resources](#resources)
- [Contact](#contact)

---

### Learning goals

- Design and implement a recursive generator (e.g., L-system or direct branching) and geometric interpretation pipeline.
- Combine **symbolic rules** with **spatial reasoning** (distance, intersection, fields).
- Practice recursion, parameterization, and reproducible randomness.
- Communicate methodology and results clearly.
- Develop awareness of how spatial rules (fields, attractors, obstacles) can modulate recursive growth processes.

---

## Tasks

1. **Implement Recursive Generator**

   - Create a Python script (`fractal_generator.py`) that uses recursive functions to generate fractal patterns. This can be based on L-system–style string rewriting or direct recursive branching logic.
   - Use the **Shapely** library to create and manipulate geometric objects, specifically for drawing lines and polylines.
   - Define the parameters of your fractal explicitly in your script. Examples include:
     - **Starting Point**: The initial coordinate from which the pattern generation starts.
     - **Initial Angle**: The starting orientation of the pattern.
     - **Angle Change**: The angle by which the direction changes at each recursive step.
     - **Length**: The initial length of the lines drawn.
     - **Length Scaling Factor**: How the length of lines changes with each recursion.
     - **Recursion Depth**: The number of times the recursive function calls itself.
   - Allow customization of these parameters to enable exploration of different fractal patterns.
   - Incorporate randomness to increase visual complexity, and use a fixed seed for reproducibility:
    
      ```python
      import random
      random.seed(42)  # set and record this per output
      ```

2. **Geometric Influences**

   - Integrate at least two types of spatial influences into your recursive generator. Examples include:
     - Attractors and Repulsors: Points or regions that pull or push growth directions.
     - Fields: Scalar or vector fields influencing direction or length.
     - Region-Aware Rules: Growth constrained within or outside specific areas.
     - Obstacles/Clipping: Preventing intersections or pruning branches.
     - Self-Avoidance: Avoiding self-intersections or overlap.
     - Adaptive Recursion: Modulating recursion depth or branching based on spatial context.
   - These influences should meaningfully affect the fractal's structure and appearance.

3. **Generate Distinct Outputs**

   - Produce at least **four distinctly different fractal patterns** by varying parameters and geometric influences.
   - Save each output as an image in the `images/` folder with descriptive filenames.
   - Record the parameter sets and random seeds used for each output to ensure reproducibility.

4. **Visualization and Appearance Mapping**

   - Use Matplotlib to plot your fractal patterns.
   - Map visual appearance attributes such as color and stroke thickness to meaningful signals like recursion depth, curvature, or distance to attractors.
   - Enhance your visualizations with custom color schemes or gradients to improve interpretability and aesthetics.
   - When saving, export a clean, tight image (not a full UI figure): hide axes/margins and save tightly.
  
      ```python
      import matplotlib.pyplot as plt
      fig, ax = plt.subplots()
      # ... draw your geometry on ax ...
      ax.set_aspect('equal', adjustable='box')
      ax.axis('off')
      plt.margins(0)
      plt.savefig('images/output.png', bbox_inches='tight', pad_inches=0, dpi=300)
      plt.close(fig)
      ```

5. **Experiments**

   - Systematically explore how different combinations of parameters and geometric influences affect the fractal outcomes.
   - Document your observations and insights regarding the interplay between recursive growth and spatial modulation.

6. **Documentation**

   - Write detailed pseudo-code explaining your recursive functions in `README.md` using a similar structure to the template provided in `TEMPLATE.md`.
   - Provide technical explanations of your algorithms and geometric influences.
   - Include a short report discussing the process and the mathematical principles behind the fractals you created.
   - Insert images of your generated fractals into the documentation.
   - Discuss challenges faced and how you addressed them.

---

## Getting Started

### Prerequisites

- **Python 3.x**
- **Shapely**
- **Matplotlib**
- **NumPy**

For 3D visualization or advanced features, you may also need:

- **mpl_toolkits.mplot3d** (comes with Matplotlib)
- **Plotly** (for interactive 3D plots)

### Suggested Structure

- Maintain state variables such as position, heading (angle), current length, and scaling factor.
- Use a branching stack to manage recursive calls and return points.
- Employ Shapely for geometric operations like line creation, intersection tests, attractor distance calculations, and containment queries.
- Structure your code to cleanly separate recursion logic, spatial influence computations, and visualization.

## Repository Structure

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

Requirements highlight: generate **four** distinct outputs, use randomness with a fixed seed recorded for reproducibility, and save only the generated image (tight layout, axes off).

---

## Instructions

1. **Clone the Repository**

   - Accept the assignment on GitHub Classroom and clone the repository to your local machine using GitHub Desktop or the command line.

2. **Set Up Your Environment**

   - Ensure all dependencies are installed.
   - Familiarize yourself with the repository structure.

3. **Implement the Recursive Generator**

   - Open `fractal_generator.py`.
   - Define parameters explicitly: starting point, initial angle, angle change, length, length scaling factor, recursion depth.
   - Implement recursive branching logic that creates line segments and updates position and orientation.
   - Use Shapely for geometric operations.
   - Implement at least two geometric influences from the list provided (e.g., attractors, obstacles, fields).
   - Map visual appearance attributes (color, stroke thickness) to meaningful signals such as recursion depth or distance to attractors.

4. **Generate and Save Outputs**

   - Run your script with different parameter sets and geometric influences to generate at least four distinct fractal patterns.
   - Save each output image in the `images/` folder with descriptive filenames.
   - Record the parameter sets and random seeds for each output to ensure reproducibility.

5. **Documentation**

   - Write detailed pseudo-code and explanations in `README.md`.
   - Describe your recursive functions, geometric influences, and visualization mappings.
   - Include images of your fractals with commentary.

6. **Version Control with Git**

   - Make regular commits with meaningful messages.
   - Push your commits to the GitHub repository.

7. **Review and Finalize**

   - Ensure your code is well-commented and clean.
   - Verify that all generated images are saved correctly.
   - Double-check your documentation for clarity and completeness.

---

## Advanced Challenges (Optional for Extra Points)

### Extending to 3D Space

- **Implement 3D Fractals**:
  - Introduce a Z-axis and modify your recursive function to handle 3D coordinates.
  - Adjust geometric transformations to include rotations around X, Y, and Z axes.
  - Handle position and orientation in 3D space.

- **Visualizing in 3D**:
  - Use `mpl_toolkits.mplot3d` in Matplotlib:

    ```python
    from mpl_toolkits.mplot3d import Axes3D
    import matplotlib.pyplot as plt

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.plot(xs, ys, zs)
    plt.show()
    ```

  - Or use `plotly` for interactive 3D plots:

    ```python
    import plotly.graph_objects as go

    fig = go.Figure(data=[go.Scatter3d(x=xs, y=ys, z=zs, mode='lines')])
    fig.show()
    ```

### Custom Color Schemes

- **Color Based on Depth**:

  ```python
  import matplotlib.pyplot as plt

  def get_color(depth, max_depth):
      return plt.cm.viridis(depth / max_depth)

  # Plot using the color
  color = get_color(current_depth, max_depth)
  ```

- **Color Gradients**:
  - Use color maps to apply gradients along the lines.
  - Consider using libraries like `matplotlib.colors` for advanced color manipulations.

### Advanced Base Cases for Recursion

- Explore alternative termination conditions beyond fixed recursion depth, such as:
  - Proximity to a goal/attractor (terminate when distance < ε).
  - Local density threshold (terminate when nearby segments exceed a count or length per area).
  - Curvature/turn-limit based termination (stop when cumulative bend exceeds a budget).
  - Proximity to obstacles or boundaries (terminate or reroute when within a buffer).

---

## Submission Guidelines

- **What to Submit**:
  - Your `fractal_generator.py` script and any additional scripts.
  - Completed `README.md` with pseudo-code, explanations, and short report (copied from your `TEMPLATE.md` draft).
  - Generated images saved in the `images/` folder.

- **Submission Checklist**:
  - [ ] Code runs without errors.
  - [ ] Code is well-commented and follows best practices (e.g., consistent naming conventions).
  - [ ] At least two geometric influences are implemented and explained.
  - [ ] Appearance mapping (color, stroke thickness) is linked to meaningful signals.
  - [ ] At least four distinct fractal images are saved, with parameter sets and random seeds recorded for reproducibility.
  - [ ] `README.md` is complete and thorough.
  - [ ] All changes are committed with meaningful messages.
  - [ ] All commits are pushed to your GitHub repository.

---

## Evaluation Criteria

- **Implementation of Recursive Functions**
  - Correct use of recursion in generating fractal patterns using geometric transformations with Shapely.
  - Ability to customize parameters and generate different outputs.

- **Geometric Influences**
  - Quality, correctness, and meaningful integration of at least two spatial influences.
  - Demonstrated understanding of how spatial rules modulate growth.

- **Visualization**
  - Clear, informative mapping of color/line width/opacity to signals (depth, curvature, distance to features).
  - Legible composition and export (axes off, tight bounds).

- **Documentation**
  - Detailed pseudo-code and technical explanations.
  - Clear discussion of algorithms, parameters, and geometric influences. Feel free to include diagrams to explain your geometric rules.
  - Inclusion and analysis of generated fractal images.

- **Variety and Control**
  - Ability to produce diverse fractal outputs through parameter and influence variation.
  - Reproducibility ensured by recording parameters and random seeds.

- **Use of Git and Version Control**
  - Regular commits with meaningful messages.
  - Proper repository structure and organization.

- **Bonus**
  - Explore advanced challenges:
    - Extension to 3D fractals.
    - Animated fractal generation or interactive visualizations.

---

## Resources

- **Python Official Documentation**: [https://docs.python.org/3/](https://docs.python.org/3/)
- **Shapely Documentation**: [https://shapely.readthedocs.io](https://shapely.readthedocs.io)
- **Matplotlib Documentation**: [https://matplotlib.org/stable/contents.html](https://matplotlib.org/stable/contents.html)
- **NumPy Documentation**: [https://numpy.org/doc/](https://numpy.org/doc/)
- **Plotly Documentation**: [https://plotly.com/python/](https://plotly.com/python/)
- **L-Systems**: [https://en.wikipedia.org/wiki/L-system](https://en.wikipedia.org/wiki/L-system)

---

## Contact

If you have any questions or need assistance, please reach out to the instructor via email or the course forum.

---

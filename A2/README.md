# A2 — Recursive Fractal System (Dragon Curve)

This assignment implements a **recursive** generator for the *Heighway dragon curve* and explores how the curve changes under **geometric influences** while keeping outputs reproducible via a fixed random seed.

## What this script does

1. **Recursive turn-sequence generation**
   - A turn sequence is generated recursively (L/R turns) using the standard dragon-curve recursion:
     - `S(n) = S(n-1) + [L] + invert(reverse(S(n-1)))`

2. **Polyline construction**
   - The turn sequence is converted into a polyline (list of points), stepped on a 2D grid.

3. **Geometric influences (variants)**
   - **baseline**: pure recursive dragon curve (no constraints)
   - **self_avoid**: skips steps that would self-intersect (segment intersection check using Shapely)
   - **attractor**: a *soft* steering influence biases turn decisions toward an attractor point (probabilistic flip)
   - **attractor_self_avoid**: combines attractor bias with self-intersection avoidance

4. **Reproducibility**
   - `SEED` controls all stochastic decisions.
   - For the attractor variants, the seed is reset before each run so that increasing iteration counts behave like a consistent “growth” of the same biased system.

## How to run

From the `A2/` folder:

```bash
python fractal_generator.py
```

Outputs are written to:

```
A2/images/
```

## Dependencies

- `numpy`
- `matplotlib`
- `shapely`

If you are running inside the course conda environment, install as needed:

```bash
conda install numpy matplotlib
pip install shapely
```

## Parameters (top of script)

- `SEED = 42`  
  Fixed seed for reproducibility.

- `ITERATION_LIST = [3, 7, 10, 15]`  
  Generates outputs for multiple recursion depths.

- `AVOID_SELF` and `STOP_ON_COLLISION`  
  Controls self-intersection behavior (`STOP_ON_COLLISION=False` skips colliding segments and continues).

- `ATTRACTOR = (20.0, 20.0)` and `BIAS_STRENGTH = 0.35`  
  Controls the attractor position and steering strength. Higher strength increases the chance of flipping a planned turn when doing so better aligns with the attractor direction.

## Output files

Filenames are generated automatically from the figure title:

```
<variant>_iterations<N>_seed<SEED>.png
```

Variants produced per iteration:
- `baseline`
- `self_avoid`
- `attractor`
- `attractor_self_avoid`

## Results

### Iteration 15 (comparison of all variants)

**Baseline**
![](images/baseline_iterations15_seed42.png)

**Self-avoid**
![](images/self_avoid_iterations15_seed42.png)

**Attractor**
![](images/attractor_iterations15_seed42.png)

**Attractor + Self-avoid**
![](images/attractor_self_avoid_iterations15_seed42.png)

### Attractor + Self-avoid growth across iterations

Iteration 3  
![](images/attractor_self_avoid_iterations3_seed42.png)

Iteration 7  
![](images/attractor_self_avoid_iterations7_seed42.png)

Iteration 10  
![](images/attractor_self_avoid_iterations10_seed42.png)

Iteration 15  
![](images/attractor_self_avoid_iterations15_seed42.png)

## Notes on interpretation

- The **baseline** curve is entirely determined by the recursion.
- **Self-avoid** introduces a hard geometric constraint by rejecting segments that would intersect existing geometry.
- **Attractor bias** introduces a soft geometric influence by probabilistically altering turn choices when a flipped turn better aligns with the attractor direction.
- The combined **attractor_self_avoid** output demonstrates how recursive growth can be shaped by both soft and hard spatial rules.

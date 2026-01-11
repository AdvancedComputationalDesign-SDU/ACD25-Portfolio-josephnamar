# A2 — Recursive Fractal System (Dragon Curve)

This assignment implements a recursive generator for the **Heighway Dragon Curve** and then modifies the resulting growth using two geometric rules:
1) a **hard constraint** that avoids self-intersections, and  
2) a **soft steering bias** that attracts the growth toward a target point.

The script generates and saves four variants (**baseline**, **self_avoid**, **attractor**, **attractor_self_avoid**) for multiple recursion depths (**iterations = 3, 7, 10, 15**).

---

## Core logic (shared by all variants)

### 1) Recursive turn sequence (the “DNA”)
The dragon curve is defined by a turn sequence of **left/right 90° turns**.  
Your function `dragon_turns(n)` builds this sequence recursively:

- Let `S(n)` be the turn sequence at iteration `n`
- Base case: `S(0) = []`
- Recurrence:
  - `S(n) = S(n-1) + [L] + invert(reverse(S(n-1)))`

In the code:
- `+1` encodes a **left turn**
- `-1` encodes a **right turn**
- `invert` is implemented by multiplying turns by `-1`

This recursion is the reason the curve shows self-similarity as iterations increase.

### 2) Walking the turns into geometry (polyline)
`build_points(...)` converts the turn list into a **polyline**:

- The walker starts at `(0, 0)`
- It takes an initial step forward
- For each turn `t`:
  - update heading by `t` (left/right)
  - take one step of length `STEP`
  - append the new point

This yields a list of points, rendered as connected line segments.

---

## Variants (what changes between outputs)

### A) `baseline`
**Goal:** show the pure recursive system with no spatial rules.  
**Logic:** uses `build_points(...)` with no attractor and no self-avoidance.  
**Result:** the canonical dragon curve for each iteration count.

### B) `self_avoid`
**Goal:** apply a **hard geometric constraint**: do not draw segments that would intersect existing segments.  
**Logic:** before accepting a candidate segment, the script checks intersection against all previous segments (excluding the most recent one, which shares an endpoint).  
If a collision is detected:
- `STOP_ON_COLLISION = False` (your setting): the step is **skipped** and the walk continues.

**Result:** the recursion still drives the system, but the geometry is “pruned” by spatial feasibility.

### C) `attractor`
**Goal:** apply a **soft steering influence** toward a fixed point `ATTRACTOR = (20, 20)`.  
**Logic:** for each turn decision, the script compares:
- the **planned** turn (from the recursive sequence)
- the **flipped** turn (left ↔ right)

It computes which choice aligns better with the direction vector pointing toward the attractor.  
If the flipped option improves alignment, it flips the turn with probability:

- `p_flip = min(1, BIAS_STRENGTH * improvement / 2)`

where `improvement` is the increase in alignment score (in the range `[0, 2]`).

**Result:** the curve remains mostly dragon-like, but exhibits a consistent drift influenced by the attractor.

### D) `attractor_self_avoid`
**Goal:** combine both influences:
- soft attractor steering
- hard self-intersection avoidance

**Logic order in the script:**
1) decide whether to flip the turn using the attractor rule  
2) test the resulting candidate segment for self-intersection  
3) if it collides, skip it (with your current settings)

**Result:** the most constrained output: recursion + steering + collision pruning.

---

## Reproducibility (seed use)

- `SEED` controls the stochastic turn-flips in the attractor variants.
- The script explicitly resets the seed before each attractor run (`np.random.seed(SEED)`), so that:
  - iteration 7 behaves like “iteration 3 continued”
  - iteration 10 behaves like “iteration 7 continued”, etc.

This makes the attractor-based series comparable across recursion depths.

---

## How to run

From inside the `A2/` folder:

```bash
python fractal_generator.py
```

Images are saved into:

```
A2/images/
```

---

## Output gallery (all variants × all iterations)

Filenames are generated automatically by the script as:

`<variant>_iterations<N>_seed42.png`

### Iteration 3

| baseline | self_avoid |
| --- | --- |
| ![](images/baseline_iterations3_seed42.png) | ![](images/self_avoid_iterations3_seed42.png) |

| attractor | attractor_self_avoid |
| --- | --- |
| ![](images/attractor_iterations3_seed42.png) | ![](images/attractor_self_avoid_iterations3_seed42.png) |

### Iteration 7

| baseline | self_avoid |
| --- | --- |
| ![](images/baseline_iterations7_seed42.png) | ![](images/self_avoid_iterations7_seed42.png) |

| attractor | attractor_self_avoid |
| --- | --- |
| ![](images/attractor_iterations7_seed42.png) | ![](images/attractor_self_avoid_iterations7_seed42.png) |

### Iteration 10

| baseline | self_avoid |
| --- | --- |
| ![](images/baseline_iterations10_seed42.png) | ![](images/self_avoid_iterations10_seed42.png) |

| attractor | attractor_self_avoid |
| --- | --- |
| ![](images/attractor_iterations10_seed42.png) | ![](images/attractor_self_avoid_iterations10_seed42.png) |

### Iteration 15

| baseline | self_avoid |
| --- | --- |
| ![](images/baseline_iterations15_seed42.png) | ![](images/self_avoid_iterations15_seed42.png) |

| attractor | attractor_self_avoid |
| --- | --- |
| ![](images/attractor_iterations15_seed42.png) | ![](images/attractor_self_avoid_iterations15_seed42.png) |

---

## Parameters used for these results

- `SEED = 42`
- `STEP = 1.0`
- `ITERATION_LIST = [3, 7, 10, 15]`
- `ATTRACTOR = (20.0, 20.0)`
- `BIAS_STRENGTH = 0.35`
- `STOP_ON_COLLISION = False`

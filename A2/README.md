# A2 — Recursive Fractal System (Dragon Curve)

This assignment explores a **recursive fractal system** based on the *Heighway dragon curve* and investigates how introducing **geometric constraints and spatial bias** alters recursive growth.

The script generates and saves four variants (**baseline**, **self_avoid**, **attractor**, **attractor_self_avoid**) for multiple recursion depths (**iterations = 3, 7, 10, 15**).

---

## Core logic (shared by all variants)

### 1) Recursive turn sequence (the “DNA”)
The dragon curve is defined by a turn sequence of **left/right 90° turns**.  
`dragon_turns(n)` builds this sequence recursively:

- Base: `S(0) = []`
- Recurrence:
  - `S(n) = S(n-1) + [L] + invert(reverse(S(n-1)))`

In the code:
- `+1` encodes a **left** turn
- `-1` encodes a **right** turn
- `invert` is implemented by multiplying turns by `-1`

For the baseline dragon curve:
- Turn count at iteration `n` is `2^n − 1`
- Segment count is `2^n` (initial step + one segment per turn)

### 2) Walking the turns into geometry (polyline)
`build_points(...)` converts the turn list into a polyline:

- Start at `(0, 0)` with an initial forward step
- For each turn:
  - update heading (E/N/W/S)
  - take one step of length `STEP`
  - append the new point

The polyline is rendered as connected line segments.

---

## Variants (what changes between outputs)

### A) `baseline`
**Pure recursion.**  
All turns are executed exactly as defined by the recursion. No turns are modified or rejected.

### B) `self_avoid`
**Hard geometric constraint.**  
Each candidate segment is checked against previous segments. If an intersection is detected:
- `STOP_ON_COLLISION = False`: the step is **skipped** and growth continues.

**Why iteration 15 can look like iteration 10:**  
Once the geometry reaches a state where **every remaining candidate step would collide**, growth cannot add new valid segments. At that point, increasing the iteration count does not increase realized geometry.

### C) `attractor`
**Soft spatial bias.**  
For each recursive turn, the algorithm evaluates the planned turn versus its flipped alternative (L ↔ R). If flipping improves alignment with the direction toward the attractor point, the turn is flipped with probability:

- `p_flip = min(1, BIAS_STRENGTH * improvement / 2)`

This treats recursion as a **proposal** and introduces controlled stochastic deviation.

**Why baseline iteration 15 does not match attractor iteration 15:**  
Baseline executes the canonical `2^15 − 1` turns deterministically.  
Attractor modifies turns during growth, breaking strict self-similarity and producing a different spatial trajectory and density.

### D) `attractor_self_avoid`
**Combined rules.**
1) optional turn flip (attractor bias)  
2) collision test (self-avoid)  
3) skip colliding steps

This produces the strongest divergence and can also saturate early if no collision-free steps remain.

---

## Reproducibility
- `SEED` controls all stochastic decisions.
- The seed is reset before each attractor-based run so that increasing iteration depth behaves like consistent “growth” of the same biased system.

---

## How to run

From inside the `A2/` folder:

```bash
python fractal_generator.py
```

Images are saved to:

```
A2/images/
```

---

## Output gallery (all variants × all iterations)

Filenames follow:

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
- `AVOID_SELF = True`
- `STOP_ON_COLLISION = False`
- `ATTRACTOR = (20.0, 20.0)`
- `BIAS_STRENGTH = 0.35`

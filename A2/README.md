# A2 — Recursive Fractal System (Dragon Curve)

This assignment explores a **recursive fractal system** based on the *Heighway dragon curve* and investigates how introducing **geometric constraints and spatial bias** alters recursive growth.

The work intentionally compares **deterministic recursion** with **rule-modified recursion**, showing how small local decisions propagate into large-scale geometric differences.

---

## 1. Baseline: Pure recursive dragon curve

### Logic
The baseline implementation follows the classic recursive definition of the dragon curve:

S(n) = S(n−1) + [L] + invert(reverse(S(n−1)))

- Each iteration doubles the previous sequence and inserts a single left turn.
- The number of turns at iteration n is 2^n − 1.
- Every turn produces exactly one segment.
- No turns are skipped, modified, or rejected.

### Consequences
- The geometry is fully deterministic.
- For a fixed iteration count and seed, the output is always identical.
- Iteration depth directly controls geometric complexity.

At iteration 15, the baseline produces a very dense, space-filling curve because all recursive turns are executed.

---

## 2. Self-avoidance: Hard geometric constraint

### Logic
The self-avoid variant introduces a collision check before committing each new segment.

- Each candidate segment is tested against all previous segments.
- If an intersection is detected, the step is rejected.
- When STOP_ON_COLLISION = False, the system skips the colliding step and attempts to continue.

### Consequences
- The recursion is still generated, but not all turns are realized geometrically.
- Once the curve reaches a configuration where every remaining turn would cause a collision, growth can no longer proceed.

### Important observation
For higher iteration counts (e.g. 15):

- The self-avoid version often terminates early.
- Iteration 15 may produce the same geometry as iteration 10 because no further valid steps exist.
- This is not a bug. It is a geometric saturation effect caused by strict self-intersection avoidance.

---

## 3. Attractor: Soft spatial bias

### Logic
The attractor variant introduces a probabilistic steering influence toward a fixed point in space.

For each recursive turn:
- The algorithm compares the planned turn with its flipped alternative.
- Both options are evaluated based on alignment with the attractor direction.
- A probability of flipping the turn is computed using BIAS_STRENGTH.

Key point:
- The recursive turn sequence is treated as a proposal, not a rule.

### Consequences
- The recursion is no longer strictly deterministic.
- Small turn changes at early iterations propagate exponentially.
- The curve spreads outward toward the attractor instead of folding inward.

### Why iteration 15 differs from the baseline
Although both are labeled “iteration 15”:

- Baseline executes all 2^15 − 1 turns exactly as defined.
- Attractor alters turn decisions dynamically, breaking self-similarity.

As a result:
- The number, placement, and density of visible segments differ.
- The attractor curve is not expected to match or build on the baseline.

---

## 4. Attractor + self-avoid: Combined rules

### Logic
This variant combines:
- Soft influence (attractor bias)
- Hard constraint (self-intersection avoidance)

The algorithm:
1. Proposes a recursive turn
2. Optionally flips it based on attractor alignment
3. Rejects the step if it causes a collision

### Consequences
- Growth becomes highly path-dependent.
- Some recursive steps are modified; others are skipped entirely.
- The curve may terminate early once no valid steps remain.

---

## 5. Reproducibility

- A fixed random seed (SEED = 42) is used.
- For attractor-based runs, the seed is reset before each variant.
- This guarantees identical results across runs while still allowing stochastic behavior.

---

## 6. Results

### Baseline (iteration 15)
![](images/baseline_iterations15_seed42.png)

### Self-avoid (iteration 15 — early termination)
![](images/self_avoid_iterations15_seed42.png)

### Attractor (iteration 15)
![](images/attractor_iterations15_seed42.png)

### Attractor + self-avoid (iteration 15)
![](images/attractor_self_avoid_iterations15_seed42.png)

### Attractor + self-avoid across iterations
Iteration 3  
![](images/attractor_self_avoid_iterations3_seed42.png)

Iteration 7  
![](images/attractor_self_avoid_iterations7_seed42.png)

Iteration 10  
![](images/attractor_self_avoid_iterations10_seed42.png)

Iteration 15  
![](images/attractor_self_avoid_iterations15_seed42.png)

---

## 7. Key takeaway

- Recursion alone produces predictable, self-similar structures.
- Hard constraints can prematurely terminate recursive growth.
- Soft biases reshape recursion without explicit rules.
- Combining both leads to emergent, non-trivial geometries.

Iteration depth alone does not guarantee comparable results once recursion is influenced by spatial rules.

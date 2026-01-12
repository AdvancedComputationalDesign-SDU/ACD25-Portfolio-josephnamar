import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from shapely.geometry import LineString

"""
Assignment A2 – Fractal Generator

This script generates 2D dragon-curve based fractal patterns using a recursive
turn sequence and a turtle-style path construction. Several controlled
variations are produced to explore constraints (self-avoidance) and steering
effects (attractor bias).

Output is visualized or saved depending on MODE.
"""

# =========================
# GLOBAL CONFIGURATION
# =========================
# Execution mode: visualize ("vis") or save images ("save")
MODE = "save"   # "vis" or "save"
# Random seed for reproducible stochastic behavior
SEED = 42
# Iteration counts to generate (higher = more segments)
ITERATION_LIST = [3, 7, 10, 15]
# Step length per move
STEP = 1.0

# Self-intersection control
AVOID_SELF = True          # True: avoid self-intersection, False: allow self-intersection
STOP_ON_COLLISION = False  

# Attractor bias parameters
USE_ATTRACTOR = True
ATTRACTOR = (20.0, 20.0)   # move this to shape composition
# Strength of attractor influence (0 = none, 1 = strong)
BIAS_STRENGTH = 0.35       # 0.2 subtle, 0.35 good, 0.6 strong



OUT_DIR = os.path.join(os.path.dirname(__file__), "images")
BASE_TITLE = "Dragon curve"

os.makedirs(OUT_DIR, exist_ok=True)
np.random.seed(SEED)


# =========================
# OUTPUT TITLE
# =========================
def make_title(base):
    return f"{base} | iterations={ITERATIONS} | seed={SEED}"


# =========================
# FRACTAL RULE GENERATION
# =========================
def dragon_turns(n):
    if n <= 0:
        return []
    prev = dragon_turns(n - 1)
    inv_rev = [-t for t in reversed(prev)]
    # 0:E, 1:N, 2:W, 3:S
    return prev + [1] + inv_rev 


# =========================
# PATH CONSTRUCTION
# =========================
def build_points(turns, step=1.0, avoid_self=False, stop_on_collision=True,
                 use_attractor=False, attractor=(0.0, 0.0), bias_strength=0.0):
    """
    Build a polyline from a dragon-curve turn sequence.
    """

    # Current heading (0=E, 1=N, 2=W, 3=S)
    heading = 0  
    x, y = 0.0, 0.0
    pts = [(x, y)]

    def step_vec(h):
        if h == 0:
            return (step, 0.0)
        if h == 1:
            return (0.0, step)
        if h == 2:
            return (-step, 0.0)
        return (0.0, -step)

    # Store previous segments for collision checks
    segments = []

    dx, dy = step_vec(heading)
    x2, y2 = x + dx, y + dy

    x, y = x2, y2
    pts.append((x, y))
    segments.append(((0.0, 0.0), (x2, y2)))

    for t in turns:

        t_use = t

        if use_attractor and bias_strength > 0.0:
            # Optional steering toward attractor
            ax, ay = attractor

            h_planned = (heading + t) % 4
            h_flipped = (heading - t) % 4

            dx_p, dy_p = step_vec(h_planned)
            dx_f, dy_f = step_vec(h_flipped)

            vx, vy = ax - x, ay - y
            n = (vx * vx + vy * vy) ** 0.5
            if n > 1e-9:
                vx, vy = vx / n, vy / n
            else:
                vx, vy = 0.0, 0.0

            score_p = dx_p * vx + dy_p * vy
            score_f = dx_f * vx + dy_f * vy

            improvement = max(0.0, score_f - score_p)
            p_flip = min(1.0, bias_strength * (improvement / 2.0))

            if np.random.rand() < p_flip:
                t_use = -t


        heading = (heading + t_use) % 4
        dx, dy = step_vec(heading)
        nx, ny = x + dx, y + dy


        if avoid_self:
            # Collision check against previous segments
            cand = LineString([(x, y), (nx, ny)])

            collision = False
            for (p0, p1) in segments[:-1]:
                old = LineString([p0, p1])
                if cand.intersects(old):
                    collision = True
                    break

            if collision:
                if stop_on_collision:
                    break
                else:
                    continue

        segments.append(((x, y), (nx, ny)))
        x, y = nx, ny
        pts.append((x, y))

    return pts



# =========================
# OUTPUT (VISUALIZE OR SAVE)
# =========================
def output(points, out_path=None, title=None):
    """
    Render the polyline and visualize or save the result.
    """
    # Build line segments
    segments = [[points[i], points[i + 1]] for i in range(len(points) - 1)]
    values = np.arange(len(segments))

    lc = LineCollection(segments, cmap="viridis", linewidth=1.0)
    lc.set_array(values)

    # Set up figure and axes
    fig, ax = plt.subplots()
    ax.add_collection(lc)
    ax.set_aspect("equal", adjustable="box")
    ax.autoscale()
    ax.axis("off")

    full_title = make_title(BASE_TITLE)

    fig.text(
        0.5,
        0.02,
        full_title,
        ha="center",
        va="center",
        fontsize=9
    )
    # Show or save depending on MODE
    if MODE == "vis":
        plt.show()
        plt.close(fig)
    elif MODE == "save":
        filename = full_title.replace(" ", "").replace("|", "_").replace("=", "")
        out_path = os.path.join(OUT_DIR, f"{filename}.png")
        fig.savefig(out_path, dpi=300, bbox_inches="tight", pad_inches=0.1)
        plt.close(fig)
        print(f"Saved: {out_path}")
    else:
        plt.close(fig)
        raise ValueError("MODE must be 'vis' or 'save'")


# =========================
# MAIN EXECUTION
# =========================
if __name__ == "__main__":

    for i in ITERATION_LIST:
        ITERATIONS = i
        turns = dragon_turns(ITERATIONS)

        # Baseline
        BASE_TITLE = "baseline"
        points = build_points(turns, step=STEP, avoid_self=False)
        output(points)

        # Self-avoid
        BASE_TITLE = "self_avoid"
        points = build_points(turns, step=STEP, avoid_self=True, stop_on_collision=STOP_ON_COLLISION)
        output(points)

        # Attractor
        BASE_TITLE = "attractor"
        np.random.seed(SEED)
        points = build_points(
            turns, step=STEP,
            avoid_self=False,
            use_attractor=True, attractor=ATTRACTOR, bias_strength=BIAS_STRENGTH
        )
        output(points)

        # Attractor + self-avoid
        BASE_TITLE = "attractor_self_avoid"
        np.random.seed(SEED)
        points = build_points(
            turns, step=STEP,
            avoid_self=True, stop_on_collision=STOP_ON_COLLISION,
            use_attractor=True, attractor=ATTRACTOR, bias_strength=BIAS_STRENGTH
        )
        output(points)

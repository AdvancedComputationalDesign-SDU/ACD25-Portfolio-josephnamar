import os
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import LineString
from matplotlib.collections import LineCollection

# =========================
# CONFIG
# =========================
SEED = 0
ITERATIONS = 3
STEP = 1.0

OUT_DIR = os.path.join(os.path.dirname(__file__), "images")
OUT_NAME = "a2_01_baseline_colored.png"

os.makedirs(OUT_DIR, exist_ok=True)
np.random.seed(SEED)


# =========================
# DRAGON TURN SEQUENCE
# =========================
def dragon_turns(n):
    if n <= 0:
        return []
    prev = dragon_turns(n - 1)
    inv_rev = [-t for t in reversed(prev)]
    return prev + [1] + inv_rev


# =========================
# BUILD POINTS
# =========================
def build_points(turns, step=1.0):
    heading = 0  # 0:E, 1:N, 2:W, 3:S
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

    dx, dy = step_vec(heading)
    x += dx
    y += dy
    pts.append((x, y))

    for t in turns:
        heading = (heading + t) % 4
        dx, dy = step_vec(heading)
        x += dx
        y += dy
        pts.append((x, y))

    return pts


# =========================
# COLORED PLOTTING
# =========================
def save_colored(points, out_path):
    # Build line segments [(p0,p1), (p1,p2), ...]
    segments = [
        [points[i], points[i + 1]]
        for i in range(len(points) - 1)
    ]

    # Color index per segment
    values = np.arange(len(segments))

    lc = LineCollection(
        segments,
        cmap="viridis",
        linewidth=1.0
    )
    lc.set_array(values)

    fig, ax = plt.subplots()
    ax.add_collection(lc)

    ax.set_aspect("equal", adjustable="box")
    ax.autoscale()
    ax.axis("off")

    fig.savefig(out_path, dpi=300, bbox_inches="tight", pad_inches=0)
    plt.close(fig)


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    turns = dragon_turns(ITERATIONS)
    points = build_points(turns, step=STEP)

    out_path = os.path.join(OUT_DIR, OUT_NAME)
    save_colored(points, out_path)

    print(f"Saved: {out_path}")

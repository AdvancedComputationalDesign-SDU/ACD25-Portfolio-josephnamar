import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

# =========================
# CONFIG
# =========================
MODE = "vis"   # "vis" or "save"
SEED = 42
ITERATIONS = [3, 7, 14]  
STEP = 1.0

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
# DRAGON TURN SEQUENCE
# =========================
def dragon_turns(n):
    if n <= 0:
        return []
    prev = dragon_turns(n - 1)
    inv_rev = [-t for t in reversed(prev)]
    # 0:E, 1:N, 2:W, 3:S
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

    # initial forward segment
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
# OUTPUT (vis or save)
# =========================
def output_colored(points, out_path=None, title=None):
    # Build line segments 
    segments = [[points[i], points[i + 1]] for i in range(len(points) - 1)]
    values = np.arange(len(segments))

    lc = LineCollection(segments, cmap="viridis", linewidth=1.0)
    lc.set_array(values)

    # Create figure and axis
    fig, ax = plt.subplots()
    ax.add_collection(lc)
    ax.set_aspect("equal", adjustable="box")
    ax.autoscale()
    ax.axis("off")

    full_title = make_title(BASE_TITLE)

    # Annotation below the figure
    fig.text(
        0.5,
        0.02,
        f"iterations = {ITERATIONS}   |   seed = {SEED}",
        ha="center",
        va="center",
        fontsize=9
    )
    # Visualise or save the figure
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
# MAIN
# =========================
if __name__ == "__main__":

    for i in ITERATIONS:
        ITERATIONS = i 

        turns = dragon_turns(ITERATIONS)
        points = build_points(turns, step=STEP)

        output_colored(points, BASE_TITLE)



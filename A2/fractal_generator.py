import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from shapely.geometry import LineString

# =========================
# CONFIG
# =========================
MODE = "vis"   # "vis" or "save"
SEED = 42
ITERATION_LIST = [3, 7, 10]
STEP = 1.0

AVOID_SELF = True          # True: avoid self-intersection, False: allow self-intersection
STOP_ON_COLLISION = False  


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
def build_points(turns, step=1.0, avoid_self=False, stop_on_collision=True):
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

    # Keep existing segments as tuples of points: [((x0,y0),(x1,y1)), ...]
    segments = []

    # initial forward segment
    dx, dy = step_vec(heading)
    x2, y2 = x + dx, y + dy

    # add initial segment
    segments.append(((x, y), (x2, y2)))
    x, y = x2, y2
    pts.append((x, y))

    for t in turns:
        heading = (heading + t) % 4
        dx, dy = step_vec(heading)
        nx, ny = x + dx, y + dy

        if avoid_self:
            # candidate new segment
            cand = LineString([(x, y), (nx, ny)])

            # check against all older segments except the most recent one
            # (adjacent segment shares endpoint; that's always "intersecting")
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
                    # skip this step and continue to next turn
                    continue

        segments.append(((x, y), (nx, ny)))
        x, y = nx, ny
        pts.append((x, y))

    return pts



# =========================
# OUTPUT (vis or save)
# =========================
def output(points, out_path=None, title=None):
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
        full_title,
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

    for i in ITERATION_LIST:
        ITERATIONS = i
        turns = dragon_turns(ITERATIONS)

        # baseline (no collision avoidance)
        BASE_TITLE = "baseline"
        points = build_points(turns, step=STEP, avoid_self=False)
        output(points)

        # self-avoid version
        BASE_TITLE = "self_avoid"
        points = build_points(turns, step=STEP, avoid_self=True, stop_on_collision=STOP_ON_COLLISION)
        output(points)




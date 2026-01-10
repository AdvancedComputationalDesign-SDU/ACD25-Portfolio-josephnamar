import os
import numpy as np
import matplotlib.pyplot as plt
from perlin_numpy import generate_perlin_noise_2d

# =========================
# CONFIG
# =========================
MODE = "save"   # "vis" or "save"
SEED = 0

h = 1280
w = 1280

OUT_DIR = os.path.join(os.path.dirname(__file__), "images")
os.makedirs(OUT_DIR, exist_ok=True)

np.random.seed(SEED)

# =========================
# HELPERS
# =========================
def center(h, w):
    if h % 2 == 0:
        center_h = h // 2 - 1
    else:
        center_h = h // 2

    if w % 2 == 0:
        center_w = w // 2 - 1
    else:
        center_w = w // 2

    return center_h, center_w


center_h, center_w = center(h, w)


def output_pattern(pattern, name):
    """
    MODE = "vis"  -> visualize (matches saving scaling)
    MODE = "save" -> save to A1/images
    """
    if MODE == "vis":
        plt.figure()
        plt.imshow(pattern, vmin=0, vmax=255)
        plt.axis("off")
        plt.title(name)
        plt.show()
    elif MODE == "save":
        path = os.path.join(OUT_DIR, f"{name}.png")
        plt.imsave(path, pattern, vmin=0, vmax=255)
    else:
        raise ValueError("MODE must be 'vis' or 'save'")


# =========================
# Example_01: central gradient + stripes + cross
# =========================
pattern = np.zeros((h, w, 3), dtype=np.uint8)
y, x = np.ogrid[:h, :w]
dist = np.sqrt((x - center_w) ** 2 + (y - center_h) ** 2)
gradient = dist / dist.max() * 255

pattern[:, :, 0] = gradient * 2
pattern[:, :, 1] = gradient
pattern[:, :, 2] = gradient * 4

pattern[:, ::2, 0] = 255  # Red channel
pattern[::4, w // 3:2 * w // 3, 1] = 255  # Green channel
pattern[w // 3:2 * w // 3, :, 1] = 255  # Green channel
pattern[:, 2 * w // 3::5, 2] = 255  # Blue channel

a, b = 45, 15
pattern[int(center_h - (h / a)):int(center_h + (h / a)),
        int(center_w - (w / b)):int(center_w + (w / b))] = \
    255 - pattern[int(center_h - (h / a)):int(center_h + (h / a)),
                  int(center_w - (w / b)):int(center_w + (w / b))]

pattern[int(center_h - (h / b)):int(center_h + (h / b)),
        int(center_w - (w / a)):int(center_w + (w / a))] = \
    255 - pattern[int(center_h - (h / b)):int(center_h + (h / b)),
                  int(center_w - (w / a)):int(center_w + (w / a))]

output_pattern(pattern, "ex01_cross_inversion")

# invert based on green channel (as in your code)
pattern[:, :, 2] = 200 - pattern[:, :, 1]

# white cross
pattern[int(center_h - (h / a)):int(center_h + (h / a)),
        int(center_w - (w / b)):int(center_w + (w / b))] = 255
pattern[int(center_h - (h / b)):int(center_h + (h / b)),
        int(center_w - (w / a)):int(center_w + (w / a))] = 255

output_pattern(pattern, "ex01_white_cross")


# =========================
# Example_02: Perlin noise variations
# =========================
pattern = np.zeros((h, w, 3), dtype=np.uint8)

np.random.seed(SEED)
noise = generate_perlin_noise_2d((h, w), (8, 8), tileable=(True, False))
normalized_noise = (noise - noise.min()) / (noise.max() - noise.min()) * 255

pattern[:, :, 0] = (normalized_noise.astype(np.uint16) * 200).astype(np.uint8)
pattern[:, :, 1] = normalized_noise.astype(np.uint8)
pattern[:, :, 2] = normalized_noise.astype(np.uint8)
output_pattern(pattern, "ex02_perlin_base")

pattern[:, :, 2] = (normalized_noise.astype(np.uint16) * 10).astype(np.uint8)
output_pattern(pattern, "ex02_perlin_blue10")

pattern[:, :, 1] = (normalized_noise.astype(np.uint16) * 70).astype(np.uint8)
output_pattern(pattern, "ex02_perlin_green70")

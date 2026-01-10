import os
import numpy as np
import matplotlib.pyplot as plt
from perlin_numpy import generate_perlin_noise_2d




# CONFIG

MODE = "vis"      # "vis" or "save"
SEED = 0

h = 1280
w = 1280

OUT_DIR = os.path.join(os.path.dirname(__file__), "images")
os.makedirs(OUT_DIR, exist_ok=True)

np.random.seed(SEED)


# HELPERS 

# find center pixel
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
    If MODE == 'vis'  -> show image
    If MODE == 'save' -> save image to A1/images
    """
    if MODE == "vis":
        plt.imshow(pattern)
        plt.axis("off")
        plt.title(name)
        plt.show()
    elif MODE == "save":
        path = os.path.join(OUT_DIR, f"{name}.png")
        plt.imsave(path, pattern)
    else:
        raise ValueError("MODE must be 'vis' or 'save'")


# =========================
# Example_05: central gradient + stripes + cross
# =========================
pattern = np.zeros((h, w, 3), dtype=np.uint8)

y, x = np.ogrid[:h, :w]
dist = np.sqrt((x - center_w) ** 2 + (y - center_h) ** 2)
gradient = dist / dist.max() * 255

pattern[:, :, 0] = np.clip(gradient * 2, 0, 255)
pattern[:, :, 1] = np.clip(gradient, 0, 255)
pattern[:, :, 2] = np.clip(gradient * 4, 0, 255)

# stripes
pattern[:, ::2, 0] = 255
pattern[::4, w // 3:2 * w // 3, 1] = 255
pattern[w // 3:2 * w // 3, :, 1] = 255
pattern[:, 2 * w // 3::5, 2] = 255

# cross inversion
a, b = 45, 15
pattern[int(center_h - h / a):int(center_h + h / a),
        int(center_w - w / b):int(center_w + w / b)] = \
    255 - pattern[int(center_h - h / a):int(center_h + h / a),
                  int(center_w - w / b):int(center_w + w / b)]

pattern[int(center_h - h / b):int(center_h + h / b),
        int(center_w - w / a):int(center_w + w / a)] = \
    255 - pattern[int(center_h - h / b):int(center_h + h / b),
                  int(center_w - w / a):int(center_w + w / a)]

output_pattern(pattern, "ex05_cross_inversion")

# invert based on green channel (as in your code)
pattern[:, :, 2] = np.clip(200 - pattern[:, :, 1], 0, 255)

# white cross
pattern[int(center_h - h / a):int(center_h + h / a),
        int(center_w - w / b):int(center_w + w / b)] = 255
pattern[int(center_h - h / b):int(center_h + h / b),
        int(center_w - w / a):int(center_w + w / a)] = 255

output_pattern(pattern, "ex05_white_cross")


# =========================
# Example_08: Perlin noise variations
# =========================
pattern = np.zeros((h, w, 3), dtype=np.uint8)

noise = generate_perlin_noise_2d((h, w), (8, 8), tileable=(True, False))
normalized_noise = (noise - noise.min()) / (noise.max() - noise.min()) * 255
n = normalized_noise.astype(np.float32)

# base
pattern[:, :, 0] = np.clip(n * 200, 0, 255)
pattern[:, :, 1] = np.clip(n, 0, 255)
pattern[:, :, 2] = np.clip(n, 0, 255)
output_pattern(pattern, "ex08_perlin_base")

# blue *10
pattern[:, :, 2] = np.clip(n * 10, 0, 255)
output_pattern(pattern, "ex08_perlin_blue10")

# green *70
pattern[:, :, 1] = np.clip(n * 70, 0, 255)
output_pattern(pattern, "ex08_perlin_green70")

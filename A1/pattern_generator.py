"""
Assignment A1 - Pattern Generator

This script generates a set of 2D raster patterns using procedural techniques.
The focus is on explicit pixel-level control, channel-wise manipulation (RGB),
and reproducibility through deterministic parameters.

The output consists of multiple pattern variations that demonstrate:
- Gradient construction from geometric distance fields
- Discrete rule-based pattern overlays (stripes and crosses)
- Channel-dependent inversion and recombination
- Stochastic texture generation using Perlin noise

All patterns are generated at a fixed resolution and either visualized
interactively or saved to disk depending on the selected MODE.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from perlin_numpy import generate_perlin_noise_2d

# =========================
# GLOBAL CONFIGURATION
# =========================
# Controls execution mode, random determinism, and output resolution

# MODE:
# "vis"  -> display patterns using matplotlib
# "save" -> export patterns as PNG files
MODE = "save"   # "vis" or "save"

# Random seed to ensure reproducible stochastic patterns
SEED = 0

# Output image resolution (height x width in pixels)
h = 1280
w = 1280

OUT_DIR = os.path.join(os.path.dirname(__file__), "images")
os.makedirs(OUT_DIR, exist_ok=True)

np.random.seed(SEED)

# =========================
# UTILITY FUNCTIONS
# =========================

# Compute the central pixel of the image grid
# Handles both even and odd dimensions explicitly
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

# Output the generated pattern
def output_pattern(pattern, name):
    """
    Handle pattern output based on the selected MODE.

    Parameters
    ----------
    pattern : np.ndarray
        RGB image array with values in the range [0, 255].
    name : str
        Filename or window title identifier.

    Notes
    -----
    Visualization and saving use identical scaling to ensure
    consistency between preview and exported results.
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
# EXAMPLE 01
# Central radial gradient with deterministic geometric overlays
# =========================

# Generate a radial distance-based gradient from the image center
pattern = np.zeros((h, w, 3), dtype=np.uint8)
y, x = np.ogrid[:h, :w]
# Euclidean distance field used as the basis for the gradient
dist = np.sqrt((x - center_w) ** 2 + (y - center_h) ** 2)
gradient = dist / dist.max() * 255

pattern[:, :, 0] = gradient * 2
pattern[:, :, 1] = gradient
pattern[:, :, 2] = gradient * 4

output_pattern(pattern, "ex01_01_gradient")

# Overlay discrete stripe patterns using index-based slicing
# Each RGB channel is modified independently
pattern[:, ::2, 0] = 255  # Red channel
pattern[::4, w // 3:2 * w // 3, 1] = 255  # Green channel
pattern[w // 3:2 * w // 3, :, 1] = 255  # Green channel
pattern[:, 2 * w // 3::5, 2] = 255  # Blue channel

output_pattern(pattern, "ex01_02_gradient_stripes")

# Invert pixel values in two orthogonal rectangular regions
# forming a cross centered in the image
a, b = 45, 15
pattern[int(center_h - (h / a)):int(center_h + (h / a)),
        int(center_w - (w / b)):int(center_w + (w / b))] = \
    255 - pattern[int(center_h - (h / a)):int(center_h + (h / a)),
                  int(center_w - (w / b)):int(center_w + (w / b))]

pattern[int(center_h - (h / b)):int(center_h + (h / b)),
        int(center_w - (w / a)):int(center_w + (w / a))] = \
    255 - pattern[int(center_h - (h / b)):int(center_h + (h / b)),
                  int(center_w - (w / a)):int(center_w + (w / a))]

output_pattern(pattern, "ex01_03_cross_inversion")

# Derive the blue channel from an inverted green channel relationship
pattern[:, :, 2] = 200 - pattern[:, :, 1]

# Overwrite the central cross region with maximum intensity (white)
# to create a strong geometric contrast
pattern[int(center_h - (h / a)):int(center_h + (h / a)),
        int(center_w - (w / b)):int(center_w + (w / b))] = 255
pattern[int(center_h - (h / b)):int(center_h + (h / b)),
        int(center_w - (w / a)):int(center_w + (w / a))] = 255

output_pattern(pattern, "ex01_04_white_cross")


# =========================
# EXAMPLE 02
# Stochastic texture generation using Perlin noise
# =========================

# Generate tileable Perlin noise as a continuous scalar field
pattern = np.zeros((h, w, 3), dtype=np.uint8)

np.random.seed(SEED)
noise = generate_perlin_noise_2d((h, w), (8, 8), tileable=(True, False))
# Normalize noise values to the 0–255 range for image encoding
normalized_noise = (noise - noise.min()) / (noise.max() - noise.min()) * 255

# Map the same noise field differently to each RGB channel
# to explore chromatic variation
pattern[:, :, 0] = (normalized_noise.astype(np.uint16) * 200).astype(np.uint8)
pattern[:, :, 1] = normalized_noise.astype(np.uint8)
pattern[:, :, 2] = normalized_noise.astype(np.uint8)
output_pattern(pattern, "ex02_perlin_base")

# Emphasize low-amplitude noise in the blue channel
pattern[:, :, 2] = (normalized_noise.astype(np.uint16) * 10).astype(np.uint8)
output_pattern(pattern, "ex02_perlin_blue10")

# Amplify mid-range noise values in the green channel
pattern[:, :, 1] = (normalized_noise.astype(np.uint16) * 70).astype(np.uint8)
output_pattern(pattern, "ex02_perlin_green70")

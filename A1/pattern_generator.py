# Assignment 1: NumPy Array Manipulation for 2D Pattern Generation

# Instructions:
# - Write your code to generate patterns using NumPy.
# - Use comments to explain your logic and the methods you're using.
# - Feel free to be creative and explore different techniques.

import numpy as np
import matplotlib.pyplot as plt

# Initialize your canvas (e.g., a 2D array filled with zeros)
# You can adjust the size as needed
canvas_height = 100  # Modify as desired
canvas_width = 100   # Modify as desired
canvas = np.zeros((canvas_height, canvas_width))

# Apply array manipulations to create a pattern
# Suggestions:
# - Use slicing and indexing to create stripes or checkerboards
# - Use mathematical functions to create gradients
# - Combine multiple patterns

# Example (you can modify or remove this):
# Create horizontal stripes
# for i in range(0, canvas_height, 20):
#     canvas[i:i+10, :] = 255  # Assign a value to create a stripe

# Introduce randomness to add variability
# Suggestions:
# - Use np.random functions to add noise
# - Randomly change pixel values within certain regions

# Example:
# noise = np.random.randint(0, 50, (canvas_height, canvas_width))
# canvas = canvas + noise

# Work with RGB channels
# Convert your 2D canvas to a 3D array for RGB representation
# Assign different colors to different parts of your pattern

# Example:
# canvas_rgb = np.stack((canvas, canvas, canvas), axis=2)

# Assign colors
# canvas_rgb[:, :, 0] = 255  # Modify the red channel
# canvas_rgb[:, :, 1] = canvas_rgb[:, :, 1] * 0.5  # Modify the green channel

# Ensure your array values are within the valid range (0-255)
# canvas_rgb = np.clip(canvas_rgb, 0, 255)

# Visualize and save your image
# plt.imshow(canvas_rgb.astype(np.uint8))
# plt.axis('off')  # Hide axis
# plt.show()

# Save the image to the images folder
# plt.savefig('images/pattern_example.png', bbox_inches='tight', pad_inches=0)
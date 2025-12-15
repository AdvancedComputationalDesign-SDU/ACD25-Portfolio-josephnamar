"""
Assignment 2: Fractal Generator

Author: Your Name

Description:
This script generates fractal patterns using recursive functions and geometric transformations.
"""

# Import necessary libraries
import math
import matplotlib.pyplot as plt
from shapely.geometry import LineString
from shapely.affinity import rotate, translate
import random

# Global list to store all line segments
line_list = []

def generate_fractal(start_point, angle, length, depth, max_depth, angle_change, length_scaling_factor):
    """
    Recursive function to generate fractal patterns.

    Parameters:
    - start_point: Tuple (x, y), starting coordinate.
    - angle: Float, current angle in degrees.
    - length: Float, length of the current line segment.
    - depth: Int, current recursion depth.
    - max_depth: Int, maximum recursion depth.
    - angle_change: Float, angle change at each recursion.
    - length_scaling_factor: Float, scaling factor for the length.
    """
    if depth > max_depth:
        return

    # Calculate the end point of the line segment
    end_x = start_point[0] + length * math.cos(math.radians(angle))
    end_y = start_point[1] + length * math.sin(math.radians(angle))
    end_point = (end_x, end_y)

    # Create a line segment using Shapely
    line = LineString([start_point, end_point])
    line_list.append(line)

    # Update the length for the next recursion
    new_length = length * length_scaling_factor

    # Increment depth
    next_depth = depth + 1

    # Recursive calls for branches
    generate_fractal(end_point, angle + angle_change, new_length, next_depth, max_depth, angle_change, length_scaling_factor)
    generate_fractal(end_point, angle - angle_change, new_length, next_depth, max_depth, angle_change, length_scaling_factor)

# Main execution
if __name__ == "__main__":
    # Parameters
    start_point = (0, 0)
    initial_angle = 90
    initial_length = 100
    recursion_depth = 0
    max_recursion_depth = 5
    angle_change = 30
    length_scaling_factor = 0.7

    # Clear the line list
    line_list.clear()

    # Generate the fractal
    generate_fractal(start_point, initial_angle, initial_length, recursion_depth, max_recursion_depth, angle_change, length_scaling_factor)

    # Visualization
    fig, ax = plt.subplots()
    for line in line_list:
        x, y = line.xy
        ax.plot(x, y, color='green', linewidth=1)

    # Optional: Customize the plot
    ax.set_aspect('equal')
    plt.axis('off')
    plt.show()

    # Save the figure
    fig.savefig('images/fractal_tree.png', dpi=300, bbox_inches='tight')

    # Repeat the process with different parameters for additional fractals
    # ...
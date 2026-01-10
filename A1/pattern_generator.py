import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
import matplotlib.animation as animation
from perlin_numpy  import generate_perlin_noise_2d


#array size
h = 1280
w = 1280

# function to find the center of the array
def center(h, w):
    if h % 2 == 0:
        center_h = h // 2 - 1  
    else:
        center_h = h//2

    if w % 2 == 0:
        center_w = w // 2 - 1 
    else:
        center_w = w//2

    return center_h, center_w

center_h, center_w = center(h, w)

# function to visualize the pattern
def visualize_pattern(pattern):
    plt.imshow(pattern)
    plt.axis('off')
    plt.show() 


# Example_01 of pattern creation
pattern = np.zeros((h, w, 3), dtype=np.uint8)
pattern[:, ::2, 0] = 255  # Red channel
pattern[::4, w//3:2*w//3, 1] = 255  # Green channel
pattern[:, 2*w//3::5, 2] = 255  # Blue channel


# Example_05 of pattern creation / central gradient
pattern = np.zeros((h, w, 3), dtype=np.uint8)
y, x = np.ogrid[:h, :w]
dist = np.sqrt((x - center_w)**2 + (y - center_h)**2)
gradient = dist / dist.max() * 255
pattern[:, :, 0] = gradient*2
pattern[:, :, 1] = gradient 
pattern[:, :, 2] = gradient *4

pattern[:, ::2, 0] = 255  # Red channel
pattern[::4, w//3:2*w//3, 1] = 255  # Green channel
pattern[w//3:2*w//3,:, 1] = 255  # Green channel
pattern[:, 2*w//3::5, 2] = 255  # Blue channel

# sliced_pattern = pattern[int(center_h-(h/20)):int(center_h+(h/20)), int(center_w-(w/20)):int(center_w+(w/20))]
# sliced_pattern_recolor = 255 - sliced_pattern
a, b = 45, 15
pattern[int(center_h-(h/a)):int(center_h+(h/a)), int(center_w-(w/b)):int(center_w+(w/b))] = 255- pattern[int(center_h-(h/a)):int(center_h+(h/a)), int(center_w-(w/b)):int(center_w+(w/b))]
pattern[int(center_h-(h/b)):int(center_h+(h/b)), int(center_w-(w/a)):int(center_w+(w/a))] = 255- pattern[int(center_h-(h/b)):int(center_h+(h/b)), int(center_w-(w/a)):int(center_w+(w/a))]

visualize_pattern(pattern)

#invert green channel
pattern[:, :, 2] = 200 - pattern[:, :, 1]

#invert sliced cross
pattern[int(center_h-(h/a)):int(center_h+(h/a)), int(center_w-(w/b)):int(center_w+(w/b))] = 255
pattern[int(center_h-(h/b)):int(center_h+(h/b)), int(center_w-(w/a)):int(center_w+(w/a))] = 255

visualize_pattern(pattern)


# Example_08 of perlin noise pattern creation
pattern = np.zeros((h, w, 3), dtype=np.uint8)
np.random.seed(0)  
noise = generate_perlin_noise_2d((h, w), (8,8), tileable=(True, False))
normalized_noise = (noise - noise.min()) / (noise.max() - noise.min()) * 255
pattern[:, :, 0] = normalized_noise.astype(np.uint16) *200
pattern[:, :, 1] = (normalized_noise).astype(np.uint16)
pattern[:, :, 2] = (normalized_noise).astype(np.uint16)
visualize_pattern(pattern)

pattern[:, :, 2] =(normalized_noise).astype(np.uint16) *10
visualize_pattern(pattern)

pattern[:, :, 1] =(normalized_noise).astype(np.uint16) *70
visualize_pattern(pattern)

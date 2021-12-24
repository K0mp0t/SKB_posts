import math
import numpy as np
from PIL import Image
from colorthief import ColorThief
from colormath.color_diff import delta_e_cie2000
from colormath.color_conversions import convert_color
from colormath.color_objects import sRGBColor, LabColor

def hilo(a, b, c):
    if c < b: b, c = c, b
    if b < a: a, b = b, a
    if c < b: b, c = c, b
    return a + c


def complement(r, g, b):
    k = hilo(r, g, b)
    return tuple(k - u for u in (r, g, b))


def get_complement_colors(image, colors_n):
    palette = ColorThief(image).get_palette(color_count=colors_n - 1)
    return [complement(*rgb) for rgb in palette]


def display_colors(colors, size=128):
    data = np.zeros((int(size / len(colors)), size, 3), dtype=np.uint8)
    for i in range(int(size / len(colors))):
        for j in range(size):
            data[i, j] = colors[math.floor(j / (size / len(colors)))]
    return Image.fromarray(data)


def get_colors_dist(color1, color2):
    return delta_e_cie2000(convert_color(sRGBColor(*color1), LabColor),
                           convert_color(sRGBColor(*color2), LabColor))


def get_true(color, result):
    for cl in result:
        if get_colors_dist(color, cl) < 20:
            return False
    return True


def get_based_colors(base, comp):
    result = []
    for comp_color in comp:
        dists = {}
        for base_color in base:
            dists[base_color] = get_colors_dist(comp_color, base_color)
        for color in sorted(dists, key=dists.get):
            if color in result:
                continue
            if not get_true(color, result):
                continue
            result.append(color)
            break
    return result

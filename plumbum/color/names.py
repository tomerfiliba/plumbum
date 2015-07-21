'''
Names for the standard and extended color set.
Extended set is similar to `vim wiki <http://vim.wikia.com/wiki/Xterm256_color_names_for_console_Vim>`_, `colored <https://pypi.python.org/pypi/colored>`_, etc. Colors based on `wikipedia <https://en.wikipedia.org/wiki/ANSI_escape_code#Colors>`_.

You can access the index of the colors with names.index(name). You can access the
rgb values with ``r=int(html[n][1:3],16)``, etc.
'''

from __future__ import division, print_function

color_names = '''\
black
red
green
yellow
blue
magenta
cyan
light_gray
dark_gray
light_red
light_green
light_yellow
light_blue
light_magenta
light_cyan
white
grey_0
navy_blue
dark_blue
blue_3
blue_3
blue_1
dark_green
deep_sky_blue_4
deep_sky_blue_4
deep_sky_blue_4
dodger_blue_3
dodger_blue_2
green_4
spring_green_4
turquoise_4
deep_sky_blue_3
deep_sky_blue_3
dodger_blue_1
green_3
spring_green_3
dark_cyan
light_sea_green
deep_sky_blue_2
deep_sky_blue_1
green_3
spring_green_3
spring_green_2
cyan_3
dark_turquoise
turquoise_2
green_1
spring_green_2
spring_green_1
medium_spring_green
cyan_2
cyan_1
dark_red
deep_pink_4
purple_4
purple_4
purple_3
blue_violet
orange_4
grey_37
medium_purple_4
slate_blue_3
slate_blue_3
royal_blue_1
chartreuse_4
dark_sea_green_4
pale_turquoise_4
steel_blue
steel_blue_3
cornflower_blue
chartreuse_3
dark_sea_green_4
cadet_blue
cadet_blue
sky_blue_3
steel_blue_1
chartreuse_3
pale_green_3
sea_green_3
aquamarine_3
medium_turquoise
steel_blue_1
chartreuse_2
sea_green_2
sea_green_1
sea_green_1
aquamarine_1
dark_slate_gray_2
dark_red
deep_pink_4
dark_magenta
dark_magenta
dark_violet
purple
orange_4
light_pink_4
plum_4
medium_purple_3
medium_purple_3
slate_blue_1
yellow_4
wheat_4
grey_53
light_slate_grey
medium_purple
light_slate_blue
yellow_4
dark_olive_green_3
dark_sea_green
light_sky_blue_3
light_sky_blue_3
sky_blue_2
chartreuse_2
dark_olive_green_3
pale_green_3
dark_sea_green_3
dark_slate_gray_3
sky_blue_1
chartreuse_1
light_green
light_green
pale_green_1
aquamarine_1
dark_slate_gray_1
red_3
deep_pink_4
medium_violet_red
magenta_3
dark_violet
purple
dark_orange_3
indian_red
hot_pink_3
medium_orchid_3
medium_orchid
medium_purple_2
dark_goldenrod
light_salmon_3
rosy_brown
grey_63
medium_purple_2
medium_purple_1
gold_3
dark_khaki
navajo_white_3
grey_69
light_steel_blue_3
light_steel_blue
yellow_3
dark_olive_green_3
dark_sea_green_3
dark_sea_green_2
light_cyan_3
light_sky_blue_1
green_yellow
dark_olive_green_2
pale_green_1
dark_sea_green_2
dark_sea_green_1
pale_turquoise_1
red_3
deep_pink_3
deep_pink_3
magenta_3
magenta_3
magenta_2
dark_orange_3
indian_red
hot_pink_3
hot_pink_2
orchid
medium_orchid_1
orange_3
light_salmon_3
light_pink_3
pink_3
plum_3
violet
gold_3
light_goldenrod_3
tan
misty_rose_3
thistle_3
plum_2
yellow_3
khaki_3
light_goldenrod_2
light_yellow_3
grey_84
light_steel_blue_1
yellow_2
dark_olive_green_1
dark_olive_green_1
dark_sea_green_1
honeydew_2
light_cyan_1
red_1
deep_pink_2
deep_pink_1
deep_pink_1
magenta_2
magenta_1
orange_red_1
indian_red_1
indian_red_1
hot_pink
hot_pink
medium_orchid_1
dark_orange
salmon_1
light_coral
pale_violet_red_1
orchid_2
orchid_1
orange_1
sandy_brown
light_salmon_1
light_pink_1
pink_1
plum_1
gold_1
light_goldenrod_2
light_goldenrod_2
navajo_white_1
misty_rose_1
thistle_1
yellow_1
light_goldenrod_1
khaki_1
wheat_1
cornsilk_1
grey_10_0
grey_3
grey_7
grey_11
grey_15
grey_19
grey_23
grey_27
grey_30
grey_35
grey_39
grey_42
grey_46
grey_50
grey_54
grey_58
grey_62
grey_66
grey_70
grey_74
grey_78
grey_82
grey_85
grey_89
grey_93'''.split()

_greys = (3.4, 7.4, 11, 15, 19, 23, 26.7, 30.49, 34.6, 38.6, 42.4, 46.4, 50, 54, 58, 62, 66, 69.8, 73.8, 77.7, 81.6, 85.3, 89.3, 93)

_grey_html = ['#' + format(int(x/100*16*16),'02x')*3 for x in _greys]

_normals =  [int(x,16) for x in '0 5f 87 af d7 ff'.split()]
_normal_html = ['#' + format(_normals[n//36],'02x') + format(_normals[n//6%6],'02x') + format(_normals[n%6],'02x') for n in range(16-16,232-16)]

_base_pattern = [(n//4,n//2%2,n%2) for n in range(8)]
_base_html = (['#{2:02x}{1:02x}{0:02x}'.format(x[0]*192,x[1]*192,x[2]*192) for x in  _base_pattern]
        + ['#808080']
        + ['#{2:02x}{1:02x}{0:02x}'.format(x[0]*255,x[1]*255,x[2]*255) for x in               _base_pattern][1:])
color_html = _base_html + _normal_html + _grey_html

color_codes_simple = list(range(8)) + list(range(60,68))
"""Simple colors, remember that reset is #9, second half is non as common."""


# Attributes
attributes_ansi = dict(
    bold=1,
    dim=2,
    italics=3,
    underline=4,
    reverse=7,
    hidden=8,
    strikeout=9,
    )

#Functions to be used for color name operations
def _distance_to_color(r, g, b, color):
    """This computes the distance to a color, should be minimized"""
    rgb = (int(color[1:3],16), int(color[3:5],16), int(color[5:7],16))
    return (r-rgb[0])**2 + (g-rgb[1])**2 + (b-rgb[2])**2


def find_nearest_color(r, g, b, color_slice=slice(None, None, None)):
    """This is a slow way to find the nearest color."""
    distances = [_distance_to_color(r, g, b, color) for color in color_html[color_slice]]
    return  min(range(len(distances)), key=distances.__getitem__)

def find_nearest_simple_color(r, g, b):
    """This will only return simple colors!
    Breaks the colorspace into cubes, returns color"""
    midlevel = 0x40 # Since bright is not included

    # The colors are originised so that it is a
    # 3D cube, black at 0,0,0, white at 1,1,1
    # Compressed to linear_integers r,g,b
    # [[[0,1],[2,3]],[[4,5],[6,7]]]
    # r*1 + g*2 + b*4
    return (r>=midlevel)*1 + (g>=midlevel)*2 + (b>=midlevel)*4

def find_nearest_colorblock(*rgb):
    """This finds the nearest color based on block system, only works
    for 17-232 color values."""
    r, g, b = (round(v / 256. * 5) for v in rgb)
    return (16 + 36 * r + 6 * g + b)

def from_html(color):
    """Convert html hex code to rgb"""
    if len(color) != 7 or color[0] != '#':
        raise ValueError("Invalid length of html code")
    return (int(color[1:3],16), int(color[3:5],16), int(color[5:7],16))


def print_html_table():
    """Prints html names for documentation"""
    print(r'<ol start=0>')
    for i in range(256):
        name = color_names[i]
        val = color_html[i]
        print(r'  <li><font color="' + val
                + r'">&#x25a0</font> <code>' + val
                + r'</code> ' + name
                + r'</li>')
    print(r'</ol>')

'''
Names for the standard and extended color set.
Extended set is similar to `vim wiki <http://vim.wikia.com/wiki/Xterm256_color_names_for_console_Vim>`_, `colored <https://pypi.python.org/pypi/colored>`_, etc. Colors based on `wikipedia <https://en.wikipedia.org/wiki/ANSI_escape_code#Colors>`_.

You can access the index of the colors with names.index(name). You can access the
rgb values with ``r=int(html[n][1:3],16)``, etc.
'''

_named_colors = '''\
black,#000000
red,#c00000
green,#00c000
yellow,#c0c000
blue,#0000c0
magenta,#c000c0
cyan,#00c0c0
light_gray,#c0c0c0
dark_gray,#808080
light_red,#ff0000
light_green,#00ff00
light_yellow,#ffff00
light_blue,#0000ff
light_magenta,#ff00ff
light_cyan,#00ffff
white,#ffffff
grey_0,#000000
navy_blue,#00005f
dark_blue,#000087
blue_3,#0000af
blue_3,#0000d7
blue_1,#0000ff
dark_green,#005f00
deep_sky_blue_4,#005f5f
deep_sky_blue_4,#005f87
deep_sky_blue_4,#005faf
dodger_blue_3,#005fd7
dodger_blue_2,#005fff
green_4,#008700
spring_green_4,#00875f
turquoise_4,#008787
deep_sky_blue_3,#0087af
deep_sky_blue_3,#0087d7
dodger_blue_1,#0087ff
green_3,#00af00
spring_green_3,#00af5f
dark_cyan,#00af87
light_sea_green,#00afaf
deep_sky_blue_2,#00afd7
deep_sky_blue_1,#00afff
green_3,#00d700
spring_green_3,#00d75f
spring_green_2,#00d787
cyan_3,#00d7af
dark_turquoise,#00d7d7
turquoise_2,#00d7ff
green_1,#00ff00
spring_green_2,#00ff5f
spring_green_1,#00ff87
medium_spring_green,#00ffaf
cyan_2,#00ffd7
cyan_1,#00ffff
dark_red,#5f0000
deep_pink_4,#5f005f
purple_4,#5f0087
purple_4,#5f00af
purple_3,#5f00d7
blue_violet,#5f00ff
orange_4,#5f5f00
grey_37,#5f5f5f
medium_purple_4,#5f5f87
slate_blue_3,#5f5faf
slate_blue_3,#5f5fd7
royal_blue_1,#5f5fff
chartreuse_4,#5f8700
dark_sea_green_4,#5f875f
pale_turquoise_4,#5f8787
steel_blue,#5f87af
steel_blue_3,#5f87d7
cornflower_blue,#5f87ff
chartreuse_3,#5faf00
dark_sea_green_4,#5faf5f
cadet_blue,#5faf87
cadet_blue,#5fafaf
sky_blue_3,#5fafd7
steel_blue_1,#5fafff
chartreuse_3,#5fd700
pale_green_3,#5fd75f
sea_green_3,#5fd787
aquamarine_3,#5fd7af
medium_turquoise,#5fd7d7
steel_blue_1,#5fd7ff
chartreuse_2,#5fff00
sea_green_2,#5fff5f
sea_green_1,#5fff87
sea_green_1,#5fffaf
aquamarine_1,#5fffd7
dark_slate_gray_2,#5fffff
dark_red,#870000
deep_pink_4,#87005f
dark_magenta,#870087
dark_magenta,#8700af
dark_violet,#8700d7
purple,#8700ff
orange_4,#875f00
light_pink_4,#875f5f
plum_4,#875f87
medium_purple_3,#875faf
medium_purple_3,#875fd7
slate_blue_1,#875fff
yellow_4,#878700
wheat_4,#87875f
grey_53,#878787
light_slate_grey,#8787af
medium_purple,#8787d7
light_slate_blue,#8787ff
yellow_4,#87af00
dark_olive_green_3,#87af5f
dark_sea_green,#87af87
light_sky_blue_3,#87afaf
light_sky_blue_3,#87afd7
sky_blue_2,#87afff
chartreuse_2,#87d700
dark_olive_green_3,#87d75f
pale_green_3,#87d787
dark_sea_green_3,#87d7af
dark_slate_gray_3,#87d7d7
sky_blue_1,#87d7ff
chartreuse_1,#87ff00
light_green,#87ff5f
light_green,#87ff87
pale_green_1,#87ffaf
aquamarine_1,#87ffd7
dark_slate_gray_1,#87ffff
red_3,#af0000
deep_pink_4,#af005f
medium_violet_red,#af0087
magenta_3,#af00af
dark_violet,#af00d7
purple,#af00ff
dark_orange_3,#af5f00
indian_red,#af5f5f
hot_pink_3,#af5f87
medium_orchid_3,#af5faf
medium_orchid,#af5fd7
medium_purple_2,#af5fff
dark_goldenrod,#af8700
light_salmon_3,#af875f
rosy_brown,#af8787
grey_63,#af87af
medium_purple_2,#af87d7
medium_purple_1,#af87ff
gold_3,#afaf00
dark_khaki,#afaf5f
navajo_white_3,#afaf87
grey_69,#afafaf
light_steel_blue_3,#afafd7
light_steel_blue,#afafff
yellow_3,#afd700
dark_olive_green_3,#afd75f
dark_sea_green_3,#afd787
dark_sea_green_2,#afd7af
light_cyan_3,#afd7d7
light_sky_blue_1,#afd7ff
green_yellow,#afff00
dark_olive_green_2,#afff5f
pale_green_1,#afff87
dark_sea_green_2,#afffaf
dark_sea_green_1,#afffd7
pale_turquoise_1,#afffff
red_3,#d70000
deep_pink_3,#d7005f
deep_pink_3,#d70087
magenta_3,#d700af
magenta_3,#d700d7
magenta_2,#d700ff
dark_orange_3,#d75f00
indian_red,#d75f5f
hot_pink_3,#d75f87
hot_pink_2,#d75faf
orchid,#d75fd7
medium_orchid_1,#d75fff
orange_3,#d78700
light_salmon_3,#d7875f
light_pink_3,#d78787
pink_3,#d787af
plum_3,#d787d7
violet,#d787ff
gold_3,#d7af00
light_goldenrod_3,#d7af5f
tan,#d7af87
misty_rose_3,#d7afaf
thistle_3,#d7afd7
plum_2,#d7afff
yellow_3,#d7d700
khaki_3,#d7d75f
light_goldenrod_2,#d7d787
light_yellow_3,#d7d7af
grey_84,#d7d7d7
light_steel_blue_1,#d7d7ff
yellow_2,#d7ff00
dark_olive_green_1,#d7ff5f
dark_olive_green_1,#d7ff87
dark_sea_green_1,#d7ffaf
honeydew_2,#d7ffd7
light_cyan_1,#d7ffff
red_1,#ff0000
deep_pink_2,#ff005f
deep_pink_1,#ff0087
deep_pink_1,#ff00af
magenta_2,#ff00d7
magenta_1,#ff00ff
orange_red_1,#ff5f00
indian_red_1,#ff5f5f
indian_red_1,#ff5f87
hot_pink,#ff5faf
hot_pink,#ff5fd7
medium_orchid_1,#ff5fff
dark_orange,#ff8700
salmon_1,#ff875f
light_coral,#ff8787
pale_violet_red_1,#ff87af
orchid_2,#ff87d7
orchid_1,#ff87ff
orange_1,#ffaf00
sandy_brown,#ffaf5f
light_salmon_1,#ffaf87
light_pink_1,#ffafaf
pink_1,#ffafd7
plum_1,#ffafff
gold_1,#ffd700
light_goldenrod_2,#ffd75f
light_goldenrod_2,#ffd787
navajo_white_1,#ffd7af
misty_rose_1,#ffd7d7
thistle_1,#ffd7ff
yellow_1,#ffff00
light_goldenrod_1,#ffff5f
khaki_1,#ffff87
wheat_1,#ffffaf
cornsilk_1,#ffffd7
grey_10_0,#ffffff
grey_3,#080808
grey_7,#121212
grey_11,#1c1c1c
grey_15,#262626
grey_19,#303030
grey_23,#3a3a3a
grey_27,#444444
grey_30,#4e4e4e
grey_35,#585858
grey_39,#626262
grey_42,#6c6c6c
grey_46,#767676
grey_50,#808080
grey_54,#8a8a8a
grey_58,#949494
grey_62,#9e9e9e
grey_66,#a8a8a8
grey_70,#b2b2b2
grey_74,#bcbcbc
grey_78,#c6c6c6
grey_82,#d0d0d0
grey_85,#dadada
grey_89,#e4e4e4
grey_93,#eeeeee
'''

color_names = [n.split(',')[0] for n in _named_colors.split()]
color_html = [n.split(',')[1] for n in _named_colors.split()]

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

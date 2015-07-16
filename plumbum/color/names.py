'''
Names for the standard and extended color set.
Extended set is similar to http://vim.wikia.com/wiki/Xterm256_color_names_for_console_Vim, https://pypi.python.org/pypi/colored, etc.

You can access the index of the colors with names.index(name). You can access the
rgb values with r=int(html[n][1:3],16), etc.
'''

_named_colors = '''\
0,black,#000000
1,red,#800000
2,green,#008000
3,yellow,#808000
4,blue,#000080
5,magenta,#800080
6,cyan,#008080
7,light_gray,#c0c0c0
8,dark_gray,#808080
9,light_red,#ff0000
10,light_green,#00ff00
11,light_yellow,#ffff00
12,light_blue,#0000ff
13,light_magenta,#ff00ff
14,light_cyan,#00ffff
15,white,#ffffff
16,grey_0,#000000
17,navy_blue,#00005f
18,dark_blue,#000087
19,blue_3,#0000af
20,blue_3,#0000d7
21,blue_1,#0000ff
22,dark_green,#005f00
23,deep_sky_blue_4,#005f5f
24,deep_sky_blue_4,#005f87
25,deep_sky_blue_4,#005faf
26,dodger_blue_3,#005fd7
27,dodger_blue_2,#005fff
28,green_4,#008700
29,spring_green_4,#00875f
30,turquoise_4,#008787
31,deep_sky_blue_3,#0087af
32,deep_sky_blue_3,#0087d7
33,dodger_blue_1,#0087ff
34,green_3,#00af00
35,spring_green_3,#00af5f
36,dark_cyan,#00af87
37,light_sea_green,#00afaf
38,deep_sky_blue_2,#00afd7
39,deep_sky_blue_1,#00afff
40,green_3,#00d700
41,spring_green_3,#00d75f
42,spring_green_2,#00d787
43,cyan_3,#00d7af
44,dark_turquoise,#00d7d7
45,turquoise_2,#00d7ff
46,green_1,#00ff00
47,spring_green_2,#00ff5f
48,spring_green_1,#00ff87
49,medium_spring_green,#00ffaf
50,cyan_2,#00ffd7
51,cyan_1,#00ffff
52,dark_red,#5f0000
53,deep_pink_4,#5f005f
54,purple_4,#5f0087
55,purple_4,#5f00af
56,purple_3,#5f00d7
57,blue_violet,#5f00ff
58,orange_4,#5f5f00
59,grey_37,#5f5f5f
60,medium_purple_4,#5f5f87
61,slate_blue_3,#5f5faf
62,slate_blue_3,#5f5fd7
63,royal_blue_1,#5f5fff
64,chartreuse_4,#5f8700
65,dark_sea_green_4,#5f875f
66,pale_turquoise_4,#5f8787
67,steel_blue,#5f87af
68,steel_blue_3,#5f87d7
69,cornflower_blue,#5f87ff
70,chartreuse_3,#5faf00
71,dark_sea_green_4,#5faf5f
72,cadet_blue,#5faf87
73,cadet_blue,#5fafaf
74,sky_blue_3,#5fafd7
75,steel_blue_1,#5fafff
76,chartreuse_3,#5fd700
77,pale_green_3,#5fd75f
78,sea_green_3,#5fd787
79,aquamarine_3,#5fd7af
80,medium_turquoise,#5fd7d7
81,steel_blue_1,#5fd7ff
82,chartreuse_2,#5fff00
83,sea_green_2,#5fff5f
84,sea_green_1,#5fff87
85,sea_green_1,#5fffaf
86,aquamarine_1,#5fffd7
87,dark_slate_gray_2,#5fffff
88,dark_red,#870000
89,deep_pink_4,#87005f
90,dark_magenta,#870087
91,dark_magenta,#8700af
92,dark_violet,#8700d7
93,purple,#8700ff
94,orange_4,#875f00
95,light_pink_4,#875f5f
96,plum_4,#875f87
97,medium_purple_3,#875faf
98,medium_purple_3,#875fd7
99,slate_blue_1,#875fff
100,yellow_4,#878700
101,wheat_4,#87875f
102,grey_53,#878787
103,light_slate_grey,#8787af
104,medium_purple,#8787d7
105,light_slate_blue,#8787ff
106,yellow_4,#87af00
107,dark_olive_green_3,#87af5f
108,dark_sea_green,#87af87
109,light_sky_blue_3,#87afaf
110,light_sky_blue_3,#87afd7
111,sky_blue_2,#87afff
112,chartreuse_2,#87d700
113,dark_olive_green_3,#87d75f
114,pale_green_3,#87d787
115,dark_sea_green_3,#87d7af
116,dark_slate_gray_3,#87d7d7
117,sky_blue_1,#87d7ff
118,chartreuse_1,#87ff00
119,light_green,#87ff5f
120,light_green,#87ff87
121,pale_green_1,#87ffaf
122,aquamarine_1,#87ffd7
123,dark_slate_gray_1,#87ffff
124,red_3,#af0000
125,deep_pink_4,#af005f
126,medium_violet_red,#af0087
127,magenta_3,#af00af
128,dark_violet,#af00d7
129,purple,#af00ff
130,dark_orange_3,#af5f00
131,indian_red,#af5f5f
132,hot_pink_3,#af5f87
133,medium_orchid_3,#af5faf
134,medium_orchid,#af5fd7
135,medium_purple_2,#af5fff
136,dark_goldenrod,#af8700
137,light_salmon_3,#af875f
138,rosy_brown,#af8787
139,grey_63,#af87af
140,medium_purple_2,#af87d7
141,medium_purple_1,#af87ff
142,gold_3,#afaf00
143,dark_khaki,#afaf5f
144,navajo_white_3,#afaf87
145,grey_69,#afafaf
146,light_steel_blue_3,#afafd7
147,light_steel_blue,#afafff
148,yellow_3,#afd700
149,dark_olive_green_3,#afd75f
150,dark_sea_green_3,#afd787
151,dark_sea_green_2,#afd7af
152,light_cyan_3,#afd7d7
153,light_sky_blue_1,#afd7ff
154,green_yellow,#afff00
155,dark_olive_green_2,#afff5f
156,pale_green_1,#afff87
157,dark_sea_green_2,#afffaf
158,dark_sea_green_1,#afffd7
159,pale_turquoise_1,#afffff
160,red_3,#d70000
161,deep_pink_3,#d7005f
162,deep_pink_3,#d70087
163,magenta_3,#d700af
164,magenta_3,#d700d7
165,magenta_2,#d700ff
166,dark_orange_3,#d75f00
167,indian_red,#d75f5f
168,hot_pink_3,#d75f87
169,hot_pink_2,#d75faf
170,orchid,#d75fd7
171,medium_orchid_1,#d75fff
172,orange_3,#d78700
173,light_salmon_3,#d7875f
174,light_pink_3,#d78787
175,pink_3,#d787af
176,plum_3,#d787d7
177,violet,#d787ff
178,gold_3,#d7af00
179,light_goldenrod_3,#d7af5f
180,tan,#d7af87
181,misty_rose_3,#d7afaf
182,thistle_3,#d7afd7
183,plum_2,#d7afff
184,yellow_3,#d7d700
185,khaki_3,#d7d75f
186,light_goldenrod_2,#d7d787
187,light_yellow_3,#d7d7af
188,grey_84,#d7d7d7
189,light_steel_blue_1,#d7d7ff
190,yellow_2,#d7ff00
191,dark_olive_green_1,#d7ff5f
192,dark_olive_green_1,#d7ff87
193,dark_sea_green_1,#d7ffaf
194,honeydew_2,#d7ffd7
195,light_cyan_1,#d7ffff
196,red_1,#ff0000
197,deep_pink_2,#ff005f
198,deep_pink_1,#ff0087
199,deep_pink_1,#ff00af
200,magenta_2,#ff00d7
201,magenta_1,#ff00ff
202,orange_red_1,#ff5f00
203,indian_red_1,#ff5f5f
204,indian_red_1,#ff5f87
205,hot_pink,#ff5faf
206,hot_pink,#ff5fd7
207,medium_orchid_1,#ff5fff
208,dark_orange,#ff8700
209,salmon_1,#ff875f
210,light_coral,#ff8787
211,pale_violet_red_1,#ff87af
212,orchid_2,#ff87d7
213,orchid_1,#ff87ff
214,orange_1,#ffaf00
215,sandy_brown,#ffaf5f
216,light_salmon_1,#ffaf87
217,light_pink_1,#ffafaf
218,pink_1,#ffafd7
219,plum_1,#ffafff
220,gold_1,#ffd700
221,light_goldenrod_2,#ffd75f
222,light_goldenrod_2,#ffd787
223,navajo_white_1,#ffd7af
224,misty_rose_1,#ffd7d7
225,thistle_1,#ffd7ff
226,yellow_1,#ffff00
227,light_goldenrod_1,#ffff5f
228,khaki_1,#ffff87
229,wheat_1,#ffffaf
230,cornsilk_1,#ffffd7
231,grey_10_0,#ffffff
232,grey_3,#080808
233,grey_7,#121212
234,grey_11,#1c1c1c
235,grey_15,#262626
236,grey_19,#303030
237,grey_23,#3a3a3a
238,grey_27,#444444
239,grey_30,#4e4e4e
240,grey_35,#585858
241,grey_39,#626262
242,grey_42,#6c6c6c
243,grey_46,#767676
244,grey_50,#808080
245,grey_54,#8a8a8a
246,grey_58,#949494
247,grey_62,#9e9e9e
248,grey_66,#a8a8a8
249,grey_70,#b2b2b2
250,grey_74,#bcbcbc
251,grey_78,#c6c6c6
252,grey_82,#d0d0d0
253,grey_85,#dadada
254,grey_89,#e4e4e4
255,grey_93,#eeeeee
'''

color_names_full = [n.split(',')[1] for n in _named_colors.split()]
color_html_full = [n.split(',')[2] for n in _named_colors.split()]

main_named_colors = slice(0,16)
normal_colors = slice(16,232)
grey_colors = slice(232,256)

def _distance_to_color(r, g, b, color):
    rgb = (int(color[1:3],16), int(color[3:5],16), int(color[5:7],16))
    """This computes the distance to a color, should be minimized"""
    return (r-rgb[0])**2 + (g-rgb[1])**2 + (b-rgb[2])**2


def find_nearest_color(r, g, b):
    """This is a slow way to find the nearest color."""
    distances = [_distance_to_color(r, g, b, color) for color in color_html_full]
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


def from_html(color):
    if len(color) != 7:
        raise ValueError("Invalid length of html code")
    return (int(color[1:3],16), int(color[3:5],16), int(color[5:7],16))

color_names_simple = [
    'black',
    'red',
    'green',
    'yellow',
    'blue',
    'magenta',
    'cyan',
    'white',
]
"""Simple colors, remember that reset is #9"""

color_html_simple = color_html_full[:7] + [color_html_full[15]]


attributes_simple = dict(
    reset=0,
    bold=1,
    dim=2,
    underline=4,
    blink=5,
    reverse=7,
    hidden=8
    )

def print_html_table():
    """Prints html names for documentation"""
    print(r'<ol start=0>')
    for i in range(256):
        name = color_names_full[i]
        val = color_html_full[i]
        print(r'  <li><font color="' + val
                + r'">&#x25a0</font> <code>' + val
                + r'</code> ' + name
                + r'</li>')
    print(r'</ol>')

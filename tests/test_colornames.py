from __future__ import with_statement, print_function
import unittest
from plumbum.color.names import find_nearest_color, color_html, find_nearest_simple_color, find_nearest_colorblock

class TestColorConvert(unittest.TestCase)

    def test_colorblock(self):

        red = (255, 0,  0)
        midway = None
        nearby = None

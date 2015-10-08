#!/usr/bin/env python
from __future__ import with_statement, print_function
import unittest
import os
from plumbum import colors

class TestVisualColor(unittest.TestCase):

    def setUp(self):
        if os.name == 'nt':
            try:
                import colorama
                colorama.init()
                self.colorama = colorama
                colors.use_color = 1
                print()
                print("Colorama initialized")
            except ImportError:
                self.colorama = None
        else:
            self.colorama = None

    def tearDown(self):
        if self.colorama:
            self.colorama.deinit()

    def testVisualColors(self):
        print()
        for c in colors.fg[:16]:
            with c:
                print('Cycle color test', end=' ')
            print(' - > back to normal')
        with colors:
            print(colors.fg.green + "Green "
                  + colors.bold + "Bold "
                  + ~colors.bold + "Normal")
        print("Reset all")

    def testToggleColors(self):
        print()
        print(colors.fg.red["This is in red"], "but this is not")
        print(colors.fg.green + "Hi, " + colors.bg[23]
              + "This is on a BG" + ~colors.bg + " and this is not but is still green.")
        colors.yellow.print("This is printed from color.")
        colors.reset()

        for attr in colors._style.attribute_names:
            print("This is", attr | getattr(colors, attr), "and this is not.")
            colors.reset()

    def testLimits(self):
        print()
        cval = colors.use_color
        colors.use_color = 4
        c = colors.rgb(123,40,200)
        print('True', repr(str(c)), repr(c))
        colors.use_color = 3
        print('Full', repr(str(c)), repr(c))
        colors.use_color = 2
        print('Simple', repr(str(c)), repr(c))
        colors.use_color = 1
        print('Basic', repr(str(c)), repr(c))
        colors.use_color = 0
        print('None', repr(str(c)), repr(c))
        colors.use_color = cval

if __name__ == '__main__':
    unittest.main()
